# SessionChrono – Modular Clipboard Notepad (Tkinter Edition)

SessionChrono is a smart clipboard-logging notepad that automatically saves copied text into categorized files.
This version is fully modular, lightweight, and optimized for local use with Tkinter.

---

## ✨ Features

- Automatic clipboard monitoring
- Categorized auto-saving (URL, CODE, MARKDOWN, JSON, XML, SQL, TRACEBACK, TODO, CHAT, LOG, NOTE)
- Built-in text editor
- Clipboard history panel
- Last copied preview
- Search inside logs with text, category, date, tag, and filename/title filters
- JSON sidecar metadata with entry IDs, categories, titles, classifier confidence, tags, and annotations
- Multi-format exports: plain text bundles, JSON with metadata, CSV summaries, Markdown reports, and ZIP archives
- Persistent daily application logs for diagnostics
- Sound alerts (WAV or fallback beep)
- Centralized runtime path and resource configuration
- Works fully offline

---

## 📁 Project Structure

```text
SessionChrono.EN-v2.0.0/
├── core/
│   ├── __init__.py
│   ├── app_controller.py
│   ├── export.py
│   ├── chrono.py
│   ├── classifier.py
│   ├── config.py
│   ├── logger.py
│   ├── storage.py
│   └── utils.py
├── icons/
│   └── .gitkeep
├── sounds/
│   └── .gitkeep
├── tests/
│   ├── test_app_controller.py
│   ├── test_classifier.py
│   ├── test_export.py
│   ├── test_metadata.py
│   ├── test_search.py
│   └── test_storage.py
├── ui/
│   ├── __init__.py
│   ├── components.py
│   ├── dialogs.py
│   ├── sounds.py
│   ├── styles.py
│   ├── tkinter_ui.py
│   └── widgets.py
├── main.py
├── README.md
└── requirements.txt
```

---

## ⚙️ Runtime path policy

Runtime path decisions are centralized in `core/config.py` so GUI, storage, and utility code use the same application metadata, resource roots, and user-data directories.

### Source / development runs

When running from source, SessionChrono keeps the historical local storage behavior:

- App root: the repository directory.
- Resource root: the repository directory.
- Auto-saved notes: `ChronoNotes/` in the repository directory.
- Settings, metadata, and exports: `settings/`, `metadata/`, and `exports/` in the repository directory.

This preserves compatibility with existing local `ChronoNotes/` data from earlier versions.

### PyInstaller / frozen runs

When `sys.frozen` is present, SessionChrono treats the executable location as the frozen application root and writes runtime data to a per-user writable application data directory instead of the bundled executable directory:

