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
