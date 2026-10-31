# Pilot verification — 2026-10-31

## Driver and NPU

The Core Ultra 7 355 pilot was upgraded from Intel NPU 32.0.100.4509 to
32.0.100.5540 and rebooted. The unchanged installed worker reports CPU, GPU and
NPU with OpenVINO `2026.2.1-21919-ede283a88e3-releases/2026/2` and GenAI
`2026.2.1.0-3123-7dea0459b2a`.

A load of the bundled Turbo INT8 export with a separate empty cache was stopped
after **1083 seconds** because of fan noise, without a ready response or cache
artifact. This is an interrupted test, not a measured timeout or proof that
compilation would never finish. No warm-load result exists. The process used
about 581 CPU seconds and was explicitly terminated; the application processes
were idle in a subsequent two-second CPU sample.

A separate tiny arithmetic model executed correctly on the NPU with both the
OpenVINO compiler (1.856 s compile + inference) and driver compiler (0.663 s).
That check used the local Python environment, not the frozen Handy worker; it
proves basic NPU operation, not Whisper readiness or identical GenAI packaging.

Intel documents two relevant, distinct issues:

- [CVS-233822](https://docs.openvino.ai/2026/about-openvino/release-notes-openvino.html):
  specific older Series 3 drivers with OpenVINO 2026.2–2026.4; 5540+ recommended.
- [OpenVINO issue 35810](https://github.com/openvinotoolkit/openvino/issues/35810):
  prolonged Whisper Turbo compilation on Panther Lake. Similarity to this pilot
  is a diagnostic hypothesis, not proof of the same root cause.

The [2026.2 NPU plugin documentation](https://github.com/openvinotoolkit/openvino/blob/releases/2026/2/src/plugins/intel_npu/README.md)
explains that `PREFER_PLUGIN` selects the compiler bundled with OpenVINO by
default. Updating the driver therefore does not necessarily replace the compiler
used by Whisper. A separate `NPU_COMPILER_TYPE=DRIVER` trial, limited to one
compiler thread and 180 seconds, did not reach readiness or create a cache.
That bounded observation does not establish an infinite hang. No such change
is enabled in the shipped application.

## Independent CPU/GPU checks

Installed and verified the catalog-pinned `whisper-large-v3-turbo-Q8_0.gguf`:
revision `5eaf945c7978e564bae5b28a5b1639dd93c2bfb1`, 886381760 bytes, SHA-256
`b2e30cc286bc9f3aba4db9099fc7403543497c05ce7100d0d83091ddfd25a183`.

The installed Handy CLI was explicitly bound to GPU index 0 (`Vulkan0`) and CPU
index 1 (`CPU`). All six cases completed with exit code 0, two transcriptions per
case. Three local synthetic fixtures exercise French, English and mixed speech.

| Fixture     | Audio (s) | GPU load (s) | GPU best inference (s) | CPU load (s) | CPU best inference (s) |
| ----------- | --------: | -----------: | ---------------------: | -----------: | ---------------------: |
| French      |     7.160 |        1.842 |                  2.049 |        1.897 |                 10.525 |
| English     |     6.315 |        1.440 |                  1.980 |        1.597 |                 12.286 |
| Mixed FR/EN |     9.895 |        1.491 |                  2.078 |        1.724 |                 15.453 |

These are smoke measurements, not controlled performance/quality benchmarks:
NPU compilation was running concurrently, the GPU's first French inference took
4.174 s, samples are synthetic, and timings include neither microphone capture
nor paste. No energy consumption or acoustic measurement was taken.

The GUI loaded the same model on Intel Graphics in 1.608 s with automatic
language detection. The user confirmed dictation into Notepad works using the
Ctrl+Space shortcut. This validates the user-observed microphone/shortcut/paste
flow. It does not establish a corpus-level word error rate or a best model.

## Loading correction validation

- Python protocol/compatibility tests: 14 passed, locally and in Windows CI.
- Frontend ESLint and TypeScript/Vite build: passed locally and in Windows CI.
- Rust formatting: passed in Windows CI.
- First native build caught an unsupported Specta JSON return type; replaced it
  with a typed optional status object. [Run 41210633433](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/actions/runs/41210633433)
  subsequently passed native build, Rust tests/clippy, package audits and silent
  MSI install/uninstall checks.
- The hash-verified MSI was administratively extracted and its application run
  locally. The French panel showed driver checking, compilation and elapsed
  seconds. Clicking Cancel removed the actual worker process and displayed the
  cancelled state; the previous GPU selection returned. Temporarily hiding the
  extracted test copy's encoder XML produced a persistent, visible missing-model
  error. The file was restored after this check.
- GPU smoke tests of the extracted build timed out while the larger NPU compile
  was running. A sequential comparison after compilation completed succeeded:
  installed build 2.145 s, corrected build 2.295 s for the same 9.895 s fixture,
  both explicitly bound to Vulkan0 and returning the same text. Do not infer a
  GPU regression or a performance improvement from these single measurements.

## Nemotron architecture-specific experiment

The pinned NVIDIA 0.6B streaming ASR reference is separate from 30B-A4B Transcribe.
See [the experiment](../experiments/nemotron_npu/README.md) for revision, hashes,
runtime commands, placement and limitations. All three neural graphs now run
explicitly on NPU, including the recurrent predictor and joint classifier.

The export's static attention mask matched unmodified HF SDPA outputs exactly.
The initial eager-reference attempt produced an empty transcript and was rejected;
the original HF mask factory also failed TorchScript tracing. The accepted path
uses SDPA and verifies the replacement mask numerically before export. NumPy
feature extraction is compared to the reference and keeps daily runtime free of
PyTorch. Eight decoder control-flow and protocol validation tests pass.

NPU tokens match reference tokens on the three synthetic short fixtures and
24.37- and 39.845-second concatenated fixtures. Valid-frame encoder relative L2 differences
are below 0.7%; padded frames are excluded because they are not decoded. This
proves these numerical cases, not superior speech accuracy. The concatenated
reference itself omits some greeting words between language changes.

The 1,024-frame encoder compiled cold in 44.43 s (44.56 s including CPU decoder
initialization in that trial). The 4,096-frame all-NPU runtime initialized cold
in 221.19 s. Warm short-form lightweight worker startup, including process and
imports, measured 0.81 s. Inference and preprocessing took roughly 0.12–0.25 s
per short phrase across runs; process CPU time was about 0.02–0.09 s. The frozen
4,096-frame executable also passes parity, with a second 24-second inference
of 0.66 s, excluding preprocessing. First inference is slower. Machine load
varied and no energy/acoustic measurement was taken.

The optional Handy integration passed [Windows CI run 41217260926](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/actions/runs/41217260926):
native build, package audits, Rust tests/clippy, silent MSI installation/removal.
The artifact for commit `f9524bc` has SHA-256
`2ced8aed41bb3af6342648681474ce06fe0f8788de2db9ac367e4d34434c07ce`.
After administrative extraction, Handy's headless transcription path reported
`OpenVINO NPU` and passed all four cases:

| Fixture      | Audio (s) | Cached engine load (s) | First inference (s) | Second inference (s) |
| ------------ | --------: | ---------------------: | ------------------: | -------------------: |
| French       |     7.160 |                  0.715 |               0.767 |                0.333 |
| English      |     6.315 |                  0.636 |               0.764 |                0.322 |
| Mixed FR/EN  |     9.895 |                  0.618 |               0.789 |                0.352 |
| Concatenated |    24.370 |                  0.627 |               0.942 |                0.513 |

Inference includes preprocessing and text decoding. Engine load excludes Handy
startup. A 42-second input failed with exit code 1 and an explicit duration-limit
error, without truncation. The advertised limit is 40 seconds (655,200 samples,
40.95 seconds internally). Cache-aware streaming is not implemented.

The extracted build's GUI loaded Nemotron, displayed its active state and green
status indicator, and retained automatic language detection and Ctrl+Space. The
runtime log confirmed `device=NPU (no fallback)`. Windows cancelled elevation
before the local MSI installation began, so Program Files remains unchanged.
The extracted build is running for the user's live microphone/paste/fan check;
permanent installation and real-voice acceptance remain pending. The existing
GPU configuration remains available.

No Intune catalog change or shared rollout was performed. NPU Whisper loading
remains unresolved; Nemotron is a separate, explicitly identified pilot model.
