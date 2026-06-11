"""Sound playback integration for the Tkinter UI."""

from __future__ import annotations

import importlib
import importlib.util
import tkinter as tk

from core.config import SOUNDS_DIR
from core.logger import get_logger

logger = get_logger()

if importlib.util.find_spec("winsound") is not None:
    winsound = importlib.import_module("winsound")
    HAS_WINSOUND = True
else:
    winsound = None
    HAS_WINSOUND = False

SOUND_FILES = {
    "start": "start.wav",
    "copy": "copy.wav",
    "error": "error.wav",
    "pause": "pause.wav",
    "resume": "resume.wav",
    "save": "save.wav",
    "open": "open.wav",
}

BEEP_PATTERNS = {
    "start": (900, 120),
    "copy": (1200, 120),
    "error": (400, 250),
    "pause": (700, 120),
    "resume": (900, 180),
    "save": (800, 120),
    "open": (1000, 100),
}


class SoundManager:
    """Play optional WAV sounds with winsound and Tk bell fallbacks."""

    def __init__(self, root: tk.Tk):
        self.root = root

    def play(self, event: str) -> None:
        if event not in BEEP_PATTERNS:
            logger.warning("Unknown sound event requested: %s", event)
            return

        if HAS_WINSOUND:
            if self._play_wav(event):
                return
            if self._play_winsound_beep(event):
                return
        else:
            logger.info("winsound unavailable; falling back to Tk bell for event %s", event)

        self._play_tk_bell(event)

    def _play_wav(self, event: str) -> bool:
        wav_name = SOUND_FILES.get(event)
        if not wav_name:
            return False

        wav_path = SOUNDS_DIR / wav_name
        if not wav_path.exists():
            logger.info("WAV sound missing for event %s at %s; falling back", event, wav_path)
            return False

        try:
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            logger.info("Played WAV sound for event %s from %s", event, wav_path)
            return True
        except Exception:
            logger.exception("Failed to play WAV sound for event %s; falling back", event)
            return False

    def _play_winsound_beep(self, event: str) -> bool:
        freq, dur = BEEP_PATTERNS[event]
        try:
            winsound.Beep(freq, dur)
            logger.info("Played winsound beep fallback for event %s", event)
            return True
        except Exception:
            logger.exception("Failed to play winsound beep for event %s; falling back to Tk bell", event)
            return False

    def _play_tk_bell(self, event: str) -> None:
        try:
            self.root.bell()
            logger.info("Played Tk bell fallback for event %s", event)
        except Exception:
            logger.exception("Failed to play Tk bell fallback for event %s", event)
