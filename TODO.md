# Remaining work

- [x] Preserve encoder and RNNT state for ten-minute NPU dictations; validate full 600-second audio, word parity, cache restart, state reset and oversized-input rejection (2026-10-31).
- [x] Complete native package/installer CI acceptance; verify ten-minute transcription and oversize rejection in the extracted Handy build.
- [x] Complete the permanent Windows upgrade and activate the separate ten-minute model on the pilot (2026-10-31); installed NPU smoke test and retained settings verified.
- [x] Install Intel NPU driver 32.0.100.5540 and reboot the pilot (2026-10-31); NPU enumerates and tiny arithmetic inference succeeds.
- [x] Validate loading changes with 14 Python tests, frontend lint and TypeScript/Vite build.
- [x] Validate Rust cancellation tests/clippy and package smoke checks in Windows CI; extract and run the test build locally.
- [x] Verify progress, elapsed time, actual cancellation and previous-model restoration in the packaged UI.
- [x] Verify unexpected-error retention in the packaged UI.
- [x] Install the final pilot build and validate the Nemotron microphone/paste flow with the user; user reports no fan surge (2026-10-31).
- [x] Validate Turbo Q8 CPU/GPU transcription; user confirms microphone, Ctrl+Space and Notepad insertion (2026-10-31).
- [x] Compare bounded Whisper compilation attempts: plugin trial interrupted after 1083 s; single-thread driver compiler trial stopped at 180 s; neither reached readiness. Root cause remains unresolved.
- [x] Implement pinned Nemotron reference export and PCM runtime; all three neural graphs execute on NPU with exact tokens on five synthetic fixtures.
- [x] Build and verify the separate Nemotron NPU model in Handy on FR/EN/mixed/24-second fixtures; verify oversized requests fail without truncation.

- [x] Complete and record CI compilation/installation verification and publish Preview 1.
- [x] Validate Nemotron on the real Core Ultra 7 355: cold/warm load, repeated FR/EN, 39.845-second audio and user dictation. Whisper NPU remains unresolved.
- [ ] Confirm unsigned preview acceptance under target App Control audit policy.
- [x] Import verified package into Intune and verify optional All Users availability.
- [ ] Test Company Portal install as standard user, upgrade and removal on the pilot.
- [ ] Evaluate OpenVINO upgrades against upstream recurrent-state/long-audio issues.
- [ ] Add release signing when a signing identity is available.
- [ ] Evaluate live text during capture separately; the ten-minute engine currently processes fragments after recording stops.
- [ ] Register Course Impact dispatch separately if this project is connected to the Wiki.

## Managed distribution — 2026-11-02

- [x] Inspect live Intune: old Whisper Preview 0.10.0, no dependencies, optional All Users.
- [x] Implement bundled ten-minute model, native allowlist and shared financial vocabulary.
- [ ] Validate 0.11.0 Windows build, clean install, upgrade and installed NPU transcription.
- [ ] Update the existing optional Intune app with the verified package and exact detection metadata.
- [ ] Remove retired pilot payloads after successful installed replacement.
- [ ] Publish converted graphs on Hugging Face after owner specifies namespace/visibility.
