"""Bundled assets, saved defaults, strength and style integration."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import chess
import chess.polyglot

from otb_chess.chess_backend import rules, uci
from otb_chess.services import settings


class EngineFeatureTests(unittest.TestCase):
    def test_defaults_migrate_once_and_preserve_selected_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            engine = root / "stockfish.exe"
            engine.touch()
            book = root / "lichess-all.bin"
            book.touch()
            config = root / "config.json"
            with patch.object(settings, "CONFIG_PATH", config), \
                    patch.object(settings, "ENGINE_DIR", root), \
                    patch.object(settings, "BOOK_DIR", root):
                config.write_text(json.dumps({"engine_path": "", "engine_side": "None"}))
                first = settings.load_config()
                self.assertEqual(first["engine_path"], str(engine))
                self.assertEqual(first["engine_side"], "Black")
                self.assertEqual(first["book_path"], str(book))
                first.update(engine_path="custom.exe", engine_elo=1500, engine_style="Quiet")
                settings.save_config(first)
                self.assertEqual(settings.load_config(), first)
                first["engine_path"] = ""
                settings.save_config(first)
                self.assertEqual(settings.load_config()["engine_path"], "")

    def test_books_contain_legal_opening_moves_and_sorted_keys(self):
        for name, expected in (("all", None), ("e4", "e2e4"), ("d4", "d2d4")):
            with self.subTest(book=name), chess.polyglot.open_reader(settings.BOOK_DIR / f"lichess-{name}.bin") as book:
                entries = list(book)
                self.assertGreater(len(entries), 1000)
                self.assertEqual([e.key for e in entries], sorted(e.key for e in entries))
                board = chess.Board()
                first = list(book.find_all(board))
                self.assertTrue(first)
                self.assertTrue(all(e.move in board.legal_moves for e in first))
                if expected:
                    self.assertEqual({e.move.uci() for e in first}, {expected})
                for _ in range(24):
                    moves = list(book.find_all(board))
                    if not moves:
                        break
                    self.assertTrue(all(e.move in board.legal_moves for e in moves))
                    board.push(max(moves, key=lambda e: e.weight).move)

    def test_style_prefers_active_or_quiet_moves(self):
        board = chess.Board("4k3/8/8/8/8/8/4R3/4K3 w - - 0 1")
        check, quiet = chess.Move.from_uci("e2e7"), chess.Move.from_uci("e2a2")
        self.assertGreater(uci.Engine.style_preference(board, check, "Active"),
                           uci.Engine.style_preference(board, quiet, "Active"))
        self.assertLess(uci.Engine.style_preference(board, check, "Quiet"),
                        uci.Engine.style_preference(board, quiet, "Quiet"))

    def test_stockfish_strength_styles_and_white_perspective_evaluation(self):
        executable = next(settings.ENGINE_DIR.rglob("stockfish*.exe"), None)
        if executable is None:
            self.skipTest("Bundled Windows Stockfish is not installed")
        import sys
        if sys.platform != "win32":
            self.skipTest("Windows executable")
        engine = uci.Engine.open(str(executable))
        self.addCleanup(engine.quit)
        self.assertEqual(engine.strength_range(), (1320, 3190))
        engine.configure_strength(1500)
        board = rules.Board()
        for style in ("Balanced", "Active", "Quiet"):
            result = engine.play(rules.snapshot_history(board), style=style)
            self.assertIn(rules.provider_move(result.move), board.legal_moves)
            self.assertIsNotNone(result.info.score)
        engine.configure_strength(None)
        board = rules.Board("7k/8/8/8/8/8/4Q3/K7 b - - 0 1")
        evaluation = engine.analyse(rules.snapshot_history(board))
        self.assertEqual(evaluation.source_fen, board.fen())
        self.assertTrue((evaluation.score.centipawns or 0) > 0 or (evaluation.score.mate or 0) > 0)


if __name__ == "__main__":
    unittest.main()
