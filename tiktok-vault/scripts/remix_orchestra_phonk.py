#!/usr/bin/env python3
"""Drift phonk remix built on a REAL orchestra recording (sample-based, like real phonk).

Default source: Musopen's public-domain Peer Gynt session, "premix_03" = In the Hall of the Mountain King.
Loops are beat-tracked, time-stretched to the phonk BPM, then drums / 808 / cowbell / vocal chops / car sfx go on top.

usage: python3 remix_orchestra_phonk.py --left L.wav --right R.wav --vox vox_dir --out out.wav
"""
import argparse, glob, os, wave
import numpy as np, librosa
from phonk_kit import *  # noqa  (SR=44100)

ap = argparse.ArgumentParser()
ap.add_argument("--left", required=True); ap.add_argument("--right", required=True)
ap.add_argument("--vox", required=True, help="folder of raw vocal tag wavs")
ap.add_argument("--out", required=True)
ap.add_argument("--bpm", type=float, default=155)
# loops: start,end in source seconds, and how many beats they hold
ap.add_argument("--intro", default="26.37,30.87,8")      # quiet theme, half phrase -> half-time intro
ap.add_argument("--loud1", default="155.89,160.57,16")   # climax
ap.add_argument("--loud2", default="130.24,135.04,16")   # climax variation
ap.add_argument("--ending", default="168.0,177.6")        # final chords
a = ap.parse_args()

BEAT = 60 / a.bpm; BAR = BEAT * 4; S16 = BEAT / 4

print("loading orchestra...")
L, _ = librosa.load(a.left, sr=SR, mono=True, res_type="soxr_hq")
R, _ = librosa.load(a.right, sr=SR, mono=True, res_type="soxr_hq")
ORC = np.stack([L, R])


def seg(t0, t1):
    return ORC[:, int(t0 * SR):int(t1 * SR)]


def stretch_to(x, dur):
    rate = x.shape[1] / SR / dur
    y = np.stack([librosa.effects.time_stretch(c, rate=rate, n_fft=4096) for c in x])
    n = int(round(dur * SR))
    y = y[:, :n] if y.shape[1] >= n else np.pad(y, ((0, 0), (0, n - y.shape[1])))
    f = int(.004 * SR)  # tiny fades so loops don't click
    y[:, :f] *= np.linspace(0, 1, f); y[:, -f:] *= np.linspace(1, 0, f)
    return y.astype(np.float32)


def loop(spec, beats_out):
    t0, t1, beats = map(float, spec.split(","))
    return stretch_to(seg(t0, t1), beats_out * BEAT)


def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-9) * peak


print("stretching loops...")
intro = norm(loop(a.intro, 16))          # 8 source beats -> 16 beats (half-time)
loud1 = norm(loop(a.loud1, 16))
loud2 = norm(loop(a.loud2, 16))
e0, e1 = map(float, a.ending.split(","))
ending = norm(seg(e0, e1))


# ---------------- vocals: memphis / phonk processing ----------------
def vox(name, semis=-4, phone=True, drive=3.0, verb=.25):
    p = os.path.join(a.vox, name + ".wav")
    y, _ = librosa.load(p, sr=SR, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)
    y = librosa.effects.pitch_shift(y, sr=SR, n_steps=semis)
    if phone:
        y = bp(y.astype(np.float32), 1100, .9)
    y = clip(norm(y) * drive, drive) * .9
    if verb:  # short dark room
        n = int(.6 * SR); ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 9)
        ir = lp(ir.astype(np.float32), 3000); ir /= np.sqrt((ir ** 2).sum())
        wet = np.convolve(y, ir)[:len(y) + n]; wet = np.pad(wet, (0, len(y) + n - len(wet)))
        y = np.pad(y, (0, n)) * (1 - verb) + wet * verb * 1.5
    return norm(y).astype(np.float32)


