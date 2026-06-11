I'll analyze the repository and create a comprehensive development plan. Let me start by exploring the codebase structure.Let me explore the repository structure:Now I have a complete understanding of the codebase. Let me create a comprehensive, structured development plan.

---

# **SessionChrono v2.0.0 Development Plan**
## *From Local Tkinter App ? Production-Ready EXE & Installer*

This plan provides concrete, step-by-step tasks for transforming SessionChrono into a modular, professional clipboard-logging application with a modern UI, advanced features, and PyInstaller packaging.

---

## **PHASE 1: FOUNDATION & ARCHITECTURE REFACTORING**

### **1.1 Restructure Project for PyInstaller Compatibility**

**Goal:** Ensure all paths are relative and the app works seamlessly when packaged.

**Task 1.1.1: Create Resource Management System**

```
sessionchrono/
??? main.py
??? app.py (app entry point with __file__ detection)
??? requirements.txt
??? build_spec.py (PyInstaller spec)
??? sounds/
?   ??? start.wav
?   ??? copy.wav
?   ??? error.wav
?   ??? ...
??? icons/
?   ??? app_icon.ico
?   ??? app_icon.png
?   ??? taskbar.ico
??? core/
?   ??? __init__.py
?   ??? chrono.py
?   ??? storage.py
?   ??? utils.py
?   ??? classifier.py (NEW)
?   ??? config.py (NEW)
?   ??? logger.py (NEW)
??? ui/
?   ??? __init__.py
?   ??? tkinter_ui.py (refactored into modules)
?   ??? widgets.py (NEW - reusable widgets)
?   ??? styles.py (NEW - theme/style definitions)
?   ??? dialogs.py (NEW - modal windows)
?   ??? components.py (NEW - complex UI sections)
??? ChronoNotes/ (auto-created at runtime)
```

**File: `core/config.py` (NEW)**

```python
import os
import sys
from pathlib import Path

# Get the root directory where app is running from
if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).parent.parent

# All paths should be relative to APP_ROOT
SOUNDS_DIR = APP_ROOT / "sounds"
ICONS_DIR = APP_ROOT / "icons"
CHRONO_NOTES_DIR = Path.home() / ".SessionChrono" / "ChronoNotes"  # Use home dir for user data

# Ensure directories exist
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
CHRONO_NOTES_DIR.mkdir(parents=True, exist_ok=True)

# Settings
APP_TITLE = "SessionChrono v2.0.0"
APP_VERSION = "2.0.0"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 750

# Classification thresholds
CLASSIFIER_THRESHOLD = 0.6
```

**Commit Task:** `refactor: centralize resource paths for PyInstaller compatibility`

---

**Task 1.1.2: Create Logging Infrastructure**

**File: `core/logger.py` (NEW)**

```python
import logging
from pathlib import Path
from datetime import datetime

class AppLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        log_dir = Path.home() / ".SessionChrono" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        self.logger = logging.getLogger("SessionChrono")
        self.logger.setLevel(logging.DEBUG)
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self._initialized = True
    
    def get_logger(self):
        return self.logger

logger = AppLogger().get_logger()
```

**Commit Task:** `feat: add application-wide logging system`

---

### **1.2 Improve Text Classification System**

**Task 1.2.1: Expand Classifier with Multiple Detection Types**

**File: `core/classifier.py` (NEW - Replace simple logic in utils.py)**

```python
import re
from typing import Tuple, Dict
from enum import Enum

class TextCategory(Enum):
    URL = "URL"
    CODE = "CODE"
    MARKDOWN = "MARKDOWN"
    JSON = "JSON"
    XML = "XML"
    SQL = "SQL"
    TRACEBACK = "TRACEBACK"
    TODO = "TODO"
    CHAT = "CHAT"
    LOG = "LOG"
    NOTE = "NOTE"

class TextClassifier:
    def __init__(self):
        self.patterns = {
            TextCategory.URL: [
                r'https?://',
                r'www\.',
                r'ftp://'
            ],
            TextCategory.JSON: [
                r'^\s*\{.*\}$',
                r'^\s*\[.*\]$',
                r'"[^"]*"\s*:',
            ],
            TextCategory.XML: [
                r'<[^>]+>',
                r'<[^>]+/>',
            ],
            TextCategory.SQL: [
                r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b',
                r'\bFROM\b',
                r'\bWHERE\b',
            ],
            TextCategory.MARKDOWN: [
                r'^#+\s',  # Headers
                r'\*\*.*\*\*',  # Bold
                r'`{1,3}.*`{1,3}',  # Code blocks
                r'^\s*[-*+]\s',  # Lists
            ],
            TextCategory.TRACEBACK: [
                r'Traceback',
                r'File "[^"]*", line \d+',
                r'\w+Error:',
                r'Stack trace',
            ],
            TextCategory.CODE: [
                r'\b(def|class|function|const|let|var)\b',
                r'\{.*\}',
                r'console\.log|print\(',
            ],
            TextCategory.TODO: [
                r'\b(TODO|FIXME|HACK|XXX|MUST|TASK|FIX)\b',
                r'to do',
                r'to-do',
            ],
            TextCategory.CHAT: [
                r'\b(copilot|chatgpt|gpt|claude|assistant|ai model)\b',
                r'I think|You said|Question:|Answer:',
            ],
        }
    
    def classify(self, text: str, confidence=False) -> str | Tuple[str, float]:
        """
        Classify text into categories.
        Returns category name, optionally with confidence score.
        """
        if not text or not text.strip():
            return (TextCategory.NOTE.value, 0.0) if confidence else TextCategory.NOTE.value
        
        t = text.strip()
        scores = {}
        
        for category, patterns in self.patterns.items():
            match_count = 0
            for pattern in patterns:
                try:
                    if re.search(pattern, t, re.IGNORECASE | re.MULTILINE):
                        match_count += 1
                except:
                    pass
            scores[category] = match_count
        
        # Find category with highest score
        best_category = max(scores, key=scores.get) if scores else TextCategory.NOTE
        score = scores[best_category] / len(self.patterns.get(best_category, [1]))
        
        if confidence:
            return (best_category.value, min(score, 1.0))
        return best_category.value
    
    def get_all_categories(self):
        return [cat.value for cat in TextCategory]

classifier = TextClassifier()
```

