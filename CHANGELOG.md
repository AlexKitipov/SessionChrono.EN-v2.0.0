# Changelog

All notable changes to SessionChrono are documented here.

The format is inspired by Keep a Changelog, and this project uses semantic versioning where practical.

---

## [2.0.0] - Unreleased

### Added

- Modular `core/` and `ui/` architecture for separating application behavior from Tkinter presentation.
- Clipboard classification for URL, code, Markdown, JSON, XML, SQL, traceback, TODO, chat, log, and note content.
- JSON metadata sidecars with entry IDs, categories, titles, classifier confidence, tags, annotations, and file availability flags.
- Filtered search across saved notes and metadata.
- Export support for TXT, JSON, CSV, Markdown, and ZIP formats.
- Persistent settings for monitoring, polling, history size, sounds, export directory, and data directory.
- Daily diagnostic application logs.
- Runtime path policy for source runs and PyInstaller/frozen builds.
- Release documentation: README, installation guide, development guide, deployment checklist, and changelog skeleton.

### Changed

- Refactored clipboard monitoring and persistence behind `ApplicationController` and `StorageManager`.
- Updated history display to include category and timestamp details.
- Routed ZIP creation through the shared export service.
- Moved frozen-build user data to per-user application data directories instead of executable directories.

### Fixed

- Clipboard monitor pause/resume lifecycle is idempotent and avoids restarting consumed threads.
- Missing or unreadable search results are reported safely instead of being opened blindly.
- Empty resource directories for icons and sounds no longer cause startup tracebacks.

### Packaging notes

- Source runs write generated data to repository-local `ChronoNotes/`, `settings/`, `metadata/`, and `exports/` directories.
- Frozen builds write user data to `%APPDATA%\SessionChrono\` on Windows, `~/Library/Application Support/SessionChrono/` on macOS, or `${XDG_DATA_HOME}/SessionChrono/` / `~/.local/share/SessionChrono/` on Linux.
- Final PyInstaller and Inno Setup scripts should follow `INSTALLATION.md` and `DEPLOY.md`.

### Known follow-ups

- Add final packaging scripts/spec files if they are not included in the v2.0.0 documentation PR.
- Add release screenshots once packaged UI artwork is finalized.
