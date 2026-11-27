# Playbook · Micro drama (dialogue) (`micro-drama`)

**Status:** draft · **state:** built 2026-11-27 from the path the first clean micro drama took; no film has run it end to end yet
**Family:** micro-drama

a live-action story ad whose characters act and talk on screen in their own voices: a conflict, a turn on the product, a visible ending; made through Higgsfield Drama Ads

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

> How every AI clip moves: `../../../motion/` (the only route, 2026-11-12). Before any paid take, the clip's movement goes through the motion chain: real footage of the same action found, tracked, read as body mechanics, rehearsed in 3D by the real skeletons with the real camera, then passed or held by the chain's own checks (nobody approves it); the finished take is then checked against the reference beat by beat. No format skips it.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | 2 |
| address | each-other |
| settings | the shared chain's own |
| product_role | turn |
| pacing | fast |
| capture | live-action |
| story | narrative |

## What is specialised, and why

- **workflow** — one fixed path, station by station, with a mechanical check after each paid step: the path the first clean part 1 took. Part 2 drifted at every step it left that path.
- **series** — not a station: a series is planned ahead of time, then each part runs this same workflow; a part that follows a made part takes its story from what that part shows on screen and keeps its matrix row (formats/recipes/drama-series-v1.md, machine/drama_series.py)
- **clip_models** — the clip model is one setting on the lane; both models are priced on every quote and the owner picks at his go; either runs the identical stations and checks
- **start** — a swipe gives the beats; with no swipe, a live-action drama story preset gives them (drama_start.py preset, then the writing chain's scratch.py), so swipes and our own films run the same workflow
- **autonomy** — the run makes every call itself through the decision layer (video-teardown decide.py) and files it for the owner to agree with or overrule; the only stop is the quote
- **camera** — every story shot moves and every beat shows a reaction (formats/recipes/drama-camera-v1.md)

## Stage order

start (swipe or own) → teardown or scratch records → writing → brief review → pack → price and go → sheets → script and plan → setups page → clips → takes → edit → approval page

## Stage settings

**audio**
- first: voice
- note: the characters' own voices are made in the clips (native sound); no separate voice-over

**clips**
- model: the shared chain's own
- resolution: 480p
- aspect_ratio: 9:16
- camera: components/video-production/formats/recipes/drama-camera-v1.md

**edit**
- method: HyperFrames in Claude's browser pane, Gemini pacing read, opening variations, the full teaser kept

## Known failures → fixes

- **part 2 written against part 1 scenes that were never made (the product never appears in the part 1 that was made)** → series planned ahead; a following part is written from previous-part-on-screen.md, the read of the made part's cut (drama-series-v1); drama_series.py check holds it  _(from runs/video-teardown/_work/Brand A-forehead-dgc7zyy-part2; stage series)_
- **the part 2 fork picked a new creative matrix row (another look, setting and product moment)** → pin the series' row before writing (run.py --fork-only, creative_matrix.py cell); drama_series.py written holds a run on another row  _(from runs/video-teardown/_work/Brand A-forehead-dgc7zyy-part2; stage writing)_
- **a script hand-patched outside the writing chain** → the brief station takes only the writing chain's accepted brief (brief_check)  _(from runs/video-teardown/_work/Brand A-forehead-dgc7zyy-part2; stage writing)_
- **clips made with product-only shots, phone-call coverage and hand-sent requests; the product sheet, prompt checks and setups page skipped** → sheets, script-plan, setups and clips stations, each followed by drama_lane.py check; every request checked against the lane before it goes  _(from runs/higgsfield/Brand A/drama-ads-Brand A-forehead-dgc7zyy-part2; stage clips)_
- **locked-off frames, slow pushes and small acting** → the drama camera recipe on every clip prompt; the setups check refuses a still camera without static_ok  _(from runs/higgsfield/Brand A/drama-ads-Brand A-forehead-dgc7zyy-part1; stage clips)_

## Cost

- target per ad: $None
- credits: priced per film by get_drama_ads_config before the go; never a remembered rate

## Quality bar — not slop

- every line of the approved brief is said, word for word, by the right character
- the product is in the shot from its own approved casting sheet wherever the script uses it
- every story shot moves; every beat shows a reaction
- a part of a series picks up from what the part before it actually showed

## The workflow — start it by name

The dialogue micro-drama line, for any micro drama, run autonomously: swipe, writing chain (holds decided by the decision layer), Studio pack, the quote, Higgsfield Drama Ads with a check after every paid step, the edit, the approval page. The only stop is the quote: the owner's go on the price opens the lane.

`python3 machine/workflow.py status micro-drama --label <label> --brand <brand>` says where a run is and what runs next.


| # | Station | Component | Does | Signs off |
|---|---|---|---|---|
| 1 | Start: a swipe, or our own | swipe-intake · video-teardown · video-writing scratch.py · video-production drama_start.py | Two starts, one workflow; the beats come from the start. WITH A SWIPE (source=swipe): the swipe is saved and indexed (swipe-intake: add.py, then intake) and torn down through stage 2 (video-teardown run.py); its beats are the swipe's, held by the structure lock. Reuse a swipe and teardown already on file; never tear one down twice. source_record = runs/intake/{brand}/<intake>/run.json. WITHOUT A SWIPE (source=own): python3 components/video-production/machine/drama_start.py preset --brand {brand} --avatar <avatar> picks the live-action drama story preset (rotating away from ones this person already had); then python3 components/video-writing/machine/scratch.py <label> --brand {brand} --product <product> --avatar <avatar> --preset <that id> (no --write); its beats are the preset's. teardown = <label>; source_record = runs/video-teardown/_work/<label>/vars/story-preset.md. Return source, teardown and source_record. | — |
| 2 | Writing chain brief | video-writing | The writing chain writes the brief; nothing is hand-patched, with the decision layer on: python3 components/video-writing/machine/run.py {teardown} --autonomous (or --piece <label> for a new piece from the same swipe). The same command writes a no-swipe film: its scratch run already carries its story preset, whose beats every pass fills. Every structure, hook, audit, swipe-match and manifest hold is decided from the owner's past calls and filed in runs/decisions/calls.jsonl; the run continues. When the film is one part of a series planned ahead, its story and creative matrix row come from that plan (formats/recipes/drama-series-v1.md): run.py {teardown} --piece <label> --fork-only, creative_matrix.py cell to pin the row, then run.py <label> --story <story.md>. A run that still stops is diagnosed and fixed here, never sent to the owner; a stale brief goes back to writing, never around it. The finished brief is filed on the board for him to read; it does not stop the run. | — |
| 3 | Studio pack | video-studio higgsfield/hf_route.py | The Studio packer turns the accepted brief into the Higgsfield request (pack.json, REQUEST.md): the route, what is on file, what to make once, what is missing. NOT READY stops here. | — |
| 4 | Price, then the owner's go | Higgsfield get_drama_ads_config · video-studio higgsfield/drama_lane.py | THE ONE STOP. Price the film on both clip models (drama_lane.py models) with get_drama_ads_config, called right before the numbers are shown: Seedance 2.5 480p with purpose film, Wan 3.0 480p with purpose stage on its own model id, under the same drama_ads_id. Show the owner both totals, Seedance first. His go names the model (Seedance when he does not say). Write quote.json for that model in the film folder: {drama_ads_id, clip_model, resolution, total_credits, quote_refs, other_quote}. Only his own go opens the lane: drama_lane.py open <film> --quote quote.json --model <his pick> --approved-by <name> --said "<his words>" --cap <credits>. Never open it on his behalf without that go. Read the account's credit balance (balance) right before the quote and show it beside both totals, with what is left after the chosen one; a balance below the total is said first. | the owner: the quote (his only stop) |
| 5 | Lane check | video-studio higgsfield/drama_lane.py | Holds every paid step until the lane is open on the owner's go: drama_ads_id, his name and words, a cap at or over the quote, one clip model the format allows, the quote on that same model. | — |
| 6 | Cast, place and product sheets | Higgsfield Drama Ads | In the Higgsfield sandbox, make each person, place and prop sheet once (steps 2-3 of the Drama Ads skill), every job with the lane's drama_ads_id. The product is never generated: it is the approved casting sheet the pack names. Write film/sheets.json: {sheets: [{kind: person|place|prop|product, name, job_id | source}]}; the product row's source is the pack's casting sheet path. | — |
| 7 | Sheets check | video-studio higgsfield/drama_lane.py | Holds the clips until every sheet is made once and the product is the pack's approved casting sheet, never generated. | — |
| 8 | Script, plan and clip prompts | Higgsfield Drama Ads | Put the approved brief into the Drama Ads script.json with every line kept word for word, write plan.json and every clip prompt with the moving-camera recipe applied, and run checks.py script, plan and clip in the sandbox until each prints PASS. Copy them back: film/script.json, film/plan.json, film/prompts/clip-<id>.txt, and film/checks.json {script: PASS, plan: PASS, clips: {<id>: PASS}}. A clip made as an extension must be a model the lane allows to extend. | — |
| 9 | Every clip's setup on the page | media-production scene input review · owner-pages | Before any clip is sent, publish every clip's exact setup on the film's page (playbook media-production, Scene input review): the ordered references with role and preview, the full prompt, the model, resolution, aspect, duration and its quote. Write film/setups.json {page, setups: [{clip, model (the lane's vendor id), resolution, aspect_ratio, duration, refs: [{role, value, file}], prompt_file, prompt_sha256, camera, quote_credits}]} and film/setups.html (or page: the published link). Showing the setup adds no new approval. | — |
| 10 | Prompt and setup check | video-studio higgsfield/drama_lane.py | Holds the clips until checks.py printed PASS for the script, the plan and every clip, every clip's setup is published, on the lane's model and settings, within that model's reference limits, with a moving camera. | — |
| 11 | Clips through the batch tools | Higgsfield Drama Ads | Send each clip exactly as its published setup, through generate_video_batch with the lane's drama_ads_id (the clip guard lets only an open lane through, and only on the lane's model). Run drama_lane.py request <film> <request.json> on every request before it goes. The first call of the model goes alone and is checked. Freeze each take in jobs.json {clips: [{clip, take, request: {params}, job_id, result_url}]}. Stop at the lane's cap. A wrong clip is fixed with clip_tools.py, not made again. | — |
| 12 | Each take looked at | Higgsfield Drama Ads · video-production | Download every take and look at it and listen to it: the camera movement, the acting and reactions, identity, the dialogue as heard, continuity with the clips around it. A take that fails is fixed (clip_tools.py) or remade inside the lane's cap, never sent to the owner. A finding the run keeps is filed through the decision layer: drama_lane.py decide <film> <clip> <look> "<finding>". Write film/takes.json {takes: [{clip, job_id, accepted, looked: {camera, acting, identity, dialogue, continuity}}]}; each is pass, or {decided: <the call id>}. A checks.py PASS is not acceptance. | — |
| 13 | Takes check | video-studio higgsfield/drama_lane.py | Holds the edit until every frozen request matches its published setup and the lane, and every clip has an accepted take that was looked at for camera, acting, identity, dialogue and continuity. | — |
| 14 | The edit | video-edit · HyperFrames in Claude's browser pane | Cut the accepted takes with their native sound in HyperFrames, opened in Claude's browser pane: pacing checked with the Gemini read, the opening variations made, and the full teaser kept as its own version. Finished versions go to deliverable/ in the film folder, with deliverable/edit.json naming each version, its takes and its checks. | — |
| 15 | Filed to the approval page | meta-upload | File the finished versions as one flexible ad into the approval folder (meta-upload, 1-check). Write deliverable/meta-filed.json with the card's folder and the files it carries. The run ends here; going live is the owner's click on the approval page, outside the run. | — |

## Rulings behind it

- {'ruled': '2026-11-27', 'rule': 'every micro drama goes through the same process every time'}
- {'ruled': '2026-11-27', 'rule': 'the process is autonomous; the only thing the owner sees is the quote'}
- {'ruled': '2026-11-27', 'rule': 'Wan is an option chosen when the prices are shown, not a test'}
- {'ruled': '2026-11-27', 'rule': "mostly swipes go in, and we can also build our own with no swipe: the swipe's beats, or a drama preset's"}