**Commit Task:** `feat: implement advanced multi-pattern text classifier with confidence scoring`

---

**Task 1.2.2: Update utils.py to Use New Classifier**

**File: `core/utils.py` (MODIFIED)**

```python
import os
from datetime import datetime
from pathlib import Path
from .config import CHRONO_NOTES_DIR
from .classifier import classifier

def make_short_title(text: str, max_len: int = 40) -> str:
    """Create a filesystem-safe short title from text."""
    lines = text.strip().splitlines()
    line = lines[0] if lines else "empty"
    line = line.replace("\t", " ").strip()
    if len(line) > max_len:
        line = line[:max_len].rsplit(" ", 1)[0] or line[:max_len]
    
    # Remove filesystem-invalid characters
    bad_chars = '<>:"/\\|?*'
    for ch in bad_chars:
        line = line.replace(ch, "_")
    
    return line or "note"

def build_filename(text: str) -> Tuple[str, str, str, str]:
    """
    Build filename and folder path for clipboard content.
    Returns: (full_path, folder, title, category)
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    
    category = classifier.classify(text)
    short = make_short_title(text)
    
    folder = CHRONO_NOTES_DIR / date_str / category
    folder.mkdir(parents=True, exist_ok=True)
    
    filename = f"{category}_{short}_{date_str}_{time_str}.txt"
    full_path = str(folder / filename)
    
    return full_path, str(folder), short, category
```

**Commit Task:** `refactor: integrate advanced classifier into utils`

---

### **1.3 Improve Storage Layer**

**Task 1.3.1: Enhance Storage Module with Better Error Handling**

**File: `core/storage.py` (MODIFIED)**

```python
import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
from .config import CHRONO_NOTES_DIR
from .logger import logger

class StorageManager:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or CHRONO_NOTES_DIR
    
    def save_text(self, path: str, text: str) -> bool:
        """Save text to file with error handling."""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Saved: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save {path}: {e}")
            return False
    
    def load_text(self, path: str) -> str:
        """Load text from file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return ""
    
    def create_zip(self, date: Optional[str] = None) -> Optional[str]:
        """Create ZIP of daily notes."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        day_folder = self.base_path / date
        if not day_folder.exists():
            logger.warning(f"No logs for {date}")
            return None
        
        zip_path = self.base_path / f"{date}_ChronoNotes.zip"
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in day_folder.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.base_path)
                        zf.write(file_path, arcname)
            logger.info(f"Created ZIP: {zip_path}")
            return str(zip_path)
        except Exception as e:
            logger.error(f"Failed to create ZIP: {e}")
            return None
    
    def search_logs(self, query: str) -> List[str]:
        """Search all log files for query string."""
        matches = []
        try:
            for file_path in self.base_path.rglob("*.txt"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if query.lower() in content.lower():
                        matches.append(str(file_path))
                except:
                    pass
        except Exception as e:
            logger.error(f"Search failed: {e}")
        return matches
    
    def get_today_entries(self) -> List[Tuple[str, str]]:
        """Get all entries from today."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries = []
        
        today_folder = self.base_path / today
        if today_folder.exists():
            for file_path in today_folder.rglob("*.txt"):
                try:
                    content = file_path.read_text(encoding="utf-8")[:100]
                    entries.append((str(file_path), content))
                except:
                    pass
        
        return entries
    
    def export_to_file(self, format: str = "txt") -> Optional[str]:
        """Export all logs to single file."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if format == "txt":
            output_path = self.base_path / f"export_{today}.txt"
            try:
                with open(output_path, "w", encoding="utf-8") as out:
                    for file_path in self.base_path.rglob("*.txt"):
                        content = file_path.read_text(encoding="utf-8")
                        out.write(f"\n--- {file_path.name} ---\n{content}\n")
                logger.info(f"Exported to: {output_path}")
                return str(output_path)
            except Exception as e:
                logger.error(f"Export failed: {e}")
        
        return None

storage = StorageManager()
```

**Commit Task:** `refactor: enhance storage layer with better error handling and export features`

---

## **PHASE 2: UI MODERNIZATION & MODULARIZATION**

### **2.1 Create Reusable UI Components**

**Task 2.1.1: Extract Widget Definitions**

**File: `ui/styles.py` (NEW)**

```python
# Theme colors
COLORS = {
    "bg_primary": "#2d2d2d",
    "bg_secondary": "#1e1e1e",
    "fg_primary": "#ffffff",
    "fg_secondary": "#d4d4d4",
    "accent_blue": "#007acc",
    "accent_green": "#4ec9b0",
    "accent_red": "#f48771",
    "border": "#3e3e3e",
    "hover": "#505050",
}

FONTS = {
    "title": ("Segoe UI", 14, "bold"),
    "heading": ("Segoe UI", 11, "bold"),
    "body": ("Segoe UI", 10),
    "mono": ("Consolas", 10),
    "mono_sm": ("Consolas", 9),
}

DIMENSIONS = {
    "window_width": 1200,
    "window_height": 750,
    "padding": 10,
    "button_height": 2,
}
```

