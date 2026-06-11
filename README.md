# SessionChrono v2.0.0

SessionChrono is a local-first clipboard notepad for people who want copied text to be captured automatically, organized predictably, and available later without a cloud account. The Tkinter desktop app watches the clipboard, classifies new text, saves each entry under `ChronoNotes/`, creates JSON metadata sidecars, and provides editor, history, search, settings, and export workflows.

The v2.0.0 codebase is intentionally modular: application behavior lives in `core/`, the Tkinter shell lives in `ui/`, and `main.py` remains the shared entry point for source runs and packaged builds.

---

## Features

- Automatic clipboard monitoring with pause/resume controls.
- Categorized note storage for `URL`, `CODE`, `MARKDOWN`, `JSON`, `XML`, `SQL`, `TRACEBACK`, `TODO`, `CHAT`, `LOG`, and `NOTE` entries.
- Built-in text editor with New, Open, Save, and Save As actions.
- Clipboard history panel with category/timestamp labels, Open Folder, Copy Path, and Entry Details actions.
- Last-copied preview panel for the newest captured clipboard item.
- Search dialog with text, category, date range, tag, and filename/title filters.
- JSON metadata sidecars with entry IDs, titles, classifier confidence, user tags, notes, and file availability flags.
- Export dialog for plain text, JSON, CSV, Markdown, and ZIP outputs.
- Daily diagnostic logs for startup, shutdown, persistence, search, export, ZIP, and sound fallback events.
- Persistent settings for monitoring, polling interval, history size, sound preferences, export location, and data directory.
- Sound alerts from bundled WAV files when present, with platform fallbacks when files are missing.
- Fully offline operation.

---

## Quick start from source

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Useful non-GUI smoke checks:

```bash
python main.py --paths
python -m core.config
python -m pytest
```

For complete install and packaging instructions, see [`INSTALLATION.md`](INSTALLATION.md). For contributor workflows, see [`DEVELOPMENT.md`](DEVELOPMENT.md). For release steps, see [`DEPLOY.md`](DEPLOY.md).

---

## Everyday usage

1. Start the app with `python main.py` or with a packaged executable.
2. Copy text in any application.
3. SessionChrono detects new clipboard text, classifies it, saves it, and updates the preview/history panels.
4. Use **Tools → Pause / Resume Monitoring** or `Ctrl+P` when you do not want clipboard captures.
5. Use **Tools → Search Logs** or `Ctrl+F` to search saved entries.
6. Use **Tools → Entry Details** to edit tags or notes for the current entry.
7. Use **Tools → Export Notes...** to create TXT, JSON, CSV, Markdown, or ZIP exports.

### Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | New editor document |
| `Ctrl+O` | Open a text file |
| `Ctrl+S` | Save current file |
| `Ctrl+Shift+S` | Save as a new file |
| `Ctrl+F` | Search logs |
| `Ctrl+P` | Pause or resume monitoring |

### Screenshot placeholders

Release screenshots can be added under a future `docs/screenshots/` directory and embedded here when final packaging artwork is available:

- Main window with editor, last copied preview, and history panel.
- Search dialog with structured filters.
- Export dialog with format and date/category filters.
- Settings dialog with monitoring, sounds, and data-directory options.

---

## Architecture overview

```text
SessionChrono.EN-v2.0.0/
├── core/                 # Business logic, persistence, classification, exports, paths
├── ui/                   # Tkinter windows, dialogs, widgets, styles, sounds
├── tests/                # Unit/integration tests for core behavior
├── icons/                # Bundled icon resources
├── sounds/               # Optional bundled sound resources
├── main.py               # CLI/Tkinter entry point
├── requirements.txt      # Runtime Python dependencies
├── INSTALLATION.md       # User install and packaging guide
├── DEVELOPMENT.md        # Contributor guide
├── DEPLOY.md             # Release checklist
└── CHANGELOG.md          # v2.0.0 release-note skeleton
```

### Core layer

