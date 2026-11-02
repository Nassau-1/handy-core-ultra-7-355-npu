# Managed NPU distribution validation — 2026-11-02

Status: model publication verified; Windows package acceptance and tenant update
remain pending. Do not interpret publication as an Intune rollout.

## Model and hardware

Pilot: Intel Core Ultra 7 355, Windows 11 25H2, Intel NPU driver
32.0.100.5540 and OpenVINO 2026.2.1. The upstream NVIDIA source revision is
`ea30d66debe3740a08b573244286791d423d6b3e`. Five static graphs execute on NPU;
CPU handles audio preparation, token selection and application control. There is
no automatic CPU/GPU neural fallback. Output is inserted after recording stops.

The FP32 production export matched reference tokens on French, English, mixed
speech and a 39.8-second synthetic fixture, including repeated requests. A
600-second synthetic fixture matched all 1,239 words, with a small punctuation
difference. Global relative L2 was 0.5691%; the largest group difference was
2.3724%. This is functional regression evidence, not a representative WER study.

The frozen production worker advertised 9,600,000 samples (600 seconds at 16 kHz)
and explicit NPU execution. Warm startup including driver preflight took 3.236 s.
The 600-second request took 10.017 s wall time and 3.359 s aggregate CPU time.
Short synthetic financial fixtures took roughly 0.26–0.33 s when warm. These are
single-machine measurements, not guarantees for every dictation.

## Publication and download contract

The owner approved public hosting at
[Nassau-1/nemotron-3.5-asr-streaming-0.6b-intel-npu](https://huggingface.co/Nassau-1/nemotron-3.5-asr-streaming-0.6b-intel-npu).
The app pins revision `8b2bb626cd2ba53c6de2f2c41f1ec241d40017e5` and 19 files
totalling 2,573,528,474 bytes. Anonymous access was verified: sizes match, LFS
SHA256 values match, and non-LFS files were downloaded and hashed independently.
An anonymous HTTP range request returned 206 and bytes matching the local
validated FP32 encoder, confirming the server supports partial retrieval.
The model repository additionally carries its model card and file inventory.

Weights retain FP32 storage. An exploratory smaller export was not selected or
published. The Windows installer contains the inference engine; the approved
weights are downloaded by Handy. No user audio, settings, compiled NPU cache,
private logs or financial glossary were uploaded to the model repository.

The source is a conversion of pretrained NVIDIA weights, with no fine-tuning.
The model card retains the upstream revision, OpenMDW-1.1 license and original
notices, plus the Apache-2.0 Transformers notice for implementation provenance.

## Financial vocabulary

The app includes 167 shared FR/EN terms, separate from personal custom words.
Explicit aliases correct observed outputs such as `EBITTDA`, `bitda`, `nopa`
and `Nopit`. Exact Unicode word boundaries, ambiguous ordinary words, amounts,
punctuation, long input, idempotence and personal spelling priority have unit
tests. Entries without aliases are reference vocabulary only.

The glossary is conservative post-processing, not decoder bias or new training.
It cannot recover a word omitted by ASR; one synthetic English fixture omitted
CAPEX. No representative financial-domain accuracy score is claimed.

## Checks and deployment boundary

Local frontend lint and TypeScript/Vite build passed. Sixteen packaging/protocol
tests and fourteen streaming-runtime tests passed. The runtime-only frozen bundle
imports successfully and enumerates CPU, GPU and NPU on the pilot.

[Windows acceptance run](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/actions/runs/41428029154)
built commit `c3fb18036120f08a1d44ac2beb22dde96bd8e04b` and passed frontend checks,
native NPU/policy/finance/download tests, clippy, package contents, silent machine
installation/detection/runtime hashes and uninstall. Final pilot acceptance
and a follow-up build containing the upgrade download screen remain pending.

The owner requested correction of the 18 development commits' Git identity and
approved rewriting the development branch. They now use Nassau-1 and its GitHub
noreply identity. Trees, messages and dates were preserved; the default branch
was unchanged. The original acceptance commit maps to
`4938254` in the corrected history. Existing CI run links retain their original
commit IDs as historical evidence. Hugging Face's current model card links to
the identical runtime source in the corrected history.

The inspected MCI Intune app still serves Whisper Preview 0.10.0. GitHub Actions
does not publish to Intune automatically. Preserve its optional All Users
assignment and avoid forced reboot. Retired pilot payloads are retained until
the replacement passes installed NPU validation.
