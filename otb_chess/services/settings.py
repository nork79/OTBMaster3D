"""Application paths, defaults, time controls and configuration storage."""

from pathlib import Path
from dataclasses import dataclass
import json
import math
import sys
import os
import logging
import tempfile


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parents[2]


USER_DATA_DIR = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OTBMaster3D"
                 if getattr(sys, "frozen", False) else APP_DIR)
CONFIG_PATH = USER_DATA_DIR / "config.json"


ENGINE_DIR = APP_DIR / "engines"


BOOK_DIR = APP_DIR / "books"


SOUND_DIR = USER_DATA_DIR / "sounds"


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
    "Infinite (clocks disabled)": TimeControl("Infinite (clocks disabled)", 0, 0),
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
        "player_name": "",
        "light_square": list(DEFAULT_LIGHT),
        "dark_square": list(DEFAULT_DARK),
        "frame_color": list(DEFAULT_FRAME),
        "background_color": list(DEFAULT_BACKGROUND),
        "background_image": "",
        "background_style": "solid",
        "flat_piece_set": "textbook",
        "move_animation_ms": 0,
        "piece_set": "tournament",
        "board_mode": "3D",
        "board_type": "tournament",
        "two_d_flipped": False,
        "three_d_facing": None,
        "two_d_scale": 1.0,
        "two_d_pan_x": 0.0,
        "two_d_pan_z": 0.0,
        "window_size": [1280, 840],
        "sidebar_width": 300,
        "bookmark_panel_geometry": None,
        "sidebar_visible": True,
        "focus_mode": False,
        "engine_panel_open": False,
        "engine_analysis_geometry": None,
        "analysis_enabled": False,
        "analysis_options": {"multipv": 3, "depth": 20, "seconds": 1.0, "threads": 1, "hash_mb": 64},
        "always_show_static_evaluation": False,
        "interface_theme": "Dark",
        "show_coordinates": True,
        "show_move_indicator": True,
        "sound_enabled": True,
        "sound_profile": "01_Soft_Lichess_Like",
        "time_control": "Bullet 2+1",
        "engine_side": "Black",
        "engine_enabled": True,
        "engine_path": next((str(p) for p in sorted(ENGINE_DIR.rglob("stockfish*.exe"))), ""),
        "book_path": str(BOOK_DIR / "lichess-all.bin") if (BOOK_DIR / "lichess-all.bin").exists() else "",
        "engine_elo": None,
        "engine_difficulty": "custom",
        "engine_rating": 1500,
        "engine_style": "Balanced",
        "engine_defaults_applied": False,
        "clock_mode": "Online",
        "clock_binding": "Spacebar",
        "custom_initial": 300.0,
        "custom_increment": 0.0,
        "camera_yaw": 0.0,
        "camera_pitch": math.radians(40),
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
    if not config["engine_defaults_applied"]:
        defaults = default_config()
        if not config["engine_path"] and defaults["engine_path"]:
            config["engine_path"] = defaults["engine_path"]
            config["engine_side"] = "Black"
        if not config["book_path"]:
            config["book_path"] = defaults["book_path"]
        config["engine_defaults_applied"] = True
    # Retire unsupported saved presets without silently assigning a new rating.
    from otb_chess.services.difficulty import DIFFICULTIES
    if config.get('engine_difficulty', 'custom') not in (*DIFFICULTIES, 'custom'):
        config['engine_difficulty'] = 'custom'
        config['engine_elo'] = None
        config['engine_path'] = default_config()['engine_path']
    # Resolve the selected preset's actual engine; do not retain a path from
    # another backend after changing preset mappings. Bookmarks remain separate.
    preset = DIFFICULTIES.get(config.get('engine_difficulty'))
    if preset:
        from otb_chess.services.difficulty import engine_path
        config['engine_path'] = str(engine_path(config['engine_difficulty']) or '')
        config['engine_elo'] = preset.rating if preset.engine in ('stockfish', 'fairy-stockfish') else None
    return config


def save_config(config):
    temporary = None
    try:
        payload = json.dumps(config, indent=2, allow_nan=False)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CONFIG_PATH.parent,
                                         prefix=CONFIG_PATH.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, CONFIG_PATH)
        return True
    except (OSError, ValueError, TypeError) as exc:
        logging.getLogger(__name__).warning("Configuration could not be saved: %s", exc)
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).warning("Could not remove configuration temporary file %s", temporary)


def ensure_dirs():
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ENGINE_DIR.mkdir(exist_ok=True)
    BOOK_DIR.mkdir(exist_ok=True)
    SOUND_DIR.mkdir(exist_ok=True)



