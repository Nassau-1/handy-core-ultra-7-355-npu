# Handy for Core Ultra 7 355 NPU — Preview 1

Windows x64 preview with an explicit **Whisper Turbo INT8 · Intel NPU** model.

- Bundles the official OpenVINO Whisper large-v3-turbo INT8 export and a private OpenVINO 2026.2.1 runtime; no Python installation or model download required.
- NPU execution is explicit and errors never silently fall back to CPU/GPU. Other Handy models remain separately available.
- Per-user compilation cache, bounded worker startup/inference, French and automatic language selection.
- Separate application identity; upstream self-update disabled for managed distribution.
- MSI/EXE installers and Intune Win32 package with installation, detection and CPU/OS requirement scripts.

## Installation

Use the x64 MSI or setup EXE. For Intune, use Install.intunewin and the matching metadata/detection/requirements from this release. See [operations](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/blob/codex/core-ultra-355-npu/docs/operations.md).

Select **Whisper Turbo INT8 · Intel NPU** in Handy. First model initialization may take up to 20 minutes. A compatible Intel NPU driver and Microsoft Edge WebView2 are prerequisites.

## Limits

This preview is unsigned. Real Core Ultra 7 355 execution, accuracy, cold/warm latency and repeated/long-audio behavior have **not** been tested because the target device is unavailable. No Microsoft Store certification, Intel endorsement or performance guarantee. Turbo translation and live streaming are not supported here. Do not weaken endpoint security policies to install it.

Windows CI verifies compilation, protocol tests, installer contents and startup, silent machine installation, model discovery, runtime loading, explicit no-NPU failure, payload hashes and uninstallation. This does not validate NPU inference or target-device policies.
