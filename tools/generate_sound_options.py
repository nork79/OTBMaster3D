"""Build standalone wooden chess sound auditions (does not change game audio)."""
from pathlib import Path
import math
import random
import struct
import wave
import zipfile

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / 'sound_options'


def impact(seed, base, damping, softness, strength=1.0):
    rng = random.Random(seed)
    length = int(RATE * .48)
    samples = [0.0] * length
    # Uneven, short-lived modes avoid a musical bell or electronic sine beep.
    modes = [(1, .7, 1), (1.47, .45, 1.35), (2.19, .3, 1.7),
             (3.31, .18, 2.2), (4.73, .1, 3.1), (6.17, .06, 4)]
    phases = [rng.uniform(-math.pi, math.pi) for _ in modes]
    filtered = 0.0
    alpha = 1 - math.exp(-2 * math.pi * softness / RATE)
    for i in range(length):
        t = i / RATE
        filtered += alpha * (rng.uniform(-1, 1) - filtered)
        attack = 1 - math.exp(-t / .0015)
        body = sum(amp * math.sin(2 * math.pi * base * ratio * t + phase)
                   * math.exp(-t * damping * decay)
                   for (ratio, amp, decay), phase in zip(modes, phases))
        contact = filtered * (1.8 * math.exp(-t * 170) + .2 * math.exp(-t * 48))
        samples[i] = strength * attack * (body * .36 + contact)
    # Quiet, filtered settling contact adds an irregular physical landing.
    offset = int(RATE * rng.uniform(.016, .027))
    filtered = 0.0
    for i in range(int(.065 * RATE)):
        t = i / RATE
        filtered += alpha * (rng.uniform(-1, 1) - filtered)
        samples[offset+i] += strength * .14 * filtered * (1-math.exp(-t/.001)) * math.exp(-t*95)
    return samples


def write(path, samples):
    # Remove DC and taper the end; retain headroom for every file.
    mean = sum(samples) / len(samples)
    clean = [v - mean for v in samples]
    fade = min(300, len(clean))
    for i in range(fade):
        clean[-fade+i] *= (fade-i-1)/fade
        clean[i] *= i/fade if i < 30 else 1
    assert max(map(abs, clean)) < 1, path
    with wave.open(str(path), 'wb') as f:
        f.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        f.writeframes(struct.pack('<'+'h'*len(clean), *(round(v*32767) for v in clean)))


def main():
    OUT.mkdir(exist_ok=True)
    variants = [('01_felted_wood', 175, 39, 950),
                ('02_warm_walnut', 225, 31, 1500),
                ('03_deep_board', 130, 27, 850),
                ('04_soft_clack', 295, 43, 2200)]
    comparison = []
    for index, (name, base, damping, softness) in enumerate(variants):
        move = impact(410+index, base, damping, softness)
        # Match perceived body energy across options without sharp peaks.
        rms = math.sqrt(sum(v*v for v in move[:6615])/6615)
        gain = min(.105/rms, .72/max(map(abs, move)))
        move = [v*gain for v in move]
        capture = [0.0]*int(RATE*.65)
        for offset, hit in [(0, impact(720+index, base*1.12, damping*1.2, softness, .48)),
                            (int(RATE*.095), impact(930+index, base*.86, damping, softness, 1.12))]:
            for i, v in enumerate(hit):
                capture[offset+i] += v*gain
        peak = max(map(abs, capture))
        if peak > .85:
            capture = [v*.85/peak for v in capture]
        write(OUT / (name+'_move.wav'), move)
        write(OUT / (name+'_capture.wav'), capture)
        # Each group: three moves, a capture, then a longer pause.
        for _ in range(3):
            comparison.extend(move)
            comparison.extend([0.0]*int(RATE*.32))
        comparison.extend(capture)
        comparison.extend([0.0]*int(RATE*1.35))
    write(OUT/'00_comparison.wav', comparison)
    (OUT/'README.txt').write_text(
        'WOODEN CHESS SOUND AUDITIONS\n\n'
        'Synthesized wood-like impacts, not recordings of a physical board.\n'
        '44.1 kHz, mono, 16-bit PCM WAV. Game sounds are unchanged.\n\n'
        '00_comparison.wav plays options 01 through 04 in order.\n'
        'Each group: three moves, one capture, then a pause.\n\n'
        '01 Felted wood: muted, cushioned placement.\n'
        '02 Warm walnut: rounded wooden knock, a little more definition.\n'
        '03 Deep board: lowest, fuller board resonance.\n'
        '04 Soft clack: clearer contact with a short wooden body.\n\n'
        'Individual move and capture files are included for each option.\n', encoding='utf-8')
    with zipfile.ZipFile(OUT/'wooden_chess_options.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.suffix in ('.wav', '.txt'):
                z.write(p, p.name)
    for p in sorted(OUT.glob('*.wav')):
        with wave.open(str(p)) as f:
            print(f'{p.name}: {f.getnframes()/f.getframerate():.2f}s, {f.getnchannels()} channel, {f.getsampwidth()*8}-bit')


if __name__ == '__main__':
    main()
