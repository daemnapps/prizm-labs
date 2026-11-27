# Wan 3.0 (a person's pick) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/wan-3.0.json` (read 2026-11-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 2 to 30
- smart duration: -1 lets the model choose the length; the door always sends a number
- resolutions: 480p to 720p to 1080p
- aspect ratios: auto to 16:9 to 9:16 to 1:1 to 4:3 to 3:4
- image formats: png to jpg to jpeg to webp
- max images: 2
- start and references: start_image / end_image cannot be combined with image, video or audio references on this door
- max image references: 10
- max video references: 5
- max video seconds total: 15
- max audio clips: 5
- max audio seconds total: 15
- credits per second: {'480p': 1, '720p': 1.75, '1080p': 3.5}
- price per second usd: 0.05 / 0.10 / 0.20 (480p / 720p / 1080p) on the keyed API, fal and Alibaba
- reference mode: Reference mode (reference pictures + voices + motion video, no start picture) is the mode a continuous take uses: the picture rides as a reference, so the first frame is rebuilt from it, not copied.
- fal route: {'endpoint': 'alibaba/wan-3.0/reference-to-video', 'key': 'FAL_KEY', 'reference_video_plus_output_max_seconds': 30, 'enable_safety_checker': "false turns off fal's own checker only; the vendor still moderates the model ('model_moderated', read 2026-11-09)", 'read': '2026-11-09, fal openapi schema and two live calls'}
- start frame mode: A start picture with no references: the exact first frame and the script; the model speaks every line in its own voices (our reads are laid after). Takes a first frame in bikinis on Higgsfield (2026-11-09).
- higgsfield cli media flags: --start-image, --image-references, --audio-references, --video-references; repeat a flag for several files; local paths are uploaded
- output: MP4, 30 fps [official]
- image rule: jpg/jpeg/png (no transparency)/bmp/webp, 240-8000 px a side, aspect within 8:1, 20 MB each [official]
- video rule: mp4/mov, 1-15 s each, 15 s total, at least 16 fps, input + output at most 30 s, input seconds billed [official][vendor fal]
- audio rule: wav/mp3, 1-15 s each, 15 s total, 15 MB each [official]
- max references total: 20
- prompt max chars: 20000
- prompt over limit: truncated, not refused [official]
- seed: not reproducible even when fixed [official]
- House: role an option on every micro-drama quote, picked at the owner's go (2026-11-27); Seedance 2.5 stays the default when he names none; mode reference mode: each speaker's sheet, the place sheet, the product sheet as image references; one voice sample per speaker; optional silent camera rehearsal as Video 1; resolution 480p, then the house's own upscale or phone pass; aspect 9:16; sound on; duration the shot list's length, 4-15 s typical; voice_budget 15 s across all samples: two speakers about 5-7 s each, three about 4-5 s each; takes one take, another only on failure; start_frame_route image-to-video from one approved start picture, sound off: single silent shots only

## The prompt structure that works

- **With a start picture, say it is the first frame and describe only what changes: the action and the camera.**
- **Say the camera keeps the first frame's framing; left unsaid, the first take pushed in from full body to waist-up within a second.**
- **One action per shot, written as visible movement.**
- **Overall description, reference citations, shots with timestamps (subject, place, move, camera), dialogue, sound, style and mood, negative list. Leave out a section the clip does not need.**
- **Name references 'Image N', 'Video N', 'Audio N', counted by upload order within each type; with two or more of a type always use the number.**
- **Say what each reference gives and nothing more: 'Image 1 is <name>, one <man|woman>, a character sheet: face, hair, skin, build and clothing only'; 'Image 3 is the room: layout and light only; nobody from it appears'; 'Video 1 is used only for camera movement; take no people, look or sound from it'.**
- **One 'Subject locking: <name> Image N, ...' line; restate each person's key traits in the shots; 'consistent throughout' and 'they do not look alike'.**
- **Once per speaker: '<Name>'s voice timbre references Audio N, <register>'; take only the voice characteristics and have the person say the lines below.**
- **Each line inside its shot: '<Name> says (<delivery in face and voice words>): "<exact words>"' then 'Lip sync.' Name the speaker on every line; never two speakers' lines in one sentence.**
- **After the shots: 'Only the quoted lines are spoken, word for word, in <language>, each once, by the named speaker; no other speech.' A shot with no lines says 'No one speaks in this shot.'**
- **'Shot N [a-bs]:' windows that touch, 2-5 s each, one bracket style throughout, each ending 'Hard cut.'; 'One continuous shot.' on the first line for a single take. No fast repeated actions.**
- **A 'Fixed spatial relationships:' line: who stands left or right, by what landmark, and that nobody crosses.**
- **Shot size, angle and ONE named move per shot in plain words (handheld follow, push in, pull out, whip pan, snap zoom, orbit, tracking, tilt); no stacked moves. Fits the drama camera recipe: a move in every shot, a cut every 2-3 s.**
- **Name the room sound and the action sounds in their own sentence and write 'no background music'.**
- **No negative field exists: end the prompt with 'Negative prompt list:' and only the real risks (subtitles, on-screen text, watermark, a third person, twins or duplicate faces, costume change, face drift, background music).**
- **150-300 words; few beats for the seconds, or the end compresses or drops.**

## Avoid

- Sending reference pictures, clips or sound together with a start picture: the door refuses the mix.
- Leaving generated sound on: it is on by default.
- Naming a real person, brand or franchise in the prompt: the vendor's moderation checks prompts, pictures and the finished clip.
- Expecting it to speak our locked voice read from a start picture: on this door a start picture cannot carry audio.
- Prompt words that call Image 1 the first frame in reference mode: no frame travels with references, so the model may paste a sheet in as the opening.
- A reference picture with more than one person or a busy background, or one reference doing two jobs.
- A storyboard or multi-panel picture with no line saying it is shot guidance only: it is read as one frame.
- Style labels like a genre name that can turn into on-screen text: describe the look instead.
- Two voice samples close in pitch and pace: they blur into one voice.
- Two angles of one moment made as two calls: the scene is rebuilt differently; cut them inside one call.
