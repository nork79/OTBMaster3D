"""Private native boundary. Only owned values cross this module's interface."""
from importlib import import_module
from ..move import Move
from ..piece import Piece
from ..values import KING

PROVIDER_DISTRIBUTION = 'cozy-chess-py'
QUALIFIED_VERSION = '0.1.1'


class _Position:
    def __init__(self, fen):
        self._c = import_module('cozy_chess')
        self._native = self._c.Board.from_fen(fen)

    @property
    def turn(self):
        return self._native.side_to_move() == self._c.Color.White

    def fen(self):
        return self._native.fen()

    def piece_at(self, square):
        sq = self._c.Square.from_index(square)
        piece = self._native.piece_on(sq)
        if piece is None:
            return None
        return Piece(int(piece) + 1, self._native.color_on(sq) == self._c.Color.White)

    def _owned_move(self, native):
        source, target = int(native.from_square), int(native.to_square)
        mover, occupant = self.piece_at(source), self.piece_at(target)
        # Cozy castles onto its friendly rook. External orthodox moves land
        # the king on c/g; conversion is confined to this boundary.
        if mover.piece_type == KING and occupant is not None and occupant.color == mover.color:
            target = (source // 8) * 8 + (6 if target > source else 2)
        promotion = None if native.promotion is None else int(native.promotion) + 1
        return Move(source, target, promotion)

    def legal_moves(self):
        return tuple(self._owned_move(move) for move in self._native.generate_moves())

    def play(self, move):
        # Matching legal moves also rejects king-to-rook input as a second
        # public castling convention. The provider owns all legality rules.
        for native in self._native.generate_moves():
            if self._owned_move(native) == move:
                self._native.play(native)
                return
        raise ValueError('Illegal move')

    def is_check(self):
        return bool(self._native.checkers())
