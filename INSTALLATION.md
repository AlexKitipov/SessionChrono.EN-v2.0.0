# SessionChrono Installation Guide

This guide covers three ways to run SessionChrono v2.0.0:

1. source checkout for development or power users;
2. portable executable produced with PyInstaller;
3. Windows installer produced with Inno Setup.

> Packaging scripts/spec files may be added by a later packaging PR. Until then, treat the PyInstaller and Inno Setup sections as the release contract that build automation should satisfy.

---

## Requirements

### Source runs

- Python 3.10 or newer is recommended.
- Tkinter must be available in the Python installation.
- Runtime dependencies from `requirements.txt`:
  - `pyperclip` on all platforms;
  - `pywin32` on Windows only.

### Portable executable and installer runs

End users of a packaged build should not need Python installed. Packaged builds should include Python, Tkinter support, runtime dependencies, `SessionChrono.ico`, and any resources from `icons/` and `sounds/`.

---

## Install from source

From a clean checkout:

```bash
cd SessionChrono.EN-v2.0.0
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Verify path resolution without starting Tkinter:

```bash
python main.py --paths
```

Run tests:

```bash
python -m unittest discover -s tests
```

### Source-run data locations

Source runs write user data into the repository checkout:

| Data | Location |
| --- | --- |
| Notes | `ChronoNotes/` |
| Application logs | `ChronoNotes/application_logs/SessionChrono_YYYY-MM-DD.log` |
| Settings | `settings/settings.json` |
| Metadata | `metadata/*.json` |
| Exports | `exports/` |

These generated directories are user data. Back them up before deleting a checkout.

---

## Portable executable

A portable build should be created with PyInstaller from the repository root. If no project-specific `.spec` file exists yet, this command is a suitable starting point for a one-folder Windows build:

```bash
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --name SessionChrono --icon SessionChrono.ico --add-data "icons;icons" --add-data "sounds;sounds" main.py
```

On macOS/Linux, PyInstaller uses `:` instead of `;` in `--add-data` values:

```bash
python -m PyInstaller --noconfirm --windowed --name SessionChrono --add-data "icons:icons" --add-data "sounds:sounds" main.py
```

Expected one-folder artifact:

```text
dist/SessionChrono/
├── SessionChrono.exe      # Windows name; platform-specific on macOS/Linux
└── _internal/             # PyInstaller runtime files and bundled resources
```

Run the executable from `dist/SessionChrono/`. Do not store user data inside the executable folder; frozen builds write to the per-user data root described below.

### Portable-build data locations

| Platform | Data root |
| --- | --- |
| Windows | `%APPDATA%\SessionChrono\` |
| macOS | `~/Library/Application Support/SessionChrono/` |
| Linux/Unix | `${XDG_DATA_HOME}/SessionChrono/` or `~/.local/share/SessionChrono/` |

Within the data root, SessionChrono uses:

```text
ChronoNotes/
ChronoNotes/application_logs/
settings/settings.json
metadata/
exports/
```

---

## Inno Setup installer

The Windows installer should wrap the PyInstaller one-folder output. A release installer is expected to:

- install the application under a normal program directory such as `{autopf}\SessionChrono`;
- include all files from `dist/SessionChrono/`;
- create Start Menu shortcuts;
- optionally create a desktop shortcut;
- register an uninstaller;
- avoid writing default user data into the installation directory.

Typical build flow after PyInstaller succeeds:

```powershell
iscc installer\SessionChrono.iss
```

If the installer script has a different path after packaging work lands, update this guide and `DEPLOY.md` together.

---

## Uninstall expectations

Uninstalling a packaged Windows build should remove installed program files and shortcuts only. It should not silently delete user data, because notes may contain important clipboard history.

Users can manually remove data after backup from:

- `%APPDATA%\SessionChrono\` on Windows;
- `~/Library/Application Support/SessionChrono/` on macOS;
- `${XDG_DATA_HOME}/SessionChrono/` or `~/.local/share/SessionChrono/` on Linux/Unix.

For source checkouts, generated data lives in `ChronoNotes/`, `settings/`, `metadata/`, and `exports/` inside the repository.

---

## Troubleshooting

### Tkinter does not open

Confirm Tkinter is available:

```bash
python -m tkinter
```

If that fails, install a Python distribution that includes Tkinter.

### Clipboard monitoring does not capture text

- Confirm monitoring is not paused (`Ctrl+P`).
- Confirm `pyperclip` is installed in the active environment.
- On Linux, ensure the desktop session has a clipboard backend compatible with `pyperclip`.

### Where did my files go?

Run:

```bash
python main.py --paths
```

For a packaged executable, check the per-user data root instead of the installation folder.
