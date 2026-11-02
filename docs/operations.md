# Windows and Intune operations

## Managed release 0.11.0

The Company Portal distribution contains the app, five Nemotron streaming graphs,
tokenizer, frozen OpenVINO runtime and shared financial vocabulary. CI exports the
model from pinned NVIDIA weights; it does not copy a developer's model cache.
The `.intunewin` wrapper additionally includes Intel's signed NPU driver
32.0.100.5540. MSI/NSIS used separately require that prerequisite separately.

Installation runs as SYSTEM. It verifies installer hashes and Intel signature,
leaves a newer driver intact, runs Intel `--silent` without `--reboot`, and returns
3010 after a driver update. Handy refuses compilation until Windows has restarted.
The driver is never uninstalled or downgraded by Handy removal/rollback.
Compilation runs only as the signed-in user, with a per-user LocalAppData cache.

## Build and source policy

Run the **Core Ultra 355 NPU Windows and Intune** workflow against the reviewed
commit. It produces MSI/EXE and `handy-ultra355-intune` containing
`Install.intunewin`, `Detect.ps1`, `Require-CoreUltra355.ps1` and
`intune-metadata.json`. The metadata supplies the exact version, ProductCode,
commands and hashes. Never reuse detection/uninstall codes from another build.
**GitHub Actions builds artifacts; it does not update Intune automatically.**

- [Model policy](../packaging/managed-policy.json): owner controls enabled IDs.
  The initial managed list permits only `nemotron-35-npu-ten-minute`.
- [Financial vocabulary](../packaging/finance-glossary.json): shared FR/EN terms
  and explicit aliases. Add terms here, test ordinary speech/amounts, build and
  deploy a new version. This does not overwrite user `custom_words`.
- Empty alias lists are reference vocabulary, not automatic corrections.
  The runtime has no glossary decoder prompt; no fine-tuning is claimed.
- [Driver lock](../packaging/intel-driver-lock.json): immutable vendor installer.
- [Model card draft](huggingface-model-card.md): upstream provenance and limits.

## Existing tenant configuration (read-only inspection, 2026-11-02)

MCI still serves **Handy Core Ultra 355 NPU (Preview) 0.10.0**, describing Whisper
Turbo INT8. There are no dependencies or supersedence relationships. Assignment
is **Available for enrolled devices / All Users**, with no Required assignment.
The install context is SYSTEM; the CPU/OS requirement script applies; detection
is a 64-bit custom script. This observation is not evidence of a new rollout.

## Updating the existing optional app

1. Validate the exact MSI and NPU payload on the pilot, including a ten-minute
   request, short FR/EN requests, model restrictions and personal vocabulary.
2. In Intune, edit the existing app package and upload `Install.intunewin`.
3. Set name/description/version to the managed Nemotron ten-minute distribution.
   Copy both commands from the matching `intune-metadata.json`.
4. Retain SYSTEM, x64 and `Require-CoreUltra355.ps1` (64-bit, string equals True).
   The requirement script enforces Windows 11 25H2/build 26200 and exact 355 CPU.
5. Replace detection with this build's `Detect.ps1`, running as 64-bit SYSTEM.
   Retain return codes 0 success, 3010 soft reboot, 1618 retry and 1603 failure.
   Keep restart behavior without forced action; tell users to restart after the
   driver update before dictating. Do not create a reboot deadline inadvertently.
6. Preserve optional All Users availability. Do not turn it into Required/ESP.
7. Verify upload completion and displayed version, commands, detection and
   assignments; then verify Company Portal installation on an eligible device.

## Validation and rollback

CI verifies frontend lint/build, native policy/glossary/NPU tests and clippy,
MSI installation/detection, complete payload hashes, missing-NPU errors and
uninstall. Hosted runners have no NPU: they install MSI directly and unit-test
installer decision logic. Hardware and the actual driver-upgrade branch require
an eligible pilot; never claim hosted CI tested a driver installation.

Keep the previous package until the new install is verified. Preserve user
settings, history, recordings and shared Hugging Face caches. The MSI upgrade
removes its owned old Whisper files. Remove only the specifically retired local
40-second Nemotron payload/cache after the replacement is proven. A rollback
must not remove or downgrade Intel's driver.
