# SessionChrono v2.0.0 Pull Request Roadmap

This roadmap translates the repository's existing `SessionChrono v2.0.0 Development Plan.md` into an ordered pull-request sequence. It is intentionally limited to planning: no production code is included here.

## Repository Baseline Used for This Roadmap

- Current entry point: `main.py` imports `start_app` from `ui.tkinter_ui`.
- Current core modules: `core/chrono.py`, `core/storage.py`, and `core/utils.py`.
- Current UI module: one large Tkinter file, `ui/tkinter_ui.py`, containing the sound manager, context menu, main window, editor, clipboard history, search dialog, ZIP creation, and app launcher.
- Current runtime output directory: `ChronoNotes/` is created from `core/utils.py` at repository/runtime root.
- Existing development plan requests the modular architecture `core/`, `ui/`, `sounds/`, and runtime `ChronoNotes/`, plus PyInstaller packaging, installer creation, classifier expansion, UI modularization, tests, and documentation.
- Packaging note: the included plan mentions an NSIS installer script, but this roadmap follows the user requirement to support installer creation with **Inno Setup**.

---

## PR 1 — Foundation: Package Boundaries, Runtime Paths, and Resource Configuration

### PR title
`refactor: centralize app configuration and runtime paths`

### Purpose / problem it solves
The current application mixes path decisions across modules, which makes local execution and PyInstaller execution fragile. This PR establishes one authoritative configuration layer for application metadata, runtime data, resources, and packaged-app path resolution.

### Detailed implementation steps
1. Add package initialization files so `core` and `ui` behave consistently as importable modules.
2. Create a central configuration module with:
   - App name and version.
   - Window defaults.
   - Development root detection.
   - PyInstaller frozen-app root detection using `sys.frozen` and `sys.executable`.
   - Resource directory paths for `sounds/` and future `icons/`.
   - User-data directory paths for `ChronoNotes/`, logs, settings, metadata, and exports.
3. Decide and document the runtime storage policy:
   - Use a user-writable directory for packaged builds.
   - Keep a predictable local development directory for source runs if desired.
4. Update existing path consumers to depend on the central configuration module instead of deriving paths independently.
5. Preserve compatibility with existing `ChronoNotes/` data where possible, or document migration behavior.
6. Add a small path-resolution smoke check that can be run without opening Tkinter.

### Files to create, modify, or delete
- Create:
  - `core/__init__.py`
  - `ui/__init__.py`
  - `core/config.py`
  - `icons/.gitkeep` or equivalent placeholder if no icon asset exists yet
  - `sounds/.gitkeep` or equivalent placeholder if no WAV assets exist yet
- Modify:
  - `main.py`
  - `core/utils.py`
  - `core/storage.py`
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None in this PR.

### Dependencies on other PRs
None. This is the first foundation PR.

### Testing steps
- Local Tkinter run:
  - Run `python main.py` from the repository root.
  - Verify the window opens.
  - Copy text and confirm it is saved under the configured `ChronoNotes/` location.
  - Use “Open Logs Folder” and confirm it opens the configured location.
- PyInstaller compatibility:
  - Run a temporary one-file or one-folder PyInstaller build after installing PyInstaller.
  - Launch the built executable.
  - Confirm the app does not attempt to write inside the bundled executable directory unless that directory is intended and writable.
  - Confirm resource paths resolve without traceback when `sounds/` is empty.

### Expected outcome
SessionChrono has stable module boundaries and centralized path/resource configuration that works in both source and frozen executable contexts.

---

## PR 2 — Observability: Application Logging and Error Reporting Foundation

### PR title
`feat: add application logging infrastructure`

### Purpose / problem it solves
The current application handles many exceptions silently or only shows status-bar messages. Production-ready packaging requires persistent logs for diagnosing clipboard, storage, UI, and build issues.

