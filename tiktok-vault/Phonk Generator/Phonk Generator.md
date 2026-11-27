# Phonk Generator
Goal: turn normal songs into **drift phonk** or **Brazilian funk** (automotivo/montagem) for car edits.

- [[SFX Library]]: 100 sfx sorted by category, when to use, how to make
- [[Song to Phonk]]: conversion recipe (drift phonk)
- [[Song to Funk]]: conversion recipe (Brazilian funk / automotivo / montagem)
- [[Car Edit Examples]]: reference tracks, car edits only

## Rules
- References = **car edits only** (drift, JDM, street, car meets)
- "Funk" = Brazilian funk (automotivo/montagem), not 70s funk
- Car sfx (screech, turbo, rev) need real recordings. Everything else can be synthesized (marked **S** in the library)
- Check licenses before using any downloaded sample in monetized edits

## Build plan
1. sfx synth script: generate every **S** sound in [[SFX Library]] to `Assets/phonk/`
2. song analyzer: BPM + key (librosa)
3. converter: stems (demucs) → retime → add drums/cowbell/808 → sfx placement → master

## Progress
- `scripts/phonk_kit.py`: synthesized kit (kick, snare, clap, hats, crash, 808 cowbell, 808 bass, pad, riser, downlifter, whoosh, boom, impact, vinyl, tape stop) plus synth car sfx (screech, turbo spool, BOV, flutter, exhaust pops, backfire, rev). Numbers match [[SFX Library]].
- `scripts/remix_mountain_king_phonk.py`: first remix. Grieg "Hall of the Mountain King" (public domain) as drift phonk, 150 BPM, B minor, 38s. Structure: muffled intro + rev → riser/turbo → silence → drop (boom, crash, screech) → break with snare roll → drop 2 (busier + backfire) → tape stop.
- Export: `loudnorm I=-9` lands ~-10.5 LUFS. Pre-limit mix ~-14.
- Lessons: too much 808 + master drive = -6 LUFS mud that buries the cowbell. Highpass the bass at 30Hz, keep the cowbell louder than the bass, and make the intro quieter so the drop hits.
- Source songs/sfx: online public-domain recordings were copyrighted or rate-limited, so v1 is all synth. User can drop their own sfx/songs into `Assets/phonk/` to swap in real sounds.

## v2: real orchestra (user rejected the all-synth version)
- **User wants:** a REAL orchestra recording as the audio plus phonk vocal chops. Not synth melodies.
- Source: Musopen Peer Gynt session (public domain) on archive.org, `musopen-grieg-peer-gynt-compressed`. It's a zip of a multitrack session, and single files can be fetched via `.../Grieg_-_Peer_Gynt.zip/Grieg%20-%20Peer%20Gynt%2FPeer%20Gynt%2FAudio%20Files%2Fpremix_03.L.wav` (and `.R`). **premix_03 = Hall of the Mountain King** (96k/24bit, 178s, crescendo; ~107 BPM at the start, accelerating to ~200).
- `scripts/remix_orchestra_phonk.py`: sample-based phonk. Beat-tracked loops time-stretched to 155 BPM. Quiet theme (26.37–30.87s) → half-time intro. Climax loops (155.89–160.57, 130.24–135.04) → drops. Real final chords as the outro. Orchestra highpassed at 90Hz so the 808 owns the low end.
- Vocals: Piper TTS (`en_US-ryan-high`, from HF rhasspy/piper-voices) → pitch −4 to −7, phone bandpass, saturation, short reverb, stutters. Raw tags are in `Assets/phonk/vox_raw/`.
- Finding loops: chroma-match the theme on an eighth-note grid over beat-tracked windows (theme pitch classes in B minor).
- Wikimedia API rate-limits this container. archive.org works.
