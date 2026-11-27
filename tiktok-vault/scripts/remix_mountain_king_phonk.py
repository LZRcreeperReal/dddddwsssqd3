#!/usr/bin/env python3
"""Drift phonk remix of Grieg - In the Hall of the Mountain King (public domain composition).
Everything is synthesized with phonk_kit. usage: python3 remix_mountain_king_phonk.py out.wav
"""
import sys, wave
import numpy as np
from phonk_kit import *  # noqa

BPM = 150
E8 = 60 / BPM / 2            # eighth note
BAR = E8 * 8
S16 = E8 / 2

# theme (midi, length in eighths), B minor
THEME = [
    (59, 1), (61, 1), (62, 1), (64, 1), (66, 1), (62, 1), (66, 2),
    (65, 1), (61, 1), (65, 2), (64, 1), (60, 1), (64, 2),
    (59, 1), (61, 1), (62, 1), (64, 1), (66, 1), (62, 1), (66, 1), (71, 1),
    (69, 1), (66, 1), (62, 1), (66, 1), (69, 4),
]
# 808 roots per half bar (4 bars x 2)
ROOTS = [35, 35, 37, 36, 35, 35, 38, 42]

N_BARS = 23
mix = {k: np.zeros(int((N_BARS * BAR + 4) * SR), np.float32) for k in ("drums", "mel", "bass", "pad", "fx")}
kick_times = []


def put(bus, x, at, gain=1.0):
    i = int(at * SR)
    j = min(i + len(x), len(mix[bus]))
    if i < len(mix[bus]):
        mix[bus][i:j] += x[:j - i] * gain


def bar_t(b, step16=0):
    return b * BAR + step16 * S16


def melody(start_bar, bars, octave=12, gain=1.0, dist=3.0, bus="mel"):
    t = start_bar * BAR
    end = (start_bar + bars) * BAR
    while t < end - 1e-6:
        for m, l in THEME:
            if t >= end - 1e-6:
                break
            put(bus, cowbell(m + octave, min(l * E8 + .05, .6), dist), t, gain)
            t += l * E8


def bass(start_bar, bars, gain=1.0):
    for b in range(bars):
        for h in range(2):
            r = ROOTS[((start_bar + b) % 4) * 2 + h]
            prev = ROOTS[((start_bar + b) % 4) * 2 + h - 1]
            t0 = bar_t(start_bar + b, h * 8)
            put("bass", bass808(r, E8 * 3, glide_from=prev if prev != r else None), t0, gain)
            put("bass", bass808(r, E8 * 1.5), t0 + E8 * 3, gain * .8)


def drums(start_bar, bars, busy=False):
    K, C, H = kick(), clap(), hat()
    sn = snare()
    for b in range(bars):
        bb = start_bar + b
        for s in (0, 6, 10) + ((14,) if busy and b % 2 else ()):
            put("drums", K, bar_t(bb, s)); kick_times.append(bar_t(bb, s))
        put("drums", C, bar_t(bb, 8), .9); put("drums", sn, bar_t(bb, 8), .6)
        for s in range(0, 16, 2 if not busy else 1):
            put("drums", H, bar_t(bb, s), .8 if s % 4 == 0 else .5)
        if b % 2 == 1:  # hat roll at the end of every 2nd bar (67)
            for k in range(6):
                put("drums", hat(.03), bar_t(bb, 13) + k * S16 / 2, .5)
        put("drums", hat(open_=True), bar_t(bb, 14), .4)


def reverb(x, secs=2.2, wet=.35):
    n = int(secs * SR)
    ir = rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / SR * 3.5 / secs * 2)
    ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return (x * (1 - wet) + y.astype(np.float32) * wet * 2).astype(np.float32)


