"""Soften audition option 4 and write the selected bundled game sounds."""
from pathlib import Path
import math
import struct
import wave

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'assets' / 'sounds' / 'soft_clack'
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('move', 'capture'):
        source = ROOT / 'sound_options' / f'04_soft_clack_{name}.wav'
        with wave.open(str(source), 'rb') as wav:
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
            rate = wav.getframerate()
            raw = wav.readframes(wav.getnframes())
        samples = struct.unpack('<'+'h'*(len(raw)//2), raw)
        # Two gentle low-pass stages round off the high-frequency contact.
        alpha = 1-math.exp(-2*math.pi*1600/rate)
        first = second = 0.0
        output = []
        for index, sample in enumerate(samples):
            first += alpha*(sample-first)
            second += alpha*(first-second)
            attack = min(1,index/(rate*.003))
            tail = min(1,(len(samples)-1-index)/(rate*.008))
            output.append(round(second*.72*attack*tail))
        path = destination / f'{name}.wav'
        with wave.open(str(path), 'wb') as wav:
            wav.setparams((1,2,rate,0,'NONE','not compressed'))
            wav.writeframes(struct.pack('<'+'h'*len(output), *output))
        rms_ratio = math.sqrt(sum(v*v for v in output)/sum(v*v for v in samples))
        assert max(map(abs,output)) < 32767
        assert rms_ratio < .72
        print(f'{name}: {20*math.log10(rms_ratio):.1f} dB vs original option 4; no clipping')


if __name__ == '__main__':
    main()
