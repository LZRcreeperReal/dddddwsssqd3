#!/usr/bin/env python3
"""Beat-synced car edit builder (H7 style): review-clip intro -> logo fade/zoom -> drop with
beat cuts, zoom punches, shake, flashes, greyscale grade, aura hero shots. Edit the SHOTS list.

usage: python3 car_edit.py config.json
config keys: out, song, song_bpm, song_drop (sec in song), intro {src, start, dur, voice_gain},
             logo, shots [[src, start, beats, "aura"|""]], fps
"""
import json, subprocess, sys, wave
import numpy as np, cv2

cfg = json.load(open(sys.argv[1]))
W, H, FPS = 1080, 1920, cfg.get("fps", 30)
BEAT = 60 / cfg["song_bpm"]
INTRO = cfg["intro"]["dur"]
T0 = cfg["song_drop"] - INTRO              # song time at edit t=0
shots = cfg["shots"]
total_beats = sum(s[2] for s in shots)
DUR = INTRO + total_beats * BEAT + cfg.get("tail", 0.6)
NF = int(DUR * FPS)


def frames(src, start, dur, grey=True):
    vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if grey:
        vf += ",hue=s=0,eq=contrast=1.12:brightness=-0.01"
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-i", src, "-t", str(dur + .2), "-an",
                        "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    a = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W, 3)
    n = int(round(dur * FPS))
    if len(a) < n:
        a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])
    return a[:n]


# ---- timeline: list of (frames array, start_frame, is_cut_shot)
timeline = [(frames(cfg["intro"]["src"], cfg["intro"]["start"], INTRO), 0, False)]
t = INTRO
for src, start, beats, kind in shots:
    d = beats * BEAT
    f0, f1 = int(round(t * FPS)), int(round((t + d) * FPS))
    timeline.append((frames(src, start, (f1 - f0) / FPS, grey=(kind != "aura")), f0, True))
    t += d
tail_src = timeline[-1][0]

# ---- logo (black bg -> alpha from brightness), greyscale like the ref
logo = cv2.cvtColor(cv2.imread(cfg["logo"]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
la = np.clip((logo.max(2) - 0.06) / 0.25, 0, 1)
lg = np.repeat(logo.mean(2, keepdims=True), 3, 2) if cfg.get("logo_grey", True) else logo
LS = int(W * cfg.get("logo_scale", .82))
logo_rgb = cv2.resize(lg, (LS, LS), interpolation=cv2.INTER_AREA)
logo_a = cv2.resize(la, (LS, LS), interpolation=cv2.INTER_AREA)
lg_in, lg_out = cfg.get("logo_in", INTRO - 1.9), INTRO

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                        "-pix_fmt", "yuv420p", "" + cfg["out"] + ".video.mp4"], stdin=subprocess.PIPE)
rng = np.random.default_rng(3)
for fi in range(NF):
    tt = fi / FPS
    seg = None
    for arr, f0, cut in timeline:
        if f0 <= fi < f0 + len(arr):
            seg = (arr, f0, cut)
    if seg is None:  # tail: hold last frame
        img = tail_src[-1].astype(np.float32) / 255; lt = 9; cut = False
    else:
        arr, f0, cut = seg
        img = arr[fi - f0].astype(np.float32) / 255; lt = (fi - f0) / FPS
    if cut or tt >= INTRO:
        z = 1 + 0.16 * np.exp(-lt / 0.11)                     # zoom punch on every cut
        sx = sy = 0
        if lt < 0.18:                                         # shake on the cut
            k = (0.18 - lt) / 0.18
            sx, sy = rng.uniform(-1, 1) * 22 * k, rng.uniform(-1, 1) * 22 * k
        M = np.array([[z, 0, (1 - z) * W / 2 + sx], [0, z, (1 - z) * H / 2 + sy]], np.float32)
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        if lt < 0.05:  # tiny motion blur on the first frames of a cut
            img = cv2.blur(img, (1, 25))
    # flash on every bar downbeat after the drop (and big one on the drop)
    if tt >= INTRO:
        bt = (tt - INTRO) % (4 * BEAT)
        amt = (0.7 if tt - INTRO < .1 else 0.35) * np.exp(-bt / 0.06) if bt < .2 else 0
        img = img + (1 - img) * amt
    # logo: fade + zoom in, hold, fade out into the drop
    if lg_in <= tt < lg_out:
        p = (tt - lg_in) / (lg_out - lg_in)
        op = min(1, p / .25) * min(1, (1 - p) / .15)
        s = 0.8 + 0.2 * (1 - (1 - min(p / .35, 1)) ** 3)
        n = int(LS * s); n -= n % 2
        lr = cv2.resize(logo_rgb, (n, n)); la_ = cv2.resize(logo_a, (n, n))[..., None] * op
        y0, x0 = int(H * .42) - n // 2, W // 2 - n // 2
        img[y0:y0 + n, x0:x0 + n] = img[y0:y0 + n, x0:x0 + n] * (1 - la_) + lr * la_
    if tt > DUR - cfg.get("tail", 0.6):
        img *= max(0, (DUR - tt) / cfg.get("tail", 0.6))
    enc.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

# ---- audio: review voice in the intro + song (ducked intro, full at the drop)
i = cfg["intro"]
af = (f"[0:a]atrim={i['start']}:{i['start'] + INTRO},asetpts=PTS-STARTPTS,volume={i.get('voice_gain', 1.3)},"
      f"afade=t=out:st={INTRO - .25}:d=0.25[v];"
      f"[1:a]atrim={T0}:{T0 + DUR},asetpts=PTS-STARTPTS,"
      f"volume='if(lt(t,{INTRO}),{cfg.get('song_intro_gain', .35)},1)':eval=frame,"
      f"afade=t=out:st={DUR - .6}:d=0.6[s];[v][s]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", i["src"], "-i", cfg["song"], "-i", "" + cfg["out"] + ".video.mp4",
                "-filter_complex", af, "-map", "2:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-shortest", "-movflags", "+faststart", cfg["out"]], check=True)
print("wrote", cfg["out"], f"{DUR:.1f}s")
