# Ink Aura (Medusa Ink style)
**What it does:** dupes a cutout sticker, puts it behind, warps it with animated noise and posterizes it into glowing ink bands with white lightning. Boils every 2 frames like CapCut's Medusa Ink.
**Good for:** subject reveals, hype moments, flexing an item (bike edits). #effect #glow #overlay
**Ref:** user's bike edit, Nov 2026 (purple ink + lightning, then purple/orange mix)

## Needs
`pip install opencv-python-headless numpy pillow "rembg[cpu]"`. rembg is only for making cutouts.

## Steps
```bash
# 1. cut out the subject from a frame (transparent png)
ffmpeg -ss 2.0 -i clip.mov -frames:v 1 src.png
python3 -c "from rembg import remove; from PIL import Image; remove(Image.open('src.png')).save('cut.png')"
# 2. run the aura
python3 scripts/aura.py --bg clip.mp4 --sticker cut.png --out out.mp4 --colors "#7a00ff,#ff0055" --bolt-color "#ffffff"
```
`--sticker` can also be a video with alpha (ProRes 4444 .mov / webm) to track a moving cutout.

## Knobs
| flag | does | default |
|---|---|---|
| `--colors` | **any hex colors**, outer→inner, any amount. One color = auto shades | (preset) |
| `--bolt-color` | lightning hex color | white-ish |
| `--palette` | quick presets if no `--colors`: purple, mix, fire, toxic, ice | purple |
| `--spread` | how far ink reaches past the shape | 18 |
| `--chaos` | tendril / warp strength | 1.0 |
| `--boil` | hold frames (1 = smooth, 2 = capcut choppy) | 2 |
| `--bolts` | lightning amount (0 = off) | 1.0 |
| `--glow` | glow strength | 0.5 |
| `--cuts` | how much ink gets randomly cut away (0–0.9) | 0.4 |
| `--bleed` | soft fibrous ink-bleed edges (0 = hard) | 1.0 |
| `--start` / `--end` | when the aura is on (sec) | whole clip |
| `--hide-sticker` | draw aura only | off |

## Notes / user feedback
- v2: **NO outline.** Colors are random patches, not rings (rings make an outline at the edge). Edge is soft and bleeds. Random chunks get cut out everywhere, even over the subject. User liked this.
- Target look = ink bleed: organic, soft and patchy, never a clean rim.
- User wants colors **fully customizable**, never locked to one look. Always expose `--colors`.
- v1: tested on the bike cutout. Rejected looks: big blurry blob, and a uniform pink rim (looked like a sticker outline). Keep it tight to the shape and patchy.
- rembg cutouts can grab extra stuff (it grabbed part of the cart). Check the cutout before running.
