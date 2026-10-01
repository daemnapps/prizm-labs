# Asset index

Turns a folder of footage into records you can search by what is *in* the
clip, not what the file is called. `IMG_5476.MOV` becomes "man patting his
face with a grey towel in a bathroom, profile reveal, usable as demo".

Two halves, deliberately split:

| Half | What it does | Cost |
|---|---|---|
| `extract.py` | frames + transcript + measurements, on this Mac | free |
| the prompt | frames + transcript -> one JSON record | ~$0.002/clip |

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
