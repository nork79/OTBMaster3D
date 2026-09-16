"""OTBMaster3D: desktop chess with clocks, engines, and OpenGL rendering."""

import colorsys
import json
import math
import random
import struct
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import chess
import chess.engine
import chess.polyglot
import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image, ImageOps, ImageTk
from piece_sets import PieceRenderer, discover_sets
from board_2d import FlatPieceRenderer, flat_square
from version import __version__

try:
    import winsound
except ImportError:
    winsound = None

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
ENGINE_DIR = APP_DIR / "engines"
BOOK_DIR = APP_DIR / "books"
SOUND_DIR = APP_DIR / "sounds"
PIECE_DIR = APP_DIR / "assets" / "pieces"

WIDTH, HEIGHT = 1180, 800
BOARD_Y = 0.0

DEFAULT_LIGHT = (0.77, 0.68, 0.53)
DEFAULT_DARK = (0.31, 0.20, 0.12)
DEFAULT_FRAME = (0.22, 0.11, 0.05)
DEFAULT_BACKGROUND = (0.055, 0.055, 0.065)
SELECT = (0.25, 0.63, 0.92)
LEGAL = (0.24, 0.78, 0.38)
COORD = (0.88, 0.84, 0.72)
TURN_INDICATOR = (1.00, 0.42, 0.08)

GLYPHS = {
    "1": [((0.5, 0.05), (0.5, 0.95)), ((0.35, 0.8), (0.5, 0.95))],
    "2": [
        ((0.15, 0.8), (0.3, 0.95)),
        ((0.3, 0.95), (0.7, 0.95)),
        ((0.7, 0.95), (0.85, 0.8)),
        ((0.85, 0.8), (0.15, 0.05)),
        ((0.15, 0.05), (0.85, 0.05)),
    ],
    "3": [
        ((0.15, 0.95), (0.75, 0.95)),
        ((0.75, 0.95), (0.85, 0.82)),
        ((0.85, 0.82), (0.55, 0.53)),
        ((0.55, 0.53), (0.85, 0.22)),
        ((0.85, 0.22), (0.75, 0.05)),
        ((0.75, 0.05), (0.15, 0.05)),
    ],
    "4": [
        ((0.75, 0.05), (0.75, 0.95)),
        ((0.75, 0.95), (0.15, 0.35)),
        ((0.15, 0.35), (0.9, 0.35)),
    ],
    "5": [
        ((0.85, 0.95), (0.2, 0.95)),
        ((0.2, 0.95), (0.2, 0.55)),
        ((0.2, 0.55), (0.72, 0.55)),
        ((0.72, 0.55), (0.85, 0.42)),
        ((0.85, 0.42), (0.85, 0.18)),
        ((0.85, 0.18), (0.72, 0.05)),
        ((0.72, 0.05), (0.15, 0.05)),
    ],
    "6": [
        ((0.8, 0.88), (0.68, 0.95)),
        ((0.68, 0.95), (0.3, 0.95)),
        ((0.3, 0.95), (0.15, 0.72)),
        ((0.15, 0.72), (0.15, 0.18)),
        ((0.15, 0.18), (0.3, 0.05)),
        ((0.3, 0.05), (0.7, 0.05)),
        ((0.7, 0.05), (0.85, 0.18)),
        ((0.85, 0.18), (0.85, 0.45)),
        ((0.85, 0.45), (0.7, 0.58)),
        ((0.7, 0.58), (0.15, 0.58)),
    ],
    "7": [((0.15, 0.95), (0.85, 0.95)), ((0.85, 0.95), (0.38, 0.05))],
    "8": [
        ((0.3, 0.5), (0.15, 0.65)),
        ((0.15, 0.65), (0.15, 0.82)),
        ((0.15, 0.82), (0.3, 0.95)),
        ((0.3, 0.95), (0.7, 0.95)),
        ((0.7, 0.95), (0.85, 0.82)),
        ((0.85, 0.82), (0.85, 0.65)),
        ((0.85, 0.65), (0.7, 0.5)),
        ((0.7, 0.5), (0.3, 0.5)),
        ((0.3, 0.5), (0.15, 0.35)),
        ((0.15, 0.35), (0.15, 0.18)),
        ((0.15, 0.18), (0.3, 0.05)),
        ((0.3, 0.05), (0.7, 0.05)),
        ((0.7, 0.05), (0.85, 0.18)),
        ((0.85, 0.18), (0.85, 0.35)),
        ((0.85, 0.35), (0.7, 0.5)),
    ],
    "A": [
        ((0.1, 0.05), (0.5, 0.95)),
        ((0.5, 0.95), (0.9, 0.05)),
        ((0.25, 0.45), (0.75, 0.45)),
    ],
    "B": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.15, 0.95), (0.62, 0.95)),
        ((0.62, 0.95), (0.82, 0.8)),
        ((0.82, 0.8), (0.82, 0.62)),
        ((0.82, 0.62), (0.62, 0.5)),
        ((0.62, 0.5), (0.15, 0.5)),
        ((0.62, 0.5), (0.84, 0.37)),
        ((0.84, 0.37), (0.84, 0.18)),
        ((0.84, 0.18), (0.62, 0.05)),
        ((0.62, 0.05), (0.15, 0.05)),
    ],
    "C": [
        ((0.85, 0.82), (0.7, 0.95)),
        ((0.7, 0.95), (0.28, 0.95)),
        ((0.28, 0.95), (0.12, 0.78)),
        ((0.12, 0.78), (0.12, 0.22)),
        ((0.12, 0.22), (0.28, 0.05)),
        ((0.28, 0.05), (0.7, 0.05)),
        ((0.7, 0.05), (0.85, 0.18)),
    ],
    "D": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.15, 0.95), (0.58, 0.95)),
        ((0.58, 0.95), (0.85, 0.7)),
        ((0.85, 0.7), (0.85, 0.3)),
        ((0.85, 0.3), (0.58, 0.05)),
        ((0.58, 0.05), (0.15, 0.05)),
    ],
    "E": [
        ((0.85, 0.95), (0.15, 0.95)),
        ((0.15, 0.95), (0.15, 0.05)),
        ((0.15, 0.5), (0.72, 0.5)),
        ((0.15, 0.05), (0.85, 0.05)),
    ],
    "F": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.15, 0.95), (0.85, 0.95)),
        ((0.15, 0.5), (0.72, 0.5)),
    ],
    "G": [
        ((0.85, 0.8), (0.7, 0.95)),
        ((0.7, 0.95), (0.28, 0.95)),
        ((0.28, 0.95), (0.12, 0.78)),
        ((0.12, 0.78), (0.12, 0.22)),
        ((0.12, 0.22), (0.28, 0.05)),
        ((0.28, 0.05), (0.72, 0.05)),
        ((0.72, 0.05), (0.85, 0.2)),
        ((0.85, 0.2), (0.85, 0.48)),
        ((0.85, 0.48), (0.55, 0.48)),
    ],
    "H": [
        ((0.15, 0.05), (0.15, 0.95)),
        ((0.85, 0.05), (0.85, 0.95)),
        ((0.15, 0.5), (0.85, 0.5)),
    ],
}


