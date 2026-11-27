# Playbook · Talking ad (`single-presenter`)

**Status:** draft · **state:** parked 2026-11-27: one person to camera; not proven end to end, so out of the owner's view (the live lines are micro-drama and song-ad). Was: new; no ad has run on it yet
**Family:** single-presenter

One person to camera in long takes, built from the talking recipe.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

> How every AI clip moves: `../../../motion/` (the only route, 2026-11-12). Before any paid take, the clip's movement goes through the motion chain: real footage of the same action found, tracked, read as body mechanics, rehearsed in 3D by the real skeletons with the real camera, then passed or held by the chain's own checks (nobody approves it); the finished take is then checked against the reference beat by beat. No format skips it.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | one |
| address | camera |
| settings | the shared chain's own |
| product_role | the shared chain's own |
| pacing | the shared chain's own |
| capture | the shared chain's own |
| story | the shared chain's own |

## What is specialised, and why

- **workflow** — The talking recipe and its role stations.

## Stage order

teardown → writing → elements → gates → voice → storyboard → pictures → clips → edit

## Stage settings

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $None

## Quality bar — not slop

- the shared QC gate: inspector + director verdicts on every clip

## The workflow — start it by name

The talking ad line, with the three roles at their stations. The one person stop is the quote, before any money moves; every review is decided by the decision layer and filed for the owner to overrule. Going live stays his click on the approval page.

`python3 machine/workflow.py status single-presenter --label <label> --brand <brand>` says where a run is and what runs next.


| # | Station | Component | Does | Signs off |
|---|---|---|---|---|
| 1 | Ad Plan | video-teardown · video-writing · marketing-doctrine | The strategist writes one Ad Plan page from the swipe or idea, in the workflow folder as ad-plan.md Also write runs/video-production/{brand}/workflow-{label}/ad-plan-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 2 | Ad Plan review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 3 | Accepted writing brief | video-writing | The writing chain runs with the decision layer on: python3 components/video-writing/machine/run.py {teardown} --autonomous (the teardown or scratch run's label). Every structure, hook, audit, swipe-match and manifest hold is decided from the owner's past calls and filed for him to overrule; the run continues. A run that still stops is diagnosed and fixed in the session, never sent to the owner. Retain the actual writing run and maker brief; a held or stale brief is not complete and goes back to writing, never around it. Writing costs are never quoted. | — |
| 4 | Brief review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 5 | Shot plan | director layer · model-inputs | The director writes the shot plan, look, locks and takes into shot-plan.md in the workflow folder, following the talking recipe, before any money moves | — |
| 6 | The quote, then the owner's go | video-production · generative-model-house | THE ONE STOP. Before any money moves, price every paid step from here to the cut on the house models (components/generative-model-house/MODEL-HOUSE.md): voice, every start picture and B-roll picture, the two proof clips and every remaining clip with its retake allowance, each as count x unit price, with the total and the stop point. Write runs/video-production/{brand}/workflow-{label}/quote.json as {"total_usd": <number>, "lines": [{"what", "count", "unit_usd", "usd"}], "stop_point": "..."} and show the owner the total and what it buys. Only his own go in chat opens the spend: record it with workflow.py go <format> --brand {brand} --label {label} --approved-by <name> --said "<his words>" --cap <dollars>, then complete this station. Writing costs are never quoted (owner, 2026-11-25). Never record a go he did not give. Spend past the cap is a new quote, never a quiet overrun. | the owner: the quote (his only stop) |
| 7 | Voice and storyboard | video-production | Use the approved brief and authored shot plan. Inside the owner's go (go.json and its cap), run run_v2.py start {brief} --brand {brand} --label {production_label} --voice-only --go runs/video-production/{brand}/workflow-{label}/go.json, then run_v2.py storyboard runs/video-production/{brand}/{production_label} --brief {brief} --go runs/video-production/{brand}/workflow-{label}/go.json. Both commands are under components/video-production/machine/. Reuse verified outputs. Stop before pictures: start without flags and start --storyboard create pictures and do not belong here. Never bypass writing acceptance or picture approvals. | — |
| 8 | Element breakdown | video-production scene_breakdown.py · shot_swaps.py | Every swipe scene read to its elements, and each element marked keep or swap for ours | — |
| 9 | 3D shot set | video-production shot_sets.py · Higgsfield 3D Jutsu | One 3D set per place and camera, with the stand-in and light locked, printed and linked to every shot | — |
| 10 | Start picture | the board | One start picture, signed off by the system's reviewer under the go (run_v2.py --go; a flagged picture is held and remade, never shipped), for the talking takes, then only the B-roll and demos the script needs, all from the shot set through image production on the board Also write runs/video-production/{brand}/workflow-{label}/pictures-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 11 | Start picture review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 12 | Two proof clips | the board | The hook and the hardest shot, one take each, with the total and stop point stated first; nothing else runs until the decision layer passes the look Also write runs/video-production/{brand}/workflow-{label}/proof-clips-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 13 | Two proof clips review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 14 | All clips | the board | The remaining clips through the board, three takes at most per shot; each failure gets one named reason and one change. The producer records the go-ahead total in clips-done.md in the workflow folder | — |
| 15 | First-take score | video-production first_take.py | Counts shots right on take one and why the rest failed; the board shows this file | — |
| 16 | Teach the recipe | video-production formats/recipes | Any failure reason seen twice is proposed as one recipe rule in learned.md in the workflow folder and filed through the decision layer; no recipe changes in the run: a new recipe version is written only after the owner agrees with the filed call Also write runs/video-production/{brand}/workflow-{label}/learn-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 17 | Teach the recipe review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 18 | Edit and hand-off | video-edit · image-edit/handoff.py | Prepare the local cut and handoff instructions; sending or publishing is a separate authorized action. Also write runs/video-production/{brand}/workflow-{label}/edit-handoff-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 19 | Edit and hand-off review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 20 | Launch package | ad-review · naming · meta-upload | Prepare the named final cut, captions and destination, then file them on the Meta approval page (meta-upload skill: Shared Assets/meta/{brand}/1-check/). Going live is the owner's click on that page, outside this run; nothing is published here. Also write runs/video-production/{brand}/workflow-{label}/launch-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 21 | Launch package check | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |

## Built from

- runs/video-production/Brand A/Brand A_flex-face-brush_brief-0299
- runs/video-production/Brand B/yai-cheek-45-70
