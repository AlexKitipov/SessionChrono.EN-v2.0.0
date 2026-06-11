"""Persistent user settings for SessionChrono.

Settings are stored as JSON in the user-writable settings directory resolved by
``core.config``.  The loader is deliberately tolerant: missing files, malformed
JSON, and invalid individual values all fall back to safe defaults so the app can
continue to start.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from .config import CHRONO_NOTES_DIR, EXPORTS_DIR, SETTINGS_DIR, ensure_user_directories
from .logger import get_logger

logger = get_logger()

SETTINGS_FILENAME = "settings.json"
SETTINGS_FILE = SETTINGS_DIR / SETTINGS_FILENAME
MIN_POLL_INTERVAL_SECONDS = 0.1
MAX_POLL_INTERVAL_SECONDS = 10.0
MIN_HISTORY_ENTRIES = 1
MAX_HISTORY_ENTRIES = 500
DEFAULT_SOUND_EVENTS = {
    "start": True,
    "copy": True,
    "error": True,
    "pause": True,
    "resume": True,
    "save": True,
    "open": True,
}
THEME_DARK = "dark"
SUPPORTED_THEMES = {THEME_DARK}


@dataclass(frozen=True)
class AppSettings:
    """User-configurable application preferences."""

    start_monitoring_on_launch: bool = True
    clipboard_poll_interval: float = 0.25
    max_history_entries: int = 20
    sound_enabled: bool = True
    sound_volume: int = 100
    sound_events: dict[str, bool] = field(default_factory=lambda: DEFAULT_SOUND_EVENTS.copy())
    default_export_directory: str = field(default_factory=lambda: str(EXPORTS_DIR))
    data_directory: str = field(default_factory=lambda: str(CHRONO_NOTES_DIR))
    theme: str = THEME_DARK

    @classmethod
    def defaults(cls) -> "AppSettings":
        """Return a fresh settings object containing safe defaults."""

        return cls()

    @classmethod
    def from_mapping(cls, payload: dict[str, Any] | None) -> "AppSettings":
        """Build settings from a JSON mapping, ignoring invalid values."""

        if not isinstance(payload, dict):
            return cls.defaults()
        defaults = cls.defaults()
        known_fields = {item.name for item in fields(cls)}
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in known_fields:
                continue
            cleaned[key] = value
        candidate = cls(**{**asdict(defaults), **cleaned})
        return candidate.normalized()

    def normalized(self) -> "AppSettings":
        """Return a copy clamped to supported value ranges."""

        poll_interval = _coerce_float(
            self.clipboard_poll_interval,
            AppSettings.defaults().clipboard_poll_interval,
            MIN_POLL_INTERVAL_SECONDS,
            MAX_POLL_INTERVAL_SECONDS,
        )
        max_history = int(
            _coerce_float(
                self.max_history_entries,
                AppSettings.defaults().max_history_entries,
                MIN_HISTORY_ENTRIES,
                MAX_HISTORY_ENTRIES,
            )
        )
        volume = int(_coerce_float(self.sound_volume, 100, 0, 100))
        sound_events = DEFAULT_SOUND_EVENTS.copy()
        if isinstance(self.sound_events, dict):
            for event in sound_events:
                if event in self.sound_events:
                    sound_events[event] = bool(self.sound_events[event])
        theme = self.theme if self.theme in SUPPORTED_THEMES else THEME_DARK
        return AppSettings(
            start_monitoring_on_launch=bool(self.start_monitoring_on_launch),
            clipboard_poll_interval=poll_interval,
            max_history_entries=max_history,
            sound_enabled=bool(self.sound_enabled),
            sound_volume=volume,
            sound_events=sound_events,
            default_export_directory=_normalize_directory(self.default_export_directory, EXPORTS_DIR),
            data_directory=_normalize_directory(self.data_directory, CHRONO_NOTES_DIR),
            theme=theme,
        )

    def to_json_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable representation."""

        return asdict(self.normalized())

    def with_updates(self, **updates: Any) -> "AppSettings":
        """Return normalized settings with selected fields replaced."""

        return AppSettings.from_mapping({**self.to_json_dict(), **updates})


@dataclass(frozen=True)
class SettingsLoadResult:
    """Detailed outcome from loading persisted settings."""

    settings: AppSettings
    path: Path
    used_defaults: bool = False
    error: str | None = None


def _coerce_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        coerced = default
    return max(minimum, min(maximum, coerced))


def _normalize_directory(value: Any, default: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        value = str(default)
    return str(Path(value).expanduser())


def load_settings(path: str | os.PathLike[str] | None = None) -> SettingsLoadResult:
    """Load settings from *path* or the default settings file."""

    settings_path = Path(path).expanduser() if path is not None else SETTINGS_FILE
    if path is None:
        ensure_user_directories()
    if not settings_path.exists():
        logger.info("Settings file not found; using defaults: %s", settings_path)
        return SettingsLoadResult(AppSettings.defaults(), settings_path, used_defaults=True)
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        settings = AppSettings.from_mapping(payload)
        return SettingsLoadResult(settings, settings_path)
    except Exception as exc:
        logger.exception("Failed to load settings; using defaults: %s", settings_path)
        return SettingsLoadResult(AppSettings.defaults(), settings_path, used_defaults=True, error=str(exc))


def save_settings(settings: AppSettings, path: str | os.PathLike[str] | None = None) -> Path:
    """Atomically save settings JSON and return the destination path."""

    settings_path = Path(path).expanduser() if path is not None else SETTINGS_FILE
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.to_json_dict()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=settings_path.parent,
            delete=False,
            prefix=f".{settings_path.name}.",
            suffix=".tmp",
        ) as tmp:
            json.dump(payload, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)
        os.replace(temp_path, settings_path)
        logger.info("Saved settings: %s", settings_path)
        return settings_path
    except Exception:
        logger.exception("Failed to save settings: %s", settings_path)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def migrate_data_directory(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
    """Copy existing notes into a new data directory without deleting originals."""

    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    if source_path == destination_path or not source_path.exists():
        destination_path.mkdir(parents=True, exist_ok=True)
        return
    destination_path.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
    logger.info("Copied data directory from %s to %s", source_path, destination_path)
