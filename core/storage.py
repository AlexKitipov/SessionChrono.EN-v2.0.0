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
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Callable

from .config import EXPORTS_DIR, LOG_ROOT, METADATA_DIR
from .logger import get_logger
from .metadata import EntryMetadata, MetadataManager

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
class SearchFilters:
    """Structured filters for note and metadata search."""

    query: str = ""
    category: str | None = None
    date_from: date | datetime | str | None = None
    date_to: date | datetime | str | None = None
    tag: str | None = None
    filename: str | None = None


@dataclass(frozen=True)
class SearchResult:
    """Structured note search result."""

    path: str
    relative_path: str
    filename: str
    snippet: str
    line_number: int
    modified_at: str | None = None
    category: str | None = None
    created_at: str | None = None
    title: str | None = None
    tags: tuple[str, ...] = ()
    file_exists: bool = True
    file_readable: bool = True


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

    def search_logs(
        self,
        query: str = "",
        *,
        category: str | None = None,
        date_from: date | datetime | str | None = None,
        date_to: date | datetime | str | None = None,
        tag: str | None = None,
        filename: str | None = None,
    ) -> list[SearchResult]:
        """Search notes by text and structured metadata filters."""

        filters = SearchFilters(query, category, date_from, date_to, tag, filename)
        logger.info("Searching notes with filters: %s", filters)
        normalized_query = query.strip().casefold()
        normalized_filename = (filename or "").strip().casefold()
        normalized_category = (category or "").strip().casefold()
        normalized_tag = (tag or "").strip().casefold()
        start_dt = self._coerce_search_datetime(date_from, end_of_day=False)
        end_dt = self._coerce_search_datetime(date_to, end_of_day=True)

        matches: dict[str, SearchResult] = {}
        metadata_by_path = {
            str(Path(record.file_path).expanduser().resolve()): record
            for record in self.metadata.list_all()
        }

        if self.base_dir.exists():
            for full_path in sorted(self.base_dir.rglob("*.txt")):
                if not full_path.is_file():
                    continue
                metadata = metadata_by_path.get(str(full_path.resolve()))
                result = self._search_file(
                    full_path,
                    metadata,
                    normalized_query,
                    normalized_filename,
                    normalized_category,
                    normalized_tag,
                    start_dt,
                    end_dt,
                )
                if result is not None:
                    matches[result.path] = result
        else:
            logger.info("Search base directory does not exist: %s", self.base_dir)

        # Metadata records with missing text files can still match structured filters
        # or metadata text (title, tags, notes). Include them safely as unavailable.
        for metadata in metadata_by_path.values():
            if metadata.file_readable and metadata.file_path in matches:
                continue
            metadata_path = Path(metadata.file_path).expanduser()
            if metadata_path.exists() and metadata.file_readable:
                continue
            result = self._search_missing_metadata(
                metadata,
                normalized_query,
                normalized_filename,
                normalized_category,
                normalized_tag,
                start_dt,
                end_dt,
            )
            if result is not None:
                matches[result.path] = result

        results = sorted(
            matches.values(),
            key=lambda item: item.created_at or item.modified_at or item.relative_path,
            reverse=True,
        )
        logger.info("Search completed with %d match(es)", len(results))
        return results

    def _search_file(
        self,
        full_path: Path,
        metadata: EntryMetadata | None,
        normalized_query: str,
        normalized_filename: str,
        normalized_category: str,
        normalized_tag: str,
        start_dt: datetime | None,
        end_dt: datetime | None,
    ) -> SearchResult | None:
        if not self._metadata_matches(metadata, normalized_category, normalized_tag, start_dt, end_dt):
            return None
        title = metadata.title if metadata else ""
        if normalized_filename and normalized_filename not in full_path.name.casefold() and normalized_filename not in title.casefold():
            return None
        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed to search file: %s", full_path)
            return None
        line_number, snippet = self._content_or_metadata_snippet(content, metadata, normalized_query)
        if normalized_query and line_number is None:
            return None
        if line_number is None:
            line_number = 1
            snippet = self._fallback_snippet(content, metadata)
        try:
            relative_path = full_path.relative_to(self.base_dir).as_posix()
        except ValueError:
            relative_path = full_path.name
        try:
            modified_at = datetime.fromtimestamp(full_path.stat().st_mtime).isoformat(timespec="seconds")
        except OSError:
            modified_at = None
        return SearchResult(
            path=str(full_path),
            relative_path=relative_path,
            filename=full_path.name,
            snippet=snippet,
            line_number=line_number,
            modified_at=modified_at,
            category=metadata.category if metadata else self._category_from_path(full_path),
            created_at=metadata.created_at if metadata else None,
            title=metadata.title if metadata else full_path.stem,
            tags=tuple(metadata.user_tags) if metadata else (),
            file_exists=True,
            file_readable=True,
        )

    def _search_missing_metadata(
        self,
        metadata: EntryMetadata,
        normalized_query: str,
        normalized_filename: str,
        normalized_category: str,
        normalized_tag: str,
        start_dt: datetime | None,
        end_dt: datetime | None,
    ) -> SearchResult | None:
        if not self._metadata_matches(metadata, normalized_category, normalized_tag, start_dt, end_dt):
            return None
        path = Path(metadata.file_path).expanduser()
        if normalized_filename and normalized_filename not in path.name.casefold() and normalized_filename not in metadata.title.casefold():
            return None
        metadata_text = " ".join([metadata.title, metadata.short_title, metadata.note, " ".join(metadata.user_tags)])
        if normalized_query and normalized_query not in metadata_text.casefold():
            return None
        try:
            relative_path = path.resolve().relative_to(self.base_dir).as_posix()
        except Exception:
            relative_path = path.name
        return SearchResult(
            path=str(path),
            relative_path=relative_path,
            filename=path.name,
            snippet="Missing file — metadata matched." if normalized_query else "Missing file.",
            line_number=0,
            modified_at=None,
            category=metadata.category,
            created_at=metadata.created_at,
            title=metadata.title,
            tags=tuple(metadata.user_tags),
            file_exists=metadata.file_exists,
            file_readable=metadata.file_readable,
        )

    @staticmethod
    def _metadata_matches(
        metadata: EntryMetadata | None,
        normalized_category: str,
        normalized_tag: str,
        start_dt: datetime | None,
        end_dt: datetime | None,
    ) -> bool:
        if normalized_category:
            if metadata is None or metadata.category.casefold() != normalized_category:
                return False
        if normalized_tag:
            if metadata is None or normalized_tag not in {tag.casefold() for tag in metadata.user_tags}:
                return False
        if start_dt or end_dt:
            if metadata is None:
                return False
            created_at = StorageManager._parse_datetime(metadata.created_at)
            if created_at is None:
                return False
            if start_dt and created_at < start_dt:
                return False
            if end_dt and created_at > end_dt:
                return False
        return True

    @staticmethod
    def _content_or_metadata_snippet(
        content: str,
        metadata: EntryMetadata | None,
        normalized_query: str,
    ) -> tuple[int | None, str]:
        if not normalized_query:
            return None, ""
        line_number, snippet = StorageManager._first_match_snippet(content, normalized_query)
        if line_number is not None:
            return line_number, snippet
        if metadata is not None:
            fields = [metadata.title, metadata.short_title, metadata.note, " ".join(metadata.user_tags)]
            for value in fields:
                if normalized_query in value.casefold():
                    snippet = value.strip()
                    if len(snippet) > 160:
                        snippet = f"{snippet[:157]}..."
                    return 0, snippet
        return None, ""

    @staticmethod
    def _fallback_snippet(content: str, metadata: EntryMetadata | None) -> str:
        if metadata and metadata.title:
            return metadata.title
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        return first_line[:160] if first_line else "(empty file)"

    @staticmethod
    def _category_from_path(path: Path) -> str | None:
        try:
            return path.parent.name
        except Exception:
            return None

    @staticmethod
    def _coerce_search_datetime(value: date | datetime | str | None, *, end_of_day: bool) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        if isinstance(value, date):
            boundary = time.max if end_of_day else time.min
            return datetime.combine(value, boundary)
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed_date = date.fromisoformat(text)
            boundary = time.max if end_of_day else time.min
            return datetime.combine(parsed_date, boundary)
        except ValueError:
            parsed_dt = StorageManager._parse_datetime(text)
            if parsed_dt is None:
                raise ValueError(f"Invalid search date: {value!r}. Use YYYY-MM-DD.")
            return parsed_dt

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

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

    def search_metadata(self, query: str = "", **filters):
        """Search entry metadata fields and structured filters."""

        return self.metadata.search(query, **filters)


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


def search_log_results(query: str, **filters) -> list[SearchResult]:
    """Return structured search results from the default storage manager."""

    return _default_manager.search_logs(query, **filters)


def search_logs(query: str) -> list[str]:
    """Backward-compatible search wrapper returning only matched paths."""

    return [result.path for result in _default_manager.search_logs(query)]
