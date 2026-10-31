# Remaining work

- [x] Install Intel NPU driver 32.0.100.5540 and reboot the pilot (2026-10-31); NPU enumerates and tiny arithmetic inference succeeds.
- [x] Validate loading changes with 14 Python tests, frontend lint and TypeScript/Vite build.
- [x] Validate Rust cancellation tests/clippy and package smoke checks in Windows CI; extract and run the test build locally.
- [x] Verify progress, elapsed time, actual cancellation and previous-model restoration in the packaged UI.
- [x] Verify unexpected-error retention in the packaged UI.
- [ ] Install the final pilot build and validate the Nemotron microphone/paste flow with the user.
- [x] Validate Turbo Q8 CPU/GPU transcription; user confirms microphone, Ctrl+Space and Notepad insertion (2026-10-31).
- [x] Compare bounded Whisper compilation attempts: plugin trial interrupted after 1083 s; single-thread driver compiler trial stopped at 180 s; neither reached readiness. Root cause remains unresolved.
- [x] Implement pinned Nemotron reference export and PCM runtime; all three neural graphs execute on NPU with exact tokens on four synthetic fixtures.
- [x] Build and verify the separate Nemotron NPU model in Handy on FR/EN/mixed/24-second fixtures; verify oversized requests fail without truncation.

- [x] Complete and record CI compilation/installation verification and publish Preview 1.
- [ ] Validate real Core Ultra 7 355: cold and warm load, repeated FR/EN, >30s audio.
- [ ] Confirm unsigned preview acceptance under target App Control audit policy.
- [x] Import verified package into Intune and verify optional All Users availability.
- [ ] Test Company Portal install as standard user, upgrade and removal on the pilot.
- [ ] Evaluate OpenVINO upgrades against upstream recurrent-state/long-audio issues.
- [ ] Add release signing when a signing identity is available.
- [ ] Evaluate live streaming only after batch transcription is validated.
- [ ] Register Course Impact dispatch separately if this project is connected to the Wiki.
