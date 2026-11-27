# RGB Split
**What it does:** shifts red/blue channels apart (chromatic glitch).
**Good for:** glitch edits, edgy vibes. #effect #glitch

## Command
```bash
ffmpeg -i in.mp4 -vf "rgbashift=rh=-10:bh=10" -c:a copy out.mp4
# only 1s–1.3s
ffmpeg -i in.mp4 -vf "rgbashift=rh=-10:bh=10:enable='between(t,1,1.3)'" -c:a copy out.mp4
```

## Knobs
| param | does | default |
|---|---|---|
| `rh` / `bh` | red / blue horizontal shift (px) | -10 / 10 |
| `rv` / `bv` | vertical shift | 0 |

## Notes
- Built-in `rgbashift` is cleaner than split+blend, use this.
