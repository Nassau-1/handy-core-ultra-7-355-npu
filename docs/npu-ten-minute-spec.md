# Ten-minute NPU dictation

Date: 2026-10-31. Status: implementation and validation in progress.

## Objective and scope

Support complete French, English and mixed-language dictations up to 600 seconds
on the existing Intel NPU. Preserve attention K/V, convolution and RNNT decoder
state between bounded fragments. Reset all state between independent dictations.
Keep explicit NPU placement and the working 40-second pilot available until the
replacement is validated. Reject audio beyond the limit without truncation.

The first integration retains Handy's current record-then-insert interaction.
The engine consumes fragments with streaming state after recording stops; live
text preview and concurrent microphone/inference scheduling are outside this
change. Do not claim that internal streaming means live typing during capture.

## Implementation plan

1. Export the pinned Transformers 5.13.0 reference with explicit bounded cache
   tensors. Separate the small first/continuation subsamplers from the shared
   encoder body, avoiding duplicate full-model weights. Group aligned native
   attention chunks for throughput without changing their lookahead.
2. Compare exported torch wrappers to unmodified cached reference calls across
   warm-up, full-cache rollover and final fragments; then verify NPU tensors and
   transcripts on French, English, mixed speech and boundary-sensitive inputs.
3. Add bounded frontend fragments, persistent RNNT state, a 600-second protocol
   limit, and progress messages that do not extend the total request deadline.
   Integrate a distinct artifact/cache identity in Handy and update duration text.
4. Exercise actual 600-second audio, oversize rejection, repeated requests,
   silence, reset, and the frozen worker/native app. Measure wall/CPU time and
   memory. Build, test and install only after parity and long-audio checks pass.

## Risks and containment

Chunk alignment, initial convolution padding, relative positions and cache
rollover can silently drop or duplicate words. Intermediate-tensor comparisons
must cover these cases, alongside reference text. NPU numeric drift may accumulate
through caches; measure per-chunk errors and long-form output. Compilation and
ten-minute inference have bounded watchdogs. Preserve the installed pilot payload
for rollback, and never replace a running worker's files.

No shared Intune rollout, new model weights, automatic CPU/GPU fallback or
unrelated settings changes are included.
