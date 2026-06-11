import threading
from typing import Callable

import pyperclip

from .logger import get_logger

try:
    import win32clipboard

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = get_logger()


def safe_clipboard_text() -> str:
    if HAS_WIN32:
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return data if isinstance(data, str) else str(data)
        except Exception:
            logger.exception("Failed to read clipboard through win32clipboard")
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                logger.debug("Clipboard was already closed after win32clipboard failure", exc_info=True)

    try:
        return pyperclip.paste()
    except Exception:
        logger.exception("Failed to read clipboard through pyperclip")
        return ""


class ClipboardMonitor:
    """Poll the system clipboard on a restart-safe background thread."""

    def __init__(self, callback: Callable[[str], None], poll_interval: float = 0.25):
        self.callback = callback
        self.poll_interval = poll_interval
        self.stop_event = threading.Event()
        self.last_text = ""
        self.thread: threading.Thread | None = None
        self._lock = threading.RLock()

    def start(self) -> bool:
        """Start monitoring once; return ``True`` when a monitor loop is active."""

        with self._lock:
            if self.is_running():
                logger.info("Clipboard monitor start requested while already running")
                return True
            if self.thread and self.thread.is_alive():
                logger.warning("Clipboard monitor start requested before previous loop exited")
                return False

            self.stop_event.clear()
            self.thread = threading.Thread(
                target=self.run,
                name="SessionChronoClipboardMonitor",
                daemon=True,
            )
            self.thread.start()
            logger.info("Clipboard monitor started")
            return True

    def run(self) -> None:
        logger.info("Clipboard monitor loop entering")
        self.last_text = safe_clipboard_text()
        while not self.stop_event.is_set():
            current = safe_clipboard_text()
            if current and current != self.last_text:
                self.last_text = current
                try:
                    self.callback(current)
                except Exception:
                    logger.exception("Clipboard monitor callback failed")
            self.stop_event.wait(self.poll_interval)
        logger.info("Clipboard monitor loop exiting")

    def stop(self, timeout: float | None = 1.0) -> bool:
        """Request monitor shutdown and join the current thread when possible."""

        with self._lock:
            thread = self.thread
            if not thread or not thread.is_alive():
                self.stop_event.set()
                logger.info("Clipboard monitor stop requested while not running")
                return True
            self.stop_event.set()
            logger.info("Clipboard monitor stop requested")

        thread.join(timeout=timeout)
        stopped = not thread.is_alive()
        if stopped:
            logger.info("Clipboard monitor stopped")
        else:
            logger.warning("Clipboard monitor did not stop within %.2f seconds", timeout or 0.0)
        return stopped

    def is_running(self) -> bool:
        thread = self.thread
        return bool(thread and thread.is_alive() and not self.stop_event.is_set())