def stutter(x, n=3, step=None):  # "a-a-ayy"
    w = int(round((step or S16) * SR))
    piece = x[:w] * np.linspace(1, .6, len(x[:w]))
    out = np.zeros(w * n + len(x), np.float32)
    for k in range(n):
        out[k * w:k * w + len(piece)] += piece
    out[n * w:] += x
    return out


V = {k: vox(k) for k in ("yeah", "ayy", "uh", "letsgo", "holdup", "drift", "slide", "what", "phonk")}
V["mk_deep"] = vox("mountainking", semis=-7, phone=False, drive=1.5, verb=.45)
V["intro_line"] = vox("kingofthehill", semis=-6, phone=True, drive=2, verb=.4)

# ---------------- timeline ----------------
N_BARS = 4 + 8 + 2 + 8 + 2
LEN = int((N_BARS * BAR + 6) * SR)
bus = {k: np.zeros((2, LEN), np.float32) for k in ("orc", "drums", "bass", "bell", "vox", "fx")}
kicks = []


def put(b, x, at, gain=1.0, pan=0.0):
    x = np.atleast_2d(x)
    if x.shape[0] == 1:
        x = np.vstack([x * (1 - pan) ** .5, x * (1 + pan) ** .5]) / 2 ** .5 * 1.41
    i = int(at * SR); j = min(i + x.shape[1], LEN)
    if i < LEN:
        bus[b][:, i:j] += x[:, :j - i] * gain


def bt(bar, s16=0):
    return bar * BAR + s16 * S16


def drums(b0, bars, busy=False):
    K, C, sn = kick(), clap(), snare()
    for b in range(b0, b0 + bars):
        for s in (0, 6, 10) + ((13,) if busy and b % 2 else ()):
            put("drums", K, bt(b, s)); kicks.append(bt(b, s))
        put("drums", C, bt(b, 8), .9); put("drums", sn, bt(b, 8), .5)
        for s in range(0, 16, 1 if busy else 2):
            put("drums", hat(), bt(b, s), .55 if s % 4 else .8, pan=.25)
        if b % 2:
            for k in range(6):
                put("drums", hat(.03), bt(b, 13) + k * S16 / 2, .5, pan=-.25)
        put("drums", hat(open_=True), bt(b, 14), .35, pan=.3)


def bass_line(b0, bars):
    # B pedal with octave jumps + F# turnaround (Mountain King hovers on Bm / F#)
    pat = [(0, 35, 5), (6, 35, 3), (10, 47, 2), (12, 42, 4)]
    for b in range(b0, b0 + bars):
        for s, m, l in pat:
            put("bass", bass808(m, l * S16 + .05, glide_from=47 if m == 35 and s == 0 and b % 2 else None), bt(b, s))


def bell_line(b0, bars, octave=0, gain=.35):
    pat = [(0, 71), (3, 71), (6, 74), (8, 71), (11, 73), (14, 66)]  # B D C# F# phonk ostinato
    for b in range(b0, b0 + bars):
        for s, m in pat:
            put("bell", cowbell(m + octave, .22, 3.5), bt(b, s), gain, pan=-.2)


def place_loop(x, b0, n_loops, gain=1.0, lowpass=None):
    for k in range(n_loops):
        y = x if lowpass is None else np.stack([lp(c, lowpass) for c in x])
        put("orc", y, bt(b0 + 4 * k), gain)


print("arranging...")
# INTRO 0-3: quiet orchestra half-time, lowpassed, deep vocal, rev, riser, 1 beat silence
place_loop(intro, 0, 1, 1.0)
bus["orc"][:, int(bt(3, 12) * SR):int(bt(4) * SR)] *= np.linspace(1, 0, int(bt(4) * SR) - int(bt(3, 12) * SR))
put("vox", V["mk_deep"], bt(0, 4), .9)
put("vox", V["intro_line"], bt(2), .8)
put("fx", rev(2.0), bt(1), .35, pan=.3)
put("fx", riser(BAR * 2 - BEAT), bt(2), .6)
put("fx", turbo_spool(BAR - BEAT), bt(3), .4)
put("vox", stutter(V["ayy"], 3), bt(3, 12) - 3 * S16, .9)
for b in range(4):
    put("bass", bass808(35, BAR * .95, dist=1.3), bt(b), .35)

