"""Central application configuration and runtime path resolution.

This module is intentionally safe to import in non-GUI contexts.  It is the
single place that decides where resources are read from and where runtime data
is written for both source runs and PyInstaller-frozen builds.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

APP_NAME = "SessionChrono"
APP_VERSION = "2.0.0"
WINDOW_TITLE = "SessionChrono Notepad Smart Full Edition"
WINDOW_DEFAULT_WIDTH = 1100
WINDOW_DEFAULT_HEIGHT = 700
WINDOW_DEFAULT_GEOMETRY = f"{WINDOW_DEFAULT_WIDTH}x{WINDOW_DEFAULT_HEIGHT}"

IS_FROZEN = bool(getattr(sys, "frozen", False))
EXECUTABLE_PATH = Path(sys.executable).resolve()
EXECUTABLE_DIR = EXECUTABLE_PATH.parent
DEV_ROOT = Path(__file__).resolve().parents[1]

# PyInstaller exposes unpacked bundled files through sys._MEIPASS for one-file
# builds.  In one-folder builds, resources can also live beside the executable.
FROZEN_APP_ROOT = EXECUTABLE_DIR if IS_FROZEN else None
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", EXECUTABLE_DIR if IS_FROZEN else DEV_ROOT)).resolve()
APP_ROOT = FROZEN_APP_ROOT or DEV_ROOT
RESOURCE_ROOT = BUNDLE_ROOT if IS_FROZEN else DEV_ROOT
SOUNDS_DIR = RESOURCE_ROOT / "sounds"
ICONS_DIR = RESOURCE_ROOT / "icons"
CONFIG_TEMPLATES_DIR = RESOURCE_ROOT / "config_templates"
DEFAULT_SETTINGS_TEMPLATE = CONFIG_TEMPLATES_DIR / "default_settings.json"


def _platform_user_data_root() -> Path:
    """Return the writable per-user application data root for this platform."""

    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / APP_NAME


# Runtime storage policy:
# - Source/development runs keep using the repository's ChronoNotes directory to
#   preserve existing local data and predictable developer behavior.
# - Frozen builds use a per-user writable data directory so the executable or
#   PyInstaller bundle directory is never required to be writable.
USER_DATA_ROOT = _platform_user_data_root() if IS_FROZEN else DEV_ROOT
CHRONO_NOTES_DIR = USER_DATA_ROOT / "ChronoNotes"
LOG_ROOT = CHRONO_NOTES_DIR
SETTINGS_DIR = USER_DATA_ROOT / "settings"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
METADATA_DIR = USER_DATA_ROOT / "metadata"
EXPORTS_DIR = USER_DATA_ROOT / "exports"


def ensure_user_directories() -> None:
    """Create runtime directories used for user-writable application data."""

    for directory in (
        CHRONO_NOTES_DIR,
        SETTINGS_DIR,
        METADATA_DIR,
        EXPORTS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def resolve_resource_path(*parts: str) -> Path:
    """Resolve a read-only bundled resource path under the resource root."""

    return RESOURCE_ROOT.joinpath(*parts)


def runtime_path_report() -> dict[str, Any]:
    """Return a JSON-serializable report for path-resolution smoke checks."""

    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "is_frozen": IS_FROZEN,
        "executable_path": str(EXECUTABLE_PATH),
        "app_root": str(APP_ROOT),
        "dev_root": str(DEV_ROOT),
        "bundle_root": str(BUNDLE_ROOT),
        "resource_root": str(RESOURCE_ROOT),
        "sounds_dir": str(SOUNDS_DIR),
        "icons_dir": str(ICONS_DIR),
        "config_templates_dir": str(CONFIG_TEMPLATES_DIR),
        "default_settings_template": str(DEFAULT_SETTINGS_TEMPLATE),
        "user_data_root": str(USER_DATA_ROOT),
        "chrono_notes_dir": str(CHRONO_NOTES_DIR),
        "log_root": str(LOG_ROOT),
        "settings_dir": str(SETTINGS_DIR),
        "settings_file": str(SETTINGS_FILE),
        "metadata_dir": str(METADATA_DIR),
        "exports_dir": str(EXPORTS_DIR),
    }


def print_runtime_path_report() -> None:
    """Print the current runtime path configuration as formatted JSON."""

    print(json.dumps(runtime_path_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    print_runtime_path_report()
