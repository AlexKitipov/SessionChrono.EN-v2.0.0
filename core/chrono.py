import time
import threading
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
    def __init__(self, callback):
        self.callback = callback
        self.stop_event = threading.Event()
        self.last_text = ""
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            if not self.stop_event.is_set():
                logger.info("Clipboard monitor start requested while already running")
                return
            self.thread.join(timeout=0.5)
            if self.thread.is_alive():
                logger.warning("Clipboard monitor restart requested before previous loop exited")
                return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        logger.info("Clipboard monitor started")

    def run(self):
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
            time.sleep(0.25)
        logger.info("Clipboard monitor loop exiting")

    def stop(self):
        self.stop_event.set()
        logger.info("Clipboard monitor stop requested")
