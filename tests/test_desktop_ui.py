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
from PySide6.QtWidgets import QApplication, QDialog, QComboBox, QDoubleSpinBox, QColorDialog, QSpinBox, QPushButton

import main
from desktop_ui import MainWindow, configure_graphics


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_graphics()
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = patch.object(main,"CONFIG_PATH",Path(self.folder.name)/"config.json")
        self.config.start()
        self.addCleanup(self.config.stop)
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
        x,y,_ = main.gluProject(3.5-chess.square_file(square)+px,0,chess.square_rank(square)-3.5+pz)
        ratio = self.widget.devicePixelRatioF()
        return QPoint(round(x/ratio),round((self.game.height-y)/ratio))

    def test_interface_themes_apply_and_persist(self):
        w,g = self.window,self.game
        original = (g.board.fen(),g.light_square,g.dark_square,g.background_color)
        styles = set()
        for name,action in w.interface_theme_actions.items():
            action.trigger()
            self.qt.processEvents()
            styles.add(w.styleSheet())
            self.assertEqual(w.interface_theme,name)
            self.assertEqual(main.load_config()["interface_theme"],name)
            self.assertEqual(sum(a.isChecked() for a in w.interface_theme_actions.values()),1)
            self.assertEqual((g.board.fen(),g.light_square,g.dark_square,g.background_color),original)
        self.assertEqual(len(styles),5)
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
                         ["Game","View","Engine","Settings","Help"])
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
        self.assertEqual(main.glGetError(),main.GL_NO_ERROR)
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

    def test_new_game_clocks_wait_for_first_legal_move(self):
        g = self.game
        for mode in ("Online","OTB"):
            g.clock_mode_var.set(mode)
            g.start_game()
            initial = (g.white_time,g.black_time)
            with patch.object(main.time,"perf_counter",return_value=g.last_clock_tick+30):
                g.update_clock()
            self.assertEqual((g.white_time,g.black_time),initial)
            self.assertFalse(g.try_move(chess.E2,chess.E5))
            with patch.object(main.time,"perf_counter",return_value=g.last_clock_tick+30):
                g.update_clock()
            self.assertEqual((g.white_time,g.black_time),initial)
            with patch.object(g,"play_game_sound"):
                self.assertTrue(g.try_move(chess.E2,chess.E4))
            before = (g.white_time,g.black_time)
            with patch.object(main.time,"perf_counter",return_value=g.last_clock_tick+2):
                g.update_clock()
            expected = (before[0]-2,before[1]) if mode == "OTB" else (before[0],before[1]-2)
            self.assertEqual((g.white_time,g.black_time),expected)

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
        self.assertEqual(main.load_config()["custom_increment"],3)
        self.assertEqual((g.white_time,g.black_time,g.increment),(125,125,3))
        self.assertEqual(w.white_clock.digits.text(),g.fmt_clock(125))

    def test_clock_settings_preserve_paused_game(self):
        w,g = self.window,self.game
        g.start_game()
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
        engine.analyse.return_value = {"score":chess.engine.PovScore(chess.engine.Cp(34),chess.WHITE),
                                      "depth":12,"pv":[chess.Move.from_uci("e2e4")]}
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
        self.assertEqual(w.engine_line.toPlainText(),"e4")
        g.analysis_enabled = False
        g.board.push_uci("d2d4")
        w.tick()
        self.assertEqual(w.engine_line.toPlainText(),"")
        g.pending_engine_position = chess.STARTING_FEN
        g.pending_engine_move = chess.Move.from_uci("d7d5")
        g.apply_pending_engine_move()
        self.assertEqual(len(g.board.move_stack),1)

    def test_layout_preferences_persist_on_close(self):
        self.window.resize(1100,720)
        self.window.focus_action.trigger()
        self.window.engine_toggle.setChecked(True)
        self.qt.processEvents()
        self.window.close()
        cfg = main.load_config()
        self.assertEqual(cfg["window_size"],[1100,720])
        self.assertTrue(cfg["focus_mode"])
        self.assertTrue(cfg["engine_panel_open"])

    def test_uci_subprocess_play_and_analysis_output(self):
        w,g = self.window,self.game
        fixture = Path(__file__).parent/"fixtures"/"uci_stub.py"
        g.engine_manager.engine = chess.engine.SimpleEngine.popen_uci([sys.executable,str(fixture)])
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
