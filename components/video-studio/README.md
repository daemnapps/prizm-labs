# Video Studio

One place to make a video ad: the storyboard, the production of each scene, the edit, the versions and the approval card, under one menu that always names the brand, the ad and the stage.

**The edit is Video Edit's (2026-11-21).** The Studio shows the work; every edit stage (cut, check, render, edit moves, covers) runs Video Edit's code (`components/video-edit/machine/studio/`), and the names here forward to it. One command delivers a production end to end: `python3 components/video-edit/machine/run.py deliver <production>` (`components/video-edit/DELIVER.md`).

## Run it

```
python3 components/video-studio/video_studio.py serve --port 8922      # the Video Studio, http://127.0.0.1:8922
python3 components/video-studio/video_studio.py run <brief> <scene>    # remake one scene alone
python3 components/video-studio/video_studio.py package <brief>        # the production package for HyperFrames
python3 components/video-studio/seed_from_brief.py <idea>              # a storyboard idea -> a production (never a second one)
python3 components/video-studio/quick_variation.py <p> <new> --lines lines.json   # a finished production -> a new one with lines swapped (quick variation)
python3 components/video-studio/sound_board.py build <brief> --scene S1 [--make]  # every sound of a scene carded, the swipe's next to ours
```

## Sound board

Every sound in a scene has its own card, as every picture does: each music section (build, break, hit, drop, out), each sound effect, each sound a person makes (sniffs, "Ew", sighs) and the room tone. A card plays the swipe's own clip of that sound and ours from the latest cut, says what ours is made from (the bank file, the music take and its cue, or the prompt of a take we made), and runs three checks: it lands on the swipe's frame, it sits over or under the music by the swipe's amount, and an ear hears the two as the same sound. `--make` makes a new take of every effect and the room through ElevenLabs sound generation, its prompt on the card; laying a take into `music/bed.json` stays the edit's step. The Production canvas opens it from the Sound button; the board is files in `briefs/<n>/sound/`, served by the `/files` route, so a running Studio picks a new board up without a restart. `sound_board.py` docstring has the details.

## One address

The Studio is the only address: it serves the storyboard board under `/board/` and the approval page under `/approve/`, and sends their own requests back to them, so a computer and a phone open one link. The apps keep running where they are (`VIDEO_STUDIO_BOARD`, `VIDEO_STUDIO_APPROVE`); nothing in them changes. The HyperFrames editor in the Edit tab still opens on its own local port.

## One ledger

Where every ad stands comes from the ledger, the Queue (`VIDEO_STUDIO_LEDGER`), in its own stage names (`components/naming/stages.json`): the Studio never keeps a stage of its own. The Studio answers `/api/productions` for the ledger to read, so an ad being built shows there at Making (Editing once it has versions), and its approval card carries it on to Approve ad, Sending to Meta and On Meta. A production made from a storyboard idea's writing run is linked to that idea by the run's name, so the board, the Studio and the ledger show one piece once.

## Stages

| Tab | What it shows |
|---|---|
| Storyboard | the storyboard board (`VIDEO_STUDIO_BOARD`) |
| Production | one node per scene, its steps, every take, and for every AI shot the reference, prompt, model and the takes thrown out |
| Edit | the cut in HyperFrames, run locally, one button per version |
| Versions | every finished version |
| Covers | each version's cover: the frame it started from, the Explore cover it follows, its words, its checks, and why each was picked (`covers_stage.py`) |
| Approve | the ad's approval card (`VIDEO_STUDIO_APPROVE`) |

Phones get the same tabs behind a drawer; Edit opens on the computer only.

## AI shots (AI lane)

An AI-lane production whose scenes still hold AI shots (`gen.shot`) gets **Make the AI shots** before **Hand off to
the editor** (`ai_shots.py`). The step holds no production logic (owner ruling, 2026-11-20): it starts the production
chain's own command for the brief (`components/video-production/machine/ai_lane.py`: elements, voice, storyboard,
pictures from 3D set prints, camera and motion plan per scene, clip plan, clips) and shows the chain's run station by
station. `ai-shots-stage.json` `dry_run` (default true) runs the chain's dry run only; false is the live run on the
owner's go, capped by `cap_credits`. A chain clip made for one scene is laid into that scene's take; the hand-off waits
until the chain has made every scene's clip.

## Covers

