# The video process — one brief to the editor's hand-off

The standard for making one AI video, scene by scene, on the board (`http://127.0.0.1:8895/prompt`, **Video ad**).
Written 2026-10-28 from the code as it stands and the owner's Tella reviews of that day (`components/model-inputs/lessons.json`
L-50 to L-62). the owner's page for the same process: **The Video Process**, (private page) (source `context/video-process-damon.html`).

Three things hold for every stage:

- **The board only starts jobs and shows them.** Every job that makes, keeps or remakes something runs as its own
  process (`components/model-inputs/board_job.py`; its state is `runs/prompt-bench/jobs/<id>.json`), so a board restart
  never kills paid work. Logic that lives only in the board is a bug.
- **Agnostic.** No brand, product, ingredient, person or gendered word is written into a prompt, the code that builds
  one, or a rule. Brand content comes only from `brands/<brand>/`; an ad's own content lives only in its run folders.
  A person's pronouns come from their own bank (`shot_swaps.pronouns`), the place from the brief.
- **Nothing spends unpressed.** A press on the board is the cost approval for that one thing.

## Where our side ends (the owner, 2026-10-28)

> "we need to get to just the brief stage for these next videos. We're still going to go one at a time through our
> established process. And then what I'd like to get out for every brief are at least the images for each scene, so I
> can ensure that it's all set up properly. And then from there, [the video editor is] gonna actually do the actual …
> turning the images into the video scenes themselves, arranging things, making tweaks and optimizations, rerunning as
> necessary … pulling in other B-roll, doing effects … he can take care of the rest."

**Our side ends at the scene pictures the owner approved (stage 4).** Stage 8, the hand-off, then carries the brief, the
approved pictures and each scene's clip prompt. Clips (5), effects (6), the edit (7), B-roll and remakes are the video
editor's. Stages 5 to 7 stay written below as the standard the editor's work is checked against and for any ad the owner
asks to run through on the board (L-80).

**A re-edit brief** (one that generates nothing: its `deliverable/EDITOR-BRIEF.md` is the whole brief) hands off
through the same front door: `tools/video-edit/handoff.py` routes it to `machine/reedit_handoff.py`.

## The stages at a glance

| # | Stage | Board button | Gate | A person decides | Output lives in |
|---|---|---|---|---|---|
| 0 | Swipe → brief | none (teardown + writing chain) | swipe match, manifest | the swipe and the brief's angle | `runs/video-writing/<brand>/<slug>/deliverable/5-brief.md` |
| 1 | Load the brief: voice and scenes | none yet (see open items) | production gate, banks, footage, elements lock, audio gate | nothing (gates pass or stop) | `runs/video-production/<brand>/<label>/` |
| 2 | Break the swipe down, scene by scene | runs with **Get the swipe frame ready** | hand drift is measured, never read | nothing | `…/<label>/scene-breakdown.json` |
| 3 | Get the swipe frame ready | **Get the swipe frame ready** | swaps come from the brief only | nothing | `runs/image-teardown/<brand>/<brand>-batch-<label>-<scene>-start/` |
| 4 | Make the start picture | **Make the start picture** | body check (auto-remake ×2) | **Approve** or **Change it** | the picture run's `out/`; `…/<label>/body-checks.json`, `shot-approvals.json`, `shot-notes.json` |
| 5 | Make the clip, one take per press | **Make the clips of the approved scenes** → **Make the clip** | face gate, clip gate before; clip judge v4, body check, voice, words after | **Keep this take** or press again | `…/<label>/clips/calls/<call>/`, `clips/ledger.json` |
| 6 | Effects | **Remake effect &lt;id&gt;** | drawn on our own scene's object | keep or remake | `…/<label>/effects/<id>/` |
| 7 | The edit | **Next: edit the video →** → **Make the cut** | the edit line's own checks | watch; cut again or back to scenes | `runs/video-edit/<brand>/<label>/renders/control.mp4` |
| 8 | Hand-off to the video editor | **Hand off to the video editor** | the hand-off's checks | nothing | Drive folder; record `runs/handoffs/video-editor/<brand>/<brief id>/handoff.json` |

