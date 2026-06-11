"""Higher-level Tkinter UI components for SessionChrono."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Mapping

from ui.styles import FONT_EDITOR, FONT_LABEL_BOLD
from ui.widgets import ClipboardHistoryList, ScrollableText


class EditorPanel(ttk.Frame):
    """Main editor panel wrapping the shared scrollable text widget."""

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.scroller = ScrollableText(self, font=FONT_EDITOR, undo=True)
        self.scroller.grid(row=0, column=0, sticky="nsew")
        self.text = self.scroller.text

    def get_text(self) -> str:
        return self.scroller.get_text()

    def set_text(self, content: str) -> None:
        self.scroller.set_text(content)

    def clear(self) -> None:
        self.scroller.clear()


class LastCopiedPanel(ttk.Frame):
    """Labeled panel showing the most recent clipboard text."""

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text="Last Copied", font=FONT_LABEL_BOLD).grid(row=0, column=0, sticky="w")
        self.scroller = ScrollableText(self, height=12)
        self.scroller.grid(row=1, column=0, sticky="nsew")
        self.text = self.scroller.text

    def set_text(self, content: str) -> None:
        self.scroller.set_text(content)


class ClipboardHistoryPanel(ttk.Frame):
    """Labeled clipboard history list with a clear action."""

    def __init__(
        self,
        parent: tk.Misc,
        on_select: Callable[[tk.Event], None],
        on_clear: Callable[[], None],
    ):
        super().__init__(parent)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text="Clipboard History", font=FONT_LABEL_BOLD).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(10, 5),
        )
        self.history_list = ClipboardHistoryList(self, on_select)
        self.history_list.grid(row=1, column=0, sticky="nsew")
        ttk.Button(self, text="Clear Session History", command=on_clear).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )
        self.listbox = self.history_list.listbox

    def set_items(self, items: Iterable[Mapping[str, str]]) -> None:
        self.history_list.set_items(items)

    def curselection(self) -> tuple[int, ...]:
        return self.history_list.curselection()


class ActionStrip(ttk.Frame):
    """Compact toolbar/action strip for commonly used commands."""

    def __init__(self, parent: tk.Misc, actions: Iterable[tuple[str, Callable[[], None]]]):
        super().__init__(parent)
        for label, command in actions:
            ttk.Button(self, text=label, command=command).pack(side="left", padx=(0, 6))
