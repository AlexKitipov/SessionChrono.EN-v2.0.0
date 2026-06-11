import os
import zipfile
from datetime import datetime

from .config import LOG_ROOT

def save_text(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def create_today_zip():
    today = datetime.now().strftime("%Y-%m-%d")
    day_folder = LOG_ROOT / today
    if not day_folder.exists():
        return None

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    zip_name = LOG_ROOT / f"{today}_ChronoNotes.zip"
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(day_folder):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, LOG_ROOT)
                zf.write(full_path, rel_path)
    return str(zip_name)

def search_logs(query: str):
    matches = []
    for root, dirs, files in os.walk(LOG_ROOT):
        for file in files:
            if not file.lower().endswith(".txt"):
                continue
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if query.lower() in content.lower():
                    matches.append(full_path)
            except:
                pass
    return matches
