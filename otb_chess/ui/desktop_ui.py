"""Single-window desktop UI. Game logic and rendering live in dedicated modules."""

from otb_chess.chess_backend import notation
from otb_chess.chess_backend import rules as chess

import math
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QSurfaceFormat, QShortcut
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QFormLayout, QComboBox,
    QDoubleSpinBox, QSpinBox, QAbstractSpinBox, QDialogButtonBox, QFileDialog, QColorDialog,
    QMessageBox, QPlainTextEdit, QSlider, QSizePolicy,
)

from otb_chess.core.game import Chess3D
from otb_chess.core.evaluation import evaluate_position
from otb_chess.services.settings import TIME_CONTROLS, TimeControl, ENGINE_DIR, BOOK_DIR, APP_DIR
from otb_chess.graphics.gl_primitives import setup_gl
from otb_chess.version import __version__
from otb_chess.ui.interface_themes import THEMES, themed_stylesheet
from otb_chess.ui.document_actions import DocumentActions
from otb_chess.graphics.board_types import BOARD_TYPES
from otb_chess.graphics.board_colors import BOARD_COLOR_THEMES
from otb_chess.ui.licenses_dialog import show_licenses
from otb_chess.ui.chess_symbols import promotion_icon, flag_icon, clock_engine_label
from otb_chess.ui.variation_preview import VariationPreview
from otb_chess.ui.engine_analysis import EngineAnalysisWindow


