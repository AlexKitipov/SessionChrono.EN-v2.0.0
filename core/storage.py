import os
import zipfile
from datetime import datetime

from .config import LOG_ROOT
from .logger import get_logger

logger = get_logger()

def save_text(path: str, text: str):
    logger.info("Saving text file: %s", path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("Saved text file: %s", path)

def load_text(path: str) -> str:
    logger.info("Loading text file: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    logger.info("Loaded text file: %s", path)
    return content

def create_today_zip():
    today = datetime.now().strftime("%Y-%m-%d")
    day_folder = LOG_ROOT / today
    logger.info("Creating ZIP for %s from %s", today, day_folder)
    if not day_folder.exists():
        logger.info("No notes found for ZIP creation: %s", day_folder)
        return None

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    zip_name = LOG_ROOT / f"{today}_ChronoNotes.zip"
    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(day_folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, LOG_ROOT)
                    zf.write(full_path, rel_path)
        logger.info("Created ZIP archive: %s", zip_name)
        return str(zip_name)
    except Exception:
        logger.exception("Failed to create ZIP archive: %s", zip_name)
        raise

def search_logs(query: str):
    logger.info("Searching notes for query: %r", query)
    matches = []

    def log_walk_error(error: OSError):
        logger.exception("Failed to walk notes directory during search: %s", error.filename)

    for root, dirs, files in os.walk(LOG_ROOT, onerror=log_walk_error):
        for file in files:
            if not file.lower().endswith(".txt"):
                continue
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if query.lower() in content.lower():
                    matches.append(full_path)
            except Exception:
                logger.exception("Failed to search file: %s", full_path)
    logger.info("Search completed for query %r with %d match(es)", query, len(matches))
    return matches
