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
MIN_SOUND_VOLUME = 0
MAX_SOUND_VOLUME = 100
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

        defaults = AppSettings.defaults()
        poll_interval = parse_poll_interval(
            self.clipboard_poll_interval,
            default=defaults.clipboard_poll_interval,
        )
        max_history = parse_history_limit(
            self.max_history_entries,
            default=defaults.max_history_entries,
        )
        volume = parse_sound_volume(self.sound_volume, default=defaults.sound_volume)
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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def parse_poll_interval(value: Any, *, default: float | None = None) -> float:
    """Parse and clamp a clipboard polling interval in seconds.

    Invalid text raises ``ValueError`` unless *default* is provided, which lets
    settings-file loading normalize predictably while UI text entry can report a
    field-specific error.
    """

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        if default is None:
            raise ValueError(
                f"Clipboard polling interval must be a number between "
                f"{MIN_POLL_INTERVAL_SECONDS:g} and {MAX_POLL_INTERVAL_SECONDS:g} seconds."
            ) from exc
        parsed = float(default)
    return _clamp(parsed, MIN_POLL_INTERVAL_SECONDS, MAX_POLL_INTERVAL_SECONDS)


def parse_history_limit(value: Any, *, default: int | None = None) -> int:
    """Parse and clamp the in-session history entry limit."""

    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        if default is None:
            raise ValueError(
                f"Maximum in-session history entries must be a whole number between "
                f"{MIN_HISTORY_ENTRIES} and {MAX_HISTORY_ENTRIES}."
            ) from exc
        parsed = int(default)
    return int(_clamp(parsed, MIN_HISTORY_ENTRIES, MAX_HISTORY_ENTRIES))


def parse_sound_volume(value: Any, *, default: int | None = None) -> int:
    """Parse and clamp sound volume as an integer percentage."""

    try:
        parsed = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        if default is None:
            raise ValueError(
                f"Sound volume must be a number between {MIN_SOUND_VOLUME} and {MAX_SOUND_VOLUME}."
            ) from exc
        parsed = int(default)
    return int(_clamp(parsed, MIN_SOUND_VOLUME, MAX_SOUND_VOLUME))


def data_directory_migration_required(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> bool:
    """Return whether saving should copy data from *source* to *destination*."""

    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    return source_path != destination_path and source_path.exists()


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
    if not data_directory_migration_required(source_path, destination_path):
        destination_path.mkdir(parents=True, exist_ok=True)
        return
    destination_path.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
    logger.info("Copied data directory from %s to %s", source_path, destination_path)
