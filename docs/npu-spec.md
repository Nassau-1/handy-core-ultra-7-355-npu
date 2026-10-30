# Core Ultra 7 355 NPU — implementation specification

Date: 2026-10-30. Status: implementation in progress.

Objective: fork Handy with a first-class, bundled Whisper large-v3-turbo INT8
OpenVINO NPU model and produce a Windows x64 installer suitable for Intune's
Company Portal. Target hardware: Intel Core Ultra 7 355 / Panther Lake.

Non-goals: public Microsoft Store submission, driver installation, automatic
deployment to endpoints, training, promised latency without target hardware.

Surfaces: model registry, transcription manager, Python worker, Windows packaging,
CI, Intune install/detection/requirements and documentation. Preserve upstream
licenses and source history. Use a separate application identifier.

Constraints: standard-user execution; application/model/runtime installed into
protected Program Files; cache in per-user LocalAppData. No external Python,
model download or environment variables required on the endpoint. The NPU model
is explicit in the selector and never silently falls back to CPU/GPU. Other
Handy models remain independently available. No translation/streaming claims
for Turbo. French and automatic language detection supported.

Risks: cold compilation can take more than 11 minutes; allow 20 minutes on load,
bound inference to 120 seconds, kill failed workers. Upstream OpenVINO issues
may affect repeated/long audio. NPU drivers and unsigned application acceptance
must be validated on the pilot. Keep the installer experimental until then.

Plan:

1. Add explicit bundled OpenVINO model and reliable worker lifecycle/cache.
2. Bundle pinned Python/OpenVINO runtime and immutable model revision in CI.
3. Build installers and Intune package with silent install/uninstall,
   version detection and CPU/OS requirements. Disable upstream self-updates.
4. Run protocol/failure tests, frontend checks, Rust compilation/lint and
   Windows installation smoke checks on CI; publish source and build evidence.
5. Record target-hardware acceptance steps, exact limits and rollback.

Verification: validate French request parameters, malformed PCM, timeout cleanup,
no-NPU errors, package integrity, installation/removal and resource resolution.
Actual NPU execution, cold/warm latency, >30-second completeness and repeated
FR/EN calls require MCI-001; no remote access is available in this session.

Containment: no tenant-wide or mandatory assignment. Separate application ID;
uninstall only this app, retain user history/cache by default. Intune packaging
does not require weakening Defender, App Control or Windows signing policies.
