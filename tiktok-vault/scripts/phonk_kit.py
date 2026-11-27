"""Phonk kit: synthesized drums, cowbell, 808, sfx and car sounds (numpy only).
All functions return float32 mono arrays at SR. Numbers in comments = SFX Library #.
"""
import numpy as np
from scipy.signal import lfilter

SR = 44100
rng = np.random.default_rng(1)


def t_(dur):
    return np.arange(int(round(dur * SR))) / SR


def env(dur, a=0.002, d=0.2, curve=4.0):
    t = t_(dur)
    e = np.minimum(t / max(a, 1e-5), 1) * np.exp(-np.maximum(t - a, 0) * curve / max(d, 1e-5))
    return e.astype(np.float32)


def clip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def lp(x, cutoff):  # one-pole lowpass; cutoff can be an array (time-varying)
    x = np.asarray(x, np.float32)
    if np.ndim(cutoff) == 0:
        a = 1 - np.exp(-2 * np.pi * cutoff / SR)
        return lfilter([a], [1, a - 1], x).astype(np.float32)
    c = np.asarray(cutoff, np.float32)
    y = np.empty_like(x); out = 0.0
    for i0 in range(0, len(x), 256):  # block-wise time-varying filter
        blk = x[i0:i0 + 256]
        a = 1 - np.exp(-2 * np.pi * float(c[min(i0, len(c) - 1)]) / SR)
        yb, zf = lfilter([a], [1, a - 1], blk, zi=[out * (1 - a)])
        y[i0:i0 + 256] = yb; out = yb[-1]
    return y


def hp(x, cutoff):
    return x - lp(x, cutoff)


def bp(x, f, q=4):
    return hp(lp(x, f * (1 + 1 / q)), f / (1 + 1 / q))


def noise(dur):
    return rng.standard_normal(int(round(dur * SR))).astype(np.float32)


def note_hz(n):  # midi -> hz
    return 440 * 2 ** ((n - 69) / 12)


def sine_sweep(f0, f1, dur, curve="exp"):
    t = t_(dur)
    f = f0 * (f1 / f0) ** (t / dur) if curve == "exp" else f0 + (f1 - f0) * t / dur
    return np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)


# ---------------- drums ----------------
def kick(dur=0.35):  # 63
    t = t_(dur)
    f = 45 + 160 * np.exp(-t * 40)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(dur, 0.001, 0.25, 5)
    x[:200] += noise(200 / SR)[:200] * np.linspace(.6, 0, 200)
    return clip(x, 2.0).astype(np.float32)


def snare(dur=0.25):  # 64 clipped snare
    tone = np.sin(2 * np.pi * 190 * t_(dur)) * env(dur, .001, .07, 5)
    n = hp(noise(dur), 1200) * env(dur, .001, .16, 5)
    return clip(tone * .7 + n * .9, 3).astype(np.float32) * .8


def clap(dur=0.3):  # 65 / 22
    x = np.zeros(int(round(dur * SR)), np.float32)
    for k, o in enumerate([0, .009, .018, .028]):
        i = int(o * SR); L = len(x) - i
        n = bp(noise(L / SR + 1e-3)[:L], 1400, 2) * env(L / SR + 1e-3, .0005, .02 if k < 3 else .18, 4)[:L]
        x[i:] += n[:L]
    return clip(x * 2.5, 2).astype(np.float32) * .7


def hat(dur=0.06, open_=False):  # 66 / 68
    d = .35 if open_ else dur
    x = hp(noise(d), 7000) * env(d, .0005, d * .6, 5)
    return (x * .35).astype(np.float32)


def crash(dur=2.0):  # 74
    x = hp(noise(dur), 4000) * env(dur, .002, 1.4, 4)
    return (x * .35).astype(np.float32)


# ---------------- melodic ----------------
def cowbell(midi, dur=0.28, dist=3.0):  # 53/54/56: two detuned squares like a TR-808 bell
    f = note_hz(midi)
    t = t_(dur)
    x = np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.48 * t))
    x = bp(x.astype(np.float32), f * 1.6, 1.2)
    x = x * env(dur, .001, dur * .55, 4)
    return (clip(x * 2, dist) * .55).astype(np.float32)


def bass808(midi, dur=0.5, glide_from=None, dist=2.5):  # 75/76
    t = t_(dur)
    f1 = note_hz(midi)
    f = np.full_like(t, f1) if glide_from is None else f1 + (note_hz(glide_from) - f1) * np.exp(-t * 18)
    f = f * (1 + .6 * np.exp(-t * 60))  # punchy attack
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(dur, .002, dur * .9, 2.2)
    return (clip(x, dist) * .8).astype(np.float32)


def pad(midis, dur):  # 6 dark pad
    t = t_(dur); x = np.zeros_like(t)
    for m in midis:
        for d in (-0.08, 0.08):
            f = note_hz(m) * 2 ** (d / 12)
            x += 2 * ((t * f) % 1) - 1
    x = lp(x.astype(np.float32) / len(midis), 900)
    e = np.minimum(t / 1.0, 1) * np.minimum((dur - t) / .5, 1)
    return (x * e * .25).astype(np.float32)