# ---------------- arrangement ----------------
# INTRO bars 0-3: rev, vinyl, muffled reverb cowbell, dark pad, riser + turbo, silence on last beat
put("fx", rev(2.2), 0, .55)
put("pad", pad([47, 50, 54], 4 * BAR - E8 * 2), 0, 1.0)
intro_mel = np.zeros_like(mix["mel"]); mix["_tmp"] = intro_mel
melody(0, 4, octave=12, gain=.9, dist=1.5, bus="_tmp")
cut = int((4 * BAR - E8 * 2) * SR)
intro_mel[cut:] = 0
mix["mel"] += reverb(lp(intro_mel, 700 + np.linspace(0, 1, len(intro_mel)) ** 8 * 0), 2.5, .5)
del mix["_tmp"]
for b in range(4):
    put("bass", bass808(35, BAR * .9, dist=1.5), bar_t(b), .3)  # sub pulse (79)
put("fx", riser(BAR * 2 - E8 * 2), bar_t(2), .8)
put("fx", turbo_spool(BAR - E8 * 2), bar_t(3), .7)

# DROP 1 bars 4-11
put("fx", boom(), bar_t(4), .9); put("drums", crash(), bar_t(4), 1.0)
put("fx", tire_screech(1.4), bar_t(4), .55)
drums(4, 8); melody(4, 8); bass(4, 8)
put("fx", bov(), bar_t(7, 12), .6)
put("fx", flutter(), bar_t(9, 12), .6)
put("fx", exhaust_pops(1.0), bar_t(11, 8), .6)

# BREAK bars 12-13: bell + 808 only, then snare roll + riser, 1 beat silence
melody(12, 2, octave=12, gain=.8)
bass(12, 1, .8)
put("fx", whoosh(.5), bar_t(12) - .25, .6)
for k in range(16):  # snare roll 1/16 -> faster (21)
    step = S16 if k < 8 else S16 / 2
    t = bar_t(13) + (k * S16 if k < 8 else 8 * S16 + (k - 8) * S16 / 2)
    if t < bar_t(13, 12):
        put("drums", snare(), t, .25 + .04 * k)
put("fx", riser(BAR - E8 * 2), bar_t(13), .7)
for k in ("mel", "bass"):
    mix[k][int(bar_t(13, 12) * SR):int(bar_t(14) * SR)] = 0  # silence before drop (100)

# DROP 2 bars 14-21: busier, extra high bell layer
put("fx", backfire(), bar_t(14), .8); put("fx", boom(), bar_t(14), .9); put("drums", crash(), bar_t(14), 1.0)
put("fx", tire_screech(1.6), bar_t(14), .5); put("fx", tire_screech(1.2), bar_t(18), .45)
drums(14, 8, busy=True); melody(14, 8); melody(18, 4, octave=24, gain=.35); bass(14, 8)
put("fx", bov(), bar_t(17, 12), .6); put("fx", exhaust_pops(1.2, 8), bar_t(21, 4), .6)

# OUTRO bar 22: last hit + downlifter, tape stop on the whole mix later
put("fx", boom(), bar_t(22), .8); put("fx", downlifter(), bar_t(22), .6)
put("mel", cowbell(71, .6), bar_t(22), .8)

# ---------------- mixdown ----------------
# sidechain (98): duck melodic buses on each kick
duck = np.ones_like(mix["mel"])
dk = 1 - .55 * np.exp(-np.arange(int(.18 * SR)) / SR * 22)
for kt in kick_times:
    i = int(kt * SR); duck[i:i + len(dk)] = np.minimum(duck[i:i + len(dk)], dk[:len(duck) - i])
out = (mix["drums"] * .85 + mix["mel"] * .9 * duck + hp(mix["bass"], 30) * .6 * duck + mix["pad"] * duck
       + mix["fx"] * .8)
out += vinyl(len(out) / SR) * .6  # crackle + hiss under everything (1, 95)
end = int((N_BARS * BAR + 1.5) * SR)
out = out[:end]
# tape stop on the outro (28)
out = tape_stop(out, BAR + 1.5)
out = out / np.abs(out).max()
out = clip(out * 1.15, 1.5)  # loud + a bit crunchy master
out = out / np.abs(out).max() * 0.95

path = sys.argv[1] if len(sys.argv) > 1 else "mountain_king_phonk.wav"
with wave.open(path, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print("wrote", path, f"{len(out) / SR:.1f}s")
