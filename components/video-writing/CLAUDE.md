# components/video-writing — the writing station

**video-writing** — takes **a finished video teardown on a route** and writes **our version of
the swipe for the brand: injection, hooks, the script, the audit, the spice and the brief
production takes**. It does not **read the swipe** (video-teardown does that) or **make the
video** (video-production and video-edit do that).

Station 2 of the four (teardown · writing · production · edit). Split out of `video-teardown`
on 2026-10-19, the owner: "make components/video-writing with the writing code and stages,
teardown hands off to it, repoint every reader, then build the mini doors per station."
History: the writing prompts moved from `video-teardown/prompts/` to `copywriter/prompts/video/`
on 2026-09-30 ("go ahead and make the move"); the code that runs them stayed in the teardown.
This finishes that split. The copywriter keeps social ad copy (`copy.py`); video writing is here.

## The four new-resident questions

- **Engine + owner:** `machine/writing_v2.py` (v2, the writing line) and `machine/run.py` (its
  command). Owner the owner.
- **Definitions + curator:** `prompts/` — every writing stage's prompt (1b, 2f, 3, 3v, the
  4-loop 4a–4g, 4m, 5 creator · ai · hook asset, 5m, 5n, 5u, 7, 7b, 8) and `prompts/v2/` for the
  v2 passes. Curator the owner. The highest `-vN-` in a folder is the live one; older ones sit in
  that folder's `archive/`.
- **Plane:** none of its own. It writes into the teardown run it is handed
  (`runs/video-teardown/_work/<label>/stages/`), and the teardown's filing copies the written
  words to `runs/video-writing/<brand>/<slug>/` (the shelf, unchanged).
- **Manifest per entry:** none. The prompts are versioned files, not a manifest.
- **Runs by:** both (a person's Mac, and the mini once its door is granted).

## How to run it

    python3 components/video-writing/machine/run.py <teardown run folder | label> [--allow-new-format]

or let the teardown hand off when it reaches stage 3:

    python3 components/video-teardown/machine/run.py <video> --brand <b> --route ai --v2 --writing v2

## Stage 5d — the director at the storyboard step (2026-11-17)

Direction from the owner, 2026-11-17: creativity runs on the chain with the existing tools and the machine keeps
one idea per scene; no person picks. Stage 5 stages each scene from the swipe's own shot (a literal re-enactment);
5d gives every staged scene one visual idea before Video Studio seeds from the brief.

    python3 components/video-writing/machine/director.py <teardown run folder | label> [--scenes S1,S3] [--dry] [--fresh]

- **Engine:** `machine/director.py`. **Prompts:** `prompts/stage-5d-director/` — the Writers' Room director
  (`room2-director-v1-owner.md`) and its ladder (`ladder-v1-owner.md`) copied as they are, a storyboard reply format
  appended to the director (`storyboard-ask-v1-owner.md`), the producer's scoring pass (`pick-v1-owner.md`, the room's
  four score axes plus the controls target and four checks) and the standing rulings (`rulings-v1-owner.md`).
- **Inputs:** the brief's scenes (words, job, beats, the swipe's shot as backbone only), stage 4i's controlling
  idea, the creative-controls VIDEO target (`creative_controls.target_md`), the run's reader card (1b), the brand's
  position and story (read only, through brandpath), the doctrine slices.
- **Decision (code, `decide`):** a pitch is out when it does not restage every beat, does not say the line, leaves
  the real scene, hides the problem on a scene before the payoff, or hides the product on a product, mechanism,
  solution, offer or result scene, or when a beat whose words name another person (and whose swipe shot shows
  that person) does not show them. The highest total of the four scores wins; a tie goes to the director's order.
  If nothing passes, the scene keeps the swipe's staging and the reason is recorded.
- **Writes:** into `stages/5-brief.md`'s json (the block Video Studio seeds from): `happens`, each beat's `do` /
  `action` / `who` / `prop` / `where`, the opening picture's `first_frame.action`, and a `director` record; the
  replaced text stays beside it (`happens_swipe`, `do_swipe`, `action_swipe`). A "Director's picks" section is added
  to the brief's prose. `stages/5-brief.before-director.md` holds the brief stage 5 wrote; a rerun starts from it.
  Pitches, scores and each pick's reason: `<run>/director/` (`picks.json`, `picks.md`, every prompt and reply).
