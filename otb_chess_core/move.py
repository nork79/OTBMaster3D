"""Immutable move data; validation here does not determine chess legality."""

from dataclasses import dataclass
from .values import PROMOTION_TYPES, validate_square


@dataclass(frozen=True, slots=True)
class Move:
    from_square: int
    to_square: int
    promotion: int | None = None

    def __post_init__(self):
        validate_square(self.from_square)
        validate_square(self.to_square)
        if self.promotion is not None and (
            type(self.promotion) is not int or self.promotion not in PROMOTION_TYPES
        ):
            raise ValueError('Promotion must be knight, bishop, rook or queen')
