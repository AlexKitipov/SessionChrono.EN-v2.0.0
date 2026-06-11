import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.metadata import MetadataManager
from core.storage import StorageManager


class MetadataManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.note_path = self.root / "ChronoNotes" / "2026-06-11" / "NOTE" / "entry.txt"
        self.note_path.parent.mkdir(parents=True)
        self.note_path.write_text("hello metadata", encoding="utf-8")
        self.metadata = MetadataManager(self.root / "metadata")

    def create_metadata(self):
        return self.metadata.create_metadata(
            file_path=self.note_path,
            category="NOTE",
            title="[NOTE] hello metadata",
            short_title="hello metadata",
            text_length=14,
            classifier_confidence=0.75,
            user_tags=["Project", "project", "important"],
            note="initial annotation",
        )

    def test_create_metadata_writes_json_sidecar(self):
        record = self.create_metadata()

        sidecar = self.root / "metadata" / f"{record.entry_id}.json"
        self.assertTrue(sidecar.exists())
        loaded = self.metadata.load(record.entry_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.file_path, str(self.note_path.resolve()))
        self.assertEqual(loaded.user_tags, ["important", "project"])
        self.assertEqual(loaded.note, "initial annotation")
        self.assertTrue(loaded.file_exists)
        self.assertTrue(loaded.file_readable)

    def test_update_metadata_changes_tags_and_note(self):
        record = self.create_metadata()

        updated = self.metadata.update_metadata(
            record.entry_id,
            user_tags=["archive", "Project"],
            note="revised annotation",
        )

        self.assertEqual(updated.user_tags, ["archive", "Project"])
        self.assertEqual(updated.note, "revised annotation")
        self.assertIsNotNone(updated.updated_at)
        reloaded = self.metadata.load(record.entry_id)
        self.assertEqual(reloaded.note, "revised annotation")

    def test_search_matches_title_note_and_tags(self):
        record = self.create_metadata()

        title_results = self.metadata.search("hello")
        note_results = self.metadata.search("annotation")
        tag_results = self.metadata.search(tags=["important"])

        self.assertEqual([item.metadata.entry_id for item in title_results], [record.entry_id])
        self.assertIn("note", note_results[0].matched_fields)
        self.assertEqual([item.metadata.entry_id for item in tag_results], [record.entry_id])

    def test_metadata_survives_missing_text_file(self):
        record = self.create_metadata()
        self.note_path.unlink()

        loaded = self.metadata.load(record.entry_id)

        self.assertIsNotNone(loaded)
        self.assertFalse(loaded.file_exists)
        self.assertFalse(loaded.file_readable)
        self.assertEqual(loaded.title, "[NOTE] hello metadata")

    def test_storage_manager_exposes_metadata_apis(self):
        storage = StorageManager(self.root / "ChronoNotes", self.root / "exports")
        storage.save_text("2026-06-11/NOTE/from-storage.txt", "from storage")
        path = self.root / "ChronoNotes" / "2026-06-11" / "NOTE" / "from-storage.txt"
        record = storage.metadata.create_metadata(
            file_path=path,
            category="NOTE",
            title="[NOTE] from storage",
            short_title="from storage",
            text_length=12,
            classifier_confidence=0.5,
        )

        loaded = storage.load_metadata_by_path(path)
        updated = storage.update_metadata(record.entry_id, user_tags=["stored"], note="via storage")
        results = storage.search_metadata("storage")

        self.assertEqual(loaded.entry_id, record.entry_id)
        self.assertEqual(updated.user_tags, ["stored"])
        self.assertEqual([item.metadata.entry_id for item in results], [record.entry_id])


if __name__ == "__main__":
    unittest.main()
