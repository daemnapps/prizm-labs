# Seedance 2.5 — what it takes, and what works

*Rendered from `components/model-inputs/inputs/seedance-2.5.json` (read 2026-10-26, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 4 to 30
- aspect ratio range: 0.4 to 2.5
- max references total: 50
- max images: 30
- image max resolution: 4K
- max videos: 10
- max video seconds total: 30
- max audio clips: 10
- max audio seconds total: 30
- stable image subjects: 1 to 8
- stable audio video subjects: 1 to 5
- best reference video seconds: 5 to 10
- edit source max seconds: 20
- storyboard panels max: 15
- audio clip seconds: 2 to 15
- audio clip mb: 15
- resolutions: 480p to 720p to 1080p
- image formats: png to jpg to jpeg to webp
- House: resolution 480p, upscaled on this Mac; aspect 9:16; takes up to the configured maximum number of attempts (default 3 on Seedance, then the Kling backup as the last rung); each scored; the best-scoring one kept, a tie to the later, flagged below_criteria if it did not pass (V34); duration a talking take: its read × 1.15 + 0.6 s, rounded up (room for the model's own pauses); a silent one: its window; 4 to 30 s, the model's own range (the old 10 s cap was the retired Omni model's, removed 2026-10-28)
- A first-frame or last-frame ROLE locks the output to that picture's aspect and cannot sit beside audio on Higgsfield; a picture called 'the first frame' in the words is allowed and followed approximately.

## The prompt structure that works

- **Name every image, video and audio by its upload number and job: 'Image 1 is the first frame', 'Video 1 is for camera movement only', 'Audio 1 is the voice'. Upload in the order the subjects first appear.**
- **Then one summary sentence: subject, place, event, style, camera.**
- **A timeline in whole-second windows that touch, or 'Shot N'. One primary change per window; too little and it improvises, too much and it adds cuts or skips the action. Do not time fast repeated actions.**
- **End with what stays constant (camera, place, light, sound), then the few negatives.**
- **Say what you want. Negatives are supported for subtitles and audio ('no subtitles', 'no BGM').**
- **Name the shot size and ONE dominant move per shot ('slow push-in at eye level'); give an unusual term a plain explanation.**
- **When a reference is accurate, say to use it; do not describe it again.**
- **Name who speaks; keep a line's delivery next to it as 'Character's line (emotion): words'. Do not repeat dialogue words or attach tone notes to single words: it triggers subtitles.**
- **Replace an emotion label with a trigger, a visible physical response and a delay. A strong emotion word can make the eyes glow.**
- **Name the visual bridge across a cut or join; describe the boundary state (pose, prop, light, camera, motion direction) on both sides of an extension.**
- **Give each file one job and state what it must NOT pass on; bind each subject one by one, not 'images 1 to 4 respectively'.**
- **A task that mixes several references and edits is unstable: split it into simpler passes.**

## Avoid

- Typing the line beside its audio: it triggers burnt-in subtitles and says the words twice.
- Strong emotion labels ('fanatical', 'extremely shocked'): they can light the eyes or overact.
- Vague words ('cinematic', 'epic reveal', 'dynamic camera', 'make it emotional and beautiful').
- Long generic blacklists: they compete with the scene.
- Several events or exact timestamps in one short window: extra cuts, skipped actions.
- A reference video with subtitles, voices or music you do not want: they override the prompt unless rejected.
- 'Based on all references', an unused file, or a mapping that lives only inside a picture.
- A locked tripod and aggressive handheld in the same beat; one continuous take with five cuts.
- Words the model must spell: it misspells; give them as a reference picture or lay them on later.
- A first/last-frame role beside audio references on Higgsfield (the 422).