# ---------------- fx ----------------
def riser(dur=2.0):  # 25 noise riser
    t = t_(dur)
    x = noise(dur)
    x = hp(x, 300 + 6000 * (t / dur) ** 2) * (t / dur) ** 2
    s = sine_sweep(200, 1800, dur) * (t / dur) ** 2 * .3  # 31 pitch riser
    return ((x * .35 + s)).astype(np.float32)


def downlifter(dur=1.5):  # 32
    t = t_(dur)
    return (lp(noise(dur), 6000 * np.exp(-t * 3) + 100) * np.exp(-t * 2.5) * .4).astype(np.float32)


def whoosh(dur=0.5):  # 26
    t = t_(dur)
    e = np.sin(np.pi * t / dur) ** 2
    return (bp(noise(dur), 900, 1.5) * e * .6).astype(np.float32)


def boom(dur=1.6):  # 13 808 boom
    t = t_(dur)
    f = 38 + 90 * np.exp(-t * 12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(dur, .002, 1.2, 3)
    return (clip(x, 1.6)).astype(np.float32)


def impact(dur=1.5):  # 18
    n = lp(noise(dur), 2500) * env(dur, .001, .5, 6)
    return (n * .5 + boom(dur) * .7).astype(np.float32)


def vinyl(dur):  # 1 crackle + 95 hiss
    x = hp(noise(dur), 3000) * .01
    clicks = (rng.random(len(x)) < 8 / SR).astype(np.float32)
    clicks = np.convolve(clicks * rng.uniform(.2, .6, len(x)), np.exp(-np.arange(60) / 8), "same")
    return (x + hp(clicks.astype(np.float32), 1500) * .5).astype(np.float32)


def tape_stop(x, dur=0.6):  # 28 apply to the tail of a signal
    n = min(int(round(dur * SR)), len(x))
    seg = x[-n:]
    rate = np.linspace(1, 0, n) ** 1.5
    pos = np.cumsum(rate); pos = pos / pos[-1] * (n - 1) * .5
    y = np.interp(pos, np.arange(n), seg) * np.linspace(1, 0, n) ** .5
    return np.concatenate([x[:-n], y]).astype(np.float32)


# ---------------- car (synth approximations) ----------------
def tire_screech(dur=1.2):  # 37/38
    t = t_(dur)
    f = 1100 + 120 * np.sin(2 * np.pi * 3.3 * t) + 60 * rng.standard_normal(len(t)).cumsum() / np.sqrt(len(t))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + .5 * np.sin(2 * np.pi * np.cumsum(f * 2.01) / SR)
    n = bp(noise(dur), 1800, 2) * .6
    am = .7 + .3 * np.sin(2 * np.pi * 23 * t)
    e = np.minimum(t / .05, 1) * np.minimum((dur - t) / .3, 1)
    return ((tone * .35 + n) * am * e * .45).astype(np.float32)


def turbo_spool(dur=1.5):  # 39
    t = t_(dur)
    f = 900 + 5000 * (t / dur) ** 1.6
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) * .25
    n = bp(noise(dur), 2500, 1.5) * (t / dur) * .2
    return (w + n).astype(np.float32)


def bov(dur=0.45):  # 40 blow-off "pssh"
    t = t_(dur)
    x = hp(noise(dur), 1500) * env(dur, .005, .3, 4)
    x = lp(x, 9000 * np.exp(-t * 4) + 1500)
    return (x * .8).astype(np.float32)


def flutter(dur=0.5):  # 41 "stututu"
    t = t_(dur)
    gate = (np.sin(2 * np.pi * 28 * t) > 0).astype(np.float32)
    return (bp(noise(dur), 1800, 1.5) * gate * np.exp(-t * 5) * .7).astype(np.float32)


def exhaust_pops(dur=0.8, n=6):  # 42
    x = np.zeros(int(round(dur * SR)), np.float32)
    for _ in range(n):
        o = int(rng.uniform(0, dur - .08) * SR)
        p = lp(noise(.08), 1200) * env(.08, .0005, .03, 5) * rng.uniform(.5, 1.2)
        x[o:o + len(p)] += p
    return clip(x * 3, 2).astype(np.float32) * .6


def backfire(dur=0.6):  # 43
    return clip(lp(noise(dur), 900) * env(dur, .0005, .15, 6) * 4 + boom(dur) * .5, 2).astype(np.float32) * .7


def rev(dur=1.6, f0=35, f1=110):  # 12 engine rev (sawtooth firing pulses)
    t = t_(dur)
    k = t / dur
    f = f0 + (f1 - f0) * np.sin(np.pi * np.minimum(k * 1.3, 1) / 2) ** 2 * (1 - .4 * np.maximum(k - .75, 0) / .25)
    ph = np.cumsum(f) / SR
    x = (2 * (ph % 1) - 1) + .5 * (2 * ((ph * 2) % 1) - 1)
    x = lp(x.astype(np.float32), 400 + 1500 * k) + lp(noise(dur), 300) * .3
    e = np.minimum(t / .1, 1) * np.minimum((dur - t) / .2, 1)
    return (clip(x * 1.5, 2) * e * .5).astype(np.float32)
