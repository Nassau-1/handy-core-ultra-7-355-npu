# Architecture

Handy retains Tauri/Rust, React, microphone/VAD capture, shortcuts and output handling.
`ModelManager` registers a local, bundled `OpenVinoNpu` model on Windows x64.
`TranscriptionManager` routes that model directly to `windows_npu.rs`; conventional
models keep their original engines. No conventional model must be downloaded first.

The Rust controller owns a persistent private Python executable, communicating
through JSON headers and binary 16 kHz float32 PCM. A reader thread and bounded
receive deadlines cover cold compilation (20 minutes) and inference (120 seconds).
Failure drops/kills the worker; a subsequent model load creates a fresh process.
The explicit device is `NPU`; device errors reach Handy's existing error flow.

Loading emits stage events and a queryable status snapshot for the UI. Native
stderr is drained continuously into bounded application diagnostics. Cancellation
uses a separate atomic token so it never waits for the busy worker mutex; the
response loop checks it at most every 100 ms and drops the child on cancellation.
Progress events do not extend the total initialization deadline. Windows driver
metadata is checked before compilation for Intel's known Series 3 incompatibility.

The worker runs `WhisperPipeline` with a per-user `CACHE_DIR` and receives language
on each call. No translation/streaming is advertised. Custom words are corrected
after transcription. Upstream repeated-state and long-audio behavior still requires
hardware acceptance; bundling is not proof of NPU correctness.

Program Files: application plus `resources/npu/{model,worker,inventory.json}`.
LocalAppData: version/model-specific compilation cache. Roaming app data: upstream
settings/history. No runtime secrets or target tenant identifiers are packaged.

Build uses a pinned model revision and content digest manifest, fixed OpenVINO
2026.2.1 packages and a frozen private Python distribution. Runtime imports are
smoke-tested before installer creation. MSI/EXE and `.intunewin` are build artifacts,
not Git source. App-local native dependencies follow upstream's build procedure.
