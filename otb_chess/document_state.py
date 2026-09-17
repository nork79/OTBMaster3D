"""Owned transfer values for notation and recovery, never live board state.

Annotated PGN stays a serialized snapshot: the existing parser/writer owns its
tree. No second mutable game tree or live rules board is maintained here.
"""
from dataclasses import dataclass
from otb_chess_core import Move


@dataclass(frozen=True)
class History:
    root_fen: str
    moves: tuple[Move, ...]
    final_fen: str


@dataclass(frozen=True)
class Document:
    headers: dict[str, str]
    history: History
    annotated_pgn: str
