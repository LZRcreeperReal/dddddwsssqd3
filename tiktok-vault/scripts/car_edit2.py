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
W, H = cfg.get("size", [1080, 1920])
FPS = 30
BEAT = 60 / cfg["bpm"]
GRADE = cfg.get("grade", "hue=s=0,curves=preset=medium_contrast")
SHARP = "unsharp=5:5:0.45:3:3:0"
T_INK, T_PRE = cfg.get("t_ink", 0.42), cfg.get("t_preview", 0.45)
CACHE = cfg.get("cache", os.path.dirname(os.path.abspath(cfg["out"])) + "/cache")
os.makedirs(CACHE, exist_ok=True)
rng = np.random.default_rng(5)


def subject_cy(src, t):
    """vertical centre (0-1) of the car in a vertical clip, for landscape crops"""
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", src, "-frames:v", "1",
                        "-vf", "scale=540:960", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    img = np.frombuffer(p.stdout, np.uint8).reshape(960, 540, 3)
    a = cutout(img, f"cy_{os.path.basename(src)}_{t:.2f}", size=(540, 960))
    ys = np.where(a.max(1) > .5)[0]
    return float((ys.min() + ys.max()) / 2 / 960) if len(ys) else 0.5


def grab(src, start, dur, grade=True, cy=None):
    if W > H:  # landscape crop out of a vertical clip, band centred on the car
        cy = subject_cy(src, start + dur / 2) if cy is None else cy
        geo = f"scale={W}:-2:flags=lanczos,crop={W}:{H}:0:'min(max(ih*{cy:.3f}-{H}/2,0),ih-{H})'"
    else:
        geo = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
    vf = f"fps={FPS},{geo},{SHARP}" + ("," + GRADE if grade else "")
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(start, 0):.3f}", "-i", src, "-t", f"{dur + .3:.3f}",
                        "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    a = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W, 3)
    n = int(round(dur * FPS))
    if len(a) < n:
        a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])
    return a[:n]


_sess = None
def cutout(img_u8, key, size=None):
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
    return cv2.resize(a, size or (W, H))


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
    cy = cfg.get("cy", {}).get(str(k))
    jump = "jump" in flags.split()
    extra = cfg.get("jump_skip", 0.8) * (dur / BEAT + 2) if jump else 0.0
    fr = grab(src, start - pre, pre + (round(t1 * FPS) - round(t * FPS)) / FPS + extra, grade="aura" not in flags, cy=cy)
    a = None
    if "ink" in flags:
        a = cutout(fr[int(pre * FPS * .5)], f"{os.path.basename(src)}_{start - pre / 2:.2f}")
    if "preview" in flags:
        a = cutout(fr[0], f"{os.path.basename(src)}_{start:.2f}")
    shots.append(dict(fr=fr, t0=t, t1=t1, pre=pre, flags=flags, a=a, jump=jump))
    t = t1
DUR = t
NF = int(round(DUR * FPS))

