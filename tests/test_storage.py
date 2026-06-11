import unittest
import zipfile
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from core.storage import StorageManager, StorageOperationResult
from core.utils import build_filename


class StorageManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base_dir = Path(self.tmp.name) / "ChronoNotes"
        self.exports_dir = Path(self.tmp.name) / "exports"
        self.storage = StorageManager(self.base_dir, self.exports_dir)

    def test_save_text_creates_parent_directories_and_loads_content(self):
        result = self.storage.save_text("2026-06-11/NOTE/example.txt", "hello storage")

        self.assertTrue(result.success, result.error)
        self.assertTrue(Path(result.path).exists())
        loaded = self.storage.load_text("2026-06-11/NOTE/example.txt")
        self.assertTrue(loaded.success, loaded.error)
        self.assertEqual(loaded.content, "hello storage")

    def test_load_text_handles_missing_file_gracefully(self):
        result = self.storage.load_text("missing.txt")

        self.assertFalse(result.success)
        self.assertEqual(result.content, "")
        self.assertIn("does not exist", result.message)

    def test_search_logs_returns_structured_results(self):
        self.storage.save_text("2026-06-11/NOTE/one.txt", "first line\nNeedle appears here")
        self.storage.save_text("2026-06-11/NOTE/two.txt", "no match here")

        results = self.storage.search_logs("needle")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].relative_path, "2026-06-11/NOTE/one.txt")
        self.assertEqual(results[0].line_number, 2)
        self.assertEqual(results[0].snippet, "Needle appears here")

    def test_create_today_zip_uses_relative_archive_paths(self):
        target_date = date(2026, 6, 11)
        self.storage.save_text("2026-06-11/NOTE/one.txt", "one")
        self.storage.save_text("2026-06-11/URL/two.txt", "two")

        result = self.storage.create_today_zip(target_date)

        self.assertTrue(result.success, result.error)
        with zipfile.ZipFile(result.path) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["2026-06-11/NOTE/one.txt", "2026-06-11/URL/two.txt", "manifest.json"],
            )

    def test_create_today_zip_reports_missing_day_without_exception(self):
        result = self.storage.create_today_zip(date(2026, 6, 11))

        self.assertFalse(result.success)
        self.assertIn("No notes", result.message)

    def test_export_hooks_can_be_registered(self):
        def exporter(notes_dir, destination):
            destination.write_text(f"exported from {notes_dir.name}", encoding="utf-8")
            return StorageOperationResult(True, str(destination), "exported")

        self.storage.register_exporter("json", exporter)
        result = self.storage.export_json(self.exports_dir / "notes.json")

        self.assertTrue(result.success, result.error)
        self.assertEqual(Path(result.path).read_text(encoding="utf-8"), "exported from ChronoNotes")

    def test_builtin_csv_export_writes_file(self):
        self.storage.save_text("2026-06-11/NOTE/one.txt", "one")

        result = self.storage.export_csv(self.exports_dir / "notes.csv")

        self.assertTrue(result.success, result.error)
        self.assertIn("relative_path", Path(result.path).read_text(encoding="utf-8"))

    def test_build_filename_accepts_injected_base_directory(self):
        full_path, folder, short, category = build_filename("remember this", self.base_dir)

        self.assertTrue(full_path.startswith(str(self.base_dir)))
        self.assertTrue(folder.startswith(str(self.base_dir)))
        self.assertEqual(short, "remember this")
        self.assertEqual(category, "NOTE")


if __name__ == "__main__":
    unittest.main()
