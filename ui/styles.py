"""Shared Tkinter styling for SessionChrono's dark UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.config import WINDOW_DEFAULT_GEOMETRY, WINDOW_TITLE

COLOR_WINDOW_BG = "#2d2d2d"
COLOR_PANEL_BG = "#1e1e1e"
COLOR_TEXT = "#d4d4d4"
COLOR_MENU_ACTIVE = "#3e3e3e"
COLOR_BUTTON_ACTIVE = "#505050"
COLOR_ACCENT = "#007acc"
COLOR_HISTORY_SELECT = "#264f78"
COLOR_WHITE = "#ffffff"

FONT_UI = ("Segoe UI", 10)
FONT_LABEL_BOLD = ("Segoe UI", 11, "bold")
FONT_EDITOR = ("Consolas", 11)
FONT_PREVIEW = ("Consolas", 10)
FONT_HISTORY = ("Consolas", 9)
FONT_SEARCH_RESULTS = ("Segoe UI", 9)

TEXT_WIDGET_OPTIONS = {
    "wrap": "word",
    "bg": COLOR_PANEL_BG,
    "fg": COLOR_TEXT,
    "insertbackground": "white",
}

MENU_OPTIONS = {
    "bg": COLOR_WINDOW_BG,
    "fg": COLOR_WHITE,
    "activebackground": COLOR_MENU_ACTIVE,
    "activeforeground": COLOR_WHITE,
    "tearoff": 0,
}

DIALOG_GEOMETRIES = {
    "search_results": "600x400",
    "settings": "680x520",
    "entry_details": "520x260",
}


def apply_window_style(root: tk.Tk) -> None:
    """Apply title, geometry, background, and ttk dark theme to the root window."""
    root.title(WINDOW_TITLE)
    root.geometry(WINDOW_DEFAULT_GEOMETRY)
    root.configure(bg=COLOR_WINDOW_BG)
    configure_ttk_style()


def configure_ttk_style() -> ttk.Style:
    """Configure and return the shared ttk dark style."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        ".",
        background=COLOR_WINDOW_BG,
        foreground=COLOR_WHITE,
        font=FONT_UI,
    )
    style.configure("TFrame", background=COLOR_WINDOW_BG)
    style.configure("TButton", background=COLOR_MENU_ACTIVE, foreground=COLOR_WHITE)
    style.map("TButton", background=[("active", COLOR_BUTTON_ACTIVE)])
    style.configure("TLabel", background=COLOR_WINDOW_BG, foreground=COLOR_WHITE)
    return style


def create_dark_menu(parent: tk.Misc) -> tk.Menu:
    """Create a menu using the shared dark color palette."""
    return tk.Menu(parent, **MENU_OPTIONS)
