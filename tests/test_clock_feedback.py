"""Native clock actions, promotion symbols, and check feedback."""
import time
import unittest
from unittest.mock import Mock, patch

import chess
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton, QMessageBox
from OpenGL.GL import glGetError, GL_NO_ERROR

from tests import test_desktop_ui as fixture
from otb_chess.graphics import rendering
from otb_chess.ui import chess_symbols


class ClockFeedbackTests(unittest.TestCase):
    setUpClass = classmethod(fixture.DesktopTests.setUpClass.__func__)
    def setUp(self):
        fixture.DesktopTests.setUp(self)
        self.game.sound_enabled = False
    tearDown = fixture.DesktopTests.tearDown

    def test_engine_labels_use_loaded_maia_profile_and_selected_side(self):
        g = self.game
        g.engine_manager.engine = Mock()
        g.engine_manager.loaded_configuration = {"engine_id": "stockfish", "name": "Stockfish"}
        g.cfg["engine_elo"] = 1900
        g.engine_side_var.set("White")
        self.window.white_clock.refresh(g)
        self.window.black_clock.refresh(g)
        self.assertEqual(self.window.white_clock.engine_label.toolTip(), "Stockfish * 1900")
        self.assertEqual(self.window.black_clock.engine_label.toolTip(), "")
        g.engine_manager.loaded_configuration = {"engine_id": "maia", "profile": "beginner", "settings": {"model": 1100}}
        g.cfg["engine_rating"] = 1900  # Unloaded selection must not relabel the loaded Maia.
        g.engine_side_var.set("Black")
        self.window.black_clock.refresh(g)
        self.assertEqual(self.window.black_clock.engine_label.toolTip(), "Maia * 300")

    def test_shared_actions_are_borderless_and_resign_the_human_side(self):
        g = self.game
        g.start_game()
        g.engine_manager.engine = Mock()
        g.engine_side = chess.BLACK
        g.board.push_uci("e2e4")
        self.window.refresh_game_actions()
        with patch.object(QMessageBox, "question", side_effect=AssertionError("No confirmation")), \
                patch.object(self.window, "edit_clock", side_effect=AssertionError("Action must not click the clock")):
            QTest.mouseClick(self.window.clock_actions["draw"], Qt.MouseButton.LeftButton)
            self.assertEqual(g.result_text, "Draw offered")
            QTest.mouseClick(self.window.clock_actions["takeback"], Qt.MouseButton.LeftButton)
            self.assertFalse(g.board.move_stack)
            g.board.push_uci("e2e4")  # Black's turn, but White's flag resigns White.
            QTest.mouseClick(self.window.clock_actions["resign"], Qt.MouseButton.LeftButton)
            self.assertEqual(g.result_text, "White resigned")
            self.assertTrue(g.game_over)
        self.assertEqual(len(self.window.clock_actions), 4)
        for button in self.window.clock_actions.values():
            self.assertIs(button.parentWidget(), self.window.game_actions_row)
            self.assertEqual(button.objectName(), "humanGameAction")
        layout = self.window.sidebar.layout()
        self.assertEqual(layout.indexOf(self.window.game_actions_row) + 1, layout.indexOf(self.window.clock_summary))

    def test_timeout_flag_is_transparent_and_blue_on_black(self):
        from PySide6.QtGui import QColor
        for background, expected in (("#252e3a", "#000000"), ("#000000", "#409cff")):
            image = chess_symbols.flag_icon(QColor(background)).pixmap(64, 64).toImage()
            self.assertEqual(image.pixelColor(5, 5).alpha(), 0)
            self.assertEqual(image.pixelColor(30, 20).name(), expected)
        self.window.setStyleSheet(self.window.styleSheet() + '\nQPushButton#clock { background: #000000; }')
        self.qt.processEvents()
        self.window.black_clock.refresh(self.game)
        image = self.window.black_clock.fallen_flag.pixmap().toImage()
        color = image.pixelColor(13, 9)
        self.assertGreater(color.blue(), color.red())

    def test_switch_sides_pauses_and_discards_old_search(self):
        g = self.game
        g.start_game()
        g.engine_manager.engine = Mock()
        g.engine_side = chess.BLACK
        g.board.push_uci("e2e4")
        fen = g.board.fen()
        generation = g.engine_manager.search_generation
        g.engine_manager.thinking = True
        self.window.refresh_game_actions()
        self.window.clock_actions["switch_sides"].click()
        self.assertEqual(g.engine_side, chess.WHITE)
        self.assertEqual(g.engine_side_var.get(), "White")
        self.assertTrue(g.clock_paused)
        g.engine_manager.engine.stop_search.assert_called_once()
        self.assertGreater(g.engine_manager.search_generation, generation)
        g.pending_engine_generation = generation
        g.pending_engine_position = fen
        g.pending_engine_move = chess.Move.from_uci("e7e5")
        g.clock_paused = False
        g.apply_pending_engine_move()
        self.assertEqual(g.board.fen(), fen)
        self.window.switch_sides_action.trigger()
        self.assertEqual(g.engine_side, chess.BLACK)
        self.assertTrue(g.clock_paused)
        g.engine_manager.thinking = False

    def test_black_human_resigns_black_even_on_whites_turn(self):
        g = self.game
        g.start_game()
        g.engine_manager.engine = Mock()
        g.engine_side = chess.WHITE
        self.window.human_game_action("resign")
        self.assertEqual(g.result_text, "Black resigned")

    def test_takeback_always_removes_one_ply_and_ignores_active_search(self):
        g = self.game
        g.start_game()
        g.engine_side = chess.BLACK
        for move in ("e2e4", "e7e5", "g1f3", "b8c6"):
            g.board.push_uci(move)
        g.engine_manager.thinking = True
        with patch.object(g.engine_manager, "stop_search") as stop:
            self.window.refresh_game_actions()
            self.assertTrue(self.window.clock_actions["takeback"].isEnabled())
            for expected in (3, 2, 1, 0):
                QTest.mouseClick(self.window.clock_actions["takeback"], Qt.MouseButton.LeftButton)
                self.assertEqual(len(g.board.move_stack), expected)
                self.assertTrue(g.clock_paused)
            self.assertTrue(stop.called)
        self.assertFalse(self.window.clock_actions["takeback"].isEnabled())
        g.pending_engine_move = chess.Move.from_uci("e2e4")
        g.pending_engine_position = g.board.fen()
        g.pending_engine_generation = 0
        g.clock_paused = False
        g.apply_pending_engine_move()
        self.assertFalse(g.board.move_stack)
        g.engine_manager.thinking = False

    def test_flag_fall_shows_only_on_expired_clock_and_clears_on_new_game(self):
        g = self.game
        for color, card, other in ((True, self.window.white_clock, self.window.black_clock),
                                    (False, self.window.black_clock, self.window.white_clock)):
            g.start_game()
            g.board.push_uci("e2e4")
            g.active_clock_color = color
            g.white_time = .01 if color else 60
            g.black_time = 60 if color else .01
            g.last_clock_tick = time.perf_counter() - 1
            g.update_clock()
            card.refresh(g)
            other.refresh(g)
            self.assertFalse(card.fallen_flag.isHidden())
            self.assertTrue(other.fallen_flag.isHidden())
            self.assertNotIn("flagged", g.result_text.lower())
            g.start_game()
            card.refresh(g)
            self.assertTrue(card.fallen_flag.isHidden())

    def test_promotion_icons_use_textbook_in_3d_and_selected_2d_set(self):
        g = self.game
        for mode, selected, expected in (("3D", "fantasy", "textbook"), ("2D", "chessnut", "chessnut")):
            g.board_mode, g.flat_piece_set = mode, selected
            captured = []
            def inspect():
                dialog = self.qt.activeModalWidget()
                for label in ("Queen", "Rook", "Bishop", "Knight"):
                    button = dialog.findChild(QPushButton, "promote" + label)
                    captured.append((button.text(), button.icon().isNull(), button.accessibleName()))
                dialog.reject()
            with patch.object(chess_symbols, "flat_piece_image", wraps=chess_symbols.flat_piece_image) as images:
                QTimer.singleShot(0, inspect)
                self.assertIsNone(g.choose_promotion(True, chess.A8))
                self.assertEqual([call.args[0] for call in images.call_args_list], [expected] * 4)
            self.assertEqual(len(captured), 4)
            self.assertTrue(all(text == "" and not empty and accessible for text, empty, accessible in captured))

    def test_red_halo_for_check_and_mate_in_both_modes_not_stalemate(self):
        g = self.game
        for mode in ("2D", "3D"):
            g.board_mode = mode
            for fen, expected in (("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1", True),
                                  ("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", True),
                                  ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", False)):
                g.board = chess.Board(fen)
                g.show_move_indicator = False
                with patch.object(rendering, "draw_check_halo", wraps=rendering.draw_check_halo) as halo:
                    self.widget.grabFramebuffer()
                    self.assertEqual(glGetError(), GL_NO_ERROR)
                    self.assertEqual(halo.called, expected)
                    if expected:
                        square = g.board.king(g.board.turn)
                        self.assertEqual(halo.call_args.args, (3.5-chess.square_file(square), chess.square_rank(square)-3.5))


if __name__ == "__main__":
    unittest.main()