### Detailed implementation steps
1. Add an application logger module with a single configured logger.
2. Write daily log files to the configured user-writable logs directory.
3. Log startup, shutdown, clipboard monitor lifecycle, save/load actions, search failures, ZIP creation, and sound playback fallback decisions.
4. Replace broad silent exception handling in core modules with logged exceptions where safe.
5. Keep UI-friendly messages concise while preserving full tracebacks in logs for diagnostics.
6. Document where logs are stored.

### Files to create, modify, or delete
- Create:
  - `core/logger.py`
- Modify:
  - `core/chrono.py`
  - `core/storage.py`
  - `core/utils.py`
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 1.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Copy a text item.
  - Pause/resume monitoring.
  - Create a ZIP.
  - Confirm log entries are written to the configured log file.
- PyInstaller compatibility:
  - Build and launch the executable.
  - Trigger the same actions.
  - Confirm log files are created in a user-writable directory and not inside a read-only bundle.

### Expected outcome
Operational failures become diagnosable through persistent logs without overwhelming the Tkinter interface.

---

## PR 3 — Core Classifier: Advanced Multi-Pattern Text Classification

### PR title
`feat: implement advanced clipboard text classifier`

### Purpose / problem it solves
The current classifier is a simple keyword check in `core/utils.py`. The v2.0.0 plan calls for a modular advanced classifier that can identify multiple content types and provide confidence scoring.

### Detailed implementation steps
1. Create a dedicated classifier module.
2. Define a category enum or equivalent constants for:
   - `URL`
   - `CODE`
   - `MARKDOWN`
   - `JSON`
   - `XML`
   - `SQL`
   - `TRACEBACK`
   - `TODO`
   - `CHAT`
   - `LOG`
   - `NOTE`
3. Implement pattern-based scoring rather than first-match-only classification.
4. Add confidence scoring and deterministic tie-breaking.
5. Handle empty, whitespace-only, very large, and binary-like clipboard strings safely.
6. Preserve a compatibility wrapper if existing callers still expect `classify_text(text) -> str`.
7. Add unit tests for every category and confidence behavior.

### Files to create, modify, or delete
- Create:
  - `core/classifier.py`
  - `tests/test_classifier.py`
