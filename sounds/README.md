# Sound asset policy

This directory is intentionally source-controlled as an optional resource directory for SessionChrono notification sounds. It should ship without real WAV assets for the v2.0.0 release candidate.

The application can run with no committed sound binaries: `ui.sounds.SoundManager` looks for optional WAV files under the `SOUNDS_DIR` path from `core.config`, and falls back to platform beeps or the Tk bell when a specific file is missing. Keeping this directory text-only avoids unreviewed binary assets while preserving the runtime path expected by source and PyInstaller builds.

Packaging keeps this directory in the bundle by collecting the text placeholders in `sessionchrono.spec`. If final WAV assets are approved for a later release, add only source-approved files, document their provenance here, and keep generated release artifacts out of Git.
