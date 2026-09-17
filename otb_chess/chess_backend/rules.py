"""Rules provider boundary. Board, Move and Piece remain provider-native today.

Replace these bindings with compatible adapters during rules migration. See
docs/chess-backend-migration.md for the required behaviour and remaining leaks.
"""

from chess import Board, Move, Piece
from otb_chess_core import Move as OwnedMove
from otb_chess.document_state import History
from otb_chess.chess_backend.values import (
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, PIECE_TYPES,
    square, square_file, square_rank,
)

__all__ = [
    "Board", "Move", "Piece", "WHITE", "BLACK", "PAWN", "KNIGHT", "BISHOP",
    "ROOK", "QUEEN", "KING", "PIECE_TYPES", "square", "square_file", "square_rank",
]


def owned_move(move):
    """Snapshot the current rules provider's move for the notation boundary."""
    return OwnedMove(move.from_square, move.to_square, move.promotion)


def snapshot_history(board):
    return History(board.root().fen(), tuple(owned_move(m) for m in board.move_stack), board.fen())


def restore_history(history):
    """Materialize transfer state using the currently selected live provider."""
    board = Board(history.root_fen)
    for move in history.moves:
        board.push(Move(move.from_square, move.to_square, move.promotion))
    if board.fen() != history.final_fen:
        raise ValueError('History does not match its final position')
    return board