- Modify:
  - `core/utils.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 1. Benefits from PR 2 for logging but can be developed after PR 1 if needed.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Copy representative samples for URL, Python code, JSON, SQL, Markdown, TODO text, traceback text, chat transcript text, and plain notes.
  - Confirm saved files appear in the expected category folders.
- PyInstaller compatibility:
  - Build the executable.
  - Repeat a reduced classification smoke test with URL, code, JSON, and plain note samples.
  - Confirm classifier imports are included in the bundle.
- Automated tests:
  - Run the classifier test suite.

### Expected outcome
Clipboard items are categorized more accurately, classification logic is isolated from filename/path construction, and classifier behavior is covered by tests.

---

## PR 4 — Storage Layer: StorageManager, Safer File Operations, Search, ZIP, and Export Hooks

### PR title
`refactor: introduce storage manager with robust file operations`

### Purpose / problem it solves
Storage is currently a small set of global functions. A production-ready app needs safer writes, logged errors, testability with temporary directories, search APIs, ZIP creation, and future export integration points.

### Detailed implementation steps
1. Introduce a `StorageManager` class initialized with a configurable base directory.
2. Keep backward-compatible function wrappers for UI code until the UI refactor consumes the class directly.
3. Make save operations create parent directories and return clear success/failure results.
4. Make load operations handle missing and unreadable files gracefully.
5. Keep ZIP creation for daily notes and ensure relative archive paths are correct.
6. Add search APIs that return structured results rather than only raw paths where practical.
7. Add extension points for later JSON/CSV/Markdown export.
8. Add integration tests using temporary directories.

### Files to create, modify, or delete
- Create:
  - `tests/test_storage.py`
- Modify:
  - `core/storage.py`
  - `core/utils.py`
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 1 and PR 2. Should come after PR 3 if filename construction is already classifier-driven.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Save a manual note.
  - Copy text and confirm automatic save.
  - Open the last auto-note.
  - Search logs.
  - Create ZIP of today.
- PyInstaller compatibility:
  - Build and run the executable.
  - Confirm automatic save, search, and ZIP creation work from the executable.
- Automated tests:
  - Run storage tests against temporary directories.

### Expected outcome
File persistence becomes reliable, testable, and ready for metadata/export features without breaking the current UI.

---

## PR 5 — UI Foundation: Styles, Reusable Widgets, Menus, and Sound Module

### PR title
`feat: add reusable Tkinter styles, widgets, and sound manager`

### Purpose / problem it solves
The current UI module contains styling, widgets, right-click behavior, sound playback, and application logic in one file. This PR extracts reusable UI foundations while keeping the visible app behavior stable.

### Detailed implementation steps
1. Create centralized theme/style constants for the dark UI.
2. Move style setup into a dedicated function or class.
3. Extract reusable widgets:
   - Scrollable text editor/preview widget.
   - Clipboard history list component.
   - Status bar component.
   - Right-click context menu.
4. Move sound playback into its own module under `ui/` or a dedicated `sounds` integration module.
5. Ensure sound fallback behavior still works when WAV files are absent.
6. Ensure all reusable UI modules import paths from `core.config`.
7. Leave `SessionChronoUI` in place but slim it down by consuming the extracted components.

### Files to create, modify, or delete
- Create:
  - `ui/styles.py`
  - `ui/widgets.py`
  - `ui/sounds.py`
- Modify:
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 1 and PR 2.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Verify dark theme styling remains consistent.
  - Verify right-click copy/cut/paste/select-all/clear works in editor and preview.
  - Verify status bar messages still update.
  - Verify sound fallback uses WAV files if available and bell/beep if not.
- PyInstaller compatibility:
  - Build and launch the executable.
  - Verify missing optional WAV files do not crash the app.
  - If WAV files are included, verify they are bundled and playable.

### Expected outcome
UI basics become reusable and maintainable while the application remains functionally equivalent.

---

## PR 6 — UI Dialogs and Components: Search, About, Settings Shell, History Details

### PR title
`feat: modularize Tkinter dialogs and side-panel components`

### Purpose / problem it solves
Search results, about information, and future settings need dedicated dialogs rather than ad hoc `Toplevel` construction inside the main window. This PR prepares the UI for feature growth.

### Detailed implementation steps
1. Create a dialogs module for:
   - About dialog.
   - Search prompt/results dialog.
   - Error/info helpers.
   - Settings dialog shell.
   - Entry details/properties dialog shell.
2. Create a components module for higher-level UI sections:
   - Editor panel.
   - Last copied panel.
   - Clipboard history panel.
   - Toolbar or action strip if desired.
3. Move search-results behavior out of `SessionChronoUI` into a dialog class/function.
4. Add keyboard shortcuts for common actions where appropriate:
   - New.
   - Open.
   - Save.
   - Search.
   - Pause/resume monitoring.
5. Keep layout and behavior stable while reducing main-window responsibilities.

### Files to create, modify, or delete
- Create:
  - `ui/dialogs.py`
  - `ui/components.py`
- Modify:
  - `ui/tkinter_ui.py`
  - `ui/widgets.py`
  - `ui/styles.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 5. Benefits from PR 4 for cleaner search APIs.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Open About.
  - Search logs and open a selected result.
  - Confirm keyboard shortcuts work.
  - Confirm history selection still loads content into the editor.
- PyInstaller compatibility:
  - Build and launch the executable.
  - Open every dialog at least once.
  - Confirm no dialog imports or resources are missing from the bundle.

### Expected outcome
Dialog and component code is modular, making future settings, metadata, and export UI work safe to implement.

---

## PR 7 — Main Window Refactor: Application Controller and Clipboard Monitor Lifecycle

### PR title
`refactor: separate application controller from Tkinter window`

### Purpose / problem it solves
The current main window directly manages clipboard monitoring, persistence, history, UI updates, sounds, and file operations. This makes pause/resume behavior and future tests brittle. This PR creates a controller boundary between core behavior and the Tkinter view.