@dataclass
class TimeControl:
    name: str
    initial_seconds: float
    increment_seconds: float


TIME_CONTROLS = {
    "Hyperbullet 15+0": TimeControl("Hyperbullet 15+0", 15, 0),
    "Hyperbullet 20+0": TimeControl("Hyperbullet 20+0", 20, 0),
    "Hyperbullet 30+0": TimeControl("Hyperbullet 30+0", 30, 0),
    "Hyperbullet 30+1": TimeControl("Hyperbullet 30+1", 30, 1),
    "Bullet 1+0": TimeControl("Bullet 1+0", 60, 0),
    "Bullet 1+1": TimeControl("Bullet 1+1", 60, 1),
    "Bullet 2+0": TimeControl("Bullet 2+0", 120, 0),
    "Bullet 2+1": TimeControl("Bullet 2+1", 120, 1),
    "Blitz 3+0": TimeControl("Blitz 3+0", 180, 0),
    "Blitz 3+2": TimeControl("Blitz 3+2", 180, 2),
    "Blitz 5+0": TimeControl("Blitz 5+0", 300, 0),
    "Blitz 5+3": TimeControl("Blitz 5+3", 300, 3),
    "Rapid 10+0": TimeControl("Rapid 10+0", 600, 0),
    "Rapid 10+5": TimeControl("Rapid 10+5", 600, 5),
    "Rapid 15+10": TimeControl("Rapid 15+10", 900, 10),
    "Rapid 20+0": TimeControl("Rapid 20+0", 1200, 0),
    "Classical 30+0": TimeControl("Classical 30+0", 1800, 0),
    "Classical 30+20": TimeControl("Classical 30+20", 1800, 20),
    "Classical 45+15": TimeControl("Classical 45+15", 2700, 15),
    "Classical 60+0": TimeControl("Classical 60+0", 3600, 0),
    "Classical 60+30": TimeControl("Classical 60+30", 3600, 30),
    "Classical 90+30": TimeControl("Classical 90+30", 5400, 30),
}


def default_config():
    return {
        "light_square": list(DEFAULT_LIGHT),
        "dark_square": list(DEFAULT_DARK),
        "frame_color": list(DEFAULT_FRAME),
        "background_color": list(DEFAULT_BACKGROUND),
        "background_image": "",
        "piece_set": "tournament",
        "board_mode": "3D",
        "two_d_flipped": False,
        "two_d_scale": 1.0,
        "two_d_pan_x": 0.0,
        "two_d_pan_z": 0.0,
        "window_size": [1280, 840],
        "sidebar_width": 300,
        "sidebar_visible": True,
        "focus_mode": False,
        "engine_panel_open": False,
        "interface_theme": "Blue",
        "show_coordinates": True,
        "show_move_indicator": True,
        "sound_enabled": True,
        "time_control": "Bullet 1+0",
        "engine_side": "None",
        "engine_path": "",
        "book_path": "",
        "clock_mode": "Online",
        "clock_binding": "Spacebar",
        "custom_initial": 300.0,
        "custom_increment": 0.0,
        "camera_yaw": 0.0,
        "camera_pitch": math.radians(34),
        "camera_distance": 12.4,
        "camera_pan_x": 0.0,
        "camera_pan_z": 0.0,
    }


