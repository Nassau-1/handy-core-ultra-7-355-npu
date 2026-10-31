# Nemotron NPU experiment

Experimental architecture-specific implementation with an optional local Handy
pilot. It is not enabled automatically and does not claim validated streaming
performance. All three neural graphs run on NPU; CPU handles audio preparation,
token control flow and text decoding.

## Reference

- [NVIDIA Nemotron 3.5 ASR Streaming 0.6B](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)
  at revision `ea30d66debe3740a08b573244286791d423d6b3e`.
- [Transformers 5.13.0 reference](https://github.com/huggingface/transformers/tree/v5.13.0/src/transformers/models/nemotron3_5_asr)
  (Apache-2.0). The exporter calls the installed reference modules; weights retain
  NVIDIA's model license. No model weights or compiled caches belong in Git.
- `model.safetensors`: 2,552,062,944 bytes, SHA-256
  `9eebdd6590289cb3030f310858f3df93256600a800a3e8200c5993d5f967e174`.

This is distinct from the 30B-A4B Nemotron 3.5 Transcribe model mentioned in the
linked Hacker News discussion. The smaller streaming model is a candidate for
local FR/EN dictation, not a demonstrated winner on this hardware.

## Design and limits

The encoder, language-prompt projector, acoustic projection, LSTM prediction
network and joint classifier target NPU explicitly. CPU variants are retained
for comparison and use one inference thread. Blank emissions advance the acoustic frame without
updating recurrent state. Nonblank tokens update the predictor. A ten-symbol
per-frame guard matches the reference greedy decoder.

Two tested shapes handle bounded utterances: 1,024 mel frames (about 10 seconds)
and 4,096 frames (the 40-second Handy pilot). Padding is masked and decoding stops at the valid acoustic length.
It does not yet export the encoder's streaming KV/convolution caches. Do not
split longer recordings into independent chunks and call that cache-aware
streaming. Feature extraction and tokenization remain on CPU.

## Reproduce

Use Python 3.12 in a separate environment. Install the CPU-only PyTorch wheel from
its official index, then `pip install -r requirements.txt`. Download the pinned
Hugging Face files (configuration, processor, tokenizer and safetensors) into a
local model directory using `download.py --output MODEL_DIRECTORY`. It verifies
each file against the pinned revision. The exporter rechecks the weight hash.

```powershell
python export.py --model MODEL_DIRECTORY --audio mono-16khz.wav --output IR_DIRECTORY
python runtime.py --artifact IR_DIRECTORY --cache CACHE_DIRECTORY --device CPU --validate --report cpu-parity.json
python runtime.py --artifact IR_DIRECTORY --cache CACHE_DIRECTORY --device NPU --compiler PLUGIN --validate --report npu-cold.json
python runtime.py --artifact IR_DIRECTORY --cache CACHE_DIRECTORY --device NPU --compiler PLUGIN --validate --report npu-warm.json
python -m unittest discover -s . -p 'test_*.py' -v
```

Add `--frames 4096` to export the 40-second pilot. `--reference-only` creates
additional fixture references without re-exporting weights. Validate them using
`runtime.py --validate --reference OTHER_REFERENCE/reference.npz`.
`--joint-device CPU` and `--predictor-device CPU` allow measured hybrid comparisons.

Use a separate cache directory for each device/compiler combination. A CPU run
checks graph and decode correctness; it does not validate NPU execution. The NPU
run checks `EXECUTION_DEVICES`, compares intermediate encoder output and requires
exact nonblank token equality against the HF reference. Encoder error is measured
only over valid acoustic frames; padded outputs are never decoded. Failure prevents
an acceptance claim. Keep wall time and CPU time distinct. The lightweight NumPy
frontend is also compared to the reference during export.

For PCM operation, call `runtime.py` with `--model`, `--artifact`, and `--cache`.
Feed signed little-endian PCM16, mono 16 kHz, on stdin; EOF ends one utterance.
The current CLI emits one UTF-8 line on stdout at completion and diagnostics on
stderr. Empty, oversized and odd-byte inputs fail explicitly. Use a binary pipe
(Python subprocess or an application), since PowerShell text pipelines can
corrupt raw PCM. Add `--worker` for persistent JSON-header + float32 PCM requests,
matching Handy's protocol. `benchmark.py` tests that actual transport across
multiple utterances and includes feature extraction in end-to-end measurements.

Install `pyinstaller==6.16.0`, then use `freeze.py --output BUILD_DIRECTORY` for a
standalone executable. The runtime needs OpenVINO, NumPy and tokenizers; it does
not import PyTorch, Transformers or librosa. Model artifacts and tokenizer files
are separate from the executable. A local payload under the application's
`nemotron-npu-pilot/{worker,artifact,tokenizer}` directory exposes a distinct
pilot model in Handy builds containing this integration. Do not replace the
bundled Whisper payload or upload the pilot to shared Intune distribution.

After a successful all-NPU validation of the frozen executable, install that
payload with `install_pilot.py --artifact IR_DIRECTORY --worker FROZEN_DIRECTORY
--model MODEL_DIRECTORY --validation VALIDATION_REPORT`. The installer checks
the pinned 4,096-frame shape and successful all-NPU reference parity, stages the
payload with a hash inventory and refuses to overwrite an existing pilot.
`benchmark.py --executable FROZEN_EXECUTABLE` verifies the packaged transport.

Compilation may take substantially longer than inference. Run experiments in a
supervised child process with a time budget; killing that child also cancels
native compilation. The currently installed Handy GPU configuration remains
the usable dictation path until the application integration is verified.

## 2026-10-31 hardware evidence

Intel Core Ultra 7 355, NPU driver 32.0.100.5540, OpenVINO 2026.2.1. Exact reference
tokens passed on synthetic French (7.16 s), English (6.315 s), mixed (9.895 s),
and concatenated mixed speech (24.37 s). Neural-graph relative L2 error on valid
encoder frames remained below 0.7%. This is not corpus-level WER evaluation.

Cold neural compilation: about 44.6 s at 1,024 frames; 221.2 s at 4,096. Cached
1,024-frame lightweight worker startup measured 0.81 s including process/imports.
Repeated short utterances took 0.12–0.25 s end to end in different runs; process
CPU time was roughly 0.02–0.09 s. No power meter or acoustic measurement was used.
First inference after loading is slower. The 24-second reference fixture took
0.60 s on the second inference with the larger shape, excluding its frontend.
At its installed location, the larger frozen worker compiled in about 105 s
under a different concurrent load, then restarted in 5.43 s including process
startup and imports. A five-second idle sample recorded 0.00 s process CPU time.
The installed persistent worker processed the 24.37-second fixture in 0.51 s
including preprocessing. A 39.845-second fixture also passed reference-token
parity; repeated inference was about 0.76 s before preprocessing. These small
synthetic examples cannot establish real-world recognition quality or silence.

`frontend.py` and `StaticEncoder` adapt algorithms from the Apache-2.0 reference;
see [the upstream license](TRANSFORMERS-LICENSE.txt). NVIDIA model licensing still
applies to weights and derived artifacts.
