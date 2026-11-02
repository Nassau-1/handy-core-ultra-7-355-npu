# ADR: managed NPU distribution and financial vocabulary

Date: 2026-11-02. Status: accepted for implementation; deployment pending validation.

The Company Portal app still packages Whisper Preview 0.10.0. The successful
Nemotron pilot has its model in user-local storage, so distributing its MSI alone
would leave colleagues without the model. All target PCs are Core Ultra 7 355.

Bundle the five static streaming graphs, tokenizer and frozen inference worker
under Program Files. Export from pinned NVIDIA weights using the accepted
streaming code; leave compiled device caches in each user's LocalAppData.
The Intune wrapper supplies Intel's signed driver and returns a soft reboot
code after an update. Compilation remains blocked in that same Windows boot.
MSI and NSIS alone require the driver to be installed separately.

An embedded owner-maintained JSON allowlist constrains native model enumeration,
selection, load, discovery and download. The UI presents the approved model only.
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
hosting is useful for provenance and reuse but is not required for CI exports.
