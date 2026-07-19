# SessionChrono Installation Guide

This guide covers three ways to run SessionChrono v2.0.0:

1. source checkout for development or power users;
2. portable executable produced with PyInstaller;
3. Windows installer produced with Inno Setup.

> This repository contains only source packaging inputs. Do not commit PyInstaller outputs such as `build/`, `dist/`, `.exe`, `.dll`, `.pyd`, bytecode, manifests, or cache files.

---

## Requirements

### Source runs

- Python 3.10 or newer is recommended.
- Tkinter must be available in the Python installation.
- Runtime dependencies from `requirements.txt`:
  - `pyperclip` on all platforms;
  - `pywin32` on Windows only;
  - `pyinstaller` for maintainers creating portable builds.

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

A portable build is created with PyInstaller from the repository root using the checked-in `sessionchrono.spec` file. The spec defines the application name (`SessionChrono`), one-folder layout, GUI/windowed mode, Windows icon, Windows version metadata from `version_info.txt`, data-resource bundling, and explicit hidden imports for clipboard, Tkinter, Windows clipboard support, and project modules.

Windows build:

```bat
build.bat
```

POSIX development-validation build:

```bash
./build.sh
```

Equivalent direct command:

```bash
python -m PyInstaller --clean --noconfirm sessionchrono.spec
```

Expected one-folder artifact:

```text
dist/SessionChrono/
├── SessionChrono.exe      # Windows name; platform-specific on macOS/Linux
└── _internal/             # PyInstaller runtime files and bundled resources
    ├── icons/             # text placeholders only unless approved assets are added
    ├── sounds/            # text placeholders only unless approved WAV files are added
    └── config_templates/
```

The v2.0.0 release candidate intentionally ships the `icons/` and `sounds/` resource directories without additional real binary assets. The repository-level `SessionChrono.ico` remains the executable and installer icon, and missing WAV files fall back to platform beeps/Tk bell behavior. These resource directory names must stay aligned with `ICONS_DIR`, `SOUNDS_DIR`, and `CONFIG_TEMPLATES_DIR` in `core.config`.

Run the executable from `dist/SessionChrono/`. Before distributing, smoke-test `python main.py --paths` in source mode and the generated executable in frozen mode to verify `core.config` resolves bundled resources and per-user writable data paths correctly. Do not store user data inside the executable folder; frozen builds write to the per-user data root described below.


### Build artifact policy

The executable, runtime libraries, compiled extension modules, PyInstaller manifests, bytecode, and all `build/` or `dist/` contents are generated artifacts. They belong in local release workspaces or GitHub release uploads only, never in source-control commits.

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

The Windows installer wraps the PyInstaller one-folder output using `installer/SessionChrono.iss`. The script configures SessionChrono v2.0.0 metadata, uses `LICENSE` as the installer license page, installs the contents of `dist/SessionChrono/`, creates Start Menu shortcuts, offers an optional desktop shortcut task, registers an uninstaller, and writes the setup executable to `dist/installer/SessionChrono-2.0.0-Setup.exe`.

Install Inno Setup 6 on a Windows build machine, then run from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm sessionchrono.spec
ISCC.exe installer\SessionChrono.iss
```

If `ISCC.exe` is not on `PATH`, call it by full path, for example:

```powershell
& "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe" installer\SessionChrono.iss
```

Expected installer artifact:

```text
dist\installer\SessionChrono-2.0.0-Setup.exe
```

The installer defaults to `{autopf}\SessionChrono`, which maps to the appropriate Program Files directory for the target Windows installation. It does not create default user data in the installation directory; frozen SessionChrono runs write notes, logs, settings, metadata, and exports under `%APPDATA%\SessionChrono\`.

See `installer/README.md` for the clean Windows VM smoke-test checklist.

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

### PyInstaller is not installed

Install dependencies in the active environment:

```bash
python -m pip install -r requirements.txt
```

Then rerun `build.bat` or `./build.sh`.

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