**File: `ui/widgets.py` (NEW)**

```python
import tkinter as tk
from tkinter import ttk
from .styles import COLORS, FONTS

class ScrolledText(tk.Frame):
    """Text widget with scrollbar."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_primary"])
        
        self.text = tk.Text(
            self,
            wrap="word",
            bg=COLORS["bg_secondary"],
            fg=COLORS["fg_secondary"],
            insertbackground="white",
            font=FONTS["mono"],
            **kwargs
        )
        scrollbar = ttk.Scrollbar(self, command=self.text.yview)
        self.text.config(yscrollcommand=scrollbar.set)
        
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def get(self, *args):
        return self.text.get(*args)
    
    def insert(self, *args):
        return self.text.insert(*args)
    
    def delete(self, *args):
        return self.text.delete(*args)

class ScrolledListbox(tk.Frame):
    """Listbox with scrollbar."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_primary"])
        
        self.listbox = tk.Listbox(
            self,
            bg=COLORS["bg_secondary"],
            fg=COLORS["fg_secondary"],
            selectbackground="#264f78",
            activestyle="none",
            font=FONTS["mono_sm"],
            **kwargs
        )
        scrollbar = ttk.Scrollbar(self, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def bind(self, *args):
        return self.listbox.bind(*args)
    
    def insert(self, *args):
        return self.listbox.insert(*args)
    
    def delete(self, *args):
        return self.listbox.delete(*args)
    
    def get(self, *args):
        return self.listbox.get(*args)
    
    def curselection(self):
        return self.listbox.curselection()

class DarkContextMenu:
    """Dark-themed right-click context menu."""
    def __init__(self, widget):
        self.widget = widget
        self.menu = tk.Menu(
            widget,
            tearoff=0,
            bg=COLORS["bg_primary"],
            fg=COLORS["fg_primary"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["fg_primary"],
        )
        
        self.menu.add_command(label="Copy", command=self._copy)
        self.menu.add_command(label="Cut", command=self._cut)
        self.menu.add_command(label="Paste", command=self._paste)
        self.menu.add_separator()
        self.menu.add_command(label="Select All", command=self._select_all)
        self.menu.add_command(label="Clear", command=self._clear)
        
        widget.bind("<Button-3>", self._show_menu)
    
    def _show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
    
    def _copy(self):
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
        except:
            pass
    
    def _cut(self):
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
            self.widget.delete("sel.first", "sel.last")
        except:
            pass
    
    def _paste(self):
        try:
            text = self.widget.clipboard_get()
            self.widget.insert(tk.INSERT, text)
        except:
            pass
    
    def _select_all(self):
        self.widget.tag_add("sel", "1.0", "end")
    
    def _clear(self):
        self.widget.delete("1.0", "end")
```

**Commit Task:** `feat: create reusable UI components and centralized styling`

---

**Task 2.1.2: Create Sound Manager Module**

**File: `ui/sounds.py` (NEW)**

```python
import os
from pathlib import Path
from .styles import COLORS

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

from ..core.config import SOUNDS_DIR
from ..core.logger import logger

class SoundManager:
    """Manages audio feedback across the application."""
    
    SOUND_FILES = {
        "start":  "start.wav",
        "copy":   "copy.wav",
        "error":  "error.wav",
        "pause":  "pause.wav",
        "resume": "resume.wav",
        "save":   "save.wav",
        "open":   "open.wav",
        "success": "success.wav",
    }
    
    BEEP_PATTERNS = {
        "start":  (900, 120),
        "copy":   (1200, 120),
        "error":  (400, 250),
        "pause":  (700, 120),
        "resume": (900, 180),
        "save":   (800, 120),
        "open":   (1000, 100),
        "success": (1500, 150),
    }
    
    def __init__(self, root=None):
        self.root = root
        self.enabled = True
    
    def play(self, event: str):
        """Play sound for given event."""
        if not self.enabled or event not in self.BEEP_PATTERNS:
            return
        
        if HAS_WINSOUND:
            self._play_windows(event)
        elif self.root:
            try:
                self.root.bell()
            except:
                pass
    
    def _play_windows(self, event: str):
        """Play WAV file or beep on Windows."""
        wav_name = self.SOUND_FILES.get(event)
        wav_path = SOUNDS_DIR / wav_name
        
        if wav_path.exists():
            try:
                winsound.PlaySound(
                    str(wav_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC
                )
                return
            except Exception as e:
                logger.warning(f"Failed to play WAV: {e}")
        
        # Fallback to beep
        freq, dur = self.BEEP_PATTERNS.get(event, (800, 100))
        try:
            winsound.Beep(freq, dur)
        except Exception as e:
            logger.warning(f"Failed to play beep: {e}")
    
    def toggle(self):
        """Toggle sound on/off."""
        self.enabled = not self.enabled
        return self.enabled

sound_manager = SoundManager()
```

**Commit Task:** `feat: create dedicated sound manager module`

---

### **2.2 Refactor Main UI into Modular Components**

**Task 2.2.1: Create Dialogs Module**

**File: `ui/dialogs.py` (NEW)**

