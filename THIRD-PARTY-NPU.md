# NPU distribution notices

Handy is MIT licensed; see [LICENSE](LICENSE). This fork retains Handy and
Bbrizly's Windows NPU prototype source history and notices. It is not an official
Intel, OpenVINO or Handy release.

The 0.11 managed distribution downloads an approved OpenVINO conversion of
[NVIDIA Nemotron 3.5 ASR Streaming 0.6B](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b),
revision `ea30d66debe3740a08b573244286791d423d6b3e`, under
[OpenMDW-1.1](packaging/OPENMDW-1.1.txt). The original model card and notices,
license and source hashes accompany the payload. No fine-tuning was performed.
The five graph export follows Apache-2.0 Transformers 5.13.0; its license is
included. Legacy Whisper artifacts are no longer bundled.

OpenVINO and Hugging Face Tokenizers are Apache-2.0 licensed.
NumPy uses a BSD license; Python uses the PSF license. PyInstaller is GPL with
the bootloader exception allowing distribution of non-GPL bundled programs.
The distribution retains package license/notice files under the worker's
`_internal` directory; Python's license is included alongside the worker.

No code or packaged binaries from EZSTT are incorporated. Its public manifest
and runtime pairing informed the choice, independently verified against Intel's
immutable Hugging Face revision.

The Intune wrapper includes the unmodified, Intel-signed NPU driver installer
32.0.100.5540. Intel's installer retains its license and third-party notices.
See [driver lock](packaging/intel-driver-lock.json). The model license does not
license Intel's driver. Driver installation never forces a reboot or downgrade.