- **Models:** run-kit's tiers through `claude_door` — the director on `designs`, the pick on `checks`. Writing
  calls only; never a picture or a clip. A rerun reuses every reply on file for the same prompt.
- **On the chain:** `writing_v2.director_after` runs 5d the moment the stage-5 writer call lands the brief (the
  model's answer or the session hand's), before any stage-5 check reads it: hole fill, claims, the section check,
  the scene fold, cast match, the production contract, the frame-map carry, swipe match, the viewer check and the
  acceptance stamp all read the directed brief, so no revalidate is needed. Its calls go through the chain's own
  door (`_claude_run`, the run's credential) and are logged with stage 5's calls as `stage5d`; its record rides on
  the run as `stages.stage5.director`. A director that cannot run leaves the brief as stage 5 wrote it and says so
  (a creative pass, not a check). A patch, any other pass, or a brief with no scene block never calls it.
- **Shots:** each kept idea also writes every shot's `face` and `gestures` (the swipe's kept as `face_swipe`,
  `gestures_swipe`).
- **Run by hand** on a brief already written (the command above): the brief's acceptance stamp then changes and
  `run.py RUN --revalidate` re-checks it. A production seeded before 5d ran keeps its takes.
- **Song ads.** A sung brief's scene (lyrics, no beats) gets one silent shot and one beat per line before it is
  directed (the song-ad rule), so the hook above covers a sung brief on its own. A sung plan made from a song spec
  (video-production `song.py --spec`, one plan scene per line) is directed with
  `director.py <spoken writing run | -> --plan <plan.json>`: one call cuts the lines into story moments (checked by
  code: every line once, in order; one scene per song section when the cut does not hold), the director stages each
  moment line by line, and the plan's scenes become those moments, each line a shot with who / action / prop /
  where / face / gestures. The plan before it is kept as `plan.before-director.json`; picks in `<plan>/director/`.
  The spoken run gives the cast, places, controlling idea, reader card and its own picks as context only.
  Given the spoken run, it also writes the directed song as a SUNG stage-5 brief in a writing run of its own,
  `runs/video-teardown/_work/<the plan's folder name>/stages/5-brief.md` (+ `run.json`, the spoken run as its
  source): every scene's `lyrics` with an empty `voice`, one shot and one beat per line, and the `song` block with one
  section per scene, its lines copied from that scene. `--times` re-lays the newest `song/timing.json` (a line the
  timing lists but did not hear takes the gap it sits in, marked `timed: "window"`) and rewrites the brief;
  `--brief-only` rewrites the brief alone. `song.py --spec` does not call it yet.
- **Production's beat grammar holds:** a beat's `do` is ONE visible action in one verb (the director writes it; a
  joined second action is cut at the first joiner, a delivery word swapped); the whole picture stays in `action`.
  A scene that nothing passes goes back to the director once, told why each pitch was out.
- **Tests:** `tests/test_director.py` (the station, a fake door) and `tests/test_director_in_chain.py` (a fake
  `claude` on PATH plays the stage-5 writer, the director and the producer through `claude_v2`).

## Writing result contract

`machine/writing_result.py.inspect_result(run_dir)` is a read-only, provider-free acceptance reader.
It returns `writing-result/v1`: `artifact_written`, `accepted`, `state`, `source` (run-relative path and
SHA256), `blockers` and `retry_budget`. The CLI writes `writing-result.json` and exits non-zero for
held or unverified writing. Acceptance is bound to the brief and its writing inputs; inherited flags
or a legacy `done` alone are unverified. AI filing promotes a deliverable and allocates its number
only when this reader accepts it. Text archives remain available while held. This is writing
acceptance, not permission to generate or publish. Automatic audit repair usage persists on
`run.json.writing_retry_budget` across resumes; unchanged accepted outputs are reused.

Existing held/done briefs use `machine/run.py RUN --revalidate`. This invokes
`writing_revalidate.revalidate(run_dir)` for one check-only sweep: no writing pass,
repair loop, original-source edit or retry-budget reset. Each required check has a
receipt under `revalidation/`; a provider outage or unavailable check remains held.
Review calls can incur cost. Unchanged accepted inputs reuse their hash-bound receipt.

## Tests

    /usr/bin/python3 -m unittest discover -s components/video-writing/tests

