# video-production — an AI video brief in, voice and stills and clips out

**video-production** — takes **an AI video brief**, makes **the voice, the
stills and the clips**. Does not **write the script**. Triggered by
`python3 machine/run.py start <brief.md | plan.json> --brand <brand> --format <format>`
(`--dry-run` spends nothing), then `record` and `pack`.

The model-agnostic AI-video production process: brief in, finished clips
out, across four generation stations — cast, voices, scenes, motion. Being
rebuilt to run fully local. The edit (cut sheet + rendering) is a separate
process, deliberately out of scope here.

Runs by: person (2026-10-08, B4a (decide-now cards) card 3, R-person-or-mini: the team, relayed verbatim by ◆ PLAN [1cc25f] before 04:49:43Z: "3 yes, 4 yes,5 yes, 6 yes"; the owner told after).

**Before you start on a second Mac (video-production#28):** Xcode command-line tools (`swiftc` compiles `machine/vision/*.swift` on first use — `swipe_guide.py`, `product_check.py`, `product_kit.py`) and Blender on PATH for product kits (see `product_kit.py` for where it looks). The whole second-computer setup — every program, key name and Drive login, each with how to confirm it — is `runs/system-integration/second-editor-setup/SETUP.md` (2026-10-10).

**Two computers, one line — the work queue (the owner, 2026-10-10: "a second video editor pump stuff too so he'll have another computer").** `machine/work_queue.py list | claim <brief> | sync | release <brief> | page` — every ad (one brief id) at its stage (song · b-roll · cut · hooks · card · done, read from `runs/video-production`, `runs/video-edit/…/deliverable/versions-index.json`, the run's Drive mirror and `Shared Assets/meta/<brand>/<state>/video/`) and which computer holds it. Claims are records on the plane, kind `video-queue` (`platform/data/kinds/video-queue.json`), committed straight onto origin/main by commit-tree + push — never through a working tree, so a busy checkout's staged work is never touched; git's fast-forward refusal is the lock. A claim with no progress for 6 hours can be taken with `--take-over`. The status page goes to `runs/video-queue/_system/status.html`. Tests: `machine/test_work_queue.py`.

**Declared dependency (local-studio#15):** `machine/product_check.py`'s
`product_mask()` runs local-studio's `jobs/segment_image.py` with
`components/local-studio/.venv` (SAM 2); without that venv the product check
fails. See components/local-studio/CLAUDE.md, "Public entry".

**The whole video chain, in order — teardown → writing → elements → production → edit — is `THE-CHAIN.md`** (the owner, 2026-10-01: "we need to establish the logical chain"). Elements are production step 1, made from the brief and checked against it (`machine/element_match.py`) before anything is reused.

## The route this machine is (ruled 2026-09-02)

**Teardown makes the brief. This machine turns the brief into output.**
They are two halves of one road and neither does the other's job:

    swipe → tools/video-teardown → A BRIEF
                                            ↓
                        THIS MACHINE → cut-ready scenes → clips

`chain_config.json` is the whole route, stage by stage, the same shape the
teardown machine's chain uses so the two read alike. Thirteen stages: six
that write (format read · production document · identity plan · ledgers ·
scene prompts · handoff), the four generation stations that were always
here (cast · voices · scenes · motion), and the machine steps between them
(train · generate · re-roll).

The named method docs are the doctrine behind the chain —
written 2026-09-01 from a real production the owner ran and generalised on his
word, brand-agnostic and format-agnostic. `formats/` holds the profiles: a
profile says what a scene CONTAINS (micro-drama, single presenter,
demonstration, testimonial montage); it never changes the method. Adding a
format costs one profile.

**Proven on the route, 2026-09-16.** Six pieces ran it end to end across
three formats — a song ad, an expert-consult ad and meme-style ads. The
`chain_config.json` stages remain the design; the checklist protocol
(`formats/RUN-PROTOCOL.md`) is what runs, by hand, with the session
pasting the prompts' variables. That day also cost ~$55 an ad against a
$3–4 floor, which is what the hard rules below are for. Lab quarantine
holds.

## Format playbooks (the owner, 2026-10-10)

*"It's about optimizing workflows for specific types of ads, as opposed to just
having a general workflow for all ads."* A **playbook** (`formats/playbooks/<id>.json`
+ `.md`) is the explicit layer that DOES carry per-format stage settings on top of
the shared chain — the one exception to "profiles never carry gates / never change
the method", which still holds for profiles. `machine/playbook.py` resolves a format
to its family playbook, or a variant of one, or `default.json` (today's chain);
`song.py` reads its flow thresholds and beats per line from it and
`direct_openai.generate(..., format_id=)` its picture quality, size and model tier —
with no playbook, nothing changes. **Match first:** `machine/playbook_builder.py`
scores every new swipe's structural signature against the families and records a
close one as a variant, drafting a new family only when nothing is close; the
teardown starts it right after triage names the format (`video-teardown/machine/run.py
playbook_hook`, a background process). `machine/playbook_learn.py <run>` feeds every
finished run back. Both write their decisions under `runs/playbook-learn/`, and —
the one declared exception to "output goes under runs/" — install drafts and
learned failures into `formats/playbooks/` itself, because a playbook is a
definition the engine executes and the owner ruled the system writes them, not him.
Runs: `runs/playbook-learn/<format>/<run>/` (MATCH.md, PROPOSAL.md) + `decisions.jsonl` — read as files, no records adapter (filer: none). Public surface for other components: `playbook_builder.ensure(run_dir)` /
`python3 machine/playbook_builder.py <teardown-run>`.

## Hard rules (2026-09-17)

- **A run is labelled by its brief number** (2026-10-15): `--label` is the brief's register id, `brand_product_brief-NNNN` (e.g. `brand_a_nova_brief-0070`, from `tools/image-teardown/briefs.json`) — so the production run, the edit run and the delivery all carry the brief number (the owner, 2026-10-15). A brief with no number yet gets one first (`tools/video-teardown/machine/file_run.py` `number_brief`).

- The platform is detected and the models shown before anything runs.
- Nothing submits without a green preflight.
- Nothing moves unverified — a still goes to motion only after it is
  verified against its cast sheet, in writing.
- A ceiling ships FLAGGED with zero re-rolls. **A clip that stops mid-line is
  not a ceiling** (the owner, 2026-09-23): the words check calls it CUT_OFF, `record`
  writes a remake order, and it is made again SURGICALLY — only the broken
  element (voice slice, frame, or clip) is remade, and what is built on it is
  rebuilt from the same originals (`machine/remake.py`, the `remake-clip` skill).
- A voice anchor id is first-class when element registration is
  rate-limited.
- One blocking poll per run; state restored from the run record.
- Sweep every ledger page before quoting spend.
- Every format enters through `formats/bank.json`, written from
  `formats/TEMPLATE.md`.
- The protocol is `formats/RUN-PROTOCOL.md`; profiles never carry gates.
- Two QC layers, two verdicts — the inspector says it is the scene
  specified; the director says it will stop a thumb; a clip ships with
  both on file.
- Every video prompt carries the no-cut line; every result shown keeps the
  anti-perfection budget (the course write-up, the owner 09-14).
- **Every speaker reads in their own voice** (2026-09-23): the brief names each
  scene's `speaker`; `voice.py` reads each scene in that person's voice,
  stitched only on that voice's own takes, and stops the run naming anyone
  who speaks without one.
- Voices are made on our ElevenLabs account, one custom voice per
  character, generated before any picture and piped into the provider
  (the chain, step by step: `VOICE-CHAIN.md`). **The song is ElevenLabs Music
  `music_v2_5`** (ruled 2026-09-23, the owner: "Eleven Labs won for me for sure";
  Lyria is the alternate), printed by `machine/song.py` from the brief's
  `song` block only — the chain: `SONG-CHAIN.md`.
- **Which way a shot is made is ruled in `SHOT-ROUTES.md` alone** (the owner, 2026-10-20: "clean up the old and newer
  ruling so this is the only ruling on how to use the different models"). Every shot is REAL (footage we own),
  SWAP (the swipe's shot with our cast swapped in, when the motion is the point) or AI (generated first and last
  frames, then a clip), labelled with its cost by `machine/shot_route.py` before anything runs. The lines below say
  how each route runs; none of them decides which route a shot takes.
- **What each model does is ruled in `components/generative-model-house/MODEL-HOUSE.md` alone** (the owner, 2026-10-20): GPT Image 2.5 for every
  picture and every image edit; Seedance 2.5 for EVERY clip (the owner, 2026-10-23; the Omni route was removed
  2026-10-26, VIDEO-RULINGS V43); Genjutsu
  for the swipe's own shots. Which model each ad format uses is decided next, there. Cost is never a reason
  to pick another model. Earlier model rulings in this file and in `providers.json` are history.
- Every talking clip is transcribed and compared to its line before it
  ships; lip-sync to the wrong words is a FLAG.
- **One image door** (2026-09-18, the owner: "gpt for all image work"): every still
  and every edit runs on GPT Image 2.5 direct — edits with input fidelity
  high and two references (previous frame, cast sheet), colour-matched to
  the first frame after. There is no other edit door: the model is the Generative Model House's `pictures.edit`
  (read by `machine/house.py`, 2026-10-21); Nano Banana Pro and direct:google are history.
- **No scene length is ever a number** (2026-09-18). A scene plays out
  fully — its characters, its elements, its words, its pain or proof —
  and its length falls out of that; a format profile gives the length
  philosophy, never a number, and a motion model's duration cap splits a
  scene at its boundary only, never by line. A scene that cannot name
  its Emotion and its Outcome is a transition — merge it or cut it; this
  rule outranks the profile.
- **A scene is a paragraph** (2026-09-18). One setting, one section of the
  argument, shot as one or more shots. **Each line is its own read** (VIDEO-RULINGS V4/V5, replaces the
  2026-09-18 "ONE read … never a call per line", C2): ElevenLabs v3 with the line's delivery sent as its audio
  tag, three reads of every line scored and one locked (`vo/locks.json`); never one long take for the whole piece.
- **Attempts are capped, every one scored, the best moves on** (VIDEO-RULINGS V33/V34, replaces "three of everything"):
  ONE read of every line (heard back; read again only when its words fail), ONE version of every start picture the
  storyboard lists (remade only when the review sends it back), and up to the configured maximum of attempts at a clip
  (default 3 on Seedance, the Kling backup as the last rung), each judged by the clip checks (`machine/clip_judge.py`,
  words, face lock, frame-by-frame). The best-scoring attempt is kept (a tie goes to the later) and, if it did not pass,
  marked `below_criteria` with the plain failed checks; the chain moves on and the flag travels to the edit. Only the
  kept one is upscaled, on this Mac. A clip output never holds the chain; only a missing or out-of-limit input does.
  `machine/run_v2.py start` runs the order — voice first, then the storyboard, then only the pictures it lists, then the clips (V7).
- **Every clip is Seedance 2.5 at 480p, upscaled on this Mac, voice and picture in ONE call** (ruled 2026-10-23; 480p since 2026-10-26, `components/generative-model-house/MODEL-HOUSE.md` Clips; `models.json` `clips.ruled_2026_10_23`): `clips_run.make_call` sends every clip to `machine/seedance.py` — a talking clip carries its locked read with the start picture, so nothing is re-voiced after; Cost never decides.
- **How a Seedance clip is prompted** (VIDEO-RULINGS V42, 2026-10-26): `SEEDANCE-INPUTS.md`, built by `machine/seedance_prompt.py` from the BytePlus Seedance 2.5 guide — bound picture and voice, one sentence, whole-second windows, constants, two negatives. `clips_run` stores it as the call's `seedance` block and `make_call` sends it whole.
- **Every clip is judged and the best attempt kept** (`machine/clip_judge.py`); one that fails is kept flagged `below_criteria`, not held.
- **The acting reaches the camera** (VIDEO-RULINGS V8, V46): each shot's `face`, `gestures` and `camera_move` go into
  the clip prompt (`machine/seedance_prompt.py`); the `emotion` label does NOT (a strong label overacts). A to-camera
  shot with no visible face or gestures is filled from the emotion bank's camera line or marked not applicable with
  the reason (`machine/acting.py`; the call's `acting`, the plan's `acting_notes`). The line's `delivery_tag` goes to
  the voice only. The person's life marks and gestures come from their `character.md` — a missing section is said in
  the plan. The creative controls reach the clip through the brief (stage 5 v7: the dials and the emotion become
  `face`, `gestures`, camera and timing). The realism index's production rows ride along. Off-camera speech never
  reaches the clip — the listener listens, lips closed.
- **Frames, not scenes: how an AI-route shot is made** (2026-09-18). A scene generates exactly two
  stills — the FIRST FRAME and the LAST FRAME, the last an edit of the
  first with two references and a colour match back to it. What happens
  between them is beats on the clip's own timeline, one verb each, timed
  off the voice track. A beat is never a generated picture.
- **The contract gate** (2026-09-18). Every item is validated against
  `machine/model-inputs.json` — the model input contract — before anything
  submits: a missing required field, a beat with two verbs, a frame with no
  delta, a to-camera scene with no audio slice, more beats than the maker
  takes. Red names the field, and nothing submits red.
- **Scene shapes and mood are bound from the doctrine, not authored
  here** (2026-09-18). `components/marketing-doctrine/` is where a
  technique's scene shape and the mood-building rules live; this machine
  reads them, bound as `{techniques}` and `{mood}`, and never restates
  them in a prompt.

- **The product is never drawn** (the owner, 2026-10-09/10: "all this slop stuff is gone … so we can print ads").
  A hero product's pixels come from the real thing, by shot type: **in use on the face** → a real clip of a
  real person using it from the brand's archive (`product_usage.py` bank → `tools/asset-index`), with our
  cast swapped in by Higgsfield Genjutsu `hf_mult_replace_object` (video + cast master; the real hand, device
  and motion stay); **hand only** → the real archive clip, cut as is; **product-only card** → the brand's own
  studio renders (Drive `products/<product>/cgi/`); **any still that still shows it** → `product_paste.py`
  lays the kit's real turntable photo over the drawn one. The redraw edit (`product_fix.py`) and Kling motion
  control (drops props) are not used for the product. Clips of the product are never made by animating a
  drawn product.
  **A product IN USE whose kit declares `in_use` is DRAWN FROM ITS REAL PICTURES, never pasted over** (the owner,
  2026-10-25, on the image-teardown carousels made this way: "literally 1000000x better than any flex implementation we
  had in the past ... not just statics but also video scenes as well"): `element_refs.bind` gives a held-product still
  the kit's `in_use.refs` (the side the camera sees, a real hold) and `in_use.line`, marks it `in_use`, and the house
  prompt layers, `product_of` and `v2_product_of` skip it. A kit without `in_use` keeps the paste above. The one shared
  definition is the kit's `kit.json`; statics read the same through `tools/image-production` `plain`.
- **A swap is the whole character, never just the face** (the owner, 2026-10-12: "only faces have changed — you need to
  do the entire character, their body build … uploading the entire casting sheet as reference … being very clear
  on his before state and after state"). **Superseded 2026-10-27 (the owner): the person goes in from the cast BASELINE — headshot, look,
  details, expressions — never the master; `cast_swap.refs` sends it and the sheets' `never_send_stems` refuse the master at the door.**
  Earlier wording kept: every Genjutsu swap sends the cast member's FULL sheet as image references
  — master, turnaround, angles-expressions, details, and the look for the shot — and the one standard prompt from
  `machine/cast_swap.py` (`refs` lists the files, `prompt --state before|after` writes the words, `put` uploads).
  The state comes from the brief: BEFORE = the problem on show as the details sheet has it; AFTER = the problem
  gone, everything else, body included, identical. A swap sent with the master alone is a face swap and is redone.
  One person carries the whole ad: every person shot — swipe shot, archive product use, opening — is the same cast
  member; a clip whose swap kept the original person's face, skin or build is dropped, never cut in.
- **Clips play at normal speed** (the owner, 2026-10-12). A clip shorter than its slot plays shorter; the edit never
  slows one down to fill time (the edit's one path, `tools/video-edit/` — `swipe_cut.py` is retired, R6).
- **Recreate the swipe, shot for shot** (the owner, 2026-10-10: "Look at the swipe. We recreate the swipe for our brand.
  That's literally it."). The first source for every shot is the SWIPE SHOT ITSELF (`framemap/shots/Kxx.mp4`),
  run through Genjutsu `hf_mult_replace_object`: their person → our cast master, their product → the real product photo,
  their box/case → the real case photo, their captions removed. Their camera, timing, framing and graphic style carry over.
  A shot whose action is product use the swipe's product cannot do (applying a shampoo) takes the real archive clip of
  our product in use instead; an ingredient montage takes the brand's own product CGI. Talking-to-camera shots stay on the
  lip-sync line with our voice. (Which shots take this SWAP route, and which go REAL or AI, is decided by
  `SHOT-ROUTES.md` alone since 2026-10-20; the old "a generated scene is the last resort" is replaced by it.)
- **AI-route frames are EDITS OF THE SWIPE's own frame** (the owner, 2026-10-20: "we should be using the swipe as the frame
  references the entire way through and just swapping in our elements"; "you are putting in the elements like the
  flowers, bottles … on the images themselves … those elements should be printed on top"). A brief whose piece says
  `"frames": "swipe-edit"` (`machine/element_refs.py` SWIPE_EDIT): image 1 is the swipe frame, then the person's FULL
  casting sheet (master, turnaround, angles-expressions, details, the look) — never the master alone — and the words say
  only what changes: the person, and any item, sticker or on-screen word removed. No prop, plate or packshot is attached;
  items are laid on in the edit as cut-outs. A scene the swipe has no shot for reuses the last swipe frame. Never swap a
  person into OUR generated frames (a generation of a generation reads as AI).
- **Then the swipe's look** (`machine/swipe_look.py <run>`, the owner: "the quality literally matches the swipe"), once, after
  every frame is made and before any clip: each channel moved toward the swipe frame along a straight line (never a
  histogram remap — it posterised a face), saturation back to the swipe's, the face lifted by the swipe's face-to-room
  light, the swipe's width, softness, grain and compression. Originals kept as `media/versions/<id>-before-swipe-look.png`.
- **A cast member built from an AI picture keeps its gloss.** Real skin comes from a real reference (Yai's sheet); a cast
  made from an AI element gets one realism edit on its start pictures ("a real, unedited iPhone front-camera frame") before
  the swipe look.
- **Every clip's words checked word by word, not by a score** (2026-10-20): a take at 91% "match" added words that are not in
  the script. A clip whose first word comes before its mouth moves (speech in the first ~0.5 s) is remade. `V2_EXTRA_TAKES=<clip>`
  gives one more paid take over v2's cap, for that run only, on the owner's word.

## Real human movement in every clip with a person (2026-10-28)

A clip with a person on screen used to get NO motion video (the swipe's
pieces are dropped to lock the picture), so the model invented movement from one still. Now `clips_run.plan` gives such
a call one entry from `movement-bank.json`, picked by what its scenes do (`machine/movement.py`), cut to the call's length
with no sound, no colour and a little softness, and bound in the prompt as movement only: the head, neck, face and arms
move like a real person, the hands go where the prompt says. The bank holds REAL footage only (our own creators' raw
takes), never AI output, and never the swipe when the swipe may be AI-made. Add entries to grow it.
A clip whose speech doubles a word the line says once ("45, 45") now fails its word check as `REPEAT` and is made again.
**Beats on their words** (same day: *"switching her hand … before she even mentions the right side"*): a talking
clip's timeline is the brief's beats, each starting when the words it is written `over` start (placed inside the line's
window on the call's clock, `seedance_prompt.cued`), never even time slots; a beat over no words follows the words
before it, and an effect's own beat is left to the edit. A press on the board starts a new round of takes
(`clips_run.make_clip`): takes already on disk are never re-judged as this round's.

## Scene clips on the board, end to end (2026-10-28)

**Superseded 2026-10-28 for kept clips (L-57, `providers.json` `upscale_on_keep: false`): a kept take is the clip as made; camera moves and sharpening are the video editor's, after the hand-off.** Earlier wording kept: the camera moves are PLANNED by the chain (`camera_moves.py plan <run>`: a cheap vision read of each section's start
picture picks which beats, by their words, earn a push-in and where) and CUT INTO THE KEPT CLIP (`camera_on_kept`,
on the chain's pick and on a person's **Keep this take** on the board). Every scene starts and ends on the full frame
(*"each scene is a loop within itself"*). A take refused on content safety with a real person's movement attached is
made again without it; a line under 2 s is padded with silence to the model's 2 s audio minimum; a press on the board
always makes a new round; the clip ledger re-reads under a file lock on every write (two jobs had wiped each other).

## Camera moves: punch-ins timed to the words (2026-10-28)

A finished take gets
lens-style push-ins with no regeneration: `machine/camera_moves.py <run> <scene id> [take]` reads the run's
`camera-moves.json` (per scene: `on`/`until` words from the take's own transcript, `to` = the point in frame,
`zoom`) and writes `clips/calls/<call>/moves/<take>.mp4` beside the take; the board shows it first on the scene card.
**Glide, never snap** : the camera
follows its aim through two critically damped springs (`GLIDE`), starts `LEAD` before the word, pans straight across
between moves closer than `MERGE` instead of pulling out, keeps creeping in while it holds (`CREEP`), drifts slowly at
rest (`DRIFT`) and never pulls out in a take's last moment.
Open: the moves are written from the brief's gestures by hand today; the point should come from a judge reading
the start picture.

## Every shot: built, lit and printed in 3D, then made real, then the lens (2026-10-28)

*"you need to set up 3D cameras and stand-ins for each shot ... the next runs we do are just consistent ... a function of
input and output. Not subjectivity."* A shot's start picture is made in this order, every run:

1. **A scene is one swipe cut** (`storyboard_plan.py`); its swaps come from the brief (`shot_swaps.py`), never a new concept.
2. **The shot set** (`shot_sets.py`): per place and per swipe camera (the frame map's `camera`), ONE 3D set in Higgsfield 3D
   Jutsu — the swipe's camera, the counter, a grey stand-in on her mark, the window key, rim, haze — rendered empty and with
   the stand-in, the empty render printed into a real room with its light kept, the light written as facts
   (`sets/<camera>/` under the person's 3D room). Shots that share a camera share the set: `shot_sets.py link`. `plan` says
   which sets a run needs; `bpy` and `prompt` print the scene code and the print words; `put` files the result.
3. **The picture** (image production, model-inputs `preview.py`): the printed room is the room picture, the stand-in is
   the light guide, the light goes in as THE LIGHT ON HER, everything takes the room's light.
4. **Made real, then the lens** (`preview.finish_people`): a skin-only realism pass with her headshot, then the medium's
   lens (`model-inputs/lenses.json`, default iPhone 15).

The why, with sources: `tools/image-production/research/movie-level-depth.md`.

## Gates — what holds failing work (listed 2026-09-20)

Nothing here is new except the last row; this is the one place they are all
named. A gate REFUSES — red names the item and what to do, and nothing submits
or ships past it.

| gate | where | what it holds |
|---|---|---|
| **The swipe match** (2026-09-24) | `run.py start`, first, `--dry-run` included — the stamp is written by `tools/video-teardown/machine/swipe_match.py` | a brief whose first line is not `swipe-match: PASSED` — held for changing the swipe's places, people, camera or order, never checked, or edited after its check (binding the cast is not an edit). the owner: "THE WHOLE POINT IS TO TAKE A SWIPE AND ADAPT, not ruin it." Only `--composed` (a brief made with no swipe) skips it |
| **The manifest** (2026-09-24) | `run.py start`, right after the swipe match — re-checks the teardown run's manifest (`tools/video-teardown/machine/manifest.py`) and reads its last line | a brief whose `MANIFEST:` line is not COMPLETE for this exact brief: a swipe core element or load-bearing item not carried, an element not banked, a price not in the brand's files, or no manifest at all. the owner: "i do not have time to babysit this anymore" |
| **the owner read it — REMOVED 2026-10-27** (the brief carries `brief-read: APPROVED by the system` as soon as the swipe check passes, tied to its fingerprint, `swipe_match.py` `check`). Earlier wording kept: (2026-09-24) | `run.py start`, after the manifest | a brief without `brief-read: APPROVED` for this exact brief — "i always need to see a written brief before moving on to the production stage" |
| **The production gate** (2026-09-23) | `model_inputs.production_gate`, run by `run.py start` right after the brief is read — before the voice, `--dry-run` included | a scene that does not say `to_camera` (refused by id — it used to default to talking whenever the scene had a voice, which is how a B-roll shot became a face); a card whose plate has words in it or that has no `lines`; a row of the swipe's make-list (`roll_sheet`, or the view's ROLL SHEET CHECK table) that maps to no scene and gives no drop reason, names a scene that does not exist, or lands on the wrong kind (a B row must be a `to_camera: false` scene, a C row a card). A brief with no roll sheet (written before v13) is WARNED, never refused; a card line carrying `[UNFILLED]` is warned. The same card and roll-sheet checks run again as preflight rule 12. **Every element (2026-09-23, `ELEMENTS.md`, brief v14):** a `kind` that disagrees with `to_camera`; a screen, split side, greenscreen background or endcard plate with quoted words or one of its own lines in it; a screen `surface`, split/greenscreen `layout`, annotation/platform_ui/transition kind or `music.energy` off its list (enums in `model-inputs.json` → `elements`); a scene `section` that is not a marketing-doctrine section id, or a piece `framework` that is not an ad-framework id nor `observed — …` (both READ from `components/marketing-doctrine/` at run time, never listed here; brief v15 — v14's `module` is a warned alias for a missing section only); `priority` outside 1–3; `opens` on no scene or on two; a greenscreen whose `talker_scene` is missing or not to camera; an endcard offer line or guarantee not found in `brands/<brand>/products/offer-bank.md` (an `[UNFILLED]` one is warned); an endcard with no product the brand holds a real packshot for; a layer, sfx cue or hook naming a scene that does not exist. Roll-sheet `S/X/G/E` rows must land on screen / split / greenscreen / endcard |
| **The banks** (2026-09-23) | `machine/banks.py`, run by `run.py start` right after the production gate — `--dry-run` included | a brief whose `music` or an `sfx` cue has no MADE row in `banks/<bank>/index.json` — refused naming the row (or saying none exists) and the `make_bank.py` line that makes it; never a silent fallback. A fitting row writes `{bank_id, file}` into `plan.json`. `--banks <folder>` points at another bank |
| **The elements lock** (2026-09-23; **no personal confirm since 2026-10-27**, : every element banked and every check green locks itself, `elements_check.py` `gate`; `VP_REUSED_AUTO=0` restores the manual lock) | `machine/elements_check.py`, run by `run.py start` right after the banks, before the voice — `--dry-run` reports, a real run refuses | every person, look, voice, setting, product and prop the brief (v17) names must be BANKED to `elements-standard.json` — documented (`character.md`/`set.md`/…, `provenance.json` checked field by field) and made FROM A REAL REFERENCE — and a scene with words must name its `speaker`, who must have their OWN voice. Anything short is refused by name and listed in `<run>/elements.json` as the make-list; all banked but not confirmed is refused until `elements_check.py confirm <run> --by the owner` writes `elements-lock.json` (a fingerprint of every file in every element folder — change one and confirm again). People are made with `machine/make_character.py`, which refuses a spec with no real reference or no adjustments, a product in a cast sheet, or a reference shared with a banked person. Generated elements live in `runs/ai-elements/<brand>/` (casting/, sets/, props/) — never `brands/` (`machine/element_paths.py`). The standard: `PRODUCTION-ELEMENTS.md` |
| **Our own footage first** (2026-10-05) | `machine/footage.py` `gate()`, run by `run.py start` right after the banks — before the elements lock, the voice and any still or clip — `--dry-run` included; `--no-footage` skips it | every B-roll scene (`to_camera: false`, not the presenter, not a card / screen / split / greenscreen / endcard) is looked up in the brand's indexed footage on the company Shared Assets drive — locally, no service (`tools/asset-index/machine/search.py`, the Shared Assets map from `shared_paths.py`). A confident match (score ≥ 0.42, the ACTION itself matched, every named product — NOVA™, PRIME™ — in the clip) is CUT: `source_plan: cut`, `owned_file` + `owned_in`/`owned_out`, and no still or clip is made for it (the storyboard frames and the clip planners skip it). Every other B-roll scene is generated and carries its nearest real clip's frame in its first frame's `refs` (`footage_ref`). Prints cut / generate / presenter and the credits not spent. **The presenter is never the library's** (2026-09-11): a to-camera or type-A beat, or a scene that does not say, is never matched. the owner: "whatever needs to be generated, we can just generate." The same pass at the brief: `footage.py --brief <5-brief.md> --brand <b>` writes `footage.json` + `footage.md` beside it. Tests: `test_footage.py` |
| **Preflight** | `machine/preflight.py check` — rules 1–12 | a batch before it is submitted: a person or product with no reference, post effects in a prompt, a start image that is not a verified frame, a model the provider does not offer, a batch over the cap, a line claimed twice, an unknown or deprecated format (rule 9, the local `formats/bank.json`), no no-cut line, and the model input contract (rule 12) |
| **Still QC** (the inspector) | `prompts/stage-5-qc/` → `preflight.py verdict --layer inspector`, then `preflight.py verify` | a still that is not the scene specified; an unverified frame never goes to motion (rule 6) |
| **Motion QC** | `prompts/stage-5b-motion-qc/` → `verdict --layer motion` | a clip that did not do what the beats said |
| **The subject zone** (2026-09-23) | `machine/safezone.py`, run by `run.py start` on every still the machine makes, before any clip is made from it; `preflight.py coverage` at `pack` | a first/last frame, plate or packshot whose face, product or hands cross out of the centred 4:5 zone of the 9:16 frame — one fix edit (frame first, cast sheet second, the one change), measured again; still outside → HELD, no clip made from it, `pack` refuses. A frame the judge could not measure is UNCHECKED and not shippable either. Records `subject_box` per frame in `direct.json` and `plan.json` for the edit. Mid-clip drift: Motion QC check 7 (v2) |
| **Director** | `prompts/stage-5c-director/` → `verdict --layer director` | a clip that will not stop a thumb; two FLAGs on one item is a weak concept, sent back to the script |
| **The audio gate** (2026-09-23) | `machine/audiocheck.py`, run by `run.py start` right after the voice, before any frame | a voice slice that says other words, stops before its line finishes, or is silent/clipping — remade once (voice only), then the run STOPS before a picture is paid for; volume drift between scenes is reported as a warning. the owner: the script and the audio drive the video. Before the gate, `voice.py` sets every scene's slice to the same loudness (−16 LUFS, one linear gain — volume only, delivery untouched; the first pilot drifted 17 LU scene to scene) |
| **The song gate** (2026-09-23) | `machine/song.py`, run by `run.py start` right after the audio gate, before any frame — only when the plan's `song` has sections (`SONG-CHAIN.md`) | BEFORE the call, dry run included: a sung line that is not a line of the script (the scenes' `lyrics`), a script line no section sings, a `style_id` that is not an APPROVED row of `banks/music-styles/index.json` (rule 6; `ruled` until 2026-10-07), a vocal the row does not sing, a section the row has no line for, a section outside 3–120 s. AFTER it: the song is transcribed and every section's lines must be heard in order (match ≥ 0.75, `providers.json gates.song_lines`) and the last line must finish — a failing take is made once more (same request, next seed), then the run STOPS naming the missing line. Writes `song/request.json`, `song.mp3` (never overwritten), `timing.json`, a −14 LUFS copy |
| **Protected words and numbers** (2026-09-23) | `machine/lexicon.py` + `machine/spoken_numbers.py`, inside the audio gate and the song gate (`VOICE-CHAIN.md` steps 4a–4b and 7) | BEFORE the call: every word of `brands/<brand>/brand-identity/voice/pronunciation.json` (brand, product, ingredient, mechanism) is swapped for how it is said, and every figure is said in words by `machine/spoken-rules.json`; ElevenLabs' own guessing is off (`apply_text_normalization: off`, seed pinned). The script and the captions keep the real spelling. AFTER it: a protected word not heard (real spelling, ≥ 0.85, `providers.json gates.protected_words`) or a figure not heard as its words is remade once (voice only, next seed), then the run STOPS naming the word. A word nobody has confirmed by ear is a WARNING naming it. Hear the words: `machine/say_it.py <brand>` |
| **Line parity** | `machine/lineparity.py`, run by `run.py record` | a talking clip that says other words than its line |
| **The line finished** (2026-09-23) | `lineparity.ending_heard`, same call | a talking clip whose line's last words are not heard at its end — CUT_OFF, whatever its overall match; `record` writes `<run>/remakes/<scene>-r1.json` and the `remake-clip` skill remakes only the broken element |
| **The face gate** (2026-10-23) | `machine/face_gate.py`, called by every clip door — `seedance.py talk/motion`, `run.py`, `drain.py`, `clips_run.make_call` | a picture of a person whose face has not passed against their banked master (`<picture>.faces.json`, tied to the picture's bytes): DIFFERENT or unanswered refuses the clip, named, before anything spends; a hand-made clip must name each person's master (`--master`) or say `--no-people`. The face check was print-only until a different man played Marcus in four scenes (the owner: "establish a fix in the chain for this"). A crowd element (the judge reads its spec's own words) comes back GROUP and passes; a person seen from behind is judged by head, hair, skin and build; of the three versions of a picture, one whose face failed is never kept over one that passed (2026-10-24). Tests: `test_face_gate.py`, `test_v2_rulings.py` |
| **The clip gate** (2026-10-09) | `machine/clip_gate.py`, run by `clips_run.py run` before any clip spends, and its count after | a clip whose picture or its person's face lineup is not approved as it is now, whose picture carries the swipe's words in none of our files, whose after-the-routine prompt still describes the spots, whose shown prompt is not the sent one, whose reference path is gone, or whose exact request was refused before, or whose picture shows slop a viewer would notice (a misspelt brand/product name, big text that is not words); after the run, frames of every new clip are read for the same slop, and a planned clip not made leaves it INCOMPLETE, named. Every check is a fault from the Grandma TV-shopping clips. Tests: `test_clip_gate.py` |
| **Coverage** | `preflight.py coverage`, run by `run.py pack` | a pack with a line uncovered or doubled, or a clip missing its motion, director or parity verdict |
| **The element library** (new 2026-09-20) | `machine/library_check.py`, preflight **rule 13** | a `format` that is not a `format/video` row in `components/elements` — and a row that exists there only as a name (`[TO DEFINE …`) is refused as **named but not defined yet**; a `style_id` that is not a `style/video` row; a scene delivery dial (`humor`, `style`, `register`, `pacing`) whose value is not on its `delivery/<dial>` list. Every refusal names the real ids. `unfilled` and empty dials are passed over. Asked on every run that uses the real bank; a run on another `--bank` is asked only when it also names `--library`. If the library cannot be read, preflight WARNS and falls back to the bank alone |

**A new format is two steps now.** Write it into `formats/bank.json` from the
template, then rebuild the library (`python3 components/elements/machine/elements.py
build`) — until then rule 13 refuses it and says exactly that.

The piece's `style` is a grade sentence, not an id, and is never asked about —
a look that IS an id goes in `style_id` (run.json, or the brief's `piece`).

## The variation chain — where scale actually comes from (2026-09-02)

One approved production feeds unlimited variations. That is the multiplier:
the expensive part (deciding the film, casting it, proving it) is paid once,
and every restyle after it is cheap.

    an APPROVED production
        └── v0 style gate → v1 formula → v2 convert assets → v3 RESTYLE
            → v4 generate → v5 QC → v6 assemble          × every style

**A variation is not a new film.** Screenplay, blocking, dialogue,
mechanics and edit are frozen; only the rendering swaps. `method-05-format-
variation.md` is the doctrine, written from a real run — including its two
recorded failures, which the chain is shaped to prevent:

- **Re-planning.** Handing approved prompts to a model to "restyle" made it
  re-plan the film — new framing, paraphrased dialogue — and the result read
  as a different film. So **stage v3 is not a model.** `machine/restyle.py`
  does exactly three mechanical things (style lock prepended · media swapped
  · photoreal descriptors stripped) and prints its own diff, so the
  guarantee that every approved word survived is auditable.
- **Re-describing.** Generating a "new base" from a text description
  produced people who were not the approved cast, and a product that was
  not the real product. So v2 converts FROM the refined source — the trained
  identity, the approved plate, the real packshot — and marks any asset with
  no source `⚠ NO SOURCE` rather than inventing one.

**The axis distinction, because it decides which chain runs.** A variation
changes how the film LOOKS. Changing the avatar, the problem or the angle
changes what the film SAYS — that is a new production through stage 0b with
different inputs, not a variation. Both scale; they are not the same lever
and conflating them is how a "variation" quietly becomes a remake.

## Frames are made by EDITING (ruled 2026-09-02)

**An edit instruction must never describe anything the source image already
shows.** The seed still already holds the framing, blocking, room, light and
pose; describing them again tells the model to rebuild them, which is the
generation we were escaping. Measured on one scene: 4,262 characters of
self-contradicting description → 204–386 characters of delta, and text
rendered legibly for the first time.

The chain, on the owner's call: **image teardown to UNDERSTAND the frame
(stages 1–2 of `tools/image-teardown`), then that understanding as the
reference for the edit** — keep what the replication spec calls
load-bearing, change what it calls swappable. The frames stage stops
guessing who is in the picture and reads it.

**Type is a layer, never a generation.** Generate a clean plate; compose the
words on top (`image-teardown/tools/compose.py`). Text cannot garble, copy
stays editable, and one plate carries every hook variation.

**B-roll and cards are made HERE, not in the edit** (the owner, 2026-09-23: B-roll
"literally has nothing to do with editing" — it is ideated from the swipe and
made at production; "clean up each stage properly so the next stage is able
to just do what it's supposed to do"). The AI brief (stage 5 ai-lane, v13)
details the A-roll first, then a headed B-ROLL section, then CARDS, then a
roll-sheet check — but its block stays ONE scene list in play order. Every
scene carries `to_camera` explicitly; a shot that cuts away from the speaker
is its own `to_camera: false` scene covering its slice of the voice, never a
line inside a talking scene. A **card** is a scene of `kind: "card"`: this
machine makes its **plate** — the picture with no words in it — as ONE still
(`<scene>-PLATE`, the still-generate door, the contract's clean line appended)
and no clip; its exact words, the moment they land on and their sound travel
in `plan.json` as `scene.card = {plate, lines, lands_on, sfx, refs}` for the
edit to set on top. Production makes every picture; the edit only composes
type.

**Every element of a video** (the owner, 2026-09-23: "all these elements need to
be green"; the contract is `ELEMENTS.md`, the brief that writes it is v15).
Every scene names its `kind`, `opens`, `section` (a marketing-doctrine section
id, the unit a version swaps) and `priority`, and the piece its `framework`
(an ad-framework id); v14's `module` is retired, read only as a warned alias; the four new
kinds nest their fields under the kind's own name. What this machine makes:

| kind | items | carried for the edit |
|---|---|---|
| `screen` | `<S>-PLATE` — one text-free still, no clip | `screen: {surface, lines, lands_on}` |
| `split` | per side (`<S>-L`, `<S>-R`): a first frame, a last frame, one silent clip — the B-roll path; the paragraph laid under the left once | `split: {of, side, layout, labels}` on each |
| `greenscreen` | a normal talking scene (F1 · FLAST · talking clip) **plus** `<S>-BG`, one text-free background still | `greenscreen: {talker_scene, layout}` |
| `endcard` | `<S>-PACKSHOT` — an EDIT (fidelity door) of the brand's REAL packshot, never a product drawn from words; the run stops if the photo is not on the machine | `endcard: {offer_lines, cta, guarantee}` |

`layers`, `hooks`, the piece's `framework`, and every scene's
`section / opens / priority` go into `plan.json` untouched. `music` and each `sfx` cue are picked from the banks
(`banks/`, see its README) and gain `{bank_id, file}`. Every clip that lands
— on the machine hand or at `record` — is colour-matched to the piece's first
frame (`colour_match.match_clip`, ffmpeg, the original archived as
`media/versions/<id>-precolour.mp4`; `--no-clip-colour` turns it off).
Fixture: `machine/fixtures/brief-v15.md`, one scene of every kind
(`brief-v14.md` is kept as the retired `module` shape the gate catches); tests:
`machine/test_elements.py`.

Full account, with the numbers and the three defects that hid inside
"edit": `frames-by-edit.md`.

## Formats vs building the avatar — keep these apart (2026-09-03)

**Building a character is its own process**, done once per person, living
in `runs/ai-elements/<brand>/casting/<name>/` (`machine/element_paths.py`
`casting_home`; a person banked before 2026-09-23 may still sit at
`brands/<brand>/ai-elements/characters/<name>/`, read as the fallback). A FORMAT consumes a character and
never makes one: it takes that character's master and the skin crops
from their own boards as references. Same cast serves a song ad, a micro-drama and a demonstration
with no rework. See `building-the-cast.md`.

## How a song ad actually gets built (worked 2026-09-03)

`formats/song-ad.md` is the profile; the exact calls from its two runs are
the provider pages, `archive/fal.md` and `archive/higgsfield.md` —
written from a real end-to-end run with the owner: words first, record the song
and KEEP THE TIMING SHEET, cast from the AI cast and use what the character
already has, one call per shot with references doing the work, ask for the
phone-camera look explicitly, animate only approved stills, cut to the
lyric timings.

**The rule underneath all of it: a reference beats a description.** Every
failure that day was something written in words that should have been
pointed at with a picture — the person, the skin, the scene, the style.

**Motion is 94% of the cost** (~62¢ a clip against ~4¢ a still), which is
why stills are approved before anything moves. A 30-second ad is about $4.

## Scene by scene on the board — what every scene now gets (the owner's Tella reviews, 2026-10-28)

Each rule is a row in `components/model-inputs/lessons.json` (L-50 to L-62) naming the line that applies it.

**The whole process, stage by stage on the board, from the brief to the editor's hand-off: `VIDEO-PROCESS.md`.**

- **The swipe, broken down** (`machine/scene_breakdown.py`, prompt `prompts/v2/scene-breakdown-v2-owner.md`): every
  swipe scene read to its smallest elements; the camera's hand drift is MEASURED on the frames, never read. The clip
  prompt carries the camera, the eyes, how things are handled and the atmosphere, never the swipe's own objects.
- **Props make physical sense, the action lands on its object, the movement bar** (`machine/seedance_prompt.py`
  `PHYSICAL`, `MOTION`): stated in every clip.
- **The same object all the way through, props in reach** (`machine/shot_swaps.py`): an object an earlier approved scene
  drew comes from that scene's picture; a prop the person picks up later is already in the start picture, within reach.
- **The body check** (`machine/body_check.py`, prompt `prompts/v2/body-check-v1-owner.md`): every start picture and
  every take, each hand traced to a shoulder, two reads that must agree; a wrong body fails a take and the board remakes
  a wrong picture by itself, up to twice, before a person sees it.
- **The clip judge v4** (`prompts/v2/clip-judge-v4-owner.md`): props, the right object, the voice, the swipe's elements.
- **One take per board press, the voice measured, no silent backup for a talking clip, no camera moves and no upscale
  on keep** (`machine/clips_run.py`, `providers.json` `max_tries` 1, `upscale_on_keep` false): the person decides on
  the board; camera moves and sharpening wait for the edit and the hand-off.
- **Effects are drawn on our own scene's object, in the swipe's style, and upscaled** (`machine/effects.py`).
- The writing chain carries the same rules from the brief on (`video-writing/prompts/v2/stage5-ai-brief-v9-owner.md`).

## What is in this folder

**The live method docs** — how the work is actually done today:

| | |
|---|---|
| `SCENE-GENERATION.md` | **how a scene is generated, end to end** — what a scene is, the six steps in order, the four-block prompt with the call that worked, what the gate refuses |
| `frames-by-edit.md` | how a frame is made. The core finding: a reference beats a description |
| `building-the-cast.md` | how a character is built. **Its own process, not a format** — done once per person, serves every format |
| `format-variation.md` | restyling an approved piece into a new visual format |
| `handoff-and-edit.md` | what the editor receives |
| `BRIEF-SPEC.md` | the brief shape, ruled 2026-09-14 |
| `PLATE-CHECK.md` | every still judged by measurement before anyone sees it |
| `AI-CREATIVE-LINE.md` | the story of the whole line, swipe to motion |

**`formats/`** — the bank: one profile per format (`bank.json` +
`TEMPLATE.md`), `RUN-PROTOCOL.md` is the one run every format follows.

**`providers/`** — the `research/` dossiers. The old door pages (`MODEL-HOUSE.md`, `fal.md`, `higgsfield.md`) are in `archive/`; which model does what is `components/generative-model-house/MODEL-HOUSE.md`.

**The machine** — `machine/`, `prompts/`, `chain_config.json`.

**`ROADMAP.md`** — the plan; three legs, in order.

**Stale, kept for history** — see `archive/README.md` for what moved there
and what superseded each piece.

## Files

- Output lands at `runs/video-production/<brand>/<label>/` per `runs/README.md`
  (2026-09-17).
- `prompts/` — one folder per stage; the CURRENT prompt files live at the
  top, versioned in the filename (`...-v2-owner.md`). **Never edit a prompt
  in place** — a change is a new file with a bumped version; retired
  versions move to `archive/` inside the stage folder. The board renders
  whatever is current.
- `machine/` — the one runner and its doors:
  - **`run.py` — the one command**: `start · record · pack`. `start` makes
    every station directly (the one hand, 2026-09-18) into `media/` +
    `direct.json`; `record --direct` runs line parity and the ledger;
    `pack` finishes. A house is used only when `--provider` forces one.
  - **The two audio chains** (2026-09-23): `VOICE-CHAIN.md` (the voice-over,
    `voice.py` → `audiocheck.py`) and `SONG-CHAIN.md` (the sung piece,
    `song.py` → the song gate; style rows in `banks/music-styles/`; tests
    `test_song.py`).
  - **The direct doors**: `voice.py` (ElevenLabs), `song.py` (ElevenLabs
    Music, the song), `direct_openai.py`
    (cast/stills), `direct_google.py` (edits; the Lyria song alternate), `seedance.py` (every clip: a talking
    clip sends the picture and the locked read in one call, a silent clip the picture), `direct_byteplus.py`
    (Seedance direct — wired, blocked on US billing). `clip_kit.py` holds the small shared helpers (ffmpeg, the run folder names).
  - **The contract** (2026-09-18): `model-inputs.json` — per station on
    the settled doors, the exact request fields, the order the maker wants
    the prompt assembled in, its limits, and which of our scene and frame
    fields fills each one, every row carrying the doc it was read from.
    `model_inputs.py` is the one reader (it assembles every prompt and
    runs the gate), `render_model_inputs.py` prints it as `MODEL-INPUTS.md`
    so a prompt can READ the contract instead of restating it, and
    `colour_match.py` holds every edit to the frame it came from.
  - **The gate code** (provider-neutral): `provider_platform.py` (the plan, the
    doors), `preflight.py` (check · verify · ledger · coverage · verdict),
    `library_check.py` (rule 13 — the element library is asked),
    `lineparity.py` (every talking clip says its line), `providers.json`
    (the only place a model slug, a URL or a request shape lives — with
    `_history` for superseded door rulings), `deliver.py` (the naming
    gate). Tests: `test_run.py`, `test_preflight.py`, `test_direct.py`,
    `test_direct_byteplus.py`, `test_voice.py`, `test_lineparity.py`,
    `test_frames.py` (the scene shape and the contract gate),
    `test_rollout.py` (the library rule, the cast per brand, the v2 prompts),
    `test_elements.py` (every element kind, the banks, clip colour).
  - **The banks** (2026-09-23): `banks.py` picks music and sfx rows,
    `make_bank.py` would make the missing ones on ElevenLabs (Sound Effects,
    Music — `--dry-run` only until a spend is approved), `brandfiles.py`
    reads the offer bank and the real packshot the same way image-production
    does.
  - **The by-hand tools stay, updated to the doors** (the owner, 2026-09-18:
    "we need chains and such… make updates to the tools, not remove
    them"): `board.py` (:8456) — pressing Generate now starts
    `drain.py`, which makes the take on the direct doors (frame on GPT
    Image → line on the cloned voice → Seedance with both; cutaway → Seedance
    silent) and writes it back where the board looks; `chain.py`,
    `pull.py` (for a take that comes back from a house as a URL),
    `ship.py`, `storyboard.py`, `briefs.py`, `pipeline.py` unchanged in
    role. They are the owner's surfaces and never move without his word.

## Where brand context lives (the owner's ruling, 2026-08-30)

Brand data NEVER lives inside the machine. It lives in
`brands/<brand>/` (the one brand home since 2026-09-02; `lab/owner/brands/`
is gone) — products (one folder per product: product.md + images/ + Drive
links), core-avatars, intake (was existing-content). The cast LIST is brand
info under `ai-elements/characters/casting/`; each person's own files are
generated work under `runs/ai-elements/<brand>/casting/<name>/`. The machine
pulls from there by the run's `brand` field. The
<brand> folder is the structural baseline; a product file is what the
thing IS — offers live in the brand's offer-bank.

## Rules for working here

1. Agnostic on every axis, everywhere except the evidence files: model-,
   brand-, product- and avatar-agnostic (the owner, 2026-08-30 — we are
   building a system; it must run on any content for any brand).
   Stations are slots with audition criteria; a model earns a slot by
   passing the audition, never by name in the process docs.
2. **The live board is the owner's working surface** (his ruling 2026-08-30):
   today that is the Cinema line's board (`machine/board.py`, :8456) for a
   run — the cast, the prompts, the plain-words redo box — and the run
   record (`media/`, `direct.json`, `verdicts.json`) beside it. The artifact
   **The Road to $10** ((private page))
   is the shareable picture of the cost story; **The Video Machine** (see
   `lab/owner/context/artifacts.md`) is how this system is set up and the
   roadmap — that old link is dead, and this is the live one.
3. Stage files may name candidate models under "candidates" — that's where
   model specifics belong, marked proven/testing/rejected.

## The four questions

Answered 2026-09-23, when this folder owed them as a resident
(`components/CLAUDE.md`). It moved out of `lab/owner/ai-video-production/`
on the owner's word, 2026-09-22.

- **Engine + owner:** `machine/run.py` is the one runner —
  `start` (brief or plan in, the twelve gates, the provider picks the models,
  a forced Higgsfield run hands the editor a submit sheet),
  then `record` and `pack`. Around it: `prompt.py` and `promptify.py`,
  `voice.py` (the read, stitched on the previous request ids so a remake still
  sounds continuous), `elements.py`, `scenes.py`, `preflight.py`,
  `deliver.py`, `drain.py`, `board.py`. `styles/` renders the board.
  **the owner.**
- **Definitions + curator:** the format bank at `formats/bank.json` with a
  document per format, `chain_config.json`, the prompts under `prompts/`,
  and the provider tables under `archive/` and `components/generative-model-house/`. **the owner.** Brand context is
  read from `brands/<brand>/` and never restated here.
  `styles/bank.json` is an element-library source (`components/elements/sources.json`
  builds `style/video` from it), as `formats/bank.json` is for `format/video` (SI-135 (elements rows truthful)).
- **The plane it emits:** `runs/video-production/<brand>/<label>/` on both
  planes — the run record, the stage records, the prompt as sent, and
  `deliverable/`, and `runs/video-production/_system/` for its two generated pages
  (style board, pipeline view), ignored by git — SI-57 (production pages home),
  2026-10-08. Media mirrors to `Shared Assets/runs/video-production/...`;
  workspace rule 3 keeps it out of git. **The runs folder and the component
  carry one name, video-production** (the owner, 2026-09-30: "naming needs to be
  lined up cleanly across all the tools"); it was `runs/video-machine/` until
  then, and every record moved with it.
- **Manifest per entry:** `run.json`, with the gate verdicts beside it. A
  failing gate HOLDS the run; it does not ship the work flagged.

**A LIBRARY — the public surface** (the team, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line). Besides the runner, other components load these `machine/` files by path or with `machine/` on the path, and may use only these names:
1. **Commands:** `machine/run.py start|record|pack` (above); `machine/edit.py <run> --scene <N> --change|--show [--dry]`; `machine/remake.py status|order|voice|record <run>`; `machine/footage.py`, `machine/storyboard.py`, `machine/assemble.py <run>`.
2. **The writing station's helpers** (video-teardown calls them): `slotfill.fill(brief, brand, product, call=, dry_run=)` → the fill record; `slotfill.brand_files(brand, product)` → `{name: text}`; `slotfill.research_call(prompt)` → text; `claimfix.fix(brief, brand, product, call=)` → `[{…}]` fixes; `sectionfit.plan_of(src)` → plan, `sectionfit.check(plan, out_dir, call=, dry_run=)` → result, `sectionfit.relabel(brief, res)` → `[str]`.
3. **The brief contract and checks:** `model_inputs.brief_violations(doc)` → `[str]`; `storyboard_plan.swipe_carry(brief_path, teardown_run)` → `[{finding, …}]` (F-numbers); `elements_check.sheet(brief_text, brand)` → `{items: […]}`.
**A second still family, on purpose:** `machine/direct_openai.py` is video-production's own stills door beside image-production — scene stills and frame fixes go straight to the provider here, and email-production's `simple_email.py` loads it by path; it is declared in item 4 below (2026-10-08, A-rule-second-still-family option (b), B4a (decide-now cards) card 11: the team, relayed verbatim by ◆ PLAN [1cc25f] before 04:52:41Z; the owner told after). video-production#11 closes on this line.

4. **Doors and utilities:** `direct_openai.cfg()` → provider config, `direct_openai.generate(prompt, references, out)`; `element_paths.casting_root|casting_home|cast_list|product_home(brand, …)` → `Path`; `clip_qc.frames(video, folder, fps=)`, `clip_qc.faces(folder)` → `[{x, y, w, h, open}]`; `clip_kit.CRISP` → the ffmpeg voice finish.
5. **Read by path:** `formats/bank.json` and `banks/<bank>/index.json` (+ the bank files it names).
Everything else in `machine/` is internal and may change without notice.

**Keys:** `ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`BYTEPLUS_API_KEY` — by name through the shared key loader: the environment, then this repo's `.env` (add `NAME=value` there), then the owner's Mac Keychain when present.

**One correction worth carrying**, found 2026-09-23: `machine/run.py` counted
its way to the workspace root from the depth it had in `lab/owner/`, so after
the move `DEFAULT_RUNS_ROOT` pointed at `~/Projects/runs` — outside the
repo, outside git, outside Drive — and the mkdir would have created it. Every
path here walks up now. **Paths are found, never counted.**

**Its runs are not consolidated yet.** There are three roots, not one:
`runs/video-production/` (the standard), this folder's own `runs/`, and
`machine/runs/`. `briefs.py` is the board and it parses the brand out of the
folder NAME, which the root layout puts one level up; `board.py` still assumes
the old file layout (`cinema/`, `rushes/`, `out/plan.json`) that none of
the root runs has. That is a card with real scope, not a tidy-up.

## Two things that are open, not settled

- **The Drive carve-out (O9).** The media stayed on Drive at its lab path when
  the code moved into `components/`, so the mirror above still reads as a lab
  path. The standing ruling is that Drive is reached by fileId through the API,
  not by the mounted folder. Migrating is its own card; until it lands, the lab
  path is deliberate, and this file says so rather than leaving it to look like
  an oversight. The mount is found through
  `components/brandpath/drive_index.py` mount(), never an account path
  (SI-44 (video mount helper)).
- **A records adapter (O12): none yet.** The convention allows "an adapter or
  'none yet' stated"; this states it. Worth knowing for whoever builds one:
  `chain_records.py` is cheap because it did not mint a kind — it files onto an
  existing one and distinguishes itself with a single constant. One shared kind
  behind one adapter is 50–100 lines per component; a kind of its own is
  450–650 plus a manifest plus worker wiring.

## Opening variations of an approved cut (2026-10-28)

`machine/hook_variations.py prepare RUN --edit EDIT --matrix MATRIX --batch hooks-v2` creates
isolated opening runs. Public functions: `prepare`, `specifications`, `plan_clip`, `make_opening`.
The matrix supplies the full moving scroll event and thumbnail independently; thumbnail-only
animation is refused. The approved edit's first spoken-scene boundary defines the replacement,
even when its source clip also contains body lines. `voice OPENING`, `plan-clip OPENING`, and
`make OPENING` use the existing banked-voice and clip production doors. Held batches cannot spend.

## Opening workflow contract (2026-10-28)

The board's `reuse_control_frame` action restores the exact approved source picture without generation, archives the replaced picture and recipe, and requires review of the restored frame. It preserves the recorded voice. Set the action/gestures separately before making a new clip so discarded prop actions do not carry over. Picture `shot_direction` remains an object with face/gesture fields.

`machine/hook_workflow.py` exposes `inspect`, `act`, `require_clip`, and `require_edit`. It reads indexed opening batches and their hook matrix, picture recipe, exact assets and byte-bound reviews. The board renders its stages; the same gates run before clip generation and editing without the board. `hook_variations.plan_clip` emits the normal storyboard contract, including frames, recorded voice, scene shots and cast. The Prompt Bench discovers active indexed batches; held batches are omitted.

Opening changes are isolated through `hook_workflow.revise(run, root, part, value)`: spoken_line, motion, or motion_reference. Saving never generates. The board shows `change_impacts` before saving and calls the same component actions. Picture approvals depend only on recipe/reference bytes; voice and motion changes reopen only their dependent stages. `clip-binding.json` binds each generated take to frame/setup/motion/voice, so an old take cannot be checked against new inputs. One opening request makes one paid clip attempt, with old media under versions/. Motion bank IDs are reusable and prepared media is cached by source bytes and trim/settings.

`higgsfield_api.upload` caches identical uploaded bytes for 24 hours and retries only storage transfers. `seedance._make` writes a request checkpoint immediately after submission; a disconnected poll resumes that request and refuses changed inputs. Do not resubmit an uncertain paid request. Opening copy revisions clear obsolete word-timed gesture anchors while preserving the action and references.

## Ad workflow runner (2026-10-29)

Public entry: `machine/workflow.py run <format> --brand <brand> --label <writing-label>`;
`complete` returns verified evidence from an active assistant task, `run --dry-run` is read-only.
The format playbook's `workflow.steps` declares `executor: agent|command|review`, input/evidence
paths, route-specific commands, paid stations and component completion checks. `workflow_runner.py`
implements the execution loop; it does not implement research, writing or production itself.
Read `.claude/skills/ad-workflow/SKILL.md` and its execution reference to operate it.

State/logs/tasks: `runs/video-production/<brand>/workflow-<label>/workflow-state.json`, per-station
logs and `NEXT.md`. Hash-bound receipts resume existing work; command failures stop and require an
explicit retry after inspection. Review gates read `components/review`'s public fold and require the
named person's accepted approval of the exact committed asset bytes. The runner never authors
human verdicts or publishes ads. Agent tasks stay in the current assistant session; no hidden child
agent or scheduler is launched. A command station can be reused only after its output checks pass.

Records adapter (O12): none for workflow checkpoints; they are local orchestration state exposed by
`run --dry-run`, not production artifacts or new review records. Owning components continue filing
their normal outputs. The legacy `status`/`pack` commands remain artifact inventory/export tools;
use the execution state for resumable workflow handoff.

Validation: `python3 machine/test_workflow.py` (offline; fixtures only, no paid generation).