### Detailed implementation steps
1. Introduce an application/controller layer responsible for:
   - Starting and stopping the clipboard monitor.
   - Receiving clipboard text events.
   - Building filenames.
   - Saving clipboard entries.
   - Updating in-memory session history.
   - Coordinating storage, classifier, metadata, and logger services.
2. Ensure pause/resume does not attempt to restart an already-consumed thread incorrectly.
3. Make clipboard monitor lifecycle explicit and idempotent.
4. Keep UI callbacks thin and focused on rendering state.
5. Add startup/shutdown logging.
6. Preserve `main.py` as the source and PyInstaller entry point.

### Files to create, modify, or delete
- Create:
  - `app.py` or `core/app_controller.py`
- Modify:
  - `main.py`
  - `core/chrono.py`
  - `ui/tkinter_ui.py`
  - `ui/components.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 4, PR 5, and PR 6.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Copy several clipboard items.
  - Pause monitoring and copy text; confirm no new entry is saved.
  - Resume monitoring and copy text; confirm saving resumes.
  - Close the app and confirm the monitor stops without hanging.
- PyInstaller compatibility:
  - Build and run the executable.
  - Repeat pause/resume and close behavior.
  - Confirm no background thread prevents executable shutdown.

### Expected outcome
The main window is no longer a monolith, clipboard monitoring is lifecycle-safe, and the app is easier to test and package.

---

## PR 8 — Metadata and Tagging: Entry Records, Notes, Tags, and Indexing

### PR title
`feat: add metadata and tagging for clipboard entries`

### Purpose / problem it solves
The v2.0.0 plan calls for a richer clipboard-logging application, not just text files. Metadata allows the app to track categories, source timestamps, titles, tags, annotations, and future export/search behavior.

### Detailed implementation steps
1. Create a metadata manager that stores sidecar metadata in JSON.
2. Define metadata fields:
   - Entry ID.
   - File path.
   - Created timestamp.
   - Category.
   - Title/short title.
   - Text length.
   - Classifier confidence.
   - User tags.
   - Optional note/annotation.
3. Save metadata whenever a clipboard item is persisted.
4. Add APIs to load, update, and search metadata.
5. Add UI affordances through existing dialogs/components:
   - View entry details.
   - Add/edit tags.
   - Add/edit annotation.
6. Keep metadata resilient if the text file is moved, missing, or unreadable.
7. Add tests for metadata create/update/search behavior.

### Files to create, modify, or delete
- Create:
  - `core/metadata.py`
  - `tests/test_metadata.py`
- Modify:
  - `core/storage.py`
  - `core/utils.py`
  - `app.py` or `core/app_controller.py`
  - `ui/dialogs.py`
  - `ui/components.py`
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 7. Benefits from PR 3 confidence scoring.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Copy an item.
  - Open entry details.
  - Add tags and an annotation.
  - Restart the app and confirm metadata persists.
- PyInstaller compatibility:
  - Build and run the executable.
  - Add metadata to a clipboard entry.
  - Confirm metadata JSON is written to the configured user data directory.
- Automated tests:
  - Run metadata tests.

### Expected outcome
Each clipboard entry has structured metadata that can power filtering, export, and a more complete user experience.

---

## PR 9 — Search, Filters, and History UX Enhancements

### PR title
`feat: add category, tag, date, and text filters to history search`

### Purpose / problem it solves
Basic full-text search is not enough once categories and metadata exist. Users need practical ways to find clipboard entries by category, date, tag, and text.

### Detailed implementation steps
1. Extend search APIs to combine:
   - Full-text query.
   - Category filter.
   - Date range filter.
   - Tag filter.
   - Filename/title filter.
2. Update the search dialog with filter controls.
3. Update the history panel to display category and timestamp clearly.
4. Add “open containing folder” and “copy path” actions for entries.
5. Add safe handling for missing files in search results.
6. Add tests for filtered search behavior.

### Files to create, modify, or delete
- Create:
  - `tests/test_search.py`
- Modify:
  - `core/storage.py`
  - `core/metadata.py`
  - `ui/dialogs.py`
  - `ui/components.py`
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 8.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Create entries in multiple categories.
  - Add tags to some entries.
  - Search by free text, category, date, and tag.
  - Open a selected result from the search dialog.
- PyInstaller compatibility:
  - Build and run the executable.
  - Confirm filter widgets render correctly and filtered search works.
- Automated tests:
  - Run search/filter tests.

### Expected outcome
Users can reliably locate clipboard history using structured filters and improved history presentation.

---

## PR 10 — Export Features: TXT, JSON, CSV, Markdown, and ZIP Improvements

### PR title
`feat: add multi-format export for ChronoNotes`

### Purpose / problem it solves
The current app can create a daily ZIP. v2.0.0 requires production-ready export options that use text files and metadata to generate shareable archives and reports.

### Detailed implementation steps
1. Create an export module with export services for:
   - Plain text bundle.
   - JSON export with metadata.
   - CSV summary.
   - Markdown report.
   - ZIP archive including text files and metadata.
2. Add date-range and category-filtered export support.
3. Add UI export dialog with format and filter options.
4. Ensure exported files are written to the configured exports directory by default.
5. Preserve current “Create ZIP of Today” behavior, but route it through the export service.
6. Add tests for each export format using temporary directories.

### Files to create, modify, or delete
- Create:
  - `core/export.py`
  - `tests/test_export.py`
- Modify:
  - `core/storage.py`
  - `core/metadata.py`
  - `ui/dialogs.py`
  - `ui/tkinter_ui.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 8. Benefits from PR 9 for reusable filter criteria.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Create several entries.
  - Export TXT, JSON, CSV, Markdown, and ZIP.
  - Open each export and verify content and metadata are included correctly.
