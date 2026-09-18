"""Board appearance, asset selection and preference persistence."""

from PIL import Image
from PIL import ImageOps
from pathlib import Path
from tkinter import messagebox
from otb_chess.services.settings import default_config, save_config
from otb_chess.graphics.board_colors import BOARD_COLOR_THEMES
from OpenGL.GL import GL_CLAMP_TO_EDGE, GL_LINEAR, GL_MAX_TEXTURE_SIZE, GL_RGB, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_UNPACK_ALIGNMENT, GL_UNSIGNED_BYTE, glBindTexture, glDeleteTextures, glGenTextures, glGetIntegerv, glPixelStorei, glTexImage2D, glTexParameteri


class AppearanceSettings:
    """Manage visual assets and persist the controller's current preferences."""

    def change_board_mode(self):
        mode = self.board_mode_var.get()
        if mode not in ("2D", "3D") or mode == self.board_mode:
            return
        self.board_mode = mode
        # Cancel only an in-progress pointer gesture, retaining the selected square.
        self.drag_piece = self.drag_world = self.left_down_pos = None
        self.board_pan_drag = self.right_drag = self.ctrl_left_rotate = self.was_drag = False
        self.pan_start_world = None
        self.camera()
        self.update_piece_description()
        self.persist()

    def update_piece_description(self):
        spec = self.piece_sets[self.piece_set]
        text = f"Flat chess symbols in {spec.name} colours." if self.board_mode == "2D" else spec.description
        self.piece_description_var.set(text)

    def change_piece_set(self, _event=None):
        index = self.piece_combo.current()
        if index < 0:
            return
        key = self.piece_set_keys[index]
        spec = self.piece_sets[key]
        try:
            self.make_context_current()
            self.piece_renderer.prepare(spec)
        except Exception as exc:
            self.piece_combo.current(self.piece_set_keys.index(self.piece_set))
            messagebox.showerror("Piece set", f"Could not load {spec.name}:\n{exc}", parent=self.ui)
            return
        self.piece_set = key
        self.update_piece_description()
        self.persist()

    @staticmethod
    def hex(rgb):
        return "#" + "".join(f"{max(0,min(255,round(c*255))):02x}" for c in rgb)

    def color_value(self, which):
        return {
            "light": self.light_square,
            "dark": self.dark_square,
            "frame": self.frame_color,
            "background": self.background_color,
        }[which]

    def set_color_value(self, which, color):
        if which == "light":
            self.light_square = color
        elif which == "dark":
            self.dark_square = color
        elif which == "frame":
            self.frame_color = color
        else:
            self.background_color = color

    def delete_background_texture(self):
        if self.background_texture is not None:
            glDeleteTextures([self.background_texture])
        self.background_texture = None
        self.background_texture_size = None
        self.background_preset_key = None

    def update_background_label(self):
        if not hasattr(self, "background_var"):
            return
        label = (
            Path(self.background_image_path).name
            if self.background_image_path
            else "Solid color"
        )
        self.background_var.set(label)

    def load_background_image(self, path, show_error=True):
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
            max_texture_size = int(glGetIntegerv(GL_MAX_TEXTURE_SIZE))
            if max(image.size) > max_texture_size:
                image.thumbnail(
                    (max_texture_size, max_texture_size), Image.Resampling.LANCZOS
                )
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            width, height = image.size
            texture = int(glGenTextures(1))
            glBindTexture(GL_TEXTURE_2D, texture)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RGB,
                width,
                height,
                0,
                GL_RGB,
                GL_UNSIGNED_BYTE,
                image.tobytes(),
            )
        except Exception as error:
            if show_error:
                messagebox.showerror(
                    "Background image", f"Could not load image:\n{error}"
                )
            return False

        self.delete_background_texture()
        self.background_texture = texture
        self.background_texture_size = (width, height)
        self.background_image_path = str(path)
        self.update_background_label()
        return True

    def apply_preset(self, name):
        self.light_square, self.dark_square, self.frame_color = BOARD_COLOR_THEMES[name]
        self.persist()

    def persist(self):
        save_config(
            {
                **{key: self.cfg.get(key, default_config()[key]) for key in
                   ("window_size", "sidebar_width", "sidebar_visible", "focus_mode", "engine_panel_open", "analysis_enabled", "always_show_static_evaluation", "interface_theme", "engine_elo", "engine_rating", "engine_style", "engine_defaults_applied", "engine_difficulty")},
                "light_square": list(self.light_square),
                "dark_square": list(self.dark_square),
                "frame_color": list(self.frame_color),
                "background_color": list(self.background_color),
                "background_image": self.background_image_path,
                "background_style": self.background_style,
                "piece_set": self.piece_set,
                "flat_piece_set": self.flat_piece_set,
                "move_animation_ms": self.move_animation_ms,
                "board_mode": self.board_mode,
                "board_type": self.board_type,
                "two_d_flipped": self.two_d_flipped,
                "two_d_scale": self.two_d_scale,
                "two_d_pan_x": self.two_d_pan_x,
                "two_d_pan_z": self.two_d_pan_z,
                "show_coordinates": self.show_coordinates,
                "show_move_indicator": self.show_move_indicator,
                "sound_enabled": self.sound_enabled,
                "sound_profile": self.sound_profile,
                "time_control": (
                    self.time_control_var.get()
                    if hasattr(self, "time_control_var") and self.time_control_var
                    else self.cfg["time_control"]
                ),
                "engine_side": (
                    self.engine_side_var.get()
                    if hasattr(self, "engine_side_var") and self.engine_side_var
                    else self.cfg["engine_side"]
                ),
                "engine_path": (
                    self.engine_var.get()
                    if hasattr(self, "engine_var") and self.engine_var
                    else self.cfg.get("engine_path", "")
                ),
                "book_path": (
                    self.book_var.get()
                    if hasattr(self, "book_var") and self.book_var
                    else self.book_path
                ),
                "camera_yaw": self.yaw,
                "camera_pitch": self.pitch,
                "camera_distance": self.distance,
                "camera_pan_x": self.pan_x,
                "camera_pan_z": self.pan_z,
                "clock_mode": (
                    self.clock_mode_var.get()
                    if hasattr(self, "clock_mode_var")
                    else self.clock_mode
                ),
                "clock_binding": (
                    self.clock_binding_var.get()
                    if hasattr(self, "clock_binding_var")
                    else self.clock_binding
                ),
                "custom_initial": (
                    float(self.custom_initial_var.get())
                    if hasattr(self, "custom_initial_var")
                    else self.cfg.get("custom_initial", 300.0)
                ),
                "custom_increment": (
                    float(self.custom_increment_var.get())
                    if hasattr(self, "custom_increment_var")
                    else self.cfg.get("custom_increment", 0.0)
                ),
            }
        )

    def toggle_coords(self):
        self.show_coordinates = bool(self.coords_var.get())
        self.persist()

    def toggle_sound(self):
        self.sound_enabled = bool(self.sound_var.get())
        self.persist()

    def toggle_move_indicator(self):
        self.show_move_indicator = bool(self.move_indicator_var.get())
        self.persist()

