# Icon asset policy

This directory is intentionally source-controlled as an optional resource directory for SessionChrono icon templates and artwork notes. It should ship without additional generated icon binaries for the v2.0.0 release candidate.

The packaging entry points use the repository-level `SessionChrono.ico` for the Windows executable and installer icon. Runtime code should resolve optional future icon resources through the `ICONS_DIR` path from `core.config`; that path is mirrored in PyInstaller by `sessionchrono.spec`.

Packaging keeps this directory in the bundle by collecting the text placeholders in `sessionchrono.spec`. If replacement artwork is approved later, document its provenance here and keep generated build outputs out of Git unless a release task explicitly approves them as source assets.
