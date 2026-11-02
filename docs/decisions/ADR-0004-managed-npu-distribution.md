# ADR: managed NPU distribution and financial vocabulary

Date: 2026-11-02. Status: accepted for implementation; deployment pending validation.

The Company Portal app still packages Whisper Preview 0.10.0. The successful
Nemotron pilot has its model in user-local storage, so distributing its MSI alone
would leave colleagues without the model. All target PCs are Core Ultra 7 355.

Bundle the frozen inference worker under Program Files. Download the five static
FP32 graphs and tokenizer from an immutable Hugging Face commit into per-user
LocalAppData. Verify sizes/SHA256, resume partial files and finalize atomically.
The export uses pinned NVIDIA weights and the accepted streaming code.
The Intune wrapper supplies Intel's signed driver and returns a soft reboot
code after an update. Compilation remains blocked in that same Windows boot.
MSI and NSIS alone require the driver to be installed separately.

An embedded owner-maintained JSON allowlist constrains native model enumeration,
selection, load, discovery and download. The UI presents the approved model and its download controls only.
Updates to the list require a new package. A remotely mutable catalog/service is
unnecessary for the current single-model deployment and is not introduced.

The financial glossary is versioned separately from user custom words. Nemotron
does not accept it as a decoding prompt in this runtime. Conservative exact
aliases and acronym casing run after recognition. Broad Soundex/fuzzy correction
over hundreds of finance terms was rejected because it can rewrite ordinary
words and amounts. Ambiguous terms remain reference vocabulary unless explicitly
spelled out; this is neither domain fine-tuning nor a guarantee of recognition.

Retain the original model's OpenMDW-1.1 license and notices. The resulting graphs
are a conversion of pretrained weights, not a newly trained model. Hugging Face
hosting is the distribution source; application CI bundles no weights.

The owner explicitly chose this split on 2026-11-02 instead of weights in Intune.
FP16 storage was investigated for the Windows cabinet size limit, but rejected
by the owner in favor of preserving FP32 and downloading through Handy. No FP16
artifact is shipped or published. Public hosting under Nassau-1 was approved.
