"""Owned orthodox chess position, lossless counters and snapshot history."""
from .move import Move
from .values import KING, PAWN, BISHOP, KNIGHT, validate_square
from .rules.cozy_backend import _Position

STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


class Board:
    def __init__(self, fen=STARTING_FEN):
        self.set_fen(fen)

    @classmethod
    def from_fen(cls, fen):
        return cls(fen)

    @staticmethod
    def _parse(fen):
        if not isinstance(fen, str):
            raise ValueError('FEN must be a string')
        fields = fen.split()
        if len(fields) != 6:
            raise ValueError('FEN must have six fields')
        if any(not s.isascii() or not s.isdecimal() for s in fields[4:]):
            raise ValueError('FEN counters must be nonnegative decimal integers')
        half, full = map(int, fields[4:])
        if full < 1:
            raise ValueError('Fullmove number must be positive')
        if fields[2] != '-' and any(ch not in 'KQkq' for ch in fields[2]):
            raise ValueError('Only orthodox castling rights are supported')
        native = fields[:4] + [str(min(half, 100)), str(min(full, 65535))]
        return _Position(' '.join(native)), half, full

    def set_fen(self, fen):
        position, half, full = self._parse(fen)
        self._position, self._half, self._full = position, half, full
        self._history = []
        self._root_fen = self._snapshot()

    @property
    def turn(self):
        return self._position.turn

    @property
    def halfmove_clock(self):
        return self._half

    @property
    def fullmove_number(self):
        return self._full

    @property
    def move_stack(self):
        return tuple(move for _, move in self._history)

    def _snapshot(self):
        fields = self._position.fen().split()
        return ' '.join(fields[:4] + [str(self._half), str(self._full)])

    def fen(self):
        """Six-field FEN; EP target only when a legal EP capture exists."""
        fields = self._snapshot().split()
        if fields[3] != '-' and not any(self._is_ep(move) for move in self.legal_moves()):
            fields[3] = '-'
        return ' '.join(fields)

    def legal_moves(self):
        return self._position.legal_moves()

    def is_legal(self, move):
        return isinstance(move, Move) and move in self.legal_moves()

    def piece_at(self, square):
        validate_square(square)
        return self._position.piece_at(square)

    def piece_map(self):
        return {sq: piece for sq in range(64) if (piece := self.piece_at(sq)) is not None}

    def _is_ep(self, move):
        piece = self.piece_at(move.from_square)
        return (piece is not None and piece.piece_type == PAWN
                and move.from_square % 8 != move.to_square % 8
                and self.piece_at(move.to_square) is None)

    def is_en_passant(self, move):
        return self.is_legal(move) and self._is_ep(move)

    def is_capture(self, move):
        return self.is_legal(move) and (self.piece_at(move.to_square) is not None or self._is_ep(move))

    def is_castling(self, move):
        return (self.is_legal(move) and self.piece_at(move.from_square).piece_type == KING
                and abs(move.to_square - move.from_square) == 2)

    def push(self, move):
        if not self.is_legal(move):
            raise ValueError('Illegal move')
        snapshot = self._snapshot()
        reset_clock = self.piece_at(move.from_square).piece_type == PAWN or self.is_capture(move)
        next_half = 0 if reset_clock else self._half + 1
        next_full = self._full + (not self.turn)
        self._position.play(move)
        self._half, self._full = next_half, next_full
        self._history.append((snapshot, move))

    def pop(self):
        if not self._history:
            raise IndexError('No moves to undo')
        snapshot, move = self._history[-1]
        self._position, self._half, self._full = self._parse(snapshot)
        self._history.pop()
        return move

    def copy(self):
        result = Board(self._snapshot())
        result._root_fen = self._root_fen
        result._history = self._history.copy()
        return result

    def root(self):
        return Board(self._root_fen)

    def is_check(self):
        return self._position.is_check()

    def is_checkmate(self):
        return self.is_check() and not self.legal_moves()

    def is_stalemate(self):
        return not self.is_check() and not self.legal_moves()

    def is_insufficient_material(self) -> bool:
        """Recognize material-only impossibility of mate, not all dead positions.

        Two knights are not insufficient: inability to force mate is different
        from impossibility of mate. Bishops alone suffice only when every bishop
        is confined to the same square colour, regardless of piece ownership.
        """
        material = [(sq, p.piece_type) for sq, p in self.piece_map().items()
                    if p.piece_type != KING]
        if not material:
            return True
        if len(material) == 1:
            return material[0][1] in (BISHOP, KNIGHT)
        if any(kind != BISHOP for _, kind in material):
            return False
        return len({(sq // 8 + sq % 8) % 2 for sq, _ in material}) == 1
