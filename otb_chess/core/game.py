"""Game controller: position, moves, game lifecycle and engine coordination."""

from otb_chess.chess_backend import books
from otb_chess.chess_backend import values as chess
from otb_chess.chess_backend.position import ChessPosition
from otb_chess_core import Move

from otb_chess.graphics.board_2d import FlatPieceRenderer, FLAT_SETS
from pathlib import Path
from otb_chess.graphics.piece_sets import PieceRenderer
from otb_chess.version import __version__
from otb_chess.graphics.piece_sets import discover_sets
import glfw
import math
import random
import time
from otb_chess.services.settings import DEFAULT_BACKGROUND, HEIGHT, PIECE_DIR, TIME_CONTROLS, WIDTH, ensure_dirs, load_config
from otb_chess.services.audio import ensure_sounds, play_sound, SOUND_PROFILES, DEFAULT_SOUND_PROFILE
from otb_chess.graphics.gl_primitives import setup_gl
from otb_chess.services.engine import EngineManager
from otb_chess.graphics.rendering import BoardRendering
from otb_chess.core.board_input import BoardInput
from otb_chess.core.appearance import AppearanceSettings
from otb_chess.ui.legacy_ui import LegacyUI
from otb_chess.core.clocks import ClockControls
from otb_chess.core.documents import GameDocuments
from otb_chess.graphics.board_types import BOARD_TYPES, BoardSurfaceRenderer


