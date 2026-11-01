# Shot routes: the one rule for which way a shot is made

Ruled by the owner, 2026-10-20: "this is the best combination … ensure this is all agnostic … clean up the old and newer ruling so this is the only ruling on how to use the different models." And: "this allows us to inventory and project costs with more accuracy as well and makes editing much more streamlined."

**This file is the only place that decides how a shot is made.** Every other rule in this component, the produce-video skill and the edit line says how a route runs, never when to use it. Where an older line says otherwise ("frames, not scenes" as the default, "never animate stills", "a generated scene is the last resort"), this file wins.

## The three routes, decided in this order for every shot

1. **REAL: real B-roll, whenever we own the footage.** The product in use, product-only shots, before-and-afters, real customers. Cut as it is from the brand's archive. Free, and true. The hero product is never drawn: when the product is on screen it comes from real footage, a real photo pasted in, or the brand's own studio renders.
2. **SWAP: the swipe's own shot, with our cast swapped in (Higgsfield Genjutsu `hf_mult_replace_object`)** when the motion is the point: a stunt, physical comedy, a specific move or gesture, crowd energy, a camera move, anything generation would fake. It needs one clean shot in the swipe, at least about 2 seconds with no cut inside, cut on the exact boundaries the frame map found. Two limits: a swap keeps the original mouth, so it carries no line of ours; and it replaces things, never adds them, so the product only goes where the swipe already has something in hand. Every swap sends the cast member's full sheet (`machine/cast_swap.py`). Every swap is checked against the cast master before it is kept: when the swap kept the original person's face (it does when our cast looks close to the person in the swipe), the same shot goes to motion transfer instead (Genjutsu `hf_mult_motion_control`: the swipe shot drives the movement, the cast master is the person), which builds our cast from the master and copies only the motion. Found 2026-10-20 on the pastor body: 9 of 9 object swaps kept the original face, 9 of 9 motion transfers carried ours.
3. **AI: generated first and last frames, then a clip** for everything else: anyone talking to camera with our voice (it needs real lip-sync), simple setups (standing, sitting, a reaction), and any shot the swipe does not have. Frames on GPT Image from the cast sheets and the swipe's real frames as references; the model is ruled in `components/generative-model-house/MODEL-HOUSE.md`.

A talking line can still play over a REAL or SWAP shot as voice-over; the route is about the picture.

## Every shot is labelled before anything runs

**Wired into the dry run (2026-10-20):** `run.py start … --dry-run` writes `BUDGET.md` through `machine/budget.py`, which routes every scene of the brief by this rule, prices pictures and generated clips for the AI scenes only, adds the swaps, and lists every scene's route, seconds, cost and reason under "Shot routes". A brief scene carries its facts (`owned_footage`, `motion_is_the_point`, `swipe_shot`, `clean_single_shot`, `needs_product`, `product_slot_in_swipe`; `to_camera` with a line counts as talking) or names its `route` outright. A scene with none of these is AI, so a brief written before this rule prices exactly as it did.

`machine/shot_route.py label <shots.json>` gives every shot its route, the reason and its cost, and totals them per route and for the piece. That is the inventory: what gets made, what gets cut from footage we own, and what it costs, before a credit is spent. The edit reads the same labels, so every clip arrives knowing what it is.

A shot in `shots.json`:

```json
{"id": "S1", "seconds": 4.2, "what": "the barber behind the chair",
 "owned_footage": false, "motion_is_the_point": true, "swipe_shot": "K22",
 "clean_single_shot": true, "talks_to_camera": false,
 "needs_product": false, "product_slot_in_swipe": false}
```

## Costs used for the projection

From the providers' own numbers and our measured runs (2026-10-20). A credit is $0.0435.

| Route | Cost |
|---|---|
| REAL | $0 |
| SWAP, 1080p | about 8.3 credits a second (35 credits for a measured 4.2 s swap) |
| AI, frames | the pictures the storyboard lists (a start, and an end only where the shot needs one), one version of each (VIDEO-RULINGS V33, 2026-10-21; the owner again 2026-10-24: "Stop doing 3 versions each"), remade only when the review sends it back, about $0.12 a picture |
| AI, clip | Seedance 2.5 for every clip (`components/generative-model-house/MODEL-HOUSE.md`): 480p (upscaled locally to 1080x1920), about $0.13 a second estimated by pixel count from the measured 720p price of 6.5 credits ($0.28) until the first 480p call prices it, one take, another only when it fails, three at most (VIDEO-RULINGS V34), the kept take upscaled locally. The old per-engine split (Omni, MiniMax, Seedance for cinematic motion) is gone: `clips_run.engine_of` was removed 2026-10-26 (V43) |

Retries are priced at 1.5 times on swaps and clips. When a run's real cost differs, update the numbers here and in `machine/shot_route.py` together.
