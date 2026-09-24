"""Integration tests for the Qt window, using an invisible native GL surface."""

import tempfile
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import chess
import chess.engine
from PySide6.QtCore import Qt, QPoint, QPointF, QTimer
from PySide6.QtGui import QWheelEvent, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QComboBox, QDoubleSpinBox, QColorDialog, QSpinBox, QPushButton, QDialogButtonBox

from otb_chess.core import game
from otb_chess.services import settings
from otb_chess.chess_backend import uci
from otb_chess.engine_state import EngineEvaluation, EngineScore
from otb_chess_core import Move as OwnedMove
import time
import tkinter as tk
from tkinter import messagebox
from OpenGL.GL import glFinish, glGetError, GL_NO_ERROR
from OpenGL.GLU import gluProject
from otb_chess.ui.desktop_ui import MainWindow, configure_graphics


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_graphics()
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = patch.object(settings,"CONFIG_PATH",Path(self.folder.name)/"config.json")
        self.config.start()
        self.addCleanup(self.config.stop)
        for name in ("ENGINE_DIR", "BOOK_DIR"):
            folder_patch = patch.object(settings, name, Path(self.folder.name))
            folder_patch.start()
            self.addCleanup(folder_patch.stop)
        self.window = MainWindow()
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,True)
        self.window.show()
        for _ in range(4):
            self.qt.processEvents()
        self.window.timer.stop()
        self.game = self.window.game
        self.widget = self.window.board_widget
        self.assertTrue(self.widget.isValid())
        self.widget.makeCurrent()

    def tearDown(self):
        self.window.close()
        self.qt.processEvents()

    def screen(self,square):
        self.widget.makeCurrent()
        self.game.camera()
        px,pz = self.game.view_pan()
        x,y,_ = gluProject(3.5-chess.square_file(square)+px,0,chess.square_rank(square)-3.5+pz)
        ratio = self.widget.devicePixelRatioF()
        return QPoint(round(x/ratio),round((self.game.height-y)/ratio))

    def test_board_types_render_and_preserve_game_and_colours(self):
        w,g = self.window,self.game
        from otb_chess.graphics.board_types import BOARD_TYPES
        original = (g.board.fen(),g.light_square,g.dark_square,g.frame_color)
        for mode in ('3D','2D'):
            w.mode_actions[mode].trigger()
            for key in BOARD_TYPES:
                w.board_type_actions[key].trigger()
                self.widget.grabFramebuffer()
                self.assertEqual(glGetError(),GL_NO_ERROR)
                self.assertEqual(g.board_type,key)
                self.assertEqual(settings.load_config()['board_type'],key)
                self.assertEqual((g.board.fen(),g.light_square,g.dark_square,g.frame_color),original)
        self.assertEqual(len(g.board_surface_renderer.textures),3)
        self.assertFalse(g.board_surface_renderer.failed)

    def test_engine_off_cancels_pending_moves_and_allows_legal_free_play(self):
        g, w = self.game, self.window
        g.start_game()
        g.engine_manager.engine = Mock()
        g.engine_side = chess.BLACK
        g.clock_mode = 'OTB'
        g.awaiting_clock_press = True
        before = (g.board.fen(), tuple(g.board.move_stack), g.white_time, g.black_time)
        with patch.object(g.engine_manager, 'request_move') as request, patch.object(g, 'pick_book_move') as book:
            QTest.mouseClick(w.engine_enabled_button, Qt.MouseButton.LeftButton)
            self.assertFalse(g.engine_enabled)
            self.assertEqual((g.board.fen(), tuple(g.board.move_stack), g.white_time, g.black_time), before)
            g.engine_manager.engine.stop_search.assert_called_once()
            g.pending_engine_move = OwnedMove(chess.E2, chess.E4)
            g.pending_engine_position = g.board.fen()
            g.apply_pending_engine_move()
            self.assertEqual(g.board.fen(), before[0])
            self.assertFalse(g.try_move(chess.E2, chess.E5))
            self.assertTrue(g.try_move(chess.E2, chess.E4))
            self.assertTrue(g.try_move(chess.E7, chess.E5))
            self.assertFalse(g.awaiting_clock_press)
            g.maybe_request_engine_move()
            g.request_analysis()
            request.assert_not_called()
            book.assert_not_called()
            self.assertFalse(g.try_move(chess.G1, chess.F3, is_engine=True))
            position = (g.board.fen(), tuple(g.board.move_stack))
            g.set_engine_enabled(True)
            self.assertEqual((g.board.fen(), tuple(g.board.move_stack)), position)
            g.game_over = True
            g.result_text = 'Checkmate'
            g.set_engine_enabled(False)
            self.assertTrue(g.game_over)
            self.assertEqual(g.result_text, 'Checkmate')

    def test_free_play_before_start_and_engine_reenable_during_game(self):
        g = self.game
        g.set_engine_enabled(False)
        self.assertTrue(g.try_move(chess.E2, chess.E4))
        self.assertTrue(g.try_move(chess.E7, chess.E5))
        g.game_started = True
        g.engine_manager.engine = Mock()
        g.engine_side = g.board.turn
        g.engine_manager.thinking = True
        before = (g.board.fen(), tuple(g.board.move_stack))
        with patch.object(g.engine_manager, 'request_move') as request, patch.object(g, 'pick_book_move', return_value=None):
            g.set_engine_enabled(True)
            request.reset_mock()
            g.engine_manager.thinking = False
            self.window.tick()
            request.assert_called_once()
        self.assertEqual((g.board.fen(), tuple(g.board.move_stack)), before)

    def test_engine_disabled_setting_survives_reopen(self):
        self.game.set_engine_enabled(False)
        self.window.close()
        self.window = MainWindow()
        self.window.timer.stop()
        self.assertFalse(self.window.game.engine_enabled)
        self.assertFalse(self.window.engine_enabled_button.isChecked())
        with patch.object(self.window.game.engine_manager, 'request_move') as request:
            self.window.game.start_game()
            self.window.game.maybe_request_engine_move()
            request.assert_not_called()

    def test_flip_persists_in_both_modes_and_setup_shortcut_preserves_position(self):
        for mode in ('2D', '3D'):
            g = self.window.game
            self.window.set_mode(mode)
            g.set_board_facing('white')
            g.flip_board()
            expected_yaw = g.yaw
            self.window.close()
            self.window = MainWindow()
            self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            self.window.show()
            self.qt.processEvents()
            self.window.timer.stop()
            g = self.window.game
            self.assertEqual(g.board_facing, 'black')
            self.assertEqual(g.yaw, expected_yaw)
            before = g.board.fen(en_passant='fen')
            observed = []
            def inspect():
                dialog = self.qt.activeModalWidget()
                observed.append(dialog.flipped)
                original = dialog.board.fen(en_passant='fen')
                dialog.activateWindow()
                dialog.fen.setFocus()
                self.qt.processEvents()
                QTest.keyClick(dialog.fen, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
                observed.append(dialog.flipped)
                observed.append(dialog.board.fen(en_passant='fen') == original)
                observed.append(dialog.board_grid.itemAtPosition(7, 0).widget() is dialog.squares[chess.A1])
                QTest.mouseClick(dialog.flip_button, Qt.MouseButton.LeftButton)
                observed.append(dialog.flipped)
                dialog.reject()
            QTimer.singleShot(0, inspect)
            self.window.setup_position()
            self.assertEqual(observed, [True, False, True, True, True])
            self.assertEqual(g.board.fen(en_passant='fen'), before)
            self.assertEqual(g.board_facing, 'black')

    def test_white_clock_stays_above_black_after_flips(self):
        for mode in ('2D', '3D'):
            self.window.set_mode(mode)
            for _ in range(2):
                self.game.flip_board()
                self.qt.processEvents()
                self.assertLess(self.window.white_clock.y(), self.window.black_clock.y())

    def test_open_source_licences_dialog_and_notice_files(self):
        from otb_chess.services.settings import APP_DIR
        from PySide6.QtWidgets import QPlainTextEdit
        import json
        help_menu = next(a.menu() for a in self.window.menuBar().actions() if a.text() == 'Help')
        action = next(a for a in help_menu.actions() if a.text() == 'Open Source Licences')
        seen = []
        def inspect_dialog():
            dialog = QApplication.activeModalWidget()
            try:
                seen.append((dialog.objectName(),dialog.findChild(QPlainTextEdit).toPlainText()))
            finally:
                dialog.reject()
        QTimer.singleShot(0,inspect_dialog)
        action.trigger()
        self.assertEqual(seen[0][0],'openSourceLicencesDialog')
        self.assertIn('PySide6',seen[0][1])
        self.assertIn('chess',seen[0][1])
        for name in ('THIRD_PARTY_NOTICES.md','licenses/README.md','third_party_bom.json'):
            self.assertTrue((APP_DIR/name).is_file())
        inventory = json.loads((APP_DIR/'third_party_bom.json').read_text(encoding='utf-8'))
        for component in inventory['components']:
            for evidence in component.get('license_files',[]):
                self.assertTrue((APP_DIR/evidence['path']).is_file())

    def test_background_presets_render_persist_and_replace_images(self):
        w,g = self.window,self.game
        self.assertEqual(len(w.background_actions),8)
        original = g.board.fen()
        for mode in ('2D','3D'):
            g.board_mode = mode
            for key,action in w.background_actions.items():
                action.trigger()
                self.widget.grabFramebuffer()
                self.assertEqual(glGetError(),GL_NO_ERROR)
                self.assertEqual(settings.load_config()['background_style'],key)
                self.assertEqual(g.board.fen(),original)
                self.assertTrue(action.isChecked())
                if key != 'solid':
                    self.assertIsNotNone(g.background_texture)
        old_key = g.background_preset_key
        g.dark_square = (.1,.2,.3)
        self.widget.grabFramebuffer()
        self.assertNotEqual(g.background_preset_key,old_key)
        from PIL import Image
        path = Path(self.folder.name)/'background.png'
        Image.new('RGB',(16,16),'blue').save(path)
        self.assertTrue(g.load_background_image(path,show_error=False))
        w.refresh_background_actions()
        self.assertFalse(any(a.isChecked() for a in w.background_actions.values()))
        w.background_actions['studio'].trigger()
        self.widget.grabFramebuffer()
        self.assertEqual(g.background_image_path,'')
        self.assertEqual(g.background_preset_key,('studio',()))
        w.background_actions['solid'].trigger()
        self.widget.grabFramebuffer()
        self.assertIsNone(g.background_texture)

    def test_additional_piece_sets_render_and_remember_independent_choices(self):
        from otb_chess.graphics.board_2d import FLAT_SETS, flat_piece_image
        w,g = self.window,self.game
        original = g.board.fen()
        w.set_actions['external:scifi'].trigger()
        g.board_mode = '3D'
        self.widget.grabFramebuffer()
        self.assertEqual(glGetError(),GL_NO_ERROR)
        self.assertEqual(settings.load_config()['piece_set'],'external:scifi')
        g.board_mode = '2D'
        signatures = set()
        for key in FLAT_SETS:
            w.flat_set_actions[key].trigger()
            for colour in (True,False):
                for piece in range(1,7):
                    image = flat_piece_image(key,piece,(.8,.8,.8),colour)
                    self.assertEqual(image.size,(256,256))
                    self.assertIsNotNone(image.getbbox())
                    self.assertEqual(image.getpixel((0,0))[3],0)
            signatures.add(flat_piece_image(key,2,(.8,.8,.8),True).tobytes())
            self.widget.grabFramebuffer()
            self.assertEqual(glGetError(),GL_NO_ERROR)
            self.assertEqual(settings.load_config()['flat_piece_set'],key)
            self.assertEqual(g.piece_set,'external:scifi')
            self.assertEqual(g.board.fen(),original)
        self.assertEqual(len(signatures),len(FLAT_SETS))
        self.window.close()
        self.qt.processEvents()
        self.window = MainWindow()
        self.assertEqual(self.window.game.flat_piece_set,'eyes')
        self.assertEqual(self.window.game.piece_set,'external:scifi')

    def test_right_click_cancels_selection_and_active_piece_drag(self):
        g,b = self.game,self.widget
        for mode in ('2D','3D'):
            g.board_mode = mode
            g.start_game()
            original = g.board.fen()
            QTest.mouseClick(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E2))
            self.assertEqual(g.selected,chess.E2)
            QTest.mouseClick(b,Qt.MouseButton.RightButton,pos=self.screen(chess.E4))
            self.assertIsNone(g.selected)
            self.assertFalse(g.legal_targets())
            QTest.mousePress(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E2))
            g.was_drag = True
            g.clock_mode,g.clock_binding = 'OTB','Right Mouse'
            with patch.object(g,'hit_clock') as clock:
                QTest.mouseClick(b,Qt.MouseButton.RightButton,pos=self.screen(chess.E4))
                clock.assert_not_called()
            QTest.mouseRelease(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E4))
            self.assertIsNone(g.selected)
            self.assertIsNone(g.drag_piece)
            self.assertEqual(g.board.fen(),original)

    def test_move_animation_slider_and_castling(self):
        from PySide6.QtWidgets import QSlider
        w,g = self.window,self.game
        self.assertEqual(g.move_animation_ms,0)
        def set_speed():
            dialog = QApplication.activeModalWidget()
            dialog.findChild(QSlider).setValue(1000)
            dialog.accept()
        QTimer.singleShot(0,set_speed)
        w.movement_settings()
        self.assertEqual(settings.load_config()['move_animation_ms'],1000)
        for mode in ('2D','3D'):
            g.board_mode = mode
            g.load_document(chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1'))
            with patch('otb_chess.core.game.time.perf_counter',return_value=10):
                self.assertTrue(g.try_move(chess.E1,chess.G1))
            with patch('otb_chess.graphics.rendering.time.perf_counter',return_value=10):
                self.assertEqual(g.animated_piece_positions()[chess.G1],(-.5,-3.5))
                self.assertEqual(g.animated_piece_positions()[chess.F1],(-3.5,-3.5))
            with patch('otb_chess.graphics.rendering.time.perf_counter',return_value=10.5):
                self.assertEqual(g.animated_piece_positions()[chess.G1],(-1.5,-3.5))
                self.widget.grabFramebuffer()
                self.assertEqual(glGetError(),GL_NO_ERROR)
            with patch('otb_chess.graphics.rendering.time.perf_counter',return_value=11):
                self.assertEqual(g.animated_piece_positions(),{})
        g.load_document(chess.Board())
        g.move_animation_ms = 0
        self.assertTrue(g.try_move(chess.E2,chess.E4))
        self.assertIsNone(g.move_animation)

    def test_session_restores_history_review_clocks_and_backup(self):
        from otb_chess.services.session import SessionStore
        g = self.game
        g.load_document(chess.Board())
        g.game_started = True
        g.clock_mode = 'OTB'
        g.clock_binding = 'Right Mouse'
        g.clock_paused = False
        self.assertTrue(g.try_move(chess.E2,chess.E4))
        g.white_time,g.black_time = 42.5,51.25
        g.clock_paused = True
        g.navigate_to_ply(0)
        store = self.window.session
        store.save(g,force=True)
        restored = SessionStore()
        g.load_document(chess.Board())
        self.assertTrue(restored.restore(g))
        self.assertEqual(len(g.board.move_stack),0)
        self.assertEqual(len(g.history_board().move_stack),1)
        self.assertEqual((g.white_time,g.black_time),(42.5,51.25))
        self.assertTrue(g.game_started)
        self.assertTrue(g.clock_paused)
        self.assertTrue(g.awaiting_clock_press)
        self.assertEqual(g.clock_binding_var.get(),'Right Mouse')
        g.return_to_live()
        restored.save(g,force=True)
        restored.path.write_text('{broken',encoding='utf-8')
        self.assertTrue(SessionStore().restore(g))
        self.assertIn('backup',g.result_text)
        restored.backup.write_text('{}',encoding='utf-8')
        self.assertFalse(SessionStore().restore(g))
        self.assertIn('could not be recovered',g.result_text)

    def test_interface_themes_apply_and_persist(self):
        w,g = self.window,self.game
        original = (g.board.fen(),g.light_square,g.dark_square,g.background_color)
        styles = set()
        for name,action in w.interface_theme_actions.items():
            action.trigger()
            self.qt.processEvents()
            styles.add(w.styleSheet())
            self.assertEqual(w.interface_theme,name)
            self.assertEqual(settings.load_config()["interface_theme"],name)
            self.assertEqual(sum(a.isChecked() for a in w.interface_theme_actions.values()),1)
            self.assertEqual((g.board.fen(),g.light_square,g.dark_square,g.background_color),original)
        self.assertEqual(len(styles),12)
        restored = MainWindow()
        try:
            self.assertEqual(restored.interface_theme,"Pink/Lollipop")
            self.assertEqual(restored.styleSheet(),w.styleSheet())
        finally:
            restored.close()

    def test_single_window_layout_and_menus(self):
        self.assertIsNone(self.game.window)  # No second GLFW window.
        self.assertGreater(self.widget.width(),self.window.sidebar.width()*2)
        self.assertEqual([a.text() for a in self.window.menuBar().actions()],
                         ["Game","File","View","Engine","Settings","Bookmarks","Help"])
        self.assertTrue(self.window.white_clock.isVisible())
        self.assertTrue(self.window.moves.isVisible())
        self.assertFalse(self.window.engine_panel.isVisible())
        self.window.focus_action.trigger()
        self.assertFalse(self.window.moves_panel.isVisible())
        self.assertTrue(self.window.white_clock.isVisible())
        self.window.focus_action.trigger()
        self.assertTrue(self.window.moves_panel.isVisible())
        self.window.sidebar_action.trigger()
        self.qt.processEvents()
        self.assertFalse(self.window.sidebar.isVisible())
        self.window.sidebar_action.trigger()
        self.window.resize(800,600)
        self.qt.processEvents()
        self.assertTrue(self.window.moves.isVisible())
        self.assertGreater(self.widget.width(),300)

    def test_sound_profiles_switch_all_events_and_restore_muted_choice(self):
        from otb_chess.services.audio import SOUND_PROFILES, ensure_sounds
        import wave
        w,g = self.window,self.game
        self.assertEqual(len(w.sound_profile_actions),9)
        for profile in SOUND_PROFILES:
            w.sound_profile_actions[profile].trigger()
            self.assertTrue(g.sound_enabled)
            self.assertEqual(g.sound_profile,profile)
            self.assertEqual(sum(a.isChecked() for a in w.sound_profile_actions.values()),1)
            for event,path in ensure_sounds(profile).items():
                self.assertEqual(getattr(g,'sound_'+event),path)
                with wave.open(str(path)) as wav:
                    self.assertGreater(wav.getnframes(),0)
            self.assertEqual(settings.load_config()['sound_profile'],profile)
        for muted in (False,True):
            if muted:
                w.sound_profile_actions[None].trigger()
            restored = MainWindow()
            restored.timer.stop()
            try:
                self.assertEqual(restored.game.sound_profile,g.sound_profile)
                self.assertEqual(restored.game.sound_enabled,not muted)
                self.assertTrue(restored.sound_profile_actions[None if muted else g.sound_profile].isChecked())
                self.assertEqual(restored.game.sound_move,g.sound_move)
                if muted:
                    with patch('otb_chess.core.game.play_sound') as sound:
                        for event,path in ensure_sounds(g.sound_profile).items():
                            restored.game.play_game_sound(path)
                        sound.assert_not_called()
            finally:
                restored.close()
        w.sound_profile_actions['03_Tournament_Wood'].trigger()
        self.assertTrue(g.sound_enabled)
        self.assertFalse(w.sound_profile_actions[None].isChecked())

    def test_sound_pack_event_mapping_and_mute(self):
        g = self.game
        cases = (
            (chess.STARTING_FEN,'e2e4','move'),
            ('4k3/8/8/8/3p4/4P3/8/4K3 w - - 0 1','e3d4','capture'),
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','e1g1','castle'),
            ('4k3/8/8/8/8/8/R7/4K3 w - - 0 1','a2e2','check'),
            ('7k/P7/8/8/8/8/8/4K3 w - - 0 1','a7a8q','promote'),
            (chess.STARTING_FEN,'e2e5','illegal'),
            ('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1','f7g7','game_end'),
        )
        for fen,uci,event in cases:
            g.load_document(chess.Board(fen))
            move = chess.Move.from_uci(uci)
            with patch.object(g,'play_game_sound') as sound:
                g.try_move(move.from_square,move.to_square,promotion=move.promotion)
                sound.assert_called_once_with(getattr(g,'sound_'+event))
        with patch.object(g,'play_game_sound') as sound:
            g.start_game()
            sound.assert_called_once_with(g.sound_game_start)
            sound.reset_mock()
            g.resign()
            sound.assert_called_once_with(g.sound_game_end)
        g.sound_enabled = False
        with patch('otb_chess.core.game.play_sound') as playback:
            g.play_game_sound(g.sound_move)
            playback.assert_not_called()

    def test_position_setup_live_fen_placement_and_validation(self):
        from otb_chess.ui.position_setup import PositionSetup
        dialog = PositionSetup(self.window,self.game.board.fen())
        try:
            ok = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
            self.assertTrue(ok.isEnabled())
            dialog.replace_board(chess.Board(None))
            self.assertFalse(ok.isEnabled())
            for square,symbol in ((chess.E1,'K'),(chess.E8,'k'),(chess.A2,'P')):
                dialog.selected_piece = symbol
                QTest.mouseClick(dialog.squares[square],Qt.MouseButton.LeftButton)
            self.assertTrue(ok.isEnabled())
            self.assertEqual(chess.Board(dialog.fen.text()).piece_at(chess.A2).symbol(),'P')
            self.assertTrue(all(not icon.isNull() for icon in dialog.piece_icons.values()))
            self.assertFalse(dialog.squares[chess.A2].icon().isNull())
            QTest.mouseClick(dialog.squares[chess.A2],Qt.MouseButton.RightButton)
            self.assertEqual(chess.Board(dialog.fen.text()).piece_at(chess.A2).symbol(),'p')
            QTest.mouseClick(dialog.squares[chess.A2],Qt.MouseButton.RightButton)
            self.assertEqual(chess.Board(dialog.fen.text()).piece_at(chess.A2).symbol(),'P')
            QTest.mouseClick(dialog.squares[chess.A2],Qt.MouseButton.MiddleButton)
            self.assertIsNone(chess.Board(dialog.fen.text()).piece_at(chess.A2))
            self.assertTrue(dialog.squares[chess.A2].icon().isNull())
            fen = 'r3k2r/8/8/3pP3/8/8/8/R3K2R w KQkq d6 0 23'
            dialog.fen.setText(fen)
            self.assertTrue(ok.isEnabled())
            self.assertEqual(dialog.board.fen(),fen.replace('d6 0 23','- 0 1'))
            self.assertEqual(dialog.fen.text(),dialog.board.fen())
            self.assertIsNone(dialog.board.ep_square)
            self.assertEqual(dialog.board.fullmove_number,1)
            self.assertFalse(dialog.findChildren(QSpinBox))
            self.assertTrue(all(c.isChecked() for c in dialog.castling.values()))
            dialog.fen.setText('not a FEN')
            self.assertFalse(ok.isEnabled())
            dialog.accept()
            self.assertNotEqual(dialog.result(),QDialog.DialogCode.Accepted)
            dialog.replace_board(chess.Board())
            self.assertTrue(ok.isEnabled())
        finally:
            dialog.close()

    def test_setup_click_pickup_drop_replaces_and_cancels(self):
        from otb_chess.ui.position_setup import PositionSetup
        dialog = PositionSetup(self.window,self.game.board.fen())
        try:
            original = dialog.board.fen()
            def click(square,button=Qt.MouseButton.LeftButton):
                QTest.mouseClick(dialog.squares[square],button)
            click(chess.B1)
            self.assertEqual(dialog.picked_square,chess.B1)
            self.assertEqual(dialog.board.fen(),original)
            self.assertTrue(dialog.squares[chess.B1].icon().isNull())
            click(chess.E7)
            self.assertIsNone(dialog.picked_square)
            self.assertIsNone(dialog.board.piece_at(chess.B1))
            self.assertEqual(dialog.board.piece_at(chess.E7).symbol(),'N')
            self.assertEqual(chess.Board(dialog.fen.text()).piece_at(chess.E7).symbol(),'N')
            click(chess.E7)
            click(chess.E7)
            self.assertEqual(dialog.board.piece_at(chess.E7).symbol(),'N')
            click(chess.E7)
            click(chess.E7,Qt.MouseButton.RightButton)
            click(chess.D4)
            self.assertEqual(dialog.board.piece_at(chess.D4).symbol(),'n')
            click(chess.D4)
            dialog.select_piece('Q')
            self.assertIsNone(dialog.picked_square)
            self.assertFalse(dialog.squares[chess.D4].icon().isNull())
            click(chess.D4)
            click(chess.D4,Qt.MouseButton.MiddleButton)
            self.assertIsNone(dialog.picked_square)
            self.assertIsNone(dialog.board.piece_at(chess.D4))
        finally:
            dialog.close()

    def test_setup_position_cancel_and_start_preserve_custom_root(self):
        from otb_chess.ui.position_setup import PositionSetup
        w,g = self.window,self.game
        original = g.board.fen()
        fen = 'r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 7 23'
        expected = fen.replace('7 23','0 1')
        for accept in (False,True):
            def choose():
                dialog = QApplication.activeModalWidget()
                self.assertIsInstance(dialog,PositionSetup)
                dialog.fen.setText(fen)
                dialog.accept() if accept else dialog.reject()
            QTimer.singleShot(0,choose)
            w.setup_position()
            self.assertEqual(g.board.fen(),expected if accept else original)
        self.assertFalse(g.game_started)
        w.play_pause()
        self.assertTrue(g.game_started)
        self.assertEqual(g.board.fen(),expected)
        self.assertEqual(g.active_clock_color,chess.BLACK)
        with patch.object(g,'play_game_sound'):
            self.assertTrue(g.try_move(chess.E8,chess.G8))
        self.assertEqual(g.history_board().root().fen(),expected)
        self.assertIn('[SetUp "1"]',g.export_pgn())
        self.assertIn('1... O-O',g.export_pgn())
        self.assertFalse(w.setup_position_action.isEnabled())
        with patch.object(w,'confirm',return_value=True):
            w.new_game()
        self.assertEqual(g.board.fen(),chess.Board().fen())

    def test_evaluation_graph_reviews_full_game_and_updates_on_new_game(self):
        from otb_chess.core.evaluation import evaluate_position
        w,g = self.window,self.game
        g.start_game()
        with patch.object(g,'play_game_sound'):
            for source,target in ((chess.E2,chess.E4),(chess.D7,chess.D5),(chess.E4,chess.D5)):
                self.assertTrue(g.try_move(source,target))
        live = g.board.fen()
        w.open_evaluation_graph()
        graph = w.evaluation_graph
        self.assertEqual(len(graph.chart.values),4)
        self.assertEqual(graph.chart.values[-1],evaluate_position(g.board).centipawns/100)
        rect = graph.chart.plot_rect()
        QTest.mouseClick(graph.chart,Qt.MouseButton.LeftButton,
                         pos=QPoint(round(rect.left()+rect.width()/3),round(rect.center().y())))
        self.assertTrue(g.clock_paused)
        self.assertEqual(len(g.board.move_stack),1)
        self.assertEqual(len(graph.chart.values),4)
        self.assertEqual(len(g.history_board().move_stack),3)
        self.assertEqual(graph.chart.current,1)
        graph.select_ply(0)
        self.assertEqual(len(g.board.move_stack),0)
        graph.select_ply(3)
        self.assertEqual(g.board.fen(),live)
        self.assertIsNone(g._review_live)
        self.assertFalse(g.analysis_enabled)
        w.open_evaluation_graph()
        self.assertIs(w.evaluation_graph,graph)
        g.start_game()
        graph.refresh()
        self.assertEqual(graph.chart.values,[0])
        graph.close()
        self.assertFalse(graph.timer.isActive())

    def test_evaluation_graph_imported_black_move_and_checkmate(self):
        import math
        w,g = self.window,self.game
        board = chess.Board()
        board.push_uci('f2f3')
        board = chess.Board(board.fen())
        for move in ('e7e5','g2g4','d8h4'):
            board.push_uci(move)
        g.load_document(board)
        w.open_evaluation_graph()
        graph = w.evaluation_graph
        self.assertIn('1... e5',graph.labels[1])
        self.assertEqual(graph.chart.values[-1],-math.inf)
        self.assertIn('checkmate',graph.labels[-1])
        graph.chart.grab()
        graph.select_ply(1)
        self.assertEqual(len(g.board.move_stack),1)
        self.assertEqual(len(graph.chart.values),4)

    def test_reset_view_centers_and_fits_board_to_viewport(self):
        g = self.game
        for width,height in ((900,760),(500,760),(1600,760)):
            g.width,g.height = width,height
            g.yaw,g.pan_x,g.pan_z,g.distance = 1,2,-2,20
            g.reset_view()
            self.widget.makeCurrent()
            from OpenGL.GL import glViewport
            glViewport(0,0,width,height)
            g.camera()
            points = [gluProject(x,y,z+g.pan_z)
                      for half,heights in ((4.36,(-.46,.025)),(3.92,(0,1.65)))
                      for x in (-half,half) for y in heights for z in (-half,half)]
            left,right = min(p[0] for p in points),max(p[0] for p in points)
            bottom,top = min(p[1] for p in points),max(p[1] for p in points)
            self.assertAlmostEqual((left+right)/2,width/2,places=3)
            self.assertAlmostEqual((bottom+top)/2,height/2,places=3)
            self.assertAlmostEqual(max((right-left)/width,(top-bottom)/height),.93,places=3)
            self.assertGreater(left,0)
            self.assertLess(right,width)
            self.assertGreater(bottom,0)
            self.assertLess(top,height)

    def test_2d_click_drag_zoom_pan_and_3d_switch(self):
        w,g,b = self.window,self.game,self.widget
        w.mode_actions["2D"].trigger()
        self.qt.processEvents()
        with patch.object(g,"play_game_sound"):
            QTest.mouseClick(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E2))
            QTest.mouseClick(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E4))
            self.assertEqual(g.board.peek(),chess.Move.from_uci("e2e4"))
            QTest.mousePress(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E7))
            QTest.mouseMove(b,self.screen(chess.E5))
            QTest.mouseRelease(b,Qt.MouseButton.LeftButton,pos=self.screen(chess.E5))
            self.assertEqual(g.board.peek(),chess.Move.from_uci("e7e5"))
        self.assertEqual(w.moves.item(0,1).text(),"e4")
        self.assertEqual(w.moves.item(0,2).text(),"e5")
        old = g.two_d_scale
        event = QWheelEvent(QPointF(100,100),QPointF(100,100),QPoint(),QPoint(0,120),
                            Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
        QApplication.sendEvent(b,event)
        self.assertLess(g.two_d_scale,old)
        g.selected = None
        start = self.screen(chess.D4)
        end = start+QPoint(30,25)
        QTest.mousePress(b,Qt.MouseButton.LeftButton,pos=start)
        QTest.mouseMove(b,end)
        QTest.mouseRelease(b,Qt.MouseButton.LeftButton,pos=end)
        actual = self.screen(chess.D4)
        self.assertLess((actual-end).manhattanLength(),3)
        for flipped in (False,True):
            g.two_d_flipped = flipped
            for square in chess.SQUARES:
                point = self.screen(square)
                self.assertEqual(g.square_at_mouse((point.x(),point.y())),square)
        fen = g.board.fen()
        w.mode_actions["3D"].trigger()
        w.set_actions["club"].trigger()
        b.grabFramebuffer()
        self.assertEqual(glGetError(),GL_NO_ERROR)
        self.assertEqual(g.board.fen(),fen)
        self.assertEqual(g.piece_set,"club")

    def test_clocks_start_pause_and_otb_click(self):
        w,g = self.window,self.game
        g.clock_mode_var.set("OTB")
        w.play_pause()
        self.assertTrue(g.game_started)
        w.play_pause()
        self.assertTrue(g.clock_paused)
        w.play_pause()
        self.assertFalse(g.clock_paused)
        with patch.object(g,"play_game_sound"):
            g.try_move(chess.E2,chess.E4)
        w.tick()
        self.assertTrue(g.awaiting_clock_press)
        self.assertEqual(w.white_clock.state.text(),"PRESS CLOCK")
        QTest.mouseClick(w.black_clock,Qt.MouseButton.LeftButton)
        self.assertTrue(g.awaiting_clock_press)
        QTest.mouseClick(w.white_clock,Qt.MouseButton.LeftButton)
        self.assertFalse(g.awaiting_clock_press)
        self.assertEqual(g.active_clock_color,chess.BLACK)

    def test_new_game_first_click_waits_for_startup_engine(self):
        w, g = self.window, self.game
        g.engine_loading = True
        w.tick()
        self.assertTrue(w.play_button.isEnabled())
        QTest.mouseClick(w.play_button, Qt.MouseButton.LeftButton)
        self.assertTrue(w.new_game_pending)
        self.assertFalse(g.game_started)
        w.tick()
        self.assertEqual(w.play_button.text(), "Starting game…")
        g.engine_manager.engine = Mock()
        g.engine_manager.path = "stockfish.exe"
        g.engine_side_var.set("Black")
        g.engine_load_result = ("stockfish.exe", (True, "Loaded"))
        g.engine_loading = False
        with patch.object(g, "request_analysis"), patch.object(g, "start_game", wraps=g.start_game) as start:
            w.tick()
            w.tick()
            start.assert_called_once()
        self.assertTrue(g.game_started)
        self.assertEqual(g.engine_side, chess.BLACK)
        self.assertFalse(w.new_game_pending)

    def test_new_game_waits_for_search_and_discards_previous_result(self):
        w, g = self.window, self.game
        for operation in ("analysis", "move"):
            with self.subTest(operation=operation):
                g.board = chess.Board()
                g.board.push_uci("e2e4")
                g.analysis_busy = operation == "analysis"
                g.engine_manager.thinking = operation == "move"
                with patch.object(w, "confirm", return_value=True) as confirm:
                    w.new_game()
                    w.new_game()
                    confirm.assert_called_once()
                self.assertTrue(w.new_game_pending)
                g.analysis_enabled = True
                g.engine_manager.engine = Mock()
                g.analysis_busy = g.engine_manager.thinking = False
                # Pending new-game requests suppress another analysis search.
                g.request_analysis()
                g.engine_manager.engine.analyse.assert_not_called()
                g.pending_engine_position = g.board.fen()
                g.pending_engine_move = OwnedMove(chess.E7, chess.E5)
                with patch.object(g, "request_analysis"), patch.object(g, "try_move") as move:
                    w.tick()
                    move.assert_not_called()
                self.assertFalse(w.new_game_pending)
                self.assertEqual(g.board.fen(), chess.STARTING_FEN)
                self.assertIsNone(g.pending_engine_move)
                self.assertTrue(g.game_started)

    def test_cancel_new_game_does_not_queue_restart(self):
        w, g = self.window, self.game
        g.board.push_uci("e2e4")
        before = g.board.fen()
        g.analysis_busy = True
        with patch.object(w, "confirm", return_value=False):
            w.new_game()
        g.analysis_busy = False
        w.tick()
        self.assertFalse(w.new_game_pending)
        self.assertEqual(g.board.fen(), before)

    def test_new_game_clocks_wait_for_first_legal_move(self):
        g = self.game
        for mode in ("Online","OTB"):
            g.clock_mode_var.set(mode)
            g.start_game()
            initial = (g.white_time,g.black_time)
            with patch.object(time,"perf_counter",return_value=g.last_clock_tick+30):
                g.update_clock()
            self.assertEqual((g.white_time,g.black_time),initial)
            self.assertFalse(g.try_move(chess.E2,chess.E5))
            with patch.object(time,"perf_counter",return_value=g.last_clock_tick+30):
                g.update_clock()
            self.assertEqual((g.white_time,g.black_time),initial)
            with patch.object(g,"play_game_sound"):
                self.assertTrue(g.try_move(chess.E2,chess.E4))
            before = (g.white_time,g.black_time)
            with patch.object(time,"perf_counter",return_value=g.last_clock_tick+2):
                g.update_clock()
            expected = (before[0]-2,before[1]) if mode == "OTB" else (before[0],before[1]-2)
            self.assertEqual((g.white_time,g.black_time),expected)

    def test_right_mouse_otb_and_paused_history_navigation(self):
        w,g = self.window,self.game
        g.clock_mode_var.set("OTB")
        g.clock_binding_var.set("Right Mouse")
        g.start_game()
        with patch.object(g,"play_game_sound"):
            g.try_move(chess.E2,chess.E4)
        self.assertTrue(g.awaiting_clock_press)
        QTest.mouseClick(self.widget,Qt.MouseButton.RightButton,pos=QPoint(50,50))
        self.assertFalse(g.awaiting_clock_press)
        self.assertFalse(g.right_drag)
        self.assertEqual(g.active_clock_color,chess.BLACK)
        with patch.object(g,"play_game_sound"):
            g.try_move(chess.E7,chess.E5)
        g.hit_clock()
        live = g.board.fen()
        g.stop_clock()
        item = w.moves.item(0,1)
        QTest.mouseClick(w.moves.viewport(),Qt.MouseButton.LeftButton,pos=w.moves.visualItemRect(item).center())
        self.assertEqual(len(g.board.move_stack),1)
        self.assertEqual(w.moves.item(0,2).text(),"e5")
        self.assertFalse(g.human_can_move())
        g.stop_clock()
        self.assertEqual(g.board.fen(),live)
        self.assertFalse(g.clock_paused)

    def test_open_save_notation_and_black_to_move_numbering(self):
        w,g = self.window,self.game
        board = chess.Board()
        board.push_uci('e2e4')
        self.assertTrue(w.import_notation(board.fen(),'fen'))
        with patch.object(g,'play_game_sound'):
            g.try_move(chess.E7,chess.E5)
        self.assertEqual(w.moves.item(0,2).text(),'e5')
        self.assertIsNone(w.moves.item(0,1))
        path = str(Path(self.folder.name)/'saved.pgn')
        with patch('otb_chess.ui.document_actions.QFileDialog.getSaveFileName',return_value=(path,'')):
            w.save_notation('pgn')
        with patch.object(w,'confirm',return_value=True):
            self.assertTrue(w.import_notation(Path(path).read_text(),'pgn'))
        self.assertEqual(g.board.root().fen(),board.fen())
        self.assertEqual(len(g.board.move_stack),1)
        self.assertFalse(g.game_started)

    def test_clock_dialog_applies_only_on_save(self):
        w,g = self.window,self.game
        errors = []
        def choose():
            try:
                dialog = w.findChild(QDialog)
                combo = dialog.findChildren(QComboBox)[0]
                combo.setCurrentText("Custom")
                fields = dialog.findChildren(QDoubleSpinBox)
                fields[0].setValue(125)
                fields[1].setValue(3)
                dialog.accept()
            except Exception as exc:
                errors.append(exc)
        QTimer.singleShot(0,choose)
        w.clock_settings()
        self.assertFalse(errors)
        self.assertEqual(g.time_control_var.get(),"Custom")
        self.assertEqual(g.selected_time_control().initial_seconds,125)
        self.assertEqual(settings.load_config()["custom_increment"],3)
        self.assertEqual((g.white_time,g.black_time,g.increment),(125,125,3))
        self.assertEqual(w.white_clock.digits.text(),g.fmt_clock(125))

    def test_clock_settings_preserve_paused_game(self):
        w,g = self.window,self.game
        g.start_game()
        with patch.object(g,"play_game_sound"):
            g.try_move(chess.E2,chess.E4)
        g.clock_paused = True
        g.white_time,g.black_time = 41,52
        original_increment = g.increment
        def choose():
            dialog = QApplication.activeModalWidget()
            dialog.findChildren(QComboBox)[0].setCurrentText("Custom")
            dialog.findChildren(QDoubleSpinBox)[0].setValue(125)
            dialog.accept()
        QTimer.singleShot(0,choose)
        w.clock_settings()
        self.assertEqual((g.white_time,g.black_time,g.increment),(41,52,original_increment))

    def test_new_game_clock_presets_apply_before_first_move(self):
        w,g = self.window,self.game
        w.new_game()
        self.assertTrue(g.game_started)
        for preset,seconds,increment in (("Bullet 2+1",120,1),("Classical 30+0",1800,0)):
            def choose():
                dialog = QApplication.activeModalWidget()
                dialog.findChildren(QComboBox)[0].setCurrentText(preset)
                dialog.accept()
            QTimer.singleShot(0,choose)
            w.clock_settings()
            self.assertEqual((g.white_time,g.black_time,g.increment),(seconds,seconds,increment))
            self.assertEqual(w.white_clock.digits.text(),g.fmt_clock(seconds))
            self.assertEqual(w.black_clock.digits.text(),g.fmt_clock(seconds))

    def test_new_game_clocks_can_be_edited_until_first_move(self):
        w,g = self.window,self.game
        w.new_game()
        for card,color in ((w.white_clock,chess.WHITE),(w.black_clock,chess.BLACK)):
            card.refresh(g)
            self.assertEqual(card.state.text(),"CLICK TO EDIT")
            def choose():
                dialog = QApplication.activeModalWidget()
                fields = dialog.findChildren(QSpinBox)
                fields[0].setValue(2)
                fields[1].setValue(15)
                dialog.accept()
            QTimer.singleShot(0,choose)
            QTest.mouseClick(card,Qt.MouseButton.LeftButton)
            self.assertEqual(g.white_time if color else g.black_time,135)
            self.assertFalse(g.clock_paused)
        with patch.object(g,"play_game_sound"):
            self.assertTrue(g.try_move(chess.E2,chess.E4))
        self.assertFalse(g.clocks_editable())
        self.assertFalse(g.clocks_waiting_for_first_move())

    def test_edit_each_paused_clock_and_cancel(self):
        w,g = self.window,self.game
        g.start_game()
        g.clock_paused = True
        g.white_time,g.black_time = 41,52
        fen = g.board.fen()
        for color,accept in ((chess.WHITE,True),(chess.BLACK,True),(chess.WHITE,False)):
            before = (g.white_time,g.black_time)
            def choose():
                dialog = QApplication.activeModalWidget()
                fields = dialog.findChildren(QSpinBox)
                fields[0].setValue(2)
                fields[1].setValue(15)
                for label,field in zip(("minutes","seconds"),fields):
                    for direction,expected in (("Increase",field.value()+1),("Decrease",field.value())):
                        button = next(b for b in dialog.findChildren(QPushButton)
                                      if b.accessibleName() == f"{direction} {label}")
                        QTest.mouseClick(button,Qt.MouseButton.LeftButton)
                        self.assertEqual(field.value(),expected)
                    self.assertNotIn(".",field.text())
                dialog.accept() if accept else dialog.reject()
            QTimer.singleShot(0,choose)
            QTest.mouseClick(w.white_clock if color else w.black_clock,Qt.MouseButton.LeftButton)
            expected = (135,before[1]) if color else (before[0],135)
            self.assertEqual((g.white_time,g.black_time),expected if accept else before)
            self.assertTrue(g.clock_paused)
            self.assertEqual(g.board.fen(),fen)

    def test_live_colour_preview_accept_and_cancel(self):
        w,g = self.window,self.game
        for which in ("light","background"):
            for accept in (False,True):
                original = g.color_value(which)
                observed = []
                def choose():
                    dialog = QApplication.activeModalWidget()
                    dialog.setCurrentColor(QColor("#123456"))
                    observed.append(g.color_value(which))
                    observed.append(g.preview_background_color)
                    self.widget.grabFramebuffer()
                    dialog.accept() if accept else dialog.reject()
                QTimer.singleShot(0,choose)
                w.choose_color(which)
                expected = QColor("#123456").getRgbF()[:3]
                self.assertEqual(observed,[expected,which == "background"])
                self.assertEqual(g.color_value(which),expected if accept else original)
                self.assertFalse(g.preview_background_color)

    def test_analysis_uses_worker_and_rejects_stale_positions(self):
        w,g = self.window,self.game
        engine = Mock()
        engine.analyse.return_value = EngineEvaluation(g.board.fen(), EngineScore(centipawns=34),
                                                       depth=12, pv=(OwnedMove(chess.E2,chess.E4),))
        g.engine_manager.engine = engine
        g.engine_manager.path = "test-engine.exe"
        g.analysis_enabled = True
        g.request_analysis()
        deadline = time.monotonic()+2
        while g.analysis_busy and time.monotonic()<deadline:
            time.sleep(.01)
        self.assertFalse(g.analysis_busy)
        w.tick()
        self.assertIn("+0.34",w.engine_metrics.text())
        self.assertEqual(w.engine_line.toPlainText(),"1. e4")
        g.analysis_enabled = False
        g.board.push_uci("d2d4")
        w.tick()
        self.assertEqual(w.engine_line.toPlainText(),"")
        g.pending_engine_position = chess.STARTING_FEN
        g.pending_engine_move = chess.Move.from_uci("d7d5")
        g.apply_pending_engine_move()
        self.assertEqual(len(g.board.move_stack),1)

    def test_engine_load_preserves_analysis_and_saves_strength_style(self):
        from otb_chess.ui.desktop_ui import ENGINE_DIR
        executable = next(ENGINE_DIR.rglob("stockfish*.exe"), None)
        if executable is None or sys.platform != "win32":
            self.skipTest("Bundled Windows Stockfish is not installed")
        w, g = self.window, self.game
        g.load_engine_path(str(executable))
        deadline = time.monotonic() + 8
        while g.engine_loading and time.monotonic() < deadline:
            QTest.qWait(10)
        w.tick()
        self.assertFalse(g.analysis_enabled)
        w.toggle_analysis(True)
        w.tick()
        self.assertTrue(g.analysis_enabled)
        self.assertTrue(w.analysis_action.isChecked())
        while g.analysis_busy and time.monotonic() < deadline:
            QTest.qWait(10)
        w.tick()
        self.assertIn("Engine evaluation:", w.engine_metrics.text())
        self.assertNotIn("favours White", w.engine_metrics.text())
        w.toggle_analysis(False)
        def choose():
            dialog = self.qt.activeModalWidget()
            dialog.findChild(QComboBox, "engineStrength").setCurrentIndex(1)
            rating = dialog.findChild(QSpinBox, "engineRating")
            self.assertEqual((rating.minimum(), rating.maximum()), (1320, 3190))
            rating.setValue(1600)
            dialog.findChild(QComboBox, "engineStyle").setCurrentText("Active")
            dialog.accept()
        QTimer.singleShot(0, choose)
        w.engine_settings()
        config = settings.load_config()
        self.assertEqual(config["engine_elo"], 1600)
        self.assertEqual(config["engine_style"], "Active")
        self.assertEqual(config["engine_path"], str(executable))

    def test_engine_rating_keeps_edits_modes_and_saved_values(self):
        w, g = self.window, self.game
        g.engine_manager.engine = Mock()
        g.engine_manager.engine.strength_range.return_value = (1320, 3190)
        g.engine_manager.path = sys.executable
        g.engine_var.set(sys.executable)
        g.cfg["engine_elo"] = 1600
        def edit_minimum():
            dialog = self.qt.activeModalWidget()
            rating = dialog.findChild(QSpinBox, "engineRating")
            strength = dialog.findChild(QComboBox, "engineStrength")
            self.assertEqual(rating.value(), 1600)
            self.assertEqual(rating.text(), "1600")
            rating.setValue(1320)
            strength.setCurrentIndex(0)
            strength.setCurrentIndex(1)
            self.assertEqual(rating.value(), 1320)
            engine = next(combo for combo in dialog.findChildren(QComboBox)
                          if combo.isEditable() and combo.currentText() == sys.executable)
            engine.setCurrentText("")
            engine.setCurrentText(sys.executable)
            self.assertEqual(rating.value(), 1320)
            strength.setCurrentIndex(0)
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
        QTimer.singleShot(0, edit_minimum)
        w.engine_settings()
        self.assertIsNone(g.cfg["engine_elo"])
        self.assertEqual(settings.load_config()["engine_rating"], 1320)
        def type_rating():
            dialog = self.qt.activeModalWidget()
            rating = dialog.findChild(QSpinBox, "engineRating")
            self.assertEqual(rating.value(), 1320)
            dialog.findChild(QComboBox, "engineStrength").setCurrentIndex(1)
            rating.lineEdit().selectAll()
            QTest.keyClicks(rating.lineEdit(), "1800")
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
        QTimer.singleShot(0, type_rating)
        w.engine_settings()
        self.assertEqual(settings.load_config()["engine_elo"], 1800)
        def reopen():
            dialog = self.qt.activeModalWidget()
            self.assertEqual(dialog.findChild(QSpinBox, "engineRating").text(), "1800")
            dialog.reject()
        QTimer.singleShot(0, reopen)
        w.engine_settings()

    def test_static_evaluation_follows_review_without_engine(self):
        w, g = self.window, self.game
        self.assertIsNone(g.engine_manager.engine)
        self.assertIn("+0.00", w.static_evaluation.text())
        self.assertNotIn("White", w.static_evaluation.text())
        self.assertNotIn("Black", w.static_evaluation.text())
        self.assertFalse(w.static_evaluation.isVisible())
        self.assertFalse(w.engine_panel.isVisible())
        w.engine_toggle.setChecked(True)
        self.assertTrue(w.static_evaluation.isVisible())
        w.engine_toggle.setChecked(False)
        self.assertFalse(w.static_evaluation.isVisible())
        for move in ("e2e4", "d7d5", "e4d5"):
            g.board.push_uci(move)
        w.refresh_moves()
        live_score = w.static_evaluation.text()
        self.assertNotIn("+0.00", live_score)
        self.assertTrue(g.navigate_to_ply(0))
        self.assertIn("+0.00", w.static_evaluation.text())
        self.assertTrue(g.navigate_to_ply(1))
        self.assertNotEqual(w.static_evaluation.text(), live_score)
        g.return_to_live()
        self.assertEqual(w.static_evaluation.text(), live_score)
        g.load_document(chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"))
        self.assertIn("White wins", w.static_evaluation.text())
        g.reset_board()
        self.assertIn("+0.00", w.static_evaluation.text())
        w.static_evaluation_action.trigger()
        self.assertTrue(w.move_list_evaluation.isVisible())
        self.assertEqual(w.move_list_evaluation.text(), "+0.00")
        self.assertFalse(w.static_evaluation.isVisible())
        self.assertTrue(settings.load_config()["always_show_static_evaluation"])
        g.board.push_uci("e2e4")
        w.refresh_moves()
        self.assertNotIn("+0.00", w.move_list_evaluation.text())
        w.engine_toggle.setChecked(True)
        self.assertFalse(w.static_evaluation.isVisible())
        w.static_evaluation_action.trigger()
        self.assertFalse(w.move_list_evaluation.isVisible())
        self.assertTrue(w.static_evaluation.isVisible())
        self.assertFalse(settings.load_config()["always_show_static_evaluation"])

    def test_analysis_preference_restored_and_not_overridden_by_engine_load(self):
        for enabled in (True,False):
            self.window.toggle_analysis(enabled)
            self.assertEqual(settings.load_config()['analysis_enabled'],enabled)
            restored = MainWindow()
            restored.timer.stop()
            try:
                self.assertEqual(restored.game.analysis_enabled,enabled)
                self.assertEqual(restored.analysis_action.isChecked(),enabled)
                self.assertEqual(restored.analysis_button.isChecked(),enabled)
                self.assertEqual(restored.analysis_button.text(),'Stop analysis' if enabled else 'Start analysis')
                restored.game.engine_load_result = ('stockfish.exe',(True,'Loaded'))
                with patch.object(restored.game,'request_analysis') as request:
                    restored.tick()
                    self.assertEqual(request.called,enabled)
                self.assertEqual(restored.game.analysis_enabled,enabled)
                self.assertEqual(settings.load_config()['analysis_enabled'],enabled)
            finally:
                restored.close()

    def test_difficulty_presets_choose_engine_strength_and_persist(self):
        from otb_chess.services.difficulty import DIFFICULTIES
        w,g = self.window,self.game
        with patch('otb_chess.services.difficulty.missing_files',return_value=[]), \
                patch('otb_chess.services.difficulty.engine_path',side_effect=lambda key:Path(self.folder.name)/('lc0.exe' if DIFFICULTIES[key].engine=='maia' else 'stockfish.exe')), \
                patch.object(g,'load_engine_path') as load:
            for key,preset in DIFFICULTIES.items():
                w.difficulty_actions[key].trigger()
                self.assertEqual(g.cfg['engine_difficulty'],key)
                self.assertEqual(g.cfg['engine_elo'],preset.rating if preset.engine=='stockfish' else None)
                self.assertEqual(g.cfg['engine_style'],'Balanced')
                self.assertEqual(g.book_var.get(),'')
                self.assertTrue(w.difficulty_actions[key].isChecked())
                self.assertEqual(settings.load_config()['engine_difficulty'],key)
                self.assertEqual(Path(load.call_args.args[0]).name,'lc0.exe' if preset.engine=='maia' else 'stockfish.exe')
            g.engine_manager.thinking = True
            load.reset_mock()
            w.select_difficulty('club')
            self.assertEqual(w.pending_difficulty,'club')
            load.assert_not_called()
            g.pending_engine_move = OwnedMove(chess.E2,chess.E4)
            g.engine_manager.thinking = False
            w.tick()
            self.assertIsNone(w.pending_difficulty)
            self.assertIsNone(g.pending_engine_move)
            self.assertFalse(g.board.move_stack)
            self.assertEqual(g.cfg['engine_difficulty'],'club')
            load.assert_called_once()

    def test_engine_maia_preset_loads_plays_and_switches_to_stockfish(self):
        from otb_chess.services.difficulty import DIFFICULTIES
        w,g = self.window,self.game
        with patch.object(settings,'ENGINE_DIR',settings.APP_DIR/'engines'):
            w.select_difficulty('club')
            deadline = time.monotonic()+8
            while g.engine_loading and time.monotonic()<deadline:
                QTest.qWait(10)
            w.tick()
            self.assertIsInstance(g.engine_manager.engine,uci.MaiaEngine)
            self.assertEqual(g.cfg['engine_difficulty'],'club')
            self.assertIn('Maia',w.engine_name.text())
            g.start_game()
            with patch.object(g,'play_game_sound'):
                self.assertTrue(g.try_move(chess.E2,chess.E4))
                while g.engine_manager.thinking and time.monotonic()<deadline:
                    QTest.qWait(10)
                w.tick()
            self.assertEqual(len(g.board.move_stack),2)
            self.assertEqual(g.last_engine_search[1].nodes,1)
            w.select_difficulty('cm_practice')
            while g.engine_loading and time.monotonic()<deadline:
                QTest.qWait(10)
            w.tick()
            self.assertIsNotNone(g.engine_manager.engine)
            self.assertNotIsInstance(g.engine_manager.engine,uci.MaiaEngine)
            self.assertEqual(g.cfg['engine_elo'],2000)
            self.assertEqual(settings.load_config()['engine_difficulty'],'cm_practice')

    def test_engine_custom_menu_opens_custom_without_changing_saved_preset(self):
        w,g = self.window,self.game
        g.cfg['engine_difficulty'] = 'club'
        g.persist()
        w.refresh_difficulty_actions()
        observed = []
        def inspect():
            dialog = QApplication.activeModalWidget()
            observed.append(dialog.findChild(QComboBox,'engineDifficulty').currentData())
            observed.append(dialog.findChild(QComboBox,'engineStyle').isEnabled())
            dialog.reject()
        QTimer.singleShot(0,inspect)
        w.custom_difficulty_action.trigger()
        self.assertEqual(observed,['custom',True])
        self.assertEqual(g.cfg['engine_difficulty'],'club')
        self.assertEqual(settings.load_config()['engine_difficulty'],'club')
        self.assertTrue(w.difficulty_actions['club'].isChecked())
        self.assertFalse(w.custom_difficulty_action.isChecked())

    def test_engine_difficulty_dialog_save_and_cancel(self):
        w,g = self.window,self.game
        original = g.cfg['engine_difficulty']
        for accept in (False,True):
            def choose():
                dialog = QApplication.activeModalWidget()
                combo = dialog.findChild(QComboBox,'engineDifficulty')
                combo.setCurrentIndex(combo.findData('beginner'))
                self.assertEqual(dialog.findChild(QSpinBox,'engineRating').value(),300)
                self.assertFalse(dialog.findChild(QSpinBox,'engineRating').isEnabled())
                dialog.accept() if accept else dialog.reject()
            with patch('otb_chess.services.difficulty.missing_files',return_value=[]), \
                    patch('otb_chess.services.difficulty.engine_path',return_value=Path(self.folder.name)/'lc0.exe'), \
                    patch.object(g,'load_engine_path') as load:
                QTimer.singleShot(0,choose)
                w.engine_settings()
                self.assertEqual(g.cfg['engine_difficulty'],'beginner' if accept else original)
                self.assertEqual(load.called,accept)
        restored = MainWindow()
        restored.timer.stop()
        try:
            self.assertEqual(restored.game.cfg['engine_difficulty'],'beginner')
            self.assertTrue(restored.difficulty_actions['beginner'].isChecked())
            self.assertEqual(restored.game.cfg['engine_rating'],300)
        finally:
            restored.close()

    def test_engine_output_analysis_button_and_menu_stay_in_sync(self):
        w, g = self.window, self.game
        w.tick()
        self.assertFalse(w.analysis_button.isEnabled())
        g.engine_manager.engine = Mock()
        w.tick()
        w.engine_toggle.setChecked(True)
        self.assertTrue(w.analysis_button.isEnabled())
        QTest.mouseClick(w.analysis_button, Qt.MouseButton.LeftButton)
        self.assertTrue(g.analysis_enabled)
        self.assertTrue(w.analysis_action.isChecked())
        self.assertEqual(w.analysis_button.text(), "Stop analysis")
        QTest.mouseClick(w.analysis_button, Qt.MouseButton.LeftButton)
        self.assertFalse(g.analysis_enabled)
        self.assertFalse(w.analysis_action.isChecked())
        self.assertEqual(w.analysis_button.text(), "Start analysis")
        with patch.object(g, "request_analysis") as request:
            w.tick()
            request.assert_not_called()
        g.board.push_uci("e2e4")
        w.tick()
        self.assertNotIn("+0.00", w.static_evaluation.text())
        w.analysis_action.trigger()
        self.assertTrue(w.analysis_button.isChecked())
        self.assertEqual(w.analysis_button.text(), "Stop analysis")
        w.analysis_action.trigger()
        self.assertFalse(w.analysis_button.isChecked())

    def test_evaluation_formats_negative_scores_and_mate(self):
        w, g = self.window, self.game
        for score, expected in ((EngineScore(centipawns=-125), "-1.25"),
                                (EngineScore(centipawns=0), "+0.00"),
                                (EngineScore(mate=-3), "Mate -3")):
            w.show_engine_info(g.board.fen(), EngineEvaluation(g.board.fen(), score))
            self.assertIn(expected, w.engine_metrics.text())

    def test_engine_lines_number_moves_from_source_position(self):
        for fen, line, expected in (
            (chess.STARTING_FEN, ("e2e4", "e7e5", "g1f3"), "1. e4 e5 2. Nf3"),
            ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 17",
             ("e7e5", "g1f3", "b8c6"), "17... e5 18. Nf3 Nc6"),
        ):
            with self.subTest(expected=expected):
                pv = tuple(OwnedMove(m.from_square, m.to_square, m.promotion)
                           for m in map(chess.Move.from_uci, line))
                self.window.show_engine_info(fen, EngineEvaluation(fen, pv=pv))
                self.assertEqual(self.window.engine_line.toPlainText(), expected)

    def test_promotion_dialog_all_pieces_for_both_colours(self):
        g = self.game
        for color in (chess.WHITE, chess.BLACK):
            for label, piece_type in (("Queen", chess.QUEEN), ("Rook", chess.ROOK),
                                      ("Bishop", chess.BISHOP), ("Knight", chess.KNIGHT)):
                with self.subTest(color=color, piece=label):
                    g.board = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1" if color else
                                          "7k/8/8/8/8/8/p7/7K b - - 0 1")
                    g.game_over = False
                    src, dst = (chess.A7, chess.A8) if color else (chess.A2, chess.A1)
                    def choose(label=label):
                        dialog = self.qt.activeModalWidget()
                        self.assertEqual(dialog.objectName(), "promotionDialog")
                        QTest.mouseClick(dialog.findChild(QPushButton, "promote" + label), Qt.MouseButton.LeftButton)
                    QTimer.singleShot(0, choose)
                    with patch.object(g, "play_game_sound"):
                        self.assertTrue(g.try_move(src, dst))
                    self.assertEqual(g.board.piece_at(dst), chess.Piece(piece_type, color))
                    self.assertEqual(g.board.peek().promotion, piece_type)
                    self.assertIn("=" + chess.piece_symbol(piece_type).upper(), g.export_pgn())

    def test_promotion_cancel_illegal_destination_and_clock_expiry(self):
        g = self.game
        g.board = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1")
        before = g.board.fen()
        g.selected = chess.A7
        QTimer.singleShot(0, lambda: self.qt.activeModalWidget().reject())
        self.assertFalse(g.try_move(chess.A7, chess.A8))
        self.assertEqual(g.board.fen(), before)
        self.assertEqual(g.selected, chess.A7)
        with patch.object(g, "choose_promotion") as chooser:
            self.assertFalse(g.try_move(chess.A7, chess.B8))
            chooser.assert_not_called()
        def expired():
            g.game_over = True
            self.qt.activeModalWidget().findChild(QPushButton, "promoteKnight").click()
        QTimer.singleShot(0, expired)
        self.assertFalse(g.try_move(chess.A7, chess.A8))
        self.assertEqual(g.board.fen(), before)

    def test_capture_promotion_through_click_and_drag(self):
        g = self.game
        for drag in (False, True):
            with self.subTest(drag=drag):
                g.board = chess.Board("1r5k/P7/8/8/8/8/8/7K w - - 0 1")
                g.game_over = False
                g.cancel_selection()
                src = self.screen(chess.A7)
                dst = self.screen(chess.B8)
                g.left_press((src.x(), src.y()))
                if drag:
                    g.left_motion((dst.x(), dst.y()))
                else:
                    g.left_release((src.x(), src.y()))
                QTimer.singleShot(0, lambda: self.qt.activeModalWidget().findChild(QPushButton, "promoteKnight").click())
                with patch.object(g, "play_game_sound"):
                    if drag:
                        g.left_release((dst.x(), dst.y()))
                    else:
                        g.left_press((dst.x(), dst.y()))
                        g.left_release((dst.x(), dst.y()))
                self.assertEqual(g.board.piece_at(chess.B8), chess.Piece(chess.KNIGHT, chess.WHITE))
                self.assertIsNone(g.board.piece_at(chess.A7))
                self.assertIsNone(g.selected)

    def test_pending_engine_or_book_underpromotion_is_preserved(self):
        g = self.game
        for color in (chess.WHITE, chess.BLACK):
            for piece in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
                g.board = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1" if color else
                                      "7k/8/8/8/8/8/p7/7K b - - 0 1")
                g.game_over = False
                g.clock_paused = False
                src, dst = (chess.A7, chess.A8) if color else (chess.A2, chess.A1)
                g.pending_engine_position = g.board.fen()
                g.pending_engine_move = OwnedMove(src, dst, piece)
                with patch.object(g, "choose_promotion") as chooser, patch.object(g, "play_game_sound"):
                    g.apply_pending_engine_move()
                    chooser.assert_not_called()
                self.assertEqual(g.board.peek().promotion, piece)
                self.assertEqual(g.board.piece_at(dst), chess.Piece(piece, color))

    def test_layout_preferences_persist_on_close(self):
        self.window.resize(1100,720)
        self.window.focus_action.trigger()
        self.window.engine_toggle.setChecked(True)
        self.qt.processEvents()
        self.window.close()
        cfg = settings.load_config()
        self.assertEqual(cfg["window_size"],[1100,720])
        self.assertTrue(cfg["focus_mode"])
        self.assertTrue(cfg["engine_panel_open"])

    def test_uci_subprocess_play_and_analysis_output(self):
        w,g = self.window,self.game
        fixture = Path(__file__).parent/"fixtures"/"uci_stub.py"
        g.engine_manager.engine = uci.Engine.open([sys.executable,str(fixture)])
        g.engine_manager.path = "UI Test Engine"
        g.engine_side_var.set("Black")
        g.start_game()
        with patch.object(g,"play_game_sound"):
            g.try_move(chess.E2,chess.E4)
            deadline = time.monotonic()+4
            while g.engine_manager.thinking and time.monotonic()<deadline:
                QTest.qWait(10)
            w.tick()
        self.assertEqual(len(g.board.move_stack),2)
        self.assertIn("Last search",w.engine_metrics.text())
        self.assertIn("Depth 8",w.engine_metrics.text())
        self.assertTrue(w.engine_line.toPlainText())
        g.analysis_enabled = True
        g.request_analysis()
        deadline = time.monotonic()+4
        while g.analysis_busy and time.monotonic()<deadline:
            QTest.qWait(10)
        w.tick()
        self.assertIn("+0.25",w.engine_metrics.text())
        self.assertNotIn("Last search",w.engine_metrics.text())


if __name__ == "__main__":
    unittest.main()