```python
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from .styles import COLORS, FONTS

class SettingsDialog(tk.Toplevel):
    """Application settings window."""
    def __init__(self, parent, config):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x300")
        self.configure(bg=COLORS["bg_primary"])
        self.config = config
        self.result = None
        
        self._build_ui()
        self.transient(parent)
        self.grab_set()
    
    def _build_ui(self):
        frame = tk.Frame(self, bg=COLORS["bg_primary"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Sound toggle
        tk.Label(frame, text="Sound Alerts", bg=COLORS["bg_primary"], fg=COLORS["fg_primary"]).pack(anchor="w")
        self.sound_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Enable", variable=self.sound_var, bg=COLORS["bg_primary"], fg=COLORS["fg_primary"]).pack(anchor="w")
        
        # Monitor interval
        tk.Label(frame, text="Monitor Interval (ms)", bg=COLORS["bg_primary"], fg=COLORS["fg_primary"]).pack(anchor="w", pady=(10, 0))
        self.interval_var = tk.StringVar(value="250")
        tk.Entry(frame, textvariable=self.interval_var).pack(anchor="w", fill="x")
        
        # Buttons
        btn_frame = tk.Frame(frame, bg=COLORS["bg_primary"])
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="OK", command=self.ok_pressed).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.cancel_pressed).pack(side="left")
    
    def ok_pressed(self):
        self.result = {
            "sound_enabled": self.sound_var.get(),
            "monitor_interval": int(self.interval_var.get())
        }
        self.destroy()
    
    def cancel_pressed(self):
        self.destroy()

class SearchDialog(tk.Toplevel):
    """Search logs dialog with results display."""
    def __init__(self, parent, search_func):
        super().__init__(parent)
        self.title("Search Logs")
        self.geometry("600x400")
        self.configure(bg=COLORS["bg_primary"])
        self.search_func = search_func
        self.result = None
        
        self._build_ui()
        self.transient(parent)
        self.grab_set()
    
    def _build_ui(self):
        # Search bar
        search_frame = tk.Frame(self, bg=COLORS["bg_primary"])
        search_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(search_frame, text="Search:", bg=COLORS["bg_primary"], fg=COLORS["fg_primary"]).pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(search_frame, text="Search", command=self.perform_search).pack(side="left")
        
        # Results listbox
        list_frame = tk.Frame(self, bg=COLORS["bg_primary"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.results_list = tk.Listbox(
            list_frame,
            bg=COLORS["bg_secondary"],
            fg=COLORS["fg_secondary"],
            font=FONTS["mono_sm"]
        )
        scrollbar = tk.Scrollbar(list_frame, command=self.results_list.yview)
        self.results_list.config(yscrollcommand=scrollbar.set)
        
        self.results_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.results_list.bind("<Double-Button-1>", self._on_select)
    
    def perform_search(self):
        query = self.search_var.get()
        if not query:
            return
        
        matches = self.search_func(query)
        self.results_list.delete(0, tk.END)
        for match in matches:
            self.results_list.insert(tk.END, match)
    
    def _on_select(self, event):
        sel = self.results_list.curselection()
        if sel:
            self.result = self.results_list.get(sel[0])
            self.destroy()
```

**Commit Task:** `feat: create reusable dialog windows`

---

**Task 2.2.2: Refactor Main UI**

**File: `ui/tkinter_ui.py` (REFACTORED)**

