"""JSON sidecar metadata management for persisted clipboard entries."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import METADATA_DIR
from .logger import get_logger

logger = get_logger()


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp suitable for JSON metadata."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_tags(tags: Iterable[str] | None) -> list[str]:
    """Trim, de-duplicate, and sort user tags case-insensitively."""

    normalized: dict[str, str] = {}
    for tag in tags or []:
        cleaned = str(tag).strip()
        if cleaned:
            normalized[cleaned.casefold()] = cleaned
    return sorted(normalized.values(), key=str.casefold)


@dataclass(frozen=True)
class EntryMetadata:
    """Structured metadata for one persisted clipboard entry."""

    entry_id: str
    file_path: str
    created_at: str
    category: str
    title: str
    short_title: str
    text_length: int
    classifier_confidence: float
    user_tags: list[str] = field(default_factory=list)
    note: str = ""
    updated_at: str | None = None
    file_exists: bool = True
    file_readable: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EntryMetadata":
        """Build metadata from a JSON dictionary with tolerant defaults."""

        return cls(
            entry_id=str(data.get("entry_id") or uuid.uuid4().hex),
            file_path=str(data.get("file_path") or ""),
            created_at=str(data.get("created_at") or _utc_now()),
            category=str(data.get("category") or "NOTE"),
            title=str(data.get("title") or data.get("short_title") or "Untitled"),
            short_title=str(data.get("short_title") or data.get("title") or "Untitled"),
            text_length=max(0, int(data.get("text_length") or 0)),
            classifier_confidence=float(data.get("classifier_confidence") or 0.0),
            user_tags=_normalize_tags(data.get("user_tags") or []),
            note=str(data.get("note") or ""),
            updated_at=data.get("updated_at"),
            file_exists=bool(data.get("file_exists", True)),
            file_readable=bool(data.get("file_readable", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        data = asdict(self)
        data["user_tags"] = _normalize_tags(self.user_tags)
        data["classifier_confidence"] = round(float(self.classifier_confidence), 4)
        return data

    def to_export_dict(self) -> dict[str, Any]:
        """Return metadata fields intended for bundled exports and reports."""

        data = self.to_dict()
        data["export_schema"] = "chrononotes.entry_metadata.v1"
        return data


@dataclass(frozen=True)
class MetadataSearchResult:
    """Metadata search match with a human-readable reason."""

    metadata: EntryMetadata
    matched_fields: tuple[str, ...]


class MetadataManager:
    """Persist and query per-entry JSON metadata sidecars."""

    def __init__(self, metadata_dir: str | os.PathLike[str] = METADATA_DIR):
        self.metadata_dir = Path(metadata_dir).expanduser().resolve()

    def create_metadata(
        self,
        *,
        file_path: str | os.PathLike[str],
        category: str,
        title: str,
        short_title: str,
        text_length: int,
        classifier_confidence: float = 0.0,
        user_tags: Iterable[str] | None = None,
        note: str = "",
        entry_id: str | None = None,
        created_at: str | None = None,
    ) -> EntryMetadata:
        """Create, save, and return metadata for a persisted entry."""

        metadata = EntryMetadata(
            entry_id=entry_id or uuid.uuid4().hex,
            file_path=str(Path(file_path).expanduser().resolve()),
            created_at=created_at or _utc_now(),
            category=category,
            title=title,
            short_title=short_title,
            text_length=max(0, int(text_length)),
            classifier_confidence=round(float(classifier_confidence), 4),
            user_tags=_normalize_tags(user_tags),
            note=note.strip(),
            updated_at=None,
        )
        return self.save(metadata)

    def save(self, metadata: EntryMetadata) -> EntryMetadata:
        """Atomically write a metadata sidecar JSON file."""

        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        refreshed = self._with_file_status(metadata)
        destination = self._path_for_id(refreshed.entry_id)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=destination.parent,
                delete=False,
                prefix=f".{destination.name}.",
                suffix=".tmp",
            ) as tmp:
                json.dump(refreshed.to_dict(), tmp, indent=2, sort_keys=True)
                tmp.write("\n")
                tmp.flush()
                os.fsync(tmp.fileno())
                temp_path = Path(tmp.name)
            os.replace(temp_path, destination)
            logger.info("Saved metadata sidecar: %s", destination)
            return refreshed
        except Exception:
            logger.exception("Failed to save metadata sidecar: %s", destination)
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise

    def load(self, entry_id: str) -> EntryMetadata | None:
        """Load metadata by entry ID, returning ``None`` if absent or unreadable."""

        path = self._path_for_id(entry_id)
        if not path.exists():
            return None
        return self._load_path(path)

    def load_by_path(self, file_path: str | os.PathLike[str]) -> EntryMetadata | None:
        """Load metadata for a text file path by scanning sidecars."""

        target = str(Path(file_path).expanduser().resolve())
        for metadata in self.list_all():
            if str(Path(metadata.file_path).expanduser().resolve()) == target:
                return metadata
        return None

    def update_metadata(
        self,
        entry_id: str,
        *,
        user_tags: Iterable[str] | None = None,
        note: str | None = None,
        title: str | None = None,
        short_title: str | None = None,
        category: str | None = None,
        file_path: str | os.PathLike[str] | None = None,
        text_length: int | None = None,
        classifier_confidence: float | None = None,
    ) -> EntryMetadata:
        """Update editable metadata fields and persist the sidecar."""

        existing = self.load(entry_id)
        if existing is None:
            raise KeyError(f"Metadata entry not found: {entry_id}")

        data = existing.to_dict()
        if user_tags is not None:
            data["user_tags"] = _normalize_tags(user_tags)
        if note is not None:
            data["note"] = note.strip()
        if title is not None:
            data["title"] = title.strip() or existing.title
        if short_title is not None:
            data["short_title"] = short_title.strip() or existing.short_title
        if category is not None:
            data["category"] = category.strip() or existing.category
        if file_path is not None:
            data["file_path"] = str(Path(file_path).expanduser().resolve())
        if text_length is not None:
            data["text_length"] = max(0, int(text_length))
        if classifier_confidence is not None:
            data["classifier_confidence"] = round(float(classifier_confidence), 4)
        data["updated_at"] = _utc_now()
        return self.save(EntryMetadata.from_dict(data))

    def upsert_for_path(self, file_path: str | os.PathLike[str], **fields: Any) -> EntryMetadata:
        """Update metadata for a path or create it when no sidecar exists."""

        existing = self.load_by_path(file_path)
        if existing is not None:
            return self.update_metadata(existing.entry_id, **fields)
        return self.create_metadata(file_path=file_path, **fields)

    def list_all(self) -> list[EntryMetadata]:
        """Return every readable sidecar sorted by creation time, newest first."""

        if not self.metadata_dir.exists():
            return []
        records: list[EntryMetadata] = []
        for path in sorted(self.metadata_dir.glob("*.json")):
            metadata = self._load_path(path)
            if metadata is not None:
                records.append(metadata)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records

    def search(
        self,
        query: str = "",
        *,
        tags: Iterable[str] | None = None,
        category: str | None = None,
        date_from: date | datetime | str | None = None,
        date_to: date | datetime | str | None = None,
        filename: str | None = None,
    ) -> list[MetadataSearchResult]:
        """Search metadata fields with optional tags, category, date, and filename filters."""

        normalized_query = query.strip().casefold()
        required_tags = {tag.strip().casefold() for tag in tags or [] if tag.strip()}
        normalized_category = (category or "").strip().casefold()
        normalized_filename = (filename or "").strip().casefold()
        start_dt = self._coerce_search_datetime(date_from, end_of_day=False)
        end_dt = self._coerce_search_datetime(date_to, end_of_day=True)
        results: list[MetadataSearchResult] = []
        for metadata in self.list_all():
            fields = {
                "entry_id": metadata.entry_id,
                "file_path": metadata.file_path,
                "category": metadata.category,
                "title": metadata.title,
                "short_title": metadata.short_title,
                "note": metadata.note,
                "user_tags": " ".join(metadata.user_tags),
            }
            tag_set = {tag.casefold() for tag in metadata.user_tags}
            if required_tags and not required_tags.issubset(tag_set):
                continue
            if normalized_category and metadata.category.casefold() != normalized_category:
                continue
            if normalized_filename:
                file_name = Path(metadata.file_path).name.casefold()
                if normalized_filename not in file_name and normalized_filename not in metadata.title.casefold():
                    continue
            created_at = self._parse_datetime(metadata.created_at)
            if start_dt and (created_at is None or created_at < start_dt):
                continue
            if end_dt and (created_at is None or created_at > end_dt):
                continue
            matched_fields = tuple(
                name for name, value in fields.items() if normalized_query and normalized_query in value.casefold()
            )
            if normalized_query and not matched_fields:
                continue
            filter_fields = []
            if required_tags:
                filter_fields.append("user_tags")
            if normalized_category:
                filter_fields.append("category")
            if normalized_filename:
                filter_fields.append("file_path")
            if (start_dt or end_dt):
                filter_fields.append("created_at")
            if not normalized_query:
                matched_fields = tuple(filter_fields)
            results.append(MetadataSearchResult(metadata, matched_fields))
        return results

    @staticmethod
    def _coerce_search_datetime(value: date | datetime | str | None, *, end_of_day: bool) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        if isinstance(value, date):
            return datetime.combine(value, time.max if end_of_day else time.min)
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.combine(date.fromisoformat(text), time.max if end_of_day else time.min)
        except ValueError:
            parsed = MetadataManager._parse_datetime(text)
            if parsed is None:
                raise ValueError(f"Invalid metadata search date: {value!r}. Use YYYY-MM-DD.")
            return parsed

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    def _path_for_id(self, entry_id: str) -> Path:
        safe_id = "".join(ch for ch in str(entry_id) if ch.isalnum() or ch in "-_") or uuid.uuid4().hex
        return self.metadata_dir / f"{safe_id}.json"

    def _load_path(self, path: Path) -> EntryMetadata | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            metadata = EntryMetadata.from_dict(data)
            return self._with_file_status(metadata)
        except Exception:
            logger.exception("Failed to load metadata sidecar: %s", path)
            return None

    @staticmethod
    def _with_file_status(metadata: EntryMetadata) -> EntryMetadata:
        target = Path(metadata.file_path).expanduser()
        file_exists = target.is_file()
        file_readable = False
        if file_exists:
            try:
                with target.open("r", encoding="utf-8"):
                    file_readable = True
            except Exception:
                file_readable = False
        data = metadata.to_dict()
        data["file_exists"] = file_exists
        data["file_readable"] = file_readable
        return EntryMetadata.from_dict(data)


_default_manager = MetadataManager(METADATA_DIR)


def get_default_metadata_manager() -> MetadataManager:
    """Return the process-wide default metadata manager."""

    return _default_manager
