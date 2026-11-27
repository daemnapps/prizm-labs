---
name: frame-edit
description: Change one thing on a scene's frame in a video production run — the run, the scene number and the ONE delta go in; the edit is written against that scene's plate with its keep/change split, queued, and comes back as a new take beside the old one. Use whenever someone says "scene 3: the product is in the wrong hand", "she should be front-on in scene 1, not in profile", "fix the frame on scene 2", "redo scene 4 but keep everything else", "frame edit", "show me what scene 3 keeps", or names a run, a scene and one change.
---

# Frame edit

> **Activates component:** `components/video-production` — `machine/edit.py`, one scene at a time.


External dependencies: `components/video-production/machine/edit.py` (the tool; it imports the discipline from `components/image-edit`), the run's own `storyboard.json` (the scenes, their plates and their splits), the run's board (`machine/storyboard.py` / `machine/board.py`, which drain the queue on the direct doors).

**One command. One scene. One change.**

```
python3 components/video-production/machine/edit.py <run-folder> --scene <N> --change "<the ONE thing to change>"
python3 components/video-production/machine/edit.py <run-folder> --scene <N> --show          # the split and every past instruction
python3 components/video-production/machine/edit.py <run-folder> --scene <N> --change "…" --dry
```

- The run is a video-production run (`runs/video-production/<brand>/<label>/`)
  whose scene already has a plate — a scene with no take is refused
  ("generate one first").
- `--show` prints the scene's LOAD-BEARING (never changes) and SWAPPABLE
  (may change) lists and every edit asked so far, with any refusal.
- **`--dry` writes the request into the scene's record and queues nothing**
  — it spends nothing.
- A real call queues the edit on the run's storyboard; the queue is drained
  on the direct doors by the run's board (pressing Generate), and the new
  take lands beside the old one — the old take is archived with the note,
  never overwritten.

## The rules the command enforces — do not work around any of them

1. **An edit instruction must never describe anything the plate already
   shows.** The plate rides along as the reference; the instruction carries
   the delta and nothing else. Past ~400 characters it has started
   describing the scene and is refused rather than spent.
2. **One change per edit** (two at a push). Counted; refused past that.
3. **The keep/change split is a written decision, not a guess.** Each scene
   type has its default (A: the presenter's identity, wardrobe and room hold;
   B: the product's geometry, whose hands, what the beat demonstrates hold;
   C: the product's geometry and finish, no rendered lettering, hold). A
   scene's own split outranks the default.
4. **When the change is ABOUT a banked thing, the bank comes too** — the
   real product, the trained identity — referenced by id, never re-described.
5. **Type is never generated.** Captions and prices are layers over a clean
   plate.
6. **A regen is an EDIT off the plate, never a fresh shot.**

## What comes back

In the run's `storyboard.json`: the scene's `edits` list (asked, the
instruction as sent, chars, changes, the reference take, the keep list, any
refusal) and the queued order; then the new take on the run's board, the
old one archived. Nothing leaves `runs/video-production/<brand>/<label>/`.

Report: the instruction as sent (it is short — show it), queued or refused
and why, and the board link; when the take lands, the new frame beside the
old as images.

Reply with the result and the folder it landed in (repo path or Drive folder name).
