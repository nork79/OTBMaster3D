"""Rules provider boundary. Board, Move and Piece remain provider-native today.

Replace these bindings with compatible adapters during rules migration. See
docs/chess-backend-migration.md for the required behaviour and remaining leaks.
"""

from chess import Board, Move, Piece
from otb_chess.chess_backend.values import (
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, PIECE_TYPES,
    square, square_file, square_rank,
)

__all__ = [
    "Board", "Move", "Piece", "WHITE", "BLACK", "PAWN", "KNIGHT", "BISHOP",
    "ROOK", "QUEEN", "KING", "PIECE_TYPES", "square", "square_file", "square_rank",
]
