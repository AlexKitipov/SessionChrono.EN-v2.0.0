import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog

from core.app_controller import ApplicationController, ClipboardEntry
from core.logger import APP_LOG_DIR, get_logger
from ui.sounds import SoundManager
from ui.components import ClipboardHistoryPanel, EditorPanel, LastCopiedPanel
from ui.dialogs import EntryDetailsDialog, ExportDialog, SearchDialog, SettingsDialog, show_about
from ui.styles import create_dark_menu, apply_window_style
from ui.widgets import StatusBar

logger = get_logger()


# ---------- MAIN UI ----------
class SessionChronoUI(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_window_style(self)

        self.controller = ApplicationController(
            on_entry_saved=self.schedule_clipboard_entry_render,
            on_error=self.schedule_controller_error,
        )
        self.sound = SoundManager(self, self.controller.settings)
        self.status_var = tk.StringVar()
        self.current_file_path = None

        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        if self.controller.settings.start_monitoring_on_launch:
            self.status_var.set("Starting clipboard monitoring...")
        else:
            self.status_var.set("Clipboard monitoring is paused by settings.")
        self.sound.play("start")

        self.controller.start()
        logger.info("SessionChrono UI initialized; application logs are stored in %s", APP_LOG_DIR)

    # ---------- DARK MENU ----------
    def _build_menu(self):
        menubar = create_dark_menu(self)

        # FILE
        file_menu = create_dark_menu(menubar)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # TOOLS
        tools_menu = create_dark_menu(menubar)
        tools_menu.add_command(
            label="Pause / Resume Monitoring",
            accelerator="Ctrl+P",
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
            label="Export Notes...",
            command=self.show_export_dialog,
        )
        tools_menu.add_command(
            label="Search Logs",
            accelerator="Ctrl+F",
            command=self.search_logs_ui,
        )
        tools_menu.add_command(
            label="Settings",
            command=self.show_settings,
        )
        tools_menu.add_command(
            label="Entry Details",
            command=self.show_entry_details,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # HELP
        help_menu = create_dark_menu(menubar)
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

        self.editor_panel = EditorPanel(main_frame)
        self.editor_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.editor = self.editor_panel.text

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=2)
        right_frame.columnconfigure(0, weight=1)

        self.last_clip_panel = LastCopiedPanel(right_frame)
        self.last_clip_panel.grid(row=0, column=0, sticky="nsew")
        self.last_clip_box = self.last_clip_panel.text

        self.history_component = ClipboardHistoryPanel(
            right_frame,
            self.on_history_select,
            self.clear_history,
            self.show_selected_entry_details,
            self.open_selected_history_folder,
            self.copy_selected_history_path,
        )
        self.history_component.grid(row=1, column=0, sticky="nsew")
        self.history_list = self.history_component.listbox

        self.status_bar = StatusBar(self, self.status_var)
        self.status_bar.pack(side="bottom", fill="x")

    def _bind_shortcuts(self):
        self.bind_all("<Control-n>", lambda _event: self.new_file())
        self.bind_all("<Control-o>", lambda _event: self.open_file())
        self.bind_all("<Control-s>", lambda _event: self.save_file())
        self.bind_all("<Control-Shift-S>", lambda _event: self.save_file_as())
        self.bind_all("<Control-F>", lambda _event: self.search_logs_ui())
        self.bind_all("<Control-f>", lambda _event: self.search_logs_ui())
        self.bind_all("<Control-p>", lambda _event: self.toggle_logging())

    # ---------- CLIPBOARD EVENT ----------
    def schedule_clipboard_entry_render(self, entry: ClipboardEntry):
        self.after(0, lambda: self.render_clipboard_entry(entry))

    def schedule_controller_error(self, message: str, error: Exception):
        self.after(0, lambda: self.report_controller_error(message, error))

    def render_clipboard_entry(self, entry: ClipboardEntry):
        self.refresh_history()
        self.last_clip_panel.set_text(entry.text)
        self.status_var.set(f"Saved clipboard: {entry.title}")
        self.sound.play("copy")

    def report_controller_error(self, message: str, error: Exception):
        self.status_var.set(f"{message}: {error}")
        self.sound.play("error")

    def refresh_history(self):
        self.history_component.set_items(self.controller.history_items)

    # ---------- HISTORY ----------
    def on_history_select(self, _event):
        idx = self.history_component.selected_index()
        if idx is None:
            return
        item = self.controller.history_entry_at(idx)
        if item is None:
            return

        try:
            result = self.controller.load_text(item.path)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            self.editor_panel.set_text(result.content)
            self.current_file_path = item.path
            self.status_var.set(f"Opened: {os.path.basename(item.path)}")
            self.sound.play("open")
        except Exception as e:
            logger.exception("Failed to open history item: %s", item.path)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")


    def selected_history_item(self):
        """Return the currently selected history entry, if any."""

        idx = self.history_component.selected_index()
        if idx is None:
            self.status_var.set("No history entry selected.")
            self.sound.play("error")
            return None
        item = self.controller.history_entry_at(idx)
        if item is None:
            self.status_var.set("No history entry selected.")
            self.sound.play("error")
        return item

    def open_selected_history_folder(self):
        """Open the folder containing the selected history entry."""

        item = self.selected_history_item()
        if item is None:
            return
        self.open_containing_folder(item.path)

    def copy_selected_history_path(self):
        """Copy the selected history entry path to the clipboard."""

        item = self.selected_history_item()
        if item is None:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(item.path)
            self.status_var.set("Copied entry path to clipboard.")
            self.sound.play("save")
        except Exception as e:
            logger.exception("Failed to copy history path: %s", item.path)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def open_containing_folder(self, path: str):
        """Open the containing folder for *path*, even if the file is missing."""

        try:
            folder = os.path.dirname(path) if path else str(self.controller.notes_dir)
            if not folder:
                folder = str(self.controller.notes_dir)
            os.makedirs(folder, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            logger.info("Opened containing folder: %s", folder)
            self.status_var.set("Opened containing folder.")
            self.sound.play("open")
        except Exception as e:
            logger.exception("Failed to open containing folder for: %s", path)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def clear_history(self):
        self.controller.clear_history()
        self.refresh_history()
        self.status_var.set("Session history cleared.")

    # ---------- FILE OPS ----------
    def new_file(self):
        logger.info("Creating new editor document")
        self.editor_panel.clear()
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
            result = self.controller.load_text(path)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            content = result.content
            self.editor_panel.set_text(content)
            self.current_file_path = path
            self.status_var.set(f"Opened: {os.path.basename(path)}")
            self.sound.play("open")
        except Exception as e:
            logger.exception("Failed to open file: %s", path)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def save_file(self):
        if not self.current_file_path:
            return self.save_file_as()
        try:
            content = self.editor_panel.get_text()
            result = self.controller.save_text(self.current_file_path, content)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            self.status_var.set(f"Saved: {os.path.basename(self.current_file_path)}")
            self.sound.play("save")
        except Exception as e:
            logger.exception("Failed to save file: %s", self.current_file_path)
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
            content = self.editor_panel.get_text()
            result = self.controller.save_text(path, content)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            self.current_file_path = path
            self.status_var.set(f"Saved As: {os.path.basename(path)}")
            self.sound.play("save")
        except Exception as e:
            logger.exception("Failed to save file as: %s", path)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    # ---------- TOOLS ----------
    def toggle_logging(self):
        active = self.controller.toggle_monitoring()
        if active:
            self.status_var.set("Clipboard monitoring resumed.")
            self.sound.play("resume")
        else:
            self.status_var.set("Clipboard monitoring paused.")
            self.sound.play("pause")

    def open_logs_folder(self):
        try:
            notes_dir = self.controller.notes_dir
            notes_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(str(notes_dir))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(notes_dir)])
            else:
                subprocess.Popen(["xdg-open", str(notes_dir)])
            logger.info("Opened notes folder: %s", notes_dir)
            self.status_var.set("Opened logs folder.")
            self.sound.play("open")
        except Exception as e:
            logger.exception("Failed to open notes folder: %s", self.controller.notes_dir)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def open_last_record(self):
        last_record_path = self.controller.last_record_path
        if not last_record_path or not os.path.exists(last_record_path):
            self.status_var.set("No last auto-note.")
            self.sound.play("error")
            return
        try:
            result = self.controller.load_text(last_record_path)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            self.editor_panel.set_text(result.content)
            self.current_file_path = last_record_path
            self.status_var.set("Opened last auto-note.")
            self.sound.play("open")
        except Exception as e:
            logger.exception("Failed to open last auto-note: %s", last_record_path)
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def create_zip(self):
        try:
            zip_result = self.controller.create_today_zip()
            zip_path = zip_result.path
            if not zip_result.success or not zip_path:
                self.status_var.set("No logs for today.")
                self.sound.play("error")
                return
            logger.info("Created ZIP from UI action: %s", zip_path)
            self.status_var.set(f"Created ZIP: {os.path.basename(zip_path)}")
            self.sound.play("save")
        except Exception as e:
            logger.exception("Failed to create ZIP from UI action")
            self.status_var.set(f"Error: {e}")
            self.sound.play("error")

    def show_export_dialog(self):
        ExportDialog(
            self,
            self.controller.storage,
            self.report_dialog_success,
            self.report_dialog_error,
        )

    def search_logs_ui(self):
        dialog = SearchDialog(
            self,
            self.controller.storage,
            self.open_search_result,
            self.report_dialog_error,
        )
        dialog.show()

    def open_search_result(self, path: str, content: str):
        self.editor_panel.set_text(content)
        self.current_file_path = path
        self.status_var.set(f"Opened from search: {os.path.basename(path)}")
        self.sound.play("open")

    def report_dialog_success(self, message: str):
        self.status_var.set(message)
        self.sound.play("save")

    def report_dialog_error(self, message: str):
        self.status_var.set(message)
        self.sound.play("error")

    # ---------- ABOUT ----------
    def show_about(self):
        show_about(self)

    def show_settings(self):
        SettingsDialog(self, self.controller.settings, self.apply_settings)

    def apply_settings(self, settings, migrate_data: bool = False):
        applied = self.controller.apply_settings(settings, migrate_data=migrate_data)
        self.sound.apply_settings(applied)
        self.status_var.set("Settings saved.")
        return applied

    def show_selected_entry_details(self):
        idx = self.history_component.selected_index()
        if idx is None:
            return self.show_entry_details()
        item = self.controller.history_entry_at(idx)
        if item is None:
            return self.show_entry_details()
        self.current_file_path = item.path
        self.editor_panel.set_text(item.text)
        return self.show_entry_details()

    def show_entry_details(self):
        title = os.path.basename(self.current_file_path) if self.current_file_path else "Current Editor"
        metadata = None
        if self.current_file_path:
            metadata = self.controller.load_metadata_by_path(self.current_file_path)
        EntryDetailsDialog(
            self,
            title=title,
            path=self.current_file_path or "",
            content=self.editor_panel.get_text(),
            metadata=metadata,
            on_save=self.save_entry_metadata,
        )

    def save_entry_metadata(self, metadata, tags: list[str], note: str):
        updated = self.controller.update_metadata(metadata.entry_id, user_tags=tags, note=note)
        self.status_var.set("Entry metadata saved.")
        self.sound.play("save")
        return updated

    # ---------- CLOSE ----------
    def on_close(self):
        try:
            self.controller.shutdown()
        except Exception:
            logger.exception("Failed to shut down application controller")
        self.destroy()


if __name__ == "__main__":
    app = SessionChronoUI()
    app.mainloop()
# ---------- ENTRY POINT ----------
def start_app():
    app = SessionChronoUI()
    app.mainloop()
