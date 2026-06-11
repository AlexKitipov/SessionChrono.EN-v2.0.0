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
