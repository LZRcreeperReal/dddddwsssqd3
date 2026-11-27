# TikTok Editing Vault
Claude's memory for TikTok edits. Read this first before any edit.

- [[Editing Style]] — how edits should look/feel
- [[Effects Index]] — every effect we've built
- [[Effect Template]] — copy this to add a new effect
- `Assets/` — overlays, SFX, LUTs, PNGs
- `scripts/` — python effect scripts (aura.py)

## Rules
- Output: 1080x1920, 30fps, H.264 + AAC, `-movflags +faststart`
- Test every effect on a clip before saving it here
- When user says an effect looks bad, update its note (don't just retry the same thing)
