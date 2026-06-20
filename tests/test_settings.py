import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.settings import (
    AppSettings,
    MAX_HISTORY_ENTRIES,
    MAX_POLL_INTERVAL_SECONDS,
    MAX_SOUND_VOLUME,
    MIN_HISTORY_ENTRIES,
    MIN_POLL_INTERVAL_SECONDS,
    MIN_SOUND_VOLUME,
    data_directory_migration_required,
    load_settings,
    migrate_data_directory,
    parse_history_limit,
    parse_poll_interval,
    parse_sound_volume,
    save_settings,
)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings_path = Path(self.tmp.name) / "settings" / "settings.json"

    def test_missing_file_uses_defaults(self):
        result = load_settings(self.settings_path)

        self.assertTrue(result.used_defaults)
        self.assertEqual(result.settings, AppSettings.defaults())
        self.assertEqual(result.path, self.settings_path)

    def test_save_and_load_round_trip(self):
        settings = AppSettings.defaults().with_updates(
            start_monitoring_on_launch=False,
            clipboard_poll_interval=1.5,
            max_history_entries=42,
            sound_enabled=False,
            sound_volume=30,
            default_export_directory=str(Path(self.tmp.name) / "exports"),
            data_directory=str(Path(self.tmp.name) / "ChronoNotes"),
            theme="dark",
        )

        saved_path = save_settings(settings, self.settings_path)
        loaded = load_settings(saved_path)

        self.assertEqual(saved_path, self.settings_path)
        self.assertFalse(loaded.used_defaults)
        self.assertEqual(loaded.settings, settings)
        payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["max_history_entries"], 42)

    def test_malformed_json_falls_back_to_defaults(self):
        self.settings_path.parent.mkdir(parents=True)
        self.settings_path.write_text("not json", encoding="utf-8")

        result = load_settings(self.settings_path)

        self.assertTrue(result.used_defaults)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.settings, AppSettings.defaults())

    def test_invalid_values_are_clamped_or_replaced(self):
        self.settings_path.parent.mkdir(parents=True)
        self.settings_path.write_text(
            json.dumps(
                {
                    "clipboard_poll_interval": 999,
                    "max_history_entries": -10,
                    "sound_volume": 150,
                    "theme": "solarized",
                    "sound_events": {"copy": False, "unknown": False},
                    "default_export_directory": "",
                    "data_directory": "",
                }
            ),
            encoding="utf-8",
        )

        settings = load_settings(self.settings_path).settings

        self.assertEqual(settings.clipboard_poll_interval, MAX_POLL_INTERVAL_SECONDS)
        self.assertEqual(settings.max_history_entries, MIN_HISTORY_ENTRIES)
        self.assertEqual(settings.sound_volume, 100)
        self.assertEqual(settings.theme, "dark")
        self.assertFalse(settings.sound_events["copy"])
        self.assertTrue(settings.sound_events["start"])
        self.assertNotEqual(settings.default_export_directory, "")
        self.assertNotEqual(settings.data_directory, "")

    def test_minimum_poll_interval_is_enforced(self):
        settings = AppSettings.defaults().with_updates(clipboard_poll_interval=0.001)

        self.assertEqual(settings.clipboard_poll_interval, MIN_POLL_INTERVAL_SECONDS)

    def test_max_history_entries_is_enforced(self):
        settings = AppSettings.defaults().with_updates(max_history_entries=9999)

        self.assertEqual(settings.max_history_entries, MAX_HISTORY_ENTRIES)

    def test_setting_parsers_clamp_valid_numeric_text(self):
        self.assertEqual(parse_poll_interval("999"), MAX_POLL_INTERVAL_SECONDS)
        self.assertEqual(parse_poll_interval("0.001"), MIN_POLL_INTERVAL_SECONDS)
        self.assertEqual(parse_history_limit("9999"), MAX_HISTORY_ENTRIES)
        self.assertEqual(parse_history_limit("-2"), MIN_HISTORY_ENTRIES)
        self.assertEqual(parse_sound_volume("150"), MAX_SOUND_VOLUME)
        self.assertEqual(parse_sound_volume("-1"), MIN_SOUND_VOLUME)
        self.assertEqual(parse_sound_volume("40.6"), 41)

    def test_setting_parsers_report_field_specific_invalid_text(self):
        with self.assertRaisesRegex(ValueError, "Clipboard polling interval"):
            parse_poll_interval("fast")
        with self.assertRaisesRegex(ValueError, "history entries"):
            parse_history_limit("many")
        with self.assertRaisesRegex(ValueError, "Sound volume"):
            parse_sound_volume("loud")

    def test_setting_parsers_use_defaults_for_invalid_persisted_values(self):
        self.assertEqual(parse_poll_interval("fast", default=1.25), 1.25)
        self.assertEqual(parse_history_limit("many", default=25), 25)
        self.assertEqual(parse_sound_volume("loud", default=75), 75)

    def test_migrate_data_directory_copies_existing_notes_without_deleting_source(self):
        source = Path(self.tmp.name) / "old" / "ChronoNotes"
        destination = Path(self.tmp.name) / "new" / "ChronoNotes"
        note = source / "2026-06-11" / "NOTE" / "one.txt"
        note.parent.mkdir(parents=True)
        note.write_text("remember this", encoding="utf-8")

        self.assertTrue(data_directory_migration_required(source, destination))

        migrate_data_directory(source, destination)

        self.assertEqual((destination / "2026-06-11" / "NOTE" / "one.txt").read_text(encoding="utf-8"), "remember this")
        self.assertTrue(note.exists())

    def test_data_directory_migration_is_explicitly_skipped_for_missing_or_same_source(self):
        source = Path(self.tmp.name) / "missing"
        destination = Path(self.tmp.name) / "new" / "ChronoNotes"

        self.assertFalse(data_directory_migration_required(source, destination))
        migrate_data_directory(source, destination)
        self.assertTrue(destination.exists())
        self.assertFalse(data_directory_migration_required(destination, destination))


if __name__ == "__main__":
    unittest.main()
