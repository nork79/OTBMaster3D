"""Supported engine play and bundled difficulty selection."""
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import json
from pathlib import Path
import tempfile
from otb_chess.chess_backend import rules, uci
from otb_chess.services.difficulty import DIFFICULTIES, engine_path, missing_files


class DifficultyTests(unittest.TestCase):
    def test_builtin_levels_run_with_correct_bundled_engine(self):
        from otb_chess.services.engine import EngineManager
        from otb_chess.bookmarks import capture_engine
        self.assertTrue(all(p.engine == 'fairy-stockfish' for p in DIFFICULTIES.values() if p.rating is not None and p.rating < 1500))
        self.assertEqual({p.engine for p in DIFFICULTIES.values()}, {'stockfish', 'fairy-stockfish'})
        for key, preset in DIFFICULTIES.items():
            with self.subTest(level=key):
                self.assertEqual(missing_files(key), [])
                app = SimpleNamespace(cfg={'engine_difficulty': key, 'engine_elo': preset.rating})
                manager = EngineManager(app)
                try:
                    ok, message = manager.load(str(engine_path(key)))
                    self.assertTrue(ok, message)
                    self.assertEqual(manager.loaded_configuration['engine_id'], preset.engine)
                    options = manager.engine.configuration_snapshot()['uci_options']
                    if preset.engine == 'fairy-stockfish':
                        self.assertFalse(options['Use NNUE'])
                    self.assertEqual(options['UCI_LimitStrength'], preset.rating is not None)
                    self.assertEqual(options['Skill Level'], preset.skill if preset.skill is not None else 20)
                    if preset.rating is not None:
                        self.assertEqual(options['UCI_Elo'], preset.rating)
                    board = rules.Board()
                    move = manager.engine.play(rules.snapshot_history(board), seconds=.03).move
                    self.assertIn(rules.provider_move(move), board.legal_moves)
                    saved = capture_engine(manager)
                    self.assertEqual(manager.restore_configuration(saved), (True, ''))
                    manager.engine.configure_strength(preset.rating)
                    self.assertEqual(capture_engine(manager)['profile_id'], saved['profile_id'])
                finally:
                    manager.unload()

    def test_saved_lower_selection_migrates_to_fairy_stockfish(self):
        from otb_chess.services import settings
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            path.write_text(json.dumps({'engine_difficulty': 'level_600',
                                       'engine_path': 'missing/engine.exe', 'engine_elo': 600}))
            with patch.object(settings, 'CONFIG_PATH', path):
                config = settings.load_config()
            self.assertEqual(Path(config['engine_path']), engine_path('level_600'))
            self.assertEqual(config['engine_elo'], 600)
            self.assertEqual(config['engine_difficulty'], 'level_600')

    def test_unsupported_saved_selection_resets_safely(self):
        from otb_chess.services import settings
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            path.write_text(json.dumps({'engine_difficulty': 'retired_preset',
                                       'engine_path': 'removed/engine.exe', 'engine_elo': 600}))
            with patch.object(settings, 'CONFIG_PATH', path):
                config = settings.load_config()
            self.assertEqual(config['engine_difficulty'], 'custom')
            self.assertIsNone(config['engine_elo'])
            self.assertEqual(config['engine_path'], settings.default_config()['engine_path'])

    def test_unsupported_bookmark_engine_is_not_launched(self):
        from otb_chess.services.engine import EngineManager
        from otb_chess.services.bookmarks import engine_reference_available
        manager = EngineManager(SimpleNamespace(cfg={}))
        previous = manager.engine = Mock()
        saved = {'engine_id': 'retired-engine', 'executable': 'removed/engine.exe'}
        with patch.object(uci.Engine, 'open') as launch:
            with self.assertLogs('otb_chess.services.engine', level='WARNING'):
                ok, message = manager.restore_configuration(saved)
            self.assertFalse(ok)
            self.assertIn('Current engine retained', message)
            self.assertIs(manager.engine, previous)
            launch.assert_not_called()
            previous.quit.assert_not_called()
        self.assertFalse(engine_reference_available(saved))

    def test_custom_executable_must_report_supported_engine(self):
        from otb_chess.services.engine import EngineManager
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'engine.exe'
            path.write_bytes(b'unsupported fixture')
            candidate = Mock()
            candidate.configuration_snapshot.return_value = {'name': 'Other engine'}
            manager = EngineManager(SimpleNamespace(cfg={'engine_difficulty': 'custom'}))
            with patch.object(uci.Engine, 'open', return_value=candidate):
                ok, message = manager.load(str(path))
            self.assertFalse(ok)
            self.assertIn('Only Stockfish and Fairy-Stockfish', message)
            candidate.quit.assert_called_once()
            self.assertIsNone(manager.engine)






if __name__ == '__main__':
    unittest.main()
