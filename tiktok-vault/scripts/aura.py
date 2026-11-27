#!/usr/bin/env python3
"""Ink Aura: ink bleeding out from behind a cutout sticker (Medusa-Ink style).

usage:
  python3 aura.py --bg clip.mp4 --sticker cutout.png --out out.mp4 [options]

The sticker is a transparent PNG (or a video with alpha) laid over the bg.
A duplicate goes behind it and constantly leaks ink that drifts/curls outward
(simple advection sim), rendered in one color with tonal depth + glow.
"""
import argparse, subprocess, json
import numpy as np, cv2

def hex2rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build_bands(spec):
    cols = [hex2rgb(c) for c in spec.replace(" ", "").split(",") if c]
    if len(cols) == 1:  # one color -> deep edge, base, lighter, near-white core
        c = np.array(cols[0], np.float32)
        cols = [tuple(c * .5), tuple(c * .8), tuple(c), tuple(c + (255 - c) * .45)]
    return cols


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out); s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d), float(j["format"]["duration"])


def reader(path, w, h, fmt, ch, loop_image=False, extra=()):
    cmd = ["ffmpeg", "-v", "quiet"] + (["-loop", "1"] if loop_image else []) + ["-i", path, *extra,
           "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", fmt, "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * ch
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, ch)
    p.kill()


