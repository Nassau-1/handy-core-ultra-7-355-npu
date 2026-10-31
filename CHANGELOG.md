# Changelog

## 2026-10-31 — Unreleased, validation in progress

- Preserve NPU worker diagnostics and display loading stages and elapsed time.
- Cancel initialization through an independent signal and terminate the worker on cancellation.
- Detect the known Core Ultra Series 3 / OpenVINO 2026.2–2026.4 driver incompatibility before compilation.
- Hide unmeasured NPU catalog ratings and label other ratings as estimates.
- Validate the loading fix in Windows CI and on the pilot: progress, elapsed time and real worker cancellation.
- Add a pinned Nemotron 3.5 ASR NPU prototype, lightweight PCM runtime and optional distinct local pilot model; application integration validation remains pending.
- Verify explicit NPU execution and reference-token parity on synthetic French, English, mixed and 24-second speech fixtures.

## 2026-10-30 — 0.10.0 preview

- Forked Handy through Bbrizly's Windows NPU branch d05dce78d878b59733c4dfc6528484eb05436790.
- Added a separate bundled Turbo INT8 NPU model with explicit backend and errors.
- Added OpenVINO cache, 20-minute initialization allowance and worker cleanup on error.
- Bundled Python/OpenVINO and an immutable, hash-verified Intel model export.
- Added distinct Windows identity, managed updates and Intune packaging/requirements.
- Published Preview 1 after Windows compilation, installed-model/runtime checks and silent installation/removal validation.
- Uploaded the verified Intune package and confirmed optional All Users catalog availability.
- Target-hardware performance and standard-user tenant delivery acceptance remain outstanding.
