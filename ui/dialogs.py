"""Modular Tkinter dialogs for SessionChrono."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Protocol

from core.config import APP_NAME, APP_VERSION
from core.logger import get_logger
from core.metadata import EntryMetadata
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
    """Placeholder settings shell for upcoming preferences UI."""

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("Settings")
        self.geometry(DIALOG_GEOMETRIES["settings"])
        self.configure(bg=COLOR_WINDOW_BG)
        self.transient(parent)
        self._build_body()

    def _build_body(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Preferences will appear here in a future update.",
            wraplength=360,
        ).pack(anchor="w", pady=(8, 12))
        ttk.Button(frame, text="Close", command=self.destroy).pack(anchor="e")


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
        on_save: Callable[[EntryMetadata, list[str], str], EntryMetadata] | None = None,
    ):
        super().__init__(parent)
        self.title("Entry Details")
        self.geometry(DIALOG_GEOMETRIES["entry_details"])
        self.configure(bg=COLOR_WINDOW_BG)
        self.transient(parent)
        self.metadata = metadata
        self.on_save = on_save
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
            details.append(("Metadata", "No sidecar metadata found for this entry."))

        for row, (label, value) in enumerate(details):
            ttk.Label(frame, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=2)
            ttk.Label(frame, text=value, wraplength=360).grid(row=row, column=1, sticky="ew", pady=2)

        edit_row = len(details)
        ttk.Label(frame, text="Tags:").grid(row=edit_row, column=0, sticky="nw", padx=(0, 8), pady=(10, 2))
        tags_entry = ttk.Entry(frame, textvariable=self.tags_var, state="normal" if metadata else "disabled")
        tags_entry.grid(row=edit_row, column=1, sticky="ew", pady=(10, 2))
        ttk.Label(frame, text="Use commas to separate tags.").grid(row=edit_row + 1, column=1, sticky="w")

        ttk.Label(frame, text="Annotation:").grid(row=edit_row + 2, column=0, sticky="nw", padx=(0, 8), pady=(8, 2))
        self.note_text = tk.Text(frame, height=5, wrap="word")
        self.note_text.grid(row=edit_row + 2, column=1, sticky="nsew", pady=(8, 2))
        self.note_text.insert("1.0", metadata.note if metadata else "")
        if not metadata:
            self.note_text.configure(state="disabled")
        frame.rowconfigure(edit_row + 2, weight=1)

        button_row = ttk.Frame(frame)
        button_row.grid(row=edit_row + 3, column=1, sticky="e", pady=(12, 0))
        ttk.Button(
            button_row,
            text="Save Metadata",
            command=self.save_metadata,
            state="normal" if metadata else "disabled",
        ).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Close", command=self.destroy).pack(side="left")

    def save_metadata(self) -> None:
        """Persist editable tags and annotation through the provided callback."""

        if not self.metadata or self.on_save is None or self.note_text is None:
            return
        tags = [part.strip() for part in self.tags_var.get().split(",") if part.strip()]
        note = self.note_text.get("1.0", "end").strip()
        try:
            self.metadata = self.on_save(self.metadata, tags, note)
            show_info(self, "Entry Details", "Metadata saved.")
        except Exception as exc:
            logger.exception("Failed to save entry metadata: %s", self.metadata.entry_id)
            show_error(self, "Entry Details", f"Failed to save metadata: {exc}")
