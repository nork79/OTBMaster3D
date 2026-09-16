"""Generated chess sounds and asynchronous playback."""

import math
import random
import struct
import threading
import wave
from otb_chess.services.settings import SOUND_DIR, ensure_dirs
try:
    import winsound
except ImportError:
    winsound = None

_sound_lock = threading.Lock()


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


def play_sound_blocking(path):
    if winsound is None:
        return
    with _sound_lock:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)


def play_sound(path):
    threading.Thread(target=play_sound_blocking, args=(path,), daemon=True).start()

