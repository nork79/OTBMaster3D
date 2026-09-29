"""Extraction contracts tested through the internal public domain facade."""
import ast
from pathlib import Path
import subprocess
import sys
import unittest

from otb_chess.chess_backend.position import ChessPosition
from otb_chess.chess_backend import values
from otb_chess.document_state import History
from otb_chess_core import Move, Piece


CYCLE = ('g1f3', 'g8f6', 'f3g1', 'f6g8')


def play(position, moves):
    for text in moves:
        position.apply(position.parse_uci(text))
    return position


class ChessPositionTests(unittest.TestCase):
    def test_legal_illegal_move_turn_san_and_undo(self):
        position = ChessPosition()
        before = position.history()
        legal, illegal = position.parse_uci('e2e4'), position.parse_uci('e2e5')
        self.assertEqual(len(position.legal_moves()), 20)
        self.assertTrue(all(isinstance(move, Move) for move in position.legal_moves()))
        self.assertEqual(position.piece_at(4), Piece(values.KING, True))
        self.assertTrue(position.is_legal(legal))
        self.assertFalse(position.is_legal(illegal))
        with self.assertRaises(ValueError):
            position.apply(illegal)
        self.assertEqual(position.history(), before)
        self.assertEqual(position.san(legal), 'e4')
        self.assertEqual(position.parse_san('e4'), legal)
        position.apply(legal)
        self.assertFalse(position.turn)
        self.assertEqual(position.moves, (legal,))
        self.assertEqual(position.undo(), legal)
        self.assertEqual(position.history(), before)

    def test_fen_roundtrip_raw_ep_rights_counters_and_atomic_set(self):
        fen = 'r3k2r/8/8/3pP3/8/8/8/R3K2R w KQkq d6 12 17'
        position = ChessPosition.from_fen(fen)
        self.assertEqual(position.fen(raw_ep=True), fen)
        self.assertEqual(position.ep_square, 43)
        self.assertTrue(position.has_legal_en_passant())
        self.assertEqual(position.castling_rights, (1 << 0) | (1 << 7) | (1 << 56) | (1 << 63))
        self.assertEqual(position.fullmove_number, 17)
        snapshot = position.history(raw_ep=True)
        self.assertEqual(ChessPosition.from_history(snapshot, raw_ep=True).history(raw_ep=True), snapshot)
        with self.assertRaises(ValueError):
            position.set_fen('8/8/8/8/8/8/8/8 w - - 0 1')
        self.assertEqual(position.history(raw_ep=True), snapshot)
        position.set_fen(ChessPosition().fen())
        self.assertEqual(position.moves, ())

    def test_raw_and_legal_only_en_passant_modes_remain_distinct(self):
        position = play(ChessPosition(), ('e2e4',))
        self.assertEqual(position.ep_square, 20)
        self.assertFalse(position.has_legal_en_passant())
        self.assertEqual(position.fen().split()[3], '-')
        self.assertEqual(position.fen(raw_ep=True).split()[3], 'e3')
        for raw in (False, True):
            snapshot = position.history(raw_ep=raw)
            restored = ChessPosition.from_history(snapshot, raw_ep=raw)
            self.assertEqual(restored.ep_square, 20)
            self.assertEqual(restored.history(raw_ep=raw), snapshot)

    def test_castling_legality_and_animation_origins(self):
        position = ChessPosition('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        before = position.history()
        move = position.parse_uci('e1g1')
        details = position.move_details(move)
        self.assertTrue(details.castling)
        self.assertEqual(dict(details.origins), {6: 4, 5: 7})
        position.apply(move)
        self.assertEqual(position.piece_at(5), Piece(values.ROOK, True))
        position.undo()
        self.assertEqual(position.history(), before)
        attacked = ChessPosition('r3kr1r/8/8/8/8/8/8/R3K2R w KQ - 0 1')
        self.assertFalse(attacked.is_legal(move))

    def test_en_passant_legality_and_capture_details(self):
        position = ChessPosition('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        move = position.parse_uci('e5d6')
        self.assertTrue(position.is_legal(move))
        self.assertTrue(position.move_details(move).capture)
        position.apply(move)
        self.assertIsNone(position.piece_at(35))
        self.assertEqual(position.material()[1], 1)
        pinned = ChessPosition('k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        self.assertFalse(pinned.is_legal(move))
        self.assertFalse(pinned.has_legal_en_passant())

    def test_promotions_and_material_are_domain_data(self):
        position = ChessPosition('1r5k/P7/8/8/8/8/8/7K w - - 0 1')
        self.assertEqual(position.promotion_choices(48, 57), {2, 3, 4, 5})
        move = position.parse_uci('a7b8q')
        position.apply(move)
        captured, balance = position.material()
        self.assertEqual(captured[True][values.ROOK], 1)
        self.assertEqual(balance, 9)
        captured[True][values.ROOK] = 99
        self.assertEqual(position.material()[0][True][values.ROOK], 1)

    def test_check_and_automatic_endings_preserve_priority(self):
        checked = ChessPosition('4k3/8/8/8/8/8/4R3/4K3 b - - 0 1')
        self.assertTrue(checked.is_check())
        self.assertEqual(checked.checked_king(), 60)
        self.assertFalse(checked.is_checkmate())
        self.assertIsNone(checked.termination())
        cases = (
            ('7k/6Q1/6K1/8/8/8/8/8 b - - 150 1', 'Checkmate', '1-0'),
            ('7k/5Q2/6K1/8/8/8/8/8 b - - 150 1', 'Stalemate', '1/2-1/2'),
            ('7k/8/8/8/8/8/8/K7 w - - 150 1', 'Draw - insufficient material', '1/2-1/2'),
            ('7k/8/8/8/8/8/8/KR6 w - - 150 1', 'Draw - fifty-move rule', '1/2-1/2'),
        )
        for fen, reason, result in cases:
            with self.subTest(reason=reason):
                position = ChessPosition(fen)
                ending = position.termination()
                self.assertEqual((ending.reason, ending.result), (reason, result))
                self.assertEqual(position.is_checkmate(), reason == 'Checkmate')
                self.assertEqual(position.is_stalemate(), reason == 'Stalemate')

    def test_threefold_automatic_after_history_roundtrip(self):
        position = play(ChessPosition(), CYCLE * 2)
        restored = ChessPosition.from_history(position.history())
        self.assertTrue(restored.is_repetition())
        self.assertEqual(restored.termination().reason, 'Draw - threefold repetition')
        play(restored, CYCLE * 2)
        self.assertEqual(restored.termination().reason, 'Draw - threefold repetition')
        self.assertEqual(restored.termination().result, '1/2-1/2')


    def test_fifty_moves_is_automatic_after_actual_move(self):
        position = ChessPosition('7k/8/8/8/8/8/8/KR6 w - - 99 1')
        before = position.history()
        self.assertIsNone(position.termination())
        self.assertEqual(position.history(), before)
        position.apply(position.parse_uci('b1b2'))
        self.assertEqual(position.termination().reason, 'Draw - fifty-move rule')

    def test_repetition_distinguishes_only_legal_ep_and_castling_rights(self):
        for placement, repeated in (
                ('4k3/8/8/3pP3/8/8/8/4K3', False),
                ('k3r3/8/8/3pP3/8/8/8/4K3', True),
                ('4k3/8/8/3p4/8/8/8/4K3', True)):
            position = ChessPosition(f'{placement} w - d6 0 1')
            out, back = ('a8b8', 'b8a8') if placement.startswith('k') else ('e8f8', 'f8e8')
            play(position, ('e1f1', out, 'f1e1', back) * 2)
            self.assertEqual(position.is_repetition(), repeated)
        position = ChessPosition('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        play(position, ('h1h2', 'h8h7', 'h2h1', 'h7h8') * 2)
        self.assertFalse(position.is_repetition())

    def test_variation_copy_and_history_review_do_not_mutate_live_state(self):
        position = play(ChessPosition(), CYCLE * 2)
        before = position.history()
        branch = position.copy()
        branch.undo()
        branch.apply(branch.parse_uci('b8c6'))
        self.assertFalse(branch.is_repetition())
        self.assertEqual(position.at_ply(0).history().moves, ())
        self.assertEqual(position.at_ply(3).moves, before.moves[:3])
        with self.assertRaises(ValueError):
            position.at_ply(100)
        moves = tuple(map(position.parse_uci, ('e2e4', 'e7e5', 'a1a8')))
        self.assertEqual(len(position.variation_positions(moves, truncate=True)), 3)
        with self.assertRaises(ValueError):
            position.variation_positions(moves)
        self.assertEqual(position.history(), before)

    def test_history_rejects_illegal_moves_and_wrong_final_fen(self):
        position = ChessPosition()
        for moves, final in (((position.parse_uci('e2e5'),), position.fen()),
                             ((), play(position.copy(), ('e2e4',)).fen())):
            with self.assertRaises(ValueError):
                ChessPosition.from_history(History(position.fen(), moves, final))

    def test_pgn_annotations_black_root_and_results_survive_facade(self):
        text = '[Event "Study"]\n\n1. e4 {main} (1. d4 {side} d5) e5 2. Nf3 $1 *'
        document = ChessPosition.read_pgn(text)[0]
        position = ChessPosition.from_history(document.history)
        exported = position.export_pgn(document)
        self.assertIn('{ main }', exported)
        self.assertIn('d4 { side }', exported)
        self.assertIn('$1', exported)
        self.assertEqual(ChessPosition.read_pgn(exported)[0].history, document.history)
        position = ChessPosition('4k3/8/8/8/8/8/8/4K2R b - - 7 17')
        root = position.fen()
        position.apply(position.parse_san('Kf7'))
        exported = position.export_pgn(result='1/2-1/2')
        restored = ChessPosition.read_pgn(exported)[0]
        self.assertEqual(restored.history.root_fen, root)
        self.assertEqual(restored.history, position.history())
        self.assertEqual(restored.headers['Result'], '1/2-1/2')

    def test_timeout_and_resignation_material_policy(self):
        position = ChessPosition()
        self.assertEqual(position.loss_outcome(True).result, '0-1')
        self.assertEqual(position.loss_outcome(False, on_time=True).reason, 'White wins on time')
        position = ChessPosition('7k/8/8/8/8/8/8/KR6 w - - 0 1')
        self.assertEqual(position.loss_outcome(True).reason, 'Draw - resignation with insufficient material')
        self.assertEqual(position.loss_outcome(True, on_time=True).result, '1/2-1/2')


class ArchitectureTests(unittest.TestCase):
    def test_domain_imports_without_ui_services_or_filesystem_setup(self):
        code = '''
import importlib.abc
import sys
class BlockApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ('PySide6', 'tkinter', 'OpenGL', 'glfw', 'otb_chess.ui',
                     'otb_chess.core', 'otb_chess.graphics', 'otb_chess.services',
                     'otb_chess.bookmarks', 'otb_chess.chess_backend.uci',
                     'otb_chess.chess_backend.books')
        if any(fullname == name or fullname.startswith(name + '.') for name in forbidden):
            raise AssertionError('Domain imported application dependency: ' + fullname)
sys.meta_path.insert(0, BlockApplication())
from otb_chess.chess_backend.position import ChessPosition
p = ChessPosition()
p.apply(p.parse_san('e4'))
assert ChessPosition.from_history(p.history()).fen() == p.fen()
assert ChessPosition.read_pgn(p.export_pgn())[0].history == p.history()
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_domain_import_allowlist_prevents_deferred_reverse_dependencies(self):
        root = Path(__file__).resolve().parents[1] / 'otb_chess'
        allowed = {'collections', 'dataclasses', 'io', 'chess', 'chess.pgn',
                   'otb_chess_core', 'otb_chess.document_state',
                   'otb_chess.chess_backend.values'}
        for file in ('chess_backend/position.py', 'chess_backend/rules.py',
                     'chess_backend/notation.py', 'document_state.py'):
            tree = ast.parse((root / file).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        self.assertIn(name.name, allowed, file)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        self.assertEqual(node.level, 1, file)
                        self.assertIsNone(node.module, file)
                        self.assertLessEqual({name.name for name in node.names}, {'rules', 'notation'})
                    else:
                        self.assertIn(node.module, allowed, file)

    def test_controller_bridge_aliases_one_state_and_review_keeps_live_history(self):
        from otb_chess.core.documents import GameDocuments
        from unittest.mock import Mock
        host = GameDocuments()
        original = ChessPosition()
        host.board = original.legacy_board
        self.assertIs(host.position.legacy_board, original.legacy_board)
        host.position.apply(host.position.parse_uci('e2e4'))
        self.assertEqual(original.moves, host.position.moves)
        host.game_started = host.game_over = False
        host.clock_paused = True
        host.refresh_move_list = Mock()
        live = host.position.history()
        host.navigate_to_ply(0)
        self.assertEqual(host.position.moves, ())
        self.assertEqual(host.history_position().history(), live)
        host.return_to_live()
        self.assertIs(host.board, original.legacy_board)
        replacement = ChessPosition()
        host.board = replacement.legacy_board
        self.assertIs(host.position.legacy_board, replacement.legacy_board)
        self.assertEqual(host.position.moves, ())
