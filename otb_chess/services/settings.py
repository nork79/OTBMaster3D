"""Application paths, defaults, time controls and configuration storage."""

from pathlib import Path
from dataclasses import dataclass
import json
import math
import sys


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[2]


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
        "background_style": "solid",
        "flat_piece_set": "classic",
        "move_animation_ms": 0,
        "piece_set": "tournament",
        "board_mode": "3D",
        "board_type": "classic",
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