- `core/config.py` defines application metadata, source/frozen path resolution, resource roots, and writable data directories.
- `core/app_controller.py` coordinates clipboard monitoring, classification, storage, metadata creation, settings, and callbacks consumed by the UI.
- `core/chrono.py` owns polling-based clipboard monitoring.
- `core/classifier.py` scores clipboard text against deterministic category rules.
- `core/storage.py` manages note reads/writes, search, ZIP creation, and export entry points.
- `core/metadata.py` manages JSON sidecars for captured entries.
- `core/export.py` implements TXT, JSON, CSV, Markdown, and ZIP export formats.
- `core/settings.py` loads, validates, saves, and migrates user settings.
- `core/logger.py` configures persistent diagnostic logging.

### UI layer

- `ui/tkinter_ui.py` builds the main desktop window and wires menu actions to the controller.
- `ui/components.py` contains major panels such as editor, preview, and history.
- `ui/dialogs.py` contains Search, Settings, Export, Entry Details, and About dialogs.
- `ui/widgets.py` contains reusable lower-level widgets.
- `ui/styles.py` centralizes theme constants and ttk styling.
- `ui/sounds.py` handles WAV playback and fallback beeps.

The UI should not own persistence policy or category rules; it should call controller/storage services and render their results.

---

## User data, exports, settings, metadata, and logs

Runtime paths are centralized in `core/config.py`. Inspect the effective values at any time with:

```bash
python main.py --paths
```

### Source/development runs

When running from a checkout, SessionChrono writes beside the repository so local development remains transparent:

| Data type | Default source-run path |
| --- | --- |
| Saved notes | `ChronoNotes/` |
| Diagnostic logs | `ChronoNotes/application_logs/SessionChrono_YYYY-MM-DD.log` |
| Settings | `settings/settings.json` |
| Metadata sidecars | `metadata/*.json` |
| Exports | `exports/` |
| Resources | `icons/`, `sounds/` |

### Frozen/PyInstaller runs

When `sys.frozen` is present, bundled resources are read from the executable bundle, while user-writable files move to the per-user application data directory:

| Platform | Data root |
| --- | --- |
| Windows | `%APPDATA%\SessionChrono\` |
| macOS | `~/Library/Application Support/SessionChrono/` |
| Linux/Unix | `${XDG_DATA_HOME}/SessionChrono/` or `~/.local/share/SessionChrono/` |

Within that root, the app uses `ChronoNotes/`, `settings/`, `metadata/`, and `exports/`.

---

## Search and metadata

The Search Logs dialog can combine filters:

- text query across note bodies plus metadata fields;
- category such as `NOTE`, `URL`, or `CODE`;
- date range in `YYYY-MM-DD` format;
- user tag;
- filename/title fragment.

Results include snippets, category, timestamp, tags, and missing-file indicators when metadata still exists but the original text file was moved or deleted.

Entry metadata is stored as JSON sidecars and can be edited through **Tools → Entry Details**. Tags and annotations are included in search and supported export formats.

---

## Exports and ZIP archives

Use **Tools → Export Notes...** to export saved notes as:

- `.txt` plain text bundle;
- `.json` structured records with metadata;
- `.csv` summary rows;
- `.md` Markdown report;
- `.zip` archive containing notes, `manifest.json`, and metadata sidecars when available.

The legacy **Tools → Create ZIP of Today** action remains available and uses the same export service to archive the current day's notes.

---

## Testing

Run the full test suite:

```bash
python -m pytest
```

Targeted suites:

```bash
python -m pytest tests/test_classifier.py
python -m pytest tests/test_storage.py
python -m pytest tests/test_metadata.py
python -m pytest tests/test_search.py
python -m pytest tests/test_export.py
python -m pytest tests/test_settings.py
python -m pytest tests/test_app_controller.py
python -m pytest tests/test_import_smoke.py
```

The automated suite includes import smoke checks for `main.py`, core modules, and Tkinter UI modules without starting the Tk event loop. The pytest setup isolates default runtime paths in a temporary directory so test runs do not write to real user `ChronoNotes/` folders.

---

## Documentation set

- [`INSTALLATION.md`](INSTALLATION.md): source install, portable executable usage, Inno Setup installer expectations, and uninstall behavior.
- [`DEVELOPMENT.md`](DEVELOPMENT.md): project structure, boundaries, adding categories/export formats/UI, and tests.
- [`DEPLOY.md`](DEPLOY.md): release checklist for version checks, clean builds, PyInstaller, installer creation, smoke tests, tags, and GitHub releases.
- [`CHANGELOG.md`](CHANGELOG.md): v2.0.0 release-note skeleton.
