"""Phase 1 regressions for the live rules, adjudication and document paths."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from otb_chess.chess_backend import rules, notation
from otb_chess.core.game import Chess3D
from otb_chess.core.documents import read_fen
from otb_chess.document_state import History
from otb_chess_core import Move
from otb_chess.services.session import SessionStore
from otb_chess.ui.desktop_ui import MainWindow


CYCLE = ('g1f3', 'g8f6', 'f3g1', 'f6g8')


def play(board, moves):
    for move in moves:
        board.push_uci(move)
    return board


def host(board=None):
    game = Chess3D.__new__(Chess3D)
    game.board = board if board is not None else rules.Board()
    game.game_started = True
    game.game_over = False
    game.clock_paused = False
    game.clock_history = []
    game.awaiting_clock_press = False
    game.awaiting_clock_color = None
    game.engine_side = None
    game.engine_manager = Mock(engine=None, thinking=False, search_generation=0)
    game.refresh_move_list = Mock()
    game.play_game_sound = Mock()
    game.sound_game_end = 'end'
    game.result_text = 'Playing'
    return game


class RepetitionTests(unittest.TestCase):
    def test_threefold_requires_claim_and_fivefold_is_automatic(self):
        board = play(rules.Board(), CYCLE * 2)
        game = host(board)
        game.update_game_end()
        self.assertFalse(game.game_over)
        self.assertTrue(game.claim_draw())
        self.assertEqual(game.result_text, 'Draw - threefold repetition')
        self.assertFalse(game.game_started)
        game.play_game_sound.assert_called_once_with('end')
        self.assertFalse(game.claim_draw())
        self.assertFalse(game.try_move(12, 28, is_engine=True))
        play(board, CYCLE * 2)
        game = host(board)
        game.awaiting_clock_press = True
        game.update_game_end()
        self.assertEqual(game.result_text, 'Draw - fivefold repetition')
        self.assertFalse(game.awaiting_clock_press)
        game.update_game_end()
        game.play_game_sound.assert_called_once_with('end')

    def test_intended_move_claim_does_not_play_move_or_claim_early(self):
        board = play(rules.Board(), CYCLE + CYCLE[:3])
        before = rules.snapshot_history(board)
        game = host(board)
        self.assertFalse(game.claim_draw())
        self.assertFalse(game.claim_draw('b8c6'))
        self.assertFalse(game.claim_draw('e7e4'))
        self.assertFalse(game.claim_draw('bad'))
        self.assertTrue(game.claim_draw('f6g8'))
        self.assertEqual(rules.snapshot_history(board), before)

    def test_placement_and_side_to_move_must_match(self):
        board = play(rules.Board(), CYCLE * 2)
        board.push_uci('b1c3')
        self.assertFalse(board.is_repetition(3))
        # Same placement after an odd-length king circuit, opposite turn.
        board = rules.Board('7k/8/8/8/8/8/8/KR6 w - - 0 1')
        play(board, ('a1a2', 'h8h7', 'a2b2', 'h7h8', 'b2a1'))
        self.assertFalse(board.is_repetition(2))

    def test_lost_castling_rights_are_not_a_repetition(self):
        board = rules.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        cycle = ('h1h2', 'h8h7', 'h2h1', 'h7h8')
        play(board, cycle * 2)
        self.assertFalse(board.is_repetition(3))
        play(board, cycle)
        self.assertTrue(board.is_repetition(3))

    def test_only_legal_ep_distinguishes_repetition(self):
        for placement, expected in (
            ('4k3/8/8/3pP3/8/8/8/4K3', False),
            ('k3r3/8/8/3pP3/8/8/8/4K3', True),
            ('4k3/8/8/3p4/8/8/8/4K3', True),
        ):
            with self.subTest(placement=placement):
                board = rules.Board(f'{placement} w - d6 0 1')
                black_out, black_back = ('a8b8', 'b8a8') if placement.startswith('k') else ('e8f8', 'f8e8')
                cycle = ('e1f1', black_out, 'f1e1', black_back)
                play(board, cycle * 2)
                self.assertEqual(board.is_repetition(3), expected)

    def test_copy_pop_and_branch_preserve_real_history(self):
        board = play(rules.Board(), CYCLE * 2)
        clone = board.copy()
        clone.pop()
        clone.push_uci('b8c6')
        self.assertFalse(clone.is_repetition(3))
        self.assertTrue(board.is_repetition(3))
        self.assertFalse(board.root().is_repetition(2))
        game = host(board)
        game.takeback()
        self.assertFalse(game.game_over)
        self.assertIsNone(rules.draw_claim_reason(game.board))


class TerminationTests(unittest.TestCase):
    def test_starting_terminal_fen_is_adjudicated(self):
        game = host()
        game.selected_time_control = Mock(return_value=Mock(initial_seconds=60, increment_seconds=0, name='Test'))
        game.engine_side_var = Mock()
        game.engine_side_var.get.return_value = 'None'
        game.clock_mode_var = Mock()
        game.clock_mode_var.get.return_value = 'Online'
        game.clock_binding_var = Mock()
        game.book_var = Mock()
        game.persist = Mock()
        game.maybe_request_engine_move = Mock()
        game.sound_game_start = 'start'
        game.start_game('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1')
        self.assertTrue(game.game_over)
        self.assertFalse(game.game_started)
        self.assertEqual(game.result_text, 'Checkmate')

    def test_mate_stalemate_and_material_precede_move_count_draws(self):
        for fen, reason in (
            ('7k/6Q1/6K1/8/8/8/8/8 b - - 150 1', 'Checkmate'),
            ('7k/5Q2/6K1/8/8/8/8/8 b - - 150 1', 'Stalemate'),
            ('7k/8/8/8/8/8/8/K7 w - - 150 1', 'Draw - insufficient material'),
        ):
            game = host(read_fen(fen))
            game.update_game_end()
            self.assertTrue(game.game_over)
            self.assertEqual(game.result_text, reason)
            self.assertIsNone(rules.draw_claim_reason(game.board))

    def test_fifty_move_claim_and_seventyfive_move_automatic_thresholds(self):
        for half in (98, 99, 100, 149, 150):
            with self.subTest(half=half):
                board = rules.Board(f'7k/8/8/8/8/8/8/KR6 w - - {half} 30')
                game = host(board)
                game.update_game_end()
                self.assertEqual(game.game_over, half >= 150)
                if half < 150:
                    self.assertEqual(game.claim_draw(), half >= 100)
                    game = host(board)
                    self.assertEqual(game.claim_draw('b1b2'), half >= 99)

    def test_pawn_moves_and_captures_reset_halfmove_clock(self):
        for fen, move in (
            ('7k/8/8/8/8/8/P7/KR6 w - - 99 1', 'a2a3'),
            ('7k/8/8/8/8/8/1r6/KR6 w - - 99 1', 'b1b2'),
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 99 1', 'e5d6'),
        ):
            board = rules.Board(fen)
            self.assertIsNone(rules.draw_claim_reason(board, rules.Move.from_uci(move)))
            board.push_uci(move)
            self.assertEqual(board.halfmove_clock, 0)

    def test_insufficient_material_matrix(self):
        for row, insufficient in (('8', True), ('2B5', True), ('2N5', True),
                                  ('2B1b3', True), ('2Bb4', False),
                                  ('2NN4', False), ('2BN4', False), ('2P5', False)):
            with self.subTest(row=row):
                board = rules.Board(f'7k/8/8/8/8/8/{row}/K7 w - - 0 1')
                self.assertEqual(board.is_insufficient_material(), insufficient)

    def test_timeout_uses_opponents_material_both_colors(self):
        for color in (True, False):
            for draw in (True, False):
                board = rules.Board('7k/8/8/8/8/8/8/KR6 w - - 0 1' if draw
                                    else '6rk/8/8/8/8/8/8/KR6 w - - 0 1')
                board.push_uci('b1b2')
                if not color:
                    board = board.mirror()
                    board.push_uci('h1h2')  # Retain a real move for the clock gate.
                game = host(board)
                game.active_clock_color = color
                game.white_time = game.black_time = 0.01
                game.last_clock_tick = time.perf_counter() - 1
                game.update_clock()
                self.assertTrue(game.game_over)
                self.assertEqual(game.result_text.startswith('Draw'), draw)

    def test_resignation_and_claim_guards(self):
        game = host(play(rules.Board(), CYCLE * 2))
        game._review_live = game.board.copy()
        self.assertFalse(game.claim_draw())
        game._review_live = None
        game.engine_side = game.board.turn
        game.engine_manager.engine = object()
        self.assertFalse(game.claim_draw())
        game.resign(True)
        self.assertEqual(game.result_text, 'White resigned')

    def test_resignation_against_bare_king_is_a_draw(self):
        for color in (True, False):
            board = rules.Board('7k/8/8/8/8/8/8/KR6 w - - 0 1')
            game = host(board if color else board.mirror())
            game.resign(color)
            self.assertTrue(game.game_over)
            self.assertEqual(game.result_text, 'Draw - resignation with insufficient material')
            self.assertEqual(notation.read_pgn(game.export_pgn())[0].headers['Result'], '1/2-1/2')


class EnPassantTests(unittest.TestCase):
    def test_capture_expiry_and_undo_both_colors(self):
        for fen, capture, quiet, reply, victim in (
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6', 'e1f1', 'e8f8', 35),
            ('4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1', 'e4d3', 'e8f8', 'e1f1', 27),
        ):
            board = read_fen(fen)
            move = rules.Move.from_uci(capture)
            self.assertIn(move, board.legal_moves)
            self.assertTrue(board.is_en_passant(move))
            board.push(move)
            self.assertIsNone(board.piece_at(victim))
            self.assertEqual(board.halfmove_clock, 0)
            board.pop()
            self.assertEqual(board.fen(), fen)
            play(board, (quiet, reply))
            self.assertNotIn(move, board.legal_moves)
            board.pop()
            board.pop()
            self.assertIn(move, board.legal_moves)

    def test_ep_cannot_expose_file_or_rank_check_but_can_evade_check(self):
        for fen, uci, legal in (
            ('k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6', False),
            ('7k/8/8/r4pPK/8/8/8/8 w - f6 0 1', 'g5f6', False),
            ('7k/8/8/3pP3/4K3/8/8/8 w - d6 0 1', 'e5d6', True),
        ):
            board = read_fen(fen)
            self.assertEqual(rules.Move.from_uci(uci) in board.legal_moves, legal)


class RestorationTests(unittest.TestCase):
    def test_claim_and_resignation_are_exported_as_pgn_results(self):
        game = host(play(rules.Board(), CYCLE * 2))
        self.assertTrue(game.claim_draw())
        document = notation.read_pgn(game.export_pgn())[0]
        self.assertEqual(document.headers['Result'], '1/2-1/2')
        self.assertEqual(document.history, rules.snapshot_history(game.board))
        game.navigate_to_ply(2)
        self.assertEqual(notation.read_pgn(game.export_pgn())[0].headers['Result'], '1/2-1/2')
        game.return_to_live()
        restored = host()
        restored.load_document(document.history, document)
        self.assertTrue(restored.game_over)
        self.assertEqual(notation.read_pgn(restored.export_pgn())[0].headers['Result'], '1/2-1/2')
        restored.takeback()
        self.assertFalse(restored.game_over)
        self.assertEqual(notation.read_pgn(restored.export_pgn())[0].headers['Result'], '*')
        for color, result in ((True, '0-1'), (False, '1-0')):
            game = host()
            game.resign(color)
            self.assertEqual(notation.read_pgn(game.export_pgn())[0].headers['Result'], result)

    def test_fen_has_no_history_pgn_replay_does(self):
        board = play(rules.Board(), CYCLE * 2)
        isolated = read_fen(board.fen())
        self.assertFalse(isolated.is_repetition(2))
        self.assertIsNone(rules.draw_claim_reason(isolated))
        pgn = notation.export_pgn(rules.snapshot_history(board))
        restored = rules.restore_history(notation.read_pgn(pgn)[0].history)
        self.assertTrue(restored.is_repetition(3))
        self.assertEqual(restored.fen(), board.fen())

    def test_fen_and_pgn_rule_state_nonstandard_roots(self):
        for fen, move in (
            ('r3k2r/8/8/8/8/8/8/R3K2R b Kq - 87 42', 'a8a7'),
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 42', 'e5d6'),
            ('4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 42', 'e4d3'),
        ):
            board = read_fen(fen)
            self.assertEqual(board.fen(), fen)
            board.push_uci(move)
            history = rules.snapshot_history(board)
            restored = rules.restore_history(notation.read_pgn(notation.export_pgn(history))[0].history)
            self.assertEqual(restored.fen(), board.fen())
            restored.pop()
            self.assertEqual(restored.fen(), fen)

    def test_loading_terminal_position_stops_play_but_claimable_does_not(self):
        for board, over in ((rules.Board('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1'), True),
                            (play(rules.Board(), CYCLE * 2), False),
                            (play(rules.Board(), CYCLE * 4), True)):
            game = host()
            game.load_document(rules.snapshot_history(board))
            self.assertEqual(game.game_over, over)
            self.assertFalse(game.game_started)
            self.assertTrue(game.clock_paused)

    def test_automatic_result_overrides_unfinished_import_header(self):
        document = notation.read_pgn(
            '[SetUp "1"]\n[FEN "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"]\n[Result "*"]\n\n*')[0]
        game = host()
        game.load_document(document.history, document)
        self.assertEqual(notation.read_pgn(game.export_pgn())[0].headers['Result'], '1-0')

    def test_illegal_history_is_rejected_even_if_final_fen_matches(self):
        board = rules.Board()
        board.push(rules.Move.from_uci('e2e5'))
        history = History(rules.Board().fen(), (Move(12, 36),), board.fen())
        with self.assertRaisesRegex(ValueError, 'illegal'):
            rules.restore_history(history)

    def test_session_cannot_override_automatic_ending_with_stale_flags(self):
        game = host(play(rules.Board(), CYCLE * 4))
        game.white_time = game.black_time = 60
        game.increment = 0
        game.active_clock_color = True
        game.clock_mode = 'Online'
        game.clock_binding = 'Spacebar'
        game.clock_mode_var = Mock()
        game.clock_binding_var = Mock()
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore()
            store.path = Path(directory) / 'session.json'
            store.backup = Path(directory) / 'backup.json'
            store.save(game, force=True)
            self.assertIsNone(store.error)
            self.assertTrue(store.restore(game))
        self.assertTrue(game.game_over)
        self.assertFalse(game.game_started)
        self.assertIn('fivefold repetition', game.result_text)

    def test_desktop_claim_action_passes_move_and_honors_cancel(self):
        window = Mock()
        for text, accepted, expected in (('', True, None), (' f6g8 ', True, 'f6g8')):
            with patch('otb_chess.ui.desktop_ui.QInputDialog.getText', return_value=(text, accepted)):
                MainWindow.prompt_draw_claim(window)
            window.game.claim_draw.assert_called_with(expected)
        window.game.claim_draw.reset_mock()
        with patch('otb_chess.ui.desktop_ui.QInputDialog.getText', return_value=('', False)):
            MainWindow.prompt_draw_claim(window)
        window.game.claim_draw.assert_not_called()
