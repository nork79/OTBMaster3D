"""Bundled chess sound pack and asynchronous playback."""

import logging
import atexit
import sys
import wave
from otb_chess.services.settings import APP_DIR
from otb_chess.services.wave_audio import SoundPlayer, read_clip

_player = SoundPlayer() if sys.platform == 'win32' else None
if _player is not None:
    atexit.register(_player.close)

SOUND_PROFILES = {
    "01_Soft_Lichess_Like": "Soft Lichess-like",
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


def play_sound(path):
    """Mix this event with any playing move; never interrupt the other side."""
    if _player is None:
        return
    try:
        _player.play(path)
    except (OSError, ValueError, EOFError, wave.Error, RuntimeError) as exc:
        logging.getLogger(__name__).warning("Sound playback unavailable: %s: %s", path, exc)


def prepare_sounds(profile):
    """Preload clips and open the output before the first short move sound."""
    if _player is not None:
        try:
            for path in ensure_sounds(profile).values():
                read_clip(path)
            _player.start()
        except (OSError, ValueError, EOFError, wave.Error, RuntimeError) as exc:
            logging.getLogger(__name__).warning('Cannot prepare sound profile: %s', exc)


def stop_sounds():
    if _player is not None:
        _player.close()

