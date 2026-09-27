"""Offline opening recognition from the bundled CC0 Lichess repertoire."""

import csv
from functools import lru_cache
from pathlib import Path
import re

from . import rules


@lru_cache(maxsize=1)
def opening_lines(folder):
    lines = {}
    for path in sorted(Path(folder).glob('*.tsv')):
        with path.open(encoding='utf-8') as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                moves = tuple(re.sub(r'\d+\.(?:\.\.)?', '', row['pgn']).split())
                lines[moves] = f"{row['name']} ({row['eco']})"
    return lines


def detect_opening(board, folder):
    """Return the deepest named line in this board's recorded move history."""
    replay = board.root()
    if replay.fen().split()[:4] != rules.Board().fen().split()[:4]:
        return None
    lines = opening_lines(str(folder))
    longest = max(map(len, lines), default=0)
    moves = []
    found = None
    for move in board.move_stack[:longest]:
        moves.append(replay.san(move))
        replay.push(move)
        found = lines.get(tuple(moves), found)
    return found
