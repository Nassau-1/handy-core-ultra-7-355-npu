# Managed NPU distribution validation — 2026-11-02

Status: public model, final Windows package, Intune publication and permanent
pilot upgrade through Company Portal verified.

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
installation/detection/runtime hashes and uninstall.

[Final Windows acceptance run](https://github.com/Nassau-1/handy-core-ultra-7-355-npu/actions/runs/41431834880)
at `710c5aa7a4777e309c6a3719e411aa08a87d0ee8` passed all checks, including the
upgrade download screen and final immutable model revision. Native checks cover
6 NPU integration, 3 managed-policy, 5 financial correction and 19 HTTP download
tests, in addition to the Python suites and frontend checks.

The first accepted package downloaded the complete 19-file model through Handy.
Cancellation at 890,916,329 bytes stopped disk growth; resume continued from that
offset and finalized only after verification. The final package's model files
are identical: its revised snapshot only changes repository documentation. To
avoid duplicating disk storage on the pilot, those verified files were hardlinked
into the final download staging folder, without a completion marker. Handy then
verified and finalized them itself. A returning user was correctly routed to the
single-model download screen; activation displayed only the approved model.

Final native NPU tests passed: 600 seconds of audio transcribed in 11.563 seconds,
with a 3.616-second cached model load, all 1,239 reference words and the ending
preserved. A one-sample oversize request failed explicitly. FR/EN/mixed financial
fixtures took 0.592/0.649/0.547 seconds, respectively; EBITDA and NOPAT corrections
were present. `--list-models` exposed exactly one approved model and requesting
an unapproved model failed. These synthetic tests do not establish domain WER;
the English fixture still contains a recognition error (`RDCF`).

The owner requested correction of the 18 development commits' Git identity and
approved rewriting the development branch. They now use Nassau-1 and its GitHub
noreply identity. Trees, messages and dates were preserved; the default branch
was unchanged. The original acceptance commit maps to
`4938254` in the corrected history. Existing CI run links retain their original
commit IDs as historical evidence. Hugging Face's current model card links to
the identical runtime source in the corrected history.

## Intune publication

The existing MCI application `250df8a0-1d13-49be-9cb5-b776fff16455` was updated to
**Handy Core Ultra 355 NPU 0.11.0**. Intune confirmed content upload complete and
application saved; reloading showed the new version, description and commands.
The optional All Users assignment was retained, with no required assignment or
forced restart. The existing custom requirement enforces Core Ultra 7 355 and
Windows build 26200 even though the generic OS selector reads Windows 11 24H2.

- Build commit: `710c5aa7a4777e309c6a3719e411aa08a87d0ee8`.
- MSI product: `{DB7623E1-3B8E-423F-BB00-CCAB2F53AC15}`.
- Intune content SHA256: `7C59C6AB22D30689A041CA6448527EDF66F944A1129B2F1E9D4B298D8DF0AA53`.
- Detection: generated 64-bit script for that exact product and version 0.11.0.
- System install: existing PowerShell wrapper command, now containing the pinned
  Intel driver prerequisite and runtime-only MSI.

GitHub Actions does not publish to Intune automatically. Each future binary
replacement needs its matching detection and uninstall metadata.

The owner recycled the obsolete 40-second payload and its cache; both paths were
verified absent. The original ten-minute rollback payload and active cache were
retained. Files in the Recycle Bin may still occupy disk space. Removal of the
old MSI-owned Whisper payload was verified after the permanent upgrade.

## Installed pilot acceptance

Company Portal synchronization exposed version 0.11.0, dated 2026-11-02. Clicking
Install completed through the Intune SYSTEM wrapper without a UAC prompt; the
portal displayed **Installed**. Intune's local action log reported detection
success and error code 0. The pilot already had Intel driver 32.0.100.5540, which
was retained. This run therefore validates the current-driver branch, not a new
driver upgrade or reboot on a colleague's machine.

The permanent MSI registry entry is 0.11.0 at the ProductCode above. The prior
pilot ProductCode `{637F17D5-5758-426B-A1C6-DD90EBA3E473}` is absent. The installed
`handy.exe` SHA256 is
`A3845068CDC70446900A89ECD8384FDA28D1BB3AF8AE27CADFDC3107D8DDDD06`, matching the
accepted artifact exactly. All 1,120 runtime inventory entries matched size and
SHA256. The MSI-owned Whisper payload is absent and the user's old downloaded
model directory is empty. The approved HF payload and active NPU cache remain.

The installed application transcribed the complete 600-second fixture on NPU in
14.261 seconds, with a 3.547-second cached load, all reference words and the ending
preserved. Its short mixed-language request passed and oversized input was
rejected. Settings fingerprints match the pre-upgrade values for shortcut
bindings, custom words, language, selected model and activation mode; the history
database remains present. The permanent Program Files application was restarted
for normal use after acceptance. Removing the installed application was tested
in CI; it was not uninstalled from the pilot after this successful upgrade.