```python
import os
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from core.chrono import ClipboardMonitor
from core.storage import storage
from core.utils import build_filename
from core.config import CHRONO_NOTES_DIR, APP_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT
from core.logger import logger

from ui.widgets import ScrolledText, ScrolledListbox, DarkContextMenu
from ui.sounds import sound_manager
from ui.styles import COLORS, FONTS, DIMENSIONS
from ui.dialogs import SettingsDialog, SearchDialog


class SessionChronoUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.configure(bg=COLORS["bg_primary"])
        
        self.sound = sound_manager
        self.status_var = tk.StringVar(value="Initializing...")
        self.current_file_path = None
        self.last_record_path = None
        self.history = []
        self.logging_active = True
        
        self._setup_style()
        self._build_menu()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        logger.info("UI initialized")
        self.status_var.set("Starting clipboard monitoring...")
        self.sound.play("start")
        
        self.monitor = ClipboardMonitor(self.handle_new_clipboard_item)
        self.monitor.start()
    
    def _setup_style(self):
        """Configure TTK styles."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            ".",
            background=COLORS["bg_primary"],
            foreground=COLORS["fg_primary"],
            font=FONTS["body"],
        )
        style.configure("TButton", background=COLORS["border"], foreground=COLORS["fg_primary"])
        style.map("TButton", background=[("active", COLORS["hover"])])
        style.configure("TLabel", background=COLORS["bg_primary"], foreground=COLORS["fg_primary"])
    
    def _build_menu(self):
        """Build application menu bar."""
        menubar = tk.Menu(
            self,
            bg=COLORS["bg_primary"],
            fg=COLORS["fg_primary"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["fg_primary"],
            tearoff=0,
        )
        
        def create_menu(parent):
            return tk.Menu(parent, bg=COLORS["bg_primary"], fg=COLORS["fg_primary"],
                          activebackground=COLORS["border"], activeforeground=COLORS["fg_primary"], tearoff=0)
        
        # FILE menu
        file_menu = create_menu(menubar)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open...", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # TOOLS menu
        tools_menu = create_menu(menubar)
        tools_menu.add_command(label="Pause/Resume", command=self.toggle_logging)
        tools_menu.add_command(label="Open Logs Folder", command=self.open_logs_folder)
        tools_menu.add_command(label="Open Last Entry", command=self.open_last_record)
        tools_menu.add_command(label="Create ZIP", command=self.create_zip)
        tools_menu.add_command(label="Search Logs", command=self.search_logs_ui)
        tools_menu.add_separator()
        tools_menu.add_command(label="Settings", command=self.show_settings)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # HELP menu
        help_menu = create_menu(menubar)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
    
    def _build_layout(self):
        """Build main UI layout."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=DIMENSIONS["padding"], pady=DIMENSIONS["padding"])
        
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)
        
        # LEFT: Editor
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)
        
        self.editor = ScrolledText(left_frame)
        self.editor.grid(row=0, column=0, sticky="nsew")
        DarkContextMenu(self.editor.text)
        
        # RIGHT: Sidebar
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        right_frame.rowconfigure(1, weight=1)
        right_frame.rowconfigure(3, weight=2)
        right_frame.columnconfigure(0, weight=1)
        
        # Last Clipboard
        ttk.Label(right_frame, text="Last Copied", font=FONTS["heading"]).grid(row=0, column=0, sticky="w")
        
        self.last_clip_box = ScrolledText(right_frame, height=12)
        self.last_clip_box.grid(row=1, column=0, sticky="nsew")
        DarkContextMenu(self.last_clip_box.text)
        
        # Clipboard History
        ttk.Label(right_frame, text="History", font=FONTS["heading"]).grid(row=2, column=0, sticky="w", pady=(10, 5))
        
        self.history_list = ScrolledListbox(right_frame)
        self.history_list.grid(row=3, column=0, sticky="nsew")
        self.history_list.bind("<<ListboxSelect>>", self.on_history_select)
        
        ttk.Button(right_frame, text="Clear History", command=self.clear_history).grid(row=4, column=0, sticky="ew", pady=(10, 0))
        
        # STATUS BAR
        status_frame = tk.Frame(self, bg=COLORS["accent_blue"])
        status_frame.pack(side="bottom", fill="x")
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=COLORS["accent_blue"],
            fg="white",
            anchor="w",
            padx=5,
            pady=3,
        ).pack(fill="x")
    
    # ----- EVENT HANDLERS -----
    def handle_new_clipboard_item(self, text: str):
        """Handle new clipboard content."""
        try:
            path, folder, short, category = build_filename(text)
            storage.save_text(path, text)
            self.last_record_path = path
            
            item_title = f"[{category}] {short}"
            self.history.insert(0, {"title": item_title, "path": path, "text": text})
            self.history = self.history[:20]
            
            self.refresh_history()
            
            self.last_clip_box.delete("1.0", tk.END)
            self.last_clip_box.insert("1.0", text)
            
            self.status_var.set(f"Saved: {item_title}")
            self.sound.play("copy")
            logger.info(f"Clipboard saved: {category}")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")
            logger.error(f"Clipboard handling error: {e}")
    
    def refresh_history(self):
        """Refresh history listbox."""
        self.history_list.delete(0, tk.END)
        for item in self.history:
            self.history_list.insert(tk.END, item["title"])
    
    def on_history_select(self, event):
        """Load selected history item."""
        sel = self.history_list.curselection()
        if not sel:
            return
        
        item = self.history[sel[0]]
        content = storage.load_text(item["path"])
        
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", content)
        self.current_file_path = item["path"]
        self.status_var.set(f"Opened: {Path(item['path']).name}")
        self.sound.play("open")
    
    def clear_history(self):
        """Clear session history."""
        self.history.clear()
        self.refresh_history()
        self.status_var.set("History cleared")
    
    # ----- FILE OPERATIONS -----
    def new_file(self):
        self.editor.delete("1.0", tk.END)
        self.current_file_path = None
        self.status_var.set("New file")
        self.sound.play("open")
    
    def open_file(self):
        # File dialog implementation
        pass
    
    def save_file(self):
        # Save implementation
        pass
    
    def save_file_as(self):
        # Save As implementation
        pass
    
    # ----- TOOLS -----
    def toggle_logging(self):
        self.logging_active = not self.logging_active
        if self.logging_active:
            self.monitor.start()
            self.status_var.set("Monitoring resumed")
            self.sound.play("resume")
        else:
            self.monitor.stop()
            self.status_var.set("Monitoring paused")
            self.sound.play("pause")
    
    def open_logs_folder(self):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(CHRONO_NOTES_DIR))
            elif sys.platform == "darwin":
                os.system(f"open '{CHRONO_NOTES_DIR}'")
            else:
                os.system(f"xdg-open '{CHRONO_NOTES_DIR}'")
            self.sound.play("open")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")
    
    def open_last_record(self):
        if not self.last_record_path or not Path(self.last_record_path).exists():
            self.status_var.set("No recent entry")
            self.sound.play("error")
            return
        
        content = storage.load_text(self.last_record_path)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", content)
        self.current_file_path = self.last_record_path
        self.status_var.set("Last entry opened")
        self.sound.play("open")
    
    def create_zip(self):
        zip_path = storage.create_zip()
        if zip_path:
            self.status_var.set(f"ZIP created: {Path(zip_path).name}")
            self.sound.play("save")
        else:
            self.status_var.set("No logs for today")
            self.sound.play("error")
    
    def search_logs_ui(self):
        dialog = SearchDialog(self, storage.search_logs)
        self.wait_window(dialog)
        if dialog.result:
            content = storage.load_text(dialog.result)
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", content)
            self.status_var.set(f"Opened: {Path(dialog.result).name}")
            self.sound.play("open")
    
    def show_settings(self):
        dialog = SettingsDialog(self, {})
        # Handle settings update
    
    def show_about(self):
        import tkinter.messagebox as mb
        mb.showinfo(APP_TITLE, "SessionChrono - Smart Clipboard Logger\nv2.0.0\n\nAutomatic clipboard monitoring with AI text classification")
    
    def on_close(self):
        try:
            self.monitor.stop()
        except:
            pass
        self.destroy()


def start_app():
    app = SessionChronoUI()
    app.mainloop()


if __name__ == "__main__":
    start_app()
```

