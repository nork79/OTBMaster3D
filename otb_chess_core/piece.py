"""Immutable piece data independent of any provider enum."""

from dataclasses import dataclass
from .values import PIECE_TYPES


@dataclass(frozen=True, slots=True)
class Piece:
    piece_type: int
    color: bool

    def __post_init__(self):
        if type(self.piece_type) is not int or self.piece_type not in PIECE_TYPES:
            raise ValueError('Unknown piece type')
        if type(self.color) is not bool:
            raise ValueError('Colour must be a Boolean')
