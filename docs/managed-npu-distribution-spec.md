# Managed ten-minute NPU distribution

Date: 2026-11-02. Status: implementation and tenant inspection.

## Scope

Ship the accepted Nemotron ten-minute engine and model to colleagues through the
existing Company Portal application. The owner confirms identical Core Ultra 7
355 PCs. Retain x64 Windows 11 25H2 eligibility, optional availability, local
audio processing, automatic FR/EN language and existing user history/settings.
The old public preview and locally customized pilot are different distributions.

## Plan

1. Inspect the live Intune app, assignment, version and dependencies. Document the
   actual GitHub build-to-portal boundary; do not imply a push deploys to Intune.
2. Bundle the pinned Nemotron model/worker in Program Files. Build reproducibly
   from the original pinned NVIDIA weights and export code. Reuse the validated
   streaming algorithm and retain per-user compilation cache.
3. Add a centrally authored allowlist, distributed with the application. The
   initial list contains only `nemotron-35-npu-ten-minute`. Enforce it in native
   enumeration, selection/loading, imports/rescan and downloads, including CLI.
   Remove the public model catalog and import/download controls from this edition.
   Standard users must not be able to expand it through their settings.
4. Package the verified Intel 32.0.100.5540 prerequisite for SYSTEM installation,
   version/hash/signature checks and explicit reboot handling. Never force a
   restart, downgrade a newer driver, or compile models as SYSTEM.
5. Bump the application version, update detection and verify clean install and
   upgrade. Test the actual packaged engine on short and 600-second audio.
6. Remove the two retired local NPU payloads/cache after verifying the replacement;
   preserve active streaming payload/cache, recordings, settings and shared HF
   caches. MSI-owned files are removed by upgrade, not arbitrary deletion.
7. Prepare a Hugging Face model card/export manifest with original provenance,
   license and measured limitations. This is a converted architecture-specific
   deployment of NVIDIA weights, not new training. Public publication requires a
   specified namespace and visibility; no machine cache or private audio/logs.
8. Include a versioned French/English financial glossary, independent of each
   user's custom words. Apply conservative exact aliases and acronym casing
   after ASR; no broad phonetic/fuzzy matching over the enterprise list, no
   expansion of abbreviations, no rewriting of numbers. Show the included
   glossary in settings. Preserve personal words and test ambiguous ordinary
   speech, punctuation, financial amounts and mixed-language sentences.

## Verification and rollout

Unit-test policy enforcement, duration/reboot/driver checks, payload integrity and
package detection; run frontend lint/build, Rust tests/clippy and installer CI.
Verify the single-model GUI and the installed NPU path on the pilot. Inspect the
concrete Intune upload/configuration before changing distribution. Preserve the
previous MSI for rollback; never uninstall or downgrade an existing driver as a
rollback step. Do not silently broaden availability or create a Required rollout.

The owner controls enabled models through reviewed source policy and versioned
packages. Remote instant model toggles and a new management service are outside
this change. Additional hardware remains unvalidated.
