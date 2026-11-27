---
name: recut
description: One change to a cut — the run and what to change on the timeline, in plain words, go in; the change is recorded with its reason, the cut sheet gets a new version, the timeline is re-rendered and waits for approval. Use whenever someone says "bring the cutaway in later", "cut the pause at 0:12", "that B-roll should cover 'the razor', not 'the burn'", "swap the order of scene 2 and 3", "hold the headline longer", "recut", "change the timeline", "approve the timeline", or names a cut and one thing to move.
---

# Recut

> **Activates component:** `components/video-edit` — `machine/run.py change … timeline`.


External dependencies: `components/video-edit/` (the machine; `machine/cutsheet.py` the sheet's shape and the gate, `machine/steps.json` the steps, `learned.json` what the owner has taught the cut).

**One command, then the approval. A change is never a regeneration.**

```
python3 components/video-edit/machine/run.py change <run-folder> timeline "<what to change, in plain words>" --why "<his reason>"
python3 components/video-edit/machine/run.py start <kit-folder> --brand <brand> --label <label> --from gate
python3 components/video-edit/machine/run.py approve <run-folder> timeline [--note "…"]
python3 components/video-edit/machine/run.py status <run-folder>
```

- `change` records the ask and the why in `changes.jsonl`, copies the latest
  cut sheet to a NEW version (`cutsheet-vN.json`) and reopens the timeline
  stop. The session then edits that new sheet to do exactly what was asked —
  and only that — and `start … --from gate` runs the gate and re-renders the
  rough cut.
- `approve … timeline` moves it on to the captions stop. Every change goes
  back through learning at the end of the run.
- The same shape works at the captions stop with `captions` in place of
  `timeline` (a caption *look* is the `caption-look` skill).

## The rules the machine enforces — do not work around any of them

1. **The sheet is the edit.** A change is a new version of the sheet with
   its reason kept; the old version stays. Never an edit in place.
2. **Nothing renders red.** The gate names the field: a hole in the picture,
   a trim past the source, a caption or overlay inside the safe zone, a look
   or transition not on its list, a cut with no `why`.
3. **A talking clip keeps its own sound**; more than one frame of lip slip is
   HELD. Dead air is cut ON the clip.
4. **B-roll is placed by the WORDS it covers**, never by seconds — so "bring
   the cutaway in later" is a change to the words it covers, and it survives
   re-timing. B-roll with nothing under it is refused.
5. **A headline that opens the video is there on frame one** and lives
   exactly as long as the clip under it.
6. **The approved read is never touched.** No line is rewritten here — that
   is production's job.
7. **What the owner has taught outranks the prompt's own rules** (`learned.json`).

## What comes back

`runs/video-edit/<brand>/<label>/` — the new `cutsheet-vN.json`, the line in
`changes.jsonl`, the re-rendered rough cut and `timeline.html` at the
timeline stop.

Report: what changed (one line), the version number, whether the gate is
green, and the timeline page link.

Reply with the result and the folder it landed in (repo path or Drive folder name).
