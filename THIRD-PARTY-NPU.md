# NPU distribution notices

Handy is MIT licensed; see [LICENSE](LICENSE). This fork retains Handy and
Bbrizly's Windows NPU prototype source history and notices. It is not an official
Intel, OpenVINO or Handy release.

The bundled Whisper large-v3-turbo model is MIT licensed:
[OpenAI model](https://huggingface.co/openai/whisper-large-v3-turbo) and
[Intel's OpenVINO export](https://huggingface.co/OpenVINO/whisper-large-v3-turbo-int8-ov).
The export's README accompanies the model. Model revision and content hashes are
in [model-lock.json](packaging/model-lock.json).

OpenVINO, OpenVINO GenAI and OpenVINO Tokenizers are Apache-2.0 licensed.
NumPy uses a BSD license; Python uses the PSF license. PyInstaller is GPL with
the bootloader exception allowing distribution of non-GPL bundled programs.
The distribution retains package license/notice files under the worker's
`_internal` directory; Python's license is included alongside the worker.

No code or packaged binaries from EZSTT are incorporated. Its public manifest
and runtime pairing informed the choice, independently verified against Intel's
immutable Hugging Face revision.
