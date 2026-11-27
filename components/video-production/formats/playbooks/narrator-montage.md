# Playbook · Narrator montage (`narrator-montage`)

**Status:** draft · **state:** parked 2026-11-27: one narrator's voiceover over a fast run of shots; not proven end to end, so out of the owner's view (the live lines are micro-drama and song-ad). Was: new; no ad has been carried end to end on it yet
**Family:** narrator-montage

a hook, then one narrator's voiceover over a fast run of short shots (the product, people using it, the proof), then the offer and the ask; the hook is a slot any hook fills

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

> How every AI clip moves: `../../../motion/` (the only route, 2026-11-12). Before any paid take, the clip's movement goes through the motion chain: real footage of the same action found, tracked, read as body mechanics, rehearsed in 3D by the real skeletons with the real camera, then passed or held by the chain's own checks (nobody approves it); the finished take is then checked against the reference beat by beat. No format skips it.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | one |
| address | voiceover |
| settings | the shared chain's own |
| product_role | hero |
| pacing | fast |
| capture | the shared chain's own |
| story | the shared chain's own |

## What is specialised, and why

- **workflow** — the narrator-montage line: hook slot, one continuous narrator read, short silent shots, the proof, the offer and the ask

## Stage order

teardown → writing → elements → gates → voice → storyboard → pictures → clips → edit

## Stage settings

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $None

## Quality bar — not slop

- one narrator voice, one continuous read, start to finish of the body
- every body shot is silent: nobody's lips move unless the hook is on screen
- the proof shot is a real customer's before and after, unaltered
- the shared QC gate: inspector + director verdicts on every clip

## The workflow — start it by name

The narrator-montage line. The one person stop is the quote, after the plan and before any money moves; every review is decided by the decision layer and filed for the owner to overrule. Going live stays his click on the approval page.

`python3 machine/workflow.py status narrator-montage --label <label> --brand <brand>` says where a run is and what runs next.


| # | Station | Component | Does | Signs off |
|---|---|---|---|---|
| 1 | Accepted writing brief | video-writing | The writing chain runs with the decision layer on: python3 components/video-writing/machine/run.py {teardown} --autonomous (the teardown or scratch run's label). Every structure, hook, audit, swipe-match and manifest hold is decided from the owner's past calls and filed for him to overrule; the run continues. A run that still stops is diagnosed and fixed in the session, never sent to the owner. Retain the actual writing run and maker brief; a held or stale brief is not complete and goes back to writing, never around it. Writing costs are never quoted. | — |
| 2 | Brief review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 3 | Plan and total | video-production storyboard_plan.py · budget.py | Follow components/video-production/formats/narrator-montage/FORMAT.md, step Plan. Name the hook from the brief's openings, pick each scene's route (owned footage or generated), and write plan.md in the workflow folder with every scene's route, seconds and cost and the total from BUDGET.md. Nothing is spent here. Also write runs/video-production/{brand}/workflow-{label}/plan-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 4 | Plan and total review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 5 | The quote, then the owner's go | video-production · generative-model-house | THE ONE STOP. Before any money moves, price every paid step from here to the cut on the house models (components/generative-model-house/MODEL-HOUSE.md): the elements still to make, the narrator read, every start picture, the two proof clips and every remaining generated section with its retake allowance (plan.md has each scene's route and cost), each as count x unit price, with the total and the stop point. Write runs/video-production/{brand}/workflow-{label}/quote.json as {"total_usd": <number>, "lines": [{"what", "count", "unit_usd", "usd"}], "stop_point": "..."} and show the owner the total and what it buys. Only his own go in chat opens the spend: record it with workflow.py go <format> --brand {brand} --label {label} --approved-by <name> --said "<his words>" --cap <dollars>, then complete this station. Writing costs are never quoted (owner, 2026-11-25). Never record a go he did not give. Spend past the cap is a new quote, never a quiet overrun. | the owner: the quote (his only stop) |
| 6 | Elements check | video-production elements_check.py · casting | Follow FORMAT.md, step Elements. List every person, voice, place and product the generated scenes need, match each to the bank, make only the gaps. Also write runs/video-production/{brand}/workflow-{label}/elements-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 7 | Elements review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 8 | Narrator read and storyboard | video-production | Use the approved brief, plan and elements. Inside the owner's go (go.json and its cap), run run_v2.py start {brief} --brand {brand} --label {production_label} --voice-only --go runs/video-production/{brand}/workflow-{label}/go.json, then run_v2.py storyboard runs/video-production/{brand}/{production_label} --brief {brief} --go runs/video-production/{brand}/workflow-{label}/go.json. Both commands are under components/video-production/machine/. One continuous narrator read. Reuse verified outputs. Stop before pictures. | — |
| 9 | Start pictures | the board | Follow FORMAT.md, step Pictures: one start picture per generated section, nothing for owned-footage scenes, an end picture only where the shot changes. Also write runs/video-production/{brand}/workflow-{label}/pictures-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 10 | Start pictures review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 11 | Two proof clips | the board | Follow FORMAT.md, step Proof clips: the first body shot after the hook and the hardest shot, one take each, with the total and stop point stated first; nothing else runs until the decision layer passes the look. Also write runs/video-production/{brand}/workflow-{label}/proof-clips-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 12 | Two proof clips review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 13 | All clips | the board | The remaining generated sections through the board, three takes at most per shot; each failure gets one named reason and one change. The producer records the go-ahead total in clips-done.md in the workflow folder. | — |
| 14 | First-take score | video-production first_take.py | Counts shots right on take one and why the rest failed; the board shows this file | — |
| 15 | File what the run taught | video-production formats/narrator-montage | Follow FORMAT.md, step Learn: write each thing the run taught into learned.md in the workflow folder, each with its one home from the routing table in components/video-production/formats/narrator-montage/LEARNINGS.md; filed through the decision layer; nothing is changed in a home in the run, only after the owner agrees with the filed call. Also write runs/video-production/{brand}/workflow-{label}/learn-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 16 | What the run taught, review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 17 | Edit and hand-off | video-edit · image-edit/handoff.py | Prepare the local cut and handoff instructions; sending or publishing is a separate authorized action. Also write runs/video-production/{brand}/workflow-{label}/edit-handoff-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 18 | Edit and hand-off review | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
| 19 | Launch package | ad-review · naming · meta-upload | Prepare the named final cut, captions and destination, then file them on the Meta approval page (meta-upload skill: Shared Assets/meta/{brand}/1-check/). Going live is the owner's click on that page, outside this run; nothing is published here. Also write runs/video-production/{brand}/workflow-{label}/launch-review.json as {"files": {"repo-relative-output-path": "sha256"}}, covering exactly the listed output files. The decision layer reviews it; nothing waits for the owner. | — |
| 20 | Launch package check | decision layer · video-teardown decide.py | The decision layer (video-teardown decide.py) passes this exact version from the owner's past calls and files the call in runs/decisions/calls.jsonl for him to agree with or overrule later; the run continues and nothing waits for him. An overruled version goes back to its authoring station. | decision layer (the owner can overrule) |
