# NPU loading reliability and multilingual validation

Date: 2026-10-31. Status: in progress.

## Objective and scope

Make the installed Core Ultra 7 355 usable for local French, English and mixed-language dictation. First update the known-incompatible Intel NPU driver and retest the unchanged 2026.2.1 runtime. Then improve worker diagnostics, progress and cancellation in `windows_npu.rs`, `windows_npu_worker.py` and the model selection UI. Compare suitable multilingual models using measured cold/warm loading and transcription evidence, not the catalog's illustrative scores.

## Constraints and non-goals

- Explicit NPU selection must never silently fall back to CPU/GPU.
- CPU/GPU validation is separate and labeled; audio remains local.
- No automatic reboot or shared Intune rollout. Preserve the installed application for rollback; use a separate test build where possible.
- Do not claim a best model or code-switching accuracy without representative evidence. Synthetic fixtures validate execution, not the user's real-world accuracy.
- Retain a total load deadline; progress messages must not reset it.

## Plan and verification

1. Verify the official driver signature/hash, install without automatic reboot, inspect the actual driver version, and probe the original runtime.
2. Capture native diagnostics, emit stage events, reject known incompatible driver combinations before compilation, and implement cancellation independently of the busy worker mutex.
3. Show loading stages/elapsed time and cancellation in the existing model UI; explain that catalog ratings are estimates and NPU scores are unmeasured.
4. Test protocol errors, compatibility boundaries, progress, timeout and cancellation. Run frontend typecheck/lint/build and Rust checks where the Windows build environment permits.
5. Measure the existing Turbo INT8 model cold and warm. Test CPU/GPU and multilingual audio separately. Evaluate larger or alternate exports only with a supported NPU path and available memory.
6. Record exact results, remaining hardware/UI checks and the chosen model tradeoff in verification docs.

## Risks and containment

Driver elevation or a reboot may require the user's intervention. Compilation may consume significant CPU/RAM. Stop test workers at bounded deadlines and retain their diagnostics. Cancellation must not let an old load publish readiness or terminate a subsequent load. Keep package versions coherent; do not change the runtime during the initial driver comparison. Changes remain on an isolated branch until verified.
