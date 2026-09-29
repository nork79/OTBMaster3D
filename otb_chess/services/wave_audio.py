"""Persistent Windows PCM output with overlapping, non-blocking chess sounds."""
import array
import ctypes as c
import logging
import threading
import wave
from functools import lru_cache

RATE = 44100
FRAMES = 882  # Two 20 ms buffers; never queue whole sound clips.


@lru_cache(maxsize=64)
def read_clip(path):
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, RATE):
            raise ValueError(f'Unsupported sound format: {path}')
        return array.array('h', wav.readframes(wav.getnframes()))


class Mixer:
    def __init__(self):
        self.lock = threading.Lock()
        self.voices = []

    def play(self, samples):
        with self.lock:
            # Bound pathological event floods without delaying newer moves.
            self.voices = self.voices[-15:] + [(samples, 0)]

    def clear(self):
        with self.lock:
            self.voices.clear()

    def render(self, frames):
        mixed = [0] * frames
        with self.lock:
            remaining = []
            for samples, offset in self.voices:
                count = min(frames, len(samples) - offset)
                for i in range(count):
                    mixed[i] += samples[offset + i]
                if offset + count < len(samples):
                    remaining.append((samples, offset + count))
            self.voices = remaining
        return array.array('h', (max(-32768, min(32767, x)) for x in mixed)).tobytes()


class _Format(c.Structure):
    _pack_ = 2
    _fields_ = [('tag', c.c_uint16), ('channels', c.c_uint16),
                ('rate', c.c_uint32), ('bytes_per_sec', c.c_uint32),
                ('align', c.c_uint16), ('bits', c.c_uint16), ('extra', c.c_uint16)]


class _Header(c.Structure):
    _fields_ = [('data', c.c_void_p), ('length', c.c_uint32),
                ('recorded', c.c_uint32), ('user', c.c_size_t),
                ('flags', c.c_uint32), ('loops', c.c_uint32),
                ('next', c.c_void_p), ('reserved', c.c_size_t)]


class WaveDevice:
    """Own headers and backing buffers until Windows has released them."""
    def __init__(self):
        self.api = c.WinDLL('winmm')
        self.handle = c.c_void_p()
        self.buffers = []
        self.api.waveOutOpen.argtypes = [c.POINTER(c.c_void_p), c.c_uint32,
            c.POINTER(_Format), c.c_size_t, c.c_size_t, c.c_uint32]
        self.api.waveOutOpen.restype = c.c_uint32
        for name in ('waveOutPrepareHeader', 'waveOutWrite', 'waveOutUnprepareHeader'):
            fn = getattr(self.api, name)
            fn.argtypes = [c.c_void_p, c.POINTER(_Header), c.c_uint32]
            fn.restype = c.c_uint32
        for name in ('waveOutReset', 'waveOutClose'):
            getattr(self.api, name).argtypes = [c.c_void_p]
            getattr(self.api, name).restype = c.c_uint32
        fmt = _Format(1, 1, RATE, RATE * 2, 2, 16, 0)
        self.check(self.api.waveOutOpen(c.byref(self.handle), 0xffffffff, c.byref(fmt), 0, 0, 0))
        try:
            for _ in range(2):
                data = c.create_string_buffer(FRAMES * 2)
                header = _Header(data=c.addressof(data), length=FRAMES * 2)
                self.check(self.api.waveOutPrepareHeader(self.handle, c.byref(header), c.sizeof(header)))
                self.buffers.append((header, data))
        except Exception:
            self.close()
            raise

    @staticmethod
    def check(result):
        if result:
            raise OSError(f'Windows wave output failed ({result})')

    def pump(self, mixer):
        for header, data in self.buffers:
            if not header.flags & 0x10:  # WHDR_INQUEUE; never overwrite in-flight PCM.
                pcm = mixer.render(FRAMES)
                c.memmove(data, pcm, len(pcm))
                self.check(self.api.waveOutWrite(self.handle, c.byref(header), c.sizeof(header)))

    def close(self):
        if self.handle:
            self.check(self.api.waveOutReset(self.handle))
            for header, _ in self.buffers:
                self.check(self.api.waveOutUnprepareHeader(self.handle, c.byref(header), c.sizeof(header)))
            self.buffers.clear()
            self.check(self.api.waveOutClose(self.handle))
            self.handle = c.c_void_p()


class SoundPlayer:
    def __init__(self, device_factory=WaveDevice):
        self.mixer = Mixer()
        self.device_factory = device_factory
        self.stopped = threading.Event()
        self.thread = None
        self.lock = threading.Lock()
        self.error = None

    def start(self):
        with self.lock:
            if self.thread is None or not self.thread.is_alive():
                self.stopped.clear()
                self.error = None
                self.thread = threading.Thread(target=self._run, name='chess-audio', daemon=True)
                self.thread.start()

    def play(self, path):
        samples = read_clip(path)
        self.start()
        self.mixer.play(samples)

    def _run(self):
        try:
            device = self.device_factory()
            try:
                while not self.stopped.is_set():
                    device.pump(self.mixer)
                    self.stopped.wait(.005)
            finally:
                device.close()
        except Exception as exc:
            self.error = str(exc)
            self.mixer.clear()
            logging.getLogger(__name__).warning('Sound playback unavailable: %s', exc)

    def close(self):
        self.stopped.set()
        if self.thread is not None:
            self.thread.join(timeout=2)
        self.mixer.clear()
