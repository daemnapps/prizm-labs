# ElevenLabs Music v2.5 — what it takes, and what works

*Rendered from `components/model-inputs/inputs/eleven-music-v2.5.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 3 to 600
- sections max: 30
- section seconds: 3 to 120
- styles per section max: 50
- negative styles per section max: 50
- lines max house: 30
- chars per line max house: 200
- music length ms: 3000 to 600000
- style language: styles must be English; lyrics may be any language
- House: context_adherence high; seed 1; format mp3_44100_192; level -14 LUFS copy; remake once, seed + 1; style one ruled row from banks/music-styles/index.json, no free text

## The prompt structure that works

- **Use a composition plan for control; a plan and a text prompt cannot be mixed.**
- **The first section's styles set genre and tone for the whole piece: load it with 6 to 7 or more specific styles.**
- **Name what you hear ('warm acoustic guitar with light fingerpicking', '80 BPM'), not moods alone.**
- **Use negative styles liberally to keep unwanted sounds out.**
- **Put inline directions in curly braces inside the text, never parentheses.**
- **Every section 3 to 120 s, at most 30 sections, 10 minutes total; the house caps lines at 200 characters and 30 lines.**
- **Every sung line must be a script line and every script line sung; the song is transcribed and each line must be heard at 0.75 or better.**
- **A failed gate remakes ONCE with seed + 1, then stops naming the missing line.**

## Avoid

- Copyrighted names or content in styles: the plan is rejected as bad_composition_plan.
- Parentheses for inline directions.
- A plan and a prompt in one call.
- A thin first section: the whole song comes out generic.
- A free-text style instead of the ruled row.
- Styles in another language.
