"""Deterministic UCI subprocess for protocol integration tests, not a chess engine."""

import sys
import chess

board = chess.Board()
for line in sys.stdin:
    command = line.strip()
    if command == "uci":
        print("id name UI Test Engine\nuciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("position "):
        position, _, moves = command.partition(" moves ")
        if position == "position startpos":
            board = chess.Board()
        else:
            board = chess.Board(position.removeprefix("position fen "))
        for move in moves.split():
            board.push_uci(move)
    elif command.startswith("go"):
        move = next(iter(board.legal_moves),None)
        uci = move.uci() if move else "0000"
        print(f"info depth 8 score cp 25 nodes 1000 pv {uci}",flush=True)
        print(f"bestmove {uci}",flush=True)
    elif command == "quit":
        break
