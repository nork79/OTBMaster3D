"""Provider contract tests: retain these when replacing python-chess."""

import ast
from pathlib import Path
import unittest

from otb_chess.chess_backend import rules, values


class BackendContractTests(unittest.TestCase):
    def test_initial_moves_and_square_conventions(self):
        board = rules.Board()
        self.assertEqual(len(list(board.legal_moves)),20)
        for rank in range(8):
            for file in range(8):
                index = values.square(file,rank)
                self.assertEqual((values.square_file(index),values.square_rank(index)),(file,rank))
        self.assertEqual(board.piece_at(4).piece_type,values.KING)
        self.assertEqual(board.piece_at(3).piece_type,values.QUEEN)

    def test_history_copy_fen_and_san(self):
        board = rules.Board()
        start = board.fen()
        move = rules.Move.from_uci('e2e4')
        self.assertEqual(board.san(move),'e4')
        board.push(move)
        copy = board.copy()
        copy.pop()
        self.assertEqual(copy.fen(),start)
        self.assertEqual(board.root().fen(),start)
        self.assertEqual(rules.Board(board.fen()).fen(),board.fen())

    def test_special_moves_and_checkmate(self):
        castle = rules.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        move = rules.Move.from_uci('e1g1')
        self.assertIn(move,castle.legal_moves)
        castle.push(move)
        self.assertEqual(castle.piece_at(5).piece_type,values.ROOK)
        ep = rules.Board()
        for uci in ('e2e4','a7a6','e4e5','d7d5'):
            ep.push(rules.Move.from_uci(uci))
        capture = rules.Move.from_uci('e5d6')
        self.assertTrue(ep.is_capture(capture))
        ep.push(capture)
        self.assertIsNone(ep.piece_at(values.square(3,4)))
        promotion = rules.Board('7k/P7/8/8/8/8/8/7K w - - 0 1')
        promotion.push(rules.Move.from_uci('a7a8n'))
        self.assertEqual(promotion.piece_at(56).piece_type,values.KNIGHT)
        mate = rules.Board()
        for uci in ('f2f3','e7e5','g2g4','d8h4'):
            mate.push(rules.Move.from_uci(uci))
        self.assertTrue(mate.is_checkmate())

    def test_third_party_imports_stay_inside_boundary(self):
        root = Path(__file__).resolve().parents[1]/'otb_chess'
        violations = []
        for path in root.rglob('*.py'):
            if 'chess_backend' in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                modules = [n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
                if any(name == 'chess' or name.startswith('chess.') for name in modules):
                    violations.append(str(path.relative_to(root)))
        self.assertEqual(violations,[])
