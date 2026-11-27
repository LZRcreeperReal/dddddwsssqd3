# Slow Zoom In
**What it does:** smooth push-in toward center.
**Good for:** build-up, storytime, dramatic moments. #effect #motion

## Command
```bash
ffmpeg -i in.mp4 -vf "zoompan=z='min(1+0.0015*on,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30" -c:a copy out.mp4
```

## Knobs
| param | does | default |
|---|---|---|
| `0.0015` | zoom speed per frame | 0.0015 |
| `1.3` | max zoom | 1.3 |

## Notes
- Tested ✅. zoompan can look a bit steppy; if so, upscale 2x first then zoom.
