# The editor sheet — what arrives per scene

`SUBMIT.md`, written by `machine/run.py start` when a house is forced with
`--provider` (the machine hand makes everything otherwise). One block per
item, in the order they run. Since the scene shape landed on 2026-09-18 a
scene arrives as **three blocks and one page of audio**, and this page says
what each of them is for. The older page, written for the two-hands
period, is `../archive/EDITOR-SHEET.md`.

## The audio, once, at the top

**Voice.** One continuous track for the whole piece — `vo/track.mp3` — and
one slice per scene, `vo/<scene>.mp3`. The slices are cuts of that one
track, not separate takes, which is the point: the read does not restart
between scenes, so the cut between two clips does not either. Upload the
slice a scene names, not the whole track.

`vo/timing.json` travels with them: where every scene and every sentence
sits on the one timeline. It is what the beats in every clip prompt were
timed against, so if a clip comes back long or short, that file is the
reference — not a stopwatch.

## Per scene, three blocks

**1 · `<scene>-F1` — the FIRST FRAME.** A generation. Its references are
listed in order and the first one is the one whose detail the door
preserves. Upload the result; its media id becomes the clip's
`start_image`.

**2 · `<scene>-FLAST` — the LAST FRAME.** An edit of the first frame, whose
prompt is the delta and nothing else. It carries **two** references, the
first frame first and the cast sheet second, and it has already been
colour-matched back to the first frame, so the pair share exposure, white
balance and size. Upload it; its media id becomes the clip's `end_image`.

**3 · `<scene>` — ONE clip.** Never one per line. The block names:

- **start_image** — the file made as `<scene>-F1`;
- **end image** — the file made as `<scene>-FLAST`, attached where the door
  takes one. **Where it does not, the block says so in that line** and the
  last frame is carried by the timeline's final beat instead — so an editor
  can always tell which of the two happened without asking;
- **beats** — how many, all timed off the one voice track;
- **door** — which door this clip is for;
- **audio_references** — the scene's slice of the track, on a to-camera
  scene;
- every other parameter the door takes: aspect, resolution, duration,
  `generate_audio`, the mode.

Then **the prompt, exactly as the model receives it**, in a fenced block —
the asset line, the one-sentence summary, the timeline of beats with their
spans, and what holds. Nothing is paraphrased between this page and the
request: what is printed is what is sent.

## What the sheet will not contain

- **No number anybody chose.** Durations and beat spans come from
  `vo/timing.json`; aspect and resolution come from the piece, declared
  once.
- **No middle frames.** A scene has two stills. A beat is an instruction
  inside the clip, and asking for it as a picture is the drift the shape
  removes.
- **No item that failed the contract gate.** `preflight.py check` runs
  every item against `machine/model-inputs.json` first; anything red stops
  the run, so a sheet that exists is a sheet whose every block is complete.

## Handing results back

    [{"id": "...", "job": "...", "url": "...", "seconds": N,
      "status": "done|nsfw|ip_detected|failed"}, ...]

    python3 machine/run.py record <run-dir> --results results.json

Every talking clip is transcribed and compared to its paragraph on the way
back in; lip-sync to the wrong words is a FLAG, not a pass.
