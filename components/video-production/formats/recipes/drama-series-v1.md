# Recipe · a micro-drama series, planned ahead (v1)

Every micro drama runs the same `micro-drama` workflow, one film at a time. A series is not a station of that
workflow: it is planned ahead of time (which parts, what each part does, the one creative matrix row they all share),
and then each part runs the workflow on its own. When a part follows a part that is already made, its story is written
from what that part actually shows on screen in its accepted final cut, never from its script, brief or plan: a scene
that was written but never made, or a product beat that was cut, does not exist for the next part.

Why: a part 2 was once written against part 1 scenes that were never produced (the product never appears in the
part 1 that was made), and the writing fork picked a fresh creative matrix row for it, so part 2 came out in another
look, setting and product moment from part 1.

## Plan ahead

Before part 1 is written: the series slug, how many parts, each part's job, and the matrix row every part keeps.
Then each part runs the `micro-drama` workflow; the steps below sit beside its writing station.

## Part 1

Write `series.json` in part 1's workflow folder:

```json
{"series": "<series slug>", "part": 1}
```

After its writing passes, `drama_series.py written <series.json> --writing-run <run>` records part 1's creative
matrix row in `continuity.json`, which the next part pins to.

## Part 2 and later

1. **The cut.** Name part N-1's accepted final cut: a repo path (with its sha256) or `{drive_id, label}`. The cut
   that went to the approval page, not a draft.
2. **The on-screen read** (`previous-part-on-screen.md` in the workflow folder). Watch the cut: stills every second
   and the sound transcribed. Write, in order:
   - every shot as seen: who is in it, where, what they do, the camera;
   - every line as heard, with its speaker;
   - every moment the product is on screen and what it is doing, or the sentence "The product never appears on
     screen.";
   - the cast, wardrobe, places and props as they look;
   - the last frame: who is where, holding what, and the line or action it ends on;
   - the open threads the cut leaves a viewer with.
   Name nothing the cut does not show.
3. **The story** (`story.md` in the workflow folder). Part N's story, picking up from the last frame and the open
   threads. Its first line is `Built from: <path of previous-part-on-screen.md>`. It goes into the writing chain
   through `--story`; the swipe keeps giving the format and structure.
4. **The pin.** Part N's creative matrix row is part N-1's row, taken from part N-1's `continuity.json`
   (`matrix_cell`: batch and row). Before the writing runs, pin it into the new piece:
   `run.py <teardown> --piece <label> --fork-only`, then
   `creative_matrix.py cell <brand> <batch> <row> runs/video-teardown/_work/<label>`, then
   `run.py <label> --story <story.md>`.

`series.json` for part N:

```json
{"series": "<series slug>", "part": 2,
 "previous": {"workflow": "runs/video-production/<brand>/workflow-<label>", "cut": {"path": "...", "sha256": "..."}},
 "on_screen": "runs/video-production/<brand>/workflow-<label>/previous-part-on-screen.md",
 "story": "runs/video-production/<brand>/workflow-<label>/story.md",
 "pin": {"batch": "<matrix batch>", "row": "<row id>"}}
```

`drama_series.py check` holds the part before any paid writing; `drama_series.py written` holds it after writing
when the writing run's row is not the pin or its story is not this story.
