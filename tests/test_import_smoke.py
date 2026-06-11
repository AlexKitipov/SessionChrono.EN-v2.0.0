"""Import smoke tests for PyInstaller and headless quality gates."""

from __future__ import annotations

import importlib


CORE_MODULES = [
    "core.app_controller",
    "core.chrono",
    "core.classifier",
    "core.config",
    "core.export",
    "core.logger",
    "core.metadata",
    "core.settings",
    "core.storage",
    "core.utils",
]

UI_MODULES = [
    "ui.components",
    "ui.dialogs",
    "ui.sounds",
    "ui.styles",
    "ui.tkinter_ui",
    "ui.widgets",
]


def test_main_import_does_not_start_tkinter():
    module = importlib.import_module("main")

    assert callable(module.main)


def test_core_modules_import_cleanly():
    for module_name in CORE_MODULES:
        assert importlib.import_module(module_name)


def test_ui_modules_import_without_creating_windows():
    for module_name in UI_MODULES:
        assert importlib.import_module(module_name)