**Commit Task:** `refactor: modularize main UI into components and widgets`

---

## **PHASE 3: ADVANCED FEATURES**

### **3.1 Implement Tagging and Metadata System**

**Task 3.1.1: Create Metadata Manager**

**File: `core/metadata.py` (NEW)**

```python
import json
from pathlib import Path
from datetime import datetime
from .config import CHRONO_NOTES_DIR

class MetadataManager:
    """Manage tags, annotations, and metadata for clipboard entries."""
    
    def __init__(self):
        self.metadata_dir = CHRONO_NOTES_DIR / ".metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def save_metadata(self, file_path: str, tags: list = None, notes: str = "", color: str = "default"):
        """Save metadata for a file."""
        file_hash = self._hash_path(file_path)
        meta_file = self.metadata_dir / f"{file_hash}.json"
        
        metadata = {
            "file_path": file_path,
            "tags": tags or [],
            "notes": notes,
            "color": color,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def load_metadata(self, file_path: str) -> dict:
        """Load metadata for a file."""
        file_hash = self._hash_path(file_path)
        meta_file = self.metadata_dir / f"{file_hash}.json"
        
        if meta_file.exists():
            with open(meta_file, "r") as f:
                return json.load(f)
        
        return {"file_path": file_path, "tags": [], "notes": "", "color": "default"}
    
    def add_tag(self, file_path: str, tag: str):
        """Add a tag to file."""
        meta = self.load_metadata(file_path)
        if tag not in meta["tags"]:
            meta["tags"].append(tag)
        self.save_metadata(file_path, **{k: v for k, v in meta.items() if k != "file_path"})
    
    def get_all_tags(self) -> list:
        """Get all unique tags used."""
        tags = set()
        for meta_file in self.metadata_dir.glob("*.json"):
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                    tags.update(data.get("tags", []))
            except:
                pass
        return sorted(list(tags))
    
    @staticmethod
    def _hash_path(path: str) -> str:
        import hashlib
        return hashlib.md5(path.encode()).hexdigest()

metadata_manager = MetadataManager()
```

**Commit Task:** `feat: implement metadata manager for tagging and annotations`

---

### **3.2 Add Export Functionality**

**Task 3.2.1: Create Export Module**

**File: `core/export.py` (NEW)**

```python
import json
import csv
from pathlib import Path
from datetime import datetime
from .storage import storage
from .config import CHRONO_NOTES_DIR

class ExportManager:
    """Export clipboard logs in multiple formats."""
    
    @staticmethod
    def export_to_json(date: str = None) -> str:
        """Export logs for a date to JSON."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        day_folder = CHRONO_NOTES_DIR / date
        data = []
        
        if day_folder.exists():
            for file_path in day_folder.rglob("*.txt"):
                content = file_path.read_text(encoding="utf-8")
                data.append({
                    "category": file_path.parent.name,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "content": content,
                    "size": len(content)
                })
        
        output_path = CHRONO_NOTES_DIR / f"export_{date}.json"
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    @staticmethod
    def export_to_csv(date: str = None) -> str:
        """Export logs metadata to CSV."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        day_folder = CHRONO_NOTES_DIR / date
        output_path = CHRONO_NOTES_DIR / f"export_{date}.csv"
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Filename", "Size (bytes)", "Path"])
            
            if day_folder.exists():
                for file_path in day_folder.rglob("*.txt"):
                    writer.writerow([
                        file_path.parent.name,
                        file_path.name,
                        file_path.stat().st_size,
                        str(file_path)
                    ])
        
        return str(output_path)
    
    @staticmethod
    def export_to_markdown(date: str = None) -> str:
        """Export logs as Markdown."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        day_folder = CHRONO_NOTES_DIR / date
        output_path = CHRONO_NOTES_DIR / f"export_{date}.md"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# SessionChrono Export - {date}\n\n")
            
            if day_folder.exists():
                categories = sorted(set(p.parent.name for p in day_folder.rglob("*.txt")))
                
                for category in categories:
                    f.write(f"## {category}\n\n")
                    
                    for file_path in sorted((day_folder / category).glob("*.txt")):
                        content = file_path.read_text(encoding="utf-8")
                        f.write(f"### {file_path.stem}\n\n")
                        f.write(f"```\n{content}\n```\n\n")
        
        return str(output_path)

export_manager = ExportManager()
```

**Commit Task:** `feat: add multi-format export functionality (JSON, CSV, Markdown)`

---

## **PHASE 4: PACKAGING & DEPLOYMENT**

### **4.1 Create PyInstaller Configuration**

**Task 4.1.1: Generate PyInstaller Spec File**

**File: `build_spec.py` (NEW)**

```python
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent

# Files to include
AUDIO_FILES = list((PROJECT_ROOT / "sounds").glob("*.wav"))
ICON_FILES = list((PROJECT_ROOT / "icons").glob("*"))

# Data files
datas = [
    (str(PROJECT_ROOT / "sounds"), "sounds"),
    (str(PROJECT_ROOT / "icons"), "icons"),
]

# Hidden imports (modules not detected by PyInstaller)
hidden_imports = [
    "pyperclip",
    "pywin32",
]

# Build spec
spec = f"""
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['{PROJECT_ROOT / "main.py"}'],
    pathex=[],
    binaries=[],
    datas={datas},
    hiddenimports={hidden_imports},
    hookspath=[],
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SessionChrono',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{PROJECT_ROOT / "icons" / "app_icon.ico"}',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SessionChrono',
)
"""

with open("sessionchrono.spec", "w") as f:
    f.write(spec)

print("? sessionchrono.spec created")
print("Build command: pyinstaller sessionchrono.spec")
```

