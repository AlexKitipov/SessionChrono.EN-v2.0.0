# SessionChrono Deployment Checklist

Use this checklist when preparing a v2.0.0 release. It is designed for source validation first, then PyInstaller packaging, then optional Windows installer creation. Source-only release-candidate PRs must not include generated binaries or build folders; create those artifacts only in the local release packaging environment after the source diff is clean.

---

## 1. Version and metadata checks

- [ ] Confirm the release version in `core/config.py` is correct.
- [ ] Confirm the About dialog displays the same version.
- [ ] Confirm README, installation guide, development guide, deploy checklist, and changelog mention the intended release.
- [ ] Confirm package resource and metadata files are present:
  - `SessionChrono.ico` for local Windows builds as the approved executable/installer icon
  - `icons/README.md` and `icons/.gitkeep` as text placeholders; optional approved icon source files only when provenance is documented
  - `sounds/README.md` and `sounds/.gitkeep` as text placeholders; optional approved sound source files only when provenance is documented
  - `config_templates/default_settings.json`
  - `sessionchrono.spec`
  - `version_info.txt`
- [ ] Run:

```bash
python main.py --paths
python -m core.config
```

---

## 2. Clean working tree and dependency check

- [ ] Start from a clean branch:

```bash
git status --short
```

- [ ] Recreate or refresh the virtual environment if dependency state is uncertain:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

- [ ] Run automated tests:

```bash
python -m pytest
```

---

## 3. Clean build directories

Remove stale packaging output before producing release artifacts:

```bash
rm -rf build dist
```

On Windows PowerShell:

```powershell
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
```

Do not delete user data directories (`ChronoNotes/`, `settings/`, `metadata/`, `exports/`) unless intentionally testing a first-run scenario and backups are not needed. Do not commit any regenerated `build/` or `dist/` content, binary installer output, `.exe`, `.dll`, `.pyd`, `.manifest`, bytecode, logs, or cache files.

---

## 4. PyInstaller build (local release environment only)

Install PyInstaller in the build environment through the project requirements:

```bash
python -m pip install -r requirements.txt
```

Do not run PyInstaller inside a source-only PR whose purpose is to prepare packaging metadata. After that PR is reviewed, run the source-controlled build wrapper for the current platform in the local release environment. Windows:

```bat
build.bat
```

POSIX development validation:

```bash
./build.sh
```

Equivalent direct command for CI or manual troubleshooting:

```bash
python -m PyInstaller --clean --noconfirm sessionchrono.spec
```

- [ ] Confirm `dist/SessionChrono/` exists locally.
- [ ] Review `build/SessionChrono/warn-SessionChrono.txt`. PyInstaller may still list harmless interpreter internals or unavailable POSIX modules when building on Windows, but optional Java, macOS, Qt, VMS, and legacy registry imports are intentionally excluded by `sessionchrono.spec` to keep the warning file focused on actionable entries.
- [ ] Confirm bundled resources are present in the generated output: `icons/`, `sounds/`, and `config_templates/`.
- [ ] Launch the executable.
- [ ] Confirm frozen user data is written to the per-user application data root, not the executable directory.

---

## 5. Inno Setup installer build (Windows local release environment only)

Do not run Inno Setup inside a source-only PR. After the PyInstaller one-folder build is verified in the Windows release environment:

- [ ] Confirm `installer/SessionChrono.iss` points at `dist/SessionChrono/`.
- [ ] Confirm installer metadata is correct: app name `SessionChrono`, version `2.0.0`, publisher, license file, icon, default install directory, and output filename `SessionChrono-2.0.0-Setup.exe`.
- [ ] Confirm Inno Setup 6 is installed and `ISCC.exe` is available on `PATH`, or note the full local path to `ISCC.exe`.
- [ ] Build the installer from the repository root:

```powershell
ISCC.exe installer\SessionChrono.iss
```

- [ ] Confirm the generated installer exists at `dist/installer/SessionChrono-2.0.0-Setup.exe`.
- [ ] Install on a clean Windows test machine or VM.
- [ ] Confirm the license page is shown.
- [ ] Confirm Start Menu shortcut works.
- [ ] Confirm optional desktop shortcut works if enabled.
- [ ] Confirm Windows Settings or Control Panel shows an uninstall entry.
- [ ] Confirm uninstall removes program files and shortcuts but preserves `%APPDATA%\SessionChrono\` user data.
- [ ] Confirm the preserved data behavior is included in release notes.

---

## 6. Manual smoke testing

Run this smoke test against both source and packaged builds when possible:

- [ ] Launch the app.
- [ ] Copy a plain note and confirm it appears in the history panel.
- [ ] Copy a URL and confirm it is categorized as `URL`.
- [ ] Copy code-like text and confirm it is categorized as `CODE` or another more specific category as appropriate.
- [ ] Pause monitoring with `Ctrl+P`; copy text; confirm no new entry appears.
- [ ] Resume monitoring with `Ctrl+P`; copy text; confirm capture resumes.
- [ ] Open **Tools → Entry Details**, add tags and a note, save, and reopen details.
- [ ] Open **Tools → Search Logs**, search by text, category, tag, date, and filename/title.
- [ ] Open **Tools → Export Notes...** and export TXT, JSON, CSV, Markdown, and ZIP formats.
- [ ] Use **Tools → Create ZIP of Today**.
- [ ] Open **Tools → Settings**, change a non-destructive preference, save, restart, and confirm persistence.
- [ ] Close the window and confirm no lingering app process remains.
- [ ] Inspect the daily application log for unexpected tracebacks.
- [ ] Confirm `git status --short` does not show `build/`, `dist/`, `.exe`, `.dll`, `.pyd`, `.pyc`, `.manifest`, or PyInstaller cache files.

---

## 7. Release notes and GitHub release

- [ ] Update `CHANGELOG.md` with final v2.0.0 notes.
- [ ] Commit documentation/package metadata updates with no generated binary files.
- [ ] Create an annotated tag:

```bash
git tag -a v2.0.0 -m "SessionChrono v2.0.0"
git push origin v2.0.0
```

- [ ] Create a GitHub release from the tag.
- [ ] Attach release artifacts generated outside Git, such as:
  - portable ZIP of `dist/SessionChrono/`;
  - Windows installer executable;
  - checksums file if produced.

Generated binaries are attached to the GitHub release only; they are not committed to the repository.
- [ ] Paste release highlights from `CHANGELOG.md`.
- [ ] Include data-location and uninstall notes in the release body.

---

## 8. Post-release verification

- [ ] Download artifacts from GitHub, not from the local build directory.
- [ ] Install or run downloaded artifacts.
- [ ] Repeat a short capture/search/export smoke test.
- [ ] Confirm checksums match if published.
- [ ] Confirm documentation links render correctly on GitHub.
