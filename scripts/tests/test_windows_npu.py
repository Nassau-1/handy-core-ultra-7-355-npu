"""Standard-library tests of the Handy Windows NPU protocol; no hardware needed."""
import importlib.util
import io
import struct
import unittest
from pathlib import Path


WORKER_FILE = Path(__file__).resolve().parents[2] / "src-tauri" / "src" / "windows_npu_worker.py"
spec = importlib.util.spec_from_file_location("windows_npu_worker", WORKER_FILE)
npu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(npu)


class FakeResult:
    texts = ["recognized text"]


class FakePipe:
    def __init__(self):
        self.audio = None
        self.kwargs = None

    def generate(self, audio, **kwargs):
        self.audio = list(audio)
        self.kwargs = kwargs
        return FakeResult()


class WindowsNpuProtocolTests(unittest.TestCase):
    def test_known_driver_incompatibility(self):
        hardware = {'cpu': 'Intel(R) Core(TM) Ultra 7 355', 'driver': '32.0.100.4509'}
        for version in ['2026.2.1-21919', '2026.3.1.0', '2026.4.0']:
            with self.subTest(version=version):
                self.assertIn('5540', npu.compatibility_error(hardware, version))
        self.assertIsNone(npu.compatibility_error(hardware, '2026.1.0'))
        hardware['driver'] = '32.0.100.5540'
        self.assertIsNone(npu.compatibility_error(hardware, '2026.2.1'))

    def test_driver_check_does_not_block_other_hardware_or_unknown_versions(self):
        self.assertIsNone(npu.compatibility_error({}, '2026.2.1'))
        self.assertIsNone(npu.compatibility_error(
            {'cpu': 'Intel Core Ultra 7 258V', 'driver': '32.0.100.4509'}, '2026.2.1'))
        self.assertIsNone(npu.compatibility_error(
            {'cpu': 'Intel Core Ultra 7 355', 'driver': None}, '2026.2.1'))

    def test_pcm_and_language(self):
        pipe = FakePipe()
        reader = io.BytesIO(struct.pack("<3f", 0.0, 0.125, -0.25))
        result = npu.process_request(
            pipe, reader, {"samples": 3, "language": "<|fr|>", "translate": False}
        )
        self.assertEqual(result, {"ok": True, "text": "recognized text"})
        self.assertEqual(pipe.audio, [0.0, 0.125, -0.25])
        self.assertEqual(pipe.kwargs, {"task": "transcribe", "language": "<|fr|>", "return_timestamps": False})

    def test_translation(self):
        pipe = FakePipe()
        reader = io.BytesIO(struct.pack("<f", 0.0))
        with self.assertRaisesRegex(ValueError, "does not support translation"):
            npu.process_request(pipe, reader, {"samples": 1, "translate": True})

    def test_auto_has_no_language_token(self):
        pipe = FakePipe()
        npu.process_request(pipe, io.BytesIO(struct.pack("<f", 0)), {"samples": 1})
        self.assertNotIn("language", pipe.kwargs)

    def test_reject_nonfinite_audio(self):
        for value in [float("nan"), float("inf"), -float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                npu.process_request(FakePipe(), io.BytesIO(struct.pack("<f", value)), {"samples": 1})

    def test_reject_truncated_pcm(self):
        with self.assertRaises(EOFError):
            npu.process_request(FakePipe(), io.BytesIO(b"\x00"), {"samples": 2})

    def test_reject_bad_length_without_reading(self):
        for length in [0, -1, True, "1", npu.MAX_SAMPLES + 1]:
            with self.subTest(length=length), self.assertRaises(ValueError):
                npu.process_request(FakePipe(), io.BytesIO(b""), {"samples": length})

    def test_reject_out_of_range_audio(self):
        with self.assertRaises(ValueError):
            npu.process_request(FakePipe(), io.BytesIO(struct.pack("<f", 9.0)), {"samples": 1})

    def test_reject_invalid_language(self):
        with self.assertRaises(ValueError):
            npu.process_request(
                FakePipe(), io.BytesIO(struct.pack("<f", 0)),
                {"samples": 1, "language": "<|auto|>"}
            )


if __name__ == "__main__":
    unittest.main()
