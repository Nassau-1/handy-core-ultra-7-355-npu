# Core Ultra 7 355 pilot acceptance

No access to the target machine was available during implementation.

- Install through Company Portal as a standard user; verify Program Files placement,
  both runtimes, offline model availability, and independent upstream Handy data.
- Select the NPU model and French. Record NPU driver/Windows versions and logs.
- Time cold initialization; confirm NPU in Task Manager and `device=NPU` in logs.
  CPU activity for audio/tokenization is normal and does not disprove NPU inference.
- Time subsequent loads and release-to-paste for 5s/15s/60s dictations separately.
- Use reference French text with names/numbers; inspect all words and punctuation.
- Alternate FR/EN/FR on the same worker in Auto, then fixed French. Confirm no stale
  language state. Test repeated 60s and 120s inputs and verify the ending is present.
- Disconnect network and repeat; no network is required for the bundled NPU path.
- Verify explicit errors when NPU is unavailable; do not accept silent CPU fallback.
- Verify custom-word correction, microphone switching, cancel/retry and sleep/resume.
- Check cache creation, idle unloading/reload, upgrade and uninstall with standard
  user and enterprise security controls intact.

Do not label the preview validated or assign broadly until the above has passed.
