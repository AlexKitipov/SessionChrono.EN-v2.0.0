"""Application controller for SessionChrono core behavior.

The controller owns clipboard monitor lifecycle, note persistence, and the
in-memory session history so the Tkinter window can stay focused on rendering
state and collecting user input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from threading import RLock
from typing import Callable, Protocol

from .chrono import ClipboardMonitor
from .config import ensure_user_directories
from .settings import AppSettings, load_settings, migrate_data_directory, save_settings
from .logger import get_logger, log_shutdown, log_startup
from .storage import (
    LoadTextResult,
    SearchResult,
    StorageManager,
    StorageOperationResult,
)
from .utils import build_filename, classify_text_with_confidence

logger = get_logger()


@dataclass(frozen=True)
class ClipboardEntry:
    """A persisted clipboard item tracked for the current UI session."""

    title: str
    path: str
    text: str
    short_title: str
    category: str
    folder: str
    metadata_id: str | None = None
    created_at: str | None = None

    def as_history_item(self) -> dict[str, str]:
        """Return the legacy mapping shape consumed by the history list widget."""

        return {
            "title": self.title,
            "path": self.path,
            "text": self.text,
            "category": self.category,
            "created_at": self.created_at or "",
        }


class ClipboardMonitorProtocol(Protocol):
    """Minimal monitor interface used by :class:`ApplicationController`."""

    def start(self) -> bool: ...

    def stop(self, timeout: float | None = 1.0) -> bool: ...

    def is_running(self) -> bool: ...


MonitorFactory = Callable[[Callable[[str], None]], ClipboardMonitorProtocol]
FilenameBuilder = Callable[[str, str | Path], tuple[str, str, str, str]]
EntryCallback = Callable[[ClipboardEntry], None]
ErrorCallback = Callable[[str, Exception], None]
MonitoringCallback = Callable[[bool], None]


class ApplicationController:
    """Coordinate SessionChrono services independently of the Tkinter view."""

    def __init__(
        self,
        storage: StorageManager | None = None,
        monitor_factory: MonitorFactory = ClipboardMonitor,
        filename_builder: FilenameBuilder = build_filename,
        history_limit: int | None = None,
        settings: AppSettings | None = None,
        on_entry_saved: EntryCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_monitoring_changed: MonitoringCallback | None = None,
    ):
        self.settings = settings or load_settings().settings
        self.storage = storage or StorageManager(
            self.settings.data_directory,
            self.settings.default_export_directory,
        )
        self.monitor_factory = monitor_factory
        self.filename_builder = filename_builder
        self.history_limit = history_limit or self.settings.max_history_entries
        self.on_entry_saved = on_entry_saved
        self.on_error = on_error
        self.on_monitoring_changed = on_monitoring_changed

        self._monitor: ClipboardMonitorProtocol | None = None
        self._history: list[ClipboardEntry] = []
        self._last_record_path: str | None = None
        self._monitoring_active = False
        self._started = False
        self._lock = RLock()

    @property
    def history(self) -> list[ClipboardEntry]:
        """Return a snapshot of clipboard entries for the current session."""

        with self._lock:
            return list(self._history)

    @property
    def history_items(self) -> list[dict[str, str]]:
        """Return a snapshot in the mapping format expected by Tkinter widgets."""

        return [entry.as_history_item() for entry in self.history]

    @property
    def last_record_path(self) -> str | None:
        with self._lock:
            return self._last_record_path

    @property
    def monitoring_active(self) -> bool:
        with self._lock:
            return self._monitoring_active

    @property
    def notes_dir(self) -> Path:
        return self.storage.base_dir

    def start(self) -> bool:
        """Start application services and clipboard monitoring idempotently."""

        with self._lock:
            if self._started:
                logger.info("Application controller start requested while already started")
                return self.monitoring_active
            ensure_user_directories()
            log_startup()
            self._started = True
        logger.info("Application controller started")
        if self.settings.start_monitoring_on_launch:
            return self.resume_monitoring()
        logger.info("Application controller started with clipboard monitoring paused by settings")
        self._notify_monitoring_changed(False)
        return False

    def shutdown(self) -> None:
        """Stop background services and write shutdown diagnostics."""

        logger.info("Application controller shutdown requested")
        self.pause_monitoring()
        log_shutdown()
        with self._lock:
            self._started = False

    def _create_monitor(self) -> ClipboardMonitorProtocol:
        """Create a clipboard monitor using the current polling preference."""

        if self.monitor_factory is ClipboardMonitor:
            return ClipboardMonitor(
                self.handle_clipboard_text,
                poll_interval=self.settings.clipboard_poll_interval,
            )
        monitor = self.monitor_factory(self.handle_clipboard_text)
        if hasattr(monitor, "poll_interval"):
            setattr(monitor, "poll_interval", self.settings.clipboard_poll_interval)
        return monitor

    def apply_settings(self, settings: AppSettings, *, migrate_data: bool = False) -> AppSettings:
        """Persist and apply settings that affect core services."""

        settings = settings.normalized()
        old_settings = self.settings
        old_data_dir = self.storage.base_dir
        save_settings(settings)
        if migrate_data and str(old_data_dir) != settings.data_directory:
            migrate_data_directory(old_data_dir, settings.data_directory)

        was_monitoring = self.monitoring_active
        if was_monitoring:
            self.pause_monitoring()

        with self._lock:
            self.settings = settings
            self.history_limit = settings.max_history_entries
            del self._history[self.history_limit :]
            self.storage = StorageManager(settings.data_directory, settings.default_export_directory)
            self._monitor = None

        if was_monitoring or (not old_settings.start_monitoring_on_launch and settings.start_monitoring_on_launch):
            self.resume_monitoring()
        elif not settings.start_monitoring_on_launch:
            self._notify_monitoring_changed(False)
        logger.info("Applied settings")
        return settings

    def resume_monitoring(self) -> bool:
        """Start the clipboard monitor if it is not already running."""

        with self._lock:
            if self._monitor is None:
                self._monitor = self._create_monitor()
            monitor = self._monitor
            if self._monitoring_active and monitor.is_running():
                logger.info("Clipboard monitoring resume requested while already active")
                return True

        started = monitor.start()
        with self._lock:
            self._monitoring_active = bool(started or monitor.is_running())
            active = self._monitoring_active
        logger.info(
            "Clipboard monitoring %s",
            "resumed" if active else "not running after resume request",
        )
        self._notify_monitoring_changed(active)
        return active

    def pause_monitoring(self) -> bool:
        """Stop the clipboard monitor if needed; safe to call repeatedly."""

        with self._lock:
            monitor = self._monitor
            was_active = self._monitoring_active
        if monitor is None:
            logger.info("Clipboard monitoring pause requested before monitor creation")
            with self._lock:
                self._monitoring_active = False
            if was_active:
                self._notify_monitoring_changed(False)
            return True
        if not was_active and not monitor.is_running():
            logger.info("Clipboard monitoring pause requested while already paused")
            return True

        stopped = monitor.stop(timeout=1.0)
        with self._lock:
            self._monitoring_active = False
        logger.info("Clipboard monitoring paused; stopped=%s", stopped)
        if was_active:
            self._notify_monitoring_changed(False)
        return stopped

    def toggle_monitoring(self) -> bool:
        """Toggle monitoring and return the new active state."""

        if self.monitoring_active:
            self.pause_monitoring()
            return False
        return self.resume_monitoring()

    def handle_clipboard_text(self, text: str) -> ClipboardEntry | None:
        """Persist one clipboard text event and update session history."""

        if not self.monitoring_active:
            logger.debug("Ignoring clipboard event while monitoring is paused")
            return None

        try:
            path, folder, short, category = self.filename_builder(text, self.storage.base_dir)
            classification_category, confidence = classify_text_with_confidence(text)
            if classification_category != category:
                logger.debug(
                    "Filename category %s differed from classifier category %s",
                    category,
                    classification_category,
                )
            result = self.storage.save_text(path, text)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            saved_path = result.path or path
            metadata = self.storage.metadata.create_metadata(
                file_path=saved_path,
                category=category,
                title=f"[{category}] {short}",
                short_title=short,
                text_length=len(text),
                classifier_confidence=confidence,
            )
            entry = ClipboardEntry(
                title=f"[{category}] {short}",
                path=saved_path,
                text=text,
                short_title=short,
                category=category,
                folder=folder,
                metadata_id=metadata.entry_id,
                created_at=metadata.created_at,
            )
            with self._lock:
                self._last_record_path = saved_path
                self._history.insert(0, entry)
                del self._history[self.history_limit :]
            logger.info("Saved clipboard entry: path=%s category=%s", saved_path, category)
            if self.on_entry_saved:
                self.on_entry_saved(entry)
            return entry
        except Exception as exc:
            logger.exception("Failed to handle clipboard text event")
            if self.on_error:
                self.on_error("Failed to save clipboard item", exc)
            return None

    def clear_history(self) -> None:
        with self._lock:
            count = len(self._history)
            self._history.clear()
        logger.info("Cleared in-memory clipboard history containing %d item(s)", count)

    def history_entry_at(self, index: int) -> ClipboardEntry | None:
        with self._lock:
            if 0 <= index < len(self._history):
                return self._history[index]
        return None

    def load_text(self, path: str | Path) -> LoadTextResult:
        return self.storage.load_text(path)

    def save_text(self, path: str | Path, text: str) -> StorageOperationResult:
        return self.storage.save_text(path, text)

    def upsert_metadata_for_path(self, path: str | Path, content: str = "", **fields):
        """Update or create metadata for a saved text file path."""

        metadata_fields = self._metadata_fields_for_path(path, content, **fields)
        return self.storage.upsert_metadata_for_path(path, **metadata_fields)

    def create_today_zip(self) -> StorageOperationResult:
        return self.storage.create_today_zip()

    def export_notes(self, format_name: str, destination: str | Path | None = None, **filters) -> StorageOperationResult:
        return self.storage.export_notes(format_name, destination, **filters)

    def search_logs(
        self,
        query: str = "",
        *,
        category: str | None = None,
        date_from: date | datetime | str | None = None,
        date_to: date | datetime | str | None = None,
        tag: str | None = None,
        filename: str | None = None,
    ) -> list[SearchResult]:
        return self.storage.search_logs(
            query,
            category=category,
            date_from=date_from,
            date_to=date_to,
            tag=tag,
            filename=filename,
        )

    def load_metadata_by_path(self, path: str | Path):
        return self.storage.load_metadata_by_path(path)

    def update_metadata(self, entry_id: str, **fields):
        return self.storage.update_metadata(entry_id, **fields)

    def search_metadata(self, query: str = "", *, tags=None):
        return self.storage.search_metadata(query, tags=tags)

    def _metadata_fields_for_path(self, path: str | Path, content: str = "", **fields):
        resolved = self.storage.resolve_path(path)
        short_title = fields.pop("short_title", None) or resolved.stem
        category = fields.pop("category", None) or self._category_from_path(resolved, content)
        title = fields.pop("title", None) or f"[{category}] {short_title}"
        text_length = fields.pop("text_length", None)
        if text_length is None:
            text_length = len(content)
        classifier_confidence = fields.pop("classifier_confidence", None)
        if classifier_confidence is None:
            classifier_confidence = classify_text_with_confidence(content)[1] if content else 0.0
        return {
            "category": category,
            "title": title,
            "short_title": short_title,
            "text_length": text_length,
            "classifier_confidence": classifier_confidence,
            **fields,
        }

    @staticmethod
    def _category_from_path(path: Path, content: str = "") -> str:
        parent_name = path.parent.name.strip()
        if parent_name.isupper() and parent_name.replace("_", "").isalpha():
            return parent_name
        return classify_text_with_confidence(content)[0] if content else "NOTE"

    def _notify_monitoring_changed(self, active: bool) -> None:
        if self.on_monitoring_changed:
            self.on_monitoring_changed(active)