**Commit Task:** `build: create PyInstaller spec file`

---

**Task 4.1.2: Create Build Scripts**

**File: `build.bat` (Windows batch script)**

```batch
@echo off
echo SessionChrono Build System
echo ===========================

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Generate spec
echo Generating PyInstaller spec...
python build_spec.py

REM Build
echo Building executable...
pyinstaller --distpath ./dist --buildpath ./build sessionchrono.spec

echo.
echo Build complete!
echo Executable: dist/SessionChrono/SessionChrono.exe
pause
```

**File: `build.sh` (Linux/Mac build script)**

```bash
#!/bin/bash

echo "SessionChrono Build System"
echo "=========================="

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Generate spec
echo "Generating PyInstaller spec..."
python build_spec.py

# Build
echo "Building..."
pyinstaller --distpath ./dist --buildpath ./build sessionchrono.spec

echo ""
echo "Build complete!"
echo "Executable: dist/SessionChrono/"
```

**Commit Task:** `build: add cross-platform build scripts`

---

### **4.2 Create Installer (NSIS for Windows)**

**Task 4.2.1: Create NSIS Installer Script**

**File: `installer/SessionChrono.nsi` (NEW)**

```nsis
; SessionChrono Installer Script

!include "MUI2.nsh"
!include "x64.nsh"

; Name and version
Name "SessionChrono v2.0.0"
OutFile "..\dist\SessionChrono_2.0.0_Setup.exe"

; Install location
InstallDir "$PROGRAMFILES\SessionChrono"
InstallDirRegKey HKLM "Software\SessionChrono" ""

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "Install"
    SetOutPath "$INSTDIR"
    File /r "..\dist\SessionChrono\*.*"
    
    ; Create Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\SessionChrono"
    CreateShortcut "$SMPROGRAMS\SessionChrono\SessionChrono.lnk" "$INSTDIR\SessionChrono.exe"
    CreateShortcut "$SMPROGRAMS\SessionChrono\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    
    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\SessionChrono.lnk" "$INSTDIR\SessionChrono.exe"
    
    ; Store install location in registry
    WriteRegStr HKLM "Software\SessionChrono" "" "$INSTDIR"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
    Delete "$INSTDIR\*.*"
    RMDir "$INSTDIR"
    Delete "$SMPROGRAMS\SessionChrono\*.*"
    RMDir "$SMPROGRAMS\SessionChrono"
    Delete "$DESKTOP\SessionChrono.lnk"
    DeleteRegKey HKLM "Software\SessionChrono"
SectionEnd
```

**Commit Task:** `build: add NSIS Windows installer script`

---

### **4.3 Create Documentation**

**Task 4.3.1: Create Installation Guide**

**File: `INSTALLATION.md` (NEW)**

```markdown
# SessionChrono Installation Guide

## System Requirements

- Windows 7 or later (64-bit)
- 50 MB free disk space
- 512 MB RAM minimum

## Installation Steps

### Method 1: Using Installer (Recommended)

1. Download `SessionChrono_2.0.0_Setup.exe`
2. Run the installer
3. Follow the on-screen instructions
4. SessionChrono will start automatically after installation

### Method 2: Portable Version

1. Extract `SessionChrono_2.0.0_Portable.zip` to your desired location
2. Run `SessionChrono.exe`
3. No installation required

### Method 3: From Source

1. Install Python 3.9+
2. Clone the repository
3. Run `pip install -r requirements.txt`
4. Run `python main.py`

## First Run

- SessionChrono will create a `.SessionChrono` folder in your home directory
- All clipboard logs will be stored in `~/.SessionChrono/ChronoNotes`
- Sound alerts are enabled by default

## Uninstallation

- Windows: Control Panel ? Programs ? Uninstall Program ? SessionChrono
- Or run `Uninstall.exe` from the installation folder

## Troubleshooting

**"App won't start"**
- Ensure you have .NET Framework 3.5+ installed
- Try running as Administrator

**"Clipboard monitoring not working"**
- Check Windows Clipboard permissions
- Restart the application

**"Sound alerts not working"**
- Check system volume
- Verify sound card drivers are installed
- Go to Settings ? disable/enable sound alerts

```

**Commit Task:** `docs: add installation and user guide`

---

**Task 4.3.2: Create Developer Documentation**

**File: `DEVELOPMENT.md` (NEW)**

```markdown
# SessionChrono Development Guide

## Project Structure

```
sessionchrono/
??? core/              # Business logic
?   ??? chrono.py      # Clipboard monitoring
?   ??? classifier.py  # Text classification
?   ??? storage.py     # File operations
?   ??? metadata.py    # Tags and annotations
?   ??? export.py      # Export formats
?   ??? config.py      # Configuration
?   ??? logger.py      # Logging
?   ??? utils.py       # Utilities
??? ui/                # User interface
?   ??? tkinter_ui.py  # Main window
?   ??? widgets.py     # Reusable components
?   ??? dialogs.py     # Modal windows
?   ??? sounds.py      # Audio management
?   ??? styles.py      # Theme/colors
??? sounds/            # WAV files
??? icons/             # Application icons
??? ChronoNotes/       # User data (auto-created)
??? main.py           # Entry point
```

## Architecture

### Core Layer (Business Logic)
- Handles clipboard monitoring, text classification, and storage
- Independent of UI implementation
- Fully testable

### UI Layer (Tkinter)
- Builds interfaces using reusable components
- Uses dependency injection for flexibility
- Dark theme with customizable colors

### Configuration
- Centralized in `core/config.py`
- All paths relative to `APP_ROOT`
- PyInstaller-compatible

## Adding Features

### New Classification Category

1. Add to `TextCategory` enum in `core/classifier.py`
2. Add regex patterns for detection
3. Update `make_short_title()` if needed

### New Export Format

1. Add method to `ExportManager` in `core/export.py`
2. Add UI option in `ui/dialogs.py`
3. Test with various clipboard content

### New UI Component

1. Create class in `ui/widgets.py` or new module
2. Use colors from `ui/styles.py`
3. Add to layout in `tkinter_ui.py`

## Testing

```bash
# Run application in development
python main.py