class Noise:
    """Smooth animated fractal noise (value noise, lerped between keyframes)."""
    def __init__(self, h, w, rng, scales=(6, 12, 24, 48), key_every=4):
        self.h, self.w, self.rng, self.k = h, w, rng, key_every
        self.oct = [(s, rng.random((2, max(2, h // s), max(2, w // s))).astype(np.float32)) for s in scales]
        self.frame = 0

    def get(self):
        t = (self.frame % self.k) / self.k
        if self.frame % self.k == 0 and self.frame:
            self.oct = [(s, np.stack([g[1], self.rng.random(g[1].shape).astype(np.float32)])) for s, g in self.oct]
        self.frame += 1
        acc, amp, tot = 0, 1.0, 0
        for s, g in self.oct[::-1]:  # coarse first, bigger weight
            layer = g[0] * (1 - t) + g[1] * t
            acc = acc + cv2.resize(layer, (self.w, self.h), interpolation=cv2.INTER_CUBIC) * amp
            tot += amp; amp *= 0.55
        return acc / tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--sticker", required=True, help="transparent png or alpha video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--color", default="#ff1a1a", help="ink color hex. comma list = custom tones dark->bright")
    ap.add_argument("--spread", type=float, default=1.0, help="how far the ink bleeds out")
    ap.add_argument("--flow", type=float, default=1.0, help="how much the ink swirls/curls")
    ap.add_argument("--bleed", type=float, default=1.0, help="fuzzy fibrous edges (0 = clean)")
    ap.add_argument("--cuts", type=float, default=0.15, help="fraction randomly cut away (0-0.9)")
    ap.add_argument("--glow", type=float, default=0.6)
    ap.add_argument("--opacity", type=float, default=1.0)
    ap.add_argument("--boil", type=int, default=1, help="hold each aura frame N frames (2 = choppy)")
    ap.add_argument("--bolts", type=float, default=0.0, help="lightning amount (off by default)")
    ap.add_argument("--bolt-color", default="#ffffff")
    ap.add_argument("--start", type=float, default=0, help="aura on at sec")
    ap.add_argument("--end", type=float, default=1e9, help="aura off at sec")
    ap.add_argument("--hide-sticker", action="store_true", help="aura only, don't draw sticker on top")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    W, H, fps, dur = probe(a.bg)
    is_img = a.sticker.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))
    sw, sh = W // 2, H // 2  # sim at half res
    sc = sw / 540  # px scale relative to 1080 wide

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-i", a.bg, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264",
                            "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                            "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)

    rng = np.random.default_rng(a.seed)
    n_vx, n_vy = (Noise(sh, sw, rng, scales=(20, 40, 80), key_every=10) for _ in range(2))
    n_fine = Noise(sh, sw, rng, scales=(2, 4, 8, 16), key_every=3)
    n_hole = Noise(sh, sw, rng, scales=(12, 24, 48), key_every=8)
    n_bolt = Noise(sh, sw, rng, scales=(3, 6, 12, 40))
    if "," in a.color:
        tones = np.array([hex2rgb(c) for c in a.color.split(",")], np.float32) / 255
    else:  # one color -> base, base, slightly lit (no dark/muddy or white tones)
        c = np.array(hex2rgb(a.color), np.float32)
        tones = np.array([c * .68, c, c + (255 - c) * .3], np.float32) / 255
    bolt_c = np.array(hex2rgb(a.bolt_color), np.float32) / 255
    gx, gy = np.meshgrid(np.arange(sw, dtype=np.float32), np.arange(sh, dtype=np.float32))
    decay = 0.90 + 0.06 * min(a.spread, 1.6)
    swirl = 2.6 * sc * a.flow
    push = 1.4 * sc * a.spread

    D = np.zeros((sh, sw), np.float32)  # ink density
    def step(m, push_x, push_y):
        nonlocal D
        vx = (n_vx.get() - .5) * 2 * swirl + push_x
        vy = (n_vy.get() - .5) * 2 * swirl + push_y - 0.4 * sc  # slight upward drift
        D = cv2.remap(D, gx - vx, gy - vy, cv2.INTER_LINEAR, borderValue=0) * decay
        D = cv2.GaussianBlur(D, (0, 0), 0.8)
        D = np.maximum(D, m)

    bg_it = reader(a.bg, W, H, "rgb24", 3)
    st_it = reader(a.sticker, W, H, "rgba", 4, loop_image=is_img)
    aura_rgb = None
    warm = False
    for i, (bg, st) in enumerate(zip(bg_it, st_it)):
        t = i / fps
        out = bg.astype(np.float32) / 255
        alpha = st[..., 3].astype(np.float32) / 255
        on = a.start <= t < a.end
        if on:
            m = cv2.resize(alpha, (sw, sh), interpolation=cv2.INTER_AREA)
            # outward push = away from the shape
            mb = cv2.GaussianBlur(m, (0, 0), 18 * sc)
            px, py = -cv2.Sobel(mb, cv2.CV_32F, 1, 0, ksize=5), -cv2.Sobel(mb, cv2.CV_32F, 0, 1, ksize=5)
            mag = np.sqrt(px ** 2 + py ** 2) + 1e-4
            px, py = px / mag * push * np.clip(mag * 40, 0, 1), py / mag * push * np.clip(mag * 40, 0, 1)
            for _ in range(1 if warm else 30):
                step(m, px, py)
            warm = True
        if on and (aura_rgb is None or i % max(1, a.boil) == 0):
            fine = n_fine.get()
            v = D + (fine - .5) * 0.5 * a.bleed * np.clip(D * 4, 0, 1)  # fibrous edge
            cov = np.clip((v - 0.12) / (0.04 + 0.12 * a.bleed), 0, 1)
            if a.cuts > 0 and (cov > 0).any():
                holes = n_hole.get()
                ht = np.quantile(holes[cov > 0], min(a.cuts, 0.9))
                cov *= np.clip((holes - ht) / 0.04, 0, 1)
            # tone by density: thin ink = deep, dense ink = bright (posterized for the capcut look)
            lv = np.clip((v - 0.12) / 0.95 + (fine - .5) * 0.9, 0, 0.999)  # patchy, no ring
            idx = (lv * len(tones)).astype(int)
            col = tones[idx]
            if a.bolts > 0:
                line = np.clip(1 - np.abs(n_bolt.get() - 0.5) / (0.012 * a.bolts), 0, 1) * np.clip(cov * 2, 0, 1)
                col = col * (1 - line[..., None]) + bolt_c * line[..., None]
                cov = np.maximum(cov, line)
            cov = cov * np.clip(0.55 + D, 0, 1)  # thin ink is more see-through
            g = cv2.GaussianBlur(col * cov[..., None], (0, 0), 7 * sc) * a.glow * 1.4
            aura_rgb = cv2.resize(col, (W, H), interpolation=cv2.INTER_LINEAR)
            aura_a = cv2.resize(cov, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * a.opacity
            aura_g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR) * a.opacity
        if on and aura_rgb is not None:
            out = out + aura_g * (1 - out)  # glow (screen)
            out = out * (1 - aura_a) + aura_rgb * aura_a
        if not a.hide_sticker:
            sa = alpha[..., None]
            out = out * (1 - sa) + st[..., :3].astype(np.float32) / 255 * sa
        enc.stdin.write((np.clip(out, 0, 1) * 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()


if __name__ == "__main__":
    main()
