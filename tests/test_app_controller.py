import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.app_controller import ApplicationController
from core.storage import StorageManager


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


if __name__ == "__main__":
    unittest.main()
