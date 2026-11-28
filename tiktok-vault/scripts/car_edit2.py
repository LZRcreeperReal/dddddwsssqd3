#!/usr/bin/env python3
"""Car edit builder v2 (H7 style, aggressive + clean).
Transitions copied from the user's edit:
  "ink"     = aura transition: next shot's car revealed through a growing ragged ink mask with a white torn
              fringe over the current shot, finished by a radial zoom-blur whip onto the beat
  "preview" = next shot's car cut out, fades in over the current shot as a glowing white silhouette that
              settles to normal tone, then hard cut (user's last 2 transitions)
Shots: [src, start, beats, flags] flags: "aura" (src is a pre-rendered aura clip, no regrade),
       "ink" / "preview" = transition INTO this shot.
usage: python3 car_edit2.py cfg.json
"""
import json, os, subprocess, sys
import numpy as np, cv2

cfg = json.load(open(sys.argv[1]))
W, H, FPS = 1080, 1920, 30
BEAT = 60 / cfg["bpm"]
GRADE = cfg.get("grade", "hue=s=0,curves=preset=medium_contrast")
CLEAN = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,unsharp=5:5:0.45:3:3:0"
T_INK, T_PRE = cfg.get("t_ink", 0.42), cfg.get("t_preview", 0.45)
CACHE = cfg.get("cache", os.path.dirname(os.path.abspath(cfg["out"])) + "/cache")
os.makedirs(CACHE, exist_ok=True)
rng = np.random.default_rng(5)


def grab(src, start, dur, grade=True):
    vf = f"fps={FPS}," + CLEAN + ("," + GRADE if grade else "")
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(start, 0):.3f}", "-i", src, "-t", f"{dur + .3:.3f}",
                        "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    a = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W, 3)
    n = int(round(dur * FPS))
    if len(a) < n:
        a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])
    return a[:n]


