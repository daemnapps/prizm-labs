# Asset index


Turns a folder of footage into records you can search by what is *in* the
clip, not what the file is called. `IMG_5476.MOV` becomes "man patting his
face with a grey towel in a bathroom, profile reveal, usable as demo".

Two halves, deliberately split:

| Half | What it does | Cost |
|---|---|---|
| `extract.py` | frames + transcript + measurements, on this Mac | free |
| the prompt | frames + transcript -> one JSON record | ~$0.002/clip |

`components/asset-index/prompts/index1-clip-v1-owner.md` is the prompt.

## Running the free half

```
python3 components/asset-index/machine/extract.py "<footage folder>" --brand <brand> [--label <name>] [--out <dir>] [--limit N]
```

Resumable — a clip with a `clip.json` is skipped, so it can be stopped and
restarted. Writes one folder per clip: frames at 384px, and `clip.json` with
path, duration, dimensions, frame timestamps and the transcript.

## Measured (2026-09-09, Rashad folder, 20 clips)

- 28.6 min of footage -> 73 frames, 3,545 words transcribed
- ~6s per clip end to end, including pulling from Drive
- 3.65 frames per clip average

## Traps

- **Whisper lives in `.venv`.** Homebrew Python refuses global installs
  (PEP 668) and breaking that would risk his system Python.
- **Frames win over rotation flags.** iPhone footage reports landscape
  dimensions with a `-90` rotation; the frame is the truth.
- **`base.en` is the model.** Good enough for indexing speech, fast on CPU.
  Bigger models cost hours across thousands of clips and change nothing about
  whether a clip is findable.

## The footage library (2026-11-06)

`library/` sorts every scene into one vocabulary keyed to the doctrine (beat, product, tier, polish, text
marks, handles, people, editor in/out on the real shot change) and answers a storyboard blank. The video chain's footage step reads it. Rules and
commands: `CLAUDE.md`, "The footage library".


## Who is on screen and what happens: the cast pass (2026-11-20)

`library/cast.py --brand <b> run [--dry-run] --budget <USD>` (paid, Gemini 3 Flash at low media resolution, about
$0.003 a clip) asks `prompts/cast-pass-v<N>-owner.md` of each clip's local proxy: the distinct persons (gender, age
band, visible skin tone, a look line, which one the clip is about), letterbox, and per scene who is on screen, face
visible, couple, action and action tags, product in use, a competitor brand, room, framing, angle, camera move,
emotion. `apply` writes those onto every library row (`people_count`, `people`, `person_ids`, `main_person`,
`woman_present`, `couple`, `face_visible`, `action`, `action_tags`, `product_in_use`, `competitor`, `room`, `framing`,
`angle`, `camera_move`, `emotion`, `letterbox`, `cast_checked`, `cast_reason`); a row it cannot fill says why.
`coverage` writes `library/coverage-story.{json,md}`: per story beat in `library/story-beats.json` (bathroom routine,
gym, couple, party, wedding, barber, office…) the clean owned scenes and named creators, and which beats are gaps
for generation. Why: Real-lane ads cast named creators in fixed roles and cut only from owned footage; casting
could not see people or story in the index. Person ids: the main person of a clip is `<brand>/<creator>` when the
creator folder is a real person, so one person is findable across clips; others are scoped to the clip. Skin tone is
the visible shade only; ethnicity stays the Drive filing's. `index_new.py` runs it after the build each pass
(new clips, then the backlog, inside the one cap). Proxies in another checkout are found through
`ASSET_INDEX_MEDIA_ROOTS`. Tests: `library/test_cast.py`.

**Per brand, from the brand's own settings (2026-11-20):** everything brand-specific in the library pass lives in
`brands/<brand>/footage-library.json` (shape in `brands/_TEMPLATE/footage-library.json`): the product category and
competitor names the cast pass asks about, the creator filing folder (`creator_root`, read by `library.creator_of`),
the footage folders `index_new.py` describes, the brand's own actions, rooms and story beats added to the shared
ones, person aliases (one creator filed under a handle and a folder name), and the daily schedule and cap
(`library/daily_brands.py`, read by `run-daily.sh` and the machine's scheduler). A new brand joins by adding that file;
no code changes. The shared words stay in `library/cast.py` and `library/story-beats.json`.
