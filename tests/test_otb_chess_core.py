"""Ownership and dependency-boundary checks for the unused internal core."""

import ast
import dataclasses
from pathlib import Path
import subprocess
import sys
import unittest

from otb_chess_core import Board, Move, Piece
from otb_chess_core import values as v


class CoreBoundaryTests(unittest.TestCase):
    def test_owned_values(self):
        self.assertEqual(v.square(7, 7), 63)
        self.assertEqual((v.square_file(10), v.square_rank(10)), (2, 1))
        move = Move(8, 16)
        self.assertEqual({move, Move(8, 16)}, {move})
        with self.assertRaises(dataclasses.FrozenInstanceError):
            move.to_square = 24
        self.assertEqual(Piece(v.KING, v.WHITE).piece_type, 6)
        for args in ((-1, 0), (0, 64), (0, 1, v.KING)):
            with self.assertRaises(ValueError):
                Move(*args)
        with self.assertRaises(ValueError):
            Piece(v.PAWN, 1)

    def test_static_import_boundary(self):
        root = Path(__file__).resolve().parents[1] / 'otb_chess_core'
        allowed = {'dataclasses', 'typing', 'importlib', 'otb_chess_core'}
        for path in root.rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split('.')[0], allowed, str(path))
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    self.assertIn(node.module.split('.')[0], allowed, str(path))

    def test_import_needs_no_site_packages_or_application(self):
        root = Path(__file__).resolve().parents[1]
        script = (
            'import sys; import otb_chess_core; '
            'import otb_chess_core.rules.cozy_backend; '
            'assert not any(n.split(".")[0] in '
            '{"chess", "cozy_chess", "otb_chess", "PySide6", "OpenGL"} '
            'for n in sys.modules)'
        )
        subprocess.run([sys.executable, '-S', '-c', script], cwd=root, check=True,
                       capture_output=True, text=True)


def sq(name):
    return v.square(ord(name[0]) - ord('a'), int(name[1]) - 1)


def mv(source, target, promotion=None):
    return Move(sq(source), sq(target), promotion)


