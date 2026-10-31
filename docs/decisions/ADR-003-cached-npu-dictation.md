# ADR-003: Bounded streaming state for ten-minute NPU dictation

Date: 2026-10-31. Status: implemented; long-reference and packaged acceptance in progress.

The user requested dictations up to ten minutes while preserving the quiet NPU
path. Increasing the previous 4,096-frame utterance shape would expand attention
work and cold compilation. Independently transcribing short chunks would reset
context and risk missing or duplicating words at joins.

Export the pinned reference's attention K/V and convolution caches explicitly.
Separate small first/continuation subsampling graphs from one shared encoder body.
Group 16 native four-frame attention chunks into 64 encoder frames (5.12 seconds)
for throughput. The attention mask still enforces the original three-frame
lookahead and 56-frame left context; grouping does not enlarge that context.
Carry RNNT prediction/hidden/cell state across groups and reset every state for
each independent dictation. Process the last partial native chunk with padding,
without decoding the unused remainder of a throughput group.

All neural graphs target NPU explicitly. NumPy performs bounded feature extraction
and creates the small Boolean attention mask on CPU. The initial graph computed
that mask from a scalar cache length inside the model: torch and OpenVINO CPU
matched, but NPU encoder errors reached 0.96 relative L2 and transcripts diverged.
Passing the equivalent Boolean mask as an input restored reference-token parity
on the initial French/mixed tests. This is an observed workaround on the pilot,
not a claim about a diagnosed upstream compiler defect.

Use a distinct `nemotron-35-npu-ten-minute` model, per-user payload directory and
cache identity. Preserve the already accepted 40-second payload for rollback.
Advertise a 9,600,000-sample (600-second) limit and reject excess input. Keep the
current 120-second inference watchdog, subject to the measured ten-minute test.

Handy's interaction remains record-then-insert. Internal cache-aware processing
does not imply live typing during microphone capture. Live preview, background
capture/inference scheduling and shared deployment are separate changes.

See [scope and verification plan](../npu-ten-minute-spec.md) and the
[reference streaming API](https://huggingface.co/docs/transformers/model_doc/nemotron3_5_asr).
