# Changelog

## 2026-11-02 — 0.11.0 managed distribution (validation in progress)

- Bundle the pinned ten-minute Nemotron export and standalone NPU runtime in the installer.
- Enforce an owner-controlled model allowlist in native APIs and remove catalog/import controls.
- Add a shared FR/EN financial glossary with conservative aliases, preserved amounts and separate personal vocabulary.
- Package signed Intel NPU driver 32.0.100.5540 with version/hash checks, no downgrade or forced reboot, and a post-update reboot gate before compilation.
- Preserve optional Company Portal availability. Publishing a GitHub build alone does not update Intune.

## 2026-10-31 — Ten-minute NPU runtime

- Add a separate cache-aware Nemotron model with bounded attention, convolution and recurrent decoder state across audio fragments; support up to 600 seconds and reject excess input.
- Keep all five neural graphs on NPU, lightweight audio preparation on CPU and the existing record-then-insert interaction.
- Validate complete synthetic ten-minute audio, state reset, frozen PCM protocols and installed payload equivalence; measure about 10–11 seconds of processing and 0.51-second cached startup.
- Document the long-reference punctuation difference and explicit lexical/numerical acceptance criteria; preserve the accepted 40-second payload.
- Pass Windows build, Rust/clippy, package and installer checks; verify full ten-minute transcription and oversize rejection in the native executable.
- Install the permanent local upgrade after a user-approved elevation retry; verify the Program Files binary, Start menu target, NPU transcription and retained ten-minute model/Auto language/Ctrl+Space settings. No reboot or shared rollout.

## 2026-10-31 — Local pilot validated

- Preserve NPU worker diagnostics and display loading stages and elapsed time.
- Cancel initialization through an independent signal and terminate the worker on cancellation.
- Detect the known Core Ultra Series 3 / OpenVINO 2026.2–2026.4 driver incompatibility before compilation.
- Hide unmeasured NPU catalog ratings and label other ratings as estimates.
- Validate the loading fix in Windows CI and on the pilot: progress, elapsed time and real worker cancellation.
- Add a pinned Nemotron 3.5 ASR NPU prototype, lightweight PCM runtime and optional distinct local pilot model; native integration and installer checks pass.
- Verify explicit NPU execution and reference-token parity on synthetic French, English, mixed, 24-second and 39-second speech fixtures.
- Install the validated build on the pilot; preserve Auto language and Ctrl+Space. User confirms dictation works without a fan surge. The current model supports 40-second dictations; no shared rollout was performed.

## 2026-10-30 — 0.10.0 preview

- Forked Handy through Bbrizly's Windows NPU branch d05dce78d878b59733c4dfc6528484eb05436790.
- Added a separate bundled Turbo INT8 NPU model with explicit backend and errors.
- Added OpenVINO cache, 20-minute initialization allowance and worker cleanup on error.
- Bundled Python/OpenVINO and an immutable, hash-verified Intel model export.
- Added distinct Windows identity, managed updates and Intune packaging/requirements.
- Published Preview 1 after Windows compilation, installed-model/runtime checks and silent installation/removal validation.
- Uploaded the verified Intune package and confirmed optional All Users catalog availability.
- Target-hardware performance and standard-user tenant delivery acceptance remain outstanding.
