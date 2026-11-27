# stage-check — every handoff checked, verified and fixed, by brief number

**stage-check** takes **a piece of work, named by its brief number or its run**, and makes **a step-by-step
verdict** (which step it stops at and why), and with `--fix` **acts on each miss directly**. Does not make
creative itself: every fix calls the tool that owns that step. Triggered by
`python3 stage_check.py <brief id | run> [--fix] [--judge]`, the `/stage-check` skill, and the always-on
image worker after every piece.

**Owner:** the owner (engine and definitions). Created 2026-10-25 directly on his word ("i need clear skills ...
anytime we make assets or move one asset from one stage to the next stage there always needs to be a check
or verification ... and something that can actually action on making the update directly"); lab station
skipped (the creative-controls precedent). Not `marketing-chain-checks` (which reports and holds, and fixes
nothing) and not `qc-checks` (which checks a finished asset): this one walks the handoffs and repairs them.

| New-resident question | Answer |
|---|---|
| Engine + owner | `stage_check.py` — the owner |
| Definitions + curator | `lanes/<lane>.json` (each lane's steps: proving file, checks, fix), `criteria.json` (written criteria for judged steps), `prompts/*-vN-owner.md` — the owner. Every file `status: draft` |
| Plane | `runs/stage-check/<brand>/<piece>/latest.json` + `history.jsonl` |
| Manifest | `latest.json` per piece: the brief, the run, `next` (the step it stops at, or `done`), every step's ok/why/judged/note/fixed |
| Runs by | both |

## How a step is held to account

Each step in `lanes/<lane>.json` names: the file that **proves** it happened, the **checks** it must pass
(`stage_check.py` `check()`), an optional **judge** (a criteria set in `criteria.json`), and its **fix**
(`fix()`), or `why_no_fix`. The engine checks every step in order; with `--fix` it acts on a miss and
checks that step again; with `--judge` the cheap reader (`run_kit.model.TIERS["reads"]`) answers the
criteria, and only a fail calls the `checks` tier for the fix note, which rides on the re-made stage's
prompt through image-teardown's viewer-notes hook.

## What it uses, and through which door

- the brief register: reads `components/image-teardown/briefs.json`; numbers through `tools/briefs.py open`;
  `--replaces` marks the old brief through `briefs.load/save`
- the stages: `components/image-teardown/tools/run.py <run> <stages>`; the record: `tools/gates.py
  file_record`; the pictures: `tools/pictures.py` and `native_finish()`
- the card: `components/meta-upload/to_check.py` (the one card writer, its LIBRARY item 1) and `cards_root()`
- the floor: `components/creative-controls/creative_controls.py floor_problems()`

Image-teardown's `tools/*` are internal to that component: these calls are a SEAM (named here so a rename
there moves this file in the same commit).

## Rules

- Fix at the step, never restart a piece. Nothing is deleted: stale pictures go to `pictures-before-<time>/`,
  a replaced card is marked `superseded_by` (the Approve page hides it).
- No brand in code. Python 3.9.6. Tests: `python3 tests/test_stage_check.py` (no network, no model).

## Video maker routes

Explicit registry/run maker route selects video.json (AI production), video-creator.json (creator/founder brief readiness), or video-unresolved.json (missing/conflicting route). Source triage ORGANIC/PAID is not a maker choice. Reports persist checklist, maker_route, route_evidence and completion_scope. Human-route and unresolved-route repair cannot call AI commands. Creator brief checks require Film/Say/Hear/Wearing/On-screen instructions with no unresolved slots. This does not validate completed filming or grant approval. Tests: tests/test_video_routes.py and tests/test_stage_check.py.
