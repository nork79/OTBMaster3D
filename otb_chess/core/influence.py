"""Geometric piece influence on an otherwise empty board (not legal moves)."""
from functools import lru_cache

from otb_chess.chess_backend import values as chess


INFLUENCE_COLORS = {1: (1.0, 1.0, 0.0), 2: (0.0, 1.0, 0.0), 3: (1.0, 0.0, 0.0)}
ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))


@lru_cache(maxsize=256)
def isolated_influence(pieces):
    """Return 64 masks: White=1, Black=2, both=3; pieces are (square, type, colour)."""
    masks = [0] * 64
    for square, kind, white in pieces:
        file, rank = chess.square_file(square), chess.square_rank(square)
        distance = 1
        if kind == chess.PAWN:
            directions = ((-1, 1 if white else -1), (1, 1 if white else -1))
        elif kind == chess.KNIGHT:
            directions = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
        else:
            directions = (DIAGONAL if kind == chess.BISHOP else ORTHOGONAL if kind == chess.ROOK
                          else ORTHOGONAL + DIAGONAL)
            if kind != chess.KING:
                distance = 7
        for dx, dy in directions:
            for step in range(1, distance + 1):
                x, y = file + dx * step, rank + dy * step
                if not (0 <= x < 8 and 0 <= y < 8):
                    break
                masks[chess.square(x, y)] |= 1 if white else 2
    return tuple(masks)
