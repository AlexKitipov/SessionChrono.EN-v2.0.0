import time
import threading
import pyperclip

try:
    import win32clipboard
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

def safe_clipboard_text() -> str:
    if HAS_WIN32:
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return data if isinstance(data, str) else str(data)
        except:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

    try:
        return pyperclip.paste()
    except:
        return ""

class ClipboardMonitor:
    def __init__(self, callback):
        self.callback = callback
        self.stop_event = threading.Event()
        self.last_text = ""

    def start(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()

    def run(self):
        self.last_text = safe_clipboard_text()
        while not self.stop_event.is_set():
            current = safe_clipboard_text()
            if current and current != self.last_text:
                self.last_text = current
                self.callback(current)
            time.sleep(0.25)

    def stop(self):
        self.stop_event.set()
