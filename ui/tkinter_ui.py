import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from core.chrono import ClipboardMonitor
from core.config import (
    APP_NAME,
    APP_VERSION,
    LOG_ROOT,
    SOUNDS_DIR,
    WINDOW_DEFAULT_GEOMETRY,
    WINDOW_TITLE,
    ensure_user_directories,
)
from core.storage import save_text, load_text, create_today_zip, search_logs
from core.utils import build_filename

# ---------- SOUND MANAGER ----------
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

SOUND_FILES = {
    "start":  "start.wav",
    "copy":   "copy.wav",
    "error":  "error.wav",
    "pause":  "pause.wav",
    "resume": "resume.wav",
    "save":   "save.wav",
    "open":   "open.wav",
}

BEEP_PATTERNS = {
    "start":  (900, 120),
    "copy":   (1200, 120),
    "error":  (400, 250),
    "pause":  (700, 120),
    "resume": (900, 180),
    "save":   (800, 120),
    "open":   (1000, 100),
}


class SoundManager:
    def __init__(self, root: tk.Tk):
        self.root = root

    def play(self, event: str):
        if event not in BEEP_PATTERNS:
            return

        if HAS_WINSOUND:
            wav_name = SOUND_FILES.get(event)
            if wav_name:
                wav_path = SOUNDS_DIR / wav_name
                if wav_path.exists():
                    try:
                        winsound.PlaySound(
                            str(wav_path),
                            winsound.SND_FILENAME | winsound.SND_ASYNC
                        )
                        return
                    except Exception:
                        pass

            freq, dur = BEEP_PATTERNS[event]
            try:
                winsound.Beep(freq, dur)
                return
            except Exception:
                pass

        try:
            self.root.bell()
        except Exception:
            pass


# ---------- RIGHT CLICK MENU ----------
class RightClickMenu:
    def __init__(self, widget):
        self.widget = widget
        self.menu = tk.Menu(
            widget,
            tearoff=0,
            bg="#2d2d2d",
            fg="white",
            activebackground="#3e3e3e",
            activeforeground="white",
        )

        self.menu.add_command(label="Copy", command=self.copy)
        self.menu.add_command(label="Cut", command=self.cut)
        self.menu.add_command(label="Paste", command=self.paste)
        self.menu.add_separator()
        self.menu.add_command(label="Select All", command=self.select_all)
        self.menu.add_command(label="Clear", command=self.clear)

        widget.bind("<Button-3>", self.show_menu)

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def copy(self):
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
        except Exception:
            pass

    def cut(self):
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
            self.widget.delete("sel.first", "sel.last")
        except Exception:
            pass

    def paste(self):
        try:
            text = self.widget.clipboard_get()
            self.widget.insert(tk.INSERT, text)
        except Exception:
            pass

    def select_all(self):
        self.widget.tag_add("sel", "1.0", "end")

    def clear(self):
        self.widget.delete("1.0", "end")


