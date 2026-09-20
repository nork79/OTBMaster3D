"""Preference saves must preserve the previous file on failure."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from otb_chess.services import settings


class SettingsTests(unittest.TestCase):
    def test_atomic_save_failure_preserves_preferences(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_PATH", Path(folder) / "config.json"):
            self.assertTrue(settings.save_config({"sound_enabled": False}))
            before = settings.CONFIG_PATH.read_bytes()
            with patch.object(settings.os, "replace", side_effect=OSError("disk error")), self.assertLogs(settings.__name__, level="WARNING"):
                self.assertFalse(settings.save_config({"sound_enabled": True}))
            self.assertEqual(settings.CONFIG_PATH.read_bytes(), before)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])
            with self.assertLogs(settings.__name__, level="WARNING"):
                self.assertFalse(settings.save_config({"camera_distance": float("nan")}))
            self.assertEqual(settings.CONFIG_PATH.read_bytes(), before)

    def test_existing_preferences_and_new_geometry_round_trip(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_PATH", Path(folder) / "nested" / "config.json"):
            config = settings.default_config()
            config.update(sound_profile="03_Tournament_Wood", sound_enabled=False,
                          board_mode="2D", board_type="marble", interface_theme="Forest",
                          bookmark_panel_geometry=[120, 140, 510, 470])
            self.assertTrue(settings.save_config(config))
            restored = settings.load_config()
            for key in ("sound_profile", "sound_enabled", "board_mode", "board_type", "interface_theme", "bookmark_panel_geometry"):
                self.assertEqual(restored[key], config[key])
            settings.CONFIG_PATH.write_text(json.dumps({"sound_enabled": False}), encoding="utf-8")
            self.assertIsNone(settings.load_config()["bookmark_panel_geometry"])
            self.assertFalse(settings.load_config()["sound_enabled"])
