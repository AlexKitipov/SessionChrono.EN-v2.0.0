# Sound asset policy

This directory is reserved for optional SessionChrono notification sound sources or text documentation.

For this v2.0.0 release-candidate PR, no generated WAV or other binary sound files are added. The application already falls back to platform beeps or the Tk bell when optional WAV files are absent, so packaging remains reproducible without committed binary sound assets.

If final WAV assets are created for a later release, keep packaging-generated files out of Git and document the asset provenance before committing any approved source asset.
