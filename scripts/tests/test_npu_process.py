"""Real subprocess/pipe tests with fake providers; these do not test ASR/NPU hardware."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

WORKER = Path(__file__).resolve().parents[2] / "src-tauri/src/windows_npu_worker.py"


class ProcessTests(unittest.TestCase):
    def run_worker(self, audio=b"", devices="['NPU']", probe=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "openvino.py").write_text(
                f"__version__='2026.2.1'\nclass Core:\n    available_devices={devices}\n"
            )
            (root / "openvino_genai.py").write_text('''
import os
from types import SimpleNamespace
__version__='2026.2.1.0'
class WhisperPipeline:
    def __init__(self, path, device, **config):
        assert device == 'NPU'
        assert os.path.isdir(config['CACHE_DIR'])
        os.write(1, b'native provider startup noise\\n')
    def generate(self, audio, **config):
        assert config['task'] == 'transcribe'
        return SimpleNamespace(texts=[config.get('language', 'auto')])
''')
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root)
            args = ["--probe"] if probe else [str(root / "model"), str(root / "cache")]
            # Test transport independently of the host's installed driver.
            runner = ("import runpy,sys; path=sys.argv.pop(1); "
                      "ns=runpy.run_path(path,run_name='worker_test'); "
                      "ns['main'].__globals__['windows_hardware']=lambda:{}; "
                      "sys.exit(ns['main']())")
            result = subprocess.run([sys.executable, "-c", runner, str(WORKER), *args], input=audio,
                                    capture_output=True, timeout=10, env=env)
            return result, [json.loads(line) for line in result.stdout.decode("utf-8").splitlines()]

    @staticmethod
    def frame(language):
        header = json.dumps({"samples": 2, "language": language}).encode() + b"\n"
        return header + struct.pack("<2f", 0.0, 0.25)

    def test_two_languages_and_native_noise_stays_off_protocol(self):
        result, messages = self.run_worker(self.frame("<|fr|>") + self.frame("<|en|>"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual([msg['stage'] for msg in messages if 'stage' in msg],
                         ['importing', 'checking_driver', 'detecting', 'compiling'])
        messages = [msg for msg in messages if 'stage' not in msg]
        self.assertEqual(messages, [{"ready": True, "device": "NPU"},
                                    {"ok": True, "text": "<|fr|>"},
                                    {"ok": True, "text": "<|en|>"}])
        self.assertIn(b"native provider startup noise", result.stderr)

    def test_no_npu_fails_without_fallback(self):
        result, messages = self.run_worker(devices="['CPU', 'GPU']")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(messages[-1]["ready"])
        self.assertIn("NPU is not visible", messages[-1]["error"])
        self.assertNotIn('compiling', [msg.get('stage') for msg in messages])
        self.assertIn(b'Traceback', result.stderr)

    def test_partial_frame_exits_with_explicit_error(self):
        result, messages = self.run_worker(b'{"samples": 4}\n\x00')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(messages[-1], {"ok": False, "error": "truncated PCM frame"})

    def test_probe_does_not_require_npu(self):
        result, messages = self.run_worker(devices="['CPU']", probe=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(messages[0]["devices"], ["CPU"])


if __name__ == "__main__":
    unittest.main()
