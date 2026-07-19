# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building SessionChrono from source.

This file is intentionally text-only.  It defines how PyInstaller should create
local build artifacts under ``build/`` and ``dist/``; those generated folders and
binaries must not be committed.
"""

from pathlib import Path


block_cipher = None
ROOT = Path(SPECPATH).resolve()
APP_NAME = "SessionChrono"
APP_VERSION = "2.0.0"

# These directory names must stay aligned with core.config.  The README and
# .gitkeep files are intentionally bundled so the resource directories exist in
# a one-folder build even when no approved binary icon or WAV assets are present.
RESOURCE_DIRECTORIES = ("icons", "sounds", "config_templates")


def tree_data(directory: str) -> list[tuple[str, str]]:
    """Return PyInstaller data-file tuples for every file under *directory*."""

    source_root = ROOT / directory
    if not source_root.exists():
        return []
    return [
        (str(path), str(path.parent.relative_to(ROOT)))
        for path in source_root.rglob("*")
        if path.is_file()
    ]


datas = []
for resource_directory in RESOURCE_DIRECTORIES:
    datas += tree_data(resource_directory)

hiddenimports = [
    # Clipboard backends and Windows clipboard support.
    "pyperclip",
    "pyperclip.clipboards",
    "pyperclip.windows",
    "win32api",
    "win32clipboard",
    "win32con",
    "winsound",
    # Tkinter submodules imported dynamically by dialogs and ttk widgets.
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.simpledialog",
    "tkinter.ttk",
    # Project modules that should remain explicit for packaging smoke checks.
    "core.app_controller",
    "core.chrono",
    "core.classifier",
    "core.config",
    "core.export",
    "core.logger",
    "core.metadata",
    "core.settings",
    "core.storage",
    "core.utils",
    "ui.components",
    "ui.dialogs",
    "ui.sounds",
    "ui.styles",
    "ui.tkinter_ui",
    "ui.widgets",
]


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "SessionChrono.ico"),
    version=str(ROOT / "version_info.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