# ---------- MAIN UI ----------
class SessionChronoUI(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_user_directories()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_DEFAULT_GEOMETRY)
        self.configure(bg="#2d2d2d")

        self.sound = SoundManager(self)
        self.status_var = tk.StringVar()
        self.current_file_path = None
        self.last_record_path = None
        self.history = []
        self.logging_active = True

        self._build_style()
        self._build_menu()
        self._build_layout()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_var.set("Starting clipboard monitoring...")
        self.sound.play("start")

        # Clipboard monitor
        self.monitor = ClipboardMonitor(self.handle_new_clipboard_item)
        self.monitor.start()

    # ---------- UI STYLE ----------
    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            ".",
            background="#2d2d2d",
            foreground="#ffffff",
            font=("Segoe UI", 10),
        )
        style.configure("TButton", background="#3e3e3e", foreground="#ffffff")
        style.map("TButton", background=[("active", "#505050")])
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")

    # ---------- DARK MENU ----------
    def _build_menu(self):
        menubar = tk.Menu(
            self,
            bg="#2d2d2d",
            fg="#ffffff",
            activebackground="#3e3e3e",
            activeforeground="#ffffff",
            tearoff=0,
        )

        def dark_menu(parent):
            return tk.Menu(
                parent,
                bg="#2d2d2d",
                fg="#ffffff",
                activebackground="#3e3e3e",
                activeforeground="#ffffff",
                tearoff=0,
            )

        # FILE
        file_menu = dark_menu(menubar)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open...", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # TOOLS
        tools_menu = dark_menu(menubar)
        tools_menu.add_command(
            label="Pause / Resume Monitoring",
            command=self.toggle_logging,
        )
        tools_menu.add_command(
            label="Open Logs Folder",
            command=self.open_logs_folder,
        )
        tools_menu.add_command(
            label="Open Last Auto-Note",
            command=self.open_last_record,
        )
        tools_menu.add_command(
            label="Create ZIP of Today",
            command=self.create_zip,
        )
        tools_menu.add_command(
            label="Search Logs",
            command=self.search_logs_ui,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # HELP
        help_menu = dark_menu(menubar)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # ---------- LAYOUT ----------
    def _build_layout(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)

        # LEFT — EDITOR
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        self.editor = tk.Text(
            left_frame,
            wrap="word",
            font=("Consolas", 11),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            undo=True,
        )
        editor_scroll = ttk.Scrollbar(left_frame, command=self.editor.yview)
        self.editor.configure(yscrollcommand=editor_scroll.set)

        self.editor.grid(row=0, column=0, sticky="nsew")
        editor_scroll.grid(row=0, column=1, sticky="ns")

        RightClickMenu(self.editor)

        # RIGHT — PANEL
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        right_frame.rowconfigure(1, weight=1)
        right_frame.rowconfigure(3, weight=2)
        right_frame.columnconfigure(0, weight=1)

        ttk.Label(
            right_frame,
            text="Last Copied",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.last_clip_box = tk.Text(
            right_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            height=12,
            insertbackground="white",
        )
        clip_scroll = ttk.Scrollbar(right_frame, command=self.last_clip_box.yview)
        self.last_clip_box.configure(yscrollcommand=clip_scroll.set)

        self.last_clip_box.grid(row=1, column=0, sticky="nsew")
        clip_scroll.grid(row=1, column=1, sticky="ns")

        RightClickMenu(self.last_clip_box)

        ttk.Label(
            right_frame,
            text="Clipboard History",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=2, column=0, sticky="w", pady=(10, 5))

        self.history_list = tk.Listbox(
            right_frame,
            bg="#1e1e1e",
            fg="#d4d4d4",
            activestyle="none",
            selectbackground="#264f78",
            font=("Consolas", 9),
        )
        hist_scroll = ttk.Scrollbar(right_frame, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=hist_scroll.set)

        self.history_list.grid(row=3, column=0, sticky="nsew")
        hist_scroll.grid(row=3, column=1, sticky="ns")

        self.history_list.bind("<<ListboxSelect>>", self.on_history_select)

        ttk.Button(
            right_frame,
            text="Clear Session History",
            command=self.clear_history,
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))

        # STATUS BAR
        status_frame = tk.Frame(self, bg="#007acc")
        status_frame.pack(side="bottom", fill="x")
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg="#007acc",
            fg="white",
            anchor="w",
            padx=5,
            pady=3,
        ).pack(fill="x")

    # ---------- CLIPBOARD EVENT ----------
    def handle_new_clipboard_item(self, text: str):
        try:
            path, folder, short, category = build_filename(text)
            save_text(path, text)
            self.last_record_path = path

            item_title = f"[{category}] {short}"
            self.history.insert(0, {"title": item_title, "path": path, "text": text})
            self.history = self.history[:20]

            self.refresh_history()

            self.last_clip_box.delete("1.0", tk.END)
            self.last_clip_box.insert("1.0", text)

            self.status_var.set(f"Saved clipboard: {item_title}")
            self.sound.play("copy")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def refresh_history(self):
        self.history_list.delete(0, tk.END)
        for item in self.history:
            self.history_list.insert(tk.END, item["title"])

    # ---------- HISTORY ----------
    def on_history_select(self, _event):
        sel = self.history_list.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.history[idx]

        try:
            content = load_text(item["path"])
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", content)
            self.current_file_path = item["path"]
            self.status_var.set(f"Opened: {os.path.basename(item['path'])}")
            self.sound.play("open")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def clear_history(self):
        self.history.clear()
        self.refresh_history()
        self.status_var.set("Session history cleared.")

    # ---------- FILE OPS ----------
    def new_file(self):
        self.editor.delete("1.0", tk.END)
        self.current_file_path = None
        self.status_var.set("New file.")
        self.sound.play("open")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            content = load_text(path)
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", content)
            self.current_file_path = path
            self.status_var.set(f"Opened: {os.path.basename(path)}")
            self.sound.play("open")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def save_file(self):
        if not self.current_file_path:
            return self.save_file_as()
        try:
            content = self.editor.get("1.0", tk.END)
            save_text(self.current_file_path, content)
            self.status_var.set(f"Saved: {os.path.basename(self.current_file_path)}")
            self.sound.play("save")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            content = self.editor.get("1.0", tk.END)
            save_text(path, content)
            self.current_file_path = path
            self.status_var.set(f"Saved As: {os.path.basename(path)}")
            self.sound.play("save")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    # ---------- TOOLS ----------
    def toggle_logging(self):
        # Важно: да не стартираме монитор-а многократно
        self.logging_active = not self.logging_active

        if self.logging_active:
            try:
                self.monitor.start()
            except RuntimeError:
                # ако вече е стартиран, игнорираме
                pass
            self.status_var.set("Clipboard monitoring resumed.")
            self.sound.play("resume")
        else:
            try:
                self.monitor.stop()
            except Exception:
                pass
            self.status_var.set("Clipboard monitoring paused.")
            self.sound.play("pause")

    def open_logs_folder(self):
        try:
            LOG_ROOT.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(str(LOG_ROOT))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(LOG_ROOT)])
            else:
                subprocess.Popen(["xdg-open", str(LOG_ROOT)])
            self.status_var.set("Opened logs folder.")
            self.sound.play("open")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def open_last_record(self):
        if not self.last_record_path or not os.path.exists(self.last_record_path):
            self.status_var.set("No last auto-note.")
            self.sound.play("error")
            return
        try:
            content = load_text(self.last_record_path)
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", content)
            self.current_file_path = self.last_record_path
            self.status_var.set("Opened last auto-note.")
            self.sound.play("open")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def create_zip(self):
        zip_path = create_today_zip()
        if not zip_path:
            self.status_var.set("No logs for today.")
            self.sound.play("error")
            return
        self.status_var.set(f"Created ZIP: {os.path.basename(zip_path)}")
        self.sound.play("save")

    def search_logs_ui(self):
        query = simpledialog.askstring("Search Logs", "Enter text:")
        if not query:
            return

        matches = search_logs(query)
        if not matches:
            messagebox.showinfo("Search Logs", "No matches found.")
            return

        win = tk.Toplevel(self)
        win.title("Search Results")
        win.geometry("600x400")
        win.configure(bg="#2d2d2d")

        lb = tk.Listbox(
            win,
            bg="#1e1e1e",
            fg="#d4d4d4",
            selectbackground="#3e3e3e",
            font=("Segoe UI", 9),
        )
        lb.pack(fill="both", expand=True, padx=10, pady=10)

        for p in matches:
            lb.insert(tk.END, p)

        def open_selected(_event=None):
            sel = lb.curselection()
            if not sel:
                return
            path = lb.get(sel[0])
            try:
                content = load_text(path)
                self.editor.delete("1.0", tk.END)
                self.editor.insert("1.0", content)
                self.current_file_path = path
                self.status_var.set(
                    f"Opened from search: {os.path.basename(path)}"
                )
                self.sound.play("open")
                win.destroy()
            except Exception as e:
                self.status_var.set(f"Error: {e}")
                self.sound.play("error")

        lb.bind("<Double-Button-1>", open_selected)

    # ---------- ABOUT ----------
    def show_about(self):
        messagebox.showinfo(
            "About SessionChrono",
            f"{APP_NAME} {APP_VERSION} – Smart clipboard-logging notepad\n"
            "Automatically saves copied text into categorized files with timestamps.\n"
            "Includes editor, history, search, ZIP archiving, and sound alerts."
        )

    # ---------- CLOSE ----------
    def on_close(self):
        try:
            self.monitor.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = SessionChronoUI()
    app.mainloop()
# ---------- ENTRY POINT ----------
def start_app():
    app = SessionChronoUI()
    app.mainloop()
