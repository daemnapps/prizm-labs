# Kling 4.0 (backup) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/kling-4.0.json` (read 2026-10-26, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 3 to 30
- resolutions: 720p to 1080p
- no 480p: Kling 4.0 has no 480p: the backup is made at 720p and upscaled on this Mac like every clip
- aspect ratios: 21:9 to 16:9 to 9:16 to 1:1 to auto
- max element ids: 7
- audio reference: none: no Kling model on Higgsfield takes our audio
- kling 3 0: {'duration_seconds': [3, 15], 'modes': ['std', 'pro', '4k'], 'sound': ['on', 'off'], 'max_shots': 5, 'shots_total_seconds_max': 15}
- price per second usd: from 0.11 (list 0.157) at 4.0; from 0.042 (list 0.084) at 3.0 — Higgsfield list, not measured
- House: role backup only, behind Seedance; mode image-to-video from the approved start picture; resolution 720p, upscaled locally; aspect 9:16; sound off (it cannot take our voice); duration the clip's own length, 3 to 10 s; takes the backup is the last rung: one attempt, scored like the others; the best-scoring attempt overall is kept (V34)

## The prompt structure that works

- **Cover subject, action, camera behaviour and visual style.**
- **With a start picture, treat it as the anchor: describe only how the scene changes (movement, camera, environment), not what is already in it.**
- **One action and one camera move per shot; split several events across shots; do not pack many shots into a short clip.**
- **State the camera move explicitly (tracking, panning, staying in a medium shot, resuming smoothly); the model follows a described move through the clip.**
- **Motion follows gravity, inertia and the environment; explicit motion descriptions reduce artifacts.**
- **If an end frame is attached the prompt must describe motion that can plausibly reach it, else it drifts; simplify the prompt and let the frames carry direction.**
- **Close with locks and the few negatives ('no subtitles', 'no on-screen text').**
- **(If native speech were used) give every speaker a unique label, put the action before the line, and tone cues per speaker. Not used: our voice is ours.**
- **Draft at 720p, lock the prompt and structure, then render the final at the size needed; do not iterate at 4K.**

## Avoid

- Several actions or camera moves in one shot.
- Vague camera or motion language in fast or continuous shots.
- Motion that conflicts with an attached end frame.
- Packing five shots into a short duration.
- Pronoun-only or unlabeled speakers (if speech is ever used).
- Expecting reference-video motion transfer from the base model: that is Kling Motion Control, a separate model.
- Using Kling's native speech for a line that must be OUR voice: it will not be our read.
