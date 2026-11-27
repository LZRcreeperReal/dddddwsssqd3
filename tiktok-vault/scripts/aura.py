#!/usr/bin/env python3
"""Ink Aura: glowing, boiling ink behind a cutout sticker (Medusa-Ink style).

usage:
  python3 aura.py --bg clip.mp4 --sticker cutout.png --out out.mp4 [options]

The sticker is a transparent PNG (or a video with alpha) laid over the bg.
A duplicate goes behind it, gets warped by animated noise and posterized into
colored ink bands with white lightning edges.
"""
import argparse, subprocess, json
import numpy as np, cv2

PALETTES = {  # outer -> inner bands (RGB), plus lightning color
    "purple": dict(bands=[(255, 40, 160), (70, 30, 255), (120, 60, 255), (190, 150, 255)], bolt=(255, 245, 255)),
    "fire":   dict(bands=[(255, 70, 0), (255, 140, 0), (255, 200, 40), (255, 240, 180)], bolt=(255, 255, 230)),
    "mix":    dict(bands=[(255, 80, 0), (110, 50, 255), (255, 150, 20), (160, 110, 255)], bolt=(255, 245, 255)),
    "toxic":  dict(bands=[(0, 120, 40), (60, 255, 60), (180, 255, 60), (230, 255, 200)], bolt=(240, 255, 240)),
    "ice":    dict(bands=[(0, 80, 255), (0, 170, 255), (120, 230, 255), (220, 250, 255)], bolt=(255, 255, 255)),
}


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
    ap.add_argument("--palette", default="purple", choices=PALETTES)
    ap.add_argument("--spread", type=float, default=18, help="how far ink reaches past the shape (px @1080w)")
    ap.add_argument("--chaos", type=float, default=1.0, help="tendril/warp strength")
    ap.add_argument("--boil", type=int, default=2, help="hold each aura frame N frames (2 = choppy capcut feel)")
    ap.add_argument("--bolts", type=float, default=1.0, help="lightning amount, 0 = off")
    ap.add_argument("--glow", type=float, default=0.8)
    ap.add_argument("--opacity", type=float, default=1.0)
    ap.add_argument("--start", type=float, default=0, help="aura on at sec")
    ap.add_argument("--end", type=float, default=1e9, help="aura off at sec")
    ap.add_argument("--hide-sticker", action="store_true", help="aura only, don't draw sticker on top")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    W, H, fps, dur = probe(a.bg)
    is_img = a.sticker.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))
    sw, sh = W // 2, H // 2  # aura sim at half res
    sc = sw / 1080 * 2  # px scale relative to 1080 wide

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-i", a.bg, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264",
                            "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                            "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)

    rng = np.random.default_rng(a.seed)
    n_warp_x, n_warp_y, n_ink = (Noise(sh, sw, rng) for _ in range(3))
    n_hole = Noise(sh, sw, rng, scales=(8, 16, 32))
    n_bolt = Noise(sh, sw, rng, scales=(3, 6, 12, 40))
    pal = PALETTES[a.palette]
    bands = np.array(pal["bands"], np.float32) / 255
    bolt_c = np.array(pal["bolt"], np.float32) / 255
    gx, gy = np.meshgrid(np.arange(sw, dtype=np.float32), np.arange(sh, dtype=np.float32))
    spread = a.spread * sc
    warp = 38 * sc * a.chaos

    bg_it = reader(a.bg, W, H, "rgb24", 3)
    st_it = reader(a.sticker, W, H, "rgba", 4, loop_image=is_img)
    aura_rgb = aura_a = None
    for i, (bg, st) in enumerate(zip(bg_it, st_it)):
        t = i / fps
        out = bg.astype(np.float32) / 255
        alpha = st[..., 3].astype(np.float32) / 255
        on = a.start <= t < a.end
        if on and (aura_rgb is None or i % max(1, a.boil) == 0):
            m = cv2.resize(alpha, (sw, sh), interpolation=cv2.INTER_AREA)
            # warp the duplicate so edges turn into tendrils
            dx, dy = (n_warp_x.get() - .5) * 2 * warp, (n_warp_y.get() - .5) * 2 * warp
            mw = cv2.remap(m, gx + dx, gy + dy, cv2.INTER_LINEAR, borderValue=0)
            mw = np.maximum(mw, m)
            # ink = warped duplicate, slightly grown, eaten by noise -> ragged patches w/ gaps
            k = int(spread) | 1
            grown = cv2.dilate(mw, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            field = cv2.GaussianBlur(grown, (0, 0), max(1, spread * .35))
            ink = n_ink.get()
            v = field * (0.3 + 1.2 * ink)
            th = [0.42, 0.52, 0.74, 0.95]
            holes = n_hole.get()  # punches gaps so it's patchy, not a solid blob
            cov = ((v > th[0]) & (holes > 0.42 - 0.25 * m)).astype(np.float32)
            idx = np.clip(np.digitize(v, th) - 1, 0, len(bands) - 1)
            col = bands[idx]
            # lightning: jagged iso-lines of high-freq noise, only inside the ink
            line = np.zeros_like(v)
            if a.bolts > 0:
                bn = n_bolt.get()
                line = np.clip(1 - np.abs(bn - 0.5) / (0.012 * a.bolts), 0, 1)
                line *= (v > th[0] * .9) * (holes > 0.3)
            col = col * (1 - line[..., None]) + bolt_c * line[..., None]
            cov = np.maximum(cov, line)
            # glow
            g = cv2.GaussianBlur(col * cov[..., None], (0, 0), 9 * sc) * a.glow * 1.6
            aura_rgb = cv2.resize(col, (W, H), interpolation=cv2.INTER_NEAREST)
            aura_a = cv2.resize(cov, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * a.opacity
            aura_g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR) * a.opacity
        if on and aura_rgb is not None:
            out = out + aura_g * (1 - out)                     # screen-ish glow
            out = out * (1 - aura_a) + aura_rgb * aura_a
        if not a.hide_sticker:
            sa = alpha[..., None]
            out = out * (1 - sa) + st[..., :3].astype(np.float32) / 255 * sa
        enc.stdin.write((np.clip(out, 0, 1) * 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()


if __name__ == "__main__":
    main()