# logo
logo = cv2.cvtColor(cv2.imread(cfg["logo"]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
la = np.clip((logo.max(2) - 0.06) / 0.25, 0, 1)
lg = np.repeat(logo.mean(2, keepdims=True), 3, 2) if cfg.get("logo_grey", True) else logo
LS = int(min(W, H) * cfg.get("logo_scale", .8))
logo_rgb, logo_a = cv2.resize(lg, (LS, LS), interpolation=cv2.INTER_AREA), cv2.resize(la, (LS, LS), interpolation=cv2.INTER_AREA)
L_IN, L_OUT = cfg.get("logo_in", 0.5), cfg.get("logo_out", 2.1)

noise_lo = [smooth_noise(90, s) for s in range(3)]
noise_hi = smooth_noise(6, 11)


BEAT0 = cfg.get("beat0", intro % BEAT)  # song beat grid phase


def frame_of(s, tt):
    st = tt - s["t0"] + s["pre"]
    if s.get("jump"):  # jump cut: on every song beat the clip skips ahead jump_skip seconds
        nb = int(np.floor((tt - BEAT0) / BEAT + 1e-6)) - int(np.floor((s["t0"] - BEAT0) / BEAT + 1e-6))
        st += cfg.get("jump_skip", 0.8) * max(nb, 0)
    i = int(round(st * FPS))
    return s["fr"][min(max(i, 0), len(s["fr"]) - 1)].astype(np.float32) / 255


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", str(cfg.get("crf", 10)), "-preset", "slower", "-tune", "film", "-profile:v", "high",
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
        A = nxt["a"] * min(1, p / cfg.get("preview_pop", 0.08))   # pops in almost instantly (like the ref)
        tone = np.clip((p - .12) / .7, 0, 1)
        obj = 1 - (1 - n0) * tone  # pure white cut-out -> fades back to the real tone before the cut
        glow = cv2.GaussianBlur(nxt["a"], (0, 0), 14)[..., None] * (1 - tone) * .35 * min(1, p / .08)
        img = img + (1 - img) * glow
        img = img * (1 - A[..., None]) + obj * A[..., None]

    # ---- incoming hit: optional zoom punch / shake / beat pulse (off = clean full frame like the refs)
    if tt >= intro - 1e-6 and (cfg.get("zoom", False) or cfg.get("shake", False)):
        z = 1.0
        if cfg.get("zoom", False):
            z = 1 + 0.12 * np.exp(-lt / 0.09) + 0.035 * np.exp(-((tt - intro) % BEAT) / 0.07)
        sx = sy = rot = 0
        if cfg.get("shake", False) and lt < 0.16:
            q = (0.16 - lt) / 0.16 * (1.8 if abs(s["t0"] - intro) < 1e-3 else 1)
            sx, sy, rot = rng.uniform(-1, 1) * 26 * q, rng.uniform(-1, 1) * 26 * q, rng.uniform(-1, 1) * 1.6 * q
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, z); M[0, 2] += sx; M[1, 2] += sy
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    # ---- flashes: on the drop, and (flash_every=2) on the in-between beats where a cut used to be
    if tt >= intro - 1.5 / FPS:
        kb = int(round((tt - intro) / BEAT)); dt = tt - (intro + kb * BEAT)
        fe = cfg.get("flash_every", 0)
        hit = (kb == 0 and cfg.get("flash_drop", True)) or (fe and kb > 0 and kb % fe == fe // 2 and kb % fe != 0)
        if hit and -1.0 / FPS <= dt < 0.2:
            peak = 0.85 if kb == 0 else cfg.get("flash_amt", 0.7)
            amt = peak * (0.5 if dt < 0 else np.exp(-dt / cfg.get("flash_decay", 0.055)))
            img = img + (1 - img) * amt
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

revs = [(sh, c) for sh, c in zip(shots, cfg["shots"]) if "rev" in c[3].split()]
inputs = ["-i", cfg["out"] + ".v.mp4", "-i", cfg["song"]]
rd = cfg.get("rev_dur", 2.3)
duck = "+".join(f"between(t,{sh['t0']:.3f},{sh['t0'] + rd - .3:.3f})" for sh, _ in revs) or "0"
fc = (f"[1:a]atrim=0:{DUR},asetpts=PTS-STARTPTS,"
      f"volume='{cfg.get('song_gain', 1.0)}*if({duck},{cfg.get('rev_duck', .55)},1)':eval=frame[s0];")
mixes = ["[s0]"]
for j, (sh, c) in enumerate(revs):  # car audio keeps playing under the next cuts, loud
    rs = c[1] + cfg.get("rev_offset", 0.0)
    inputs += ["-ss", f"{rs:.3f}", "-t", f"{rd:.3f}", "-i", c[0]]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{rs:.3f}", "-t", f"{rd:.3f}", "-i", c[0], "-vn", "-ac", "1",
                          "-ar", "22050", "-af", "highpass=f=30", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    rms_db = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    g = 10 ** ((cfg.get("rev_target_db", -9.0) - rms_db) / 20)  # boost the rev to a fixed loud level
    print(f"rev {os.path.basename(c[0])}: rms {rms_db:.1f} dB -> gain x{g:.1f}")
    fc += (f"[{2 + j}:a]aresample=48000,highpass=f=30,volume={g:.3f},alimiter=limit=0.97,"
           f"afade=t=in:d=0.02,afade=t=out:st={rd - .45}:d=0.45,adelay={int(sh['t0'] * 1000)}|{int(sh['t0'] * 1000)}[r{j}];")
    mixes.append(f"[r{j}]")
fc += (f"{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0:duration=first,"
       f"alimiter=limit=0.95,afade=t=out:st={DUR - .3}:d=0.3[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc,
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest",
                "-movflags", "+faststart", cfg["out"]], check=True)
os.remove(cfg["out"] + ".v.mp4")
print("wrote", cfg["out"], f"{DUR:.2f}s")