def load_config():
    config = default_config()
    if CONFIG_PATH.exists():
        try:
            saved_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            config.update(
                {key: value for key, value in saved_config.items() if key in config}
            )
        except Exception:
            pass
    return config


def save_config(config):
    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:
        pass


def ensure_dirs():
    ENGINE_DIR.mkdir(exist_ok=True)
    BOOK_DIR.mkdir(exist_ok=True)
    SOUND_DIR.mkdir(exist_ok=True)


def ensure_sounds():
    ensure_dirs()

    def wood(path, pitch, duration, volume, double=False):
        rate = 44100
        total = int(rate * duration)
        rng = random.Random(1000 + int(pitch))
        frames = bytearray()
        for i in range(total):
            t = i / rate
            body = (
                0.75 * math.sin(2 * math.pi * pitch * t)
                + 0.27 * math.sin(2 * math.pi * pitch * 2.08 * t)
            ) * math.exp(-t * 32)
            click = rng.uniform(-1, 1) * math.exp(-t * 120) * 0.55
            second = 0
            if double and t > 0.042:
                tt = t - 0.042
                second = (
                    0.45
                    * (
                        math.sin(2 * math.pi * pitch * 0.78 * tt)
                        + rng.uniform(-0.25, 0.25)
                    )
                    * math.exp(-tt * 38)
                )
            v = max(-1, min(1, (body + click + second) * volume))
            frames += struct.pack("<h", int(32767 * v))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(frames)

    def tone(path):
        rate = 44100
        total = int(rate * 0.12)
        frames = bytearray()
        for i in range(total):
            t = i / rate
            v = (
                0.28
                * (
                    math.sin(2 * math.pi * 800 * t)
                    + 0.4 * math.sin(2 * math.pi * 1200 * t)
                )
                * math.exp(-t * 22)
            )
            frames += struct.pack("<h", int(32767 * max(-1, min(1, v))))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(frames)

    m = SOUND_DIR / "move.wav"
    c = SOUND_DIR / "capture.wav"
    k = SOUND_DIR / "check.wav"
    if not m.exists():
        wood(m, 155, 0.105, 0.72)
    if not c.exists():
        wood(c, 118, 0.145, 0.78, True)
    if not k.exists():
        tone(k)
    return m, c, k


_sound_lock = threading.Lock()


def play_sound_blocking(path):
    if winsound is None:
        return
    with _sound_lock:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)


def play_sound(path):
    threading.Thread(target=play_sound_blocking, args=(path,), daemon=True).start()


def setup_gl(w, h):
    glViewport(0, 0, max(1, w), max(1, h))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(40, w / max(1, float(h)), 0.1, 80)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glEnable(GL_NORMALIZE)
    glEnable(GL_MULTISAMPLE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.28, 0.28, 0.28, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.92, 0.92, 0.92, 1))
    glLightfv(GL_LIGHT1, GL_AMBIENT, (0, 0, 0, 1))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.22, 0.25, 0.30, 1))
    glClearColor(0.055, 0.055, 0.065, 1)


def material(rgb, shininess=35):
    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, (*rgb, 1))
    glMaterialfv(GL_FRONT, GL_SPECULAR, (0.32, 0.32, 0.32, 1))
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)


def draw_box(cx, cy, cz, sx, sy, sz, color):
    material(color, 18)
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    faces = [
        ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
        ((0, -1, 0), [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)]),
        ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]),
        ((0, 0, 1), [(x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1)]),
        ((-1, 0, 0), [(x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1)]),
        ((1, 0, 0), [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)]),
    ]
    glBegin(GL_QUADS)
    for n, vs in faces:
        glNormal3f(*n)
        for v in vs:
            glVertex3f(*v)
    glEnd()


def draw_disc(x, y, z, radius, color, segments=32):
    """Draw a small upward-facing disc on the board plane."""
    glDisable(GL_LIGHTING)
    glColor3f(*color)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x, y, z)
    for step in range(segments + 1):
        angle = 2 * math.pi * step / segments
        glVertex3f(x + radius * math.cos(angle), y, z - radius * math.sin(angle))
    glEnd()
    glEnable(GL_LIGHTING)


def draw_glyph(ch, x, y, z, view_yaw, scale=0.18):
    """Draw a board label flat on the board and readable from the current view."""
    segs = GLYPHS.get(ch.upper())
    if not segs:
        return
    glDisable(GL_LIGHTING)
    glColor3f(*COORD)
    glLineWidth(1.5)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-math.degrees(view_yaw), 0, 1, 0)
    glRotatef(90, 1, 0, 0)
    glScalef(-scale, scale, scale)
    glBegin(GL_LINES)
    for a, b in segs:
        glVertex3f(a[0] - 0.5, a[1] - 0.5, 0)
        glVertex3f(b[0] - 0.5, b[1] - 0.5, 0)
    glEnd()
    glPopMatrix()
    glEnable(GL_LIGHTING)


