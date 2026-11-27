# Playbook · General chain (no playbook) (`default`)

**Status:** approved · **state:** the shared chain as it runs today
**Family:** default

**Signed:** the owner 2026-10-10 — the general chain stays the fallback for any format without its own playbook: "as opposed to just having a general workflow for all ads"

Every setting here is the shared chain's own (THE-CHAIN.md, providers.json, RUN-PROTOCOL.md). null = the shared chain decides; a family playbook overrides only what it names.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

> How every AI clip moves: `../../../motion/` (the only route, 2026-11-12). Before any paid take, the clip's movement goes through the motion chain: real footage of the same action found, tracked, read as body mechanics, rehearsed in 3D by the real skeletons with the real camera, then passed or held by the chain's own checks (nobody approves it); the finished take is then checked against the reference beat by beat. No format skips it.

## Structural signature

| | |
|---|---|
| audio | the shared chain's own |
| speakers | the shared chain's own |
| address | the shared chain's own |
| settings | the shared chain's own |
| product_role | the shared chain's own |
| pacing | the shared chain's own |
| capture | the shared chain's own |
| story | the shared chain's own |

## Stage order

teardown → writing → elements → gates → voice → storyboard → pictures → clips → edit

## Stage settings

**audio**
- first: voice
- song_model: the shared chain's own
- voice_model: the shared chain's own

**song**
- flow: the shared chain's own
- length_s: the shared chain's own

**pictures**
- door: direct.openai
- model_key: the shared chain's own
- quality: the shared chain's own
- size: the shared chain's own
- aspect: 9:16
- fix_calls: on
- style_lock: the swipe's style row
- send_size: the shared chain's own

**clips**
- model: seedance_2_5
- resolution: 720p
- seconds: 4, 10
- clips_per_picture: 1
- takes: 1
- max_tries: 3
- upscale: local, the picked take only
- stills_allowed: off
- short_clip: the shared chain's own

**cast**
- reuse: per-brand cast bank first
- recurring: off

**hooks**
- shape: hooks as format fills (writing station 2.2)

**captions**
- look: the swipe's own caption look (style.caption)

**gates**
- apply: all 13 (run.py start)
- skip: 

**edit**
- method: video-edit machine cut, or the editor hand-off
- loudness: -14 LUFS

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $None

## Quality bar — not slop

- the shared QC gate: inspector + director verdicts on every clip

## The workflow — start it by name

Draft reviewed production intake; generation is outside this fallback recipe.

`python3 machine/workflow.py status default --label <label> --brand <brand>` says where a run is and what runs next.


| # | Station | Component | Does | Signs off |
|---|---|---|---|---|
| 1 | Accepted writing brief | video-writing | The writing chain runs with the decision layer on: python3 components/video-writing/machine/run.py {teardown} --autonomous (the teardown or scratch run's label). Every structure, hook, audit, swipe-match and manifest hold is decided from the owner's past calls and filed for him to overrule; the run continues. A run that still stops is diagnosed and fixed in the session, never sent to the owner. Retain the actual writing run and maker brief; a held or stale brief is not complete and goes back to writing, never around it. Writing costs are never quoted. | — |
| 2 | Brief review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 3 | Prepare production plan | video-production · model-inputs | Read the resolved existing family and style, then author the scene/asset/cast plan, exact component steps, missing inputs, estimate and stopping point. This draft fallback is reviewed planning coverage, not a proven end-to-end production recipe. Do not generate. | — |
| 4 | Production plan review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
