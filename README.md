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
- Search inside logs
- ZIP archiving of daily notes
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
│   ├── test_classifier.py
│   └── test_storage.py
├── ui/
│   ├── __init__.py
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



## 🖥️ UI foundation modules

The Tkinter application is split into reusable UI foundation modules while preserving the existing desktop workflow:

- `ui/styles.py` centralizes dark theme colors, fonts, menu styling, and ttk theme setup.
- `ui/widgets.py` provides reusable scrollable text panes, clipboard history list, status bar, search result list, and the right-click context menu for copy/cut/paste/select-all/clear.
- `ui/sounds.py` owns sound playback and keeps the same optional WAV behavior: if a bundled WAV file exists under the configured `sounds/` resource directory it is used on Windows, otherwise the app falls back to a winsound beep or Tk bell without crashing.
- `ui/tkinter_ui.py` keeps `SessionChronoUI` as the main application shell and composes the shared styles, widgets, and sound manager.

These modules rely on centralized configuration from `core/config.py`, so source and PyInstaller/frozen runs resolve resources consistently.

---

## 💾 Storage manager

`core/storage.py` exposes a `StorageManager` class that owns note persistence below a configurable base directory. The Tkinter UI uses the default manager today, while compatibility wrappers such as `save_text()`, `load_text()`, `create_today_zip()`, and `search_logs()` remain available for older callers during the UI refactor.

Storage operations now:

- Create parent directories before writes and replace files atomically after writing a temporary file.
- Return structured success/failure result objects from `StorageManager` methods instead of relying on uncaught file exceptions.
- Treat missing or unreadable loads as clear failed results with empty content.
- Build daily ZIP archives with archive members relative to the notes root, such as `YYYY-MM-DD/NOTE/example.txt`.
- Return structured search results with absolute paths, relative paths, matched line numbers, snippets, filenames, and modification timestamps.
- Provide export hook methods for future JSON, CSV, and Markdown integrations (`export_json()`, `export_csv()`, and `export_markdown()`).

To run the storage integration tests against temporary directories:

```bash
python -m unittest tests.test_storage
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
