# SessionChrono Development Guide

This guide explains how to work on the v2.0.0 modular codebase without mixing core behavior, Tkinter presentation, and packaging concerns.

---

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py --paths
python -m unittest discover -s tests
```

Start the app:

```bash
python main.py
```

---

## Project structure

```text
core/
  app_controller.py   Application orchestration and UI-facing callbacks
  chrono.py           Clipboard polling monitor
  classifier.py       Text classification rules and confidence scores
  config.py           App metadata, resource roots, user-data paths
  export.py           TXT/JSON/CSV/Markdown/ZIP export implementation
  logger.py           Daily diagnostic logging
  metadata.py         Entry metadata sidecars, tags, notes, availability
  settings.py         Persistent settings and data-directory migration
  storage.py          Note persistence, search, ZIP/export facade
  utils.py            Filename/category compatibility helpers
ui/
  tkinter_ui.py       Main Tkinter window and menu wiring
  components.py       Editor, last copied, and history panels
  dialogs.py          Search, Settings, Export, Entry Details, About
  widgets.py          Reusable lower-level widgets
  styles.py           Theme constants and ttk styling
  sounds.py           Sound playback and fallback behavior
tests/
  test_*.py           Unit and integration coverage
main.py               CLI entry point and Tkinter startup
```

---

## Core/UI boundaries

### Core owns

- runtime path decisions;
- clipboard polling lifecycle;
- classification rules;
- filename generation;
- note persistence;
- metadata sidecars;
- search and export behavior;
- settings validation and migration;
- diagnostic logging.

### UI owns

- Tkinter window layout;
- menus and keyboard shortcuts;
- dialogs and message boxes;
- file/folder chooser interactions;
- rendering controller state into widgets;
- user-facing status messages.

### Boundary rules

- Do not place persistence policy in Tkinter widgets.
- Do not import Tkinter from `core/` modules.
- Prefer `ApplicationController` as the bridge between `ui/tkinter_ui.py` and lower-level services.
- Keep compatibility wrappers in `core/storage.py` and `core/utils.py` thin; new behavior should live in classes/services that tests can instantiate with temporary directories.
- Keep imports simple; do not wrap imports in `try`/`except` blocks.

---

## Adding classifier categories

1. Add the category to `TextCategory` in `core/classifier.py`.
2. Add weighted rules to `TextClassifier.PATTERNS`.
3. Add the category to `TextClassifier.TIE_BREAK_ORDER` where deterministic tie-breaking should place it.
4. Confirm filename/category consumers still accept the category string.
5. Add tests in `tests/test_classifier.py` for positive examples, tie behavior if relevant, and fallback behavior.
6. Run:

```bash
python -m unittest tests.test_classifier
python -m unittest discover -s tests
```

Classifier rules should be deterministic, defensive, and safe for empty, very large, or binary-like clipboard text.

---

## Adding export formats

Built-in exports are implemented in `core/export.py` and exposed through `StorageManager.export_notes()` in `core/storage.py`.

To add a first-class format:

1. Add the normalized format name to `SUPPORTED_EXPORT_FORMATS`.
2. Add or update extension handling in `normalize_export_format()` and `default_export_filename()` if needed.
3. Implement a writer method on `ChronoNotesExporter`.
4. Route the format in `ChronoNotesExporter.export()`.
5. Add a convenience wrapper on `StorageManager` if it improves call-site readability.
6. Update the Export dialog options in `ui/dialogs.py`.
7. Add tests in `tests/test_export.py` and, when routed through storage, `tests/test_storage.py`.
8. Update `README.md`, `INSTALLATION.md` if packaging implications exist, and `CHANGELOG.md`.

For experimental or plugin-like formats, `StorageManager.register_exporter()` can register a custom exporter hook without changing the built-in exporter class.

---

## Adding UI components or dialogs

### Components

Use `ui/components.py` for reusable major panels that appear in the main window, such as editor/history/preview sections. Components should expose methods/properties that `ui/tkinter_ui.py` can call without needing to know internal widget structure.

### Dialogs

Use `ui/dialogs.py` for modal or top-level dialogs. Keep these patterns:

- pass dependencies in as constructor arguments or callbacks;
- avoid direct writes to storage when a controller method should own the action;
- report user-facing errors with parented message boxes;
- log diagnostic details through `core.logger` when exceptions are caught around user actions.

### Styles and widgets

- Put theme constants and ttk configuration in `ui/styles.py`.
- Put small reusable widget classes in `ui/widgets.py`.
- Keep shortcut registration in `ui/tkinter_ui.py` unless a component has a self-contained binding.

---

## Settings and data migration

Settings are represented by `AppSettings` in `core/settings.py`. When adding a setting:

1. Add a field and default to `AppSettings`.
2. Normalize and validate it in `AppSettings.normalized()`.
3. Add controls to `SettingsDialog` if it is user-facing.
4. Apply changes through `ApplicationController.apply_settings()` when runtime behavior changes.
5. Add tests in `tests/test_settings.py` and controller tests if needed.

Data-directory changes should preserve user data. Use migration/copy behavior rather than destructive moves unless the user explicitly chooses otherwise.

---

## Running tests

Full suite:

```bash
python -m unittest discover -s tests
```

Targeted suites:

```bash
python -m unittest tests.test_app_controller
python -m unittest tests.test_classifier
python -m unittest tests.test_export
python -m unittest tests.test_metadata
python -m unittest tests.test_search
python -m unittest tests.test_settings
python -m unittest tests.test_storage
```

Path smoke checks:

```bash
python main.py --paths
python -m core.config
```

Manual Tkinter smoke test:

```bash
python main.py
```

Then copy text from another application, confirm a history entry appears, pause/resume monitoring, run a search, edit Entry Details, and export a small set of notes.

---

## Documentation updates

When changing behavior, update the relevant guide in the same PR:

- `README.md` for user-visible features and architecture summaries;
- `INSTALLATION.md` for setup, package, data-location, or uninstall changes;
- `DEVELOPMENT.md` for contributor workflows or extension points;
- `DEPLOY.md` for release process changes;
- `CHANGELOG.md` for release-note entries.