- Windows: `%APPDATA%\SessionChrono\`
- macOS: `~/Library/Application Support/SessionChrono/`
- Linux and other Unix-like systems: `${XDG_DATA_HOME}/SessionChrono/` or `~/.local/share/SessionChrono/`

Inside that writable data root, notes continue to live under `ChronoNotes/`, with additional directories reserved for `settings/`, `metadata/`, and `exports/`.

Bundled resources are resolved from the PyInstaller bundle extraction/root path where available, so empty `sounds/` and `icons/` directories are safe and do not cause tracebacks.

### Application diagnostics logs

SessionChrono writes persistent diagnostic logs through `core/logger.py`. Log files are created daily under:

```text
<LOG_ROOT>/application_logs/SessionChrono_YYYY-MM-DD.log
```

`LOG_ROOT` is resolved by `core/config.py`:

- Source / development runs: `<repository>/ChronoNotes/application_logs/`
- PyInstaller / frozen Windows runs: `%APPDATA%\SessionChrono\ChronoNotes\application_logs\`
- PyInstaller / frozen macOS runs: `~/Library/Application Support/SessionChrono/ChronoNotes/application_logs/`
- PyInstaller / frozen Linux runs: `${XDG_DATA_HOME}/SessionChrono/ChronoNotes/application_logs/` or `~/.local/share/SessionChrono/ChronoNotes/application_logs/`

The logs capture startup and shutdown, clipboard monitor lifecycle events, file save/load actions, search failures, ZIP creation, and sound playback fallback decisions. UI messages stay concise while logged exceptions preserve tracebacks for diagnostics.

---

## 🧭 Application controller boundary

`core/app_controller.py` owns the application behavior that used to live directly in the Tkinter window:

- Starting, pausing, resuming, and shutting down the clipboard monitor.
- Receiving clipboard text events from `core/chrono.py`.
- Building categorized filenames through `core/utils.py`.
- Saving clipboard text through `core/storage.py`.
- Maintaining the current in-memory session history and last auto-note path.
- Emitting startup, shutdown, persistence, and monitor lifecycle diagnostics through `core/logger.py`.

`ui/tkinter_ui.py` now acts as a view layer: it wires menu commands and shortcuts to controller methods, renders controller state into the editor/history/preview widgets, and keeps file dialogs or platform folder-opening UI in the Tkinter shell. The `main.py` entry point remains the source and PyInstaller startup path.

Clipboard monitoring lifecycle is explicit and idempotent. Pausing stops and joins the current monitor loop, resuming creates a fresh background thread through the monitor object instead of attempting to restart a consumed `threading.Thread`, and repeated pause/resume requests are safe. This prevents background clipboard polling from keeping a frozen executable alive after the window closes.

---

## 🖥️ UI foundation modules

The Tkinter application is split into reusable UI foundation modules while preserving the existing desktop workflow:

- `ui/styles.py` centralizes dark theme colors, fonts, menu styling, dialog geometry, and ttk theme setup.
- `ui/widgets.py` provides low-level reusable controls such as scrollable text panes, clipboard history lists, status bars, search result lists, and the right-click context menu for copy/cut/paste/select-all/clear.
- `ui/components.py` composes higher-level main-window sections, including the editor panel, last-copied preview, clipboard history panel, and a reusable action strip for future toolbar work.
- `ui/dialogs.py` owns pop-up UI flows for About, filtered log search/results, export options, settings, entry details, and parented info/error message helpers.
- `ui/sounds.py` owns sound playback and keeps the same optional WAV behavior: if a bundled WAV file exists under the configured `sounds/` resource directory it is used on Windows, otherwise the app falls back to a winsound beep or Tk bell without crashing.
- `ui/tkinter_ui.py` keeps `SessionChronoUI` as the main application shell and composes the shared styles, components, dialogs, widgets, and sound manager.

These modules rely on centralized configuration from `core/config.py`, so source and PyInstaller/frozen runs resolve resources consistently.

### Keyboard shortcuts

The main Tkinter window registers common shortcuts for desktop workflows:

- `Ctrl+N`: new editor document.
- `Ctrl+O`: open a text file.
- `Ctrl+S`: save the current file.
- `Ctrl+Shift+S`: save as a new file.
- `Ctrl+F`: search saved logs.
- `Ctrl+P`: pause or resume clipboard monitoring.

---


## ⚙️ Persistent settings

Use **Tools → Settings** to edit production preferences without changing code. Settings are saved as a user-writable JSON file in the resolved settings directory (`settings/settings.json` during source runs, or the per-user application data directory in PyInstaller/frozen builds). The app falls back to safe defaults if the file is missing or malformed.

Configurable preferences include:

- Start clipboard monitoring automatically on launch.
- Clipboard polling interval.
- Maximum number of in-session history entries.
- Sound enablement, volume preference, and individual event toggles.
- Default export directory used by export actions.
- ChronoNotes data directory, with an optional safe copy/migration control that copies existing notes to the new directory without deleting originals.
- A reserved theme option that keeps the current dark theme as the default.

To run the settings persistence tests:

```bash
python -m unittest tests.test_settings
```

---

## 💾 Storage manager

`core/storage.py` exposes a `StorageManager` class that owns note persistence below a configurable base directory. The Tkinter UI uses the default manager today, while compatibility wrappers such as `save_text()`, `load_text()`, `create_today_zip()`, and `search_logs()` remain available for older callers during the UI refactor.

Storage operations now:

- Create parent directories before writes and replace files atomically after writing a temporary file.
- Return structured success/failure result objects from `StorageManager` methods instead of relying on uncaught file exceptions.
- Treat missing or unreadable loads as clear failed results with empty content.
- Build daily ZIP archives through the export service with archive members relative to the notes root, such as `YYYY-MM-DD/NOTE/example.txt`, plus `manifest.json` and metadata sidecars when available.
- Return structured search results with absolute paths, relative paths, matched line numbers, snippets, filenames, modification timestamps, categories, creation timestamps, tags, and safe missing-file availability flags.
- Export ChronoNotes in production-ready formats: TXT bundles, JSON records with metadata, CSV summaries, Markdown reports, and ZIP archives. Relative export filenames are written below the configured exports directory by default, which keeps frozen/PyInstaller builds from writing inside the bundled application directory.
- Apply date-range and category filters consistently across export formats.

To run the storage integration tests against temporary directories:

```bash
python -m unittest tests.test_storage
```

---


## 🔎 Filtered history search

The **Search Logs** dialog (`Ctrl+F`) supports practical filters that can be combined in one search:

- Full-text query across note bodies plus metadata title, short title, tags, and annotations.
- Category filter, such as `NOTE`, `URL`, `CODE`, or any classifier category folder.
- Date range filters using `YYYY-MM-DD` values against metadata creation timestamps.
- Tag filter for user tags maintained in the Entry Details dialog.
- Filename/title filter for matching either the saved text filename or the metadata title.

Search results show category, timestamp, tags, and a clear `(missing file)` marker when a metadata sidecar still matches but the original text file is unavailable. Missing files are never opened blindly; attempts to open one return a concise error while keeping the result visible so users understand what happened.

The clipboard history panel now displays each entry with its category and timestamp. Selected history entries also provide **Open Folder** and **Copy Path** actions for quickly locating the underlying saved note or sharing its filesystem path.

To run the filtered search tests:

```bash
python -m unittest tests.test_search
```


## 📤 Exporting ChronoNotes

Use **Tools → Export Notes...** to create shareable files from saved ChronoNotes. The export dialog supports:

- Format selection for plain text (`.txt`), JSON (`.json`), CSV (`.csv`), Markdown (`.md`), or ZIP (`.zip`).
- Optional category filtering, such as `NOTE`, `URL`, or `CODE`.
- Optional date ranges using `YYYY-MM-DD`.
- Default output into the configured exports directory (`exports/` in source runs, or the per-user data directory in PyInstaller/frozen builds).

The legacy **Create ZIP of Today** menu action is still available, but it now uses the same export service and writes a ZIP containing today's text files, a `manifest.json`, and metadata JSON files for entries that have sidecars.

To run the export tests:

```bash
python -m unittest tests.test_export
```

---

## 🏷️ Entry metadata and tagging

Each auto-saved clipboard entry now gets a JSON sidecar managed by `core/metadata.py`. Metadata sidecars are stored under the configured metadata directory (`metadata/` in source runs, or the per-user data directory for PyInstaller/frozen builds) and include:

- Entry ID, file path, created timestamp, category, title, and short title.
- Text length and classifier confidence.
- Editable user tags and an optional annotation/note.
- File availability flags so metadata can still be loaded and searched if the text file was moved, deleted, or is unreadable.

The Tkinter **Entry Details** dialog shows metadata for the current editor file or selected history item, and lets users add/edit comma-separated tags plus a free-form annotation. `StorageManager` exposes `load_metadata_by_path()`, `update_metadata()`, and `search_metadata()` for future filtering and export features.

To run the metadata tests:

```bash
python -m unittest tests.test_metadata
```

---

## 🧠 Clipboard classification

Clipboard text is classified by `core/classifier.py`, which scores all supported categories before selecting a deterministic best match. The classifier recognizes URL, CODE, MARKDOWN, JSON, XML, SQL, TRACEBACK, TODO, CHAT, LOG, and NOTE content, and can return a confidence score for callers that need more detail.

`core.utils.classify_text(text)` remains available as a compatibility wrapper and returns only the category string used for folder and filename creation. Empty, whitespace-only, very large, and binary-like clipboard strings safely fall back to `NOTE` instead of raising errors.

To run the classifier unit tests:

```bash
python -m unittest tests.test_classifier
```

---

## 🧪 Automated tests

Run all automated tests with:

```bash
python -m unittest discover -s tests
```

---

## ▶️ Running locally

Install dependencies, then start the Tkinter application from the repository root:

```bash
pip install -r requirements.txt
python main.py
```

---

## 🧪 Path-resolution smoke check

To inspect path resolution without importing or opening Tkinter, run:

```bash
python main.py --paths
```

You can also run the configuration module directly:

```bash
python -m core.config
```

Both commands print the resolved app root, resource directories, and writable data directories as JSON.
