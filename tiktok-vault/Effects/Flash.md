# Flash
**What it does:** quick white flash.
**Good for:** cuts, beat drops. #effect #transition

## Command
```bash
# flash every 1s for 0.08s
ffmpeg -i in.mp4 -vf "eq=brightness='if(lt(mod(t,1),0.08),0.6,0)':eval=frame" -c:a copy out.mp4
# single flash at 2.0s
ffmpeg -i in.mp4 -vf "eq=brightness='if(between(t,2,2.08),0.6,0)':eval=frame" -c:a copy out.mp4
```

## Knobs
| param | does | default |
|---|---|---|
| `mod(t,1)` | interval in sec — match beat with 60/BPM | 1 |
| `0.08` | flash length | 0.08 |
| `0.6` | brightness | 0.6 |

## Notes
- Tested ✅
