"""Multi-format export services for ChronoNotes."""

from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable

from .metadata import EntryMetadata, MetadataManager

SUPPORTED_EXPORT_FORMATS = ("txt", "json", "csv", "markdown", "zip")


@dataclass(frozen=True)
class ExportFilters:
    """Optional filters applied before exporting ChronoNotes entries."""

    date_from: date | datetime | str | None = None
    date_to: date | datetime | str | None = None
    category: str | None = None


@dataclass(frozen=True)
class ExportItem:
    """A note text file and its associated metadata, ready for export."""

    path: Path
    relative_path: str
    content: str
    metadata: EntryMetadata | None = None
    modified_at: str | None = None

    @property
    def category(self) -> str:
        if self.metadata is not None:
            return self.metadata.category
        parts = Path(self.relative_path).parts
        return parts[1] if len(parts) > 1 else self.path.parent.name

    @property
    def title(self) -> str:
        if self.metadata is not None:
            return self.metadata.title
        return self.path.stem

    @property
    def created_at(self) -> str | None:
        if self.metadata is not None:
            return self.metadata.created_at
        return self.modified_at

    def to_record(self) -> dict[str, Any]:
        """Return a JSON-serializable export record."""

        metadata = self.metadata.to_export_dict() if self.metadata is not None else None
        return {
            "relative_path": self.relative_path,
            "file_name": self.path.name,
            "title": self.title,
            "category": self.category,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "text_length": len(self.content),
            "line_count": len(self.content.splitlines()) or 1,
            "metadata": metadata,
            "content": self.content,
        }


class ChronoNotesExporter:
    """Export ChronoNotes text files and metadata to practical report formats."""

    def __init__(self, notes_dir: str | Path, metadata: MetadataManager):
        self.notes_dir = Path(notes_dir).expanduser().resolve()
        self.metadata = metadata

    def export(
        self,
        format_name: str,
        destination: str | Path,
        filters: ExportFilters | None = None,
    ) -> Path:
        """Write an export file for *format_name* and return its final path."""

        normalized = normalize_export_format(format_name)
        destination_path = Path(destination).expanduser().resolve()
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        items = self.collect_items(filters)
        if normalized == "txt":
            self._write_txt(destination_path, items, filters)
        elif normalized == "json":
            self._write_json(destination_path, items, filters)
        elif normalized == "csv":
            self._write_csv(destination_path, items)
        elif normalized == "markdown":
            self._write_markdown(destination_path, items, filters)
        elif normalized == "zip":
            self._write_zip(destination_path, items, filters)
        else:  # pragma: no cover - normalize_export_format guards this.
            raise ValueError(f"Unsupported export format: {format_name}")
        return destination_path

    def collect_items(self, filters: ExportFilters | None = None) -> list[ExportItem]:
        """Return readable text notes that match optional date/category filters."""

        filters = filters or ExportFilters()
        start_dt = coerce_export_datetime(filters.date_from, end_of_day=False)
        end_dt = coerce_export_datetime(filters.date_to, end_of_day=True)
        normalized_category = (filters.category or "").strip().casefold()
        metadata_by_path = {
            str(Path(record.file_path).expanduser().resolve()): record
            for record in self.metadata.list_all()
        }
        items: list[ExportItem] = []
        if not self.notes_dir.exists():
            return items
        for path in sorted(self.notes_dir.rglob("*.txt")):
            if not path.is_file():
                continue
            metadata = metadata_by_path.get(str(path.resolve()))
            category = metadata.category if metadata is not None else self._category_from_path(path)
            if normalized_category and category.casefold() != normalized_category:
                continue
            created_at = parse_datetime(metadata.created_at) if metadata is not None else None
            if start_dt or end_dt:
                comparable = created_at or self._date_from_relative_path(path) or self._modified_datetime(path)
                if comparable is None:
                    continue
                if start_dt and comparable < start_dt:
                    continue
                if end_dt and comparable > end_dt:
                    continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            try:
                relative_path = path.relative_to(self.notes_dir).as_posix()
            except ValueError:
                relative_path = path.name
            items.append(
                ExportItem(
                    path=path,
                    relative_path=relative_path,
                    content=content,
                    metadata=metadata,
                    modified_at=self._modified_iso(path),
                )
            )
        items.sort(key=lambda item: (item.created_at or item.modified_at or "", item.relative_path))
        return items

    def _write_txt(self, destination: Path, items: Iterable[ExportItem], filters: ExportFilters | None) -> None:
        lines = ["ChronoNotes Plain Text Export", self._filter_summary(filters), ""]
        for item in items:
            lines.extend(
                [
                    "=" * 72,
                    item.title,
                    f"Path: {item.relative_path}",
                    f"Category: {item.category}",
                    f"Created: {item.created_at or 'Unknown'}",
                    "-" * 72,
                    item.content.rstrip(),
                    "",
                ]
            )
        destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _write_json(self, destination: Path, items: list[ExportItem], filters: ExportFilters | None) -> None:
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_notes_dir": str(self.notes_dir),
            "filters": filters_to_dict(filters),
            "entry_count": len(items),
            "entries": [item.to_record() for item in items],
        }
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_csv(self, destination: Path, items: Iterable[ExportItem]) -> None:
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "relative_path",
                    "title",
                    "category",
                    "created_at",
                    "modified_at",
                    "text_length",
                    "line_count",
                    "tags",
                    "note",
                ],
            )
            writer.writeheader()
            for item in items:
                metadata = item.metadata
                writer.writerow(
                    {
                        "relative_path": item.relative_path,
                        "title": item.title,
                        "category": item.category,
                        "created_at": item.created_at or "",
                        "modified_at": item.modified_at or "",
                        "text_length": len(item.content),
                        "line_count": len(item.content.splitlines()) or 1,
                        "tags": ", ".join(metadata.user_tags) if metadata else "",
                        "note": metadata.note if metadata else "",
                    }
                )

    def _write_markdown(self, destination: Path, items: Iterable[ExportItem], filters: ExportFilters | None) -> None:
        lines = ["# ChronoNotes Export", "", self._filter_summary(filters), ""]
        for item in items:
            lines.extend(
                [
                    f"## {escape_markdown_heading(item.title)}",
                    "",
                    f"- **Path:** `{item.relative_path}`",
                    f"- **Category:** {item.category}",
                    f"- **Created:** {item.created_at or 'Unknown'}",
                ]
            )
            if item.metadata and item.metadata.user_tags:
                lines.append(f"- **Tags:** {', '.join(item.metadata.user_tags)}")
            if item.metadata and item.metadata.note:
                lines.extend([f"- **Note:** {item.metadata.note}"])
            lines.extend(["", "```text", item.content.rstrip(), "```", ""])
        destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _write_zip(self, destination: Path, items: list[ExportItem], filters: ExportFilters | None) -> None:
        manifest = {
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_notes_dir": str(self.notes_dir),
            "filters": filters_to_dict(filters),
            "entry_count": len(items),
            "entries": [item.to_record() | {"content": None} for item in items],
        }
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            for item in items:
                archive.write(item.path, item.relative_path)
                if item.metadata is not None:
                    archive.writestr(
                        f"metadata/{item.metadata.entry_id}.json",
                        json.dumps(item.metadata.to_export_dict(), indent=2, sort_keys=True) + "\n",
                    )

    def _filter_summary(self, filters: ExportFilters | None) -> str:
        data = filters_to_dict(filters)
        active = {key: value for key, value in data.items() if value}
        if not active:
            return "Filters: none"
        return "Filters: " + ", ".join(f"{key}={value}" for key, value in active.items())

    def _category_from_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.notes_dir).parts[1]
        except Exception:
            return path.parent.name or "NOTE"

    def _date_from_relative_path(self, path: Path) -> datetime | None:
        try:
            day = path.relative_to(self.notes_dir).parts[0]
            return datetime.combine(date.fromisoformat(day), time.min)
        except Exception:
            return None

    @staticmethod
    def _modified_iso(path: Path) -> str | None:
        modified = ChronoNotesExporter._modified_datetime(path)
        return modified.isoformat(timespec="seconds") if modified else None

    @staticmethod
    def _modified_datetime(path: Path) -> datetime | None:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return None


