# Car Edit Style (user's H7 edits)
Ref: user's own edit, "high quality greyscale koenigsegg edit", Mountain King Funk, account H7editz.

- **Greyscale** grade (contrast up) on all footage. Aura stays colored so it pops
- **Intro = car review clip** with the reviewer's voice (TikTok reviewers: zachsgarage, supercarblondie, carwow). Song plays quietly underneath
- **H7 logo** (`Assets/` → user's logo png, chrome H7 with santa hat on black): fades and zooms in over the intro shot, holds, fades out right as the drop hits
- **Drop:** hard cut on the drop with a flash, then cuts every 2 beats, zoom punch + shake + motion blur on every cut, flash on each bar downbeat
- Aura hero shots on the first bar of the drop and the last bar
- User adds extra effects themselves afterwards

## Pipeline (`scripts/car_edit.py` + json config)
1. `yt-dlp` TikTok videos work (`https://www.tiktok.com/@user/video/<id>`, list a profile with `--flat-playlist`). **YouTube downloads are bot-blocked here** (search works, downloads don't)
2. Pick an intro review line + shots (contact sheets at 1fps with timestamps)
3. Aura shots: extract greyscale clip → rembg per frame → `aura.py --layers ...`
4. `car_edit.py cfg.json`: song + bpm + drop time, intro clip, logo, shots `[src, start, beats, "aura"|""]`
- Watch for burned-in text in source clips (captions, "KOENIGSEGG ASMR") and start the shot after it
