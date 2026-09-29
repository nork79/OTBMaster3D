"""Internal chess-domain facade over the unchanged production rules provider.

No application services belong here. Native boards are exposed only through the
explicit legacy bridge while existing setup/rendering consumers are migrated.
"""
from collections import Counter
from dataclasses import dataclass

from otb_chess_core import Move, Piece
from otb_chess.document_state import History
from . import rules, notation

_DEFAULT_POSITION = object()


@dataclass(frozen=True)
class Termination:
    reason: str
    result: str


@dataclass(frozen=True)
class MoveDetails:
    move: Move
    capture: bool
    castling: bool
    # Destination/source pairs used to animate both king and rook when castling.
    origins: tuple[tuple[int, int], ...]


class ChessPosition:
    """One board owns placement, turn, counters, rights and repetition history.

    Normal construction and imports own their board. ``from_board`` explicitly
    borrows a legacy board by default so existing references stay synchronized.
    Copies, history reconstruction, and variation branches are independent.
    """

    def __init__(self, fen=_DEFAULT_POSITION):
        self._board = rules.Board() if fen is _DEFAULT_POSITION else rules.Board(fen)

    @classmethod
    def from_board(cls, board, *, copy=False):
        position = cls.__new__(cls)
        position._board = board.copy() if copy else board
        return position

    @property
    def legacy_board(self):
        """Temporary compatibility escape hatch; aliases, never duplicates state."""
        return self._board

    @classmethod
    def from_fen(cls, text):
        position = cls(text.strip())
        if not position.is_valid():
            raise ValueError('The FEN does not describe a valid chess position.')
        return position

    def set_fen(self, text):
        candidate = self.from_fen(text)
        self._board.set_fen(candidate.fen(raw_ep=True))

    def fen(self, *, raw_ep=False):
        return self._board.fen(en_passant='fen' if raw_ep else 'legal')

    def is_valid(self):
        return self._board.is_valid()

    @property
    def turn(self):
        return self._board.turn

    @property
    def fullmove_number(self):
        return self._board.fullmove_number

    @property
    def castling_rights(self):
        return self._board.castling_rights

    @property
    def ep_square(self):
        return self._board.ep_square

    def has_legal_en_passant(self):
        return self._board.has_legal_en_passant()

    def piece_at(self, square):
        piece = self._board.piece_at(square)
        return Piece(piece.piece_type, piece.color) if piece else None

    def pieces(self):
        return {square: Piece(piece.piece_type, piece.color)
                for square, piece in self._board.piece_map().items()}

    @property
    def moves(self):
        return tuple(rules.owned_move(move) for move in self._board.move_stack)

    def legal_moves(self):
        return tuple(rules.owned_move(move) for move in self._board.legal_moves)

    def is_legal(self, move):
        return rules.provider_move(move) in self._board.legal_moves

    def legal_targets(self, source):
        return {move.to_square for move in self.legal_moves() if move.from_square == source}

    def promotion_choices(self, source, destination):
        return {move.promotion for move in self.legal_moves()
                if move.from_square == source and move.to_square == destination and move.promotion}

    @staticmethod
    def parse_uci(text):
        return rules.owned_move(rules.Move.from_uci(text))

    @staticmethod
    def uci(move):
        return rules.provider_move(move).uci()

    def san(self, move):
        if not self.is_legal(move):
            raise ValueError('Illegal move')
        return notation.san(self.fen(), move)

    def parse_san(self, text):
        return rules.owned_move(self._board.parse_san(text))

    def move_details(self, move):
        if not self.is_legal(move):
            raise ValueError('Illegal move')
        native = rules.provider_move(move)
        castle = self._board.is_castling(native)
        origins = [(move.to_square, move.from_square)]
        if castle:
            rank = rules.square_rank(move.from_square)
            kingside = rules.square_file(move.to_square) > rules.square_file(move.from_square)
            origins.append((rules.square(5 if kingside else 3, rank),
                            rules.square(7 if kingside else 0, rank)))
        return MoveDetails(rules.owned_move(move), self._board.is_capture(native), castle, tuple(origins))

    def apply(self, move):
        if not self.is_legal(move):
            raise ValueError('Illegal move')
        self._board.push(rules.provider_move(move))

    def undo(self):
        return rules.owned_move(self._board.pop())

    def reset(self):
        self._board.reset()

    def copy(self):
        return self.from_board(self._board, copy=True)

    def at_ply(self, ply):
        if not 0 <= ply <= len(self._board.move_stack):
            raise ValueError('Ply outside move history')
        position = self.copy()
        while len(position._board.move_stack) > ply:
            position.undo()
        return position

    def history(self, *, raw_ep=False):
        root = self._board.root().fen(en_passant='fen' if raw_ep else 'legal')
        return History(root, self.moves, self.fen(raw_ep=raw_ep))

    @classmethod
    def from_history(cls, history, *, raw_ep=False):
        position = cls(history.root_fen)
        for move in history.moves:
            position.apply(move)
        if position.fen(raw_ep=raw_ep) != history.final_fen:
            raise ValueError('History does not match its final position')
        return position

    @staticmethod
    def read_pgn(text):
        return notation.read_pgn(text)

    def export_pgn(self, original=None, result=None):
        return notation.export_pgn(self.history(), original, result)

    def is_check(self):
        return self._board.is_check()

    def checked_king(self):
        return self._board.king(self.turn) if self.is_check() else None

    def is_checkmate(self):
        return self._board.is_checkmate()

    def is_stalemate(self):
        return self._board.is_stalemate()

    def is_insufficient_material(self):
        return self._board.is_insufficient_material()

    def is_repetition(self, count=3):
        return self._board.is_repetition(count)

    def termination(self):
        """Automatic endings only; preserve the established rules.py priority."""
        reason = rules.termination_reason(self._board)
        if reason is None:
            return None
        result = self._board.result() if self._board.is_checkmate() else '1/2-1/2'
        return Termination(reason, result)


    def loss_outcome(self, loser, *, on_time=False):
        """Existing timeout/resignation material policy; the controller triggers it."""
        if self._board.has_insufficient_material(not loser):
            reason = 'Draw - timeout with insufficient material' if on_time else 'Draw - resignation with insufficient material'
            return Termination(reason, '1/2-1/2')
        reason = (('Black' if loser else 'White') + ' wins on time' if on_time
                  else ('White' if loser else 'Black') + ' resigned')
        return Termination(reason, '0-1' if loser else '1-0')

    def variation_positions(self, moves, *, truncate=False):
        """Independent preview boards; invalid PV tails may be truncated for display."""
        position = self.copy()
        positions = [position.copy()]
        for move in moves:
            if not position.is_legal(move):
                if truncate:
                    break
                raise ValueError('Variation contains an illegal move')
            position.apply(move)
            positions.append(position.copy())
        return tuple(positions)

    def material(self):
        """Recorded captures by capturer and White-minus-Black material in pawns."""
        captured = {rules.WHITE: Counter(), rules.BLACK: Counter()}
        board = self._board.copy()
        while board.move_stack:
            move = board.pop()
            if board.is_en_passant(move):
                captured[board.turn][rules.PAWN] += 1
            else:
                piece = board.piece_at(move.to_square)
                if piece is not None and piece.color != board.turn:
                    captured[board.turn][piece.piece_type] += 1
        values = {rules.PAWN: 1, rules.KNIGHT: 3, rules.BISHOP: 3,
                  rules.ROOK: 5, rules.QUEEN: 9, rules.KING: 0}
        balance = sum(values[piece.piece_type] * (1 if piece.color else -1)
                      for piece in self._board.piece_map().values())
        return captured, balance
