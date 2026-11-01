# The Four Stations — the move plan (step d, 2026-09-30 — MOVED the same day)

Mirror of **The Four Stations** artifact ((team page)), tab *d · Move plan*.
Nothing here has moved. Moves happen only in a quiet window the owner agrees to — `tools/video-teardown/machine/` is edited by several sessions a day.

## What stays true through every move
- **One command.** `machine/run.py <video> --brand <brand> --route <route>` keeps running all of it; the runner finds prompts through its list of prompt homes (`machine/chain.py` `PROMPT_HOMES`), so a moved folder is one line in that list, not a new machine.
- **Old runs untouched.** Every run keeps its own copy of the prompts it ran (`<run>/prompts/`); nothing under `machine/runs/` or `runs/video-teardown/` is moved or rewritten.
- **Never mid-run.** A move waits until no run is going and no other session has the machine open with changes.

## The moves, in order

| # | What | From | To | Proof it worked |
|---|---|---|---|---|
| 1 | Route lock (done 2026-09-30) | — | `machine/run.py` | `machine/test_route_lock.py` |
| 2 | **Done 2026-09-30.** Writing prompt folders — 1b, 2f, 3, 3v, 4-loop (4a–4g), 4m, 5 (creator, ai, hook asset), 5m, 5n, 5u, 7, 7b, 8 | `tools/video-teardown/prompts/` | `tools/copywriter/prompts/video/` (same folder names) | every chain × route resolves; `machine/test_chain_replay.py` replays a real run through every step on both routes |
| 3 | Copywriter runs the same writing prompts, not its own copies of hooks, expansion, close | `tools/copywriter/prompts/stage5-hooks…`, `stage6-expansion…`, `stage7-close…` | retired to `superseded/` once the social-copy route runs side by side | one source written both ways, both pages shown to the owner |
| 4 | Frames (old 6) — **retired** (the owner, 2026-09-30: "no more frames, only the brief and swipe file link") | `tools/video-teardown/prompts/stage-6-frames/` | taken out of the run; the brief carries the swipe file link | a run finishes with the brief and the link, no pictures |
| 5 | Teardown stays | `tools/video-teardown/` (T0–T4 prompts, deep passes, audio teardown call) | — | — |
| 6 | Editing — moved 2026-09-30 by another session | `the team notes/video-edit/` | `tools/video-edit/` | — |

## Before anything depends on the new stations
The team's system path runs on each folder that changes: `/system-fit` → `/system-ready` → `/system-review` — on `tools/copywriter/` before move 2, on `tools/video-production/` before move 4.

## the owner's calls — settled 2026-09-30
Copywriter writes video too (side by side first) · spice stays on creator/founder as her delivery notes · no more frames · the writing process is the same for every route.