Spends nothing. Proves: the prompts live here and the old home is gone; every v2 pass's prompt
exists; every `{slot}` each pass asks for has a source, on the ai and the creator route; the
teardown loads writing from here and hands off only on `--writing v2` writing stages; the command
prints its help and refuses a teardown run that does not exist.

## What it leans on (not moved, on purpose)

- **The chain engine is the teardown's.** Filling a prompt, calling the model, the run record,
  the stage gates: `video-teardown/machine/run.py` + `chain.py`. writing_v2 loads them by path,
  through the names the teardown declares as its **writing seam** (video-teardown CLAUDE.md,
  public surface item 5) and nothing else.
  v1 writing (the default when `--writing v2` is not given) still runs inside the teardown's
  stage loop and reads its prompts from here.
- **The stage-5 gates live here since 2026-10-19:** `machine/swipe_match.py` (5m), `machine/manifest.py`
  (5n), `machine/cast_match.py`, with their tests in `tests/`. Production and the teardown load
  them from here; the teardown keeps forwarding copies under the same names so any reader not yet
  repointed still works. Public names: `swipe_match.stamp_of|read_of|brief_hash|check`,
  `manifest.status_of|check`, `cast_match.check|repair|readable_mismatches|scene_mismatches`.
- **Creator and founder runs write on v1** (2026-10-19): v2 has only the AI-lane brief, so the
  teardown keeps v1 writing for any other route and `writing_v2` refuses one before any call.
  **They write on the same rules** (verify row 10, 2026-10-21): the v1 heads (3 v23, 4b v24, 4c v16, 4d
  v20, 4e v14, 4f v11, 4g v11, 5 creator v33) ask for `{ask_lane}`, and 4g + 5 for `{video_spice}` and
  `{realism_index}`; the teardown binds them (`chain.RUN_INPUTS`) and fills them from
  `writing_v2.run_inputs(st)`, the same text the v2 passes get. Organic and paid are the same video (V1).

## Not done in this move

- `components/chain-runner/chains/video-teardown/chain.json:119` still cites the old
  `copywriter/prompts/video/...` path as provenance. That file is generated, never
  hand-edited (CR-2 (VT parity)), and is the developer's: repin it there.
- `platform/workers/mini-worker/teardown_adapter.py` looks for writing prompts only under the
  teardown component (already wrong since 09-30, red-test R-list 2026-10-02). the developer's.

## Stage 2w — Winner match (2026-11-23)

Owner, 2026-11-23: every swipe is matched with a winner before writing, the owner picks, then injection runs as usual.
`writing_v2.run_writing` calls `winner_match.on_chain` first, on every run: it rebuilds the brand's winner index
(`winner_index.py`), ranks the banked winners against the swipe on the trait matrix (both read from their own
teardowns: awareness in/out, format, cast, framework, sections, sophistication, length, pace, tone, hook, sound), writes
`winner-match.json` into the run and `stages.stage2w`. No model call, no spend, nothing picked.

- **The winner lane waits for a pick.** No winner, or only the brand's default from `winner.json`, holds stage 3
  (`waiting_for: winner pick`). A winner named on the command counts as picked. A run already written, or a
  from-scratch piece, is never held.
- **The pick:** the Studio board (Creative Options → Orders) shows the top 3 with fit and reason and a Pick button
  (`POST /api/winner-pick/<run>`), which calls `winner_match.pick_winner` and starts the writing. By hand:
  `winner_match.py pick <run> <winner> --why "..."`; `winner_match.py match <run>` runs 2w alone.
- Swipe orders from the board start on the winner lane with no winner (they used to default to swipe only).
- **Proof without a registry (2026-11-26):** `winner_index.py` reaches a winner's bank row through the brand's registry
  when it has one, else through the audit video the run tore down; every record carries `bank_id`. A second run of the
  same post or audit video folds under the original. Test: `tests/test_winner_index_no_registry.py`.
- **The winner's shape rides in the lane (2026-11-26):** `{winner_lane}` adds WINNER SHAPE (the arc its shape call
  named, `runs/winners/<brand>/shapes/shapes.json`), each arc beat with the doctrine section it holds (creative-controls
  `arcs`), its devices, and a line that keeps a founder teller out of new work (`writing_v2.winner_shape`). No shape
  call, no block.
