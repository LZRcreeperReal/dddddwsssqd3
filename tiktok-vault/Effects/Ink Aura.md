# Ink Aura (Medusa Ink style)
**What it does:** a copy of a cutout sticker sits behind it and keeps leaking ink that drifts and curls outward, like ink bleeding in water. **One color** with depth from tone (thin ink is deep, dense ink is a bit brighter), plus a soft glow.
**Good for:** subject reveals, hype moments, flexing an item (bike edits). #effect #glow #overlay

## Needs
`pip install opencv-python-headless numpy pillow "rembg[cpu]"`. rembg is only for making cutouts.

## Steps
```bash
# 1. cut out the subject (transparent png)
ffmpeg -ss 2.0 -i clip.mov -frames:v 1 src.png
python3 -c "from rembg import remove; from PIL import Image; remove(Image.open('src.png')).save('cut.png')"
# 2. aura
python3 scripts/aura.py --bg clip.mp4 --sticker cut.png --out out.mp4 --color "#ff1a1a"
```
`--sticker` can also be a video with alpha (ProRes 4444 .mov / webm) for a moving cutout.

## Knobs
| flag | does | default |
|---|---|---|
| `--color` | ink color hex. **One color** (auto tones). Comma list = custom tones dark→bright | #ff1a1a |
| `--spread` | how far the ink bleeds out | 1.0 |
| `--flow` | how much it swirls/curls | 1.0 |
| `--bleed` | fuzzy fibrous edges (0 = clean) | 1.0 |
| `--cuts` | fraction randomly cut away | 0.15 |
| `--glow` | glow strength | 0.6 |
| `--boil` | hold frames (2 = choppy) | 1 |
| `--bolts` | lightning, **off by default** (user doesn't want it) | 0 |
| `--start` / `--end` | when it's on (sec) | whole clip |
| `--hide-sticker` | aura only | off |

## How it works
Ink density field: each frame it's advected by a smooth noise flow plus an outward push (away from the shape) and a slight upward drift, decays, blurs, and gets re-injected from the sticker's alpha. Rendered with fibrous noise edges and posterized tones.

## History / user feedback
- v1: noise-warped blob with posterized bands + lightning. Too blobby, uniform pink rim looked like a sticker outline.
- v2: random color patches + random cuts. User: "doesn't look right."
- User's ref was 2 Medusa Ink overlays stacked, which is why it had 2 colors. **Default is ONE color.**
- v3 (current): real ink-bleed sim, red, no lightning. Avoid: dark/muddy edge tones, a bright ring hugging the subject, outlines.