- PyInstaller compatibility:
  - Build and run the executable.
  - Create each export format from the executable.
  - Confirm export files are written outside the bundled app directory.
- Automated tests:
  - Run export tests.

### Expected outcome
Users can export clipboard history in practical formats, and the existing ZIP feature becomes part of a coherent export system.

---

## PR 11 — Settings and Preferences: Persistent User Configuration

### PR title
`feat: add persistent settings and preferences dialog`

### Purpose / problem it solves
Production users need control over app behavior without editing code. This PR adds persistent settings and exposes them through the UI.

### Detailed implementation steps
1. Add a settings model and persistence module.
2. Store settings in a user-writable JSON file.
3. Support preferences for:
   - Start monitoring on launch.
   - Clipboard polling interval.
   - Maximum in-session history entries.
   - Sound enabled/disabled.
   - Sound volume or event toggles where feasible.
   - Default export directory.
   - Default data directory display/migration controls where safe.
   - Theme option reserved for future themes, while keeping dark theme default.
4. Complete the settings dialog created earlier.
5. Wire settings into clipboard monitor, sound manager, storage/export defaults, and UI startup.
6. Add tests for settings load/save/default fallback behavior.

### Files to create, modify, or delete
- Create:
  - `core/settings.py`
  - `tests/test_settings.py`
- Modify:
  - `core/config.py`
  - `core/chrono.py`
  - `ui/dialogs.py`
  - `ui/sounds.py`
  - `ui/tkinter_ui.py`
  - `app.py` or `core/app_controller.py`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 7. Benefits from PR 10 for export directory settings.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Open settings.
  - Disable sounds and verify actions no longer play audio.
  - Change max history entries and verify history length.
  - Restart and confirm settings persist.
- PyInstaller compatibility:
  - Build and run the executable.
  - Change settings, restart executable, and confirm persistence.
- Automated tests:
  - Run settings tests.

### Expected outcome
User preferences persist across sessions and core behavior becomes configurable without code changes.

---

## PR 12 — Documentation Refresh: User, Developer, Architecture, and Installation Guides

### PR title
`docs: add v2.0.0 user, developer, and installation documentation`

