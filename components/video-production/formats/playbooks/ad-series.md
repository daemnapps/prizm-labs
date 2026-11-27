# Playbook · Ad series (`ad-series`)

**Status:** draft · **state:** parked 2026-11-27: three or more ads told as one story; not proven end to end, so out of the owner's view (the live lines are micro-drama and song-ad). Was: new; dry runs only (no production run)
**Family:** ad-series

three or more ads that run as one story: each ad is a full ad in its own format, and a ledger carries the card, the product, the cast and the open promises from one ad to the next

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
| product_role | hero |
| pacing | the shared chain's own |
| capture | the shared chain's own |
| story | series |

## What is specialised, and why

- **workflow** — a series layer: arc card and ledger before any ad is written; each ad then runs its own format's workflow

## Stage order

teardown → writing → series → elements → gates → voice → storyboard → pictures → clips → edit

## Stage settings

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $None

## Quality bar — not slop

- the ledger passes series_check.py with no L-check failing
- each ad stands alone: hook, proof, ask
- the recurring object is the same real item in every ad

## The workflow — start it by name

The ad-series line. No person stop: the arc card and ledger are decided by the decision layer and filed for the owner to overrule; then each ad runs its own format's workflow, whose one stop is its quote.

`python3 machine/workflow.py status ad-series --label <label> --brand <brand>` says where a run is and what runs next.


| # | Station | Component | Does | Signs off |
|---|---|---|---|---|
| 1 | Arc card and ledger | video-production formats/ad-series | Follow components/video-production/formats/ad-series/FORMAT.md, steps Arc and Ledger. Write arc.md and ledger.json in the workflow folder, then run python3 components/video-production/formats/ad-series/series_check.py on ledger.json. Also write runs/video-production/{brand}/workflow-{label}/arc-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 2 | Arc card and ledger review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 3 | File what the series taught | video-production formats/ad-series | Follow FORMAT.md, step Learn: each lesson into learned.md in the workflow folder with its one home from the routing table in LEARNINGS.md; filed through the decision layer; nothing changes in a home in the run, only after the owner agrees with the filed call. | — |
