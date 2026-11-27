---
name: stage-handoff
description: Hand one component of the video chain (video teardown → video writing → video production → video edit) to whoever holds the next role, and pull in what is waiting for your role. Use when someone says "hand brief <number> to video production", "hand this teardown to writing", "hand brief <number> to the video producer", "send this brief to a creator for storyboarding", "what's waiting for me", "what's waiting for the video producer", "open brief <number> as video producer", "is the <number> hand-off ready", "who holds which role", or takes over a role and wants to pick up the chain from there.
---

> **Activates component:** `components/video-edit/handoff/` (`pack.py`, `check.py`, `pull.py`; folded out of `components/stage-handoff/` 2026-11-19, which now holds only the data: `chains/*.json`, `roles.json`). The rule: `components/video-edit/handoff/SPEC.md`.

The chain is four components; each is a stage held by a ROLE (`roles.json`), never a person. A hand-off is one folder
at `runs/handoffs/<role>/<brand>/<brief key or run label>/`, the same path on the Drive. Do every step yourself;
report the outcome in one line.

## "Hand this teardown to writing"

`/usr/bin/python3 components/video-edit/handoff/pack.py video-writing <teardown label>`, then
`check.py <label> --role creative-strategist`. It refuses a teardown without stages 1 and 2, or one already written.

## "Hand brief <number> to video production" / "to the video producer"

`/usr/bin/python3 components/video-edit/handoff/pack.py video-production <number>` with `VIDEO_STUDIO_DATA` set when the Video
Studio's data is on this machine (so the pack says which Studio production it already has). Then
`check.py <number> --role video-producer`. Report the folder and any failed check, nothing else. It refuses a brief
whose writing was not accepted, or a non-AI route: say so in one line.

## "What's waiting for me" / "for the <role>"

`/usr/bin/python3 components/video-edit/handoff/pull.py waiting --person <name>` (or `--role <role>`). Show the open ones:
number, brand, title.

## "Open brief <number> as <role>"

`pull.py open <number> --role <role>`. It brings the folder down from the Drive when it is not here and prints
START.md and the activation line. Then DO what the activation line says: it is the chain switched on from this stage
(for the video producer: read BRIEF.md, set it up in the Video Studio, storyboard, motion, clips, Send to maker).
The video-editor role opens through the `video-briefs` skill instead.

## Never

- Name a person in a stage or a chain file: holders live only in `roles.json`.
- Delete or move anything on the Drive.
- Ask the owner inside a stage; only spend past a cap, going live, sending and signing are theirs.