class Chess3D(GameDocuments, LegacyUI, BoardRendering, BoardInput, AppearanceSettings, ClockControls):
    """Own game state and coordinate focused behaviour components.

    The mixins share this controller's state, keeping existing Qt and GLFW
    integrations compatible without forwarding or duplicating mutable values.
    """

    engine_enabled = True

    def __init__(self, render_widget=None):
        ensure_dirs()
        self.cfg = load_config()
        self.render_widget = render_widget
        self.window = None
        self.width, self.height = WIDTH, HEIGHT
        if render_widget is None:
            if not glfw.init():
                raise RuntimeError("GLFW init failed.")
            glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
            glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
            glfw.window_hint(glfw.SAMPLES, 4)
            glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
            self.window = glfw.create_window(WIDTH, HEIGHT, f"OTBMaster3D v{__version__}", None, None)
            if not self.window:
                glfw.terminate()
                raise RuntimeError("Could not create OpenGL window.")
            glfw.make_context_current(self.window)
            glfw.swap_interval(1)
            setup_gl(WIDTH, HEIGHT)
        self.board = ChessPosition().legacy_board
        self.move_animation_ms = max(0,min(1500,int(self.cfg.get("move_animation_ms",0))))
        self.move_animation = None
        self.board_type = self.cfg.get("board_type","tournament")
        if self.board_type not in BOARD_TYPES:
            self.board_type = "tournament"
        self.board_surface_renderer = BoardSurfaceRenderer()
        self.board_mode = self.cfg.get("board_mode", "3D")
        if self.board_mode not in ("2D", "3D"):
            self.board_mode = "3D"
        self.two_d_flipped = bool(self.cfg.get("two_d_flipped", False))
        self.two_d_scale = max(0.4, min(2.5, float(self.cfg.get("two_d_scale", 1.0))))
        self.two_d_pan_x = float(self.cfg.get("two_d_pan_x", 0.0))
        self.two_d_pan_z = float(self.cfg.get("two_d_pan_z", 0.0))
        self.flat_piece_renderer = FlatPieceRenderer()
        self.flat_piece_set = self.cfg.get("flat_piece_set","textbook")
        if self.flat_piece_set not in FLAT_SETS:
            self.flat_piece_set = "textbook"
        self.piece_sets = discover_sets(PIECE_DIR)
        self.piece_set = self.cfg.get("piece_set", "tournament")
        if self.piece_set not in self.piece_sets:
            self.piece_set = "tournament"
        self.piece_renderer = PieceRenderer()
        self.piece_load_error = None
        if render_widget is None:
            try:
                self.piece_renderer.prepare(self.piece_sets[self.piece_set])
            except (OSError, ValueError, RuntimeError) as exc:
                self.piece_load_error = f"Could not load saved pieces: {exc}"
                self.piece_set = "club"
                self.piece_renderer.prepare(self.piece_sets[self.piece_set])
        self.light_square = tuple(self.cfg["light_square"])
        self.dark_square = tuple(self.cfg["dark_square"])
        self.frame_color = tuple(self.cfg["frame_color"])
        self.background_color = tuple(
            self.cfg.get("background_color", DEFAULT_BACKGROUND)
        )
        self.background_image_path = self.cfg.get("background_image", "")
        from otb_chess.graphics.backgrounds import BACKGROUNDS
        self.background_style = self.cfg.get("background_style", "solid")
        if self.background_style not in BACKGROUNDS:
            self.background_style = "solid"
        self.background_preset_key = None
        self.background_texture = None
        self.background_texture_size = None
        self.show_coordinates = bool(self.cfg["show_coordinates"])
        self.show_move_indicator = bool(self.cfg.get("show_move_indicator", True))
        self.sound_enabled = bool(self.cfg.get("sound_enabled", True))
        self.sound_profile = self.cfg.get("sound_profile", DEFAULT_SOUND_PROFILE)
        if self.sound_profile not in SOUND_PROFILES:
            self.sound_profile = DEFAULT_SOUND_PROFILE
        self.yaw = float(self.cfg.get("camera_yaw", 0.0))
        self._three_d_facing = self.cfg.get("three_d_facing")
        if self._three_d_facing not in ("white", "black"):
            self._three_d_facing = "black" if math.cos(self.yaw) < 0 else "white"
        self.pitch = float(self.cfg.get("camera_pitch", math.radians(40)))
        self.distance = float(self.cfg.get("camera_distance", 12.4))
        self.pan_x = float(self.cfg.get("camera_pan_x", 0.0))
        self.pan_z = float(self.cfg.get("camera_pan_z", 0.0))
        self.target_y = 0.25
        self.selected = self.drag_piece = self.drag_world = self.left_down_pos = None
        self.was_drag = False
        self.right_drag = False
        self.ctrl_left_rotate = False
        self.last_mouse = (0, 0)
        self.board_pan_drag = False
        self.pan_start_world = None
        self.pan_start_offset = (0.0, 0.0)
        self.camera_dirty = False
        self.last_camera_change = 0.0
        for event, path in ensure_sounds(self.sound_profile).items():
            setattr(self, "sound_" + event, path)
        tc = TIME_CONTROLS.get(self.cfg["time_control"], TIME_CONTROLS["Bullet 1+0"])
        self.white_time = tc.initial_seconds
        self.black_time = tc.initial_seconds
        self.increment = tc.increment_seconds
        self.active_clock_color = chess.WHITE
        self.last_clock_tick = time.perf_counter()
        self.clock_history = []
        self.clock_paused = False
        self.clock_mode = self.cfg.get("clock_mode", "Online")
        self.clock_binding = self.cfg.get("clock_binding", "Spacebar")
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.game_started = False
        self.game_over = False
        self.result_text = "Ready"
        self.engine_enabled = bool(self.cfg.get("engine_enabled", True))
        self.engine_side = {
            "None": None,
            "White": chess.WHITE,
            "Black": chess.BLACK,
        }.get(self.cfg["engine_side"])
        self.engine_manager = EngineManager(self)
        self.pending_engine_move = None
        self.pending_engine_position = None
        self.last_engine_search = None
        self.pending_engine_error = None
        self.book_path = self.cfg.get("book_path", "")
        self.ui = None
        if render_widget is None:
            glfw.set_window_user_pointer(self.window, self)
            glfw.set_framebuffer_size_callback(self.window, self._resize)
            glfw.set_scroll_callback(self.window, self._scroll)
            glfw.set_mouse_button_callback(self.window, self._mouse)
            glfw.set_cursor_pos_callback(self.window, self._cursor)
            glfw.set_key_callback(self.window, self._key)

    def legal_targets(self):
        if self.selected is None:
            return set()
        return self.position.legal_targets(self.selected)

    def human_can_move(self):
        if self._review_live is not None:
            return False
        engine_has_turn = (
            self.engine_enabled and self.game_started
            and self.engine_manager.engine is not None
            and self.engine_side == self.board.turn
        )
        return (
            not self.game_over and not (self.engine_enabled and self.awaiting_clock_press) and not engine_has_turn
        )

    def try_move(self, fr, to, is_engine=False, promotion=None):
        if is_engine and not self.engine_enabled:
            return False
        if self.game_over:
            return False
        if fr is None or to is None or fr == to:
            return False
        if not is_engine and not self.human_can_move():
            return False
        p = self.position.piece_at(fr)
        if not p:
            return False
        if p.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7):
            choices = self.position.promotion_choices(fr, to)
            if not choices:
                self.play_game_sound(self.sound_illegal)
                return False
            if promotion is None and not is_engine:
                position = self.board.fen()
                promotion = self.choose_promotion(p.color, to)
                # A modal chooser runs the UI timer: the clock can expire meanwhile.
                if self.board.fen() != position or not self.human_can_move():
                    return False
            if promotion not in choices:
                return False
        try:
            mv = Move(fr, to, promotion=promotion)
        except ValueError:
            if not is_engine:
                self.play_game_sound(self.sound_illegal)
            return False
        if not self.position.is_legal(mv):
            if not is_engine:
                self.play_game_sound(self.sound_illegal)
            return False
        mover = self.board.turn
        details = self.position.move_details(mv)
        capture, castle = details.capture, details.castling
        if self.game_started:
            self.clock_history.append(
                (self.white_time, self.black_time, self.active_clock_color)
            )
        origins = dict(details.origins)
        self.position.apply(mv)
        self.move_animation = (self.board, self.board.fen(),time.perf_counter(),
                               self.move_animation_ms / 1000,origins) if self.move_animation_ms else None
        if self.game_started:
            if len(self.board.move_stack) == 1:
                self.last_clock_tick = time.perf_counter()
            if self.clock_mode == "OTB" and not is_engine and self.engine_enabled:
                self.awaiting_clock_press = True
                self.awaiting_clock_color = mover
                self.active_clock_color = mover
                mover_name = "White" if mover == chess.WHITE else "Black"
                self.result_text = (
                    f"{mover_name} moved - hit clock ({self.clock_binding})"
                )
            else:
                if mover == chess.WHITE:
                    self.white_time += self.increment
                else:
                    self.black_time += self.increment
                self.active_clock_color = self.board.turn
                self.last_clock_tick = time.perf_counter()
        self.refresh_move_list()
        self.update_game_end()
        if not self.game_over:
            sound = (self.sound_promote if promotion else self.sound_castle if castle
                     else self.sound_check if self.position.is_check()
                     else self.sound_capture if capture else self.sound_move)
            self.play_game_sound(sound)
        if self.game_started and not self.game_over and not self.awaiting_clock_press:
            self.maybe_request_engine_move()
        return True

    def update_game_end(self):
        was_over = self.game_over
        ending = self.position.termination()
        if ending is not None:
            self.game_over = True
            self.game_started = False
            self.awaiting_clock_press = False
            self.awaiting_clock_color = None
            self.result_text = ending.reason
        if self.game_over and not was_over:
            self.play_game_sound(self.sound_game_end)

    def play_game_sound(self, path):
        if self.sound_enabled:
            play_sound(path)

    def switch_sides(self):
        if not self.engine_enabled or self.engine_side is None or self.engine_manager.engine is None or self.game_over:
            return
        self.return_to_live()
        self.update_clock()
        if self.game_over:
            return
        self.clock_paused = True
        self.engine_manager.search_generation += 1
        if self.engine_manager.thinking:
            self.engine_manager.stop_search()
        self.pending_engine_move = self.pending_engine_position = self.pending_engine_error = None
        self.last_engine_search = None
        self.move_animation = None
        self.cancel_selection()
        self.engine_side = not self.engine_side
        self.engine_side_var.set("White" if self.engine_side else "Black")
        self.last_clock_tick = time.perf_counter()
        self.result_text = "Sides switched - clocks paused"

    def takeback(self):
        self.return_to_live()
        if not self.board.move_stack:
            return
        self.clock_paused = True
        self.engine_manager.search_generation += 1
        if self.engine_manager.thinking:
            self.engine_manager.stop_search()
        self.pending_engine_move = self.pending_engine_position = self.pending_engine_error = None
        self.last_engine_search = None
        self.move_animation = None
        self.position.undo()
        self._declared_result = None
        if self.clock_history:
            self.white_time, self.black_time, self.active_clock_color = self.clock_history.pop()
        self.active_clock_color = self.board.turn
        self.game_started = True
        self.selected = None
        self.game_over = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.result_text = "Move taken back — clocks paused"
        self.last_clock_tick = time.perf_counter()
        self.refresh_move_list()

        self.update_game_end()

    def reset_board(self):
        self._declared_result = None
        self._review_live = self._pgn_document = None
        self.position.reset()
        self.clock_history.clear()
        self.selected = None
        self.game_started = False
        self.game_over = False
        self.clock_paused = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.result_text = "Board reset"
        self.refresh_move_list()

    def start_game(self, starting_fen=None):
        starting_position = ChessPosition(starting_fen) if starting_fen is not None else ChessPosition()
        if not starting_position.is_valid():
            raise ValueError("The starting position is not valid")
        self._review_live = self._pgn_document = None
        time_control = self.selected_time_control()
        if time_control is None:
            return

        requested_engine_side = {
            "None": None,
            "White": chess.WHITE,
            "Black": chess.BLACK,
        }[self.engine_side_var.get()]
        engine_unavailable = (
            requested_engine_side is not None and self.engine_manager.engine is None
        )
        if engine_unavailable:
            requested_engine_side = None
            self.engine_side_var.set("None")

        self.board = starting_position.legacy_board
        self._declared_result = None
        self.clock_history.clear()
        self.white_time = time_control.initial_seconds
        self.black_time = time_control.initial_seconds
        self.increment = time_control.increment_seconds
        self.active_clock_color = self.board.turn
        self.last_clock_tick = time.perf_counter()
        self.clock_paused = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.game_started = True
        self.game_over = False
        if engine_unavailable:
            self.result_text = (
                f"Game started - {time_control.name}; no engine loaded, "
                "both sides are human"
            )
        else:
            self.result_text = f"Game started - {time_control.name}"
        self.clock_mode = self.clock_mode_var.get()
        self.clock_binding = self.clock_binding_var.get()
        self.engine_side = requested_engine_side
        self.book_path = self.book_var.get()
        self.play_game_sound(self.sound_game_start)
        self.refresh_move_list()
        self.persist()
        self.update_game_end()
        self.maybe_request_engine_move()

    def resign(self, color=None):
        if self.game_started and not self.game_over:
            color = self.board.turn if color is None else color
            self.game_started = False
            self.game_over = True
            ending = self.position.loss_outcome(color)
            self.result_text, self._declared_result = ending.reason, ending.result
            self.play_game_sound(self.sound_game_end)

    def offer_draw(self):
        if self.game_started and not self.game_over:
            self.result_text = "Draw offered"

    def claim_draw(self, intended_move=None):
        if self.game_over or self._review_live is not None:
            return False
        if (self.engine_enabled and self.game_started and self.engine_side == self.board.turn
                and self.engine_manager.engine is not None):
            self.result_text = "Only the player to move can claim a draw"
            return False
        if isinstance(intended_move, str):
            try:
                intended_move = self.position.parse_uci(intended_move.strip())
            except ValueError:
                self.result_text = "Enter a move such as e2e4 or a7a8q"
                return False
        reason = self.position.draw_claim_reason(intended_move)
        if reason is None:
            self.result_text = "No valid draw claim for this position or intended move"
            return False
        # Application lifecycle is separate from position.termination(): imported
        # results, claims, resignation and timeout may finish a nonterminal board.
        # TODO extraction: consolidate these flags in a game-session record.
        self.game_started = False
        self.game_over = True
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.result_text = reason
        self._declared_result = '1/2-1/2'
        self.play_game_sound(self.sound_game_end)
        return True

    def pick_book_move(self):
        if self.cfg.get("engine_difficulty", "custom") != "custom":
            return None  # Presets should play at their chosen strength from move one.
        path = self.book_var.get() if self.book_var else self.book_path
        if not path or not Path(path).exists():
            return None
        try:
            with books.open_reader(path) as rd:
                es = list(rd.find_all(self.board))
                if not es:
                    return None
                return random.choices(es, weights=[max(1, e.weight) for e in es], k=1)[
                    0
                ].move
        except Exception:
            return None

    def set_engine_enabled(self, enabled):
        enabled = bool(enabled)
        if enabled == self.engine_enabled:
            return
        self.engine_enabled = enabled
        self._engine_resume_pending = enabled and self.engine_manager.thinking
        self.cfg["engine_enabled"] = enabled
        self.engine_manager.search_generation += 1
        self.pending_engine_move = self.pending_engine_position = self.pending_engine_error = None
        if not enabled:
            self.engine_manager.stop_search()
            self.awaiting_clock_press = False
            self.awaiting_clock_color = None
            self.active_clock_color = self.board.turn
        elif self.engine_side is None:
            self.engine_side = self.engine_side_var.get() == "White"
            self.engine_side_var.set("White" if self.engine_side else "Black")
        if not self.game_over and self._review_live is None:
            self.result_text = "Engine on" if enabled else "Engine off - free play"
        self.persist()
        if enabled:
            self.maybe_request_engine_move()

    def maybe_request_engine_move(self):
        if not self.engine_enabled:
            return
        if self.clock_paused or self._review_live is not None or self.pending_engine_move is not None:
            return
        if not (
            self.game_started
            and not self.game_over
            and self.engine_side is not None
            and self.board.turn == self.engine_side
        ):
            return
        bm = self.pick_book_move()
        if bm:
            self.pending_engine_generation = self.engine_manager.search_generation
            self.pending_engine_position = self.board.fen()
            self.pending_engine_move = bm
        elif self.engine_manager.engine:
            self.engine_manager.request_move()

    def apply_pending_engine_move(self):
        if not self.engine_enabled:
            self.pending_engine_move = self.pending_engine_position = self.pending_engine_error = None
            return
        if self.clock_paused or self._review_live is not None:
            return
        if self.pending_engine_error:
            self.result_text = f"Engine error: {self.pending_engine_error}"
            self.pending_engine_error = None
        mv = self.pending_engine_move
        if mv is None:
            return
        self.pending_engine_move = None
        generation = getattr(self, "pending_engine_generation", self.engine_manager.search_generation)
        if generation != self.engine_manager.search_generation:
            self.pending_engine_position = None
            return
        source = self.pending_engine_position
        self.pending_engine_position = None
        if source is not None and source != self.board.fen():
            return
        if self.position.is_legal(mv):
            self.try_move(mv.from_square, mv.to_square, True, promotion=mv.promotion)

