---
name: stage-check
description: Check, verify and fix every handoff of a piece of work by its brief number — "check brief 0247", "stage check this run", "is 0243 ready", "where is this brief stuck", "pick up brief 0247", "verify these image ads", "run the stage check on the batch", "/stage-check <brief or run>". Walks every step in order (swipe → teardown → brief → record → number → pictures → approval card → Queue), says which step it stops at and why, and with --fix acts on each miss directly instead of re-running everything. Use it after making any asset, before handing work to someone, and when picking up someone else's piece.
---

# stage-check: every handoff checked, verified, fixed

> **Activates component:** `components/stage-check` — checks a piece against its lane's stages.


External dependencies (greppable): `components/stage-check/stage_check.py` (the engine),
`components/stage-check/lanes/<lane>.json` (each lane's steps: the file that proves each one, its checks,
its fix), `components/stage-check/criteria.json` (the written criteria a judged step must meet),
`components/image-teardown/briefs.json` (the brief register), `components/meta-upload/to_check.py` (the one
card writer), `runs/queue/<brand>/` (the Queue store).

Why it exists (the owner, 2026-10-25): things slipped through the cracks between stages, came in through
different doors and went unrecognised, or got re-run from scratch instead of fixed. "Anytime we make assets
or move one asset from one stage to the next stage there always needs to be a check or verification ... and
something that can actually action on making the update directly." A piece is found by its brief number
and folder, so anyone handed "brief 0247" can pull it and carry on from the exact step it stopped at.

## Steps

1. **Name the piece.** A brief id (`Brand A_flex_brief-0247`, or `brief-0247` with `--brand --product`) or
   an image-teardown run name. Several: `--batch id1,id2` or a file with one per line.

2. **Check.** `python3 components/stage-check/stage_check.py <ref>` prints one line per step (✓ / ✗ and
   why) and the step it stops at. It writes `runs/stage-check/<brand>/<piece>/latest.json`; read that
   instead of re-deriving where a piece stands.

3. **Fix.** Add `--fix`: each miss gets its own fix (re-run that stage and the ones after it, file the
   record, open the brief number, make the missing pictures, match them to the swipe's fidelity, file the
   approval card), then that step is checked again. Nothing is re-run that already passes.
   - A run that REPLACES an older brief: add `--replaces <old brief id>`. The old brief is marked
     deprecated and points at the new one; its card leaves the Approve list once the new card is filed.
   - A brief with no landing page: `--links <catalog link ids>`. A card with no words to reuse:
     `--words <words.json or copywriter run>`.

4. **Judge** (add `--judge`): the steps that carry written criteria (`criteria.json`, e.g. the brand
   step's native rules: the swipe's own colours, setting and words; product only where the swipe has a
   place) are read by the cheap model (run-kit's `reads` tier, Haiku). Only a fail calls the `checks` tier
   (Sonnet) to write the note the re-make carries. Never Opus for a check.

5. **End of every batch** (more than one piece, or `--review`): a completeness check of every piece and a
   review sheet, `runs/stage-check/<brand>/_batches/<time>/review.jpg` (each row: the real post, then its
   pictures, and where it stands) plus `summary.md`. Send the sheet to the owner for review.

6. **Report** one line per piece: the brief, the step it now stops at (or "every step passes"), and what
   was fixed. Show the pictures, never the check table, when the person asked to see the work.

## Rules

- **Six pictures, always** (the owner, 2026-10-25; it is in every brief): three headlines × two people-or-scene
  versions inside the swipe's own setting, read off stages 3-5 (`variants-plan.json`), one picture each,
  retried until each lands. Fewer than six is a fail the fix completes. A headline stage that stopped itself,
  or a variation stage with fewer than two variations, fails its own step and is re-made.

- **Fix, don't restart.** A miss is fixed at its own step; a passing step is never re-run.
- **Steps with no fix say so.** A run with no swipe (it was never opened on one) and the Queue (it syncs
  itself every minute) are reported, never forced.
- **A wordless swipe is said loudly, never rebuilt**: a static from it carries no words; pick a captioned
  post.
- **Nothing is deleted.** Pictures made from an old brand step go to `pictures-before-<time>/`; a replaced
  card stays in its folder, marked `superseded_by`.
- **Criteria change in `criteria.json`, never in code**, and the lane's steps in `lanes/<lane>.json`.
- The always-on image worker (`components/image-teardown/tools/worker.py`) runs this with `--fix` on every
  piece it finishes.

## Lanes

`image` (static ads from a swipe) is built. Video and email follow the same shape: a `lanes/<lane>.json`
with each step's proving file, checks and fix.

## Video route coverage

The engine resolves explicit maker route from the brief register and run records. AI uses video.json and requires generated-clip/edit/card evidence. Creator/founder uses video-creator.json and checks filming-brief readiness, not filmed footage. Unknown/conflicting routes stop with no repair. Human-route --fix never starts AI writing or production. Read components/WORKFLOWS.md for the route and review boundaries; passing a creator brief does not approve a shoot or a launch.
