"""Modular Tkinter dialogs for SessionChrono."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Protocol

from core.config import APP_NAME, APP_VERSION
from core.logger import get_logger
from core.storage import SearchResult
from ui.styles import COLOR_WINDOW_BG, DIALOG_GEOMETRIES
from ui.widgets import SearchResultsList

logger = get_logger()


class SearchProvider(Protocol):
    """Protocol for storage objects that can search and load note text."""

    def search_logs(self, query: str) -> list[SearchResult]:
        """Return structured note search results for *query*."""

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

    def show(self) -> None:
        """Prompt the user and open a result window when matches are found."""

        query = simpledialog.askstring("Search Logs", "Enter text:", parent=self.parent)
        if not query:
            return

        try:
            self.matches = self.storage.search_logs(query)
        except Exception as exc:
            logger.exception("Search failed for query: %r", query)
            self._report_error(f"Search failed: {exc}")
            return

        if not self.matches:
            show_info(self.parent, "Search Logs", "No matches found.")
            return

        logger.info("Search dialog found %d match(es) for query: %r", len(self.matches), query)
        self._build_results_window(query)

    def _build_results_window(self, query: str) -> None:
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Search Results — {query}")
        self.window.geometry(DIALOG_GEOMETRIES["search_results"])
        self.window.configure(bg=COLOR_WINDOW_BG)
        self.window.transient(self.parent)

        frame = ttk.Frame(self.window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Double-click a result to open it.").grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.results_list = SearchResultsList(frame)
        self.results_list.grid(row=1, column=0, sticky="nsew")
        self.results_list.set_results(self.matches)
        self.results_list.bind("<Double-Button-1>", self.open_selected)
        self.results_list.bind("<Return>", self.open_selected)
        self.results_list.focus_set()

        button_row = ttk.Frame(frame)
        button_row.grid(row=2, column=0, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Open", command=self.open_selected).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Close", command=self.window.destroy).pack(side="left")

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
    """Read-only note details/properties shell."""

    def __init__(self, parent: tk.Misc, *, title: str, path: str, content: str):
        super().__init__(parent)
        self.title("Entry Details")
        self.geometry(DIALOG_GEOMETRIES["entry_details"])
        self.configure(bg=COLOR_WINDOW_BG)
        self.transient(parent)
        self._build_body(title=title, path=path, content=content)

    def _build_body(self, *, title: str, path: str, content: str) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        details = (
            ("Title", title),
            ("File", os.path.basename(path) if path else "Unsaved"),
            ("Path", path or "Unsaved editor content"),
            ("Characters", str(len(content))),
            ("Lines", str(len(content.splitlines()) or 1)),
        )
        for row, (label, value) in enumerate(details):
            ttk.Label(frame, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=2)
            ttk.Label(frame, text=value, wraplength=360).grid(row=row, column=1, sticky="ew", pady=2)

        ttk.Button(frame, text="Close", command=self.destroy).grid(row=len(details), column=1, sticky="e", pady=(12, 0))
