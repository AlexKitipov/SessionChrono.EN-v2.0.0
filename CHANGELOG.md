# Changelog

All notable changes to SessionChrono are documented here.

The format is inspired by Keep a Changelog, and this project uses semantic versioning where practical.

---

## [2.0.0] - 2026-06-11 Release Candidate

### Added

- Modular `core/` and `ui/` architecture for separating application behavior from Tkinter presentation.
- Clipboard classification for URL, code, Markdown, JSON, XML, SQL, traceback, TODO, chat, log, and note content.
- JSON metadata sidecars with entry IDs, categories, titles, classifier confidence, tags, annotations, and file availability flags.
- Filtered search across saved notes and metadata.
- Export support for TXT, JSON, CSV, Markdown, and ZIP formats.
- Persistent settings for monitoring, polling, history size, sounds, export directory, and data directory.
- Daily diagnostic application logs.
- Runtime path policy for source runs and PyInstaller/frozen builds.
- Release documentation: README, installation guide, development guide, deployment checklist, installer checklist, and finalized release-candidate notes.
- Source-controlled PyInstaller spec, Windows version metadata, build wrappers, and Inno Setup script for reproducible local packaging.

### Changed

- Refactored clipboard monitoring and persistence behind `ApplicationController` and `StorageManager`.
- Updated history display to include category and timestamp details.
- Routed ZIP creation through the shared export service.
- Moved frozen-build user data to per-user application data directories instead of executable directories.

### Fixed

- Clipboard monitor pause/resume lifecycle is idempotent and avoids restarting consumed threads.
- Missing or unreadable search results are reported safely instead of being opened blindly.
- Empty resource directories for icons and sounds no longer cause startup tracebacks.
- Obsolete committed `.bak` files and Python bytecode caches were removed from source control.

### Packaging notes

- Repository changes for this release candidate are text-only except pre-existing approved source assets; PyInstaller output, installer executables, DLLs, `.pyd` files, bytecode, manifests, logs, and runtime data must remain uncommitted.
- Source runs write generated data to repository-local `ChronoNotes/`, `settings/`, `metadata/`, and `exports/` directories.
- Frozen builds write user data to `%APPDATA%\SessionChrono\` on Windows, `~/Library/Application Support/SessionChrono/` on macOS, or `${XDG_DATA_HOME}/SessionChrono/` / `~/.local/share/SessionChrono/` on Linux.
- PyInstaller and Inno Setup scripts are source-controlled for local release builds; generated binaries are attached to GitHub releases only.
- Release artifact candidates for local generation are `dist/SessionChrono/`, a portable ZIP derived from that folder, `dist/installer/SessionChrono-2.0.0-Setup.exe`, and optional checksum files.

### Known follow-ups

- Run final Windows PyInstaller and Inno Setup packaging in a clean release environment.
- Add release screenshots once packaged UI artwork is finalized.
