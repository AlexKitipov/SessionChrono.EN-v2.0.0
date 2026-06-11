# SessionChrono Windows Installer

This directory contains the Inno Setup packaging script for SessionChrono v2.0.0. It wraps the PyInstaller one-folder output from `dist/SessionChrono/` into a Windows installer with Start Menu shortcuts, an optional desktop shortcut, and standard uninstall registration.

## Prerequisites

- Windows build machine or VM.
- Python environment with project dependencies installed.
- Inno Setup 6 installed, with `ISCC.exe` available from a Developer Command Prompt, PowerShell session, or its full installation path.

## Build flow

From the repository root:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm sessionchrono.spec
ISCC.exe installer\SessionChrono.iss
```

The expected installer output is:

```text
dist\installer\SessionChrono-2.0.0-Setup.exe
```

Do not commit `build/`, `dist/`, generated executables, DLLs, PYDs, manifests, or other build artifacts. Attach release binaries to a GitHub release instead.

## Uninstall and user data behavior

The installer removes installed application files and shortcuts during uninstall. It intentionally preserves `%APPDATA%\SessionChrono\`, including `ChronoNotes/`, application logs, settings, metadata, and exports, because those files may contain user-created clipboard history.

Users who want a complete data purge should back up any important notes first, uninstall the application, and then manually delete `%APPDATA%\SessionChrono\`.

## Clean Windows VM smoke test

Use a clean Windows VM or test account for release validation:

1. Build `dist\SessionChrono\` with PyInstaller.
2. Build `dist\installer\SessionChrono-2.0.0-Setup.exe` with `ISCC.exe installer\SessionChrono.iss`.
3. Run the installer and accept the license.
4. Confirm the install path defaults to `Program Files\SessionChrono`.
5. Launch SessionChrono from the Start Menu shortcut.
6. If the desktop shortcut task was selected, launch from the desktop shortcut too.
7. Copy plain text and confirm a note is saved.
8. Copy a URL and confirm it is categorized as `URL`.
9. Use search, export/ZIP, settings persistence, and log inspection workflows.
10. Uninstall from Windows Settings or Control Panel.
11. Confirm program files and shortcuts are removed.
12. Confirm `%APPDATA%\SessionChrono\` remains unless manually deleted.
