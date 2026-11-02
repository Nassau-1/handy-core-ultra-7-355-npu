# Handy for Core Ultra 7 355's NPU

A Windows x64 fork of [Handy](https://github.com/cjpais/Handy) with an explicit
**Nemotron 3.5 · Intel NPU · 10 min** model, a bundled OpenVINO runtime, and an
Intune Company Portal package. Based on [Bbrizly's Windows NPU prototype](https://github.com/Bbrizly/Handy-NPU-support/tree/feature/windows-intel-npu-openvino).

## Status — 2026-11-02

Managed **0.11.0** is published in the existing optional MCI Intune application.
It downloads the approved FP32 model from Hugging Face, enforces an embedded
model allowlist, includes a shared FR/EN financial glossary and installs the
signed Intel NPU driver when needed. Personal vocabulary and history are retained.
See the [distribution specification](docs/managed-npu-distribution-spec.md),
[operations guide](docs/operations.md) and [validation record](docs/verification-2026-11-02.md).

The final Windows package passed build, native tests, installation and removal
checks. On the Core Ultra 7 355, its 600-second synthetic fixture transcribed in
11.563 seconds with all 1,239 reference words and the ending preserved; cached
model loading took 3.616 seconds. These are single-machine functional tests,
not an accuracy or latency guarantee. Company Portal installation and the
permanent pilot upgrade also passed; the installed ten-minute test took 14.261
seconds, with all reference words and the ending preserved.

The old [Whisper Preview 1 release](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/releases/tag/v0.10.0-npu-preview.1)
is historical; its NPU loading problem remains unresolved. No Microsoft Store
certification or Intel endorsement is implied.

## Use

Install **Handy Core Ultra 355 NPU** from Company Portal on an eligible Core Ultra
7 355 with Windows 11 25H2 or later and WebView2. Restart Windows if the Intel
driver was updated. Open Handy and download the single approved model (about
2.6 GB) from [Hugging Face](https://huggingface.co/Nassau-1/nemotron-3.5-asr-streaming-0.6b-intel-npu).
The download can be cancelled and resumed; all files are hash-verified. The first
load prepares an NPU cache, reused on later starts. Dictation then works offline.

Use the configured shortcut to start and stop dictation. French, English and mixed
speech are supported up to ten minutes. Text is inserted after recording stops.
Neural graphs run on OpenVINO `NPU`, with audio preparation and application control
on CPU. Errors are explicit; there is no automatic CPU/GPU neural fallback.

Only the model approved in the managed policy is exposed. The 167-term financial
glossary applies conservative corrections after recognition; personal custom words
remain separate and take precedence. This is not model fine-tuning or decoder bias.
Local audio history follows Handy's settings; optional cloud post-processing must
be deliberately configured by the user. The NPU worker itself has no network path.

## Distribution

- Application: **Handy Core Ultra 355 NPU**, version 0.11.0.
- Identity: `com.nassau.handy.ultra355npu`; coexists with upstream Handy.
- Windows installer is per-machine; normal use requires no administrator rights.
- Intune: [operations and catalog configuration](docs/operations.md).
- Upstream automatic updater is disabled; use Intune version replacement.
- Builds are unsigned until a signing identity is configured. Never disable
  Defender or App Control to install this preview.

## Development

Windows x64, Python 3.12, stable Rust/MSVC, Bun and Vulkan SDK are required.
See [upstream build instructions](BUILD.md). Run:

```powershell
bun install --frozen-lockfile
python -m pip install -r packaging/npu-requirements.txt
python scripts/prepare_npu.py
bun run tauri build
```

Build payloads live under ignored `build/` and `src-tauri/resources/npu/`.
No environment variables or developer tools are required on the installed target.
The [Windows workflow](.github/workflows/windows-intel-npu.yml) performs compilation,
protocol tests, runtime/package checks and Intune packaging. Hardware validation
is a separate [acceptance checklist](docs/acceptance.md).

## Project

- [Architecture](docs/architecture.md), [decision](docs/decisions/ADR-001-npu-distribution.md)
- [Specification](docs/npu-spec.md), [verification](docs/verification.md)
- [Security](SECURITY.md), [third-party notices](THIRD-PARTY-NPU.md)
- [Changelog](CHANGELOG.md), [remaining work](TODO.md)
- [Original Handy README](README.upstream.md), [MIT license](LICENSE)
