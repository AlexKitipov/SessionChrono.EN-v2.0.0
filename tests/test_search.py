import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.storage import StorageManager


class FilteredSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.storage = StorageManager(self.root / "ChronoNotes", self.root / "exports")
        self.alpha_path = self.root / "ChronoNotes" / "2026-06-10" / "NOTE" / "alpha-note.txt"
        self.beta_path = self.root / "ChronoNotes" / "2026-06-11" / "URL" / "beta-link.txt"
        self.gamma_path = self.root / "ChronoNotes" / "2026-06-12" / "NOTE" / "gamma-note.txt"
        self.storage.save_text(self.alpha_path, "alpha body with shared needle")
        self.storage.save_text(self.beta_path, "beta body with shared needle")
        self.storage.save_text(self.gamma_path, "gamma body without the word")
        self.storage.metadata.create_metadata(
            file_path=self.alpha_path,
            category="NOTE",
            title="Alpha Project Note",
            short_title="Alpha",
            text_length=29,
            classifier_confidence=0.9,
            user_tags=["project", "alpha"],
            note="first annotation",
            created_at="2026-06-10T09:00:00+00:00",
        )
        self.storage.metadata.create_metadata(
            file_path=self.beta_path,
            category="URL",
            title="Beta Reference Link",
            short_title="Beta",
            text_length=28,
            classifier_confidence=0.8,
            user_tags=["reference"],
            note="second annotation",
            created_at="2026-06-11T09:00:00+00:00",
        )
        self.storage.metadata.create_metadata(
            file_path=self.gamma_path,
            category="NOTE",
            title="Gamma Project Note",
            short_title="Gamma",
            text_length=27,
            classifier_confidence=0.7,
            user_tags=["project", "gamma"],
            note="third annotation",
            created_at="2026-06-12T09:00:00+00:00",
        )

    def test_combines_text_category_tag_and_date_filters(self):
        results = self.storage.search_logs(
            "needle",
            category="NOTE",
            tag="project",
            date_from="2026-06-10",
            date_to="2026-06-11",
        )

        self.assertEqual([Path(result.path).name for result in results], ["alpha-note.txt"])
        self.assertEqual(results[0].category, "NOTE")
        self.assertEqual(results[0].tags, ("alpha", "project"))

    def test_filename_filter_matches_filename_or_title(self):
        by_filename = self.storage.search_logs(filename="beta-link")
        by_title = self.storage.search_logs(filename="gamma project")

        self.assertEqual([Path(result.path).name for result in by_filename], ["beta-link.txt"])
        self.assertEqual([Path(result.path).name for result in by_title], ["gamma-note.txt"])

    def test_query_matches_metadata_title_when_body_does_not_match(self):
        results = self.storage.search_logs("gamma project")

        self.assertEqual([Path(result.path).name for result in results], ["gamma-note.txt"])
        self.assertEqual(results[0].line_number, 0)
        self.assertIn("Gamma Project", results[0].snippet)

    def test_missing_file_metadata_result_is_safe(self):
        self.alpha_path.unlink()

        results = self.storage.search_logs("alpha", tag="project")

        self.assertEqual(len(results), 1)
        self.assertEqual(Path(results[0].path).name, "alpha-note.txt")
        self.assertFalse(results[0].file_exists)
        self.assertFalse(results[0].file_readable)
        self.assertIn("Missing file", results[0].snippet)


if __name__ == "__main__":
    unittest.main()
