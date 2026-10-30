# Security

This fork handles microphone audio, local transcript history and clipboard/paste.
The NPU subprocess performs local inference and receives audio over anonymous pipes.
It is launched from packaged application resources, never PATH or user-supplied Python.

Program Files holds the installed application/runtime/model. Each user owns their
cache and Handy data. Audio/transcripts follow upstream history settings and should
be treated as sensitive. Optional user-configured cloud post-processing remains an
upstream feature; local NPU inference does not enable it.

Never commit credentials, certificates/private keys, tenant exports, audio, logs,
model binaries or local configuration. The public repository contains generic
Intune packaging only. Build downloads use an immutable model revision with file
hashes; the Microsoft packaging executable is SHA256 pinned.

Report vulnerabilities through GitHub private vulnerability reporting where
available. Do not put recordings, tokens or personal information in public issues.
Revoke exposed secrets, remove them from history and rebuild compromised artifacts.

Experimental unsigned builds require validation under the organization's existing
App Control/Defender policies. No policy bypass, broad exclusions or driver changes
are part of installation. NPU failure is explicit, with no silent CPU fallback.
