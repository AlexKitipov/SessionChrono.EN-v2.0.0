"""Reusable Tkinter widgets for SessionChrono."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Mapping

from core.storage import SearchResult

from core.logger import get_logger
from ui.styles import (
    COLOR_ACCENT,
    COLOR_HISTORY_SELECT,
    COLOR_MENU_ACTIVE,
    COLOR_PANEL_BG,
    COLOR_TEXT,
    COLOR_WHITE,
    FONT_HISTORY,
    FONT_PREVIEW,
    FONT_SEARCH_RESULTS,
    TEXT_WIDGET_OPTIONS,
    create_dark_menu,
)

logger = get_logger()


class RightClickMenu:
    """Attach a copy/cut/paste/select-all/clear context menu to a text widget."""

    def __init__(self, widget: tk.Text):
        self.widget = widget
        self.menu = create_dark_menu(widget)
        self.menu.add_command(label="Copy", command=self.copy)
        self.menu.add_command(label="Cut", command=self.cut)
        self.menu.add_command(label="Paste", command=self.paste)
        self.menu.add_separator()
        self.menu.add_command(label="Select All", command=self.select_all)
        self.menu.add_command(label="Clear", command=self.clear)

        widget.bind("<Button-3>", self.show_menu)

    def show_menu(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def copy(self) -> None:
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
        except Exception:
            logger.debug("Right-click copy ignored because no selection was available", exc_info=True)

    def cut(self) -> None:
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
            self.widget.delete("sel.first", "sel.last")
        except Exception:
            logger.debug("Right-click cut ignored because no selection was available", exc_info=True)

    def paste(self) -> None:
        try:
            text = self.widget.clipboard_get()
            self.widget.insert(tk.INSERT, text)
        except Exception:
            logger.debug("Right-click paste ignored because clipboard text was unavailable", exc_info=True)

    def select_all(self) -> None:
        self.widget.tag_add("sel", "1.0", "end")

    def clear(self) -> None:
        self.widget.delete("1.0", "end")


class ScrollableText(tk.Frame):
    """A dark themed Text widget with a vertical scrollbar and context menu."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        font: tuple = FONT_PREVIEW,
        height: int | None = None,
        undo: bool = False,
    ):
        super().__init__(parent, bg=COLOR_PANEL_BG)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        options = dict(TEXT_WIDGET_OPTIONS)
        options.update({"font": font, "undo": undo})
        if height is not None:
            options["height"] = height

        self.text = tk.Text(self, **options)
        self.scrollbar = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.context_menu = RightClickMenu(self.text)

    def get_text(self) -> str:
        return self.text.get("1.0", tk.END)

    def set_text(self, content: str) -> None:
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)

    def clear(self) -> None:
        self.text.delete("1.0", tk.END)


class ClipboardHistoryList(tk.Frame):
    """Scrollable clipboard history list with selection callback support."""

    def __init__(self, parent: tk.Misc, on_select: Callable[[tk.Event], None]):
        super().__init__(parent, bg=COLOR_PANEL_BG)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            self,
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT,
            activestyle="none",
            selectbackground=COLOR_HISTORY_SELECT,
            font=FONT_HISTORY,
        )
        self.scrollbar = ttk.Scrollbar(self, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.scrollbar.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", on_select)

    def set_items(self, items: Iterable[Mapping[str, str]]) -> None:
        self.listbox.delete(0, tk.END)
        for item in items:
            title = item.get("title", "Untitled")
            category = item.get("category", "NOTE")
            timestamp = item.get("created_at") or item.get("timestamp") or ""
            display = f"[{category}] {title}"
            if timestamp:
                display = f"{timestamp}  {display}"
            self.listbox.insert(tk.END, display)

    def curselection(self) -> tuple[int, ...]:
        return self.listbox.curselection()


class StatusBar(tk.Frame):
    """Reusable blue status bar bound to a StringVar."""

    def __init__(self, parent: tk.Misc, textvariable: tk.StringVar):
        super().__init__(parent, bg=COLOR_ACCENT)
        self.label = tk.Label(
            self,
            textvariable=textvariable,
            bg=COLOR_ACCENT,
            fg=COLOR_WHITE,
            anchor="w",
            padx=5,
            pady=3,
        )
        self.label.pack(fill="x")


class SearchResultsList(tk.Listbox):
    """Dark listbox used by search dialogs."""

    def __init__(self, parent: tk.Misc):
        super().__init__(
            parent,
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT,
            selectbackground=COLOR_MENU_ACTIVE,
            font=FONT_SEARCH_RESULTS,
        )

    def set_results(self, results: Iterable[SearchResult]) -> None:
        """Render structured search results in a stable display format."""

        self.delete(0, tk.END)
        for result in results:
            category = f"[{result.category}] " if result.category else ""
            timestamp = f"{result.created_at or result.modified_at}  " if (result.created_at or result.modified_at) else ""
            tags = f"  tags: {', '.join(result.tags)}" if result.tags else ""
            availability = "  (missing file)" if not result.file_readable else ""
            line = result.line_number if result.line_number else "metadata"
            self.insert(
                tk.END,
                f"{timestamp}{category}{result.relative_path}:{line} — {result.snippet}{tags}{availability}",
            )
