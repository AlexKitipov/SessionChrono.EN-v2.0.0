import csv
import json
import unittest
import zipfile
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from core.storage import StorageManager
from ui.dialogs import ExportDialog


class ExportServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base_dir = self.root / "ChronoNotes"
        self.exports_dir = self.root / "exports"
        self.storage = StorageManager(self.base_dir, self.exports_dir)
        self.note_path = self.base_dir / "2026-06-10" / "NOTE" / "note.txt"
        self.url_path = self.base_dir / "2026-06-11" / "URL" / "url.txt"
        self.storage.save_text(self.note_path, "alpha note\nsecond line")
        self.storage.save_text(self.url_path, "https://example.com")
        self.note_meta = self.storage.metadata.create_metadata(
            file_path=self.note_path,
            category="NOTE",
            title="[NOTE] alpha note",
            short_title="alpha note",
            text_length=22,
            classifier_confidence=0.91,
            user_tags=["alpha", "export"],
            note="first test note",
            created_at="2026-06-10T12:00:00+00:00",
        )
        self.url_meta = self.storage.metadata.create_metadata(
            file_path=self.url_path,
            category="URL",
            title="[URL] example",
            short_title="example",
            text_length=19,
            classifier_confidence=0.88,
            created_at="2026-06-11T12:00:00+00:00",
        )

    def test_txt_export_includes_content_and_metadata(self):
        result = self.storage.export_txt("bundle.txt")

        self.assertTrue(result.success, result.error)
        self.assertTrue(str(result.path).startswith(str(self.exports_dir)))
        text = Path(result.path).read_text(encoding="utf-8")
        self.assertIn("ChronoNotes Plain Text Export", text)
        self.assertIn("[NOTE] alpha note", text)
        self.assertIn("Category: NOTE", text)
        self.assertIn("alpha note", text)

    def test_json_export_includes_metadata(self):
        result = self.storage.export_json("bundle.json")

        self.assertTrue(result.success, result.error)
        payload = json.loads(Path(result.path).read_text(encoding="utf-8"))
        self.assertEqual(payload["entry_count"], 2)
        note_entry = next(entry for entry in payload["entries"] if entry["category"] == "NOTE")
        self.assertEqual(note_entry["metadata"]["entry_id"], self.note_meta.entry_id)
        self.assertEqual(note_entry["metadata"]["user_tags"], ["alpha", "export"])
        self.assertIn("alpha note", note_entry["content"])

    def test_csv_export_writes_summary_rows(self):
        result = self.storage.export_csv("summary.csv")

        self.assertTrue(result.success, result.error)
        with Path(result.path).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["relative_path"], "2026-06-10/NOTE/note.txt")
        self.assertEqual(rows[0]["tags"], "alpha, export")
        self.assertEqual(rows[1]["category"], "URL")

    def test_markdown_export_honors_date_and_category_filters(self):
        result = self.storage.export_markdown(
            "filtered.md",
            date_from="2026-06-10",
            date_to="2026-06-10",
            category="NOTE",
        )

        self.assertTrue(result.success, result.error)
        markdown = Path(result.path).read_text(encoding="utf-8")
        self.assertIn("# ChronoNotes Export", markdown)
        self.assertIn("[NOTE] alpha note", markdown)
        self.assertIn("first test note", markdown)
        self.assertNotIn("https://example.com", markdown)

    def test_zip_export_includes_text_files_manifest_and_metadata(self):
        result = self.storage.export_zip("archive.zip")

        self.assertTrue(result.success, result.error)
        with zipfile.ZipFile(result.path) as archive:
            names = sorted(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("2026-06-10/NOTE/note.txt", names)
            self.assertIn(f"metadata/{self.note_meta.entry_id}.json", names)
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        self.assertEqual(manifest["entry_count"], 2)

    def test_export_notes_accepts_blank_destination_for_default_exports_dir(self):
        result = self.storage.export_notes("json", "")

        self.assertTrue(result.success, result.error)
        self.assertTrue(str(result.path).startswith(str(self.exports_dir)))
        self.assertEqual(Path(result.path).suffix, ".json")

    def test_export_notes_writes_selected_absolute_destination(self):
        destination = self.root / "chosen" / "manual.csv"

        result = self.storage.export_notes("csv", destination)

        self.assertTrue(result.success, result.error)
        self.assertEqual(Path(result.path), destination.resolve())
        self.assertTrue(destination.exists())

    def test_export_dialog_uses_format_specific_default_extensions(self):
        self.assertEqual(ExportDialog._default_extension("txt"), ".txt")
        self.assertEqual(ExportDialog._default_extension("json"), ".json")
        self.assertEqual(ExportDialog._default_extension("csv"), ".csv")
        self.assertEqual(ExportDialog._default_extension("markdown"), ".md")
        self.assertEqual(ExportDialog._default_extension("zip"), ".zip")

    def test_create_today_zip_routes_through_export_service(self):
        result = self.storage.create_today_zip(target_date=date(2026, 6, 11))

        self.assertTrue(result.success, result.error)
        self.assertTrue(str(result.path).startswith(str(self.exports_dir)))
        with zipfile.ZipFile(result.path) as archive:
            names = sorted(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("2026-06-11/URL/url.txt", names)
            self.assertNotIn("2026-06-10/NOTE/note.txt", names)


if __name__ == "__main__":
    unittest.main()
