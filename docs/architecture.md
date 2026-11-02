# Architecture

## Managed distribution (0.11.0)

The MCI build exposes only the owner-approved ten-minute Nemotron model.
`packaging/managed-policy.json` is embedded in both the Rust backend and React UI;
user settings and discovery cannot add models. The shared financial glossary is
also embedded, with personal spelling taking priority over its exact aliases.

Program Files contains Handy and `resources/npu/worker`, the frozen OpenVINO
runtime. Weights are downloaded anonymously from the public Nassau-1 Hugging Face
repository. `managed-model-lock.json` pins an immutable commit and 19 file hashes.
Downloads resume in a separate staging directory, verify SHA256, then atomically
finalize into LocalAppData `managed-models/<manifest digest>`. A completion marker
and expected sizes distinguish a ready payload from an interrupted download.

Five neural graphs execute on NPU with encoder and RNNT state carried across
fragments, then reset between dictations. The maximum request is 600 seconds;
the app records first and inserts text after stop. Audio features and token
control use CPU. There is no silent neural CPU/GPU fallback.

The Intune wrapper installs Intel's signed driver when needed and returns a
restart-required code without forcing reboot. Worker preflight rejects an old
driver or a pending same-boot driver update before compiling. Cache compilation
runs in the user's session, not SYSTEM. See
[managed distribution decision](decisions/ADR-0004-managed-npu-distribution.md),
[operations](operations.md) and [validation](verification-2026-11-02.md).

## Earlier preview and pilot implementations

The following describes the earlier 0.10 previews retained in source for history
and experiments. Their model entries are hidden by the managed build policy.

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

## Optional Nemotron NPU pilot

The optional `nemotron-35-npu-pilot` model is registered only when its complete
payload exists in LocalAppData under `nemotron-npu-pilot`. It shares Handy's
capture, cancellation, worker protocol and output handling, with a separate
worker, model artifact and compilation cache. The default Whisper payload and
GPU model remain available. See [ADR-002](decisions/ADR-002-nemotron-npu-pilot.md).

The pinned 0.6B reference is exported as three static OpenVINO graphs: encoder,
recurrent predictor and joint classifier. All three explicitly target NPU;
NumPy audio features, token selection and text decoding run on CPU. Runtime
does not import PyTorch or Transformers. The persistent worker reports actual
execution devices and its maximum sample count during initialization. Rust
rejects oversized requests before sending audio, and the worker validates the
protocol independently. The current 4,096-frame artifact supports approximately
40 seconds per utterance. Installation
and numerical validation are documented in the
[experiment README](../experiments/nemotron_npu/README.md).

The separate `nemotron-35-npu-ten-minute` model uses the
`nemotron-npu-streaming` payload and a distinct cache. Five NPU graphs split the
first/continuation subsamplers from the shared encoder, predictor and joint.
Bounded attention, convolution and predictor state carry across 64-frame groups,
then reset for the next dictation. The host computes audio features and the small
Boolean attention mask. Native four-frame attention boundaries are preserved;
unused final group padding is never decoded. Both native and worker limits are
600 seconds. Handy still records first and inserts the final result after stop.
See [ADR-003](decisions/ADR-003-cached-npu-dictation.md) for numeric acceptance and
the rejected independent-chunk approach. The 40-second payload stays intact.
