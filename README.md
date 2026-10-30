# Handy for Core Ultra 7 355's NPU

A Windows x64 fork of [Handy](https://github.com/cjpais/Handy) with an explicit
**Whisper Turbo INT8 · Intel NPU** model, a bundled OpenVINO runtime, and an
Intune Company Portal package. Based on [Bbrizly's Windows NPU prototype](https://github.com/Bbrizly/Handy-NPU-support/tree/feature/windows-intel-npu-openvino).

## Status — 2026-10-30

Experimental implementation. Build and packaging validation in progress.
**Not yet tested on a Core Ultra 7 355.** No latency or accuracy guarantee.
No Microsoft Store certification or Intel endorsement is implied.

## Use

Install the x64 MSI or setup EXE. Python and the pinned OpenVINO model are included;
there is no separate model download. In Handy's model selector, choose
**Whisper Turbo INT8 · Intel NPU**, then select French or Auto in language settings.
The first model load can take up to 20 minutes while the NPU compiles it; subsequent
loads use a per-user cache. Keep the model loaded between dictations for best latency.
A compatible Intel NPU driver and Microsoft Edge WebView2 are required.

The selected NPU model always uses OpenVINO `NPU`. If initialization or inference
fails, Handy displays an error; it never silently uses CPU/GPU. Other Handy models
can be selected separately. Turbo does not translate to English or provide live
streaming in this edition. Custom words use Handy's text correction, not a prompt.
Local audio history follows Handy's settings; optional cloud post-processing must
be deliberately configured by the user. The NPU worker itself has no network path.

## Distribution

- Application: **Handy Core Ultra 355 NPU**, version 0.10.0.
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
