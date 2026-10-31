# Remaining work

- [x] Install Intel NPU driver 32.0.100.5540 and reboot the pilot (2026-10-31); NPU enumerates and tiny arithmetic inference succeeds.
- [x] Validate loading changes with 14 Python tests, frontend lint and TypeScript/Vite build.
- [x] Validate Rust cancellation tests/clippy and package smoke checks in Windows CI; extract and run the test build locally.
- [x] Verify progress, elapsed time, actual cancellation and previous-model restoration in the packaged UI.
- [ ] Verify unexpected-error retention in the packaged UI and install the final pilot build.
- [x] Validate Turbo Q8 CPU/GPU transcription; user confirms microphone, Ctrl+Space and Notepad insertion (2026-10-31).
- [ ] Investigate slow Whisper compilation with the driver compiler versus bundled compiler, with bounded CPU use; pilot test stopped after 1083 s due to fan noise, not a successful NPU load.
- [x] Implement pinned Nemotron reference export and PCM runtime; all three neural graphs execute on NPU with exact tokens on four synthetic fixtures.
- [ ] Build and verify the separate Nemotron NPU model in Handy, including its 40-second request limit and microphone/paste flow.

- [x] Complete and record CI compilation/installation verification and publish Preview 1.
- [ ] Validate real Core Ultra 7 355: cold and warm load, repeated FR/EN, >30s audio.
- [ ] Confirm unsigned preview acceptance under target App Control audit policy.
- [x] Import verified package into Intune and verify optional All Users availability.
- [ ] Test Company Portal install as standard user, upgrade and removal on the pilot.
- [ ] Evaluate OpenVINO upgrades against upstream recurrent-state/long-audio issues.
- [ ] Add release signing when a signing identity is available.
- [ ] Evaluate live streaming only after batch transcription is validated.
- [ ] Register Course Impact dispatch separately if this project is connected to the Wiki.
