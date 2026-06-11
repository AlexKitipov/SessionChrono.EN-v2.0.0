"""Application controller for SessionChrono core behavior.

The controller owns clipboard monitor lifecycle, note persistence, and the
in-memory session history so the Tkinter window can stay focused on rendering
state and collecting user input.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Callable, Protocol

from .chrono import ClipboardMonitor
from .config import ensure_user_directories
from .logger import get_logger, log_shutdown, log_startup
from .storage import (
    LoadTextResult,
    SearchResult,
    StorageManager,
    StorageOperationResult,
    get_default_storage_manager,
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

    def as_history_item(self) -> dict[str, str]:
        """Return the legacy mapping shape consumed by the history list widget."""

        return {"title": self.title, "path": self.path, "text": self.text}


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
        history_limit: int = 20,
        on_entry_saved: EntryCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_monitoring_changed: MonitoringCallback | None = None,
    ):
        self.storage = storage or get_default_storage_manager()
        self.monitor_factory = monitor_factory
        self.filename_builder = filename_builder
        self.history_limit = history_limit
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
        return self.resume_monitoring()

    def shutdown(self) -> None:
        """Stop background services and write shutdown diagnostics."""

        logger.info("Application controller shutdown requested")
        self.pause_monitoring()
        log_shutdown()
        with self._lock:
            self._started = False

    def resume_monitoring(self) -> bool:
        """Start the clipboard monitor if it is not already running."""

        with self._lock:
            if self._monitor is None:
                self._monitor = self.monitor_factory(self.handle_clipboard_text)
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

    def create_today_zip(self) -> StorageOperationResult:
        return self.storage.create_today_zip()

    def search_logs(self, query: str) -> list[SearchResult]:
        return self.storage.search_logs(query)

    def load_metadata_by_path(self, path: str | Path):
        return self.storage.load_metadata_by_path(path)

    def update_metadata(self, entry_id: str, **fields):
        return self.storage.update_metadata(entry_id, **fields)

    def search_metadata(self, query: str = "", *, tags=None):
        return self.storage.search_metadata(query, tags=tags)

    def _notify_monitoring_changed(self, active: bool) -> None:
        if self.on_monitoring_changed:
            self.on_monitoring_changed(active)
