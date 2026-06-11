"""Storage services for SessionChrono notes.

The UI still imports compatibility functions from this module, but new code should
prefer :class:`StorageManager` so tests and future features can inject a
specific runtime directory.
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from .config import EXPORTS_DIR, LOG_ROOT, METADATA_DIR
from .logger import get_logger
from .metadata import MetadataManager

logger = get_logger()


@dataclass(frozen=True)
class StorageOperationResult:
    """Result for operations that either produce a path or an error message."""

    success: bool
    path: str | None = None
    message: str = ""
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


@dataclass(frozen=True)
class LoadTextResult:
    """Result returned by :meth:`StorageManager.load_text`."""

    success: bool
    path: str
    content: str = ""
    message: str = ""
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


@dataclass(frozen=True)
class SearchResult:
    """Structured note search result."""

    path: str
    relative_path: str
    filename: str
    snippet: str
    line_number: int
    modified_at: str | None = None


Exporter = Callable[[Path, Path], StorageOperationResult]


class StorageManager:
    """Manage note persistence below a configurable base directory."""

    def __init__(
        self,
        base_dir: str | os.PathLike[str] = LOG_ROOT,
        exports_dir: str | os.PathLike[str] | None = None,
    ):
        self.base_dir = Path(base_dir).expanduser().resolve()
        default_exports = self.base_dir.parent / "exports"
        self.exports_dir = Path(exports_dir).expanduser().resolve() if exports_dir else default_exports
        self._exporters: dict[str, Exporter] = {}
        default_metadata_dir = (
            Path(METADATA_DIR)
            if self.base_dir == Path(LOG_ROOT).expanduser().resolve()
            else self.base_dir.parent / "metadata"
        )
        self.metadata = MetadataManager(default_metadata_dir)

    def resolve_path(self, path: str | os.PathLike[str]) -> Path:
        """Resolve absolute paths as-is and relative paths under ``base_dir``."""

        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.base_dir / candidate
        return candidate.resolve()

    def save_text(self, path: str | os.PathLike[str], text: str) -> StorageOperationResult:
        """Atomically save text, creating parent directories when needed."""

        destination = self.resolve_path(path)
        logger.info("Saving text file: %s", destination)
        temp_path: Path | None = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=destination.parent,
                delete=False,
                prefix=f".{destination.name}.",
                suffix=".tmp",
            ) as tmp:
                tmp.write(text)
                tmp.flush()
                os.fsync(tmp.fileno())
                temp_path = Path(tmp.name)
            os.replace(temp_path, destination)
            logger.info("Saved text file: %s", destination)
            return StorageOperationResult(True, str(destination), "Saved text file.")
        except Exception as exc:
            logger.exception("Failed to save text file: %s", destination)
            if temp_path:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    logger.debug(
                        "Failed to remove temporary file after save failure: %s",
                        temp_path,
                        exc_info=True,
                    )
            return StorageOperationResult(False, str(destination), "Failed to save text file.", str(exc))

    def load_text(self, path: str | os.PathLike[str]) -> LoadTextResult:
        """Load text while returning a clear failed result for missing/unreadable files."""

        source = self.resolve_path(path)
        logger.info("Loading text file: %s", source)
        if not source.exists():
            message = "File does not exist."
            logger.info("%s path=%s", message, source)
            return LoadTextResult(False, str(source), message=message)
        if not source.is_file():
            message = "Path is not a file."
            logger.info("%s path=%s", message, source)
            return LoadTextResult(False, str(source), message=message)
        try:
            content = source.read_text(encoding="utf-8")
            logger.info("Loaded text file: %s", source)
            return LoadTextResult(True, str(source), content, "Loaded text file.")
        except Exception as exc:
            logger.exception("Failed to load text file: %s", source)
            return LoadTextResult(False, str(source), message="Failed to load text file.", error=str(exc))

    def create_today_zip(self, target_date: date | None = None) -> StorageOperationResult:
        """Create a ZIP archive for one day's notes using paths relative to ``base_dir``."""

        target_date = target_date or datetime.now().date()
        day_name = target_date.strftime("%Y-%m-%d")
        day_folder = self.base_dir / day_name
        zip_path = self.base_dir / f"{day_name}_ChronoNotes.zip"
        logger.info("Creating ZIP for %s from %s", day_name, day_folder)

        if not day_folder.exists():
            message = "No notes found for ZIP creation."
            logger.info("%s path=%s", message, day_folder)
            return StorageOperationResult(False, str(zip_path), message)

        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for full_path in sorted(path for path in day_folder.rglob("*") if path.is_file()):
                    zf.write(full_path, full_path.relative_to(self.base_dir).as_posix())
            logger.info("Created ZIP archive: %s", zip_path)
            return StorageOperationResult(True, str(zip_path), "Created ZIP archive.")
        except Exception as exc:
            logger.exception("Failed to create ZIP archive: %s", zip_path)
            return StorageOperationResult(False, str(zip_path), "Failed to create ZIP archive.", str(exc))

    def search_logs(self, query: str) -> list[SearchResult]:
        """Search text notes and return structured results with snippets."""

        logger.info("Searching notes for query: %r", query)
        normalized_query = query.casefold()
        if not normalized_query:
            logger.info("Search skipped because query was empty")
            return []

        matches: list[SearchResult] = []
        if not self.base_dir.exists():
            logger.info("Search base directory does not exist: %s", self.base_dir)
            return matches

        for full_path in sorted(self.base_dir.rglob("*.txt")):
            if not full_path.is_file():
                continue
            try:
                content = full_path.read_text(encoding="utf-8")
            except Exception:
                logger.exception("Failed to search file: %s", full_path)
                continue
            line_number, snippet = self._first_match_snippet(content, normalized_query)
            if line_number is None:
                continue
            try:
                relative_path = full_path.relative_to(self.base_dir).as_posix()
            except ValueError:
                relative_path = full_path.name
            try:
                modified_at = datetime.fromtimestamp(full_path.stat().st_mtime).isoformat(timespec="seconds")
            except OSError:
                modified_at = None
            matches.append(
                SearchResult(
                    path=str(full_path),
                    relative_path=relative_path,
                    filename=full_path.name,
                    snippet=snippet,
                    line_number=line_number,
                    modified_at=modified_at,
                )
            )
        logger.info("Search completed for query %r with %d match(es)", query, len(matches))
        return matches

    @staticmethod
    def _first_match_snippet(content: str, normalized_query: str) -> tuple[int | None, str]:
        for index, line in enumerate(content.splitlines() or [content], start=1):
            if normalized_query in line.casefold():
                snippet = line.strip()
                if len(snippet) > 160:
                    snippet = f"{snippet[:157]}..."
                return index, snippet
        return None, ""

    def register_exporter(self, format_name: str, exporter: Exporter) -> None:
        """Register an exporter hook for future JSON/CSV/Markdown integrations."""

        self._exporters[format_name.casefold()] = exporter
        logger.info("Registered storage exporter: %s", format_name)

    def export_notes(
        self,
        format_name: str,
        destination: str | os.PathLike[str] | None = None,
    ) -> StorageOperationResult:
        """Invoke a registered export hook or report a clear unsupported format."""

        normalized_format = format_name.casefold()
        destination_path = self.resolve_path(destination) if destination else self.exports_dir / normalized_format
        exporter = self._exporters.get(normalized_format)
        if not exporter:
            message = f"Export format is not implemented: {format_name}"
            logger.info(message)
            return StorageOperationResult(False, str(destination_path), message)
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            return exporter(self.base_dir, destination_path)
        except Exception as exc:
            logger.exception("Failed to export notes as %s to %s", format_name, destination_path)
            return StorageOperationResult(False, str(destination_path), "Failed to export notes.", str(exc))

    def export_json(self, destination: str | os.PathLike[str] | None = None) -> StorageOperationResult:
        return self.export_notes("json", destination)

    def export_csv(self, destination: str | os.PathLike[str] | None = None) -> StorageOperationResult:
        return self.export_notes("csv", destination)

    def export_markdown(self, destination: str | os.PathLike[str] | None = None) -> StorageOperationResult:
        return self.export_notes("markdown", destination)

    def load_metadata(self, entry_id: str):
        """Load entry metadata by ID."""

        return self.metadata.load(entry_id)

    def load_metadata_by_path(self, path: str | os.PathLike[str]):
        """Load entry metadata for a text path."""

        return self.metadata.load_by_path(path)

    def update_metadata(self, entry_id: str, **fields):
        """Update entry metadata fields."""

        return self.metadata.update_metadata(entry_id, **fields)

    def search_metadata(self, query: str = "", *, tags=None):
        """Search entry metadata fields and tags."""

        return self.metadata.search(query, tags=tags)


_default_manager = StorageManager(LOG_ROOT, EXPORTS_DIR)


def get_default_storage_manager() -> StorageManager:
    return _default_manager


def save_text(path: str, text: str) -> StorageOperationResult:
    """Backward-compatible wrapper around :meth:`StorageManager.save_text`."""

    return _default_manager.save_text(path, text)


def load_text_result(path: str) -> LoadTextResult:
    """Return the structured load result for callers that need diagnostics."""

    return _default_manager.load_text(path)


def load_text(path: str) -> str:
    """Backward-compatible wrapper returning file content or an empty string."""

    return _default_manager.load_text(path).content


def create_today_zip() -> str | None:
    """Backward-compatible ZIP wrapper returning the archive path or ``None``."""

    result = _default_manager.create_today_zip()
    return result.path if result.success else None


def search_log_results(query: str) -> list[SearchResult]:
    """Return structured search results from the default storage manager."""

    return _default_manager.search_logs(query)


def search_logs(query: str) -> list[str]:
    """Backward-compatible search wrapper returning only matched paths."""

    return [result.path for result in _default_manager.search_logs(query)]
