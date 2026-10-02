"""Real Rodent play, native personalities, strength and bookmark restoration."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from otb_chess.bookmarks import capture_engine
from otb_chess.chess_backend import rules
from otb_chess.services import personalities, settings
from otb_chess.services.engine import EngineManager
from otb_chess.services.bookmarks import engine_reference_available


@unittest.skipUnless(sys.platform == "win32" and personalities.engine_path().is_file(), "Install Rodent IV first")
class RodentTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(cfg={"engine_difficulty": "personality", "engine_personality": "tal",
                                      "engine_elo": 1500, "engine_book_mode": "none", "engine_style": "Active"})
        self.manager = EngineManager(self.app)
        self.addCleanup(self.manager.unload)

    def load(self):
        ok, message = self.manager.load(str(personalities.engine_path()))
        self.assertTrue(ok, message)

    def test_all_personalities_play_and_restore_with_and_without_repertoire(self):
        for key in personalities.PERSONALITIES:
            for mode in ("none", "personality"):
                with self.subTest(personality=key, openings=mode):
                    self.app.cfg.update(engine_personality=key, engine_book_mode=mode)
                    self.load()
                    self.assertEqual(self.manager.engine.strength_range(), (800, 2800))
                    saved = capture_engine(self.manager)
                    self.assertEqual(saved['profile'], 'personality')
                    options = saved['settings']['uci_options']
                    self.assertTrue(options['PersonalityFile'].endswith(key + '.txt'))
                    self.assertEqual(options['UCI_Elo'], 1500)
                    self.assertEqual(options['UseBook'], mode == 'personality')
                    board = rules.Board()
                    move = self.manager.engine.play(rules.snapshot_history(board), seconds=.03).move
                    self.assertIn(rules.provider_move(move), board.legal_moves)
                    self.assertTrue(engine_reference_available(saved))
                    self.assertEqual(self.manager.restore_configuration(saved), (True, ''))
                    self.assertEqual(capture_engine(self.manager)['profile_id'], saved['profile_id'])

    def test_rating_endpoints_full_strength_and_native_style(self):
        self.load()
        self.app.board = rules.Board()
        for elo in (800, 2800, None):
            self.app.cfg['engine_elo'] = elo
            with patch.object(self.manager.engine, 'play', wraps=self.manager.engine.play) as play:
                self.manager.request_move()
                deadline = time.monotonic() + 5
                while self.manager.thinking and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertFalse(self.manager.thinking)
                self.assertIsNone(getattr(self.app, 'pending_engine_error', None))
                self.assertEqual(play.call_args.kwargs['style'], 'Balanced')
            options = self.manager.engine.configuration_snapshot()['uci_options']
            self.assertEqual(options['UCI_LimitStrength'], elo is not None)
            if elo is not None:
                self.assertEqual(options['UCI_Elo'], elo)

    def test_missing_or_changed_resources_retain_working_engine(self):
        self.load()
        saved = capture_engine(self.manager)
        previous = self.manager.engine
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'tal.txt'
            file.write_text('setoption name OwnAttack value 100\n')
            for path in (file, Path(folder) / 'missing.txt'):
                changed = deepcopy(saved)
                changed['settings']['rodent']['personality_file'] = str(path)
                with self.assertLogs('otb_chess.services.engine', level='WARNING'):
                    ok, message = self.manager.restore_configuration(changed)
                self.assertFalse(ok)
                self.assertIn('Current engine retained', message)
                self.assertIs(self.manager.engine, previous)

    def test_custom_book_and_config_round_trip(self):
        self.app.cfg.update(engine_book_mode='custom', book_path=str(settings.BOOK_DIR / 'lichess-e4.bin'))
        self.load()
        saved = capture_engine(self.manager)
        self.assertFalse(saved['settings']['uci_options']['UseBook'])
        self.assertEqual(saved['settings']['rodent']['custom_book'], self.app.cfg['book_path'])
        self.assertEqual(self.manager.restore_configuration(saved), (True, ''))
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'CONFIG_PATH', Path(folder) / 'config.json'):
            config = settings.default_config()
            config.update(self.app.cfg)
            config['engine_path'] = str(personalities.engine_path())
            self.assertTrue(settings.save_config(config))
            loaded = settings.load_config()
            for key in self.app.cfg:
                self.assertEqual(loaded[key], config[key])


if __name__ == '__main__':
    unittest.main()
