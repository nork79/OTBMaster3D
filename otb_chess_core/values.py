"""Owned data conventions: Boolean colours and a1=0 through h8=63."""

WHITE, BLACK = True, False
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(1, 7)
PIECE_TYPES = (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING)
PROMOTION_TYPES = (KNIGHT, BISHOP, ROOK, QUEEN)


def validate_square(index: int) -> None:
    if type(index) is not int or not 0 <= index < 64:
        raise ValueError('Square must be an integer from 0 to 63')


def square(file_index: int, rank_index: int) -> int:
    if any(type(n) is not int or not 0 <= n < 8 for n in (file_index, rank_index)):
        raise ValueError('File and rank must be integers from 0 to 7')
    return rank_index * 8 + file_index


def square_file(index: int) -> int:
    validate_square(index)
    return index % 8


def square_rank(index: int) -> int:
    validate_square(index)
    return index // 8
