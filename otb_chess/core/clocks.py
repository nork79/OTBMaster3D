"""Clock timing, increments, manual presses and time-control selection."""

from otb_chess.chess_backend import values as chess
from otb_chess.chess_backend.position import ChessPosition

from tkinter import messagebox
import time
from otb_chess.services.settings import TIME_CONTROLS, TimeControl


class ClockControls:
    """Clock behaviour using the game controller's shared timing state.

    Hosts provide time-control values and engine scheduling. No window or timer
    is created here: the UI calls update_clock from its event loop.
    """

    clocks_disabled = False

    def _record_ply_clock(self):
        if getattr(self, "_review_live", None) is not None:
            return
        ply = len(self.board.move_stack)
        ply_clocks = getattr(self, "ply_clocks", None)
        if not isinstance(ply_clocks, list):
            ply_clocks = []
            self.ply_clocks = ply_clocks
        if not ply_clocks:
            hist = getattr(self, "clock_history", None)
            if hist:
                w0, b0, _ = hist[0]
                ply_clocks.append((float(w0), float(b0)))
            else:
                ply_clocks.append((float(self.white_time), float(self.black_time)))
        while len(ply_clocks) <= ply:
            ply_clocks.append((float(self.white_time), float(self.black_time)))
        ply_clocks[ply] = (float(self.white_time), float(self.black_time))
        del ply_clocks[ply + 1:]

    def _truncate_ply_clocks(self):
        ply_clocks = getattr(self, "ply_clocks", None)
        if not isinstance(ply_clocks, list) or not ply_clocks:
            return
        ply = len(self.board.move_stack)
        del ply_clocks[ply + 1:]
        if len(ply_clocks) == ply + 1:
            ply_clocks[ply] = (float(self.white_time), float(self.black_time))

    def clock_times_at_ply(self, ply: int) -> tuple[float, float]:
        ply_clocks = getattr(self, "ply_clocks", None)
        if isinstance(ply_clocks, (list, tuple)) and 0 <= ply < len(ply_clocks):
            w_val, b_val = ply_clocks[ply]
            return float(w_val), float(b_val)
        hist = getattr(self, "clock_history", None) or []
        if hist:
            if ply <= 0:
                return float(hist[0][0]), float(hist[0][1])
            if ply < len(hist):
                turn_at_ply = hist[ply][2]
                if turn_at_ply == chess.BLACK:
                    return float(hist[ply][0]), float(hist[ply - 1][1])
                return float(hist[ply - 1][0]), float(hist[ply][1])
        return float(self.white_time), float(self.black_time)

    def displayed_clock_time(self, color: bool) -> float:
        if getattr(self, "_review_live", None) is not None:
            hist_moves = self.history_position().moves
            cur_moves = self.position.moves
            common = 0
            while common < len(cur_moves) and common < len(hist_moves) and cur_moves[common] == hist_moves[common]:
                common += 1
            w_time, b_time = self.clock_times_at_ply(common)
            return w_time if color else b_time
        return float(self.white_time if color else self.black_time)

    def clocks_editable(self):
        online = getattr(self, "online_session", None)
        if online is not None and online.active:
            return False
        return not self.clocks_disabled and not self.game_over and (self.clock_paused or self.clocks_waiting_for_first_move())

    def clocks_waiting_for_first_move(self):
        online = getattr(self, "online_session", None)
        if online is not None and online.active:
            return not self.game_over and len(self.board.move_stack) < 2 and self._review_live is None
        return not self.game_over and not self.board.move_stack and self._review_live is None

    def hit_clock(self):
        if self.clocks_disabled:
            return
        if (
            self.clock_mode != "OTB"
            or not self.game_started
            or self.game_over
            or self.clock_paused
            or self._review_live is not None
            or not self.awaiting_clock_press
        ):
            return
        mover = self.awaiting_clock_color
        if mover == chess.WHITE:
            self.white_time += self.increment
        elif mover == chess.BLACK:
            self.black_time += self.increment
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.active_clock_color = self.board.turn
        self.last_clock_tick = time.perf_counter()
        self._record_ply_clock()
        self.result_text = "Clock hit"
        self.maybe_request_engine_move()

    def stop_clock(self):
        online = getattr(self, "online_session", None)
        if online is not None and online.active:
            return
        if not self.game_started or self.game_over:
            return
        self.return_to_live()
        self.clock_paused = not self.clock_paused
        self.last_clock_tick = time.perf_counter()
        self.result_text = "Clock stopped" if self.clock_paused else "Clock resumed"
        if not self.clock_paused:
            self.maybe_request_engine_move()
        if hasattr(self, "stop_btn"):
            self.stop_btn.config(text="Resume Clock" if self.clock_paused else "Stop Clock")

    def selected_time_control(self):
        """Return the selected preset or a validated custom time control."""
        selected = self.time_control_var.get()
        if selected != "Custom":
            return TIME_CONTROLS[selected]

        try:
            initial = float(self.custom_initial_var.get())
            increment = float(self.custom_increment_var.get())
            if initial <= 0 or increment < 0:
                raise ValueError
        except (TypeError, ValueError):
            messagebox.showerror(
                "Time control",
                "Custom initial seconds must be > 0 and increment must be >= 0.",
            )
            return None

        return TimeControl("Custom", initial, increment)

    def reset_clock(self):
        self.return_to_live()
        time_control = self.selected_time_control()
        if time_control is None:
            return

        self.white_time = time_control.initial_seconds
        self.clocks_disabled = time_control.name == 'Infinite (clocks disabled)'
        self.black_time = time_control.initial_seconds
        self.increment = time_control.increment_seconds
        self.active_clock_color = chess.WHITE
        self.clock_paused = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.last_clock_tick = time.perf_counter()
        self.ply_clocks = [(float(self.white_time), float(self.black_time))]
        self.result_text = f"Clock reset - {time_control.name}"
        if hasattr(self, "stop_btn"):
            self.stop_btn.config(text="Stop Clock")

    def update_clock(self):
        now = time.perf_counter()
        online = getattr(self, "online_session", None)
        online_active = online is not None and online.active
        min_moves = 2 if online_active else 1
        if (self.clocks_disabled or not self.game_started or self.game_over
                or self.clock_paused or len(self.board.move_stack) < min_moves):
            self.last_clock_tick = now
            return
        e = now - self.last_clock_tick
        self.last_clock_tick = now
        if self.active_clock_color == chess.WHITE:
            self.white_time = max(0, self.white_time - e)
            if self.white_time <= 0 and not online_active:
                self.game_started = False
                self.game_over = True
                self._record_ply_clock()
                ending = ChessPosition.from_board(self.board).loss_outcome(chess.WHITE, on_time=True)
                self.result_text, self._declared_result = ending.reason, ending.result
                self.play_game_sound(self.sound_game_end)
        else:
            self.black_time = max(0, self.black_time - e)
            if self.black_time <= 0 and not online_active:
                self.game_started = False
                self.game_over = True
                self._record_ply_clock()
                ending = ChessPosition.from_board(self.board).loss_outcome(chess.BLACK, on_time=True)
                self.result_text, self._declared_result = ending.reason, ending.result
                self.play_game_sound(self.sound_game_end)

    @staticmethod
    def fmt_clock(s):
        s = max(0, s)
        return (
            f"{int(s)//60}:{s%60:04.1f}" if s < 20 else f"{int(s)//60}:{int(s)%60:02d}"
        )

