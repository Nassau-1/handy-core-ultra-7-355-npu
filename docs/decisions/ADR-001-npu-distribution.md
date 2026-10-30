# ADR-001 — explicit bundled NPU model and Intune Win32 delivery

Status: accepted for experimental pilot. Date: 2026-10-30.

The target is a Windows Core Ultra 7 355 and an existing Company Portal catalog.
Bbrizly's fork supplies an initial Windows OpenVINO pipe integration, but requires
external Python/model configuration and silently falls back after 120 seconds.
Panther Lake cold compilation has been reported around 11 minutes.

Use that branch as the provenance base, then expose a distinct bundled model,
package a private OpenVINO worker, allow 20-minute compilation, and report NPU
errors explicitly. A per-machine MSI inside an Intune Win32 package enables
standard-user self-service without a Microsoft Store public submission.

Rejected: Linux-only fork as direct Windows base; user-installed Python/environment
variables; using a GGML model selector while actually running another NPU model;
automatic CPU fallback masquerading as NPU success; retraining an already exported
model; public Store submission without a Partner Center identity or certification.

Consequences: larger installer, per-user compilation cache, pinned runtime upkeep,
unsigned preview policy checks and required real-device validation before claiming
NPU performance or production readiness. The owner subsequently requested optional
All Users catalog availability for this Preview, with CPU/OS eligibility checks.
The tenant's identity is not a signing identity and is never embedded in source.