def normalize_export_format(format_name: str) -> str:
    """Normalize UI labels/extensions into service format names."""

    normalized = (format_name or "").strip().lower().lstrip(".")
    aliases = {"text": "txt", "plain text": "txt", "md": "markdown"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {format_name}")
    return normalized


def default_export_filename(format_name: str, filters: ExportFilters | None = None) -> str:
    """Build a deterministic, human-readable default export filename."""

    normalized = normalize_export_format(format_name)
    filters = filters or ExportFilters()
    if filters.date_from and filters.date_from == filters.date_to:
        stamp = str(filters.date_from)[:10]
    else:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    extension = "md" if normalized == "markdown" else normalized
    return f"ChronoNotes_{stamp}.{extension}"


def filters_to_dict(filters: ExportFilters | None) -> dict[str, str]:
    """Serialize export filters for report metadata."""

    filters = filters or ExportFilters()
    return {
        "date_from": serialize_filter_value(filters.date_from),
        "date_to": serialize_filter_value(filters.date_to),
        "category": (filters.category or "").strip(),
    }


def serialize_filter_value(value: date | datetime | str | None) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def coerce_export_datetime(value: date | datetime | str | None, *, end_of_day: bool) -> datetime | None:
    """Coerce an export date filter into a naive datetime boundary."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return datetime.combine(value, time.max if end_of_day else time.min)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.combine(date.fromisoformat(text), time.max if end_of_day else time.min)
    except ValueError:
        parsed = parse_datetime(text)
        if parsed is None:
            raise ValueError(f"Invalid export date: {value!r}. Use YYYY-MM-DD.")
        return parsed


def parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string as a naive UTC comparable datetime."""

    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def escape_markdown_heading(text: str) -> str:
    """Keep exported headings readable without changing note content."""

    return text.replace("\n", " ").strip() or "Untitled"
