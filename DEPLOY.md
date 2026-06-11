# SessionChrono Deployment Checklist

Use this checklist when preparing a v2.0.0 release. It is designed for source validation first, then PyInstaller packaging, then optional Windows installer creation.

---

## 1. Version and metadata checks

- [ ] Confirm the release version in `core/config.py` is correct.
- [ ] Confirm the About dialog displays the same version.
- [ ] Confirm README, installation guide, development guide, deploy checklist, and changelog mention the intended release.
- [ ] Confirm package icon/resource files are present:
  - `SessionChrono.ico`
  - `icons/`
  - `sounds/`
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
python -m unittest discover -s tests
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

Do not delete user data directories (`ChronoNotes/`, `settings/`, `metadata/`, `exports/`) unless intentionally testing a first-run scenario and backups are not needed.

---

## 4. PyInstaller build

Install PyInstaller in the build environment:

```bash
python -m pip install pyinstaller
```

If a project `.spec` file exists after packaging work lands, prefer it:

```bash
python -m PyInstaller --noconfirm SessionChrono.spec
```

If no `.spec` file exists, use a direct command. Windows one-folder example:

```bash
python -m PyInstaller --noconfirm --windowed --name SessionChrono --icon SessionChrono.ico --add-data "icons;icons" --add-data "sounds;sounds" main.py
```

macOS/Linux one-folder example:

```bash
python -m PyInstaller --noconfirm --windowed --name SessionChrono --add-data "icons:icons" --add-data "sounds:sounds" main.py
```

- [ ] Confirm `dist/SessionChrono/` exists.
- [ ] Confirm bundled resources are present in the generated output.
- [ ] Launch the executable.
- [ ] Confirm frozen user data is written to the per-user application data root, not the executable directory.

---

## 5. Inno Setup installer build (Windows)

After the PyInstaller one-folder build is verified:

- [ ] Confirm the Inno Setup script points at `dist/SessionChrono/`.
- [ ] Confirm installer metadata, version, publisher, icon, and output filename are correct.
- [ ] Build the installer:

```powershell
iscc installer\SessionChrono.iss
```

- [ ] Install on a clean Windows test machine or VM.
- [ ] Confirm Start Menu shortcut works.
- [ ] Confirm optional desktop shortcut works if enabled.
- [ ] Confirm uninstall removes program files and shortcuts but preserves `%APPDATA%\SessionChrono\` user data.

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

---

## 7. Release notes and GitHub release

- [ ] Update `CHANGELOG.md` with final v2.0.0 notes.
- [ ] Commit documentation/package metadata updates.
- [ ] Create an annotated tag:

```bash
git tag -a v2.0.0 -m "SessionChrono v2.0.0"
git push origin v2.0.0
```

- [ ] Create a GitHub release from the tag.
- [ ] Attach release artifacts, such as:
  - portable ZIP of `dist/SessionChrono/`;
  - Windows installer executable;
  - checksums file if produced.
- [ ] Paste release highlights from `CHANGELOG.md`.
- [ ] Include data-location and uninstall notes in the release body.

---

## 8. Post-release verification

- [ ] Download artifacts from GitHub, not from the local build directory.
- [ ] Install or run downloaded artifacts.
- [ ] Repeat a short capture/search/export smoke test.
- [ ] Confirm checksums match if published.
- [ ] Confirm documentation links render correctly on GitHub.