_sess = None
def cutout(img_u8, key):
    """alpha (float 0-1) of the main subject, cached"""
    global _sess
    fn = f"{CACHE}/{key}.png"
    if not os.path.exists(fn):
        from rembg import new_session, remove
        from PIL import Image
        _sess = _sess or new_session(cfg.get("cut_model", "isnet-general-use"))
        from cutout_seq import biggest
        im = np.array(remove(Image.fromarray(img_u8), session=_sess)); im[..., 3] = biggest(im[..., 3])
        Image.fromarray(im).save(fn)
    a = cv2.imread(fn, cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
    return cv2.resize(a, (W, H))


def smooth_noise(scale, seed):
    r = np.random.default_rng(seed)
    g = r.random((H // scale + 2, W // scale + 2)).astype(np.float32)
    return cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)


def radial_blur(img, amount):
    if amount <= 0.01:
        return img
    acc = img.copy(); n = 8
    for k in range(1, n):
        z = 1 + amount * 0.12 * k / n
        M = np.array([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]], np.float32)
        acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


# ---------------- build shots ----------------
intro = cfg["intro_dur"]
shots = []  # dict(frames, t0, t1, flags, alpha_for_transition)
t = 0.0
for k, (src, start, beats, flags) in enumerate(cfg["shots"]):
    dur = beats * BEAT if beats > 0 else -beats  # negative beats = seconds
    t1 = t + dur
    pre = T_INK if "ink" in flags else 0.0
    fr = grab(src, start - pre, pre + (round(t1 * FPS) - round(t * FPS)) / FPS, grade="aura" not in flags)
    a = None
    if "ink" in flags:
        a = cutout(fr[int(pre * FPS * .5)], f"{os.path.basename(src)}_{start - pre / 2:.2f}")
    if "preview" in flags:
        a = cutout(fr[0], f"{os.path.basename(src)}_{start:.2f}")
    shots.append(dict(fr=fr, t0=t, t1=t1, pre=pre, flags=flags, a=a))
    t = t1
DUR = t
NF = int(round(DUR * FPS))

# logo
logo = cv2.cvtColor(cv2.imread(cfg["logo"]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
la = np.clip((logo.max(2) - 0.06) / 0.25, 0, 1)
lg = np.repeat(logo.mean(2, keepdims=True), 3, 2) if cfg.get("logo_grey", True) else logo
LS = int(W * .8)
logo_rgb, logo_a = cv2.resize(lg, (LS, LS), interpolation=cv2.INTER_AREA), cv2.resize(la, (LS, LS), interpolation=cv2.INTER_AREA)
L_IN, L_OUT = cfg.get("logo_in", 0.5), cfg.get("logo_out", 2.1)

noise_lo = [smooth_noise(90, s) for s in range(3)]
noise_hi = smooth_noise(6, 11)


def frame_of(s, tt):
    i = int(round((tt - s["t0"] + s["pre"]) * FPS))
    return s["fr"][min(max(i, 0), len(s["fr"]) - 1)].astype(np.float32) / 255


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "13", "-preset", "slow", "-tune", "film",
                        "-pix_fmt", "yuv420p", cfg["out"] + ".v.mp4"], stdin=subprocess.PIPE)
for fi in range(NF):
    tt = fi / FPS
    k = max(j for j, s in enumerate(shots) if s["t0"] <= tt + 1e-6)
    s = shots[k]
    img = frame_of(s, tt)
    lt = tt - s["t0"]
    nxt = shots[k + 1] if k + 1 < len(shots) else None

    # ---- outgoing transitions (drawn over the tail of the current shot)
    if nxt is not None and "ink" in nxt["flags"] and tt >= nxt["t0"] - T_INK:
        p = (tt - (nxt["t0"] - T_INK)) / T_INK
        nimg = frame_of(nxt, tt)
        A = cv2.GaussianBlur(nxt["a"], (0, 0), 3)
        dist = cv2.distanceTransform((A < .5).astype(np.uint8), cv2.DIST_L2, 5)  # 0 inside the car
        nz = noise_lo[fi % 3] * 0.6 + noise_lo[(fi + 1) % 3] * 0.4
        d = dist + (nz - .5) * 260 + (noise_hi - .5) * 60
        R = -60 + (p ** 1.6) * 1500
        mask = np.clip((R - d) / 6, 0, 1)
        fringe = np.clip(1 - np.abs(d - R + 14) / 14, 0, 1) * (noise_hi > .42)  # white torn edge
        img = img * (1 - mask[..., None]) + nimg * mask[..., None]
        img = img + (1 - img) * fringe[..., None] * 0.95
        if p > .72:  # radial whip blur onto the beat
            img = radial_blur(img, (p - .72) / .28 * 1.6)
    if nxt is not None and "preview" in nxt["flags"] and tt >= nxt["t0"] - T_PRE:
        p = (tt - (nxt["t0"] - T_PRE)) / T_PRE
        n0 = nxt["fr"][0].astype(np.float32) / 255
        A = nxt["a"] * min(1, p / .35)
        tone = np.clip((p - .3) / .5, 0, 1)
        obj = 1 - (1 - n0) * tone  # white silhouette -> real tone
        glow = cv2.GaussianBlur(nxt["a"], (0, 0), 18)[..., None] * (1 - tone) * .6 * min(1, p / .35)
        img = img + (1 - img) * glow
        img = img * (1 - A[..., None]) + obj * A[..., None]

    # ---- incoming hit: zoom punch + shake on every cut after the intro, beat pulses
    if tt >= intro - 1e-6:
        z = 1 + 0.12 * np.exp(-lt / 0.09)
        bl = ((tt - intro) % BEAT)
        z += 0.035 * np.exp(-bl / 0.07)  # pulse on every beat
        sx = sy = rot = 0
        if lt < 0.16:
            q = (0.16 - lt) / 0.16 * (1.8 if abs(s["t0"] - intro) < 1e-3 else 1)
            sx, sy, rot = rng.uniform(-1, 1) * 26 * q, rng.uniform(-1, 1) * 26 * q, rng.uniform(-1, 1) * 1.6 * q
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, z); M[0, 2] += sx; M[1, 2] += sy
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        if abs(tt - intro) < .1:  # flash on the drop
            img = img + (1 - img) * 0.8 * (1 - abs(tt - intro) / .1)
    # ---- logo fade + zoom (intro)
    if L_IN <= tt < L_OUT:
        p = (tt - L_IN) / (L_OUT - L_IN)
        op = min(1, p / .25) * min(1, (1 - p) / .2)
        sc = 0.82 + 0.18 * (1 - (1 - min(p / .4, 1)) ** 3)
        n = int(LS * sc) // 2 * 2
        lr, la_ = cv2.resize(logo_rgb, (n, n)), cv2.resize(logo_a, (n, n))[..., None] * op
        y0, x0 = int(H * .45) - n // 2, W // 2 - n // 2
        img[y0:y0 + n, x0:x0 + n] = img[y0:y0 + n, x0:x0 + n] * (1 - la_) + lr * la_
    # ---- fade to black at the end (like the ref)
    fo = cfg.get("fade_out", .45)
    if tt > DUR - fo:
        img = img * max(0, (DUR - tt) / fo)
    enc.stdin.write((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cfg["out"] + ".v.mp4", "-i", cfg["song"],
                "-filter_complex", f"[1:a]atrim=0:{DUR},asetpts=PTS-STARTPTS,afade=t=out:st={DUR - .3}:d=0.3[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest",
                "-movflags", "+faststart", cfg["out"]], check=True)
os.remove(cfg["out"] + ".v.mp4")
print("wrote", cfg["out"], f"{DUR:.2f}s")
