---
license: openmdw-1.1
library_name: openvino
language:
  - fr
  - en
pipeline_tag: automatic-speech-recognition
tags:
  - openvino
  - intel-npu
  - speech-recognition
---

# Nemotron 3.5 ASR Streaming 0.6B — Intel NPU conversion

This is a conversion of pretrained NVIDIA weights, with no fine-tuning and no
financial-domain training. It is not an official NVIDIA or Intel release.

Source: [NVIDIA model](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b),
revision `ea30d66debe3740a08b573244286791d423d6b3e`.
Weight SHA256: `9eebdd6590289cb3030f310858f3df93256600a800a3e8200c5993d5f967e174`.
Retain the full OpenMDW-1.1 license and original model card/notices in any upload.
The export and NumPy frontend follow Apache-2.0 Transformers 5.13.0.

## Format and execution

Five static OpenVINO graphs: first/continuing subsampler, streaming encoder,
RNNT predictor and joint. The source export saves FP32 weights; this is not an
INT8 quantization. The graph's attention, convolution and recurrent states are
explicit and persist across fragments within a request, then reset between
requests. Device compilation and any execution precision choices are handled
by OpenVINO and the Intel NPU plugin.

Requires the custom [runtime and export code](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/tree/51fa5a29575a4fe06ccbf88200d46fec0a8e01e3/experiments/nemotron_npu).
This is not a standard `AutoModel` or Optimum checkpoint. Do not upload compiled
NPU blobs, Windows binaries, test recordings, user caches or private logs as model
weights. Publish the portable IR, tokenizer/constants, inventory, licenses and
pinned source/provenance only.

`runtime.py --artifact ARTIFACT --model TOKENIZER --cache CACHE` accepts mono
16 kHz signed little-endian PCM16 on stdin until EOF and emits final UTF-8 text.
The Handy worker uses a framed float32 protocol. All five neural graphs run on
NPU; audio preparation, token handling and application logic use CPU. No GPU or
CPU fallback is silently selected. This is record-then-insert, not live captions.

## Validation and limitations

Validated pilot: Intel Core Ultra 7 355, Windows 11 25H2, Intel NPU driver
32.0.100.5540, OpenVINO 2026.2.1. French, English and mixed speech were tested.
Maximum request: 600 seconds. Longer input is rejected without silent truncation.
Original pilot measurements: about 40 seconds for cold preparation, 0.5 seconds
for cached model compilation/load (before the managed driver's preflight), and
about 10–11 seconds to process a synthetic ten-minute recording. These are
single-machine observations, not general accuracy or performance benchmarks.

Short synthetic fixtures matched reference tokens. The long fixture matched
words with a small punctuation/case difference; see the repository's validation
policy and reports. No representative financial-domain WER has been established.
The financial glossary belongs to Handy post-processing, not these model weights.
The FP32 export was revalidated on 2026-11-02: French, English, mixed and 39.8-second fixtures matched reference tokens. The 600-second fixture matched all 1,239 words; the largest group-relative L2 difference was 2.3724%, global L2 0.5691%. The frozen worker processed it in 10.0 seconds. Managed driver preflight adds about three seconds at worker startup. This is a functional synthetic test, not a representative accuracy benchmark.