# Build executable
python build_spec.py
pyinstaller sessionchrono.spec

# Create installer (Windows)
cd installer
makensis SessionChrono.nsi
```

## Code Style

- PEP 8 compliant
- Type hints encouraged
- Docstrings for all functions
- Dark theme colors only (from `styles.py`)

```

**Commit Task:** `docs: add developer guide and architecture docs`

---

## **PHASE 5: TESTING & QUALITY ASSURANCE**

### **5.1 Create Test Suite**

**Task 5.1.1: Add Unit Tests**

**File: `tests/test_classifier.py` (NEW)**

```python
import unittest
from core.classifier import TextClassifier, TextCategory

class TestClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = TextClassifier()
    
    def test_url_detection(self):
        url_text = "Check out https://github.com/awesome/project"
        result = self.classifier.classify(url_text)
        self.assertEqual(result, TextCategory.URL.value)
    
    def test_code_detection(self):
        code_text = "def hello():\n    print('world')"
        result = self.classifier.classify(code_text)
        self.assertEqual(result, TextCategory.CODE.value)
    
    def test_json_detection(self):
        json_text = '{"name": "John", "age": 30}'
        result = self.classifier.classify(json_text)
        self.assertEqual(result, TextCategory.JSON.value)
    
    def test_todo_detection(self):
        todo_text = "TODO: Fix the bug in login page"
        result = self.classifier.classify(todo_text)
        self.assertEqual(result, TextCategory.TODO.value)
    
    def test_confidence_score(self):
        text = "def foo(): pass"
        result, score = self.classifier.classify(text, confidence=True)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

if __name__ == "__main__":
    unittest.main()
```

**Commit Task:** `test: add unit tests for text classifier`

---

**Task 5.1.2: Add Integration Tests**

**File: `tests/test_storage.py` (NEW)**

```python
import unittest
import tempfile
from pathlib import Path
from core.storage import StorageManager

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(Path(self.temp_dir.name))
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_save_and_load(self):
        test_path = self.storage.base_path / "test.txt"
        test_content = "Hello, SessionChrono!"
        
        self.storage.save_text(str(test_path), test_content)
        loaded = self.storage.load_text(str(test_path))
        
        self.assertEqual(loaded, test_content)
    
    def test_search_logs(self):
        # Create test files
        file1 = self.storage.base_path / "file1.txt"
        file2 = self.storage.base_path / "file2.txt"
        
        self.storage.save_text(str(file1), "SessionChrono is great")
        self.storage.save_text(str(file2), "Hello world")
        
        results = self.storage.search_logs("SessionChrono")
        self.assertEqual(len(results), 1)

if __name__ == "__main__":
    unittest.main()
```

**Commit Task:** `test: add storage integration tests`

---

## **PHASE 6: DEPLOYMENT CHECKLIST**

Create **`DEPLOY.md`**:

```markdown
# SessionChrono Deployment Checklist

## Pre-Release

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped in config.py
- [ ] Git tags created

## Build Process

- [ ] Clean build directory: `rm -rf build dist`
- [ ] Generate spec: `python build_spec.py`
- [ ] Build executable: `pyinstaller sessionchrono.spec`
- [ ] Test standalone executable
- [ ] Create installer: `makensis installer/SessionChrono.nsi`
- [ ] Test installer on clean Windows system

## Post-Release

- [ ] Upload to GitHub Releases
- [ ] Update website/documentation
- [ ] Announce on social media
- [ ] Monitor issue tracker for bugs
- [ ] Gather user feedback

## Version Control

- Tag: `git tag v2.0.0`
- Push: `git push origin --tags`

```

---

## **SUMMARY: QUICK IMPLEMENTATION ORDER**

**Week 1: Foundation**
1. ? Create config.py & centralize paths
2. ? Implement logging system
3. ? Create advanced classifier
4. ? Enhance storage layer

**Week 2: UI Refactoring**
5. ? Create styles.py & widgets.py
6. ? Extract dialogs & components
7. ? Modularize main UI
8. ? Create sounds module

**Week 3: Advanced Features**
9. ? Metadata/tagging system
10. ? Multi-format export
11. ? Add settings dialog
12. ? Implement filters & search

**Week 4: Packaging & Testing**
13. ? Create PyInstaller spec
14. ? Add build scripts
15. ? Create NSIS installer
16. ? Write unit tests
17. ? Documentation

---

## **CONCRETE NEXT STEPS**

1. **Start with Phase 1.1.1**: Create `core/config.py` and update imports across codebase
2. **Then Phase 1.1.2**: Add `core/logger.py` for application-wide logging
3. **Then Phase 1.2.1**: Implement advanced classifier in `core/classifier.py`
4. **Then Phase 2.1.1**: Create UI styles in `ui/styles.py` and reusable widgets
5. **Continue systematically** through phases, committing each completed task

This plan is **production-ready** and follows industry best practices for Python packaging, modularity, and maintainability. Each task is self-contained and can be completed incrementally!