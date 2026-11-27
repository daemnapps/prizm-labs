# The logic layer in production (2026-11-18)

The video line had its stages; the thinking that connects them was thin. A walk of the line found decisions that were
silent, two rules that disagreed, and reasons written at one stage and read by no stage after it. This page lists what
production now decides by rule, where the rule lives, and what it writes so the next stage reads the reason.
Nothing here is a new gate: every item decides, records why, and moves on.

## What production decides, and where

| Decision | The rule | Where | What it writes |
|---|---|---|---|
| How the whole ad is made (AI, AI + Real, Real, a creator) | The maker route, then a format made one way by its own definition, then whether the style is filmed footage, then the footage decision. A person's pick at Produce always wins. A production saved with no lane gets one answer for every reader. | `machine/lane.py`, settings `machine/lanes.json` | `lane`, `lane_why`, `lane_by` on the production; one trail row |
| Each scene: our footage, the swipe's shot, or generated | ONE rule, `shot_route.route()`: footage we own first, on the footage match as its evidence; then the swipe's own shot when the motion is the point; else generated. | `machine/shot_route.py`, facts from `machine/route_facts.py` | `route`, `route_why`, `route_by` on each scene; `ROUTES.md`; one trail row |
| What the footage match was judged on | The score against the bar, the action, the named product, the text marks. No clip with words burned in; never one clip section on two scenes. Both asked BEFORE the decision, so a scene they rule out is generated in the same pass. | `machine/footage.py` (`evidence_of`, `why_of`, `usable`) | `owned_evidence`, `footage_why` on each scene |
| A scene given to our footage becomes a file | Cut `owned_in` → `owned_out` into `media/<scene>.mp4`, picture only, read through gdrive-creator; verdict rows that say it is our own footage. | `machine/owned_clips.py`, called by `run.py start` after the footage step | `media/<scene>.mp4`, `owned_media` on the scene, `motion` and `director` rows in `verdicts.json` |
| Who plays a new person | The casting door is asked first, in the brief's own words. A role the bank covers with a person whose sheet is ready is bound; otherwise the door's answer is kept and the step carries on as before. | `machine/auto_elements.py` (`ask_casting`, `cast_from`) calling `components/casting` `bank.who_plays` | one trail row per new person |
| How many takes, which take is kept | ONE block: `providers.json` `direct.clip_route.attempts`. A press on the board: one take. The automatic run: another only when one fails, three at most. Best score kept; none passing = the best attempt kept, flagged. | `machine/takes.py` (the only reader) | the counts every reader asks for; the budget's priced tries |

## One budget, one run

`budget.py` prices the routes through `route_facts.preview`, the same door the run uses, worked on a copy. A run that
has routed is priced on its own routes; before that the budget previews by the same rule and says so on the page.

## The trail

`machine/trail_door.py` writes production's rows onto the run's decision trail (run-kit `trail`, kept as `trail` on the
run's own `run.json`). A row is a note: one that cannot be written is said once and the run carries on.

## Public names (for other components)

`lane.py` (`default`, `for_writing`, `of`, `chosen`, `label`, `lanes`) · `owned_clips.py` (`place`, `readable`, `cut`) ·
`takes.py` (`counts`, `expected`, `pick`, `best_attempt`, `keep`, `said`) · `route_facts.py` (`route_plan`, `preview`,
`summary`, `by_rule`) · `trail_door.py` (`note`, `rows`, `block`).

## Held for review (written, not live)

`machine/held.json` lists each with its before and after; `machine/held.py` `on(id)` is false for all of them.

| Item | Code | Off means |
|---|---|---|
| Openings from the body | `hook_variations.py` `body_openings`, `from-body <run>` | proposals print; `--apply` is refused |
| Cast by audience | `auto_elements.py` `audience_cast`, `lead_of` | `run()` never calls them |
| Lessons into prompts | reader `components/video-edit/machine/learn.py` `block(stage)` | no prompt carries the slot |

## Tests

`machine/test_owned_clips.py` · `test_takes.py` · `test_lane.py` · `test_casting_door.py` · `test_held.py`
(`/usr/bin/python3 -m unittest <name>` from `machine/`; no network, no spend).
