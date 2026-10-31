# Architecture-specific ASR experiment

Date: 2026-10-31. Status: local pilot implemented, installed and validated; no shared release.

## User objective

Apply the reference-implementation-to-optimized-runtime approach discussed in
[Hacker News](https://news.ycombinator.com/item?id=50282593): local PCM input,
UTF-8 text output, genuine execution on the Core Ultra 7 355 NPU, and measured
French, English and mixed-language quality. Sustained dictation should keep CPU
load and fan noise low. The user accepts ventilation during one-time preparation.

## Candidate and boundaries

Investigate NVIDIA Nemotron 3.5 ASR Streaming 0.6B, using its official Transformers
implementation as the numerical reference. It is distinct from the newly
announced 30B-A4B Transcribe model for recorded audio. The latter's memory footprint
and hybrid MoE architecture require a separate feasibility study; do not silently
substitute one model's claims or weights for the other.

Keep the working Handy GPU configuration intact. Prototype export, inference and
benchmark commands under `experiments/nemotron_npu/` before connecting a backend
to the GUI. Pin model/code revisions and verify numerical output before optimizing.

## Implementation and acceptance

1. Inspect the reference encoder, recurrent decoder, tokenizer and feature
   extraction. Separate static compute graphs from token/control loops.
2. Export a bounded-shape acoustic encoder to OpenVINO and explicitly compile it
   for NPU. Preserve streaming state or clearly label a batch-only first stage.
3. Implement the reference RNNT decode and language conditioning. Document every
   component that runs on CPU; no implicit device fallback.
4. Provide a CLI with documented PCM framing and UTF-8 stdout, diagnostics on
   stderr, persistent model/cache reuse and bounded failure/cancellation.
5. Compare intermediate tensors and transcripts to the reference on identical
   inputs. Then measure cold/warm load, time to first text, real-time factor,
   per-utterance CPU time, memory and FR/EN/code-switching errors.
6. Integrate only a verified candidate; retain errors and the independent GPU
   baseline. Do not claim quiet operation from wall-clock speed alone.

Memory bandwidth is a useful profiling dimension when a measured kernel is
memory-bound. An arbitrary 80% of peak memory bandwidth is not an ASR correctness
or end-to-end latency criterion. Record measured bottlenecks and use appropriate
metrics for the encoder, decoder and host/NPU transfers separately.

## Risks

Unsupported NPU operators, fixed-shape/cache constraints and RNNT control flow
may limit offload. Rewriting a Python reference alone does not establish hardware
support or performance. Preserve failing graphs/logs, test smaller graph portions,
and distinguish an experimental hybrid pipeline from complete NPU execution.
