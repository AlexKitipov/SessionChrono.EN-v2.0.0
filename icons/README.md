# Icon asset policy

This directory is reserved for source-controlled icon templates and other text-based artwork notes used by SessionChrono packaging.

For this v2.0.0 release-candidate PR, no generated binary icon files are added here. If release artwork is produced locally, keep generated `.ico`, `.png`, or other binary render outputs out of the commit unless a future release task explicitly approves them as source assets.

The PyInstaller and Inno Setup scripts currently reference the repository-level `SessionChrono.ico` when a local Windows package is built. Any replacement artwork should be reviewed as an asset-source change separately from generated build artifacts.
