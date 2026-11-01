# Playbook · Remedy (`remedy`)

**Status:** draft · **state:** proven-once
**Family:** remedy

A presenter at a counter shows a remedy from tradition step by step, then the product as today's version; one gross hook, every step shown, the payoff close.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | 1 |
| address | to-camera |
| settings | 1 |
| product_role | payoff |
| pacing | measured |
| capture | phone |
| story | teach |

## What is specialised, and why

- **video spice at level 3 in the brief** — the owner 2026-10-20: realism is emotional connection; mechanical cuts and faces read as AI (tools/video-production/VIDEO-SPICE.md)
- **one step per line; the clip prompt carries the shot's action the whole time** — whisking said but not shown, the lime never squeezed (2026-10-20)
- **prop masters at real size, a reference in every shot** — the nose model changed size across the reel (2026-10-20)
- **picture check before any clip, by the model house judge** — a book open and shut at once (2026-10-20)
- **the voice is a per-line read fitted to the lips, never one take stretched across clips** — the stretched take read mechanical (2026-10-20)

## Stage order

teardown (or the format's own writer for an organic topic) → replication spec → injection (brand, product, avatar words) → writing + spice (video spice level 3, realism index writing entries) → shots (one step per line, angle, camera, hands_off, props) → set (once per presenter) + prop masters (product = the real photo) → pictures (carry-over across the whole piece) + picture check → voice (per line, delivery as a v3 tag) → clips (Seedance 2.5, 480p, action in the prompt, end frame on continuous hand-offs) + clip check → edit (edits-glow captions, pace breathing, room tone, match/whip) → deliver, track, learn

## Stage settings

**audio**
- first: voice
- voice_model: model-house sound.voice
- fit: none — the locked read is the clip's own audio; nothing is fitted afterwards
- per: line
- delivery: the shot's `delivery` as a v3 audio tag
- nobody_talks: off

**pictures**
- door: model-house pictures.edit
- quality: high
- aspect: 9:16
- set: one locked set per presenter; every first frame is an edit of it
- carry: reel — every shot carries over from the shot before, across beats
- props: one master picture per prop at its real size, referenced in every shot it appears in; the product master is the real product photo
- life_marks: the presenter's life marks in every picture
- realism: realism index production entries (skin, place) for the format
- check: picture check (model-house behind.judge): impossible objects, prop size, missing action, malformed hands; one remake with the judge's fix
- fix_calls: on

**clips**
- model: seedance_2_5
- resolution: 720p
- seconds: 4, 10
- clips_per_picture: 1, 1
- takes: 1
- prompt_order: the shot's action ('What happens in this shot, the whole time') → the presenter's face and voice → the hold note → the camera move → the realism index production entries (camera-hand, face)
- end_frame: a `continuous` hand-off ends on the next shot's first picture (end_image_url) so the join disappears
- check: clip check (model-house behind.judge): the shot kept its object, the camera did not jump, nothing new entered; one remake with the strict hold note
- stills_allowed: off
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least

**cast**
- reuse: on
- recurring: on
- product: real photo only, never drawn

**hooks**
- how: 3 concepts per topic built from the levers (literal · huge · texture · action · split), judged 'would you stop on this with the sound off'
- first_frame: the oversized model of the problem at the lens, the remedy already on it

**captions**
- look: edits-glow (tools/video-edit), picked by format
- place: aim at the neck, move off any face or mouth
- timing: exact word timings handed to the editor (model-house sound.words)
- emphasis: the step's action, the ingredient, the payoff word, the comment word — about one word in six

**gates**
- apply: line check, picture check, clip check, lips in time
- skip: 

**edit**
- pace: breathing — cuts between shots only, no splits at breaths, no punch-in jumps
- room_tone: the set's room tone from the SFX bank
- transitions: from the shot plan's hands_off: match and whip drawn; continuous and action are plain cuts

**copy**
- ask: the lane's: organic = comment the word and follow; paid = tap the button. Nothing else changes between lanes (RUN-PROTOCOL.md, one machine)

## Known failures → fixes

- **the camera jumped to her face and dropped the hook prop** → hold note in every clip prompt; the clip check remakes a clip that lost its object  _(from grandma-yai/runs/egg-white-pore-peel; stage clips)_
- **choppy, fragment script; voice restarted every cut** → monologue first, then shots; the script judge scores it against the real reels  _(from grandma-yai/runs/grandma-yai-cracked-heels-banana-paste; stage writing)_
- **mechanical: 16–17 short shots, pause splits and punch-ins, one take stretched onto lips, the same excited face** → 9–13 shots, pace breathing, per-line read fitted to lips, emotion and face per shot  _(from grandma-yai/runs/the-egg-white-peel; stage edit)_
- **a book open and shut at once; malformed hands** → picture check before any clip  _(from grandma-yai/runs/egg-white-pore-peel-v3; stage pictures)_
- **the nose model changed size between shots** → prop masters at real size, referenced in every shot  _(from grandma-yai/runs/egg-white-pore-peel-v3; stage pictures)_
- **whisking and squeezing the lime said but never shown** → one step per line; the clip prompt carries the action  _(from grandma-yai/runs/egg-white-pore-peel-v3; stage writing)_
- **captions over her mouth in wide shots; words up to 0.8 s off her voice** → edits-glow aims at the neck and moves off faces; exact Scribe word timings in the kit  _(from runs/video-edit/<brand>/remedy-egg-white-pore-peel-v2; stage edit)_

## Cost

- target per ad: $8
- cap_usd_per_ad: the shared chain's own
- _cap: 2026-10-21 (P40, VIDEO-RULINGS V5/V17): no dollar cap; cost is never a reason to stop or to take a lesser element.
- measured: about $6–8 a reel on 2026-10-20 (11–17 clips on the old Omni route at 720p, 13–17 GPT Image edits, line reads)
- how: one version of every start picture and one take of every clip, each judged, another only if it fails (three tries at most); an element none of whose three passes is HELD and made again, never shipped (VIDEO-RULINGS V5, 2026-10-21; was: one picture per shot, one remake max per check)

## Quality bar — not slop

- the hook frame stops a thumb with the sound off
- every step said is shown, in order
- one object, one look: props and the product never change
- her face travels with the words; never the same excited face throughout
- no caption ever covers a face or a mouth; words land within 3 frames
- cuts land between shots; nothing feels chopped or mechanical

## Built from

- t
- h
- e
-  
- G
- r
- a
- n
- d
- m
- a
-  
- Y
- a
- i
-  
- r
- e
- e
- l
- s
- ,
-  
- 2
- 0
- 2
- 6
- -
- 1
- 0
- -
- 2
- 0
-  
- (
- D
- a
- m
- o
- n
- '
- s
-  
- s
- a
- n
- d
- b
- o
- x
-  
- r
- e
- e
- l
-  
- l
- i
- n
- e
- ,
-  
- g
- r
- a
- n
- d
- m
- a
- -
- y
- a
- i
- /
- )

## Rulings behind it

- the owner 2026-10-20: organic and paid are the same video; only the ask and how gradual the pitch is differ
- the owner 2026-10-20: don't worry about over claiming, it's content
- the owner 2026-10-20: captions on her neck, never her mouth
