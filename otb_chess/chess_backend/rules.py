"""Rules provider boundary. Board, Move and Piece remain provider-native today.

New domain consumers should use chess_backend.position.ChessPosition. These
bindings remain for setup/rendering compatibility and provider internals. See
docs/chess_core_architecture.md for the current boundary and extraction steps.
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


def provider_move(move):
    """Convert an owned engine move to the current production rules provider."""
    return Move(move.from_square, move.to_square, move.promotion)


def snapshot_history(board):
    return History(board.root().fen(), tuple(owned_move(m) for m in board.move_stack), board.fen())


def termination_reason(board):
    """Automatic endings only; threefold and fifty moves require a claim."""
    if board.is_checkmate():
        return 'Checkmate'
    if board.is_stalemate():
        return 'Stalemate'
    if board.is_insufficient_material():
        return 'Draw - insufficient material'
    if board.is_seventyfive_moves():
        return 'Draw - seventy-five-move rule'
    if board.is_fivefold_repetition():
        return 'Draw - fivefold repetition'
    return None


def draw_claim_reason(board, intended_move=None):
    """Validate a current-position claim or a specified, unplayed legal move.

    The provider compares placement, turn, rights and legally available EP;
    counters are not part of repetition identity. Never synthesize history.
    """
    if termination_reason(board) is not None:
        return None
    if intended_move is not None:
        if intended_move not in board.legal_moves:
            return None
        board = board.copy()
        board.push(intended_move)
    if board.is_fifty_moves():
        return 'Draw - fifty-move rule'
    if board.is_repetition(3):
        return 'Draw - threefold repetition'
    return None


def restore_history(history):
    """Materialize transfer state using the currently selected live provider."""
    board = Board(history.root_fen)
    for move in history.moves:
        native = Move(move.from_square, move.to_square, move.promotion)
        if native not in board.legal_moves:
            raise ValueError('History contains an illegal move')
        board.push(native)
    if board.fen() != history.final_fen:
        raise ValueError('History does not match its final position')
    return board