Once every version is rendered, the Next step job runs straight on into the covers (`covers_stage.py`); nobody presses
or picks. Per version: the strongest moment of its opener (one frame a second, the closest face, never a sibling's
picture); an Explore cover its avatar sees to follow, with a rated move (the cover index, `components/asset-index/swipes`,
the avatar's own pull only; a swipe the brief names must be one of those too); its headline (the first line of its opener
the other versions do not say, whole or cut at a first clause of at least three words; a line runs to its . ? ! and never
ends at an abbreviation, an initial or an ellipsis inside it); image production's standing cover direction. All
versions go to image production's cover job as one job (`make.py covers --job`), with the ad's filed 3D set: the
brief's own, else the set the production's own take records, start frames or generated shots were made from.

Each cover is checked: the tool's verdict, size, words off faces, faces against the cast sheets, made by the tool
(GATE-5), unlike its siblings, and the card's cover checks (`meta-upload/cover_rule.py`). A face or sameness miss is made
again once from the next moment and the next swipe, then held.

Held, with the reason on the board:
- a swipe that is not one of the avatar's covers, or has no rated move;
- a line with no whole clause of 3 to `headline_words` words, or one that opens a quote it does not close (the brief
  names `covers.<version>.headline`);
- no filed 3D set, no cast named (`name the cast`), or no face reader on this machine: before anything is sent;
- a check that could not be read, a face check that stopped or whose judge did not answer included: it is not made
  again.

A re-run makes only the versions not yet ready; a cover still ready from the same render is kept. Only a record the tool
wrote in this run is read back. The stage is never offered or run for a production whose card is approved, live or
already carries a cover for every video, or whose card cannot be read: it keeps "Open Versions". The card is found by
the full brief key: brief.json's `brief_key`, else the number the brand's brief list filed the production under
(`video_studio.filed_brief`), for a production filed straight from a card. A card with only some versions' covers does
not stop the stage: the rest are made.

The hand-off is `briefs/<production>/covers/to-file.json`: the filer takes its `thumbs` and `cover_records`, video for
video (`python3 covers_stage.py file-args <production> [--media ...]`, or `covers_stage.filer_kwargs`). A run withdraws
it before it starts; a cover whose video was rendered again since is never handed over. The set goes over whole or
not at all: while any version is held, `thumbs` and `cover_records` are all '' (the ready ones are named in `withheld`).
What a brief names in
`brief.json` `covers` (avatar, swipes, set, product, and per version headline, swipe, second, direction) wins. Switch:
`cover-stage.json` (`on`, `after_render`, and the parts `skip_closed`, `hold_unread`, `concept_required`, `pick_set`,
`filed_brief`, `face_unread`, `whole_hand_off`, `whole_sentences`;
row COVER-STAGE in `team/rollbacks.md`).

## Settings, not paths

