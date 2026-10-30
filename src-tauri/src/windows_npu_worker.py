"""Windows x64 OpenVINO Whisper worker for Handy.

Transport: one UTF-8 JSON header line followed by N little-endian float32 PCM
samples at 16 kHz mono; one UTF-8 JSON response line. No network usage.
Requires Intel NPU + openvino/openvino-genai and an exported OpenVINO Whisper model.
"""
import json
import os
import sys


MAX_SAMPLES = 16000 * 600
PROTOCOL_OUT = None


def write_message(payload):
    writer = PROTOCOL_OUT or sys.stdout
    writer.write(json.dumps(payload, ensure_ascii=False) + "\n")
    writer.flush()


def read_exact(reader, count):
    """Read a binary PCM frame without accepting partial samples."""
    data = bytearray()
    while len(data) < count:
        block = reader.read(count - len(data))
        if not block:
            raise EOFError("truncated PCM frame")
        data.extend(block)
    return data


def process_request(pipe, reader, request):
    sample_count = request.get("samples")
    if type(sample_count) is not int or not 0 < sample_count <= MAX_SAMPLES:
        raise ValueError("invalid PCM sample count")
    pcm = read_exact(reader, sample_count * 4)
    # Array converts directly to float32 without numpy as a required dependency.
    import array
    samples = array.array("f")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    if not all(-1.01 <= x <= 1.01 for x in samples):
        raise ValueError("PCM samples must be normalized to [-1, 1]")

    if request.get("translate"):
        raise ValueError("Whisper Turbo does not support translation")
    kwargs = {"task": "transcribe", "return_timestamps": False}
    language = request.get("language")
    if language is not None:
        if (not isinstance(language, str) or len(language) != 6
                or not language.startswith("<|") or not language.endswith("|>")
                or not all("a" <= c <= "z" for c in language[2:4])):
            raise ValueError("invalid Whisper language token")
        kwargs["language"] = language

    result = pipe.generate(list(samples), **kwargs)
    text = result.texts[0] if result.texts else ""
    return {"ok": True, "text": text}


def main():
    global PROTOCOL_OUT
    # Native libraries may print to fd 1. Reserve a separate descriptor for JSON.
    PROTOCOL_OUT = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    if sys.argv[1:] == ["--probe"]:
        import openvino
        import openvino_genai
        write_message({"devices": openvino.Core().available_devices,
                       "openvino": openvino.__version__, "genai": openvino_genai.__version__})
        return 0
    if len(sys.argv) != 3:
        write_message({"ready": False, "error": "Expected model and writable cache directories"})
        return 2
    try:
        import openvino
        import openvino_genai

        # Do not silently run on CPU/GPU; a genuine Intel NPU must be present.
        devices = openvino.Core().available_devices
        if "NPU" not in devices:
            raise RuntimeError("Intel NPU is not visible to OpenVINO (available: %s)" % devices)
        os.makedirs(sys.argv[2], exist_ok=True)
        pipe = openvino_genai.WhisperPipeline(sys.argv[1], "NPU", CACHE_DIR=sys.argv[2])
        write_message({"ready": True, "device": "NPU"})
    except Exception as exc:
        write_message({"ready": False, "error": str(exc)})
        return 1

    reader = sys.stdin.buffer
    while True:
        header = reader.readline()
        if not header:
            break
        try:
            request = json.loads(header)
            write_message(process_request(pipe, reader, request))
        except Exception as exc:
            write_message({"ok": False, "error": str(exc)})
            # On a malformed binary frame, input may be desynchronized.
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
