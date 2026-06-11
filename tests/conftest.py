"""Pytest quality-gate fixtures and test runtime isolation."""

from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path

_TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="sessionchrono-tests-"))


def pytest_configure(config):
    """Route default app runtime paths to a disposable test directory.

    Several modules configure logging at import time, so this hook patches
    ``core.config`` before pytest imports test modules that depend on storage,
    settings, logger, or UI modules. Tests that exercise persistence still use
    their own ``TemporaryDirectory`` instances, while any default-path fallback
    stays outside the repository and outside real user ``ChronoNotes`` folders.
    """

    from core import config as app_config

    app_config.USER_DATA_ROOT = _TEST_RUNTIME_ROOT
    app_config.CHRONO_NOTES_DIR = _TEST_RUNTIME_ROOT / "ChronoNotes"
    app_config.LOG_ROOT = app_config.CHRONO_NOTES_DIR
    app_config.SETTINGS_DIR = _TEST_RUNTIME_ROOT / "settings"
    app_config.SETTINGS_FILE = app_config.SETTINGS_DIR / "settings.json"
    app_config.METADATA_DIR = _TEST_RUNTIME_ROOT / "metadata"
    app_config.EXPORTS_DIR = _TEST_RUNTIME_ROOT / "exports"


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TEST_RUNTIME_ROOT, ignore_errors=True)


atexit.register(lambda: shutil.rmtree(_TEST_RUNTIME_ROOT, ignore_errors=True))