### Purpose / problem it solves
The current README is short and does not fully explain the modular architecture, usage flows, packaging process, or installer process. This PR creates release-grade documentation.

### Detailed implementation steps
1. Expand README with:
   - Product overview.
   - Feature list.
   - Architecture overview.
   - Local run instructions.
   - Screenshot placeholders if needed.
   - User data and logs locations.
2. Add installation guide covering:
   - Source install.
   - Portable executable.
   - Inno Setup installer.
   - Uninstall expectations.
3. Add developer guide covering:
   - Project structure.
   - Core/UI boundaries.
   - Adding classifier categories.
   - Adding export formats.
   - Adding UI components/dialogs.
   - Running tests.
4. Add deployment checklist covering:
   - Version checks.
   - Clean build.
   - PyInstaller build.
   - Installer build.
   - Manual smoke testing.
   - GitHub release/tag steps.
5. Add changelog or release notes skeleton for v2.0.0.

### Files to create, modify, or delete
- Create:
  - `INSTALLATION.md`
  - `DEVELOPMENT.md`
  - `DEPLOY.md`
  - `CHANGELOG.md`
- Modify:
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Should be started after PR 1 and finalized after PR 11 so docs match implemented behavior.

### Testing steps
- Local Tkinter run:
  - Follow the documented source-run steps on a clean checkout.
  - Confirm `python main.py` works as documented.
- PyInstaller compatibility:
  - Follow the documented executable-build steps once PR 13 lands.
  - Confirm documentation accurately describes generated artifacts and paths.
- Documentation checks:
  - Verify every documented file path exists.
  - Verify every documented command is current.

### Expected outcome
Users and contributors have clear, release-ready instructions for using, developing, building, and releasing SessionChrono.

---

## PR 13 — Test Suite and Quality Gates

### PR title
`test: add automated quality gates for core modules`

### Purpose / problem it solves
The development plan requires quality assurance. Before packaging, the app needs a repeatable automated test suite for classifier, storage, metadata, search, export, settings, and import health.

### Detailed implementation steps
1. Add a test runner configuration, preferably `pytest` unless the project intentionally stays with `unittest`.
2. Add or consolidate tests for:
   - Classifier behavior.
   - Filename/path building.
   - Storage save/load/search/ZIP.
   - Metadata persistence.
   - Search filters.
   - Export formats.
   - Settings defaults and persistence.
3. Add import smoke tests for `main.py`, core modules, and UI modules without starting Tkinter where possible.
4. Add linting or formatting configuration if the project adopts it.
5. Document the expected test commands.
6. Ensure tests do not write to real user `ChronoNotes/` directories.

### Files to create, modify, or delete
- Create:
  - `tests/`
  - `tests/conftest.py`
  - Test files for core modules as listed above
  - Optional `pytest.ini` or `pyproject.toml` test configuration
