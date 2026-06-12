"""Modular Tkinter dialogs for SessionChrono."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Protocol

from core.config import APP_NAME, APP_VERSION
from core.export import ExportFilters, default_export_filename
from core.logger import get_logger
from core.metadata import EntryMetadata
from core.settings import AppSettings, DEFAULT_SOUND_EVENTS, SUPPORTED_THEMES
from core.storage import SearchResult
from ui.styles import COLOR_WINDOW_BG, DIALOG_GEOMETRIES
from ui.widgets import SearchResultsList

logger = get_logger()


class SearchProvider(Protocol):
    """Protocol for storage objects that can search and load note text."""

    def search_logs(self, query: str = "", **filters) -> list[SearchResult]:
        """Return structured note search results for *query* and filters."""

    def load_text(self, path: str):
        """Load note text from *path*."""


OpenResultCallback = Callable[[str, str], None]
ErrorCallback = Callable[[str], None]


def show_info(parent: tk.Misc, title: str, message: str) -> None:
    """Show a parented informational message box."""

    messagebox.showinfo(title, message, parent=parent)


def show_error(parent: tk.Misc, title: str, message: str) -> None:
    """Show a parented error message box."""

    messagebox.showerror(title, message, parent=parent)


def show_about(parent: tk.Misc) -> None:
    """Display SessionChrono application information."""

    show_info(
        parent,
        "About SessionChrono",
        f"{APP_NAME} {APP_VERSION} – Smart clipboard-logging notepad\n"
        "Automatically saves copied text into categorized files with timestamps.\n"
        "Includes editor, history, search, ZIP archiving, and sound alerts.",
    )


class SearchDialog:
    """Prompt for a search query, render results, and open selected matches."""

    def __init__(
        self,
        parent: tk.Misc,
        storage: SearchProvider,
        on_open_result: OpenResultCallback,
        on_error: ErrorCallback | None = None,
    ):
        self.parent = parent
        self.storage = storage
        self.on_open_result = on_open_result
        self.on_error = on_error
        self.matches: list[SearchResult] = []
        self.window: tk.Toplevel | None = None
        self.results_list: SearchResultsList | None = None
        self.query_var: tk.StringVar | None = None
        self.category_var: tk.StringVar | None = None
        self.date_from_var: tk.StringVar | None = None
        self.date_to_var: tk.StringVar | None = None
        self.tag_var: tk.StringVar | None = None
        self.filename_var: tk.StringVar | None = None
        self.summary_var: tk.StringVar | None = None

    def show(self) -> None:
        """Open a searchable dialog with structured filter controls."""

        self._build_results_window("")

    def run_search(self) -> None:
        """Execute the current search form and refresh the results list."""

        if self.results_list is None:
            return
        query = self.query_var.get().strip() if self.query_var else ""
        filters = {
            "category": self.category_var.get().strip() if self.category_var else "",
            "date_from": self.date_from_var.get().strip() if self.date_from_var else "",
            "date_to": self.date_to_var.get().strip() if self.date_to_var else "",
            "tag": self.tag_var.get().strip() if self.tag_var else "",
            "filename": self.filename_var.get().strip() if self.filename_var else "",
        }
        try:
            self.matches = self.storage.search_logs(query, **filters)
        except Exception as exc:
            logger.exception("Search failed for query: %r filters=%s", query, filters)
            self._report_error(f"Search failed: {exc}")
            return

        self.results_list.set_results(self.matches)
        if self.summary_var is not None:
            self.summary_var.set(f"{len(self.matches)} match(es) found.")
        if self.matches:
            self.results_list.selection_clear(0, tk.END)
            self.results_list.selection_set(0)
            self.results_list.activate(0)
        logger.info("Search dialog found %d match(es)", len(self.matches))

    def _build_results_window(self, query: str) -> None:
        self.window = tk.Toplevel(self.parent)
        self.window.title("Search Logs")
        self.window.geometry(DIALOG_GEOMETRIES["search_results"])
        self.window.configure(bg=COLOR_WINDOW_BG)
        self.window.transient(self.parent)

        self.query_var = tk.StringVar(value=query)
        self.category_var = tk.StringVar()
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()
        self.tag_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.summary_var = tk.StringVar(value="Enter filters, then choose Search.")

        frame = ttk.Frame(self.window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        filters = ttk.LabelFrame(frame, text="Filters", padding=8)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for column in range(6):
            filters.columnconfigure(column, weight=1)

        ttk.Label(filters, text="Text").grid(row=0, column=0, sticky="w")
        text_entry = ttk.Entry(filters, textvariable=self.query_var)
        text_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 6), pady=(0, 6))
        text_entry.bind("<Return>", lambda _event: self.run_search())

        ttk.Label(filters, text="Category").grid(row=0, column=2, sticky="w")
        ttk.Entry(filters, textvariable=self.category_var).grid(row=1, column=2, sticky="ew", padx=(0, 6), pady=(0, 6))

        ttk.Label(filters, text="Tag").grid(row=0, column=3, sticky="w")
        ttk.Entry(filters, textvariable=self.tag_var).grid(row=1, column=3, sticky="ew", padx=(0, 6), pady=(0, 6))

        ttk.Label(filters, text="Filename / title").grid(row=0, column=4, columnspan=2, sticky="w")
        ttk.Entry(filters, textvariable=self.filename_var).grid(row=1, column=4, columnspan=2, sticky="ew", pady=(0, 6))

        ttk.Label(filters, text="From date (YYYY-MM-DD)").grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Entry(filters, textvariable=self.date_from_var).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 6))

        ttk.Label(filters, text="To date (YYYY-MM-DD)").grid(row=2, column=2, columnspan=2, sticky="w")
        ttk.Entry(filters, textvariable=self.date_to_var).grid(row=3, column=2, columnspan=2, sticky="ew", padx=(0, 6))

        ttk.Button(filters, text="Search", command=self.run_search).grid(row=3, column=4, sticky="ew", padx=(0, 6))
        ttk.Button(filters, text="Clear", command=self.clear_filters).grid(row=3, column=5, sticky="ew")

        ttk.Label(frame, textvariable=self.summary_var).grid(row=1, column=0, sticky="w", pady=(0, 6))

        self.results_list = SearchResultsList(frame)
        self.results_list.grid(row=2, column=0, sticky="nsew")
        self.results_list.set_results(self.matches)
        self.results_list.bind("<Double-Button-1>", self.open_selected)
        self.results_list.bind("<Return>", self.open_selected)
        self.results_list.focus_set()

        button_row = ttk.Frame(frame)
        button_row.grid(row=3, column=0, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Open", command=self.open_selected).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Close", command=self.window.destroy).pack(side="left")
        text_entry.focus_set()

    def clear_filters(self) -> None:
        """Clear all search controls and current results."""

        for variable in (
            self.query_var,
            self.category_var,
            self.date_from_var,
            self.date_to_var,
            self.tag_var,
            self.filename_var,
        ):
            if variable is not None:
                variable.set("")
        self.matches = []
        if self.results_list is not None:
            self.results_list.set_results([])
        if self.summary_var is not None:
            self.summary_var.set("Enter filters, then choose Search.")

    def open_selected(self, _event: tk.Event | None = None) -> None:
        """Load the selected match and pass its content to the owner."""

        if self.results_list is None:
            return
        selection = self.results_list.curselection()
        if not selection:
            return
        result_item = self.matches[selection[0]]
        path = result_item.path
        try:
            result = self.storage.load_text(path)
            if not result.success:
                raise RuntimeError(result.error or result.message)
            self.on_open_result(path, result.content)
            if self.window is not None:
                self.window.destroy()
        except Exception as exc:
            logger.exception("Failed to open search result: %s", path)
            self._report_error(f"Error: {exc}")

    def _report_error(self, message: str) -> None:
        if self.on_error is not None:
            self.on_error(message)
        else:
            show_error(self.parent, "SessionChrono", message)


class SettingsDialog(tk.Toplevel):
    """Persistent settings editor for user preferences."""

    def __init__(
        self,
        parent: tk.Misc,
        settings: AppSettings,
        on_save: Callable[[AppSettings, bool], AppSettings] | None = None,
    ):
        super().__init__(parent)
        self.title("Settings")
        self.geometry(DIALOG_GEOMETRIES["settings"])
        self.configure(bg=COLOR_WINDOW_BG)
        self.transient(parent)
        self.settings = settings.normalized()
        self.on_save = on_save
        self.start_monitoring_var = tk.BooleanVar(value=self.settings.start_monitoring_on_launch)
        self.poll_interval_var = tk.StringVar(value=str(self.settings.clipboard_poll_interval))
        self.history_limit_var = tk.StringVar(value=str(self.settings.max_history_entries))
        self.sound_enabled_var = tk.BooleanVar(value=self.settings.sound_enabled)
        self.sound_volume_var = tk.DoubleVar(value=self.settings.sound_volume)
        self.export_dir_var = tk.StringVar(value=self.settings.default_export_directory)
        self.data_dir_var = tk.StringVar(value=self.settings.data_directory)
        self.migrate_data_var = tk.BooleanVar(value=False)
        self.theme_var = tk.StringVar(value=self.settings.theme)
        self.event_vars = {
            event: tk.BooleanVar(value=self.settings.sound_events.get(event, True))
            for event in DEFAULT_SOUND_EVENTS
        }
        self._build_body()

    def _build_body(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Settings", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        ttk.Checkbutton(
            frame,
            text="Start clipboard monitoring on launch",
            variable=self.start_monitoring_var,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=3)

        ttk.Label(frame, text="Clipboard polling interval (seconds):").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.poll_interval_var, width=10).grid(row=2, column=1, sticky="w", pady=3)

        ttk.Label(frame, text="Maximum in-session history entries:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.history_limit_var, width=10).grid(row=3, column=1, sticky="w", pady=3)

        ttk.Separator(frame).grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Checkbutton(frame, text="Enable sounds", variable=self.sound_enabled_var).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=3
        )
        ttk.Label(frame, text="Sound volume:").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Scale(frame, from_=0, to=100, variable=self.sound_volume_var, orient="horizontal").grid(
            row=6, column=1, sticky="ew", pady=3
        )
        ttk.Label(frame, text="Event sounds:").grid(row=7, column=0, sticky="nw", pady=3)
        events_frame = ttk.Frame(frame)
        events_frame.grid(row=7, column=1, columnspan=2, sticky="w", pady=3)
        for index, (event, variable) in enumerate(self.event_vars.items()):
            ttk.Checkbutton(events_frame, text=event.title(), variable=variable).grid(
                row=index // 3, column=index % 3, sticky="w", padx=(0, 10)
            )

        ttk.Separator(frame).grid(row=8, column=0, columnspan=3, sticky="ew", pady=8)
        self._directory_row(frame, 9, "Default export directory:", self.export_dir_var, self.choose_export_dir)
        self._directory_row(frame, 10, "Data directory:", self.data_dir_var, self.choose_data_dir)
        ttk.Checkbutton(
            frame,
            text="Copy existing notes into the new data directory when saving",
            variable=self.migrate_data_var,
        ).grid(row=11, column=1, columnspan=2, sticky="w", pady=3)

        ttk.Label(frame, text="Theme:").grid(row=12, column=0, sticky="w", pady=(10, 3))
        ttk.OptionMenu(frame, self.theme_var, self.theme_var.get(), *sorted(SUPPORTED_THEMES)).grid(
            row=12, column=1, sticky="w", pady=(10, 3)
        )
        ttk.Label(frame, text="Dark is the current default; this setting is reserved for future themes.").grid(
            row=13, column=1, columnspan=2, sticky="w"
        )

        button_row = ttk.Frame(frame)
        button_row.grid(row=14, column=1, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(button_row, text="Save", command=self.save).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Cancel", command=self.destroy).pack(side="left")

    def _directory_row(self, frame: ttk.Frame, row: int, label: str, variable: tk.StringVar, command) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=3)
        ttk.Button(frame, text="Browse...", command=command).grid(row=row, column=2, sticky="e", padx=(6, 0), pady=3)

    def choose_export_dir(self) -> None:
        selected = filedialog.askdirectory(parent=self, initialdir=self.export_dir_var.get() or None)
        if selected:
            self.export_dir_var.set(selected)

    def choose_data_dir(self) -> None:
        selected = filedialog.askdirectory(parent=self, initialdir=self.data_dir_var.get() or None)
        if selected:
            self.data_dir_var.set(selected)

    def save(self) -> None:
        try:
            settings = self.settings.with_updates(
                start_monitoring_on_launch=self.start_monitoring_var.get(),
                clipboard_poll_interval=float(self.poll_interval_var.get()),
                max_history_entries=int(self.history_limit_var.get()),
                sound_enabled=self.sound_enabled_var.get(),
                sound_volume=int(round(self.sound_volume_var.get())),
                sound_events={event: variable.get() for event, variable in self.event_vars.items()},
                default_export_directory=self.export_dir_var.get(),
                data_directory=self.data_dir_var.get(),
                theme=self.theme_var.get(),
            )
            if self.on_save is not None:
                settings = self.on_save(settings, self.migrate_data_var.get())
            self.settings = settings
            show_info(self, "Settings", "Settings saved.")
            self.destroy()
        except Exception as exc:
            logger.exception("Failed to save settings")
            show_error(self, "Settings", f"Failed to save settings: {exc}")


class EntryDetailsDialog(tk.Toplevel):
    """Entry details dialog with editable tags and annotation."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        path: str,
        content: str,
        metadata: EntryMetadata | None = None,
        on_save: Callable[[EntryMetadata | None, str, str, list[str], str], EntryMetadata] | None = None,
    ):
        super().__init__(parent)
        self.title("Entry Details")
        self.geometry(DIALOG_GEOMETRIES["entry_details"])
        self.configure(bg=COLOR_WINDOW_BG)
        self.transient(parent)
        self.metadata = metadata
        self.path = path
        self.content = content
        self.on_save = on_save
        self.can_edit_metadata = bool(path)
        self.tags_var = tk.StringVar(value=", ".join(metadata.user_tags) if metadata else "")
        self.note_text: tk.Text | None = None
        self._build_body(title=title, path=path, content=content)

    def _build_body(self, *, title: str, path: str, content: str) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        metadata = self.metadata
        details = [
            ("Title", metadata.title if metadata else title),
            ("File", os.path.basename(path) if path else "Unsaved"),
            ("Path", path or "Unsaved editor content"),
            ("Characters", str(metadata.text_length if metadata else len(content))),
            ("Lines", str(len(content.splitlines()) or 1)),
        ]
        if metadata:
            details.extend(
                [
                    ("Entry ID", metadata.entry_id),
                    ("Created", metadata.created_at),
                    ("Category", metadata.category),
                    ("Confidence", f"{metadata.classifier_confidence:.2%}"),
                    ("Text file", "Available" if metadata.file_readable else "Missing or unreadable"),
                ]
            )
        else:
            details.append((
                "Metadata",
                "No sidecar metadata found; saving details will create one."
                if self.can_edit_metadata
                else "Unsaved editor content has no file path for metadata.",
            ))

        for row, (label, value) in enumerate(details):
            ttk.Label(frame, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=2)
            ttk.Label(frame, text=value, wraplength=360).grid(row=row, column=1, sticky="ew", pady=2)

        edit_row = len(details)
        ttk.Label(frame, text="Tags:").grid(row=edit_row, column=0, sticky="nw", padx=(0, 8), pady=(10, 2))
        tags_entry = ttk.Entry(
            frame,
            textvariable=self.tags_var,
            state="normal" if self.can_edit_metadata else "disabled",
        )
        tags_entry.grid(row=edit_row, column=1, sticky="ew", pady=(10, 2))
        ttk.Label(frame, text="Use commas to separate tags.").grid(row=edit_row + 1, column=1, sticky="w")

        ttk.Label(frame, text="Annotation:").grid(row=edit_row + 2, column=0, sticky="nw", padx=(0, 8), pady=(8, 2))
        self.note_text = tk.Text(frame, height=5, wrap="word")
        self.note_text.grid(row=edit_row + 2, column=1, sticky="nsew", pady=(8, 2))
        self.note_text.insert("1.0", metadata.note if metadata else "")
        if not self.can_edit_metadata:
            self.note_text.configure(state="disabled")
        frame.rowconfigure(edit_row + 2, weight=1)

        button_row = ttk.Frame(frame)
        button_row.grid(row=edit_row + 3, column=1, sticky="e", pady=(12, 0))
        ttk.Button(
            button_row,
            text="Save Metadata",
            command=self.save_metadata,
            state="normal" if self.can_edit_metadata else "disabled",
        ).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Close", command=self.destroy).pack(side="left")

    def save_metadata(self) -> None:
        """Persist editable tags and annotation through the provided callback."""

        if not self.can_edit_metadata or self.on_save is None or self.note_text is None:
            return
        tags = [part.strip() for part in self.tags_var.get().split(",") if part.strip()]
        note = self.note_text.get("1.0", "end").strip()
        try:
            self.metadata = self.on_save(self.metadata, self.path, self.content, tags, note)
            show_info(self, "Entry Details", "Metadata saved.")
        except Exception as exc:
            logger.exception(
                "Failed to save entry metadata: %s",
                self.metadata.entry_id if self.metadata else self.path,
            )
            show_error(self, "Entry Details", f"Failed to save metadata: {exc}")


