"""Standalone candidate qualification; no application or python-chess imports.

Run with an isolated Python 3.13 environment containing cozy-chess-py==0.1.1.
These are provider checks, not a migration or an application adapter.
"""
import copy
import importlib.util
import platform
import unittest
from importlib.metadata import version

import cozy_chess as c


def moves(board):
    return {str(move) for move in board.generate_moves()}


def perft(board, depth):
    if depth == 0:
        return 1
    legal = board.generate_moves()
    if depth == 1:
        return len(legal)
    total = 0
    for move in legal:
        child = copy.copy(board)
        child.play(move)
        total += perft(child, depth - 1)
    return total


class RulesProbe(unittest.TestCase):
    def test_isolated_install(self):
        self.assertIsNone(importlib.util.find_spec('chess'))
        self.assertEqual(version('cozy-chess-py'), '0.1.1')

    def test_perft(self):
        # Standard published perft positions/counts; no provider implementation copied.
        positions = [
            (c.Board().fen(), (20, 400, 8902, 197281)),
            ('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1',
             (48, 2039, 97862)),
            ('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1', (14, 191, 2812, 43238)),
        ]
        for fen, counts in positions:
            for depth, expected in enumerate(counts, 1):
                with self.subTest(fen=fen, depth=depth):
                    self.assertEqual(perft(c.Board.from_fen(fen), depth), expected)

    def test_piece_square_and_color_access(self):
        board = c.Board()
        self.assertEqual(int(c.Square.A1), 0)
        self.assertEqual(int(c.Square.H8), 63)
        self.assertEqual(board.piece_on(c.Square.E1), c.Piece.King)
        self.assertEqual(board.color_on(c.Square.E1), c.Color.White)
        self.assertEqual(len(board.occupied()), 32)
        self.assertEqual(board.side_to_move(), c.Color.White)

    def test_copy_and_illegal_move_are_nonmutating(self):
        board = c.Board()
        before = board.fen()
        self.assertFalse(board.try_play(c.Move.from_str('e2e5')))
        self.assertEqual(board.fen(), before)
        child = copy.copy(board)
        self.assertTrue(child.try_play(c.Move.from_str('e2e4')))
        self.assertEqual(board.fen(), before)
        self.assertNotEqual(child.fen(), before)
        self.assertEqual(copy.deepcopy(child).fen(), child.fen())

    def test_castling_encoding_and_execution(self):
        board = c.Board.from_fen('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        self.assertTrue({'e1h1', 'e1a1'} <= moves(board))
        self.assertNotIn('e1g1', moves(board))
        board.play(c.Move.from_str('e1h1'))
        self.assertEqual(board.piece_on(c.Square.G1), c.Piece.King)
        self.assertEqual(board.piece_on(c.Square.F1), c.Piece.Rook)
        self.assertFalse(board.castle_rights(c.Color.White).has_short())

    def test_castling_through_check_rejected(self):
        board = c.Board.from_fen('4kr2/8/8/8/8/8/8/R3K2R w KQ - 0 1')
        self.assertNotIn('e1h1', moves(board))
        self.assertIn('e1a1', moves(board))

    def test_en_passant_and_pin(self):
        board = c.Board.from_fen('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        self.assertIn('e5d6', moves(board))
        board.play(c.Move.from_str('e5d6'))
        self.assertIsNone(board.piece_on(c.Square.D5))
        self.assertEqual(board.piece_on(c.Square.D6), c.Piece.Pawn)
        pinned = c.Board.from_fen('k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        self.assertNotIn('e5d6', moves(pinned))

    def test_all_promotions(self):
        board = c.Board.from_fen('1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1')
        expected = {f'a7{target}{piece}' for target in ('a8', 'b8') for piece in 'qrbn'}
        self.assertEqual({m for m in moves(board) if m.startswith('a7')}, expected)
        for move in expected:
            child = copy.copy(board)
            child.play(c.Move.from_str(move))
            self.assertNotEqual(child.piece_on(c.Square.from_str(move[2:4])), c.Piece.Pawn)

    def test_checkmate_stalemate_and_material_gap(self):
        mate = c.Board.from_fen('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1')
        stale = c.Board.from_fen('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')
        self.assertEqual(mate.status(), c.GameStatus.Won)
        self.assertTrue(mate.checkers())
        self.assertEqual(moves(mate), set())
        self.assertEqual(stale.status(), c.GameStatus.Drawn)
        self.assertFalse(stale.checkers())
        self.assertEqual(moves(stale), set())
        bare = c.Board.from_fen('4k3/8/8/8/8/8/8/4K3 w - - 0 1')
        self.assertEqual(bare.status(), c.GameStatus.Ongoing)

    def test_fen_validation_and_counter_limits(self):
        prefix = '4k3/8/8/8/8/8/8/R3K3 w - - '
        for suffix in ('0 1', '99 65535', '100 1'):
            self.assertEqual(c.Board.from_fen(prefix + suffix).fen(), prefix + suffix)
        for fen in ('invalid', '8/8/8/8/8/8/8/8 w - - 0 1', prefix + '101 1', prefix + '0 65536'):
            with self.subTest(fen=fen), self.assertRaises(ValueError):
                c.Board.from_fen(fen)
        board = c.Board.from_fen(prefix + '100 1')
        self.assertEqual(board.status(), c.GameStatus.Drawn)
        self.assertTrue(board.generate_moves())
        board.play(c.Move.from_str('a1a2'))
        self.assertEqual(board.halfmove_clock, 100)

    def test_fen_ep_policy(self):
        board = c.Board()
        board.play(c.Move.from_str('e2e4'))
        self.assertEqual(board.fen().split()[3], 'e3')

    def test_repetition_requires_owned_history(self):
        board = c.Board()
        root = copy.copy(board)
        for _ in range(4):
            for move in ('g1f3', 'g8f6', 'f3g1', 'f6g8'):
                board.play(c.Move.from_str(move))
        self.assertTrue(board.same_position(root))
        self.assertEqual(board.hash(), root.hash())
        self.assertEqual(board.status(), c.GameStatus.Ongoing)
        for method in ('pop', 'san', 'parse_san', 'is_insufficient_material'):
            self.assertFalse(hasattr(board, method))


if __name__ == '__main__':
    print('Python:', platform.python_version(), 'Platform:', platform.platform(), flush=True)
    print('Candidate:', version('cozy-chess-py'), flush=True)
    unittest.main(verbosity=2)
