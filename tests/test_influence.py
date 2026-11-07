import unittest

import chess

from otb_chess.core.influence import isolated_influence


class InfluenceTests(unittest.TestCase):
    def test_every_piece_and_square_matches_isolated_attacks(self):
        for white in (False, True):
            for kind in chess.PIECE_TYPES:
                for square in chess.SQUARES:
                    board = chess.Board.empty()
                    board.set_piece_at(square, chess.Piece(kind, white))
                    masks = isolated_influence(((square, kind, white),))
                    self.assertEqual({sq for sq, mask in enumerate(masks) if mask}, set(board.attacks(square)))
                    self.assertEqual(masks[square], 0)

    def test_blockers_are_ignored_and_shared_influence_combines(self):
        masks = isolated_influence(((chess.A1, chess.ROOK, True),
                                    (chess.A2, chess.PAWN, True),
                                    (chess.H8, chess.ROOK, False)))
        self.assertEqual(masks[chess.A3], 1)
        self.assertEqual(masks[chess.H7], 2)
        self.assertEqual(masks[chess.A8], 3)
        self.assertEqual(masks[chess.H1], 3)
        self.assertEqual(masks[chess.A2], 1)  # Occupied squares can be influenced by other pieces.
        self.assertEqual(masks[chess.A1], 0)

    def test_empty_position_has_no_influence(self):
        self.assertEqual(isolated_influence(()), (0,) * 64)

    def test_reported_h2_position_is_shared_influence(self):
        board = chess.Board('r1b1kb1r/ppp1pppp/3q1n2/8/3n4/2NP1N2/PPPBBPPP/R2QK2R w KQkq - 5 8')
        pieces = tuple((sq, p.piece_type, p.color) for sq, p in board.piece_map().items())
        self.assertEqual(isolated_influence(pieces)[chess.H2], 3)
        sources = {sq for sq, kind, white in pieces
                   if isolated_influence(((sq, kind, white),))[chess.H2]}
        self.assertEqual(sources, {chess.H1, chess.F3, chess.D6, chess.H8})