class ExportDialog(tk.Toplevel):
    """Dialog for exporting ChronoNotes with format and filter options."""

    FORMAT_CHOICES = (
        ("Plain text (.txt)", "txt"),
        ("JSON with metadata (.json)", "json"),
        ("CSV summary (.csv)", "csv"),
        ("Markdown report (.md)", "markdown"),
        ("ZIP archive (.zip)", "zip"),
    )

    def __init__(
        self,
        parent: tk.Misc,
        storage,
        on_success: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self.title("Export ChronoNotes")
        self.geometry("560x350")
        self.configure(bg=COLOR_WINDOW_BG)
        self.transient(parent)
        self.storage = storage
        self.on_success = on_success
        self.on_error = on_error
        self.format_var = tk.StringVar(value=self.FORMAT_CHOICES[0][0])
        self.category_var = tk.StringVar()
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self._build_body()

    def _build_body(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Export Format:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        format_menu = ttk.OptionMenu(
            frame,
            self.format_var,
            self.format_var.get(),
            *(label for label, _value in self.FORMAT_CHOICES),
            command=lambda _choice: self._refresh_destination_hint(),
        )
        format_menu.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Category:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(frame, textvariable=self.category_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Leave blank to include all categories.").grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="From date:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(12, 4))
        ttk.Entry(frame, textvariable=self.date_from_var).grid(row=3, column=1, sticky="ew", pady=(12, 4))
        ttk.Label(frame, text="Use YYYY-MM-DD. Leave blank for no start date.").grid(row=4, column=1, sticky="w")

        ttk.Label(frame, text="To date:").grid(row=5, column=0, sticky="w", padx=(0, 8), pady=(12, 4))
        ttk.Entry(frame, textvariable=self.date_to_var).grid(row=5, column=1, sticky="ew", pady=(12, 4))
        ttk.Label(frame, text="Use YYYY-MM-DD. Leave blank for no end date.").grid(row=6, column=1, sticky="w")

        ttk.Label(frame, text="Destination:").grid(row=7, column=0, sticky="w", padx=(0, 8), pady=(12, 4))
        destination_row = ttk.Frame(frame)
        destination_row.grid(row=7, column=1, sticky="ew", pady=(12, 4))
        destination_row.columnconfigure(0, weight=1)
        ttk.Entry(destination_row, textvariable=self.destination_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(destination_row, text="Browse/Save As...", command=self.choose_destination).grid(
            row=0,
            column=1,
            padx=(6, 0),
        )
        ttk.Label(
            frame,
            text="Leave blank to export to the default exports folder with an automatic filename.",
        ).grid(row=8, column=1, sticky="w")

        button_row = ttk.Frame(frame)
        button_row.grid(row=9, column=1, sticky="e", pady=(16, 0))
        ttk.Button(button_row, text="Export", command=self.run_export).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Cancel", command=self.destroy).pack(side="left")

    def _selected_format(self) -> str:
        selected = self.format_var.get()
        for label, value in self.FORMAT_CHOICES:
            if label == selected:
                return value
        return "txt"

    def _refresh_destination_hint(self) -> None:
        destination = self.destination_var.get().strip()
        if not destination:
            return
        path = os.fspath(destination)
        root, _extension = os.path.splitext(path)
        self.destination_var.set(f"{root}{self._default_extension(self._selected_format())}")

    def _export_filters(self) -> dict[str, str]:
        return {
            "date_from": self.date_from_var.get().strip(),
            "date_to": self.date_to_var.get().strip(),
            "category": self.category_var.get().strip(),
        }

    @staticmethod
    def _default_extension(format_name: str) -> str:
        return ".md" if format_name == "markdown" else f".{format_name}"

    @classmethod
    def _filetypes_for_format(cls, format_name: str) -> list[tuple[str, str]]:
        labels = {
            "txt": "Plain text",
            "json": "JSON",
            "csv": "CSV",
            "markdown": "Markdown",
            "zip": "ZIP archive",
        }
        extension = cls._default_extension(format_name)
        return [(labels.get(format_name, "Export file"), f"*{extension}"), ("All files", "*.*")]

    def _suggested_export_filename(self, format_name: str, filters: dict[str, str] | None = None) -> str:
        filters = filters or self._export_filters()
        return default_export_filename(format_name, ExportFilters(**filters))

    def choose_destination(self) -> None:
        """Prompt for the export destination path with a format-appropriate extension."""

        format_name = self._selected_format()
        filters = self._export_filters()
        current_destination = self.destination_var.get().strip()
        initial_dir = getattr(self.storage, "exports_dir", "") or None
        initial_file = self._suggested_export_filename(format_name, filters)
        if current_destination:
            current_path = os.path.expanduser(current_destination)
            initial_dir = os.path.dirname(current_path) or initial_dir
            initial_file = os.path.basename(current_path) or initial_file
        selected = filedialog.asksaveasfilename(
            parent=self,
            title="Choose export destination",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=self._default_extension(format_name),
            filetypes=self._filetypes_for_format(format_name),
        )
        if selected:
            self.destination_var.set(selected)

    def run_export(self) -> None:
        """Execute the export request and report the output path."""

        format_name = self._selected_format()
        filters = self._export_filters()
        destination = self.destination_var.get().strip()
        try:
            result = self.storage.export_notes(format_name, destination, **filters)
            if not result.success or not result.path:
                raise RuntimeError(result.error or result.message or "Export failed.")
            message = f"Exported: {result.path}"
            if self.on_success is not None:
                self.on_success(message)
            else:
                show_info(self, "Export ChronoNotes", message)
            self.destroy()
        except Exception as exc:
            logger.exception("ChronoNotes export failed")
            message = f"Export failed: {exc}"
            if self.on_error is not None:
                self.on_error(message)
            else:
                show_error(self, "Export ChronoNotes", message)
