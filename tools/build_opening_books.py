"""Build Polyglot repertoire books from the CC0 Lichess opening TSV files."""
from collections import Counter
import csv
import io
from pathlib import Path
import struct

import chess
import chess.pgn
import chess.polyglot


def build(folder):
    entries = {name: Counter() for name in ("all", "e4", "d4")}
    lines = 0
    for source in sorted((folder / "sources").glob("*.tsv")):
        for row in csv.DictReader(source.open(encoding="utf-8"), delimiter="\t"):
            game = chess.pgn.read_game(io.StringIO(row["pgn"]))
            if game.errors:
                raise ValueError(game.errors)
            moves = list(game.mainline_moves())
            if not moves:
                continue
            group = {"e2e4": "e4", "d2d4": "d4"}.get(moves[0].uci())
            board = game.board()
            for move in moves[:24]:
                target = move.to_square
                if board.is_castling(move):
                    target = chess.square(7 if board.is_kingside_castling(move) else 0,
                                          chess.square_rank(move.from_square))
                raw = target | (move.from_square << 6) | (((move.promotion or 1) - 1) << 12)
                key = (chess.polyglot.zobrist_hash(board), raw)
                entries["all"][key] += 1
                if group:
                    entries[group][key] += 1
                board.push(move)
            lines += 1
    for name, counts in entries.items():
        path = folder / f"lichess-{name}.bin"
        with path.open("wb") as stream:
            for (key, raw), count in sorted(counts.items()):
                stream.write(struct.pack(">QHHI", key, raw, min(count, 65535), 0))
        print(f"{path.name}: {len(counts)} entries")
    print(f"Source: {lines} opening lines")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "books")
