"""Legacy Tk interface retained for compatibility and regression coverage."""

from otb_chess.chess_backend import rules as chess
from otb_chess.chess_backend import notation

from PIL import Image
from PIL import ImageTk
from pathlib import Path
from otb_chess.version import __version__
import colorsys
from tkinter import filedialog
import glfw
import math
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
from otb_chess.services.settings import BOOK_DIR, ENGINE_DIR, TIME_CONTROLS
from otb_chess.graphics.board_colors import BOARD_COLOR_THEMES


class LegacyUI:
    """Optional Tk host methods; the normal application uses desktop_ui."""

    def choose_promotion(self, color, square):
        dialog = tk.Toplevel(self.ui)
        dialog.title("Pawn promotion")
        dialog.transient(self.ui)
        selected = None
        ttk.Label(dialog, text="Choose the promotion piece:").pack(padx=16, pady=12)
        row = ttk.Frame(dialog)
        row.pack(padx=16, pady=12)
        def choose(piece_type):
            nonlocal selected
            selected = piece_type
            dialog.destroy()
        for label, piece_type in (("Queen", chess.QUEEN), ("Rook", chess.ROOK),
                                  ("Bishop", chess.BISHOP), ("Knight", chess.KNIGHT)):
            ttk.Button(row, text=label, command=lambda p=piece_type: choose(p)).pack(side="left")
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=12)
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        dialog.grab_set()
        dialog.wait_window()
        return selected

    def refresh_move_list(self):
        if not hasattr(self, "move_text"):
            return
        b = chess.Board()
        sans = []
        for mv in self.board.move_stack:
            sans.append(notation.san(b.fen(), chess.owned_move(mv)))
            b.push(mv)
        lines = []
        for i in range(0, len(sans), 2):
            move_no = i // 2 + 1
            white = sans[i]
            black = sans[i + 1] if i + 1 < len(sans) else ""
            lines.append(f"{move_no}. {white} {black}".rstrip())
        self.move_text.config(state="normal")
        self.move_text.delete("1.0", "end")
        self.move_text.insert("1.0", "\n".join(lines))
        self.move_text.config(state="disabled")
        self.move_text.see("end")

    def refresh_engines(self):
        self.engine_combo["values"] = [""] + [
            str(p) for p in sorted(ENGINE_DIR.glob("*.exe"))
        ]

    def refresh_books(self):
        self.book_combo["values"] = [""] + [
            str(p) for p in sorted(BOOK_DIR.glob("*.bin"))
        ]

    def load_engine(self):
        path = self.engine_var.get()
        if not path:
            return
        ok, msg = self.engine_manager.load(path)
        self.result_text = msg
        if not ok:
            messagebox.showerror("UCI engine", msg)
        self.persist()

    def browse_engine(self):
        p = filedialog.askopenfilename(
            initialdir=ENGINE_DIR, filetypes=[("Engine", "*.exe"), ("All", "*.*")]
        )
        if p:
            self.engine_var.set(p)
            self.load_engine()

    def browse_book(self):
        p = filedialog.askopenfilename(
            initialdir=BOOK_DIR, filetypes=[("Polyglot", "*.bin"), ("All", "*.*")]
        )
        if p:
            self.book_var.set(p)
            self.book_path = p
            self.persist()

    def choose_color(self, which):
        original_color = self.color_value(which)
        original_background_image = self.background_image_path
        if which == "background":
            self.delete_background_texture()
            self.board_surface_renderer.close()
            self.background_image_path = ""
            self.update_background_label()

        hue, saturation, value = colorsys.rgb_to_hsv(*original_color)
        picker = tk.Toplevel(self.ui)
        picker.title(
            {
                "light": "Light squares",
                "dark": "Dark squares",
                "frame": "Board frame",
                "background": "Background",
            }[which]
        )
        picker.resizable(False, False)
        picker.transient(self.ui)

        wheel_size = 180
        center = wheel_size / 2
        radius = center - 3
        wheel_pixels = []
        for y in range(wheel_size):
            for x in range(wheel_size):
                dx = x - center
                dy = center - y
                distance = math.hypot(dx, dy)
                if distance <= radius:
                    pixel_hue = (math.atan2(dy, dx) / math.tau) % 1.0
                    pixel_saturation = distance / radius
                    rgb = colorsys.hsv_to_rgb(pixel_hue, pixel_saturation, 1.0)
                    wheel_pixels.append(tuple(round(channel * 255) for channel in rgb))
                else:
                    wheel_pixels.append((45, 45, 48))

        wheel_source = Image.new("RGB", (wheel_size, wheel_size))
        wheel_source.putdata(wheel_pixels)
        wheel_image = ImageTk.PhotoImage(wheel_source)
        wheel = tk.Canvas(
            picker,
            width=wheel_size,
            height=wheel_size,
            highlightthickness=0,
            background="#2d2d30",
        )
        wheel.pack(padx=10, pady=(10, 4))
        wheel.create_image(0, 0, anchor="nw", image=wheel_image)
        wheel.image = wheel_image
        marker = wheel.create_oval(0, 0, 0, 0, outline="black", width=2)

        brightness = tk.DoubleVar(value=value)
        preview = tk.Label(picker, height=2, relief="sunken")
        preview.pack(fill="x", padx=10, pady=4)

        def update_marker():
            marker_x = center + math.cos(hue * math.tau) * saturation * radius
            marker_y = center - math.sin(hue * math.tau) * saturation * radius
            wheel.coords(marker, marker_x - 5, marker_y - 5, marker_x + 5, marker_y + 5)

        def apply_live_color(*_):
            color = colorsys.hsv_to_rgb(hue, saturation, brightness.get())
            self.set_color_value(which, color)
            preview.config(background=self.hex(color))
            update_marker()

        def select_from_wheel(event):
            nonlocal hue, saturation
            dx = event.x - center
            dy = center - event.y
            distance = math.hypot(dx, dy)
            if distance > radius:
                return
            hue = (math.atan2(dy, dx) / math.tau) % 1.0
            saturation = distance / radius
            apply_live_color()

        def adjust_brightness(event):
            step = 0.03 if event.delta > 0 else -0.03
            brightness.set(max(0.05, min(1.0, brightness.get() + step)))
            apply_live_color()

        def accept():
            self.persist()
            picker.destroy()

        def cancel():
            self.set_color_value(which, original_color)
            if which == "background" and original_background_image:
                self.load_background_image(original_background_image, show_error=False)
            picker.destroy()

        wheel.bind("<Button-1>", select_from_wheel)
        wheel.bind("<B1-Motion>", select_from_wheel)
        wheel.bind("<MouseWheel>", adjust_brightness)
        ttk.Label(picker, text="Brightness").pack(anchor="w", padx=10)
        brightness_scale = ttk.Scale(
            picker,
            from_=0.05,
            to=1.0,
            variable=brightness,
            command=apply_live_color,
        )
        brightness_scale.pack(fill="x", padx=10)
        brightness_scale.bind("<MouseWheel>", adjust_brightness)
        actions = ttk.Frame(picker)
        actions.pack(fill="x", padx=8, pady=10)
        ttk.Button(actions, text="Cancel", command=cancel).pack(side="right", padx=2)
        ttk.Button(actions, text="Apply", command=accept).pack(side="right", padx=2)
        picker.protocol("WM_DELETE_WINDOW", cancel)
        picker.bind("<Escape>", lambda _event: cancel())
        apply_live_color()
        picker.grab_set()

    def browse_background_image(self):
        path = filedialog.askopenfilename(
            title="Choose background image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path and self.load_background_image(path):
            self.persist()

    def build_ui(self):
        root = tk.Tk()
        self.ui = root
        root.title(f"OTBMaster3D v{__version__} - Controls")
        root.geometry("620x780+10+10")
        root.resizable(False, True)
        self.white_clock_var = tk.StringVar(value=self.fmt_clock(self.white_time))
        self.black_clock_var = tk.StringVar(value=self.fmt_clock(self.black_time))
        self.status_var = tk.StringVar(value=self.result_text)
        self.time_control_var = tk.StringVar(value=self.cfg["time_control"])
        self.engine_side_var = tk.StringVar(value=self.cfg["engine_side"])
        self.engine_var = tk.StringVar(value=self.cfg.get("engine_path", ""))
        self.book_var = tk.StringVar(value=self.cfg.get("book_path", ""))
        self.background_var = tk.StringVar()
        self.coords_var = tk.BooleanVar(value=self.show_coordinates)
        self.move_indicator_var = tk.BooleanVar(value=self.show_move_indicator)
        self.sound_var = tk.BooleanVar(value=self.sound_enabled)
        self.clock_mode_var = tk.StringVar(value=self.cfg.get("clock_mode", "Online"))
        self.clock_binding_var = tk.StringVar(
            value=self.cfg.get("clock_binding", "Spacebar")
        )
        self.custom_initial_var = tk.StringVar(
            value=str(self.cfg.get("custom_initial", 300.0))
        )
        self.custom_increment_var = tk.StringVar(
            value=str(self.cfg.get("custom_increment", 0.0))
        )
        outer = ttk.Frame(root)
        outer.pack(fill="both", expand=True, padx=6, pady=6)
        controls = ttk.Frame(outer)
        controls.pack(side="left", fill="both", expand=True)
        control_canvas = tk.Canvas(controls, highlightthickness=0, width=420)
        control_scroll = ttk.Scrollbar(controls, orient="vertical", command=control_canvas.yview)
        control_scroll.pack(side="right", fill="y")
        control_canvas.pack(side="left", fill="both", expand=True)
        control_canvas.configure(yscrollcommand=control_scroll.set)
        left = ttk.Frame(control_canvas)
        control_window = control_canvas.create_window(0, 0, window=left, anchor="nw")
        left.bind("<Configure>", lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all")))
        control_canvas.bind("<Configure>", lambda e: control_canvas.itemconfigure(control_window, width=e.width))

        def scroll_controls(event):
            widget = event.widget
            if isinstance(widget, (ttk.Combobox, tk.Text)):
                return
            while widget is not None:
                if widget == controls:
                    control_canvas.yview_scroll(-int(event.delta / 120), "units")
                    return "break"
                widget = getattr(widget, "master", None)

        root.bind("<MouseWheel>", scroll_controls)
        right = ttk.LabelFrame(outer, text="Moves", width=165)
        right.pack(side="right", fill="both", expand=False, padx=(8, 0))
        right.pack_propagate(False)

        clocks = ttk.Frame(left)
        clocks.pack(fill="x", pady=4)
        ttk.Label(clocks, text="Black").grid(row=0, column=0, sticky="w")
        ttk.Label(
            clocks, textvariable=self.black_clock_var, font=("Consolas", 18, "bold")
        ).grid(row=0, column=1, sticky="e")
        ttk.Label(clocks, text="White").grid(row=1, column=0, sticky="w")
        ttk.Label(
            clocks, textvariable=self.white_clock_var, font=("Consolas", 18, "bold")
        ).grid(row=1, column=1, sticky="e")
        clocks.columnconfigure(1, weight=1)

        pieces = ttk.LabelFrame(left, text="Piece set")
        pieces.pack(fill="x", pady=(3, 6))
        view_row = ttk.Frame(pieces)
        view_row.pack(fill="x", padx=8, pady=(7, 0))
        ttk.Label(view_row, text="Board view").pack(side="left")
        self.board_mode_var = tk.StringVar(value=self.board_mode)
        for mode in ("3D", "2D"):
            ttk.Radiobutton(view_row, text=mode, value=mode, variable=self.board_mode_var,
                            command=self.change_board_mode).pack(side="left", padx=(12, 0))
        self.piece_set_keys = list(self.piece_sets)
        self.piece_combo = ttk.Combobox(
            pieces, state="readonly",
            values=[self.piece_sets[key].name for key in self.piece_set_keys],
        )
        self.piece_combo.current(self.piece_set_keys.index(self.piece_set))
        self.piece_combo.pack(fill="x", padx=8, pady=(7, 3))
        self.piece_combo.bind("<<ComboboxSelected>>", self.change_piece_set)
        self.piece_description_var = tk.StringVar(
            value=self.piece_load_error or self.piece_sets[self.piece_set].description
        )
        if not self.piece_load_error:
            self.update_piece_description()
        ttk.Label(pieces, textvariable=self.piece_description_var, wraplength=360).pack(
            anchor="w", padx=8, pady=(0, 7)
        )

        game = ttk.LabelFrame(left, text="Game")
        game.pack(fill="x", pady=3)
        ttk.Combobox(
            game,
            state="readonly",
            textvariable=self.time_control_var,
            values=list(TIME_CONTROLS) + ["Custom"],
            width=22,
        ).pack(fill="x", padx=6, pady=4)
        self.customrow = ttk.Frame(game)
        ttk.Label(self.customrow, text="Custom sec").pack(side="left")
        ttk.Entry(self.customrow, textvariable=self.custom_initial_var, width=8).pack(
            side="left", padx=(4, 10)
        )
        ttk.Label(self.customrow, text="Inc").pack(side="left")
        ttk.Entry(self.customrow, textvariable=self.custom_increment_var, width=6).pack(
            side="left", padx=4
        )

        def update_custom_visibility(*_):
            if self.time_control_var.get() == "Custom":
                self.customrow.pack(
                    fill="x", padx=6, pady=2, after=game.winfo_children()[0]
                )
            else:
                self.customrow.pack_forget()

        self.time_control_var.trace_add("write", update_custom_visibility)
        update_custom_visibility()
        clockrow = ttk.Frame(game)
        clockrow.pack(fill="x", padx=6, pady=2)
        ttk.Label(clockrow, text="Clock mode").pack(side="left")
        ttk.Combobox(
            clockrow,
            state="readonly",
            textvariable=self.clock_mode_var,
            values=["Online", "OTB"],
            width=9,
        ).pack(side="left", padx=4)
        ttk.Label(clockrow, text="Hit").pack(side="left", padx=(8, 0))
        ttk.Combobox(
            clockrow,
            state="readonly",
            textvariable=self.clock_binding_var,
            values=["Spacebar", "Right Mouse", "Middle Mouse", "Mouse Button 4", "Mouse Button 5"],
            width=16,
        ).pack(side="left", padx=4)
        row = ttk.Frame(game)
        row.pack(fill="x", padx=4, pady=2)
        ttk.Button(row, text="Start", command=self.start_game).pack(
            side="left", expand=True, fill="x", padx=2
        )
        ttk.Button(row, text="Resign", command=self.resign).pack(
            side="left", expand=True, fill="x", padx=2
        )
        ttk.Button(row, text="Draw", command=self.offer_draw).pack(
            side="left", expand=True, fill="x", padx=2
        )
        ttk.Button(game, text="Takeback", command=self.takeback).pack(
            fill="x", padx=6, pady=3
        )
        row2 = ttk.Frame(game)
        row2.pack(fill="x", padx=4, pady=2)
        ttk.Button(row2, text="Reset Board", command=self.reset_board).pack(
            side="left", expand=True, fill="x", padx=2
        )
        ttk.Button(row2, text="Flip Board", command=self.flip_board).pack(
            side="left", expand=True, fill="x", padx=2
        )
        ttk.Button(game, text="Reset View", command=self.reset_view).pack(
            fill="x", padx=6, pady=3
        )
        self.stop_btn = ttk.Button(game, text="Stop Clock", command=self.stop_clock)
        self.stop_btn.pack(fill="x", padx=6, pady=(3, 3))
        ttk.Button(game, text="Reset Clock", command=self.reset_clock).pack(
            fill="x", padx=6, pady=(0, 6)
        )

        settings = ttk.LabelFrame(left, text="Settings")
        settings.pack(fill="x", pady=4)
        ttk.Label(settings, text="Engine side").pack(anchor="w", padx=6, pady=(4, 0))
        ttk.Combobox(
            settings,
            state="readonly",
            textvariable=self.engine_side_var,
            values=["None", "White", "Black"],
        ).pack(fill="x", padx=6)
        self.engine_combo = ttk.Combobox(
            settings, state="readonly", textvariable=self.engine_var
        )
        self.engine_combo.pack(fill="x", padx=6, pady=2)
        er = ttk.Frame(settings)
        er.pack(fill="x", padx=5)
        ttk.Button(er, text="Refresh Engines", command=self.refresh_engines).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Button(er, text="Browse", command=self.browse_engine).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Button(er, text="Load", command=self.load_engine).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Label(settings, text="Opening book").pack(anchor="w", padx=6, pady=(5, 0))
        self.book_combo = ttk.Combobox(
            settings, state="readonly", textvariable=self.book_var
        )
        self.book_combo.pack(fill="x", padx=6)
        br = ttk.Frame(settings)
        br.pack(fill="x", padx=5, pady=2)
        ttk.Button(br, text="Refresh Books", command=self.refresh_books).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Button(br, text="Browse", command=self.browse_book).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Separator(settings).pack(fill="x", padx=6, pady=5)
        preset = ttk.Combobox(
            settings,
            state="readonly",
            values=list(BOARD_COLOR_THEMES),
        )
        preset.set("Wood")
        preset.pack(fill="x", padx=6)
        preset.bind("<<ComboboxSelected>>", lambda e: self.apply_preset(preset.get()))
        cr = ttk.Frame(settings)
        cr.pack(fill="x", padx=5, pady=3)
        ttk.Button(cr, text="Light", command=lambda: self.choose_color("light")).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Button(cr, text="Dark", command=lambda: self.choose_color("dark")).pack(
            side="left", expand=True, fill="x", padx=1
        )
        ttk.Button(
            cr, text="Board Frame", command=lambda: self.choose_color("frame")
        ).pack(side="left", expand=True, fill="x", padx=1)
        background_row = ttk.Frame(settings)
        background_row.pack(fill="x", padx=5, pady=(0, 3))
        ttk.Button(
            background_row,
            text="Background Color",
            command=lambda: self.choose_color("background"),
        ).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(
            background_row,
            text="Background Image",
            command=self.browse_background_image,
        ).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Label(settings, textvariable=self.background_var).pack(
            anchor="w", padx=6, pady=(0, 3)
        )
        display_options = ttk.Frame(settings)
        display_options.pack(fill="x", padx=6, pady=(0, 5))
        ttk.Checkbutton(
            display_options,
            text="Coordinates",
            variable=self.coords_var,
            command=self.toggle_coords,
        ).pack(side="left")
        ttk.Checkbutton(
            display_options,
            text="Sound",
            variable=self.sound_var,
            command=self.toggle_sound,
        ).pack(side="left", padx=(12, 0))
        ttk.Checkbutton(
            display_options,
            text="Move indicator",
            variable=self.move_indicator_var,
            command=self.toggle_move_indicator,
        ).pack(side="left", padx=(12, 0))

        ttk.Label(left, textvariable=self.status_var, wraplength=360).pack(
            fill="x", pady=6
        )
        ttk.Label(
            left,
            text=(
                "Ctrl+F flip | U takeback | right-drag or Ctrl+left-drag rotate | "
                "left-drag empty board pan | wheel zoom"
            ),
            wraplength=360,
        ).pack(fill="x")

        self.move_text = tk.Text(
            right, width=17, font=("Consolas", 10), state="disabled", wrap="none"
        )
        self.move_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.refresh_engines()
        self.refresh_books()
        self.refresh_move_list()
        remembered = self.engine_var.get()
        if remembered and Path(remembered).exists():
            ok, msg = self.engine_manager.load(remembered)
            self.result_text = msg
        if self.background_image_path:
            if not Path(
                self.background_image_path
            ).exists() or not self.load_background_image(
                self.background_image_path, show_error=False
            ):
                self.background_image_path = ""
                self.result_text = "Saved background image was not available"
        self.update_background_label()
        return root

    def ui_tick(self):
        if glfw.window_should_close(self.window):
            try:
                self.ui.destroy()
            except Exception:
                pass
            return
        self.update_clock()
        self.apply_pending_engine_move()
        self.maybe_persist_camera()
        self.white_clock_var.set(self.fmt_clock(self.white_time))
        self.black_clock_var.set(self.fmt_clock(self.black_time))
        self.status_var.set(self.result_text)
        self.draw()
        glfw.swap_buffers(self.window)
        glfw.poll_events()
        self.ui.after(8, self.ui_tick)

    def run(self):
        root = self.build_ui()
        self.ui_tick()
        try:
            root.mainloop()
        finally:
            self.persist()
            self.engine_manager.unload()
            self.delete_background_texture()
            self.piece_renderer.close()
            self.flat_piece_renderer.close()
            try:
                glfw.destroy_window(self.window)
            except Exception:
                pass
            glfw.terminate()

