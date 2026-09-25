import unittest

from otb_chess.chess_backend import rules as chess
from otb_chess.ui.material import material_summary


class MaterialTests(unittest.TestCase):
    def test_captures_both_sides_and_takeback_without_mutating_board(self):
        board = chess.Board()
        for move in ('e2e4', 'd7d5', 'e4d5'):
            board.push_uci(move)
        before = chess.snapshot_history(board)
        captured, balance = material_summary(board)
        self.assertEqual((captured[chess.WHITE], captured[chess.BLACK], balance), ('\u265f', '', 1))
        self.assertEqual(chess.snapshot_history(board), before)
        board.push_uci('d8d5')
        captured, balance = material_summary(board)
        self.assertEqual((captured[chess.WHITE], captured[chess.BLACK], balance), ('\u265f', '\u2659', 0))
        board.pop()
        self.assertEqual(material_summary(board)[1], 1)

    def test_en_passant_and_promotion_capture(self):
        board = chess.Board('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        board.push_uci('e5d6')
        self.assertEqual(material_summary(board), ({True: '\u265f', False: ''}, 1))
        board = chess.Board('1r5k/P7/8/8/8/8/8/7K w - - 0 1')
        board.push_uci('a7b8q')
        self.assertEqual(material_summary(board), ({True: '\u265c', False: ''}, 9))

    def test_fen_material_does_not_invent_capture_history(self):
        board = chess.Board('7k/8/8/8/8/8/P7/5r1K w - - 0 1')
        self.assertEqual(material_summary(board), ({True: '', False: ''}, -4))
