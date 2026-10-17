"""Popup and display-only variation preview regressions."""
import json
import threading
import time
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

import chess
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle, QStyleOptionSpinBox

from tests import test_desktop_ui as fixture
from otb_chess.chess_backend import rules
from otb_chess.engine_state import EngineEvaluation, EngineScore
from otb_chess.bookmarks import capture_position
from otb_chess.services import settings


class EngineAnalysisTests(unittest.TestCase):
    setUpClass = classmethod(fixture.DesktopTests.setUpClass.__func__)
    setUp = fixture.DesktopTests.setUp
    tearDown = fixture.DesktopTests.tearDown

    def line(self, moves=('e2e4', 'e7e5', 'g1f3'), score=34):
        return EngineEvaluation(self.game.board.fen(), EngineScore(centipawns=score), 18,
                                pv=tuple(rules.owned_move(chess.Move.from_uci(m)) for m in moves))

    def present(self, info=None):
        info = info or self.line()
        self.window.show_engine_info(info.source_fen, info)
        self.window.open_engine_analysis()
        return self.window.engine_panel

    def state(self):
        g = self.game
        return (capture_position(g.board), g.export_pgn(), g.white_time, g.black_time,
                g.active_clock_color, g.game_started, g.game_over, g.result_text,
                tuple(g.clock_history), g.awaiting_clock_press, g.awaiting_clock_color)

    def test_best_three_persist_rerank_and_replace_without_changing_live_lines(self):
        panel = self.window.engine_panel
        fen, token = self.game.board.fen(), self.game.analysis_position_token()
        initial = [self.line((move,), score) for move, score in
                   (('e2e4', 40), ('d2d4', 30), ('c2c4', 20))]
        panel.present(fen, initial, token)
        self.assertEqual(len(panel.best_lines), 3)
        newcomer = self.line(('g1f3',), 50)
        panel.present(fen, (newcomer,), token)
        self.assertEqual([chess.square_name(line[1][0].from_square) + chess.square_name(line[1][0].to_square) for line in panel.best_lines], ['g1f3', 'e2e4', 'd2d4'])
        self.assertEqual(len(panel.lines), 1)
        # A deeper but worse score changes only the live pane.
        panel.present(fen, (replace(newcomer, score=EngineScore(centipawns=10), depth=20),), token)
        self.assertIn('+0.50', panel.best_view.toPlainText())
        self.assertIn('+0.10', panel.line_view.toPlainText())
        panel.present(fen, (newcomer,), token)
        self.assertEqual(panel.best_lines[0][1][0], newcomer.pv[0])
        panel.select_move(2, 1, best=True)
        self.assertEqual(self.game.preview_board.peek().uci(), 'd2d4')
        selections = panel.best_view.extraSelections()
        self.assertEqual(selections[0].cursor.selectedText(), 'd4')
        panel.return_to_current()
        self.game.load_document(chess.Board())
        panel.refresh_preview()
        self.assertEqual(panel.best_lines, [])
        self.assertEqual(panel.best_view.toPlainText(), '')
        self.assertEqual(panel.candidates, {})

    def test_retained_score_only_improves_for_side_to_move(self):
        for black in (False, True):
            self.game.load_document(chess.Board())
            if black:
                self.game.board.push_uci('e2e4')
            panel = self.window.engine_panel
            fen, token = self.game.board.fen(), self.game.analysis_position_token()
            sign = -1 if black else 1
            move = 'e7e5' if black else 'e2e4'
            peak = self.line((move,), sign * 60)
            panel.present(fen, (peak,), token)
            worse = replace(peak, score=EngineScore(centipawns=sign * 50), depth=25)
            panel.present(fen, (worse,), token)
            self.assertIn(f'{sign * .6:+.2f}', panel.best_view.toPlainText())
            self.assertIn(f'{sign * .5:+.2f}', panel.line_view.toPlainText())
            better = replace(peak, score=EngineScore(centipawns=sign * 70), depth=12)
            panel.present(fen, (better,), token)
            self.assertIn(f'{sign * .7:+.2f}', panel.best_view.toPlainText())

    def test_best_three_ranks_black_and_mating_lines(self):
        self.game.board.push_uci('e2e4')
        panel = self.window.engine_panel
        lines = [self.line((move,), score) for move, score in
                 (('e7e5', 50), ('c7c5', -30), ('e7e6', 10))]
        panel.present(self.game.board.fen(), lines, self.game.analysis_position_token())
        self.assertEqual([chess.square_name(line[1][0].from_square) + chess.square_name(line[1][0].to_square) for line in panel.best_lines], ['c7c5', 'e7e6', 'e7e5'])
        ranked = [replace(lines[0], score=EngineScore(mate=mate)) for mate in (-2, -5, 5, 2)]
        ordered = sorted(ranked + [lines[1]], key=lambda info: panel.rank_score(info, False), reverse=True)
        self.assertEqual([info.score.mate for info in ordered], [-2, -5, None, 5, 2])

    def test_move_list_prefers_current_analysis_score(self):
        fen = 'r1b4r/ppp1kppp/5n2/b7/2B5/Q1P5/P4PPP/RN4K1 b - - 1 13'
        self.game.load_document(chess.Board(fen))
        self.assertEqual(self.window.move_list_evaluation.text(), '')
        info = self.line(moves=(), score=842)
        self.window.show_engine_info(fen, (info, self.line(moves=(), score=700)))
        self.assertEqual(self.window.move_list_evaluation.text(), '+8.42')
        self.assertEqual(self.window.static_evaluation.text(), '+8.42')
        self.window.refresh_moves()
        self.assertEqual(self.window.move_list_evaluation.text(), '+8.42')
        self.game.load_document(chess.Board())
        self.window.show_engine_info(fen, info)
        self.assertEqual(self.window.move_list_evaluation.text(), '+8.42')
        self.game.load_document(chess.Board(fen))
        self.assertEqual(self.window.move_list_evaluation.text(), '+8.42')

    def test_background_score_updates_with_analysis_disabled_and_rejects_stale_results(self):
        w, g = self.window, self.game
        self.assertFalse(g.analysis_enabled)
        self.assertFalse(w.engine_panel.isVisible())
        token = g.analysis_position_token()
        g.position_evaluator.poll.return_value = (token, self.line(score=842), None)
        w.poll_position_evaluation()
        self.assertEqual(w.move_list_evaluation.text(), '+8.42')
        g.board.push_uci('e2e4')
        w.refresh_moves()
        w.poll_position_evaluation()
        self.assertEqual(w.move_list_evaluation.text(), '+8.42')
        self.assertEqual(g.position_evaluator.request.call_args.args[0].final_fen, g.board.fen())
        g.position_evaluator.poll.return_value = (g.analysis_position_token(), None, 'Stockfish missing')
        w.poll_position_evaluation()
        self.assertEqual(w.move_list_evaluation.text(), '+8.42')
        self.assertEqual(w.move_list_evaluation.toolTip(), 'Stockfish missing')

    def test_move_list_engine_mate_and_missing_scores(self):
        fen = self.game.board.fen()
        for score, expected in ((EngineScore(mate=-3), 'Mate -3'),
                                (EngineScore(centipawns=-82), '-0.82')):
            self.window.show_engine_info(fen, EngineEvaluation(fen, score))
            self.assertEqual(self.window.move_list_evaluation.text(), expected)
            for missing in (None, EngineScore()):
                self.window.show_engine_info(fen, EngineEvaluation(fen, missing))
                self.assertEqual(self.window.move_list_evaluation.text(), expected)

    def test_mismatched_engine_result_cannot_replace_move_list_score(self):
        info = EngineEvaluation(chess.Board().fen(), EngineScore(centipawns=842))
        self.game.board.push_uci('e2e4')
        self.window.refresh_moves()
        expected = self.window.move_list_evaluation.text()
        self.window.show_engine_info(self.game.board.fen(), info)
        self.assertEqual(self.window.move_list_evaluation.text(), expected)

    def test_option_arrows_receive_clicks_and_save_values(self):
        panel = self.present()
        self.qt.processEvents()
        for theme in ('Dark', 'Warm Paper'):
            self.window.set_interface_theme(theme)
            self.qt.processEvents()
            for key, control in panel.options.items():
                with self.subTest(theme=theme, option=key):
                    original = control.value()
                    for subcontrol, expected in (
                            (QStyle.SubControl.SC_SpinBoxUp, original + control.singleStep()),
                            (QStyle.SubControl.SC_SpinBoxDown, original)):
                        option = QStyleOptionSpinBox()
                        control.initStyleOption(option)
                        rect = control.style().subControlRect(
                            QStyle.ComplexControl.CC_SpinBox, option, subcontrol, control)
                        self.assertFalse(control.lineEdit().geometry().intersects(rect))
                        # Route clicks to the actual child under the pointer, as the OS does.
                        target = control.childAt(rect.center()) or control
                        QTest.mouseClick(target, Qt.MouseButton.LeftButton,
                                         pos=target.mapFrom(control, rect.center()))
                        self.assertAlmostEqual(control.value(), expected)
                        self.assertAlmostEqual(settings.load_config()['analysis_options'][key], expected)

    def test_nonmodal_single_window_and_sidebar_cleanup(self):
        panel = self.present()
        self.assertFalse(panel.isModal())
        self.assertFalse(self.window.sidebar.isAncestorOf(panel))
        self.assertFalse(self.window.sidebar.isAncestorOf(self.window.engine_line))
        self.assertEqual(self.window.sidebar.layout().indexOf(panel), -1)
        self.window.open_engine_analysis()
        self.assertIs(self.window.engine_panel, panel)
        self.assertIn('+0.34   Depth 18   1. e4 e5 2. Nf3', self.window.engine_line.toPlainText())
        self.game.analysis_enabled = True
        panel.close()
        self.assertTrue(self.game.analysis_enabled)
        self.assertFalse(panel.isVisible())
        self.assertIsNotNone(settings.load_config()['engine_analysis_geometry'])

    def test_preview_never_changes_live_board_pgn_clocks_or_saved_position(self):
        g = self.game
        g.game_started = True
        g.white_time, g.black_time = 272, 231
        g.clock_paused = False
        g.active_clock_color = chess.WHITE
        panel = self.present()
        before, board = self.state(), g.board
        panel.select_line(0)
        self.assertTrue(g.clock_paused)
        self.assertFalse(g.human_can_move())
        for mode in ('2D', '3D'):
            self.window.set_mode(mode)
            panel.step(1)
            self.assertIs(g.board, board)
            self.assertIs(g.display_board, g.preview_board)
            self.assertNotEqual(g.display_board.fen(), board.fen())
            self.widget.grabFramebuffer()
            self.assertEqual(self.state(), before)
        self.assertFalse(g.try_move(chess.E2, chess.E4))
        self.assertFalse(g.try_move(chess.E2, chess.E4, is_engine=True))
        g.last_clock_tick = time.perf_counter() - 1000
        g.update_clock()
        g.hit_clock()
        g.stop_clock()
        self.assertEqual(self.state(), before)
        self.window.session.save(g, force=True)
        saved = json.loads(self.window.session.path.read_text())
        self.assertEqual(saved['pgn'], before[1])
        self.assertEqual(saved['state']['white_time'], 272)
        self.assertEqual(saved['state']['black_time'], 231)
        self.assertIn('Variation Preview', self.window.preview_status.text())
        panel.return_to_current()
        self.assertIs(g.board, board)
        self.assertIs(g.display_board, board)
        self.assertEqual(self.state(), before)
        self.assertFalse(g.clock_paused)
        self.assertLess(time.perf_counter()-g.last_clock_tick, .5)

    def test_paused_and_otb_clocks_and_side_are_restored_exactly(self):
        g = self.game
        g.board.push_uci('e2e4')
        g.clock_mode = 'OTB'
        g.game_started = True
        g.white_time, g.black_time = 120, 99
        g.active_clock_color = chess.WHITE
        g.awaiting_clock_press, g.awaiting_clock_color = True, chess.WHITE
        for paused in (False, True):
            g.clock_paused = paused
            panel = self.present(self.line(('e7e5', 'g1f3')))
            before = self.state()
            panel.select_line(0)
            panel.step(2)
            panel.close()
            self.assertEqual(self.state(), before)
            self.assertEqual(g.clock_paused, paused)
            self.assertEqual(g.board.turn, chess.BLACK)

    def test_pending_engine_move_waits_until_return(self):
        g = self.game
        g.start_game()
        panel = self.present()
        g.pending_engine_move = self.line().pv[0]
        g.pending_engine_position = g.board.fen()
        g.pending_engine_generation = g.engine_manager.search_generation
        panel.select_line(0)
        g.apply_pending_engine_move()
        self.assertEqual(len(g.board.move_stack), 0)
        self.assertIsNotNone(g.pending_engine_move)
        panel.return_to_current()
        g.apply_pending_engine_move()
        self.assertEqual(g.board.peek().uci(), 'e2e4')

    def test_load_same_fen_cancels_preview_and_rejects_old_line(self):
        panel = self.present()
        panel.select_line(0)
        panel.step(2)
        self.game.load_document(chess.Board())
        self.game.white_time = 50
        self.game.black_time = 75
        self.assertIsNone(self.game.variation_preview)
        panel.select_line(0)
        self.assertIsNone(self.game.variation_preview)
        panel.refresh_preview()
        self.assertEqual(panel.lines, [])
        self.assertEqual(panel.line_view.toPlainText(), '')
        panel.return_to_current()
        self.assertEqual((self.game.white_time, self.game.black_time), (50, 75))
        self.assertEqual(self.game.board.fen(), chess.STARTING_FEN)

    def test_external_live_mutation_and_termination_cannot_be_overwritten(self):
        g = self.game
        panel = self.present()
        panel.select_line(0)
        g.board.push_uci('d2d4')
        g.white_time = 30
        panel.step(1)
        self.assertIsNone(g.variation_preview)
        self.assertEqual(g.board.peek().uci(), 'd2d4')
        self.assertEqual(g.white_time, 30)
        panel = self.present(self.line(('d7d5',)))
        panel.select_line(0)
        g.game_over, g.game_started = True, False
        g.result_text = 'White resigned'
        panel.refresh_preview()
        self.assertIsNone(g.variation_preview)
        self.assertTrue(g.game_over)
        self.assertEqual(g.result_text, 'White resigned')

    def test_live_analysis_refresh_does_not_replace_selected_preview(self):
        panel = self.present()
        panel.select_line(0)
        panel.step(1)
        preview = self.game.preview_board.fen()
        self.present(self.line(('d2d4', 'd7d5'), -125))
        self.assertIn('-1.25', panel.line_view.toPlainText())
        self.assertEqual(self.game.preview_board.fen(), preview)
        panel.select_line(0)
        panel.step(1)
        self.assertEqual(self.game.preview_board.peek().uci(), 'd2d4')

    def test_stale_background_result_is_discarded_even_after_identical_fen_load(self):
        g = self.game
        entered, release = threading.Event(), threading.Event()
        result = self.line()
        def analyse(_, **options):
            entered.set()
            release.wait(5)
            return result
        g.analysis_engine = Mock(analyse_variations=analyse)
        g.analysis_enabled = True
        g.request_analysis()
        try:
            self.assertTrue(entered.wait(2))
            g.load_document(chess.Board())
        finally:
            release.set()
        deadline = time.monotonic()+3
        while g.analysis_busy and time.monotonic()<deadline:
            QTest.qWait(10)
        self.assertFalse(g.analysis_busy)
        self.assertIsNone(g.engine_output)

    def test_full_pv_black_numbering_and_candidate_selection(self):
        g = self.game
        g.load_document(chess.Board('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 17'))
        first, second = self.line(('e7e5', 'g1f3')), self.line(('c7c5', 'g1f3'), -25)
        panel = self.present(first)
        panel.present(g.board.fen(), (first, second), g.analysis_position_token())
        self.assertIn('17... e5 18. Nf3', panel.line_view.toPlainText())
        self.assertEqual(len(panel.lines), 2)
        panel.select_line(1)
        panel.step(1)
        self.assertEqual(g.preview_board.peek().uci(), 'c7c5')
        self.assertIn('Variation 2', g.preview_description)

    def test_keyboard_navigation_and_escape_on_main_board(self):
        panel = self.present()
        panel.select_line(0)
        self.window.activateWindow()
        self.widget.setFocus()
        self.qt.processEvents()
        QTest.keyClick(self.widget, Qt.Key.Key_Right)
        self.assertEqual(self.game.variation_preview['index'], 1)
        QTest.keyClick(self.widget, Qt.Key.Key_Left)
        self.assertEqual(self.game.variation_preview['index'], 0)
        QTest.keyClick(self.widget, Qt.Key.Key_Escape)
        self.assertIsNone(self.game.variation_preview)

    def test_invalid_pv_truncates_and_special_moves_use_legal_copies(self):
        for fen, uci in (('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 'e1g1'),
                         ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6'),
                         ('7k/P7/8/8/8/8/8/7K w - - 0 1', 'a7a8n')):
            self.game.load_document(chess.Board(fen))
            panel = self.present(self.line((uci, 'a1a8')))
            panel.select_line(0)
            panel.step(1)
            expected = chess.Board(fen)
            expected.push_uci(uci)
            self.assertEqual(self.game.preview_board.fen(), expected.fen())
            self.assertEqual(self.game.board.fen(), chess.Board(fen).fen())
            self.assertEqual(len(panel.lines[0][1]), 1)
            panel.return_to_current()

    def test_click_exact_move_and_highlight_navigation(self):
        panel = self.present()
        self.game.analysis_engine = Mock()
        self.window.toggle_analysis(True)
        start, end = panel.line_view.move_spans[0][2]
        cursor = panel.line_view.textCursor()
        cursor.setPosition(start + 1)
        point = panel.line_view.cursorRect(cursor).center()
        QTest.mouseClick(panel.line_view.viewport(), Qt.MouseButton.LeftButton, pos=point)
        self.assertFalse(self.game.analysis_enabled)
        self.game.analysis_engine.stop_search.assert_called_once()
        self.assertFalse(self.window.analysis_action.isChecked())
        self.assertEqual(self.window.analysis_button.text(), 'Start analysis')
        self.assertEqual(self.game.variation_preview['index'], 3)
        self.assertEqual(self.game.preview_board.peek().uci(), 'g1f3')
        selections = panel.line_view.extraSelections()
        self.assertEqual(selections[0].cursor.selectedText(), 'Nf3')
        panel.step(-1)
        selections = panel.line_view.extraSelections()
        self.assertEqual(selections[0].cursor.selectedText(), 'e5')
        panel.return_to_current()
        self.assertEqual(panel.line_view.extraSelections(), [])

    def test_analysis_independent_of_play_engine_and_options_persist(self):
        g = self.game
        panel = self.window.engine_panel
        panel.options['multipv'].setValue(2)
        panel.options['depth'].setValue(12)
        self.assertEqual(settings.load_config()['analysis_options']['multipv'], 2)
        g.engine_manager.engine = Mock()
        g.engine_manager.thinking = True
        g.engine_enabled = False
        g.analysis_engine = Mock()
        g.analysis_engine.analyse_variations.return_value = (self.line(), self.line(('d2d4',)))
        g.analysis_enabled = True
        g.request_analysis()
        deadline = time.monotonic() + 3
        while g.analysis_busy and time.monotonic() < deadline:
            QTest.qWait(10)
        g.analysis_engine.analyse_variations.assert_called_once()
        self.assertEqual(g.analysis_engine.analyse_variations.call_args.kwargs['depth'], 12)
        g.engine_manager.engine.analyse.assert_not_called()
        self.window.tick()
        self.assertEqual(len(panel.lines), 2)

    def test_material_panel_follows_variation_and_return(self):
        panel = self.present(self.line(('e2e4', 'd7d5', 'e4d5')))
        panel.select_move(0, 3)
        self.window.tick()
        self.assertIn('\u265f', self.window.captured_white.text())
        self.assertEqual('', self.window.captured_black.text())
        self.assertEqual(self.window.material_balance.text(), '+1')
        panel.return_to_current()
        self.window.tick()
        self.assertEqual(self.window.material_balance.text(), '0')
        self.assertEqual(self.window.captured_white.text(), '')
