import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.app_controller import ApplicationController
from core.storage import StorageManager
from ui.dialogs import SearchDialog


class FakeMonitor:
    instances = []

    def __init__(self, callback):
        self.callback = callback
        self.start_calls = 0
        self.stop_calls = 0
        self.running = False
        FakeMonitor.instances.append(self)

    def start(self):
        self.start_calls += 1
        if self.running:
            return True
        self.running = True
        return True

    def stop(self, timeout=1.0):
        self.stop_calls += 1
        self.running = False
        return True

    def is_running(self):
        return self.running


class RecordingSearchStorage:
    def __init__(self):
        self.base_dir = Path("/tmp/recording-search-storage")
        self.search_calls = []

    def search_logs(self, query="", **filters):
        self.search_calls.append((query, filters))
        return []

    def load_text(self, path):
        return None


class FakeSearchVariable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeSearchResultsList:
    def __init__(self):
        self.results = None

    def set_results(self, results):
        self.results = results


class ApplicationControllerTests(unittest.TestCase):
    def setUp(self):
        FakeMonitor.instances.clear()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base_dir = Path(self.tmp.name) / "ChronoNotes"
        exports_dir = Path(self.tmp.name) / "exports"
        self.storage = StorageManager(base_dir, exports_dir)

    def make_controller(self, **kwargs):
        return ApplicationController(
            storage=self.storage,
            monitor_factory=FakeMonitor,
            **kwargs,
        )

    def test_resume_and_pause_are_idempotent(self):
        controller = self.make_controller()

        self.assertTrue(controller.resume_monitoring())
        self.assertTrue(controller.resume_monitoring())
        self.assertTrue(controller.pause_monitoring())
        self.assertTrue(controller.pause_monitoring())

        monitor = FakeMonitor.instances[0]
        self.assertEqual(monitor.start_calls, 1)
        self.assertEqual(monitor.stop_calls, 1)
        self.assertFalse(controller.monitoring_active)

    def test_clipboard_text_is_saved_and_added_to_history(self):
        saved_entries = []
        controller = self.make_controller(on_entry_saved=saved_entries.append)
        controller.resume_monitoring()

        entry = controller.handle_clipboard_text("remember this")

        self.assertIsNotNone(entry)
        self.assertEqual(entry.title, "[NOTE] remember this")
        self.assertEqual(controller.last_record_path, entry.path)
        self.assertEqual(controller.history[0], entry)
        self.assertEqual(saved_entries, [entry])
        self.assertTrue(Path(entry.path).exists())
        self.assertEqual(Path(entry.path).read_text(encoding="utf-8"), "remember this")
        self.assertIsNotNone(entry.metadata_id)
        metadata = self.storage.load_metadata_by_path(entry.path)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.entry_id, entry.metadata_id)
        self.assertEqual(metadata.category, "NOTE")
        self.assertEqual(metadata.text_length, len("remember this"))

    def test_clipboard_text_is_ignored_when_paused(self):
        controller = self.make_controller()

        entry = controller.handle_clipboard_text("paused text")

        self.assertIsNone(entry)
        self.assertEqual(controller.history, [])
        self.assertIsNone(controller.last_record_path)

    def test_history_limit_is_enforced(self):
        controller = self.make_controller(history_limit=2)
        controller.resume_monitoring()

        controller.handle_clipboard_text("first")
        controller.handle_clipboard_text("second")
        controller.handle_clipboard_text("third")

        self.assertEqual([entry.text for entry in controller.history], ["third", "second"])

    def test_search_logs_forwards_structured_filters(self):
        storage = RecordingSearchStorage()
        controller = ApplicationController(storage=storage, monitor_factory=FakeMonitor)

        results = controller.search_logs(
            "needle",
            category="NOTE",
            date_from="2026-06-10",
            date_to="2026-06-11",
            tag="project",
            filename="alpha-note",
        )

        self.assertEqual(results, [])
        self.assertEqual(
            storage.search_calls,
            [
                (
                    "needle",
                    {
                        "category": "NOTE",
                        "date_from": "2026-06-10",
                        "date_to": "2026-06-11",
                        "tag": "project",
                        "filename": "alpha-note",
                    },
                )
            ],
        )

    def test_controller_satisfies_search_dialog_provider_contract(self):
        storage = RecordingSearchStorage()
        controller = ApplicationController(storage=storage, monitor_factory=FakeMonitor)
        dialog = SearchDialog.__new__(SearchDialog)
        dialog.storage = controller
        dialog.results_list = FakeSearchResultsList()
        dialog.query_var = FakeSearchVariable("needle")
        dialog.category_var = FakeSearchVariable("NOTE")
        dialog.date_from_var = FakeSearchVariable("2026-06-10")
        dialog.date_to_var = FakeSearchVariable("2026-06-11")
        dialog.tag_var = FakeSearchVariable("project")
        dialog.filename_var = FakeSearchVariable("alpha-note")
        dialog.summary_var = FakeSearchVariable()
        dialog.matches = []
        dialog.on_error = None

        dialog.run_search()

        self.assertTrue(callable(controller.load_text))
        self.assertEqual(dialog.matches, [])
        self.assertEqual(dialog.results_list.results, [])
        self.assertEqual(dialog.summary_var.get(), "0 match(es) found.")
        self.assertEqual(
            storage.search_calls,
            [
                (
                    "needle",
                    {
                        "category": "NOTE",
                        "date_from": "2026-06-10",
                        "date_to": "2026-06-11",
                        "tag": "project",
                        "filename": "alpha-note",
                    },
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
