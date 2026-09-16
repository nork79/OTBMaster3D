"""Application-owned chess vocabulary, independent of the rules library.

Squares are integers a1=0 through h8=63; colours are White=True, Black=False.
These are data conventions, not move-generation or legality implementations.
"""

WHITE, BLACK = True, False
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(1, 7)
PIECE_TYPES = (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING)


def square(file_index, rank_index):
    return rank_index * 8 + file_index


def square_file(index):
    return index % 8


def square_rank(index):
    return index // 8
