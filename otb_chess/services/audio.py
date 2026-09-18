"""Bundled chess sound pack and asynchronous playback."""

import threading
from otb_chess.services.settings import APP_DIR
try:
    import winsound
except ImportError:
    winsound = None

_sound_lock = threading.Lock()

SOUND_PROFILES = {
    "01_Soft_Lichess_Like": "Soft Lichess-like",
    "02_Crisp_Chesscom_Like": "Crisp Chess.com-like",
    "03_Tournament_Wood": "Tournament Wood",
    "04_Modern_Digital": "Modern Digital",
    "05_Mechanical": "Mechanical",
    "06_Premium_Wood": "Premium Wood",
    "07_Ultra_Minimal": "Ultra Minimal",
    "08_Subtle_Arcade": "Subtle Arcade",
}
DEFAULT_SOUND_PROFILE = "01_Soft_Lichess_Like"


def ensure_sounds(profile=DEFAULT_SOUND_PROFILE):
    if profile not in SOUND_PROFILES:
        profile = DEFAULT_SOUND_PROFILE
    sound_dir = APP_DIR / "assets" / "sounds" / "profiles" / profile
    return {name: sound_dir / (name + ".wav") for name in
            ("move", "capture", "castle", "check", "promote", "illegal", "game_start", "game_end")}


def play_sound_blocking(path):
    if winsound is None:
        return
    with _sound_lock:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)


def play_sound(path):
    threading.Thread(target=play_sound_blocking, args=(path,), daemon=True).start()

