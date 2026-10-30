# Verification

Date: 2026-10-30.

## Evidence

- [Windows build and native checks](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/actions/runs/41085509166), installer source commit `d530e61e78d1e0119d887d440e513a1ecbd550a0`.
  Compilation, MSI/NSIS generation, runtime-content audits, two Rust NPU tests and
  Clippy passed. That run failed later in the initial packaging smoke harness;
  it is not represented as an entirely successful workflow.
- [Final installation, Intune packaging and publication](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/actions/runs/41091853092): **success**.
  Reuses the exact compiled installers; a source-diff guard verified that the
  application/model code still matches the build. Packaging commit `fbf56b6`.
- [Preview 1](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/releases/tag/v0.10.0-npu-preview.1)
  contains MSI, EXE, Install.intunewin, matching detection/requirement scripts,
  metadata and SHA256SUMS.txt. Release filenames use GitHub-normalized dots.

## Checks performed

- 12 Python tests: request validation and subprocess protocol, repeated French/English
  parameters, malformed PCM and explicit no-NPU errors. These use fake providers
  where needed and do not measure speech recognition quality.
- Frontend lint, TypeScript/Vite production build, changed-Rust formatting.
- Windows release compilation, two Rust validation tests and Clippy. Existing
  upstream warnings and the frontend large-chunk warning remain nonblocking.
- Frozen OpenVINO/GenAI runtime import and version probe.
- Actual silent per-machine MSI install through Windows PowerShell; Intune detection
  returns the installed 0.10.0 version.
- Installed Handy enumerates the bundled NPU model as downloaded and recommended.
- Installed worker imports successfully and returns an explicit NPU-unavailable
  error on the CPU-only runner; all bundled payload hashes match the inventory.
- Silent uninstall removes the MSI product registration.
- Locally downloaded Intune package SHA256 verified against release metadata:
  `C92F08AC56211C8BD4A182969FC6DEB576B169D8A0C930879A2FE8DBD8044858`.

The smoke harness was corrected to suppress empty COM return values, calculate
MSI SHA256 through .NET in Windows PowerShell, explicitly wait for the Windows GUI
executable, and reset the intentional no-NPU exit status after all assertions pass.

## Catalog verification

Intune reported the content upload complete and the app saved successfully on
2026-10-30. Saved properties confirm the exact commands, x64 requirement, CPU/OS
script, version-detection script, System context and optional All Users assignment.
No Required or uninstall assignment was created. Endpoint installation counts
are not used as proof of delivery; no target install was performed.

## Unverified

Actual Core Ultra 7 355 execution, NPU utilization, cold/warm latency, French
accuracy, repeated/long-audio completeness, standard-user Company Portal install,
upgrade and target App Control acceptance require the unavailable target device.
See [acceptance](acceptance.md). The release is unsigned and experimental.
Passing packaging checks is not evidence of NPU inference performance.
