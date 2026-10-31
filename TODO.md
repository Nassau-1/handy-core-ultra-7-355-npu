# Remaining work

- [x] Install Intel NPU driver 32.0.100.5540 on the pilot (2026-10-31); reboot required before retest.
- [x] Validate loading changes with 14 Python tests, frontend lint and TypeScript/Vite build.
- [ ] Validate Rust cancellation tests/clippy and package smoke checks in Windows CI, then install the test build.
- [ ] Test cancellation and error/progress UI on the pilot after reboot.
- [ ] Validate a CPU/GPU model, microphone, shortcuts and insertion independently.

- [x] Complete and record CI compilation/installation verification and publish Preview 1.
- [ ] Validate real Core Ultra 7 355: cold and warm load, repeated FR/EN, >30s audio.
- [ ] Confirm unsigned preview acceptance under target App Control audit policy.
- [x] Import verified package into Intune and verify optional All Users availability.
- [ ] Test Company Portal install as standard user, upgrade and removal on the pilot.
- [ ] Evaluate OpenVINO upgrades against upstream recurrent-state/long-audio issues.
- [ ] Add release signing when a signing identity is available.
- [ ] Evaluate live streaming only after batch transcription is validated.
- [ ] Register Course Impact dispatch separately if this project is connected to the Wiki.
