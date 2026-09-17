"""Position-only evaluation invariants and history independence."""
import unittest

from otb_chess.chess_backend.rules import Board
from otb_chess.core.evaluation import evaluate_position


class StaticEvaluationTests(unittest.TestCase):
    def test_start_is_equal_and_quiet_development_changes_score(self):
        board = Board()
        self.assertEqual(evaluate_position(board).text, "+0.00")
        board.push_uci("e2e4")
        score = evaluate_position(board).centipawns
        self.assertGreater(score, 0)
        board.turn = not board.turn
        self.assertEqual(evaluate_position(board).centipawns, score)
        board.pop()
        self.assertEqual(evaluate_position(board).centipawns, 0)

    def test_capture_and_colour_mirror(self):
        board = Board()
        for move in ("e2e4", "d7d5", "e4d5"):
            board.push_uci(move)
        score = evaluate_position(board).centipawns
        self.assertGreater(score, 80)
        self.assertEqual(evaluate_position(board.mirror()).centipawns, -score)
        self.assertEqual(evaluate_position(Board(board.fen())).centipawns, score)

    def test_terminal_positions(self):
        for fen, result in (
            ("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", "White wins — checkmate"),
            ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "Draw — stalemate"),
            ("7k/8/8/8/8/8/8/K7 w - - 0 1", "Draw — insufficient material"),
        ):
            self.assertEqual(evaluate_position(Board(fen)).text, result)


if __name__ == "__main__":
    unittest.main()
