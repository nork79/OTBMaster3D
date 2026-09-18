"""Clock timing, increments, manual presses and time-control selection."""

from otb_chess.chess_backend import values as chess

from tkinter import messagebox
import time
from otb_chess.services.settings import TIME_CONTROLS, TimeControl


class ClockControls:
    """Clock behaviour using the game controller's shared timing state.

    Hosts provide time-control values and engine scheduling. No window or timer
    is created here: the UI calls update_clock from its event loop.
    """

    def clocks_editable(self):
        return not self.game_over and (self.clock_paused or self.clocks_waiting_for_first_move())

    def clocks_waiting_for_first_move(self):
        return not self.game_over and not self.board.move_stack and self._review_live is None

    def hit_clock(self):
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
        self.result_text = "Clock hit"
        self.maybe_request_engine_move()

    def stop_clock(self):
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
        self.black_time = time_control.initial_seconds
        self.increment = time_control.increment_seconds
        self.active_clock_color = chess.WHITE
        self.clock_paused = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.last_clock_tick = time.perf_counter()
        self.result_text = f"Clock reset - {time_control.name}"
        if hasattr(self, "stop_btn"):
            self.stop_btn.config(text="Stop Clock")

    def update_clock(self):
        now = time.perf_counter()
        if not self.game_started or self.game_over or self.clock_paused or not self.board.move_stack:
            self.last_clock_tick = now
            return
        e = now - self.last_clock_tick
        self.last_clock_tick = now
        if self.active_clock_color == chess.WHITE:
            self.white_time = max(0, self.white_time - e)
            if self.white_time <= 0:
                self.game_started = False
                self.game_over = True
                self.result_text = "White flagged"
                self.play_game_sound(self.sound_game_end)
        else:
            self.black_time = max(0, self.black_time - e)
            if self.black_time <= 0:
                self.game_started = False
                self.game_over = True
                self.result_text = "Black flagged"
                self.play_game_sound(self.sound_game_end)

    @staticmethod
    def fmt_clock(s):
        s = max(0, s)
        return (
            f"{int(s)//60}:{s%60:04.1f}" if s < 20 else f"{int(s)//60}:{int(s)%60:02d}"
        )