STYLE = """
QMainWindow, QDialog { background: #171b22; color: #e8eaf0; }
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #e8eaf0; }
QMenuBar { background: #1e242e; padding: 5px 12px; }
QMenuBar::item { padding: 7px 14px; border-radius: 4px; }
QMenuBar::item:selected, QMenu::item:selected { background: #384354; }
QMenu { background: #242c38; border: 1px solid #414b5b; padding: 6px; }
QMenu::item { padding: 7px 26px; }
QMenu::separator { height: 1px; background: #414b5b; margin: 5px; }
QWidget#sidebar { background: #1b212b; }
QLabel#section { color: #a3afc1; font-size: 11px; font-weight: 600; }
QLabel#hint { color: #a3afc1; font-size: 12px; }
QPushButton, QToolButton { background: #2b3543; border: 1px solid #3b4759;
    border-radius: 6px; padding: 8px 12px; }
QPushButton:hover, QToolButton:hover { background: #39475b; }
QPushButton:disabled { color: #748095; }
QPushButton#moveNavigation, QPushButton#humanGameAction { background: transparent; border: none;
    border-radius: 3px; padding: 2px; font-size: 12px; }
QPushButton#moveNavigation:hover, QPushButton#humanGameAction:hover { background: #39475b; }
QPushButton#primary { background: #d5944a; color: #161a20; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #e5a65c; }
QPushButton#clock { background: #252e3a; border: 2px solid #364152; padding: 8px; }
QPushButton#clock[active="true"] { background: #333127; border: 2px solid #e5a65c; }
QPushButton#clock[waiting="true"] { border: 2px solid #80bfab; }
QLabel#clockDigits { font-family: 'Consolas'; font-size: 39px; font-weight: 600; }
QTableWidget { background: #1b212b; alternate-background-color: #202834;
    border: none; selection-background-color: #364253; gridline-color: #303a49; }
QTreeWidget { background: #1b212b; border: none; selection-background-color: #364253; }
QTreeWidget::item { padding: 4px 0px; }
QTreeWidget::item:selected { background: #364253; color: #e8eaf0; }
QTableWidget::item { padding: 6px; }
QHeaderView::section { background: #1b212b; color: #a3afc1; border: none;
    padding: 9px 4px; font-size: 11px; font-weight: 600; }
QSplitter::handle { background: #303a49; width: 4px; }
QStatusBar { background: #1e242e; color: #a3afc1; }
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QPlainTextEdit {
    background: #111720; border: 1px solid #414b5b; border-radius: 4px; padding: 7px; }
QComboBox QAbstractItemView { background: #242c38; selection-background-color: #414b5b; }
QScrollBar:vertical { background: #1b212b; width: 10px; }
QScrollBar::handle:vertical { background: #4a5668; min-height: 24px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


class Value:
    """UI-independent setting cell used by the existing game controller."""
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class DesktopGame(VariationPreview, Chess3D):
    def __init__(self, widget):
        super().__init__(render_widget=widget)
        self.owner = widget.owner
        for name, value in {
            "time_control": self.cfg["time_control"], "engine_side": self.cfg["engine_side"],
            "engine": self.cfg["engine_path"], "book": self.cfg["book_path"],
            "clock_mode": self.clock_mode, "clock_binding": self.clock_binding,
            "custom_initial": self.cfg["custom_initial"],
            "custom_increment": self.cfg["custom_increment"], "board_mode": self.board_mode,
            "piece_description": "", "background": "",
        }.items():
            setattr(self, name + "_var", Value(value))
        self.engine_output = None
        self.engine_loading = False
        self.engine_load_result = None
        self.analysis_engine = None
        self.analysis_lock = threading.Lock()
        self.analysis_revision = 0
        self.analysis_busy = False
        self.analysis_enabled = bool(self.cfg.get("analysis_enabled", False))
        self.analysis_stamp = 0
        self.closed = False

    def choose_promotion(self, color, square):
        dialog = QDialog(self.owner)
        dialog.setObjectName("promotionDialog")
        dialog.setWindowTitle("Pawn promotion")
        layout = QVBoxLayout(dialog)
        name = chr(ord('a') + chess.square_file(square)) + str(chess.square_rank(square) + 1)
        layout.addWidget(QLabel(f"Promote {'White' if color else 'Black'}'s pawn on {name} to:"))
        row = QHBoxLayout()
        selected = None
        def choose(piece_type):
            nonlocal selected
            selected = piece_type
            dialog.accept()
        for label, piece_type in (("Queen", chess.QUEEN), ("Rook", chess.ROOK),
                                  ("Bishop", chess.BISHOP), ("Knight", chess.KNIGHT)):
            button = QPushButton()
            button.setIcon(promotion_icon(self, piece_type, color))
            button.setIconSize(QSize(64, 64))
            button.setFixedSize(82, 82)
            button.setAccessibleName(label)
            button.setObjectName("promote" + label)
            button.setDefault(piece_type == chess.QUEEN)
            button.clicked.connect(lambda _, p=piece_type: choose(p))
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        self.drag_piece = self.drag_world = None
        self.was_drag = False
        return selected if dialog.exec() == QDialog.DialogCode.Accepted else None

    def try_move(self, fr, to, is_engine=False, promotion=None):
        moved = super().try_move(fr,to,is_engine,promotion=promotion)
        if moved:
            self.owner.sync_engine_output()
            self.owner.session.save(self,force=True)
        return moved

    def refresh_move_list(self):
        if hasattr(self.owner, "moves"):
            self.owner.refresh_moves()

    def selected_time_control(self):
        name = self.time_control_var.get()
        if name != "Custom":
            return TIME_CONTROLS.get(name, TIME_CONTROLS["Bullet 2+1"])
        initial, increment = float(self.custom_initial_var.get()), float(self.custom_increment_var.get())
        if not math.isfinite(initial) or not math.isfinite(increment) or initial <= 0 or increment < 0:
            QMessageBox.warning(self.owner, "Time control", "Enter a positive duration and a nonnegative increment.")
            return None
        return TimeControl("Custom", initial, increment)

    def choose_set(self, key):
        try:
            self.make_context_current()
            self.piece_renderer.prepare(self.piece_sets[key])
        except Exception as exc:
            QMessageBox.warning(self.owner, "Piece set", str(exc))
            self.owner.set_actions[self.piece_set].setChecked(True)
            return
        self.piece_set = key
        self.persist()

    def request_analysis(self):
        if (self.closed or not self.analysis_enabled or self.analysis_busy
                or self.owner.new_game_pending or self.owner.pending_difficulty is not None):
            return
        board = chess.snapshot_history(self.board)
        token = self.analysis_position_token()
        revision = self.analysis_revision
        options = dict(self.cfg.get("analysis_options", {}))
        self.analysis_busy = True
        self.analysis_stamp = time.perf_counter()

        def worker():
            try:
                with self.analysis_lock:
                    if self.closed or not self.analysis_enabled or revision != self.analysis_revision:
                        return
                    if self.analysis_engine is None:
                        from otb_chess.chess_backend import uci
                        path = next(iter(sorted(ENGINE_DIR.rglob("stockfish*.exe"))), None)
                        if path is None:
                            raise RuntimeError("Stockfish is unavailable in the engines folder.")
                        self.analysis_engine = uci.Engine.open(str(path))
                    if self.closed or not self.analysis_enabled or revision != self.analysis_revision:
                        return
                    info = self.analysis_engine.analyse_variations(board, **options)
                    if (not self.closed and self.analysis_enabled and revision == self.analysis_revision
                            and token == self.analysis_position_token()):
                        self.engine_output_token = token
                        self.engine_output = (board.final_fen, info, None)
            except Exception as exc:
                if not self.closed and revision == self.analysis_revision and token == self.analysis_position_token():
                    self.engine_output_token = token
                    self.engine_output = (board.final_fen, None, str(exc))
            finally:
                self.analysis_busy = False

        threading.Thread(target=worker, daemon=True).start()

    def load_engine_path(self, path):
        if getattr(self.owner, "bookmark_pending", None) is not None:
            return
        if self.engine_loading or self.engine_manager.thinking or self.analysis_busy:
            self.result_text = "Wait for the current engine search to finish."
            return
        self.engine_loading = True
        self.engine_output = None
        self.result_text = "Loading engine…"

        def worker():
            if path:
                result = self.engine_manager.load(path)
            else:
                self.engine_manager.unload()
                result = (True, "Engine unloaded")
            self.engine_load_result = (path, result)
            self.engine_loading = False

        threading.Thread(target=worker, daemon=True).start()


class BoardWidget(QOpenGLWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.ready = False
        self.cleaned = False
        self.setMinimumSize(320, 280)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.game = DesktopGame(self)

    def initializeGL(self):
        g = self.game
        setup_gl(max(1, self.width()), max(1, self.height()))
        try:
            g.piece_renderer.prepare(g.piece_sets[g.piece_set])
        except Exception as exc:
            g.piece_set = "club"
            g.piece_renderer.prepare(g.piece_sets["club"])
            g.result_text = f"Using Classic Club: {exc}"
        if g.background_image_path:
            if not g.load_background_image(g.background_image_path, show_error=False):
                g.background_image_path = ""
                g.result_text = "Saved background image was not available"
        self.ready = True

    def resizeGL(self, width, height):
        ratio = self.devicePixelRatioF()
        self.game.width, self.game.height = max(1, round(width*ratio)), max(1, round(height*ratio))
        setup_gl(self.game.width, self.game.height)

    def paintGL(self):
        if self.ready:
            self.game.draw()

    def wheelEvent(self, event):
        g = self.game
        dy = event.angleDelta().y()/120
        if g.board_mode == "2D":
            g.two_d_scale = max(.4, min(2.5, g.two_d_scale*math.exp(-max(-10,min(10,dy))*.1)))
        else:
            g.distance = max(7, min(22, g.distance-dy*.7))
        g.mark_camera_dirty()
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if not self.ready:
            return
        self.setFocus()
        self.makeCurrent()
        g = self.game
        pos = (event.position().x(), event.position().y())
        bindings = {Qt.MouseButton.RightButton: "Right Mouse", Qt.MouseButton.MiddleButton: "Middle Mouse", Qt.MouseButton.BackButton: "Mouse Button 4",
                    Qt.MouseButton.ForwardButton: "Mouse Button 5"}
        if event.button() == Qt.MouseButton.RightButton and g.selected is not None:
            g.cancel_selection()
        elif g.clock_mode == "OTB" and bindings.get(event.button()) == g.clock_binding:
            g.hit_clock()
        elif event.button() == Qt.MouseButton.RightButton or (
                event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            g.right_drag = True
            g.last_mouse = pos
        elif event.button() == Qt.MouseButton.LeftButton:
            g.left_press(pos)
        self.update()

    def mouseMoveEvent(self, event):
        if not self.ready:
            return
        self.makeCurrent()
        g = self.game
        pos = (event.position().x(), event.position().y())
        g.hover_square = g.square_at_mouse(pos)
        if g.right_drag:
            if g.board_mode == "3D":
                g.yaw += (pos[0]-g.last_mouse[0])*.009
                g.pitch = max(math.radians(14),min(math.radians(72),g.pitch+(pos[1]-g.last_mouse[1])*.007))
                g.mark_camera_dirty()
            g.last_mouse = pos
        elif event.buttons() & Qt.MouseButton.LeftButton:
            g.left_motion(pos)
        self.update()

    def leaveEvent(self, event):
        self.game.hover_square = None
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.ready:
            return
        self.makeCurrent()
        g = self.game
        if g.right_drag:
            g.right_drag = False
            g.mark_camera_dirty()
        elif event.button() == Qt.MouseButton.LeftButton:
            g.left_release((event.position().x(),event.position().y()))
        self.update()

    def cleanup(self):
        if self.cleaned or not self.ready:
            return
        self.makeCurrent()
        self.game.delete_background_texture()
        self.game.board_surface_renderer.close()
        self.game.piece_renderer.close()
        self.game.flat_piece_renderer.close()
        self.doneCurrent()
        self.cleaned = True


class ClockCard(QPushButton):
    def __init__(self, name, color, owner):
        super().__init__()
        self.setObjectName("clock")
        self.setMinimumHeight(106)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.color = color
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        row = QHBoxLayout()
        self.name = QLabel(name.upper())
        self.name.setObjectName("section")
        self.engine_label = QLabel("")
        self.engine_label.setObjectName("hint")
        self.engine_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.state = QLabel("")
        self.state.setObjectName("hint")
        row.addWidget(self.name)
        row.addWidget(self.engine_label, 1)
        layout.addLayout(row)
        self.digits = QLabel("0:00")
        self.digits.setObjectName("clockDigits")
        time_row = QHBoxLayout()
        time_row.addWidget(self.digits)
        self.fallen_flag = QLabel()
        self.fallen_flag.setObjectName("fallenFlag")
        self.fallen_flag.setPixmap(flag_icon().pixmap(28, 28))
        self.fallen_flag.setAccessibleName("Time expired")
        self.fallen_flag.setToolTip("Time expired")
        self.fallen_flag.hide()
        time_row.addWidget(self.fallen_flag)
        time_row.addStretch()
        layout.addLayout(time_row)
        layout.addWidget(self.state)
        for widget in (self.name,self.engine_label,self.state,self.digits,self.fallen_flag):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.clicked.connect(lambda: owner.edit_clock(color) if owner.game.clocks_editable() else owner.hit_clock(color))
        self.setToolTip("In OTB mode, click the running clock after making your move.")

    def refresh(self, game):
        remaining = game.white_time if self.color else game.black_time
        self.digits.setText(game.fmt_clock(remaining))
        label = clock_engine_label(game, self.color)
        self.engine_label.setToolTip(label)
        self.engine_label.setText(self.engine_label.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, self.engine_label.width()))
        background = self.palette().color(self.backgroundRole())
        if getattr(self, "_flag_background", None) != background.name():
            self._flag_background = background.name()
            self.fallen_flag.setPixmap(flag_icon(background).pixmap(28, 28))
        self.fallen_flag.setVisible(game.game_over and remaining <= 0)
        active = game.game_started and not game.game_over and game.active_clock_color == self.color
        waiting = active and game.awaiting_clock_press
        editable = game.clocks_editable()
        first_move = game.game_started and not game.game_over and not game.board.move_stack
        self.state.setText("CLICK TO EDIT" if editable else "WAITING FOR MOVE" if first_move else "PRESS CLOCK" if waiting else "RUNNING" if active else "")
        self.setToolTip("Click to adjust this clock before the first move or while paused." if editable else "In OTB mode, click the running clock after making your move.")
        self.setCursor(Qt.CursorShape.PointingHandCursor if editable else Qt.CursorShape.ArrowCursor)
        if self.property("active") != active or self.property("waiting") != waiting:
            self.setProperty("active",active)
            self.setProperty("waiting",waiting)
            self.style().unpolish(self)
            self.style().polish(self)


class MainWindow(DocumentActions, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"OTBMaster3D v{__version__}")
        self.setMinimumSize(760,560)
        self.setStyleSheet(STYLE)
        self.board_widget = BoardWidget(self)
        self.game = self.board_widget.game
        from otb_chess.services.session import SessionStore
        self.session = SessionStore()
        self.session.restore(self.game)
        cfg = self.game.cfg
        self.interface_theme = cfg.get("interface_theme","Dark")
        if self.interface_theme not in THEMES:
            self.interface_theme = "Dark"
        self.setStyleSheet(themed_stylesheet(STYLE,self.interface_theme))
        size = cfg.get("window_size",[1280,840])
        self.resize(max(760,min(3840,int(size[0]))),max(560,min(2160,int(size[1]))))
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.board_widget)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(520)
        self.splitter.addWidget(self.sidebar)
        self.splitter.setStretchFactor(0,1)
        self.splitter.setStretchFactor(1,0)
        self.sidebar_width = max(250,min(520,int(cfg.get("sidebar_width",300))))
        self.splitter.setSizes([self.width()-self.sidebar_width,self.sidebar_width])
        self.setCentralWidget(self.splitter)
        self.build_sidebar()
        self.build_menus()
        for key, callback in (('Left', lambda: self.engine_panel.step(-1)),
                              ('Right', lambda: self.engine_panel.step(1)),
                              ('Escape', self.engine_panel.return_to_current)):
            shortcut = QShortcut(QKeySequence(key), self.board_widget)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
        self.refresh_moves()
        self.statusBar().setSizeGripEnabled(True)
        self.board_status = QLabel("")
        self.board_status.setObjectName("hint")
        self.statusBar().addPermanentWidget(self.board_status)
        self.focus_action.setChecked(bool(cfg.get("focus_mode",False)))
        self.sidebar_action.setChecked(bool(cfg.get("sidebar_visible",True)))
        self.engine_toggle.setChecked(bool(cfg.get("engine_panel_open",False)))
        self.apply_visibility()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        self.last_fen = None
        self.last_output = None
        self.last_search = None
        self.closing = False
        self.new_game_pending = False
        self.pending_difficulty = None
        self.bookmark_panel = None
        self.bookmark_pending = None
        remembered = self.game.engine_var.get()
        if remembered and Path(remembered).is_file():
            QTimer.singleShot(0,lambda: self.game.load_engine_path(remembered))

    def build_sidebar(self):
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(16,16,16,12)
        layout.setSpacing(10)
        self.preview_status = QLabel()
        self.preview_status.setWordWrap(True)
        self.preview_status.setStyleSheet('font-weight: bold; color: #d5944a;')
        self.preview_status.hide()
        label = QLabel("GAME CLOCK")
        label.setObjectName("section")
        clock_heading = QHBoxLayout()
        clock_heading.addWidget(label)
        self.game_status = QLabel()
        self.game_status.setObjectName("gameStatus")
        self.game_status.setWordWrap(True)
        self.game_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        clock_heading.addWidget(self.game_status, 1)
        layout.addLayout(clock_heading)
        layout.addWidget(self.preview_status)
        self.black_clock = ClockCard("Black",chess.BLACK,self)
        self.white_clock = ClockCard("White",chess.WHITE,self)
        layout.addWidget(self.white_clock)
        layout.addWidget(self.black_clock)
        from otb_chess.ui.material import CapturedPieces
        self.captured_white = CapturedPieces()
        self.captured_black = CapturedPieces()
        self.captured_white.setToolTip("Captured by White")
        self.captured_black.setToolTip("Captured by Black")
        self.material_balance = QLabel()
        self.material_row = QHBoxLayout()
        self.material_row.setSpacing(4)
        self.material_row.addWidget(self.captured_white, 1)
        divider = QLabel("|")
        divider.setObjectName("hint")
        self.material_row.addWidget(divider)
        self.material_row.addWidget(self.captured_black, 1)
        self.material_row.addWidget(self.material_balance)
        layout.addLayout(self.material_row)
        self.material_balance.setToolTip(
            "White minus Black material: pawn 1, knight/bishop 3, rook 5, queen 9.\n"
            "Captured pieces are counted from recorded moves; promotions affect the balance.")
        self._material_position = None
        self.refresh_material()
        self.engine_enabled_button = QPushButton()
        self.engine_enabled_button.setObjectName("engineEnabled")
        self.engine_enabled_button.setCheckable(True)
        self.engine_enabled_button.setChecked(self.game.engine_enabled)
        self.engine_enabled_button.toggled.connect(self.game.set_engine_enabled)
        self.engine_enabled_button.setText("Engine on" if self.game.engine_enabled else "Engine off - free play")
        layout.addWidget(self.engine_enabled_button)
        self.game_actions_row = QWidget()
        actions = QHBoxLayout(self.game_actions_row)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(3)
        self.clock_actions = {}
        for key, symbol in (("resign", "⚑"), ("draw", "="), ("claim_draw", "½"), ("takeback", "−"), ("switch_sides", "⇄")):
            button = QPushButton(symbol)
            button.setObjectName("humanGameAction")
            button.setFixedSize(28, 24)
            button.setStyleSheet("QPushButton#humanGameAction { font-size: 18px; } QToolTip { font-size: 12px; padding: 4px 6px; }")
            button.clicked.connect(lambda checked=False, action=key: self.invoke(self.human_game_action, action))
            self.clock_actions[key] = button
            actions.addWidget(button)
        actions.addStretch()
        layout.addWidget(self.game_actions_row)
        self.refresh_game_actions()
        self.clock_summary = QLabel("")
        self.clock_summary.setObjectName("hint")
        layout.addWidget(self.clock_summary)
        self.play_button = QPushButton("Start game")
        self.play_button.setObjectName("primary")
        self.play_button.clicked.connect(self.play_pause)
        layout.addWidget(self.play_button)
        self.moves_panel = QWidget()
        moves_layout = QVBoxLayout(self.moves_panel)
        moves_layout.setContentsMargins(0,10,0,0)
        navigation = QHBoxLayout()
        navigation.setSpacing(3)
        self.move_navigation = {}
        for symbol,description in (("<<","Go to the beginning of the game"),
                                   ("<","Move back"),(">","Move forward"),
                                   (">>","Go to the end of the game")):
            button = QPushButton(symbol)
            button.setObjectName("moveNavigation")
            button.setFixedSize(28,24)
            button.setToolTip(description + " (pause the clock first)")
            button.setAccessibleName(description)
            button.clicked.connect(lambda checked=False,step=symbol:self.navigate_history(step))
            navigation.addWidget(button)
            self.move_navigation[symbol] = button
        navigation.addStretch()
        moves_layout.addLayout(navigation)
        label = QLabel("MOVE LIST")
        label.setObjectName("section")
        move_heading = QHBoxLayout()
        move_heading.addWidget(label)
        self.move_list_evaluation = QLabel()
        self.move_list_evaluation.setObjectName("moveListEvaluation")
        self.move_list_evaluation.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.move_list_evaluation.setWordWrap(True)
        move_heading.addWidget(self.move_list_evaluation, 1)
        moves_layout.addLayout(move_heading)
        self.moves = QTableWidget(0,3)
        self.moves.setHorizontalHeaderLabels(["#","WHITE","BLACK"])
        self.moves.verticalHeader().hide()
        self.moves.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        self.moves.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.moves.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.moves.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.moves.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.moves.cellClicked.connect(self.navigate_move)
        self.moves.setToolTip("Pause the clock, then click a move to review its position.")
        self.moves.setAlternatingRowColors(True)
        self.moves.setShowGrid(False)
        self.moves.setMinimumHeight(90)
        moves_layout.addWidget(self.moves,1)
        layout.addWidget(self.moves_panel,1)
        self.static_evaluation = QLabel()
        self.static_evaluation.setObjectName("staticEvaluation")
        self.static_evaluation.setWordWrap(True)
        self.static_evaluation.setToolTip(
            "Instant estimate of the displayed board: material, piece placement and pawn structure.\n"
            "No engine or move search. Values are in pawns.\n"
            "Tactical threats can make the engine's evaluation different.")
        self.move_list_evaluation.setToolTip(self.static_evaluation.toolTip())
        self.engine_toggle = QAction("Engine Analysis", self)
        self.engine_toggle.setCheckable(True)
        self.engine_toggle.toggled.connect(self.set_analysis_window_visible)
        self.engine_panel = EngineAnalysisWindow(self)
        engine_layout = self.engine_panel.content_layout
        engine_layout.addWidget(self.static_evaluation)
        self.engine_name = QLabel("No engine loaded")
        self.engine_name.setObjectName("hint")
        self.engine_name.setWordWrap(True)
        engine_layout.addWidget(self.engine_name)
        self.analysis_button = QPushButton("Stop analysis" if self.game.analysis_enabled else "Start analysis")
        self.analysis_button.setObjectName("toggleEngineAnalysis")
        self.analysis_button.setCheckable(True)
        self.analysis_button.setChecked(self.game.analysis_enabled)
        self.analysis_button.setEnabled(True)
        self.analysis_button.setToolTip(
            "Start or stop automatic line calculation. The current short search may finish.\n"
            "Static evaluation stays active; the engine still plays its turns.")
        self.analysis_button.clicked.connect(lambda enabled: self.invoke(self.toggle_analysis, enabled))
        engine_layout.addWidget(self.analysis_button)
        self.engine_metrics = QLabel("Enable analysis from the Engine menu.")
        self.engine_metrics.setWordWrap(True)
        engine_layout.addWidget(self.engine_metrics)
        self.engine_line = self.engine_panel.line_view
        self.engine_panel.finish_layout()
        self.focus_spacer = QWidget()
        layout.addWidget(self.focus_spacer,1)

    def action(self, menu, text, callback, shortcut=None, checkable=False, checked=False):
        action = QAction(text,self)
        action.setCheckable(checkable)
        if checkable:
            action.setChecked(checked)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda checked=False: self.invoke(callback,checked) if checkable else self.invoke(callback))
        menu.addAction(action)
        return action

    def invoke(self, callback, *args):
        if self.board_widget.ready:
            self.board_widget.makeCurrent()
        callback(*args)
        self.session.save(self.game,force=True)
        self.board_widget.update()

    def build_menus(self):
        g = self.game
        game = self.menuBar().addMenu("Game")
        self.action(game,"New game…",self.new_game,"Ctrl+N")
        self.setup_position_action = self.action(game,"Setup Position…",self.setup_position)
        self.action(game,"Start / pause clock",self.play_pause,"Ctrl+P")
        self.action(game,"Press OTB clock",lambda: self.hit_clock(),"Space")
        game.addSeparator()
        self.action(game,"Take back",g.takeback,"U")
        self.switch_sides_action = self.action(game,"Switch sides",lambda: self.human_game_action("switch_sides"))
        self.action(game,"Go to starting position",lambda:g.navigate_to_ply(0))
        self.action(game,"Return to latest move",g.return_to_live)
        self.action(game,"Resign…",self.resign)
        self.action(game,"Offer draw",g.offer_draw)
        self.action(game,"Claim draw",self.prompt_draw_claim)
        self.action(game,"Reset board…",self.reset_board)
        self.action(game,"Reset clock…",self.reset_clock)
        game.addSeparator()
        self.action(game,"Quit",self.close,"Ctrl+Q")
        self.build_file_menu()
        view = self.menuBar().addMenu("View")
        modes = QActionGroup(self)
        self.mode_actions = {}
        for mode in ("3D","2D"):
            act = self.action(view,f"{mode} board",lambda _,m=mode: self.set_mode(m),checkable=True,checked=g.board_mode==mode)
            modes.addAction(act)
            self.mode_actions[mode] = act
        pieces = view.addMenu("3D piece set")
        group = QActionGroup(self)
        self.set_actions = {}
        for key,spec in g.piece_sets.items():
            act = self.action(pieces,spec.name,lambda _,k=key: g.choose_set(k),checkable=True,checked=g.piece_set==key)
            group.addAction(act)
            self.set_actions[key] = act
        from otb_chess.graphics.board_2d import FLAT_SETS
        flat_pieces = view.addMenu("2D piece set")
        flat_group = QActionGroup(self)
        self.flat_set_actions = {}
        for key,name in FLAT_SETS.items():
            act = self.action(flat_pieces,name,lambda _,k=key:self.set_option("flat_piece_set",k),
                              checkable=True,checked=g.flat_piece_set==key)
            flat_group.addAction(act)
            self.flat_set_actions[key] = act
        view.addSeparator()
        self.action(view,"Flip board",g.flip_board,"Ctrl+F")
        self.action(view,"Reset view",g.reset_view,"Ctrl+R")
        self.action(view,"Coordinates",lambda v:self.set_option("show_coordinates",v),checkable=True,checked=g.show_coordinates)
        self.action(view,"Move indicator",lambda v:self.set_option("show_move_indicator",v),checkable=True,checked=g.show_move_indicator)
        view.addSeparator()
        self.sidebar_action = self.action(view,"Show sidebar",lambda _:self.apply_visibility(),"Ctrl+B",True,True)
        self.focus_action = self.action(view,"Focus mode (board and clocks)",lambda _:self.apply_visibility(),"Ctrl+Shift+F",True)
        self.fullscreen_action = self.action(view,"Fullscreen",self.set_fullscreen,"F11",True)
        from otb_chess.ui.bookmark_panel import BookmarkMenu
        self.bookmarks_menu = BookmarkMenu(self)
        engine = self.menuBar().addMenu("Engine")
        from otb_chess.services.difficulty import DIFFICULTIES
        difficulty = engine.addMenu("Difficulty")
        difficulty.setToolTipsVisible(True)
        difficulty_group = QActionGroup(self)
        self.difficulty_actions = {}
        for key,preset in DIFFICULTIES.items():
            action = self.action(difficulty,preset.label,lambda _,k=key:self.select_difficulty(k),
                                 checkable=True,checked=g.cfg.get("engine_difficulty")==key)
            action.setToolTip(preset.description)
            difficulty_group.addAction(action)
            self.difficulty_actions[key] = action
        self.custom_difficulty_action = self.action(difficulty,"Custom settings…",lambda _:self.engine_settings("custom"),
                                                    checkable=True,checked=g.cfg.get("engine_difficulty","custom")=="custom")
        difficulty_group.addAction(self.custom_difficulty_action)
        self.action(engine,"Engine and opening book…",self.engine_settings)
        self.analysis_action = self.action(engine,"Analyse position",self.toggle_analysis,"Ctrl+A",True,
                                           checked=g.analysis_enabled)
        self.action(engine,"Open Evaluation Graph",self.open_evaluation_graph)
        self.action(engine,"Engine Analysis",self.open_engine_analysis)
        self.static_evaluation_action = self.action(
            engine, "Always show static evaluation", self.toggle_static_evaluation,
            checkable=True, checked=bool(g.cfg.get("always_show_static_evaluation", False)))
        settings = self.menuBar().addMenu("Settings")
        self.action(settings,"Time control and clock…",self.clock_settings)
        self.action(settings,"Piece movement speed…",self.movement_settings)
        interface = settings.addMenu("Interface theme")
        theme_group = QActionGroup(self)
        self.interface_theme_actions = {}
        for name in THEMES:
            action = self.action(interface,name,lambda _,n=name:self.set_interface_theme(n),
                                 checkable=True,checked=name == self.interface_theme)
            theme_group.addAction(action)
            self.interface_theme_actions[name] = action
        types = settings.addMenu("Board Type")
        type_group = QActionGroup(self)
        self.board_type_actions = {}
        for key,spec in BOARD_TYPES.items():
            action = self.action(types,spec.name,lambda _,k=key:self.set_board_type(k),
                                 checkable=True,checked=g.board_type==key)
            type_group.addAction(action)
            self.board_type_actions[key] = action
        themes = settings.addMenu("Board Color Theme")
        for name in BOARD_COLOR_THEMES:
            self.action(themes,name,lambda n=name:g.apply_preset(n))
        colors = settings.addMenu("Colours")
        for name,key in (("Light squares","light"),("Dark squares","dark"),("Board frame","frame"),("Background","background")):
            self.action(colors,name+"…",lambda k=key:self.choose_color(k))
        from otb_chess.graphics.backgrounds import BACKGROUNDS
        background = settings.addMenu("Background")
        background_group = QActionGroup(self)
        self.background_actions = {}
        for key,name in BACKGROUNDS.items():
            action = self.action(background,name,lambda _,k=key:self.set_background_style(k),
                                 checkable=True,checked=not g.background_image_path and g.background_style==key)
            background_group.addAction(action)
            self.background_actions[key] = action
        background.aboutToShow.connect(self.refresh_background_actions)
        background.addSeparator()
        self.action(background,"Choose solid colour…",lambda:self.choose_color("background"))
        self.action(background,"Choose image…",self.choose_background)
        self.action(background,"Remove background image",self.clear_background)
        from otb_chess.services.audio import SOUND_PROFILES
        sounds = settings.addMenu("Sound profile")
        sound_group = QActionGroup(self)
        self.sound_profile_actions = {}
        for key,label in [(None,"No sounds"),*SOUND_PROFILES.items()]:
            action = self.action(sounds,label,lambda _,k=key:self.set_sound_profile(k),
                                 checkable=True,checked=(g.sound_enabled and g.sound_profile==key)
                                 if key is not None else not g.sound_enabled)
            sound_group.addAction(action)
            self.sound_profile_actions[key] = action
        self.menuBar().addMenu(self.bookmarks_menu)
        help_menu = self.menuBar().addMenu("Help")
        self.action(help_menu,"Open Source Licences",lambda:show_licenses(self))
        self.action(help_menu,"Controls",self.show_controls)
        self.action(help_menu,"About",lambda:QMessageBox.about(self,"OTBMaster3D",f"OTBMaster3D v{__version__}\n\nDesktop chess with 2D and 3D views.\nStaunton models: clarkerubber (MIT).\nSee assets/pieces/README.md for credits."))

    def movement_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Piece movement speed")
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Slower ←    Movement speed    → Instant"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setInvertedAppearance(True)
        slider.setInvertedControls(True)
        slider.setRange(0,1500)
        slider.setSingleStep(50)
        slider.setPageStep(250)
        slider.setValue(self.game.move_animation_ms)
        slider.setAccessibleName("Piece movement duration in milliseconds")
        layout.addWidget(slider)
        label = QLabel()
        def update_label(value):
            label.setText("Instant (default)" if value == 0 else f"{value/1000:.2f} seconds per move")
        slider.valueChanged.connect(update_label)
        update_label(slider.value())
        layout.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.game.move_animation_ms = slider.value()
            self.game.move_animation = None
            self.game.persist()
        dialog.deleteLater()

    def set_interface_theme(self, name):
        self.interface_theme = name if name in THEMES else "Dark"
        self.setStyleSheet(themed_stylesheet(STYLE,self.interface_theme))
        self.interface_theme_actions[self.interface_theme].setChecked(True)
        self.game.cfg["interface_theme"] = self.interface_theme
        self.game.persist()

    def set_mode(self, mode):
        self.game.board_mode_var.set(mode)
        self.game.change_board_mode()

    def set_board_type(self, key):
        if key in BOARD_TYPES:
            self.game.board_type = key
            self.game.persist()
            self.board_widget.update()

    def set_option(self, name, value):
        setattr(self.game,name,value)
        self.game.persist()

    def apply_visibility(self, *_):
        if not hasattr(self,"focus_action"):
            return
        focus = self.focus_action.isChecked()
        if self.sidebar.isVisible() and not self.sidebar_action.isChecked():
            self.sidebar_width = self.sidebar.width()
        self.sidebar.setVisible(self.sidebar_action.isChecked())
        self.moves_panel.setVisible(not focus)
        always_static = self.static_evaluation_action.isChecked()
        self.move_list_evaluation.setVisible(always_static)
        self.static_evaluation.setVisible(not always_static)
        self.focus_spacer.setVisible(focus)

    def toggle_static_evaluation(self, enabled):
        self.game.cfg["always_show_static_evaluation"] = enabled
        self.apply_visibility()
        self.game.persist()

    def set_fullscreen(self, enabled):
        self.showFullScreen() if enabled else self.showNormal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.fullscreen_action.setChecked(False)
            self.showNormal()
        else:
            super().keyPressEvent(event)

    def open_evaluation_graph(self):
        from otb_chess.ui.evaluation_graph import EvaluationGraph
        if not hasattr(self, "evaluation_graph"):
            self.evaluation_graph = EvaluationGraph(self)
        self.evaluation_graph.show()
        self.evaluation_graph.raise_()
        self.evaluation_graph.activateWindow()

    def navigate_history(self, step):
        current = len(self.game.board.move_stack)
        end = len(self.game.history_board().move_stack)
        target = {"<<":0,"<":max(0,current-1),">":min(end,current+1),">>":end}[step]
        self.game.navigate_to_ply(target)
        self.refresh_navigation()
        self.board_widget.update()

    def refresh_navigation(self):
        g = self.game
        current = len(g.board.move_stack)
        end = len(g.history_board().move_stack)
        self.setup_position_action.setEnabled(not end and not g.game_over and g._review_live is None)
        allowed = not (g.game_started and not g.game_over and not g.clock_paused and current)
        for symbol in ("<<","<"):
            self.move_navigation[symbol].setEnabled(allowed and current > 0)
        for symbol in (">",">>"):
            self.move_navigation[symbol].setEnabled(allowed and current < end)

    def refresh_moves(self):
        evaluation = evaluate_position(self.game.board).text
        self.static_evaluation.setText(f"Position evaluation: {evaluation}")
        self.move_list_evaluation.setText(evaluation)
        self.refresh_navigation()
        history = self.game.history_board()
        board = history.root()
        self.moves.setRowCount(0)
        current = None
        row = -1
        for ply,move in enumerate(history.move_stack,1):
            if row < 0 or board.turn == chess.WHITE:
                row += 1
                self.moves.insertRow(row)
                self.moves.setItem(row,0,QTableWidgetItem(str(board.fullmove_number)))
            column = 1 if board.turn == chess.WHITE else 2
            item = QTableWidgetItem(notation.san(board.fen(), chess.owned_move(move)))
            item.setData(Qt.ItemDataRole.UserRole,ply)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if ply == len(self.game.board.move_stack):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                current = item
            self.moves.setItem(row,column,item)
            board.push(move)
        if current:
            self.moves.scrollToItem(current)

    def hit_clock(self, color=None):
        g = self.game
        if g.clock_mode == "OTB" and (color is None or color == g.active_clock_color):
            g.hit_clock()

    def confirm(self, title, text):
        return QMessageBox.question(self,title,text) == QMessageBox.StandardButton.Yes

    def setup_position(self):
        g = self.game
        if g.history_board().move_stack or g.game_over or g._review_live is not None:
            g.result_text = "Choose New game before setting up a position."
            return
        if g.engine_loading or g.engine_manager.thinking or self.new_game_pending:
            g.result_text = "Wait for the engine operation to finish before setting up a position."
            return
        from otb_chess.ui.position_setup import PositionSetup
        dialog = PositionSetup(self,g.board.fen(en_passant='fen'), flipped=g.board_facing == 'black')
        dialog.orientation_changed.connect(lambda flipped: g.set_board_facing('black' if flipped else 'white'))
        timer_running = self.timer.isActive()
        self.timer.stop()
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                g.load_document(dialog.board)
                g.move_animation = None
                g.engine_output = None
                g.reset_clock()
                g.active_clock_color = g.board.turn
                g.result_text = "Position ready — press Start game."
                self.last_fen = self.last_output = self.last_search = None
                self.refresh_moves()
                self.session.save(g,force=True)
                self.board_widget.update()
        finally:
            dialog.deleteLater()
            if timer_running:
                self.timer.start()

    def new_game(self, starting_fen=None):
        g = self.game
        if self.new_game_pending:
            return
        if g.board.move_stack and not self.confirm("New game","Start a new game? The current moves will be cleared."):
            return
        self.new_game_pending = True
        self.pending_start_fen = starting_fen
        self.start_pending_game()

    def start_pending_game(self):
        if not self.new_game_pending:
            return
        g = self.game
        if (g.engine_loading or g.engine_manager.thinking or g.analysis_busy
                or g.engine_load_result is not None):
            g.result_text = "Starting a new game when the engine is ready…"
            return
        self.new_game_pending = False
        g.pending_engine_move = None
        g.pending_engine_position = None
        g.pending_engine_error = None
        g.engine_output = None
        g.last_engine_search = None
        g.move_animation = None
        g.cancel_selection()
        self.last_fen = self.last_output = self.last_search = None
        g.start_game(getattr(self,"pending_start_fen",None))
        self.pending_start_fen = None

    def play_pause(self):
        if not self.game.game_started or self.game.game_over:
            g = self.game
            starting_fen = (g.board.fen(en_passant='fen')
                            if not g.game_over and not g.history_board().move_stack else None)
            self.new_game(starting_fen)
        else:
            self.game.stop_clock()

    def human_player_color(self):
        g = self.game
        engine_side = g.engine_side if g.engine_enabled and g.engine_manager.engine is not None else None
        return not engine_side if engine_side is not None else g.board.turn

    def refresh_game_actions(self):
        g = self.game
        side = "White" if self.human_player_color() else "Black"
        for key, label in (("resign", f"Resign {side}"), ("draw", f"Offer draw as {side}"),
                           ("claim_draw", "Claim draw in the current position"),
                           ("takeback", "Take back one move"), ("switch_sides", "Switch sides and pause")):
            button = self.clock_actions[key]
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setEnabled(self.can_switch_sides() if key == "switch_sides"
                              else not g.game_over and g._review_live is None if key == "claim_draw"
                              else bool(g.history_board().move_stack) if key == "takeback"
                              else g.game_started and not g.game_over)

        if hasattr(self, "switch_sides_action"):
            self.switch_sides_action.setEnabled(self.can_switch_sides())
        reason = g.result_text
        if g.game_over:
            if reason.startswith('Draw -') or g._declared_result == '1/2-1/2':
                status = 'Game Drawn'
            else:
                status = reason.replace('resigned', 'Resigned').replace('wins on time', 'Wins on Time')
        elif g._review_live is not None:
            status = 'Reviewing'
        elif reason == 'Draw offered':
            status = 'Draw Offered'
        elif g.board.is_check():
            status = 'Check'
        elif g.game_started:
            status = 'Paused' if g.clock_paused else 'Playing'
        else:
            status = 'Ready'
        self.game_status.setText(status)
        self.game_status.setToolTip(reason)

    def can_switch_sides(self):
        g = self.game
        return (g.engine_enabled and g.engine_side is not None and g.engine_manager.engine is not None
                and not g.game_over and not g.engine_loading
                and not getattr(self, "new_game_pending", False)
                and getattr(self, "bookmark_pending", None) is None)

    def human_game_action(self, action):
        g = self.game
        if action == "switch_sides":
            if self.can_switch_sides():
                g.switch_sides()
                self.white_clock.refresh(g)
                self.black_clock.refresh(g)
        elif action == "takeback":
            g.takeback()
        elif action == "resign":
            g.resign(self.human_player_color())
        elif action == "draw":
            g.offer_draw()
        elif action == "claim_draw":
            g.claim_draw()
        self.refresh_game_actions()

    def prompt_draw_claim(self):
        self.human_game_action("claim_draw")

    def resign(self):
        if self.game.game_started and self.confirm("Resign","Resign the current game?"):
            self.game.resign()

    def reset_board(self):
        if self.game.engine_manager.thinking or self.game.engine_loading or self.game.analysis_busy:
            self.game.result_text = "Wait for the current engine operation to finish."
            return
        if not self.game.board.move_stack or self.confirm("Reset board","Clear the current moves and reset the board?"):
            self.game.pending_engine_move = None
            self.game.last_engine_search = None
            self.game.engine_output = None
            self.game.reset_board()

    def reset_clock(self):
        if self.confirm("Reset clock","Reset both clocks to the selected time control?"):
            self.game.reset_clock()

    def edit_clock(self, color):
        g = self.game
        if not g.clocks_editable():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Adjust {'White' if color else 'Black'} clock")
        form = QFormLayout(dialog)
        remaining = max(0,math.ceil(g.white_time if color else g.black_time))

        def time_field(label, maximum, value):
            field = QSpinBox()
            field.setRange(0,maximum)
            field.setValue(value)
            field.setAccessibleName(label)
            field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            row = QHBoxLayout()
            row.addWidget(field,1)
            for text,step in (("−",-1),("+",1)):
                button = QPushButton(text)
                button.setFixedSize(40,36)
                button.setAutoDefault(False)
                button.setAutoRepeat(True)
                button.setAccessibleName(f"{'Increase' if step > 0 else 'Decrease'} {label.lower()}")
                button.clicked.connect(lambda checked=False,s=step: field.stepBy(s))
                row.addWidget(button)
            form.addRow(label,row)
            return field

        minutes = time_field("Minutes",1440,remaining // 60)
        seconds = time_field("Seconds",59,remaining % 60)
        form.addRow(QLabel("The game stays paused after saving." if g.clock_paused else "Clocks start after the first legal move."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted and g.clocks_editable():
            value = minutes.value()*60+seconds.value()
            if color:
                g.white_time = value
            else:
                g.black_time = value
            self.white_clock.refresh(g)
            self.black_clock.refresh(g)
        dialog.deleteLater()

    @staticmethod
    def time_control_panel_width():
        return 410

    def get_bookmark_panel(self):
        if self.bookmark_panel is None:
            from otb_chess.ui.bookmark_panel import BookmarkPanel
            self.bookmark_panel = BookmarkPanel(self)
        return self.bookmark_panel

    def toggle_bookmarks(self, visible):
        if visible:
            self.get_bookmark_panel().show_panel()
        elif self.bookmark_panel is not None:
            self.bookmark_panel.hide()

    def open_bookmark(self, node):
        from otb_chess.services.bookmark_actions import validate_restore
        try:
            validate_restore(node)
            if self.bookmark_pending is not None:
                raise ValueError("A bookmark is already opening.")
        except (ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Bookmarks", str(exc))
            return
        g = self.game
        g.update_clock()
        g.clock_paused = True
        self.new_game_pending = False
        self.pending_difficulty = None
        self.bookmark_pending = {"node": node, "analysis": g.analysis_enabled, "stage": "waiting"}
        g.analysis_enabled = False
        g.result_text = "Opening bookmark — clocks paused"
        self.board_widget.setEnabled(False)
        self.sidebar.setEnabled(False)
        self.menuBar().setEnabled(False)
        self.advance_bookmark_restore()

    def advance_bookmark_restore(self):
        pending = self.bookmark_pending
        g = self.game
        if pending["stage"] == "waiting":
            # Drain existing workers before discarding their results. No position
            # from an old search can arrive after the new board is installed.
            if g.engine_manager.thinking or g.analysis_busy:
                g.engine_manager.stop_search()
            if g.engine_loading or g.engine_manager.thinking or g.analysis_busy:
                return
            g.engine_load_result = None
            g.pending_engine_move = g.pending_engine_position = g.pending_engine_error = None
            g.engine_output = None
            pending["stage"] = "engine"
            def worker():
                try:
                    pending["result"] = g.engine_manager.restore_configuration(pending["node"].get("engine"))
                except Exception as exc:
                    pending["result"] = (False, str(exc))
            threading.Thread(target=worker, daemon=True).start()
            return
        if "result" not in pending:
            return
        try:
            from otb_chess.services.bookmark_actions import restore_bookmark
            self.board_widget.makeCurrent()
            restore_bookmark(g, pending["node"], pending["result"])
            self.last_fen = self.last_output = self.last_search = None
            self.engine_line.clear()
            self.refresh_moves()
            self.refresh_difficulty_actions()
            self.black_clock.refresh(g)
            self.white_clock.refresh(g)
            self.play_button.setText("Resume clock")
            self.clock_summary.setText(f"{g.time_control_var.get()} · {'Manual clock' if g.clock_mode == 'OTB' else 'Automatic clock'}")
            self.statusBar().showMessage(g.result_text)
            self.session.save(g, force=True)
        except Exception as exc:
            QMessageBox.warning(self, "Could not open bookmark", str(exc))
        finally:
            g.clock_paused = True
            g.analysis_enabled = pending["analysis"]
            self.bookmark_pending = None
            self.board_widget.setEnabled(True)
            self.sidebar.setEnabled(True)
            self.menuBar().setEnabled(True)
            self.board_widget.update()

    def clock_settings(self):
        g = self.game
        dialog = QDialog(self)
        dialog.setWindowTitle("Time control and clock")
        dialog.setMinimumWidth(self.time_control_panel_width())
        form = QFormLayout(dialog)
        preset = QComboBox()
        preset.addItems(list(TIME_CONTROLS)+["Custom"])
        preset.setCurrentText(g.time_control_var.get())
        initial,increment = QDoubleSpinBox(),QDoubleSpinBox()
        initial.setRange(.1,86400)
        increment.setRange(0,3600)
        initial.setValue(float(g.custom_initial_var.get()))
        increment.setValue(float(g.custom_increment_var.get()))
        initial.setSuffix(" sec")
        increment.setSuffix(" sec")
        mode = QComboBox()
        mode.addItems(["Online","OTB"])
        mode.setCurrentText(g.clock_mode_var.get())
        binding = QComboBox()
        binding.addItems(["Spacebar","Right Mouse","Middle Mouse","Mouse Button 4","Mouse Button 5"])
        binding.setCurrentText(g.clock_binding_var.get())
        form.addRow("Time control",preset)
        form.addRow("Initial time",initial)
        form.addRow("Increment",increment)
        form.addRow("Clock mode",mode)
        form.addRow("Clock input",binding)
        def custom_visibility():
            form.setRowVisible(initial,preset.currentText()=="Custom")
            form.setRowVisible(increment,preset.currentText()=="Custom")
        preset.currentTextChanged.connect(custom_visibility)
        custom_visibility()
        note = QLabel("Saved settings update idle clocks immediately.\nDuring a game, settings apply to the next game.\nOnline = automatic clock switching; OTB = press after moving.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for cell,value in ((g.time_control_var,preset.currentText()),(g.custom_initial_var,initial.value()),
                               (g.custom_increment_var,increment.value()),(g.clock_mode_var,mode.currentText()),
                               (g.clock_binding_var,binding.currentText())):
                cell.set(value)
            if not g.game_started or g.clocks_waiting_for_first_move():
                tc = g.selected_time_control()
                g.white_time = g.black_time = tc.initial_seconds
                g.increment = tc.increment_seconds
                g.clock_mode = g.clock_mode_var.get()
                g.clock_binding = g.clock_binding_var.get()
                self.white_clock.refresh(g)
                self.black_clock.refresh(g)
            g.persist()

    def refresh_difficulty_actions(self):
        key = self.pending_difficulty or self.game.cfg.get("engine_difficulty","custom")
        for name,action in self.difficulty_actions.items():
            action.setChecked(name == key)
        self.custom_difficulty_action.setChecked(key not in self.difficulty_actions)

    def select_difficulty(self, key):
        from otb_chess.services.difficulty import DIFFICULTIES, missing_files, engine_path
        g = self.game
        missing = missing_files(key)
        if missing:
            QMessageBox.warning(self,"Difficulty unavailable",", ".join(missing)+" is missing. Reinstall the bundled engines.")
            self.refresh_difficulty_actions()
            return
        if g.engine_loading or g.engine_manager.thinking or g.analysis_busy or g.engine_load_result is not None:
            self.pending_difficulty = key
            self.refresh_difficulty_actions()
            g.result_text = "Difficulty will change when the current engine operation finishes."
            return
        self.pending_difficulty = None
        preset = DIFFICULTIES[key]
        g.pending_engine_move = g.pending_engine_position = None
        g.pending_engine_error = g.engine_output = g.last_engine_search = None
        self.last_output = self.last_search = None
        g.cfg.update(engine_difficulty=key,engine_elo=preset.rating if preset.engine == "stockfish" else None,
                     engine_rating=preset.rating or 1500,engine_style="Balanced")
        g.book_var.set("")
        g.book_path = ""
        if g.engine_side_var.get() == "None":
            g.engine_side_var.set("Black")
        g.engine_side = chess.WHITE if g.engine_side_var.get() == "White" else chess.BLACK
        path = str(engine_path(key))
        g.engine_var.set(path)
        g.persist()
        self.refresh_difficulty_actions()
        g.load_engine_path(path)

    def engine_settings(self, initial_difficulty=None):
        g = self.game
        dialog = QDialog(self)
        dialog.setWindowTitle("Engine and opening book")
        dialog.setMinimumWidth(520)
        form = QFormLayout(dialog)
        from otb_chess.services.difficulty import DIFFICULTIES
        presets = QComboBox()
        presets.setObjectName("engineDifficulty")
        presets.addItem("Custom settings", "custom")
        for key,preset in DIFFICULTIES.items():
            presets.addItem(preset.label,key)
        presets.setCurrentIndex(max(0,presets.findData(initial_difficulty if initial_difficulty is not None
                                                      else g.cfg.get("engine_difficulty","custom"))))
        preset_note = QLabel("Choose a level to set the engine and strength automatically. Ratings are approximate practice levels.")
        preset_note.setWordWrap(True)
        form.addRow("Difficulty",presets)
        form.addRow(preset_note)
        engine = QComboBox()
        engine.setEditable(True)
        engine.addItems([""]+[str(p) for p in sorted(ENGINE_DIR.rglob("*.exe"))])
        engine.setCurrentText(g.engine_var.get())
        book = QComboBox()
        book.setEditable(True)
        book.addItems([""] + [str(p) for p in sorted(BOOK_DIR.glob("*.bin"))])
        book.setCurrentText(g.book_var.get())
        side = QComboBox()
        side.addItems(["None","White","Black"])
        side.setCurrentText(g.engine_side_var.get())
        def browse(widget, folder, file_filter):
            path,_ = QFileDialog.getOpenFileName(dialog,"Choose file",str(folder),file_filter)
            if path:
                widget.setCurrentText(path) if isinstance(widget,QComboBox) else widget.setText(path)
        for label,widget,folder,file_filter in (("UCI engine",engine,ENGINE_DIR,"Executables (*.exe);;All files (*)"),
                                               ("Opening book",book,BOOK_DIR,"Polyglot books (*.bin);;All files (*)")):
            row = QHBoxLayout()
            row.addWidget(widget,1)
            button = QPushButton("Browse…")
            button.clicked.connect(lambda _,w=widget,f=folder,t=file_filter:browse(w,f,t))
            row.addWidget(button)
            form.addRow(label,row)
        form.addRow("Engine plays",side)
        strength = QComboBox()
        strength.setObjectName("engineStrength")
        strength.addItems(["Full strength", "Limit rating"])
        strength.setCurrentIndex(0 if g.cfg.get("engine_elo") is None else 1)
        rating = QSpinBox()
        rating.setObjectName("engineRating")
        rating.setRange(0, 10000)
        rating.setValue(g.cfg.get("engine_elo") if g.cfg.get("engine_elo") is not None
                        else g.cfg.get("engine_rating", 1500))
        rating.setKeyboardTracking(False)
        def update_rating_enabled():
            rating.setEnabled(strength.isEnabled() and strength.currentIndex() == 1)
        def update_limits():
            loaded = g.engine_manager.engine
            limits = loaded.strength_range() if loaded and engine.currentText() == g.engine_manager.path else None
            strength.setEnabled(limits is not None)
            if limits:
                rating.setRange(*limits)
            update_rating_enabled()
        strength.currentIndexChanged.connect(update_rating_enabled)
        engine.currentTextChanged.connect(update_limits)
        update_limits()
        style = QComboBox()
        style.setObjectName("engineStyle")
        style.addItems(["Balanced", "Active", "Quiet"])
        style.setCurrentText(g.cfg.get("engine_style", "Balanced"))
        form.addRow("Strength", strength)
        form.addRow("Target rating", rating)
        form.addRow("Playing style", style)
        help_text = QLabel("Load an engine to see its supported rating range. Ratings are estimates.\n"
                           "Active favours checks/captures; Quiet favours quieter moves of similar value.\n"
                           "Styles need engine MultiPV support and can affect strength. Book moves bypass these controls.")
        help_text.setWordWrap(True)
        form.addRow(help_text)
        note = QLabel("Engine side and opening book apply to the next game.\nLeave the engine path empty to unload it.")
        note.setObjectName("hint")
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        def preset_changed():
            preset = DIFFICULTIES.get(presets.currentData())
            if preset:
                from otb_chess.services.difficulty import engine_path
                engine.setCurrentText(str(engine_path(presets.currentData()) or ""))
                book.setCurrentText("")
                rating.setRange(0,10000)
                rating.setValue(preset.rating or 1500)
                strength.setCurrentIndex(1 if preset.rating is not None else 0)
                style.setCurrentText("Balanced")
            for widget in (engine,book,strength,rating,style):
                widget.setEnabled(preset is None)
            if preset:
                preset_note.setText(preset.description+" Opening books are disabled for presets.")
            else:
                preset_note.setText("Custom engine settings. Ratings are estimates.")
                update_limits()
        presets.currentIndexChanged.connect(preset_changed)
        preset_changed()
        def accept():
            if g.engine_manager.thinking or g.engine_loading or g.analysis_busy:
                QMessageBox.information(dialog,"Engine busy","Wait for the current engine operation to finish.")
                return
            from otb_chess.services.difficulty import missing_files
            if presets.currentData() != "custom":
                if missing_files(presets.currentData()):
                    QMessageBox.warning(dialog,"Engine missing","Reinstall the bundled engines to use this preset.")
                    return
                dialog.accept()
                return
            for path in (engine.currentText().strip(),book.currentText().strip()):
                if path and not Path(path).is_file():
                    QMessageBox.warning(dialog,"File not found",path)
                    return
            dialog.accept()
        buttons.accepted.connect(accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            previous_difficulty = g.cfg.get("engine_difficulty","custom")
            g.engine_side_var.set(side.currentText())
            if presets.currentData() != "custom":
                self.select_difficulty(presets.currentData())
                dialog.deleteLater()
                return
            g.cfg["engine_difficulty"] = "custom"
            self.refresh_difficulty_actions()
            g.book_var.set(book.currentText().strip())
            if strength.isEnabled():
                rating.interpretText()
                g.cfg["engine_rating"] = rating.value()
                g.cfg["engine_elo"] = rating.value() if strength.currentIndex() else None
            g.cfg["engine_style"] = style.currentText()
            path = engine.currentText().strip()
            if (path != g.engine_manager.path or (path and g.engine_manager.engine is None)
                    or previous_difficulty != "custom"):
                g.load_engine_path(path)
            else:
                g.persist()
        self.refresh_difficulty_actions()

    def choose_color(self, which):
        g = self.game
        original = g.color_value(which)
        dialog = QColorDialog(QColor.fromRgbF(*original),self)
        dialog.setWindowTitle("Choose colour")
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog,True)

        def preview(color):
            if color.isValid():
                g.preview_background_color = which == "background"
                g.set_color_value(which,(color.redF(),color.greenF(),color.blueF()))
                self.board_widget.update()

        dialog.currentColorChanged.connect(preview)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                preview(dialog.currentColor())
                if which == "background":
                    self.board_widget.makeCurrent()
                    g.delete_background_texture()
                    g.background_image_path = ""
                    g.background_style = "solid"
            else:
                g.set_color_value(which,original)
        finally:
            g.preview_background_color = False
            self.board_widget.update()
            g.persist()
            dialog.deleteLater()

    def refresh_background_actions(self):
        for key,action in self.background_actions.items():
            action.setChecked(not self.game.background_image_path and self.game.background_style == key)

    def set_background_style(self, style):
        self.game.delete_background_texture()
        self.game.background_image_path = ""
        self.game.background_style = style
        self.game.persist()
        self.refresh_background_actions()
        self.board_widget.update()

    def choose_background(self):
        path,_ = QFileDialog.getOpenFileName(self,"Background image","","Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)")
        if path:
            self.board_widget.makeCurrent()
            if not self.game.load_background_image(path,show_error=False):
                QMessageBox.warning(self,"Background image","This image could not be loaded.")
            self.game.persist()

    def clear_background(self):
        self.game.delete_background_texture()
        self.game.background_image_path = ""
        self.game.persist()

    def set_sound_profile(self, profile):
        from otb_chess.services.audio import ensure_sounds, SOUND_PROFILES
        g = self.game
        if profile is not None and profile not in SOUND_PROFILES:
            return
        g.sound_enabled = profile is not None
        if profile is not None:
            g.sound_profile = profile
            for event,path in ensure_sounds(profile).items():
                setattr(g,"sound_"+event,path)
        for key,action in self.sound_profile_actions.items():
            action.setChecked(key == profile)
        g.persist()

    def toggle_analysis(self, enabled):
        self.game.analysis_enabled = enabled
        self.game.analysis_revision += 1
        if not enabled and self.game.analysis_engine is not None:
            self.game.analysis_engine.stop_search()
        self.game.cfg["analysis_enabled"] = enabled
        self.game.persist()
        self.analysis_action.setChecked(enabled)
        self.analysis_button.setChecked(enabled)
        self.analysis_button.setText("Stop analysis" if enabled else "Start analysis")
        if enabled:
            self.open_engine_analysis()
        else:
            self.engine_metrics.setText("Analysis paused")

    def open_engine_analysis(self):
        self.engine_toggle.setChecked(True)
        self.engine_panel.show()
        self.engine_panel.raise_()
        self.engine_panel.activateWindow()

    def set_analysis_window_visible(self, visible):
        if visible:
            self.engine_panel.show()
            self.engine_panel.raise_()
        else:
            self.engine_panel.close()

    def sync_engine_output(self):
        """Playing-engine searches do not populate the Stockfish analysis panel."""
        if self.game.analysis_enabled:
            return
        return

    def show_engine_info(self, source, info, prefix=""):
        evaluations = info if isinstance(info, (tuple, list)) else (info,)
        if not evaluations:
            return
        info = evaluations[0]
        score = info.score
        if score is not None:
            score_text = f"Mate {score.mate:+d}" if score.mate is not None else f"{score.centipawns/100:+.2f}"
        else:
            score_text = "—"
        self.engine_metrics.setText(f"{prefix}Engine evaluation: {score_text}   ·   Depth {info.depth if info.depth is not None else '—'}")
        token = self.game.analysis_position_token() if source == self.game.board.fen() else None
        self.engine_panel.present(source, evaluations, token, prefix)

    def show_controls(self):
        QMessageBox.information(self,"Controls",
            "Move: click source and destination, or drag a piece.\n"
            "Zoom: wheel up / down. Pan: drag an empty area.\n"
            "Rotate 3D: right-drag or Ctrl + left-drag.\n"
            "When Right Mouse is the OTB binding, use Ctrl + left-drag to rotate.\n\n"
            "Ctrl+F: flip   Ctrl+R: reset view   U: take back\n"
            "Space: press OTB clock   F11: fullscreen\n"
            "Ctrl+B: sidebar   Ctrl+Shift+F: Focus mode")

    def refresh_material(self):
        from otb_chess.ui.material import material_summary
        board = self.game.display_board
        position = chess.snapshot_history(board)
        if position == self._material_position:
            return
        self._material_position = position
        captured, balance = material_summary(board)
        self.captured_white.setText(captured[chess.WHITE])
        self.captured_black.setText(captured[chess.BLACK])
        self.material_row.setStretch(0, max(1, len(captured[chess.WHITE])))
        self.material_row.setStretch(2, max(1, len(captured[chess.BLACK])))
        self.material_balance.setText(f"{balance:+d}" if balance else "0")

    def tick(self):
        if self.closing:
            return
        if self.bookmark_pending is not None:
            self.advance_bookmark_restore()
            return
        g = self.game
        self.engine_panel.refresh_preview()
        g.update_clock()
        self.engine_enabled_button.blockSignals(True)
        self.engine_enabled_button.setChecked(g.engine_enabled)
        self.engine_enabled_button.setText("Engine on" if g.engine_enabled else "Engine off - free play")
        self.engine_enabled_button.blockSignals(False)
        if (getattr(g, '_engine_resume_pending', False) and not g.engine_manager.thinking
                and not self.new_game_pending and self.pending_difficulty is None):
            g._engine_resume_pending = False
            g.maybe_request_engine_move()
        if not self.new_game_pending and self.pending_difficulty is None:
            g.apply_pending_engine_move()
        self.session.save(g)
        g.maybe_persist_camera()
        if g.engine_load_result is not None:
            path,(ok,message) = g.engine_load_result
            g.engine_load_result = None
            g.result_text = message
            g.engine_var.set(path if ok else "")
            if not path or not ok:
                g.engine_side = None
            g.persist()
            if ok and path and self.pending_difficulty is None and not self.new_game_pending:
                g.maybe_request_engine_move()
        if self.pending_difficulty is not None:
            self.select_difficulty(self.pending_difficulty)
        self.start_pending_game()
        self.black_clock.refresh(g)
        self.white_clock.refresh(g)
        self.refresh_material()
        self.refresh_game_actions()
        self.play_button.setText("Starting game…" if self.new_game_pending else "Start game" if not g.game_started or g.game_over else "Resume clock" if g.clock_paused else "Pause clock")
        self.play_button.setEnabled(not self.new_game_pending and
                                    (not g.game_started or g.game_over or
                                     not (g.engine_loading or g.engine_manager.thinking)))
        self.refresh_navigation()
        self.clock_summary.setText(f"{g.time_control_var.get()}  ·  {'Manual clock' if g.clock_mode == 'OTB' else 'Automatic clock'}")
        self.statusBar().showMessage(g.preview_description or self.session.error or g.result_text)
        self.board_status.setText(g.preview_description or f"{g.board_mode}  ·  {g.piece_sets[g.piece_set].name}")
        self.engine_name.setText("Stockfish - Full strength")
        self.analysis_button.setEnabled(True)
        fen = g.board.fen()
        if fen != self.last_fen:
            self.refresh_moves()
            self.engine_line.clear()
            self.engine_metrics.setText("Analysing…" if g.analysis_enabled else "Enable analysis from the Engine menu.")
            self.last_fen = fen
        if g.analysis_enabled and time.perf_counter()-g.analysis_stamp > .75:
            g.request_analysis()
        output = g.engine_output
        if output is not None and output is not self.last_output:
            self.last_output = output
            source,info,error = output
            if (source == fen and g.analysis_enabled
                    and getattr(g, 'engine_output_token', g.analysis_position_token()) == g.analysis_position_token()):
                if error:
                    self.engine_metrics.setText(error)
                else:
                    self.show_engine_info(source,info)
        self.board_widget.update()

    def closeEvent(self, event):
        g = self.game
        if g.engine_loading or self.bookmark_pending is not None:
            g.result_text = "Finishing engine load before closing…"
            QTimer.singleShot(100,self.close)
            event.ignore()
            return
        self.closing = True
        self.timer.stop()
        g.end_variation(resume=False)
        self.engine_panel.remember_geometry()
        self.engine_panel.hide()
        g.closed = True
        g.update_clock()
        self.session.save(g,force=True)
        if self.sidebar.isVisible():
            self.sidebar_width = self.sidebar.width()
        if self.bookmark_panel is not None:
            self.bookmark_panel.remember_geometry()
        normal_size = self.normalGeometry().size() if self.isFullScreen() or self.isMaximized() else self.size()
        g.cfg.update(window_size=[normal_size.width(),normal_size.height()],sidebar_width=self.sidebar_width,
                     sidebar_visible=self.sidebar_action.isChecked(),focus_mode=self.focus_action.isChecked(),
                     engine_panel_open=self.engine_toggle.isChecked())
        g.persist()
        if g.analysis_engine is not None:
            g.analysis_engine.stop_search()
        with g.analysis_lock:
            if g.analysis_engine is not None:
                g.analysis_engine.quit()
                g.analysis_engine = None
        g.engine_manager.unload()
        self.board_widget.cleanup()
        event.accept()


def configure_graphics():
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setVersion(2,1)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)


def run():
    configure_graphics()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("OTBMaster3D")
    app.setWindowIcon(QIcon(str(APP_DIR / "assets" / "app-icon.ico")))
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OTBMaster3D.Desktop")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
