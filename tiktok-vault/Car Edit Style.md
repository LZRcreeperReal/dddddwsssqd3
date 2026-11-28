# Car Edit Style (user's H7 edits)
Ref: user's own edit, "high quality greyscale koenigsegg edit", Mountain King Funk, account H7editz.

- **Greyscale** grade (contrast up) on all footage. Aura stays colored so it pops
- ~~Intro = review clip~~ → user changed this: **NO people in any clip** (no reviewers, hands, drivers or pedestrians clearly visible) and **NO captions/burned-in text**
- **Footage = raw supercars driving on the road** (spotting style, like the example edits). Best raw source: TikTok **@hypercarsoflondon** (raw London/Monaco spotting). Only use clips TikTok serves in **1080p**: check with `yt-dlp -S res,br --print '%(height)s'`, since many are only 540/720p
- **Quality matters a lot**: decode with lanczos + light hqdn3d + unsharp, render aura intermediates at crf 6–11, final x264 crf 12 slow tune film, 320k audio. Don't double-encode at low quality, and don't blur frames except for intended whips
- **Aggressive + clean** = fast beat cuts, but **NO screen shake, NO zoom-in/zoom punches** (full frame, framed like the reference edits). Flash on the drop only
- **Aura is per-video**: the user said forget it for the hypercars edit. Ask/decide per edit, not by default
- **Format: RAW full frame.** NO cropping or zooming of clips. A landscape crop out of vertical clips = zoomed in and rejected ("they aren't raw", bad tracking). Vertical clips → vertical 1080x1920 output. Only make landscape if the source footage is landscape
- **Cut on EVERY beat after the drop** (new clip each beat)
- **Intro jump cuts**: on every beat in the intro the same clip skips ahead 0.8s (`jump` flag, `jump_skip` 0.8, `beat0` = song beat phase) and plays normally between beats
- **User HATES the ink/aura transition**. Don't use it. Straight beat cuts + the preview transitions (their last 2) only
- **Rev clip**: one shot should be a car revving, **rev WAY louder than the song** (boost the rev to ~-8 dB RMS, duck the song to ~0.38 under it). Pick a sustained pull, not short blips: hypercarsoflondon f12.mp4 9.7–12.4s = V12 pull, with its audio carrying on under the next beat cuts (`rev` flag in car_edit2: ~2.3s of the clip's audio, highpassed, faded). Find revs by RMS spikes + broadband harmonic blips in the spectrogram (hypercarsoflondon huracan.mp4 ~14.5s = double blip)
- **H7 logo** (`Assets/` → user's logo png, chrome H7 with santa hat on black): fades and zooms in over the intro shot, holds, fades out right as the drop hits
- **Drop:** hard cut on the drop with a flash, then cuts every 2 beats, zoom punch + shake + motion blur on every cut, flash on each bar downbeat
- Aura hero shots on the first bar of the drop and the last bar
- User adds extra effects themselves afterwards

## Transitions copied from the user's edit (`car_edit2.py`)
- **ink** (aura transition): the next shot's car is revealed through a growing ragged ink mask (distance from the car's cutout + noise), with a white torn fringe on the mask edge, then a radial zoom-blur whip lands on the beat
- **preview** (the user's last 2 transitions): the next shot's subject is cut out and fades in over the current shot as a glowing white silhouette, settles to real tone, then hard cut. The edit ends with a fade to black
- Cutouts: `scripts/cutout_seq.py` keeps the biggest blob only. `bria-rmbg` is much more accurate than isnet but ~10s/frame on CPU. Pick aura shots with ONE car and nothing in the foreground

## Pipeline (`scripts/car_edit.py` + json config)
0. User sends the song as a screen recording of the TikTok sound page: pull the audio, find where it loops (TikTok previews loop) and where the drop is (low-band energy jump)
1. `yt-dlp` TikTok videos work (`https://www.tiktok.com/@user/video/<id>`, list a profile with `--flat-playlist`). **YouTube downloads are bot-blocked here** (search works, downloads don't)
2. Pick an intro review line + shots (contact sheets at 1fps with timestamps)
3. Aura shots: extract greyscale clip → rembg per frame → `aura.py --layers ...`
4. `car_edit.py cfg.json`: song + bpm + drop time, intro clip, logo, shots `[src, start, beats, "aura"|""]`
- Watch for burned-in text in source clips (captions, "KOENIGSEGG ASMR") and start the shot after it