## 0 · Swipe → brief (before the board)

- **In:** the swipe video, the brand, the product.
- **Out:** the AI brief, `5-brief.md`, written on `tools/video-writing/prompts/v2/stage5-ai-brief-v9-damon.md`, plus
  the teardown run the board reads (`framemap/shots/`, `source.mp4`).
- **Runs:** `tools/video-teardown/machine/run.py <video> --brand <brand> --writing v2` → video-writing stages 3 → 5.
- **Gate:** the swipe match (`video-teardown/machine/swipe_match.py`, the brief's first line `swipe-match: PASSED`) and the
  manifest (`manifest.py`, `MANIFEST: COMPLETE`). The brief carries the scene rules from the start: props, the same
  object, the movement bar, effects on our object.
- **A person decides:** which swipe, which brand and avatar. Nothing else; the "the owner read" was removed 2026-10-27.

## 1 · Load the brief: voice first, then the scenes

- **In:** the brief and its teardown run.
- **Out:** `runs/video-production/<brand>/<label>/` — `plan.json`, `vo/` (one read per line, locked in `vo/locks.json`),
  `storyboard.json` (one scene per swipe cut, `storyboard_plan.py`). The label is the brief's register id
  (`brand_product_brief-NNNN`).
- **Runs:** `tools/video-production/machine/run_v2.py start <brief> --brand <brand> --format <format> --label <id>`
  up to the storyboard (voice → storyboard → pictures → clips; the board takes over at pictures).
- **Gates:** the production gate, the banks, our own footage first, the elements lock (every person, look, place, prop
  banked from a real reference), the audio gate and protected words. Each refuses by name.
- **Board:** the brief appears as a card under **Video ad** once `storyboard.json` exists.

## 2 · Break the swipe down, scene by scene (L-50, L-51)

- **In:** each scene's span of the swipe, with its sound.
- **Out:** `scene-breakdown.json`: the camera's hand drift, where the eyes go, each prop's state and lift, where each
  ingredient goes and its texture, what each action lands on, the sound effects, the atmosphere.
- **Runs:** inside the **Get the swipe frame ready** job, for a scene not yet read (`prompt_bench._open_job`), or by hand
  `tools/video-production/machine/scene_breakdown.py <run> [G01 …]`; prompt `prompts/v2/scene-breakdown-v2-damon.md`.
- **Rule:** held or propped is MEASURED on the frames (`camera_drift`), never read by a model. The clip prompt carries the
  camera, the eyes, the handling and the atmosphere — never the swipe's own objects. The clip judge checks the same list
  (shown on the scene card).

## 3 · Get the swipe frame ready (L-59, L-60)

- **In:** the scene's first swipe frame, the brief's cast, place and props for that scene.
- **Out:** a picture run with its swap list (`out/swaps.json`).
- **Board button:** **Get the swipe frame ready** (`prompt_bench.shot_open` → its own process: image-teardown `open` +
  `run.py all`, then `shot_swaps.py` writes the swaps, then the scene's breakdown, stage 2).
- **Rules, all in `machine/shot_swaps.py`:**
  - The swaps come from the VIDEO BRIEF, never the picture chain's own concept.
  - Our person from the cast baseline (headshot, look, labelled accessories), named with their own pronouns.
  - Our place is the brief's set; when the shot's 3D set is built, the room is its printed plate and the stand-in guides
    the light.
  - **The same object all the way through:** an object an earlier approved scene drew is taken from that scene's picture.
  - **Props in reach:** a prop picked up later in the scene is already in the start picture, within reach, not yet held.
  - The swipe's captions and stickers are removed; words are the edit's layer.

## 4 · Make the start picture (L-61)

- **In:** the swap list.
- **Out:** the start picture (made → realism pass → lens), kept in the picture run.
- **Board button:** **Make the start picture**.
- **Gate — the body check** (`machine/body_check.py`, `prompts/v2/body-check-v1-damon.md`): each hand traced to a
  shoulder, at most two arms and two hands, no oversized or fused hand; two reads that must agree. A wrong body is
  remade automatically, up to twice (`prompt_bench.BODY_RETRIES`), before a person sees it.
- **A person decides:** **Approve** (tied to the picture's exact bytes; a remade picture is not approved) or **Change it**
  (the note is kept on the scene in `shot-notes.json` and outranks everything else in the picture's words; one job,
  `prompt_bench._change_job`, rewrites the swaps and remakes the picture). A wrong body that survived the remakes shows **Approve anyway**.

**One style of shot, one picture (2026-10-31).** Scenes that show the same person doing the same thing, a talking head
for example, share one start picture: new lines, expressions and emotions come in the clip, so no new picture is made for
them. A new picture is made only when the person does something significantly different in the shot. `machine/shared_shots.py` runs after the storyboard and measures this on the swipe's own frames: same people, looks and place on alike frames share the first section's picture.

**Demonstrations come from our footage first (2026-10-31).** A demonstration scene, such as a barber working on a client in
the chair, uses real clips from the brand's indexed footage (`tools/asset-index/machine/search.py`); a picture is
generated only when the library has nothing that fits. A clip counts only when it comes from the scene's own setting (`footage.py` `_in_place`).

## 5 · Make the clip, one take per press (L-53 to L-57, L-62)

- **In:** the approved start picture, the locked read, one real-movement reference, the breakdown.
- **Out:** one take in `clips/calls/<call>/`, its checks in `clips/ledger.json`.
- **Board buttons:** **Make the clips of the approved scenes** → the clip steps → **Make the clip**; then
  **Keep this take** on the scene card.
- **What goes in the prompt** (`machine/seedance_prompt.py`): picture and voice bound in one Seedance 2.5 call at 480p;
  the beats on their words (`cued`); **props make physical sense** (`PHYSICAL`: a lid comes off before anything is
  taken out; every ingredient goes somewhere visible and stays the same thing); **the movement bar** (`MOTION`: hands
  keep doing the real task, unhurried, eyes drop to the hands and come back to the lens, head and shoulders move
  naturally); the breakdown's camera, eyes, handling and atmosphere; a real-person movement reference
  (`movement.py`, `movement-bank.json`).
- **Gates before spend:** the face gate (`face_gate.py`) and the clip gate (`clip_gate.py`).
- **Checks after:** the clip judge v4 (`prompts/v2/clip-judge-v4-damon.md`: props, the action on the right object, the
  voice, the swipe's elements); the body check on the take (a wrong body is a hard fail); the voice measured (a silent
  talking take fails; a talking clip never goes to the silent backup); the words checked word by word (`CUT_OFF`,
  `REPEAT`, and `MISSING` for a take that skips three or more words of its line, `lineparity.py`); a failed word check
  is made again.
- **One take per press** (`providers.json` `max_tries: 1` for a hand run): the take is judged and shown; the person keeps
  it or presses for another. A press always starts a new round.
- **Keep this take** makes it the scene's clip **as made**: no camera moves and no upscale (`upscale_on_keep: false`);
  both wait for the edit and the hand-off.

## 6 · Effects (L-52, L-58)

- **In:** the brief's effect for the scene, our scene's approved picture, the product kit's in-use photos.
- **Out:** `effects/<id>/still.png`, `clip.mp4` (upscaled), the made clip beside it, older tries in `versions/`.
- **Board button:** **Remake effect &lt;id&gt;** (`prompt_bench.effect_make` → `machine/effects.py`).
- **Rule:** an explainer the swipe draws on an object is drawn on the matching object in OUR scene's picture, in the
  swipe's style — never a separate diagram on black. Laid in over its words by the edit.

## 7 · The edit

- **In:** every scene's kept clip in order, every effect as B-roll of the same name.
- **Out:** the draft cut `runs/video-edit/<brand>/<label>/renders/control.mp4`, captions on.
- **Board buttons:** **Next: edit the video →** → **Make the cut** (`prompt_bench.edit_make` →
  `tools/video-edit/machine/line.py <run> --draft --approved --no-file`, its own process).
- **What made the final cut** (the owner on cut 4 of the first video, 2026-10-28: "fire. great this is it. establish this
  process"). The run's own choices live only in `runs/video-edit/<brand>/<label>/decisions.json`, each with the
  person's words:
  - **The edit only cuts (L-66).** Script, voice and clips are approved, so nothing is regenerated here; word, mouth
    and sync findings are listed for a person, never a stop (`render_map.py` `_lenient`). Each stage has one job.
  - **A phrase a take never said (L-70)** is cut only when the person accepts it: `cut_words` (`render_map.accepted_cut`).
  - **A scene taken out (L-71):** `drop_sections` `{scene: their words}`; it is not in the cut and the edit notes say
    why (`edit_map.dropped_sections`).
  - **The captions follow the swipe (L-72):** the bank look nearest the swipe's own captions, as the breakdown reads
    them, before the format's default (`looks.from_swipe`); `captions.look_id` still overrides.
  - **The opening in the caption look (L-73):** no separate headline look unless the swipe shows one
    (`looks.headline_distinct`); `text_keep` still overrides.
  - **Single opening words wrap as one line (L-74)** (`map_sheet.py`).
  - **An effect that didn't come out well stays out (L-75):** its placement moves from `broll.place` to
    `broll_removed` with the person's words; the hand-off still carries it for the editor.

## 8 · Hand-off to the video editor

- **In:** the run, its brief id from the register.
- **Out:** one Drive folder — the brief, every scene's clip, stills and voice, the music and sound, a one-page how-to —
  and its record `runs/handoffs/video-editor/<brand>/<brief id>/handoff.json`. Named by the role, never the person.
- **Board button:** **Hand off to the video editor** (`prompt_bench.handoff`, kind `clip` → `tools/image-edit/handoff.py`,
  which reads the lane from the register; the package is video-edit's).
- Nothing is made or spent. From here the editor finishes the video: **camera moves and sharpening the scene clips are
  the editor's** (the owner, 2026-10-28: "I'm going to have the team handle the rest of this stuff later"; L-57,
  `upscale_on_keep: false`). Effect clips arrive already sharpened (L-58).

## Today's rules, where each is enforced

| Lesson | Rule | Enforced by |
|---|---|---|
| L-50 | Every swipe scene read to its smallest elements | `scene_breakdown.py` `read` |
| L-51 | Held or propped is measured, hand drift into the prompt | `scene_breakdown.py` `camera_drift` |
| L-52 | Effects drawn on our own scene's object | `effects.py` `our_picture` |
| L-53 | Props make physical sense | `seedance_prompt.py` `PHYSICAL`; clip judge v4 |
| L-54 | The action lands on the right object, and stays it | clip judge v4 |
| L-55 | A talking take carries the voice | `clips_run.py` voice check |
| L-56 | One take per press | `providers.json` `max_tries: 1` |
| L-57 | No camera moves on a kept clip | `clips_run.py` keep |
| L-58 | No low-resolution effect reaches the edit | `effects.py` `upscaled` |
| L-59 | The same object scene to scene | `shot_swaps.py` `earlier_picture` |
| L-60 | Props in reach | `shot_swaps.py` later props |
| L-61 | The body check on every picture and take | `body_check.py`; `clips_run.py`; `prompt_bench.py` |
| L-62 | The movement bar | `seedance_prompt.py` `MOTION` |
| L-66 | The edit only cuts; findings are listed, never a stop | `video-edit/machine/render_map.py` `_lenient` |
| L-67 | A take that skips 3+ words of its line is MISSING and made again | `lineparity.py` verdict `MISSING` |
| L-70 | A phrase never said is cut only when a person accepts it | `render_map.accepted_cut` |
| L-71 | A scene a person takes out is out, with their words | `edit_map.dropped_sections` |
| L-72 | The captions follow the swipe | `looks.from_swipe`, `map_sheet.py` |
| L-73 | The opening is in the caption look unless the swipe has a headline look | `looks.headline_distinct`, `edit_map.py` |
| L-74 | Single opening words wrap as one line | `map_sheet.py` |
| L-75 | An effect that didn't come out well stays out of the cut | decisions.json `broll_removed` |

## Open — not standardised yet

Kept in one list for the owner to rule on; mirrored on The Video Process page. Settled 2026-10-28 on his "do whatever to
make this smooth": the breakdown runs with the swipe frame; Change it is its own job; camera moves and sharpening are
the editor's; the rule numbers no longer clash (the edit rule is L-66, the skipped-words check L-67); the board's
wording is neutral.

1. **Loading a brief has no board button.** Stage 1 is run by a session (`run_v2.py start`); the board shows the brief
   only once `storyboard.json` exists.
2. **Edit and teardown prompts that still carry one brand or person** (the writing prompts were made brand-free on
   2026-10-28, see below): the edit's cut prompt says "she", the edit prompts name the owner, and teardown prompt
   headers (changelog lines, sent to the model) name a brand.
3. **Skincare logic in code:** the "after the routine, the spots are gone" rule (`clips_run.py` `EVEN_SKIN`,
   `clip_gate.py`) and the effects fallback that treats `scrub|serum|cream` as the product
   (`effects.py` `product_refs`). Generalising them from the product kit changes behaviour.
4. **Captions and the opening:** settled (L-72, L-73).
5. **Effects don't hold up yet.** Out of the first video's cut (L-75). Whether the board makes them better next
   brief or the editor makes them is the owner's call.
6. **Brand buttons on the board** spell one brand's name in capitals by hand (`prompt_bench.html`); it should come from
   the brand's own files.

## The writing prompts made brand-free (2026-10-28)

New versions, live now; no rule, slot, placeholder or output format changed. Old versions kept.

| Stage | Old → new | Lines changed |
|---|---|---|
| The brief (AI video) | `stage5-ai-brief-v8` → `stage5-ai-brief-v9-damon.md` | 48 |
| Our version of the swipe | `stage3-injection-v7` → `stage3-injection-v8-damon.md` | 24 |
| Reading the hooks | `stage4v2a-readhooks-v4` → `stage4v2a-readhooks-v5-damon.md` | 20 |
| Placement, expansion, close | `stage4v2b-build-v5` → `stage4v2b-build-v6-damon.md` | 19 |
| The audit | `stage4e-audit-v7` → `stage4e-audit-v8-damon.md` | 12 |
| Spice | `stage4g-spice-v6` → `stage4g-spice-v7-damon.md` | 24 |
| Presenter body | `presenter-body-v5` → `presenter-body-v6-damon.md` | 14 |
| Swipe match | `swipe-match-v1` → `swipe-match-v2-damon.md` | 4 |
| Creator brief | `stage5-creator-brief-v34` → `stage5-creator-brief-v35-damon.md` | 67 |
| Creator page concept | `stage7b-concept-v8` → `stage7b-concept-v9-damon.md` | 37 |
| Who it speaks to | `stage1b-audience-v12` → `stage1b-audience-v13-damon.md` | 11 |
| Hooks (creator) | `stage4b-hook-v25` → `stage4b-hook-v26-damon.md` | 32 |
| Placement (creator) | `stage4a-placement-v17` → `stage4a-placement-v18-damon.md` | 16 |
| Our version (creator) | `stage3-injection-v24` → `stage3-injection-v25-damon.md` | 29 |