# DROP 1 4-11
put("fx", boom(), bt(4), .9); put("drums", crash(), bt(4), .9); put("fx", tire_screech(1.4), bt(4), .35, pan=-.4)
place_loop(loud1, 4, 2); drums(4, 8); bass_line(4, 8); bell_line(4, 8)
for b, k in [(5, "yeah"), (7, "uh"), (9, "phonk"), (11, "what")]:
    put("vox", V[k], bt(b, 12), .85)
put("vox", stutter(V["letsgo"], 2, S16 * 2), bt(8), .8)
put("fx", bov(), bt(7, 12), .45, pan=.5); put("fx", flutter(), bt(9, 12), .45, pan=-.5)
put("fx", exhaust_pops(1.0), bt(11, 8), .45)

# BREAK 12-13: intro theme filtered + hold up + snare roll + riser, silence before drop
place_loop(intro[:, :int(2 * BAR * SR)], 12, 1, .9, lowpass=1200)
put("vox", V["holdup"], bt(12), .9)
for k in range(16):
    t = bt(13) + (k * S16 if k < 8 else 8 * S16 + (k - 8) * S16 / 2)
    if t < bt(13, 12):
        put("drums", snare(), t, .2 + .04 * k)
put("fx", riser(BAR - BEAT), bt(13), .6)
put("bass", bass808(35, BAR, dist=1.3), bt(12), .4)

# DROP 2 14-21: loud variation + busier
put("fx", backfire(), bt(14), .7); put("fx", boom(), bt(14), .9); put("drums", crash(), bt(14), .9)
put("fx", tire_screech(1.6), bt(14), .35, pan=.4); put("fx", tire_screech(1.2), bt(18), .3, pan=-.4)
place_loop(loud2, 14, 1); place_loop(loud1, 18, 1)
drums(14, 8, busy=True); bass_line(14, 8); bell_line(14, 8); bell_line(18, 4, octave=12, gain=.15)
put("vox", V["drift"], bt(14, 4), .9)
for b, k in [(15, "yeah"), (17, "slide"), (19, "ayy"), (21, "uh")]:
    put("vox", V[k], bt(b, 12) if k != "slide" else bt(b, 8), .85)
put("fx", bov(), bt(17, 12), .45, pan=.5)

# OUTRO 22-23: real final orchestra chords + boom, downlifter
put("orc", ending[:, :int(2 * BAR * SR + 3 * SR)], bt(22), 1.0)
put("fx", boom(), bt(22), .8); put("fx", downlifter(), bt(22), .5)
put("vox", V["mk_deep"], bt(23), .7)

# ---------------- mix ----------------
print("mixing...")
duck = np.ones(LEN, np.float32)
dk = 1 - .5 * np.exp(-np.arange(int(.16 * SR)) / SR * 24)
for t in kicks:
    i = int(t * SR); duck[i:i + len(dk)] = np.minimum(duck[i:i + len(dk)], dk[:LEN - i])
orc_hp = np.stack([hp(c, 90) for c in bus["orc"]])  # leave the low end to the 808
mix = (orc_hp * 1.0 * duck + bus["drums"] * .8 + np.stack([hp(c, 30) for c in bus["bass"]]) * .55 * duck
       + bus["bell"] * duck + bus["vox"] * .75 + bus["fx"] * .7)
vn = vinyl(LEN / SR + .01)[:LEN]; mix += vn[None, :] * .5
end = int((N_BARS * BAR + 4) * SR)
mix = mix[:, :end]
mix = norm(mix); mix = clip(mix * 1.1, 1.4); mix = norm(mix, .95)

with wave.open(a.out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
print("wrote", a.out, f"{mix.shape[1] / SR:.1f}s")