class BoardTests(unittest.TestCase):
    def test_initial_owned_api(self):
        board = Board()
        self.assertEqual(len(board.legal_moves()), 20)
        self.assertEqual(len(board.piece_map()), 32)
        self.assertIs(board.turn, True)
        self.assertEqual(board.piece_at(sq('e1')), Piece(v.KING, v.WHITE))
        self.assertTrue(all(type(m) is Move for m in board.legal_moves()))
        self.assertTrue(all(type(p) is Piece for p in board.piece_map().values()))
        board.piece_map().clear()
        self.assertEqual(len(board.piece_map()), 32)

    def test_history_copy_root_and_undo(self):
        board = Board()
        start = board.fen()
        first, second = mv('e2', 'e4'), mv('e7', 'e5')
        board.push(first)
        self.assertEqual(board.fen().split()[3], '-')
        after_first = board.fen()
        board.push(second)
        self.assertEqual(board.move_stack, (first, second))
        clone = board.copy()
        self.assertEqual(clone.pop(), second)
        self.assertEqual(clone.fen(), after_first)
        self.assertEqual(board.move_stack, (first, second))
        self.assertEqual(clone.root().fen(), start)
        self.assertEqual(clone.root().move_stack, ())
        board.pop()
        board.pop()
        self.assertEqual(board.fen(), start)
        with self.assertRaises(IndexError):
            board.pop()

    def test_illegal_and_failed_load_are_atomic(self):
        board = Board()
        board.push(mv('e2', 'e4'))
        before = board.fen(), board.move_stack, board.root().fen()
        for bad in (mv('e7', 'e4'), 'e7e5'):
            self.assertFalse(board.is_legal(bad))
            with self.assertRaises(ValueError):
                board.push(bad)
        for fen in ('bad', '8/8/8/8/8/8/8/8 w - - 0 1',
                    before[0].rsplit(' ', 1)[0] + ' 0'):
            with self.assertRaises(ValueError):
                board.set_fen(fen)
        self.assertEqual((board.fen(), board.move_stack, board.root().fen()), before)
        board.set_fen(Board().fen())
        self.assertEqual(board.move_stack, ())

    def test_large_counters_and_nonstandard_root(self):
        fen = '4k3/8/8/8/8/8/8/R3K3 b - - 999999 1000000'
        board = Board.from_fen(fen)
        self.assertEqual(board.fen(), fen)
        board.push(mv('e8', 'e7'))
        self.assertEqual((board.halfmove_clock, board.fullmove_number), (1000000, 1000001))
        self.assertEqual(board.copy().fen(), board.fen())
        self.assertEqual(board.root().fen(), fen)
        self.assertFalse(board.is_stalemate())
        board.pop()
        self.assertEqual(board.fen(), fen)

    def test_four_castles_and_undo(self):
        for side, rank in (('w', '1'), ('b', '8')):
            for target, rook in (('g', 'f'), ('c', 'd')):
                with self.subTest(side=side, target=target):
                    fen = f'r3k2r/8/8/8/8/8/8/R3K2R {side} KQkq - 0 1'
                    board = Board(fen)
                    move = mv('e' + rank, target + rank)
                    self.assertTrue(board.is_castling(move))
                    self.assertFalse(board.is_capture(move))
                    self.assertFalse(board.is_legal(mv('e' + rank, 'h' + rank)))
                    board.push(move)
                    self.assertEqual(board.piece_at(sq(target + rank)), Piece(v.KING, side == 'w'))
                    self.assertEqual(board.piece_at(sq(rook + rank)), Piece(v.ROOK, side == 'w'))
                    board.pop()
                    self.assertEqual(board.fen(), fen)

    def test_castling_through_check(self):
        board = Board('4kr2/8/8/8/8/8/8/R3K2R w KQ - 0 1')
        self.assertFalse(board.is_legal(mv('e1', 'g1')))
        self.assertTrue(board.is_legal(mv('e1', 'c1')))

    def test_ep_capture_undo_and_pin(self):
        fen = '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1'
        board = Board(fen)
        move = mv('e5', 'd6')
        self.assertEqual(board.fen(), fen)
        self.assertTrue(board.is_capture(move))
        self.assertTrue(board.is_en_passant(move))
        board.push(move)
        self.assertIsNone(board.piece_at(sq('d5')))
        self.assertEqual(board.halfmove_clock, 0)
        board.pop()
        self.assertEqual(board.fen(), fen)
        self.assertTrue(board.copy().is_legal(move))
        pinned = Board('k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        self.assertFalse(pinned.is_legal(move))
        self.assertEqual(pinned.fen().split()[3], '-')

    def test_promotions_both_colors_capture_and_quiet(self):
        for fen, source, targets, color in (
            ('1r2k3/P7/8/8/8/8/8/4K3 w - - 88 1', 'a7', ('a8', 'b8'), True),
            ('4k3/8/8/8/8/8/p7/1R2K3 b - - 88 1', 'a2', ('a1', 'b1'), False),
        ):
            for target in targets:
                for promotion in v.PROMOTION_TYPES:
                    with self.subTest(source=source, target=target, promotion=promotion):
                        board = Board(fen)
                        move = mv(source, target, promotion)
                        self.assertTrue(board.is_legal(move))
                        self.assertEqual(board.is_capture(move), target[0] == 'b')
                        board.push(move)
                        self.assertEqual(board.piece_at(sq(target)), Piece(promotion, color))
                        self.assertEqual(board.halfmove_clock, 0)
                        self.assertEqual(board.pop(), move)
                        self.assertEqual(board.fen(), fen)

    def test_check_and_terminal_policy(self):
        mate = Board('7k/6Q1/6K1/8/8/8/8/8 b - - 200 1')
        stale = Board('7k/5Q2/6K1/8/8/8/8/8 b - - 200 1')
        self.assertTrue(mate.is_check())
        self.assertTrue(mate.is_checkmate())
        self.assertFalse(mate.is_stalemate())
        self.assertTrue(stale.is_stalemate())
        self.assertFalse(stale.is_checkmate())
        bare = Board('4k3/8/8/8/8/8/8/4K3 w - - 200 1')
        self.assertFalse(bare.is_stalemate())
        self.assertTrue(bare.legal_moves())

    def test_perft_owned_adapter(self):
        def count(board, depth):
            if depth == 1:
                return len(board.legal_moves())
            before = board.fen(), board.move_stack
            total = 0
            for move in board.legal_moves():
                board.push(move)
                total += count(board, depth - 1)
                self.assertEqual(board.pop(), move)
            self.assertEqual((board.fen(), board.move_stack), before)
            return total
        # Fixtures/counts retained from tools/cozy_rules_probe.py, no oracle.
        for fen, counts in (
            (Board().fen(), (20, 400, 8902, 197281)),
            ('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1', (48, 2039, 97862)),
            ('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1', (14, 191, 2812, 43238)),
        ):
            for depth, expected in enumerate(counts, 1):
                with self.subTest(fen=fen, depth=depth):
                    self.assertEqual(count(Board(fen), depth), expected)

    def test_castling_attacks_on_start_transit_and_destination(self):
        for side, king_rank in (('w', '1'), ('b', '8')):
            for file in ('e', 'f', 'g', 'd', 'c'):
                row = {'e': '1k2r3', 'f': '1k3r2', 'g': '1k4r1', 'd': '1k1r4', 'c': '1kr5'}[file]
                own = 'R3K2R'
                if side == 'b':
                    row, own = row.upper(), own.lower()
                placement = f'{row}/8/8/8/8/8/8/{own}' if side == 'w' else f'{own}/8/8/8/8/8/8/{row}'
                board = Board(f'{placement} {side} {"KQ" if side == "w" else "kq"} - 0 1')
                for target in (('c', 'g') if file == 'e' else ('g',) if file in 'fg' else ('c',)):
                    with self.subTest(side=side, attacker=file, castle=target):
                        move = mv('e' + king_rank, target + king_rank)
                        before = board.fen()
                        self.assertFalse(board.is_legal(move))
                        with self.assertRaises(ValueError):
                            board.push(move)
                        self.assertEqual(board.fen(), before)

    def test_rights_after_king_rook_moves_and_rook_capture(self):
        for side, rank in (('w', '1'), ('b', '8')):
            fen = f'r3k2r/8/8/8/8/8/8/R3K2R {side} KQkq - 22 15'
            cases = [('e' + rank, 'd' + rank, 'kq' if side == 'w' else 'KQ'),
                     ('h' + rank, 'h' + ('2' if side == 'w' else '7'), 'Qkq' if side == 'w' else 'KQq'),
                     ('a' + rank, 'a' + ('2' if side == 'w' else '7'), 'Kkq' if side == 'w' else 'KQk'),
                     ('a' + rank, 'a' + ('8' if side == 'w' else '1'), 'Kk'),
                     ('h' + rank, 'h' + ('8' if side == 'w' else '1'), 'Qq')]
            for source, target, rights in cases:
                with self.subTest(side=side, source=source, target=target):
                    board = Board(fen)
                    board.push(mv(source, target))
                    self.assertEqual(board.fen().split()[2], rights)
                    board.pop()
                    self.assertEqual(board.fen(), fen)

    def test_ep_expiry_and_snapshot_restoration_both_colors(self):
        for fen, quiet, ep in (
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', mv('e1', 'f1'), mv('e5', 'd6')),
            ('4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1', mv('e8', 'f8'), mv('e4', 'd3')),
        ):
            board = Board(fen)
            board.push(quiet)
            self.assertEqual(board.fen().split()[3], '-')
            board.pop()
            self.assertEqual(board.fen(), fen)
            self.assertTrue(board.is_en_passant(ep))
            board.push(ep)
            self.assertEqual(len(board.piece_map()), 3)
            board.pop()
            self.assertEqual(board.fen(), fen)

    def test_double_check_and_king_exposure(self):
        double = Board('4r2k/8/8/8/1b6/8/8/R3K3 w - - 0 1')
        self.assertTrue(double.is_check())
        self.assertTrue(double.legal_moves())
        self.assertTrue(all(move.from_square == sq('e1') for move in double.legal_moves()))
        pinned = Board('4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1')
        before = pinned.fen(), pinned.piece_map(), pinned.move_stack
        with self.assertRaises(ValueError):
            pinned.push(mv('e2', 'f2'))
        self.assertEqual((pinned.fen(), pinned.piece_map(), pinned.move_stack), before)

    def test_fen_canonicalization_matrix(self):
        start = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        self.assertEqual(Board().fen(), start)
        fixtures = [start, 'r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 65536 999999',
                    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 100 65535',
                    'k3r3/8/8/3pP3/8/8/8/4K3 w - d6 101 65536',
                    '4k3/8/8/3p4/8/8/8/4K3 w - d6 0 1']
        for fen in fixtures:
            with self.subTest(fen=fen):
                board = Board(fen)
                expected = fen.split()
                if fen in fixtures[-2:]:
                    expected[3] = '-'
                self.assertEqual(board.fen(), ' '.join(expected))
                self.assertEqual(Board(board.fen()).fen(), board.fen())
                self.assertEqual(board.root().fen(), board.fen())

    def test_repeated_cycles_full_history_and_copy_branch(self):
        board = Board()
        root = board.fen()
        cycle = (mv('g1', 'f3'), mv('g8', 'f6'), mv('f3', 'g1'), mv('f6', 'g8'))
        snapshots = []
        for move in cycle * 5:
            snapshots.append(board.fen())
            board.push(move)
        self.assertEqual(board.move_stack, cycle * 5)
        self.assertEqual((board.halfmove_clock, board.fullmove_number), (20, 11))
        clone = board.copy()
        clone.pop()
        clone.push(mv('b8', 'c6'))
        self.assertNotEqual(clone.move_stack, board.move_stack)
        self.assertEqual(clone.root().fen(), root)
        for expected_move, expected_fen in zip(reversed(cycle * 5), reversed(snapshots)):
            self.assertEqual(board.pop(), expected_move)
            self.assertEqual(board.fen(), expected_fen)
        self.assertEqual(board.fen(), root)
        self.assertEqual(board.move_stack, ())
        for _ in range(3):
            for move in cycle:
                board.push(move)
            for move in reversed(cycle):
                self.assertEqual(board.pop(), move)
            self.assertEqual(board.fen(), root)

    def test_capture_queries_turn_and_counter_transitions(self):
        board = Board('4k3/8/8/8/8/8/r7/R3K3 w - - 100001 65536')
        move = mv('a1', 'a2')
        self.assertTrue(board.is_capture(move))
        self.assertFalse(board.is_en_passant(move))
        board.push(move)
        self.assertIs(board.turn, False)
        self.assertEqual(board.piece_at(sq('a2')), Piece(v.ROOK, True))
        self.assertIsNone(board.piece_at(sq('a1')))
        self.assertEqual((board.halfmove_clock, board.fullmove_number), (0, 65536))
        board.push(mv('e8', 'e7'))
        self.assertIs(board.turn, True)
        self.assertEqual((board.halfmove_clock, board.fullmove_number), (1, 65537))

    def test_every_public_board_member_returns_owned_data(self):
        board = Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        castle = mv('e1', 'g1')
        results = {
            'turn': board.turn, 'halfmove_clock': board.halfmove_clock,
            'fullmove_number': board.fullmove_number, 'move_stack': board.move_stack,
            'fen': board.fen(), 'legal_moves': board.legal_moves(),
            'is_legal': board.is_legal(castle), 'piece_at': board.piece_at(4),
            'piece_map': board.piece_map(), 'is_capture': board.is_capture(castle),
            'is_castling': board.is_castling(castle), 'is_en_passant': board.is_en_passant(castle),
            'copy': board.copy(), 'root': board.root(), 'is_check': board.is_check(),
            'is_checkmate': board.is_checkmate(), 'is_stalemate': board.is_stalemate(),
            'is_insufficient_material': board.is_insufficient_material(),
            'from_fen': Board.from_fen(board.fen()), 'push': board.push(castle),
        }
        results['pop'] = board.pop()
        results['set_fen'] = board.set_fen(Board().fen())
        self.assertEqual(set(results), {name for name in dir(Board) if not name.startswith('_')})
        def owned(value):
            self.assertIn(type(value), (Board, Move, Piece, bool, int, str, tuple, dict, type(None)))
            if isinstance(value, (Move, Piece)):
                for field in dataclasses.fields(value):
                    owned(getattr(value, field.name))
            elif isinstance(value, tuple):
                for item in value:
                    owned(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    owned(key)
                    owned(item)
        for value in results.values():
            owned(value)
        self.assertNotIn(mv('e1', 'h1'), results['legal_moves'])
        self.assertNotIn(mv('e1', 'a1'), results['legal_moves'])


class MaterialTests(unittest.TestCase):
    def test_bare_kings_and_single_minor_both_colors(self):
        for row in ('8', '2B5', '2N5', '2b5', '2n5'):
            with self.subTest(row=row):
                board = Board(f'7k/8/8/8/8/8/{row}/K7 w - - 0 1')
                self.assertIs(board.is_insufficient_material(), True)

    def test_same_square_color_bishops_including_promoted_material(self):
        for row in ('2B1b3', '2b1B3', '2B1B3', '2b1b3', 'B1b1B3', '1B1b4'):
            with self.subTest(row=row):
                self.assertTrue(Board(f'5k2/8/8/8/8/8/{row}/K7 w - - 0 1').is_insufficient_material())

    def test_pawn_rook_queen_preclude_material_draw(self):
        for kind in 'PRQprq':
            with self.subTest(piece=kind):
                self.assertFalse(Board(f'7k/8/8/8/8/8/2{kind}5/K7 w - - 0 1').is_insufficient_material())

    def test_minor_combinations_that_permit_mate(self):
        for row in ('2BN4', '2Bn4', '2bN4', '2bn4', '2NN4', '2Nn4',
                    '2nn4', '2Bb4', '2BB4', '2bb4'):
            with self.subTest(row=row):
                self.assertFalse(Board(f'7k/8/8/8/8/8/{row}/K7 w - - 0 1').is_insufficient_material())

    def test_capture_transition_and_query_preserve_complete_state(self):
        board = Board('7k/8/8/8/8/8/3r4/K1B5 w - - 999999 888888')
        self.assertFalse(board.is_insufficient_material())
        board.push(mv('c1', 'd2'))
        def state():
            return (board.fen(), board.root().fen(), board.move_stack,
                    board.piece_map(), board.turn, board.halfmove_clock,
                    board.fullmove_number, board.legal_moves())
        before = state()
        for _ in range(3):
            self.assertTrue(board.is_insufficient_material())
            self.assertEqual(state(), before)
        board.pop()
        self.assertFalse(board.is_insufficient_material())