class EngineManager:
    def __init__(self, app):
        self.app = app
        self.engine = None
        self.path = ""
        self.lock = threading.Lock()
        self.thinking = False

    def load(self, path):
        self.unload()
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(path)
            self.path = path
            return True, f"Loaded engine: {Path(path).name}"
        except Exception as e:
            self.engine = None
            return False, f"Engine load failed: {e}"

    def unload(self):
        with self.lock:
            if self.engine:
                try:
                    self.engine.quit()
                except Exception:
                    pass
            self.engine = None
            self.path = ""
            self.thinking = False

    def request_move(self):
        if not self.engine or self.thinking:
            return
        self.thinking = True
        position = self.app.board.copy()

        def worker():
            try:
                with self.lock:
                    if not self.engine:
                        return
                    result = self.engine.play(
                        position, chess.engine.Limit(time=0.12), info=chess.engine.INFO_ALL
                    )
                self.app.last_engine_search = (position.fen(), result.info)
                self.app.pending_engine_position = position.fen()
                self.app.pending_engine_move = result.move
            except Exception as e:
                self.app.pending_engine_error = str(e)
            finally:
                self.thinking = False

        threading.Thread(target=worker, daemon=True).start()


class Chess3D:
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
        self.board = chess.Board()
        self.board_mode = self.cfg.get("board_mode", "3D")
        if self.board_mode not in ("2D", "3D"):
            self.board_mode = "3D"
        self.two_d_flipped = bool(self.cfg.get("two_d_flipped", False))
        self.two_d_scale = max(0.4, min(2.5, float(self.cfg.get("two_d_scale", 1.0))))
        self.two_d_pan_x = float(self.cfg.get("two_d_pan_x", 0.0))
        self.two_d_pan_z = float(self.cfg.get("two_d_pan_z", 0.0))
        self.flat_piece_renderer = FlatPieceRenderer()
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
        self.background_texture = None
        self.background_texture_size = None
        self.show_coordinates = bool(self.cfg["show_coordinates"])
        self.show_move_indicator = bool(self.cfg.get("show_move_indicator", True))
        self.sound_enabled = bool(self.cfg.get("sound_enabled", True))
        self.yaw = float(self.cfg.get("camera_yaw", 0.0))
        self.pitch = float(self.cfg.get("camera_pitch", math.radians(34)))
        self.distance = float(self.cfg.get("camera_distance", 12.4))
        self.pan_x = float(self.cfg.get("camera_pan_x", 0.0))
        self.pan_z = float(self.cfg.get("camera_pan_z", 0.0))
        if math.cos(self.yaw) < 0:
            # Always open from White's side, while keeping a panned board in the
            # same apparent screen position.
            self.yaw = (self.yaw + math.pi) % math.tau
            self.pan_x = -self.pan_x
            self.pan_z = -self.pan_z
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
        self.sound_move, self.sound_capture, self.sound_check = ensure_sounds()
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

    @staticmethod
    def _s(w):
        return glfw.get_window_user_pointer(w)

    @staticmethod
    def _resize(w, x, y):
        s = Chess3D._s(w)
        s.width, s.height = max(1, x), max(1, y)
        setup_gl(s.width, s.height)

    @staticmethod
    def _scroll(w, dx, dy):
        s = Chess3D._s(w)
        if s.board_mode == "2D":
            s.two_d_scale = max(0.4, min(2.5, s.two_d_scale * math.exp(-max(-10, min(10, dy)) * 0.1)))
        else:
            s.distance = max(7, min(22, s.distance - dy * 0.7))
        s.mark_camera_dirty()

    @staticmethod
    def _mouse(w, b, a, m):
        s = Chess3D._s(w)
        p = glfw.get_cursor_pos(w)
        if a == glfw.PRESS and s.clock_mode == "OTB":
            binding_map = {
                "Middle Mouse": glfw.MOUSE_BUTTON_MIDDLE,
                "Mouse Button 4": glfw.MOUSE_BUTTON_4,
                "Mouse Button 5": glfw.MOUSE_BUTTON_5,
            }
            if s.clock_binding in binding_map and b == binding_map[s.clock_binding]:
                s.hit_clock()
                return
        if b == glfw.MOUSE_BUTTON_LEFT:
            if a == glfw.PRESS and (m & glfw.MOD_CONTROL):
                s.ctrl_left_rotate = True
                s.last_mouse = p
                s.board_pan_drag = False
                s.drag_piece = None
                return
            elif a == glfw.RELEASE and s.ctrl_left_rotate:
                s.ctrl_left_rotate = False
                s.mark_camera_dirty()
                return
            elif a == glfw.PRESS:
                s.left_press(p)
            elif a == glfw.RELEASE:
                s.left_release(p)
        elif b == glfw.MOUSE_BUTTON_RIGHT:
            if a == glfw.PRESS:
                s.right_drag = True
                s.last_mouse = p
            elif a == glfw.RELEASE:
                s.right_drag = False
                s.mark_camera_dirty()

    @staticmethod
    def _cursor(w, x, y):
        s = Chess3D._s(w)
        if s.right_drag or s.ctrl_left_rotate:
            if s.board_mode == "2D":
                return
            dx = x - s.last_mouse[0]
            dy = y - s.last_mouse[1]
            s.yaw += dx * 0.009
            s.pitch = max(math.radians(14), min(math.radians(72), s.pitch + dy * 0.007))
            s.last_mouse = (x, y)
            s.mark_camera_dirty()
        elif glfw.get_mouse_button(w, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS:
            s.left_motion((x, y))

    @staticmethod
    def _key(w, key, sc, action, mods):
        if action != glfw.PRESS:
            return
        s = Chess3D._s(w)
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(w, True)
        elif (
            key == glfw.KEY_SPACE
            and s.clock_mode == "OTB"
            and s.clock_binding == "Spacebar"
        ):
            s.hit_clock()
        elif key == glfw.KEY_F and mods & glfw.MOD_CONTROL:
            s.flip_board()
        elif key == glfw.KEY_U:
            s.takeback()

    def mark_camera_dirty(self):
        self.camera_dirty = True
        self.last_camera_change = time.perf_counter()

    def maybe_persist_camera(self):
        if self.camera_dirty and time.perf_counter() - self.last_camera_change > 0.35:
            self.camera_dirty = False
            self.persist()

    def camera(self):
        aspect = self.width / max(1, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.board_mode == "2D":
            half_x = 4.65 * self.two_d_scale * max(1, aspect)
            half_z = 4.65 * self.two_d_scale * max(1, 1 / aspect)
            glOrtho(-half_x, half_x, -half_z, half_z, 0.1, 80)
        else:
            gluPerspective(40, aspect, 0.1, 80)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if self.board_mode == "2D":
            gluLookAt(0, 10, 0, 0, 0, 0, 0, 0, -1 if self.two_d_flipped else 1)
            return
        cp = math.cos(self.pitch)
        distance = self.distance * max(1, 1.48 / aspect)
        eye = (
            math.sin(self.yaw) * cp * distance,
            math.sin(self.pitch) * distance + self.target_y,
            -math.cos(self.yaw) * cp * distance,
        )
        gluLookAt(*eye, 0, self.target_y, 0, 0, 1, 0)
        glLightfv(GL_LIGHT0, GL_POSITION, (4, 9, -6, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, (-5, 5, 5, 1))

    def draw_background(self):
        glClearColor(*self.background_color, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if (getattr(self, "preview_background_color", False)
                or self.background_texture is None or self.background_texture_size is None):
            return

        image_width, image_height = self.background_texture_size
        image_aspect = image_width / image_height
        viewport_aspect = self.width / max(1, self.height)
        u0, u1, v0, v1 = 0.0, 1.0, 0.0, 1.0
        if image_aspect > viewport_aspect:
            visible_width = viewport_aspect / image_aspect
            u0 = (1.0 - visible_width) / 2
            u1 = 1.0 - u0
        else:
            visible_height = image_aspect / viewport_aspect
            v0 = (1.0 - visible_height) / 2
            v1 = 1.0 - v0

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glDepthMask(GL_FALSE)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(-1, 1, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.background_texture)
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(u0, v0)
        glVertex2f(-1, -1)
        glTexCoord2f(u1, v0)
        glVertex2f(1, -1)
        glTexCoord2f(u1, v1)
        glVertex2f(1, 1)
        glTexCoord2f(u0, v1)
        glVertex2f(-1, 1)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glDepthMask(GL_TRUE)
        glEnable(GL_CULL_FACE)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def draw_board(self):
        flat = self.board_mode == "2D"
        yaw = self.view_yaw()
        if flat:
            flat_square(0, 0, 8.72, 8.72, self.frame_color, y=0)
        else:
            draw_box(0, -0.14, 0, 8.72, 0.28, 8.72, self.frame_color)
        legal = self.legal_targets()
        for r in range(8):
            for f in range(8):
                sq = chess.square(f, r)
                col = self.dark_square if (f + r) % 2 == 0 else self.light_square
                if sq == self.selected:
                    col = SELECT
                elif sq in legal:
                    col = tuple(0.60 * c + 0.40 * l for c, l in zip(col, LEGAL))
                if flat:
                    flat_square(3.5 - f, r - 3.5, 1, 1, col)
                else:
                    draw_box(3.5 - f, 0.005, r - 3.5, 0.995, 0.025, 0.995, col)

        if self.show_move_indicator:
            indicator_x = 4.17 if math.cos(yaw) >= 0 else -4.17
            indicator_z = -4.17 if self.board.turn == chess.WHITE else 4.17
            draw_disc(indicator_x, 0.04, indicator_z, 0.055, TURN_INDICATOR)

        if self.show_coordinates:
            # Screen-left is +X from White's initial view, so files are stored in
            # reverse world-X order. Keep them on the edge nearest the viewer so
            # White sees A..H and Black sees H..A after the board is flipped.
            file_label_z = -4.12 if math.cos(yaw) >= 0 else 4.12
            for f, ch in enumerate("HGFEDCBA"):
                draw_glyph(ch, f - 3.5, 0.035, file_label_z, yaw, 0.18)
            # Rank 1 belongs at the near-left corner and increases away from White.
            for r, ch in enumerate("12345678"):
                rank_label_x = -4.12 if flat and self.two_d_flipped else 4.12
                draw_glyph(ch, rank_label_x, 0.035, r - 3.5, yaw, 0.18)

    def draw(self):
        self.draw_background()
        self.camera()
        glPushMatrix()
        pan_x, pan_z = self.view_pan()
        glTranslatef(pan_x, 0, pan_z)
        self.draw_board()
        for sq, p in self.board.piece_map().items():
            if self.drag_piece == sq and self.was_drag and self.drag_world:
                continue
            self.draw_game_piece(
                p,
                3.5 - chess.square_file(sq),
                chess.square_rank(sq) - 3.5,
                sq == self.selected,
            )
        if self.drag_piece is not None and self.was_drag and self.drag_world:
            p = self.board.piece_at(self.drag_piece)
            if p:
                x, _, z = self.drag_world
                self.draw_game_piece(
                    p,
                    max(-3.85, min(3.85, x - pan_x)),
                    max(-3.85, min(3.85, z - pan_z)),
                    True,
                )
        glPopMatrix()

    def draw_game_piece(self, piece, x, z, lifted=False):
        spec = self.piece_sets[self.piece_set]
        if self.board_mode == "2D":
            self.flat_piece_renderer.draw(spec, piece, x, z, self.view_yaw(), lifted)
        else:
            self.piece_renderer.draw(spec, piece, x, z, lifted)

    def make_context_current(self):
        if self.render_widget is not None:
            self.render_widget.makeCurrent()
        else:
            glfw.make_context_current(self.window)

    def view_pan(self):
        return (self.two_d_pan_x, self.two_d_pan_z) if self.board_mode == "2D" else (self.pan_x, self.pan_z)

    def view_yaw(self):
        if self.board_mode == "2D":
            return math.pi if self.two_d_flipped else 0
        return self.yaw

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

    def ray_to_board(self, mx, my):
        # Input positions are window coordinates; OpenGL uses framebuffer pixels.
        self.make_context_current()
        if self.render_widget is not None:
            window_width, window_height = self.render_widget.width(), self.render_widget.height()
        else:
            window_width, window_height = glfw.get_window_size(self.window)
        mx *= self.width / max(1, window_width)
        my *= self.height / max(1, window_height)
        self.camera()
        vp = glGetIntegerv(GL_VIEWPORT)
        model = glGetDoublev(GL_MODELVIEW_MATRIX)
        proj = glGetDoublev(GL_PROJECTION_MATRIX)
        near = gluUnProject(mx, vp[3] - my, 0, model, proj, vp)
        far = gluUnProject(mx, vp[3] - my, 1, model, proj, vp)
        dy = far[1] - near[1]
        if abs(dy) < 1e-8:
            return None
        t = (BOARD_Y - near[1]) / dy
        if t < 0:
            return None
        return (
            near[0] + t * (far[0] - near[0]),
            BOARD_Y,
            near[2] + t * (far[2] - near[2]),
        )

    def square_at_mouse(self, pos):
        p = self.ray_to_board(*pos)
        if not p:
            return None
        pan_x, pan_z = self.view_pan()
        f = 7 - int(math.floor((p[0] - pan_x) + 4))
        r = int(math.floor((p[2] - pan_z) + 4))
        return chess.square(f, r) if 0 <= f < 8 and 0 <= r < 8 else None

    def legal_targets(self):
        if self.selected is None:
            return set()
        return {
            m.to_square
            for m in self.board.legal_moves
            if m.from_square == self.selected
        }

    def human_can_move(self):
        engine_has_turn = (
            self.game_started
            and self.engine_manager.engine is not None
            and self.engine_side == self.board.turn
        )
        return (
            not self.game_over and not self.awaiting_clock_press and not engine_has_turn
        )

    def try_move(self, fr, to, is_engine=False):
        if fr is None or to is None or fr == to:
            return False
        if not is_engine and not self.human_can_move():
            return False
        p = self.board.piece_at(fr)
        if not p:
            return False
        promo = (
            chess.QUEEN
            if p.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7)
            else None
        )
        mv = chess.Move(fr, to, promotion=promo)
        if mv not in self.board.legal_moves:
            return False
        mover = self.board.turn
        capture = self.board.is_capture(mv)
        if self.game_started:
            self.clock_history.append(
                (self.white_time, self.black_time, self.active_clock_color)
            )
        self.board.push(mv)
        if self.game_started:
            if len(self.board.move_stack) == 1:
                self.last_clock_tick = time.perf_counter()
            if self.clock_mode == "OTB" and not is_engine:
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
        self.play_game_sound(self.sound_capture if capture else self.sound_move)
        if self.board.is_check():
            threading.Timer(
                0.15, lambda: self.play_game_sound(self.sound_check)
            ).start()
        self.refresh_move_list()
        self.update_game_end()
        if self.game_started and not self.game_over and not self.awaiting_clock_press:
            self.maybe_request_engine_move()
        return True

    def hit_clock(self):
        if (
            self.clock_mode != "OTB"
            or not self.game_started
            or self.game_over
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

    def update_game_end(self):
        if self.board.is_checkmate():
            self.game_over = True
            self.game_started = False
            self.result_text = "Checkmate"
        elif self.board.is_stalemate():
            self.game_over = True
            self.game_started = False
            self.result_text = "Stalemate"
        elif self.board.is_insufficient_material():
            self.game_over = True
            self.game_started = False
            self.result_text = "Draw - insufficient material"

    def play_game_sound(self, path):
        if self.sound_enabled:
            play_sound(path)

    def left_press(self, pos):
        sq = self.square_at_mouse(pos)
        self.left_down_pos = pos
        self.was_drag = False
        if (
            self.human_can_move()
            and self.selected is not None
            and sq in self.legal_targets()
        ):
            if self.try_move(self.selected, sq):
                self.selected = None
                return
        p = self.board.piece_at(sq) if sq is not None else None
        if self.human_can_move() and p and p.color == self.board.turn:
            self.selected = sq
            self.drag_piece = sq
            self.drag_world = self.ray_to_board(*pos)
            self.board_pan_drag = False
        else:
            self.board_pan_drag = True
            self.pan_start_world = self.ray_to_board(*pos)
            self.pan_start_offset = self.view_pan()

    def left_motion(self, pos):
        if self.left_down_pos:
            dx = pos[0] - self.left_down_pos[0]
            dy = pos[1] - self.left_down_pos[1]
            if dx * dx + dy * dy > 16:
                self.was_drag = True
        if self.drag_piece is not None:
            self.drag_world = self.ray_to_board(*pos)
        elif self.board_pan_drag and self.was_drag:
            cur = self.ray_to_board(*pos)
            if cur:
                if self.pan_start_world is None:
                    self.pan_start_world = cur
                    self.pan_start_offset = self.view_pan()
                else:
                    pan_x = self.pan_start_offset[0] + (
                        cur[0] - self.pan_start_world[0]
                    )
                    pan_z = self.pan_start_offset[1] + (
                        cur[2] - self.pan_start_world[2]
                    )
                    if self.board_mode == "2D":
                        self.two_d_pan_x, self.two_d_pan_z = pan_x, pan_z
                    else:
                        self.pan_x, self.pan_z = pan_x, pan_z
                    self.mark_camera_dirty()

    def left_release(self, pos):
        if self.drag_piece is not None:
            src = self.drag_piece
            dst = self.square_at_mouse(pos)
            if self.was_drag:
                moved = self.try_move(src, dst)
                self.selected = None if moved else src
        elif self.board_pan_drag and self.was_drag:
            self.mark_camera_dirty()
        self.drag_piece = self.drag_world = self.left_down_pos = None
        self.board_pan_drag = False
        self.pan_start_world = None
        self.was_drag = False

    def refresh_move_list(self):
        if not hasattr(self, "move_text"):
            return
        b = chess.Board()
        sans = []
        for mv in self.board.move_stack:
            sans.append(b.san(mv))
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

    def takeback(self):
        if self.engine_manager.thinking or not self.board.move_stack:
            return
        pops = (
            2 if self.engine_side is not None and len(self.board.move_stack) >= 2 else 1
        )
        for _ in range(pops):
            if self.board.move_stack:
                self.board.pop()
            if self.clock_history:
                self.white_time, self.black_time, self.active_clock_color = (
                    self.clock_history.pop()
                )
        self.selected = None
        self.game_over = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.result_text = "Move taken back"
        self.last_clock_tick = time.perf_counter()
        self.refresh_move_list()

    def reset_board(self):
        self.board.reset()
        self.clock_history.clear()
        self.selected = None
        self.game_started = False
        self.game_over = False
        self.clock_paused = False
        self.awaiting_clock_press = False
        self.awaiting_clock_color = None
        self.result_text = "Board reset"
        self.refresh_move_list()

    def reset_view(self):
        if self.board_mode == "2D":
            self.two_d_flipped = False
            self.two_d_scale = 1.0
            self.two_d_pan_x = self.two_d_pan_z = 0.0
            self.persist()
            self.result_text = "View reset"
            return
        self.yaw = 0.0
        self.pitch = math.radians(34)
        self.distance = 12.4
        self.pan_x = 0.0
        self.pan_z = 0.0
        self.mark_camera_dirty()
        self.persist()
        self.result_text = "View reset"

    def flip_board(self):
        if self.board_mode == "2D":
            self.two_d_flipped = not self.two_d_flipped
            self.two_d_pan_x = -self.two_d_pan_x
            self.two_d_pan_z = -self.two_d_pan_z
            self.persist()
            return
        self.yaw = (self.yaw + math.pi) % math.tau
        self.pan_x = -self.pan_x
        self.pan_z = -self.pan_z
        self.mark_camera_dirty()

    def stop_clock(self):
        if not self.game_started or self.game_over:
            return
        self.clock_paused = not self.clock_paused
        self.last_clock_tick = time.perf_counter()
        self.result_text = "Clock stopped" if self.clock_paused else "Clock resumed"
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

    def start_game(self):
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

        self.board.reset()
        self.clock_history.clear()
        self.white_time = time_control.initial_seconds
        self.black_time = time_control.initial_seconds
        self.increment = time_control.increment_seconds
        self.active_clock_color = chess.WHITE
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
        self.refresh_move_list()
        self.persist()
        self.maybe_request_engine_move()

    def resign(self):
        if self.game_started and not self.game_over:
            loser = "White" if self.board.turn == chess.WHITE else "Black"
            self.game_started = False
            self.game_over = True
            self.result_text = f"{loser} resigned"

    def offer_draw(self):
        if self.game_started and not self.game_over:
            self.result_text = "Draw offered"

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
        else:
            self.black_time = max(0, self.black_time - e)
            if self.black_time <= 0:
                self.game_started = False
                self.game_over = True
                self.result_text = "Black flagged"

    @staticmethod
    def fmt_clock(s):
        s = max(0, s)
        return (
            f"{int(s)//60}:{s%60:04.1f}" if s < 20 else f"{int(s)//60}:{int(s)%60:02d}"
        )

    def pick_book_move(self):
        path = self.book_var.get() if self.book_var else self.book_path
        if not path or not Path(path).exists():
            return None
        try:
            with chess.polyglot.open_reader(path) as rd:
                es = list(rd.find_all(self.board))
                if not es:
                    return None
                return random.choices(es, weights=[max(1, e.weight) for e in es], k=1)[
                    0
                ].move
        except Exception:
            return None

    def maybe_request_engine_move(self):
        if not (
            self.game_started
            and not self.game_over
            and self.engine_side is not None
            and self.board.turn == self.engine_side
        ):
            return
        bm = self.pick_book_move()
        if bm:
            self.pending_engine_position = self.board.fen()
            self.pending_engine_move = bm
        elif self.engine_manager.engine:
            self.engine_manager.request_move()

    def apply_pending_engine_move(self):
        if self.pending_engine_error:
            self.result_text = f"Engine error: {self.pending_engine_error}"
            self.pending_engine_error = None
        mv = self.pending_engine_move
        if mv is None:
            return
        self.pending_engine_move = None
        source = self.pending_engine_position
        self.pending_engine_position = None
        if source is not None and source != self.board.fen():
            return
        if mv in self.board.legal_moves:
            self.try_move(mv.from_square, mv.to_square, True)

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

    def choose_color(self, which):
        original_color = self.color_value(which)
        original_background_image = self.background_image_path
        if which == "background":
            self.delete_background_texture()
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

    def delete_background_texture(self):
        if self.background_texture is not None:
            glDeleteTextures([self.background_texture])
        self.background_texture = None
        self.background_texture_size = None

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

    def apply_preset(self, name):
        presets = {
            "Wood": ((0.77, 0.68, 0.53), (0.31, 0.20, 0.12), (0.22, 0.11, 0.05)),
            "Tournament Green": (
                (0.92, 0.90, 0.78),
                (0.30, 0.48, 0.34),
                (0.16, 0.22, 0.14),
            ),
            "Blue": ((0.88, 0.90, 0.92), (0.31, 0.43, 0.57), (0.14, 0.18, 0.24)),
            "Grey": ((0.82, 0.82, 0.82), (0.35, 0.35, 0.35), (0.18, 0.18, 0.18)),
        }
        self.light_square, self.dark_square, self.frame_color = presets[name]
        self.persist()

    def persist(self):
        save_config(
            {
                **{key: self.cfg.get(key, default_config()[key]) for key in
                   ("window_size", "sidebar_width", "sidebar_visible", "focus_mode", "engine_panel_open", "interface_theme")},
                "light_square": list(self.light_square),
                "dark_square": list(self.dark_square),
                "frame_color": list(self.frame_color),
                "background_color": list(self.background_color),
                "background_image": self.background_image_path,
                "piece_set": self.piece_set,
                "board_mode": self.board_mode,
                "two_d_flipped": self.two_d_flipped,
                "two_d_scale": self.two_d_scale,
                "two_d_pan_x": self.two_d_pan_x,
                "two_d_pan_z": self.two_d_pan_z,
                "show_coordinates": self.show_coordinates,
                "show_move_indicator": self.show_move_indicator,
                "sound_enabled": self.sound_enabled,
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
            values=["Spacebar", "Middle Mouse", "Mouse Button 4", "Mouse Button 5"],
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
            values=["Wood", "Tournament Green", "Blue", "Grey"],
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


if __name__ == "__main__":
    from desktop_ui import run
    run()