| Setting | Default |
|---|---|
| `VIDEO_STUDIO_DATA` (holds `briefs/` and `sources/`) | `runs/video-studio/` |
| `VIDEO_STUDIO_DRIVE` (a synced `Shared Assets` for library clips) | none; clips are pulled by link |
| `VIDEO_STUDIO_BOARD`, `VIDEO_STUDIO_APPROVE`, `VIDEO_STUDIO_STUDIO` | `127.0.0.1` ports 8914, 8795, 8922 |
| `VIDEO_STUDIO_BOARD_DATA` (the storyboard board's `matrix.json`, `owner-edits/`) | `runs/storyboard/` |
| `VIDEO_STUDIO_WRITING` (the writing runs, each with its production brief) | `runs/video-teardown/_work/` |
| `VIDEO_STUDIO_COVER_INDEX` (the cover swipe index the cover stage follows) | `runs/asset-index/swipes/covers/` |
| `VIDEO_STUDIO_CASTING` (the cast sheets the cover faces are checked against) | `runs/ai-elements/` |

Keys come through `components/keys/loader.py`. Brands come from `brands/`: a brand with a `meta/account.json` shows in the menu, under its `label`.

## A brief's own files (data, in `briefs/<brief>/`)

- `brief.json`: scene order, the take each scene uses (`picks`), the storyboard idea, caption spellings (`spell`), the narrator's name (`voice_name`).
- `scenes/<scene>/take-N.json`: one workflow per take; every step's tool, model, prompt, seed, source, in/out, crop, sound and caption.
- `music/suno.json`: the music sheet `suno_bed.py` cuts to the edit (takes, lane, beat grid, cue sheet, EQ).
- A brief's own cut scripts (a shot table, its hook openings) live with the brief, never in this folder.

## Every shot copies its swipe shot

A brief's shots come from its swipe (`swipe_shots.py` → `shot-list.json`), its picks are data (`picks.json`), and `swipe_cut.py <brief> --run` cuts every scene at the swipe's shares. Then `swipe_check.py <brief> [cut]` proves it, and one of its checks is the pictures themselves: `shot_copy.py` sets each made shot's frame beside its swipe shot's and has the vision judge say COPIES, WEAK or MISSING, with what ours needs (cached per frame; `SHOT-COPY.json`, `SHOT-AUDIT.jpg`, swipe left, ours right). A MISSING shot fails the check; WEAK ones are shown. `shot_copy.py <brief> --fill [ids]` routes each miss: owned footage first (asset index, candidates judged against the swipe shot, no price or text on screen), else an AI recipe from the swipe's guide frame and the face master (a people picture needs its filed 3D set first, image-production RULE GATE-4), else, with the product in the shot, a creator shoot line. A shot the owner keeps as it is carries his words as `owner_ok` in `picks.json`. The judge door asks Gemini first; where that network call hangs, `VISION_JUDGE_ORDER=claude` runs it on the Claude plan.

## AI shots

A missing shot is defined first by `shot_spec.py <idea> <shot>` (route; our product's use from its kit through `video-production/machine/shot_use.py`; the team's per-shot job: picture teardown 1, 1k, 2, 2b, `shot_swaps.py`, `scene_breakdown.py`), written to `briefs/<idea>/shot-spec/<shot>.json`. `gen_ref.py` makes every AI shot one way, from the Generative Model House: a real reference frame → still → clip → phone pass. It makes nothing without a complete AI-routed spec, and the clip's words are the spec's. Every run is recorded on the shot's recipe and shown under "How it was made". Pictures go through `components/image-production` and its referencing rules.

The clip's motion is real footage of the same action, never invented by the model: the swipe shot's own seconds (its span in the frame map), or the recipe's `motion` (owned footage, else TikTok/YouTube). `gen_ref.py` runs it through the motion chain (`components/motion/`: tracked, read as body mechanics, rehearsed in 3D by the real skeletons with the real camera, checked) and makes the clip through `take.py` from the still. `take.py` reaches motion through the same door (`motion_chain.for_take`): a tracked camera takes the written shot sizes out of the take. `motion.py`, `motion_program.py` and `blocking_blender.py` here are forwards to `components/motion/`. The face check runs on the still first, and the person's real face leads the still's references. A real creator on a cast board (`image-production/cast_board.py`) carries their real video frames under the look sheet.

## Voices

Every speaking role takes the one voice set for its demographic: `brands/<brand>/ai-elements/voices.json`, read by `voices.py`. The narrator gets the voice for the people on screen (brief.json `audience.face`, else the brief record's `moves.face`, else `shot_fill.person`). Each on-camera speaker gets the voice for their own face (a take's cast `face`). `voice_continuous.py` sets the narrator before every read. `quick_variation.py --face <sex/age/ethnicity>` recasts every voice of a copy (lines.json `cast_faces` for the speakers). `swipe_check.py` fails `voices_match` on any mismatch. A demographic with no voice is refused by name until one real voiceprint of it is added to the list. `python3 voices.py <production> [--apply]` shows or sets them.
## Product on skin

`product_layer.py` lays a product that is used on the face or body into a take's hand from its own 3D kit, so a video model never draws it: the take's hand holds a plain stand-in in one keyable colour; the face mesh and hands are tracked, the stand-in is keyed out, the product is rendered at its true size where the stand-in sits, the hand stays in front, the light is read off the clip. The method, the plan format and what holds and breaks: `PRODUCT-LAYER.md`.

## How an ad is made is the chain's call (2026-11-18)

The Studio shows the lane and its reason; it never decides one. `components/video-production/machine/lane.py` gives the
call for a new production (the maker route, the format, the style, the footage decision) and the one answer for a
production saved before lanes were recorded. A lane picked at Produce is the person's and is recorded as theirs. The
header shows `Made as …` with the reason on hover. Tests: `test_lane_call.py`.
