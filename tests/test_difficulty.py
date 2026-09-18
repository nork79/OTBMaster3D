"""Maia policy-only play and bundled difficulty selection."""
import unittest
from unittest.mock import Mock, patch
from otb_chess.chess_backend import rules, uci
from otb_chess.services.difficulty import DIFFICULTIES, engine_path, weights_path, missing_files


class DifficultyTests(unittest.TestCase):
    def test_maia_uses_one_node_and_ignores_stockfish_style(self):
        transport = Mock()
        board = rules.Board()
        transport.play.return_value = Mock(move=rules.Move.from_uci('e2e4'),ponder=None,info={})
        engine = uci.MaiaEngine(transport)
        engine.mistakes = 0
        result = engine.play(rules.snapshot_history(board),style='Active')
        self.assertEqual(rules.provider_move(result.move).uci(),'e2e4')
        self.assertEqual(transport.play.call_args.args[1].nodes,1)
        self.assertIsNone(transport.play.call_args.args[1].time)
        transport.analyse.assert_not_called()
        engine.configure_strength(300)
        transport.configure.assert_not_called()
        transport.analyse.return_value = {}
        engine.analyse(rules.snapshot_history(board))
        self.assertEqual(transport.analyse.call_args.args[1].nodes,1)

    def test_beginner_mistakes_are_legal_and_have_no_false_engine_score(self):
        transport = Mock()
        engine = uci.MaiaEngine(transport)
        engine.mistakes = .8
        board = rules.Board('4k3/8/8/8/8/8/4r3/4K3 w - - 0 1')
        with patch('otb_chess.chess_backend.uci.random.random',return_value=0):
            result = engine.play(rules.snapshot_history(board))
        self.assertIn(rules.provider_move(result.move),board.legal_moves)
        self.assertIsNone(result.info.score)
        transport.play.assert_not_called()

    def test_bundled_models_play_legal_moves_on_cpu(self):
        for key,preset in DIFFICULTIES.items():
            if preset.engine != 'maia' or preset.mistakes:
                continue
            if missing_files(key):
                self.skipTest('Maia CPU assets are not installed')
            with self.subTest(key=key):
                engine = uci.MaiaEngine.open_model(engine_path(key),weights_path(key))
                try:
                    board = rules.Board()
                    board.push_uci('e2e4')
                    result = engine.play(rules.snapshot_history(board))
                    self.assertIn(rules.provider_move(result.move),board.legal_moves)
                    self.assertEqual(result.info.nodes,1)
                finally:
                    engine.quit()

    def test_presets_resolve_bundled_engines(self):
        if not engine_path('club').is_file():
            self.skipTest('Install the optional bundled engines to check their assets')
        for key,preset in DIFFICULTIES.items():
            self.assertFalse(missing_files(key),key)
            if preset.engine == 'maia':
                self.assertEqual(engine_path(key).name,'lc0.exe')
                self.assertIn(str(preset.model),weights_path(key).name)
            else:
                self.assertIn('stockfish',engine_path(key).name)


if __name__ == '__main__':
    unittest.main()
