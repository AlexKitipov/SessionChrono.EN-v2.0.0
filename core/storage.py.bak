import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_ROOT = os.path.join(os.path.dirname(BASE_DIR), "ChronoNotes")
os.makedirs(LOG_ROOT, exist_ok=True)

def classify_text(text: str) -> str:
    t = text.strip().lower()
    if any(x in t for x in ("http://", "https://", "www.")):
        return "URL"
    if any(x in t for x in ("exception", "traceback", "error", "stack trace")):
        return "LOG"
    if any(x in t for x in ("def ", "class ", "{", "};", "console.log", "function ")):
        return "CODE"
    if any(x in t for x in ("todo", "must", "fix ", "task", "to do")):
        return "TODO"
    if any(x in t for x in ("copilot", "chatgpt", "assistant", "ai", "model")):
        return "CHAT"
    return "NOTE"

def make_short_title(text: str, max_len: int = 30) -> str:
    lines = text.strip().splitlines()
    line = lines[0] if lines else "empty"
    line = line.replace("\t", " ").strip()
    if len(line) > max_len:
        line = line[:max_len].rsplit(" ", 1)[0] or line[:max_len]
    bad = '<>:"/\\|?*'
    for ch in bad:
        line = line.replace(ch, "_")
    return line or "note"

def build_filename(text: str):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    category = classify_text(text)
    short = make_short_title(text)

    folder = os.path.join(LOG_ROOT, date_str, category)
    os.makedirs(folder, exist_ok=True)

    filename = f"{category}_{short}_{date_str}_{time_str}.txt"
    full_path = os.path.join(folder, filename)
    return full_path, folder, short, category