- Off for one shell: `VW_WINNER_MATCH_OFF=1`. Page: Brand A Winners, https://claude.ai/artifact/RAwaL3yyn7w4Yb7SFEXdU9
  (`winner_page.py`). Tests: `tests/test_winner_index.py`, `tests/test_winner_match.py`.

## Hook format and creative controls (2026-10-28)

The v2 Read Hooks pass writes one `hook-matrix` JSON block alongside LINE/SCROLL/THUMB V0–V5.
`machine/hook_matrix.py` (`check`, `from_text`) reads the public creative-controls targets and floors;
every opening names its format evidence, dial execution, watch payoff and body join. The approved
control is described without forcing a remake. Variations below a shared floor, missing evidence,
or mismatched prose stop the split and use the normal corrective pass. Spice and the final brief
carry these rows into production. This reuses creative-controls; it does not define a second dial bank.

## The front of the logic layer (2026-11-18)

- **The hand read of a brief is a role's.** `swipe_match.py <run> --strategist-read` stamps the read as the
  creative strategist's (owner ruling, 2026-11-18: brief approval sits with that role; the owner steps in on a
  trip-wire). `--owner-read` is the older name of the same door. Test: `tests/test_brief_read_role.py`.
- **The logic layer's prompt versions are live** (owner approved 2026-11-19): idea v3 (the angle chosen first, the
  concept named), openings v11, script v11, audit v13 (the native note, no new fail), spice v11, brief v17 (idea and
  concept carried by name), audience v15, creator brief v37, creator page v11; the format-call guidance prints
  with every stop on a new format. The from-scratch picks prompt (`prompts/proposed/stage2s-scratch-picks-v1`)
  is approved and not yet run by anything: scratch.py still takes its picks from the person.
- **The thinking travels.** `{decision_trail}` is the run's decision trail (run-kit `trail.block`, `NONE` when
  empty), in reach of every pass on every route. The moment the stage-5 writer call lands the brief,
  `piece_keys` writes `piece.trail`, `piece.idea` and `piece.concept` into its block, once, before anything
  stamps or hashes it.
- **Layers arrive with their reasons.** `{declared_layers}` prints, under each layer's name, why the triage called
  it that (`layers._why`; `layer_reasons` on the older chain). Creator and founder prompts may ask for it too.
- **What the later stations hand back**, each a plain read that says `NONE` in words when empty, none read by a
  prompt until it asks: `{winners_feed}` = `runs/winners/<brand>/taught.md` (the winners side), `{edit_lessons}` =
  video-edit's `learned.json` rules and lessons bank rows filed for the brief, the writing or the teardown,
  `{winner_breakdown}` = `runs/winners/<brand>/breakdown.md`.
- **The dial preset can follow the awareness level: written, switched OFF** (`PRESET_FOLLOWS_AWARENESS`, or
  `VW_PRESET_BY_AWARENESS=1` for one shell) until the owner rules it on. On, the run keeps one preset as
  `controls_preset` with its reason and a trail row; the filed `hook-matrix.json` names it, and the hook check and
  the director read the same one.
- Tests: `tests/test_logic_layer_front.py`.

## The ask (2026-11-03)