- Modify:
  - `requirements.txt`
  - `DEVELOPMENT.md`
  - `README.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PRs 3, 4, 8, 9, 10, and 11 for full coverage. Some tests can be introduced earlier within their respective feature PRs.

### Testing steps
- Local Tkinter run:
  - Run automated tests first.
  - Then run `python main.py` for a manual smoke test.
- PyInstaller compatibility:
  - Run import smoke tests before building.
  - Build the executable after tests pass.
  - Launch executable for manual smoke test.
- Automated tests:
  - Run the full test suite from a clean checkout.

### Expected outcome
The repository has repeatable quality gates that reduce regressions before packaging and release.

---

## PR 14 — PyInstaller Packaging: Spec, Build Scripts, and Resource Bundling

### PR title
`build: add PyInstaller packaging for SessionChrono`

### Purpose / problem it solves
The app must be distributable as an executable. This PR adds PyInstaller configuration, resource bundling, clean-build scripts, and executable smoke-test instructions.

### Detailed implementation steps
1. Add a PyInstaller spec generation script or checked-in `.spec` file.
2. Include data resources:
   - `sounds/`
   - `icons/`
   - Any default configuration templates.
3. Include hidden imports needed by clipboard, Tkinter, PyInstaller, Windows clipboard support, and project modules.
4. Add Windows build script.
5. Add POSIX build script for development validation where feasible.
6. Ensure the executable name, icon, version metadata, and dist layout are defined.
7. Confirm source and frozen runtime paths both work through `core.config`.
8. Document known platform requirements.

### Files to create, modify, or delete
- Create:
  - `build_spec.py` or `sessionchrono.spec`
  - `build.bat`
  - `build.sh`
  - Optional `version_info.txt`
- Modify:
  - `requirements.txt`
  - `README.md`
  - `INSTALLATION.md`
  - `DEPLOY.md`
- Delete:
  - None.

### Dependencies on other PRs
Depends on PR 1 and should land after the main feature/module layout stabilizes, ideally after PR 13.

### Testing steps
- Local Tkinter run:
  - Run `python main.py` before packaging to confirm source mode still works.
- PyInstaller compatibility:
  - Clean previous `build/` and `dist/` directories.
  - Run the build script.
  - Launch the generated executable.
  - Copy text and confirm auto-save.
  - Open logs folder.
  - Search logs.
  - Export or ZIP notes.
  - Close and confirm clean shutdown.

### Expected outcome
A reproducible PyInstaller build creates a working SessionChrono executable with required resources bundled and user data written to safe locations.

---

## PR 15 — Inno Setup Installer: Windows Installer, Shortcuts, Uninstall, and Smoke Test

### PR title
`build: add Inno Setup installer for Windows distribution`

### Purpose / problem it solves
The user requirement explicitly calls for installer creation via Inno Setup. This PR packages the PyInstaller output into a Windows installer with shortcuts and uninstall support.

### Detailed implementation steps
1. Add an `installer/` directory.
2. Create an Inno Setup script for SessionChrono.
3. Configure installer metadata:
   - App name.
   - Version `2.0.0`.
   - Publisher.
   - Default installation directory.
   - License file.
   - Output filename.
4. Include PyInstaller `dist/` artifacts.
5. Add Start Menu shortcut.
6. Add optional desktop shortcut task.
7. Add uninstall behavior.
8. Decide whether user data in `ChronoNotes/` remains after uninstall and document the behavior.
9. Add build instructions for `ISCC.exe`.
10. Add installer smoke-test checklist for a clean Windows VM.

### Files to create, modify, or delete
- Create:
  - `installer/SessionChrono.iss`
  - Optional `installer/README.md`
- Modify:
  - `INSTALLATION.md`
  - `DEPLOY.md`
  - `README.md`
- Delete:
  - Do not create or keep NSIS-only installer files unless explicitly retained as unsupported alternatives.

### Dependencies on other PRs
Depends on PR 14.

### Testing steps
- Local Tkinter run:
  - Run `python main.py` before building to verify source still works.
- PyInstaller compatibility:
  - Build the PyInstaller executable.
  - Run the executable directly from `dist/`.
  - Build the Inno Setup installer with `ISCC installer/SessionChrono.iss`.
  - Install on a clean Windows environment.
  - Launch from Start Menu and optional desktop shortcut.
  - Copy text and verify saving, search, export/ZIP, settings persistence, and logs.
  - Uninstall and verify app binaries are removed and user data behavior matches documentation.

### Expected outcome
SessionChrono can be distributed as a Windows installer generated by Inno Setup from the PyInstaller build output.

---

## PR 16 — Final Release Hardening: Assets, Cleanup, Versioning, and v2.0.0 Release Candidate

### PR title
`release: prepare SessionChrono v2.0.0 release candidate`

### Purpose / problem it solves
Before final release, the repository needs cleanup, consistent versioning, release notes, asset validation, build validation, and removal of obsolete artifacts.

### Detailed implementation steps
1. Ensure version `2.0.0` is consistent in:
   - `core/config.py`
   - README.
   - Installer script.
   - PyInstaller metadata.
   - Changelog.
2. Add or finalize icons and optional WAV assets.
3. Remove committed runtime artifacts and caches.
4. Add or update `.gitignore` for:
   - `__pycache__/`
   - build outputs.
   - dist outputs.
   - temporary logs.
   - local `ChronoNotes/` if runtime data should not be committed.
5. Validate `.bak` files and delete them if they are obsolete.
6. Run the full test suite.
7. Run local Tkinter smoke test.
8. Run PyInstaller build smoke test.
9. Run Inno Setup installer smoke test.
10. Update release notes and deployment checklist.
11. Prepare release tag instructions.

### Files to create, modify, or delete
- Create:
  - Optional finalized assets under `icons/` and `sounds/`
- Modify:
  - `.gitignore`
  - `README.md`
  - `CHANGELOG.md`
  - `DEPLOY.md`
  - `core/config.py`
  - `installer/SessionChrono.iss`
  - PyInstaller spec/build metadata files
- Delete:
  - `core/__pycache__/` committed files
  - `ui/__pycache__/` committed files
  - Obsolete `.bak` files such as `core/storage.py.bak` and `ui/tkinter_ui.py.bak` if confirmed unnecessary
  - Any accidental build artifacts

### Dependencies on other PRs
Depends on all previous PRs.

### Testing steps
- Local Tkinter run:
  - Run `python main.py`.
  - Exercise clipboard logging, pause/resume, history, search, metadata/tags, settings, export, ZIP, and shutdown.
- PyInstaller compatibility:
  - Run a clean PyInstaller build.
  - Launch executable and repeat critical smoke tests.
- Inno Setup compatibility:
  - Build installer.
  - Install on a clean Windows environment.
  - Repeat critical smoke tests.
  - Uninstall and verify documented cleanup behavior.
- Automated tests:
  - Run the full test suite from a clean checkout.

### Expected outcome
The repository is clean, versioned, documented, tested, packaged, installer-ready, and ready for a v2.0.0 release tag.

---

## Recommended Merge Order

1. PR 1 — Foundation configuration and paths.
2. PR 2 — Logging.
3. PR 3 — Advanced classifier.
4. PR 4 — Storage manager.
5. PR 5 — UI styles/widgets/sounds.
6. PR 6 — Dialogs/components.
7. PR 7 — Controller and monitor lifecycle.
8. PR 8 — Metadata/tagging.
9. PR 9 — Search and filters.
10. PR 10 — Exports.
11. PR 11 — Settings.
12. PR 12 — Documentation refresh.
13. PR 13 — Test suite and quality gates.
14. PR 14 — PyInstaller packaging.
15. PR 15 — Inno Setup installer.
16. PR 16 — Final release hardening.

## Cross-PR Acceptance Criteria

Every implementation PR should satisfy the following before merge:

- Source run still works with `python main.py` unless the PR is documentation-only.
- Clipboard monitoring can be started and stopped cleanly.
- Clipboard text can be saved to `ChronoNotes/` or the configured data directory.
- No new hard-coded absolute paths are introduced.
- New user-writable data goes through `core.config`.
- New core behavior has automated tests where practical.
- New UI behavior has a manual Tkinter smoke test.
- PyInstaller compatibility is considered for imports, resources, and writable paths.
- Documentation is updated when user-facing behavior changes.

## Minimal Final Release Smoke-Test Matrix

| Area | Source run | PyInstaller EXE | Inno Setup install |
| --- | --- | --- | --- |
| Launch app | Required | Required | Required |
| Clipboard auto-save | Required | Required | Required |
| Category classification | Required | Required | Required |
| Pause/resume monitor | Required | Required | Required |
| Open logs folder | Required | Required | Required |
| Search/filter entries | Required | Required | Required |
| Edit and save note | Required | Required | Required |
| Metadata/tags | Required | Required | Required |
| Export TXT/JSON/CSV/Markdown/ZIP | Required | Required | Required |
| Settings persistence | Required | Required | Required |
| Sound fallback | Required | Required | Required |
| Clean shutdown | Required | Required | Required |
| Uninstall behavior | Not applicable | Not applicable | Required |
