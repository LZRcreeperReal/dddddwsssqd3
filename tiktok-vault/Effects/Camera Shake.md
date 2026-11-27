# Camera Shake
**What it does:** jitters the frame like a handheld impact.
**Good for:** hits, jumpscares, beat drops. #effect #motion

## Command
```bash
ffmpeg -i in.mp4 -vf "crop=iw/1.1:ih/1.1:(iw-ow)/2+sin(t*40)*20:(ih-oh)/2+cos(t*35)*20,scale=1080:1920" -c:a copy out.mp4
```
Only during 1s–1.5s: wrap the offsets in `if(between(t,1,1.5), ..., 0)`.

## Knobs
| param | does | default |
|---|---|---|
| `1.1` | zoom-in so edges don't show | 1.1 |
| `40` / `35` | shake speed | 40/35 |
| `20` | shake strength (px) | 20 |

## Notes
- Tested ✅
