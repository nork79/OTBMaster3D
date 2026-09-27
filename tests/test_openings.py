import unittest
from otb_chess.chess_backend import rules
from otb_chess.chess_backend.openings import detect_opening
from otb_chess.services.settings import APP_DIR


class OpeningTests(unittest.TestCase):
    def test_opening_follows_history_and_takeback(self):
        board = rules.Board()
        folder = APP_DIR / 'books' / 'sources'
        self.assertIsNone(detect_opening(board, folder))
        for san in ('e4', 'e5', 'Nf3', 'Nc6', 'Bb5'):
            board.push_san(san)
        before = rules.snapshot_history(board)
        self.assertIn('Ruy Lopez', detect_opening(board, folder))
        self.assertEqual(before, rules.snapshot_history(board))
        board.pop()
        self.assertNotIn('Ruy Lopez', detect_opening(board, folder))
        self.assertIsNone(detect_opening(rules.Board('7k/8/8/8/8/8/P7/7K w - - 0 1'), folder))
