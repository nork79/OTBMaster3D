"""Deterministic position estimate in centipawns, always from White's viewpoint.

This lightweight heuristic does not search moves or use engine results. It is
intended as immediate board feedback, not a substitute for tactical analysis.
"""
from dataclasses import dataclass

from otb_chess.chess_backend import values as chess
from otb_chess.chess_backend.position import ChessPosition


MATERIAL = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
            chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
PHASE = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}


@dataclass(frozen=True)
class StaticEvaluation:
    centipawns: int | None
    result: str | None = None

    @property
    def text(self):
        return self.result if self.result else f"{self.centipawns / 100:+.2f}"


def evaluate_position(board):
    position = ChessPosition.from_board(board)
    if position.is_checkmate():
        return StaticEvaluation(None, f"{'Black' if position.turn else 'White'} wins — checkmate")
    if position.is_stalemate():
        return StaticEvaluation(0, "Draw — stalemate")
    if position.is_insufficient_material():
        return StaticEvaluation(0, "Draw — insufficient material")

    pieces = position.pieces()
    phase = min(24, sum(PHASE.get(piece.piece_type, 0) for piece in pieces.values())) / 24
    pawns = {chess.WHITE: [0] * 8, chess.BLACK: [0] * 8}
    bishops = {chess.WHITE: 0, chess.BLACK: 0}
    score = 0.0
    for square, piece in pieces.items():
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        relative_rank = rank if piece.color == chess.WHITE else 7 - rank
        centre = 7 - (abs(2 * file - 7) + abs(2 * rank - 7)) / 2
        value = MATERIAL[piece.piece_type]
        if piece.piece_type == chess.PAWN:
            pawns[piece.color][file] += 1
            value += max(0, relative_rank - 1) * 6 + centre * 2
        elif piece.piece_type == chess.KNIGHT:
            value += centre * 10
        elif piece.piece_type == chess.BISHOP:
            bishops[piece.color] += 1
            value += centre * 5
        elif piece.piece_type == chess.ROOK:
            value += 15 if relative_rank == 6 else 0
        elif piece.piece_type == chess.QUEEN:
            value += centre * 2
        elif piece.piece_type == chess.KING:
            shelter = 20 if relative_rank == 0 and file in (1, 2, 6) else 0
            value += phase * (shelter - centre * 8) + (1 - phase) * centre * 8
        score += value if piece.color == chess.WHITE else -value

    for color, files in pawns.items():
        bonus = 25 if bishops[color] >= 2 else 0
        for file, count in enumerate(files):
            bonus -= max(0, count - 1) * 15
            neighbours = (files[file - 1] if file > 0 else 0) + (files[file + 1] if file < 7 else 0)
            if not neighbours:
                bonus -= count * 12
        score += bonus if color == chess.WHITE else -bonus
    return StaticEvaluation(round(score))
