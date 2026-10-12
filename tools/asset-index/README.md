# Asset index

**Keys this tool needs:** none. Put your own in `.env` at the top of the repo — see [`.env.example`](../../.env.example).

Turns a folder of footage into records you can search by what is *in* the
clip, not what the file is called. `IMG_5476.MOV` becomes "man patting his
face with a grey towel in a bathroom, profile reveal, usable as demo".

Two halves, deliberately split:

| Half | What it does | Cost |
|---|---|---|
| `extract.py` | frames + transcript + measurements, on this Mac | free |
| the prompt | frames + transcript -> one JSON record | ~$__/clip |

`content-machine/asset-index/prompts/index1-clip-v1-damon.md` is the prompt.

## Running the free half

```
tools/asset-index/.venv/bin/python tools/asset-index/extract.py "<folder>" <out_dir>
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

## Our own footage first (the owner, 2026-10-06)

Before production generates a B-roll scene, it asks the index whether we
already own the shot:

    python3 tools/asset-index/machine/search.py --brand <brand> "man runs fingertips along his jaw"

`search.py` scores every SCENE inside every indexed clip — what it shows and
what is said in it — against the description, with no service and no network.
Same records and same words, same answer. It returns only clips that resolve to
the shared drive everyone can open (`shared_paths.py`: each record's file is
found there by name, confirmed by size; set `SHARED_ASSETS_ROOT` to that
drive's folder holding `brands/<brand>/`). Each hit carries the clip, the time
range, the shared path, the nearest frame and a score from 0 to 1.

Tests: `python3 tools/asset-index/machine/test_index.py` (12, temp folders only).
