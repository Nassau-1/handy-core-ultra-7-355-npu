# ADR-002: Separate locally validated Nemotron NPU pilot

Date: 2026-10-31. Status: accepted; native application and user dictation validated on the local pilot.

The bundled Whisper Turbo INT8 pipeline still did not finish initialization in
the bounded hardware trials after the driver update. A pinned Transformers
Nemotron 3.5 ASR Streaming 0.6B reference exported to OpenVINO successfully runs
its encoder, recurrent predictor and joint classifier explicitly on the pilot's
NPU. It preserves reference tokens on three short synthetic FR/EN/mixed fixtures
and a 24-second combined fixture. These are correctness smoke tests, not a
representative speech-quality benchmark.

Expose it under a distinct `nemotron-35-npu-pilot` identity only when its complete
local payload exists. Keep the bundled Whisper model and conventional GPU models
separate. Store the optional payload in per-user application data, outside source
control and outside shared Intune packages. Reuse the cancellable worker protocol,
explicit device checks and persistent worker lifecycle.

The initial pilot uses a fixed 4,096-frame encoder, advertises a 40-second
dictation limit, and rejects oversized requests rather than truncating or quietly
changing devices. CPU performs feature extraction, token control flow and text
decoding; all three neural graphs target NPU. The lightweight NumPy frontend is
checked against the HF frontend and avoids PyTorch imports during normal use.

Rejected: relabeling the existing Whisper ID while replacing its weights (would
misrepresent model selection), automatic CPU fallback (would conceal placement),
and calling independent audio chunks cache-aware streaming (would alter context).
The 30B-A4B Transcribe model is a different architecture and not this artifact.

Longer recordings and genuine streaming require a separate export of encoder
attention/convolution state, or explicit validated segmentation. Do not increase
the shape blindly: cold compilation measured about 45 seconds for 1,024 frames
and 221 seconds for 4,096 on this pilot, with different concurrent machine load.
