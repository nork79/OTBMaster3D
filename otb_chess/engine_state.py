"""Immutable engine results. Scores are normalized to White's perspective."""
from dataclasses import dataclass
from otb_chess_core import Move


@dataclass(frozen=True)
class EngineScore:
    centipawns: int | None = None
    mate: int | None = None


@dataclass(frozen=True)
class EngineEvaluation:
    source_fen: str
    score: EngineScore | None = None
    depth: int | None = None
    seldepth: int | None = None
    nodes: int | None = None
    nps: int | None = None
    pv: tuple[Move, ...] = ()


@dataclass(frozen=True)
class EngineResult:
    move: Move | None
    ponder: Move | None
    info: EngineEvaluation
