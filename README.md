# SessionChrono – Modular Clipboard Notepad (Tkinter Edition)

SessionChrono is a smart clipboard-logging notepad that automatically saves copied text into categorized files.
This version is fully modular, lightweight, and optimized for local use with Tkinter.

---

## ✨ Features

- Automatic clipboard monitoring
- Categorized auto-saving (URL, CODE, TODO, CHAT, LOG, NOTE)
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
│   ├── config.py
│   ├── logger.py
│   ├── storage.py
│   └── utils.py
├── icons/
│   └── .gitkeep
├── sounds/
│   └── .gitkeep
├── ui/
│   ├── __init__.py
│   └── tkinter_ui.py
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