A piece made for a promotion names the creative strategist's ask it was ordered with:
`run.py <run> --ask <ask name | ask.json>` writes the run's `vars/ask.md` (the repo-relative path, the same
convention image and copy writing read) and keeps `ask` on run.json — file, name, moment, window, offer lines.
Every writing pass is then handed the ask on top (`writing_v2.ask_block`): the offer lines it may say word for
word, the never-list, and the moment with its window and lines; where they differ from the offer bank, the ask
wins, and the brief names them in its header. A named ask that cannot be read stops the pass. A run with no
`vars/ask.md` writes exactly as before. v2 only: creator and founder runs (v1, the teardown's stage loop) do
not read it yet.

## The story preset (2026-11-21)

A piece can be written in a story preset (creative-controls `story_presets.json`, brand-free): `run.py <run> --preset
<id>` (or `--preset auto`: the chain picks from the run's format and awareness, rotating away from presets already
written for the same avatar, and keeps why) writes `vars/story-preset.md` and `story_preset` on run.json. Every pass
is handed the preset's shape on top, under the ask (`writing_v2.preset_block`): the beats at their marks timed to the
length, where the product enters, cast roles, tone, captions, and our nine checks; everything inside the shape still
comes from the inputs each prompt already binds (avatar, culture map, verbatim language, objection and offer banks,
dials, house rules). After the brief, `preset_check` writes notes to `writing_notes.story_preset` (never a hold).
`--dry` builds the first pass's prompt with every block and files it under `prompts/`, calling no model.
From scratch: `scratch.py <label> --brand --product --avatar --preset <id> [--dry | --write]` (the preset gives arc,
format and look; scratch runs now carry the swipe writing lane, which they lacked). Tests: `tests/test_story_preset.py`.

**Orders** (the Video Studio's Creative Options board, 2026-11-21): an order is a scratch run (or a fork of a teardown,
when a swipe is picked) carrying `combo` and `target_seconds` on run.json; Start writes it in the background. With no
story file, the locked concept the scratch checks read is the order's story preset at its own length, else the arc
(`swipe_match.scratch_story`). An order made in Higgsfield (`combo.tool`) carries the production contract as a note,
never a hold (writing chain and `--revalidate` alike), and a claims reader that skips a line is asked once more before
the check counts as not run. Tests: `tests/test_orders.py`.

## What may stop a finished script (2026-11-20)

Owner ruling, 2026-11-20: only money and law hold; the language layer (the brand's customer words) is what gets the
words right, and every writing pass reads it (`{language_bank}` and the prior verbatim rows in each pass's prompt).
`machine/holds.py` is the one place that decides:

- **Holds:** a cure / remove / erase word in any line (code; a run ruling naming that exact line settles it); the
  product file's own banned words (its Forbidden slash list) and an offer, price or guarantee line not word for word in
  the offer bank, product file, run ask or RULINGS.md, when the claims judge flags it and a second ask repeats it.
- **Notes, never a stop:** a section label disagreement (the judge's majority relabel rides on the receipt); a claim the
  product file, brand position, offer files, run rulings or the language bank say word for word; any other judge flag;
  the audit's findings once its two automatic repairs are spent (the brief is still written). Notes land on
  `run.json.writing_notes` and in `writing-result.json` `notes`.
- **Switch:** `machine/holds.json` per lane (`sections`, `claims`, `audit`), or `WRITING_HOLDS_OLD` on one machine;
  row WH-1 (money-law holds) in `team/rollbacks.md`. Tests: `tests/test_money_law_holds.py`.

## The swipe's picture and motion are the base, everything on them is ours (2026-11-20)

Owner, 2026-11-20 (last word of three that day): "we use the swipe image to generate our version, and we still extract
the motion patterns from the swipe to generate our own." Stage 5 stays on v17. Stage 5d runs in `director.mode()`
"swipe-base" (prompts `storyboard-ask`/`pick`/`rulings` v3): each scene card gives the swipe's shot — staging,
composition, camera, motion pattern, what the swipe shows — and what the swipe does there and why (`swipe_moment`;
the teardown's scene mechanics and psychology ride in the seed, `swipe_understanding`). A pitch keeps that composition
and motion pattern and layers our people, place (`setting_id`, one of the brief's places), product and idea with the
dial target, and writes every shot's `angle`, `camera_move` (push-in · pan · tilt · arc · handheld · hold) and
`camera_why`, starting from the swipe's camera; a move production cannot take puts it out; the producer scores
`camera` (totals out of 50). The swipe's values stay beside each field (`angle_swipe`, `camera_move_swipe`,
`setting_id_swipe`, `happens_swipe`, `do_swipe`, `face_swipe`, `gestures_swipe`). On file and off: stage 5 v18 and
director v2 (staged fresh, the swipe as understanding only). Switch: `machine/visuals_ours.json` (`lanes.brief`,
`lanes.director`, `director_base`), or `VISUALS_OURS_OFF` / `VISUALS_DIRECTOR_BASE` on one machine;
row VO-1 (visuals ours) in `team/rollbacks.md`. Tests: `tests/test_visuals_ours.py`.

## Strategist profile handoff (2026-11-26)

Before injection, validate the selected person through creative-strategist `who.selection`
(its CONTRACT.md). This also catches resumed runs whose old audience pass selected no sub.
Keep the source receipt as `selected_profile`; attach `profile.json` and `profile.md` to the
run. Every writing pass reads that person's strategist profile through the shared who block.
Test: `tests/test_strategist_profile_selection.py`.
