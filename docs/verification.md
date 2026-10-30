# Verification

Date: 2026-10-30. In progress.

- Python protocol unit tests: 8 passed locally (French/Auto, normalized/nonfinite PCM,
  malformed frames and rejection of unsupported Turbo translation).
- Local Rust formatting: performed using a repository-local stable toolchain.
- Windows/MSVC compilation, lint and installer smoke: pending CI.
- Target NPU, latency/accuracy and Intune delivery: not tested; target unavailable.

This file will be updated with final build evidence. No performance is inferred
from passing protocol tests or installation.
