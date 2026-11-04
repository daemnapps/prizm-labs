# image-edit — an edit is a delta off a reference, never a fresh shot

**image-edit** — takes **a reference picture and ONE change** (free words,
a named fix, or a variation row) — makes **the edited picture, judged against
the reference, filed as a new version**. Does not **describe the scene,
generate fresh, rewrite the words, or write over the original**. Triggered by
`python3 tools/image-edit/edit.py <picture> --brand <b> --change "…"`,
`… --fix <row>`, or `python3 tools/image-edit/vary.py <baseline> --brand <b> --v <row:args>`
(`--dry-run` on both spends nothing).

**Owner:** the owner (engine and definitions both). Built 2026-09-22, build 5 on
The Build List (`lab/owner/BUILD-LIST.md`).

the owner, 2026-09-22: *"editors can create variations from baseline image drafts
easily (draft follows variation instructions while maintaining reference and
just making clean adjustments based on the brief variations). This is
effectively the same mechanics as making scene / frame adjustments for
videos, using references and making adjustments cleanly."*

**This is an EXTRACTION, not an invention.** The discipline is the owner's 2 Sep
ruling (`tools/video-production/frames-by-edit.md`), measured on a real
run — *an edit instruction must never describe anything the reference already
shows* — and the one-change rule of 11 Sep. Both were code in the video
machine's `machine/edit.py`; that file now imports them from here and is the
first caller. The generation is `tools/image-production`'s (`from_image`
routes to the edit model, the keep-everything clause, its one-picture judge,
the gates). What is new here is only what neither had: the fix and variation
libraries, and the two-picture judge.

---

## The one rule, and the second one

    generate from a description        4,262 chars   wrong wardrobe, blended faces
    edit, but still describing it      766-1,133     composition better, caption wrong
    EDIT, DELTA ONLY                     204-386     scene held, wardrobe right, legible

1. **The instruction carries the delta and nothing else.** The reference
   carries the composition. A change past 400 characters has started
   describing the scene and is refused before anything is spent.
2. **One change per edit** (two at a push). Five changes in one sentence come
   back wrong and nothing says which one did it. Counted, and refused.

Every reference has a **keep/change split**: what is LOAD-BEARING (never
changes) and what is SWAPPABLE. `splits.json` holds the default per kind —
`picture` (a finished static), `slide`, `frame-A/B/C` (the video machine's,
verbatim minus its run-specific wardrobe line). A caller's own split for one
picture outranks the kind's.

## The request

    brand     required   a folder under brands/
    picture   required   the reference — a file ON THIS MACHINE (`baseline` for vary)
    change    one of     the ONE thing to change, in words
    fix       one of     a row in library/fixes-vN-owner.json; `args` fills its slots
    args      optional   the slots a fix or variation needs — a missing one is refused BY NAME
    kind      optional   picture (default) · slide · frame-A · frame-B · frame-C
    keep      optional   more things that must not move
    elements  optional   element ids the change is about — each rides along as <<<id>>>
    product   optional   a product the brand declares; its photo rides along
    purpose   optional   image-production purpose; default `ad`
    aspect    optional   default: 9:16 for a 4:5 or 9:16 reference (assets are 9:16 only);
                         else the reference's own frame, read off its header
                         (every picture routes to GPT Image — one door, 2026-09-22)
    model     optional   force one image model — a declared row
    references optional  more reference pictures on this machine (the real logo, the
                         product photo) — reproduced exactly, never described
    words     optional   the words the result carries, verbatim (a list of lines) — a
                         carousel slide's own words; the guard counts the change as
                         written, not the words (engine.py's docstring is the source)
    count     optional   rolls per edit; default 1
    label     optional   default <picture stem>--<fix|edit>
    out       optional   default runs/image-edit/<brand>/<label>/
    dry_run   optional   resolve, write edit.json, spend nothing

A field nothing on this list names is REFUSED, not ignored. `change` and
`fix` are exactly one.

**vary**: `brand`, `baseline`, `variations` (a list of `id` or
`{id, args}`), plus `kind · keep · product · purpose · aspect · count · label ·
out · dry_run`. One edit per row, each under `<out>/<id>/`, the set's record
in `variations.json`.

**sequence** (2026-09-22, build 4): `brand`, `slide_one` (the plate — the
judged draft, never written to), `deltas` (the AI sequence brief file — its
slide-deltas `json` block is read — or a `.json` list of `{slide, change,
keep, type}`), plus `keep · product · purpose · aspect · count · label · out ·
dry_run · model · references`. One edit per slide from two onward, kind
`slide`, judged against slide one with a thread test (same person, product,
palette, framing), finished to 9:16; `sequence.json` records the set with
each slide's `type` for the compositor. `sequence.py` is the command. Slide
one as a delta, or a brief with no block, is refused by name. `sequence.py --to-check --links …`
finishes it: the slides in order become one carousel card in `meta/<brand>/1-check/carousel/`
(components/meta-upload/feed_carousel.py, which also files an existing run or a folder of slide-NN.png).
On a Mac without the owner's Shared Assets Drive mount, set `META_CARDS_ROOT` to that
drive's `meta/` folder first: `sequence.py` passes no `--root`, so without it the
card is refused by name (`components/meta-upload/to_check.py:52-59`).

## Variations on the picture path (2026-10-27)

the owner, 2026-10-27: *"everything needs to go through the same path to get the same level of output"* and *"image edit
should call on model inputs."* A brief's variations of an APPROVED picture (one made through components/model-inputs, so
it has a recipe) are made by `vary_recipe(req)` / `vary.py <approved.png> --brand <b> --from-brief <variations.json>
[--only h1,p2] [--dry-run]`:

    image teardown (the brief's variations, as data)  ->  image-edit (approved picture + ONE change; judges the result)
      ->  model-inputs (preview.variation_brief, the prompt, the 76-input check)  ->  image-production plain (sends it,
      sets the words on top)  ->  Model House (GPT Image 2.5, then the backups)

- The approved picture's own recipe is the start: `<stem>.recipe.json` beside it (or in `generated/`) and its plate
  `generated/<stem>.plate.png`, the picture before its words. It goes in as its own IMAGE with one job: keep everything
  except THE ONE CHANGE. Its approval is its `.liked.json` (PSH-5 (chosen references)); a plate carries its picture's.
- A variation row: `id`, `label`, and any of `words` (one per zone; set on top), `picture` (the one change, in the
  brief's words), `swap` (swap-list rows; a row whose `from` matches replaces it), `stays_drop`, `people`
  (`made-up` drops the cast face and sets the casting dial to 1), `person` (`who`, `age`, `look`, `wardrobe`, filled as a
  person would on the sheet).
- Words only: no new picture, the approved plate gets the new words (free). Anything else: one picture through
  `preview.make_picture(recipe, approved_by, out_dir=<variation>/engine)`, then this component's two-picture judge on
  the plates (the change present, nothing else moved); a result that moved more is held under `rejected/`.
- The input check runs first on every row; a refused row names the input and spends nothing. `--dry-run` writes each
  row's exact prompt and inputs into its `edit.json`.
- Stage 5 (tools/image-writing, since 2026-10-27) writes `out/variations.json` itself: the approved picture's five
  one-change rows. The batch step (`image-teardown/tools/variations.py`) still uses the older edit path; the board and
  the stage check use this one.

### A set change, on a run with a kept 3D set (2026-10-30)

The approved picture of such a run is a print of a 3D set, and stage 5 v9 writes each picture row as a change to that
set. So `vary_recipe` finds the run's set (image-production `picture_sets.kept`, read by path) and each row takes a `route`:

- **`words`**: words only, the approved plate gets the new words, free, as above.
- **`set`**: any row that changes the picture, on a run with a kept print. The row becomes `<variation>/set-request.json`
  (`picture_sets.change_request`: the change, the set's project, camera and light, the product's casting sheet, the print's
  words from `print_prompt`, the steps, the credits, the words on the set's props read from the brief, and flags for a row with no size or a run with no signage found). A dry run
  writes it too and spends nothing. A session builds and prints it in Higgsfield 3D Jutsu and files the print with
  `picture_sets.py put-change`. The next run takes that print as the picture, sets the words on top and judges it against
  the approved plate once. Until then the row's `state` is `waiting-for-set`. Nothing is generated flat.
- **`edit`**: a picture change on a run with no kept set, the flat edit above, unchanged.

`variations.json` carries each row's `route`, plus `waiting_for_set` and `print_credits` (2.5 per print still to make).
The hand-off carries the same request: a set row's folder holds `set-request.json`, the kept print and the product sheet
instead of `prompt.md`, and its run sheet step is the set change, not a flat picture.
A set row is never sent to `preview.make_picture`: that hands back the run's own print unchanged.

## New deliveries from the roles (`delivery.py`, 2026-10-27)

the owner, 2026-10-27 (Tella): *"check for [the graphic designer's] recent delivery"*; *"for [the video editor] as well on
the video side, everything needs to run through the same process"*; *"make this name agnostic. and the name of the
folders need to be the same for both repo and drive ... briefs should come from final stages of the chains, not some
random set up."* Ads a person finishes outside the chain (Higgsfield, an editor's cut) come back into the repo,
matched to their brief.

- **Named by role, one setting:** `delivery.json` `roles`: `graphic-designer` (pictures, card lane image) and
  `video-editor` (videos, lane video); `filled_by` is the one place a person is named. No person's name in a folder,
  path, command, button or lane. `state` stays `awaiting-pm` until the team confirms the folders.
- **Where:** a brief's hand-off folder is `runs/handoffs/<role>/<brand>/<brief key>/`, the same path in the repo and
  under `Shared Assets/` on the Drive. The check reads the repo's `returned/` first, then the Drive's, then the LEGACY
  places (`legacy_folders`, the old `Shared Assets/handoffs/…`) last, one Drive id once (2026-10-28). The packages put the brief there (`handoff.py` here,
  video-edit `machine/editor_handoff.py`); the person saves the finished files into its `returned/`.
  `place(role, brand)`, `returned_folder(role, brand, key)` and `repo_folder(role, brand)` are the readers.
- **Matching:** only files inside a `returned/` are read, never the package around it. The folder name decides the
  brief: the register key (`brand_product_brief-NNNN`), else a brief ID or old code in it, looked up in
  image-teardown's register (`tools/briefs.py`). A folder that is not one of this brand's briefs is listed, left alone,
  and asked about again next check.
- **Bringing it in:** each new file is read by Drive id to the SAME path in the repo
  (`runs/handoffs/<role>/<brand>/<brief key>/returned/…`, media git-ignored); the brief's `delivery.json` beside
  `returned/` records it (repo-relative paths and `{drive_id, label}`). A file already at that path, or named in the
  hand-off road's own `returned/index.json` (an agent's take-back), is already in. `runs/handoffs/<role>/<brand>/
  deliveries.json` is the ledger of Drive ids seen. The Drive is listed in batched questions, so a check takes seconds.
- **The card:** `delivery.py --brand <b> --send <role>/<brief key>` (the board's "Send to the Meta approval page")
  files the delivery as one card in To check through meta-upload `to_check.py`, in the role's lane; a second send
  updates that card.
- **Walls:** Drive by key only (`GDRIVE_SA_KEY`, gdrive-creator `folder_by_path` / `get_media` and the `svc` seam's
  list); nothing on the Drive is written, deleted, moved or renamed; nothing is sent to anyone.
- **Asked from:** the Make a Picture Ad board (`components/model-inputs/prompt_bench.html`), "Check for new
  deliveries" on step 1, each role's work under its name; the board only asks and shows. Command:
  `delivery.py --brand <b> [--role <role>] [--dry-run]`. Tests: `python3 tests/test_delivery.py`.

**The reference check (`reference_check.py`, 2026-10-28).** Proves the model actually used the references. Beside each returned file the maker saves `<asset>.receipt.json` (generation id, model, the
prompt as sent, every input in order, settings, who, when; the run sheet's Return step asks for it), or a one-line
`<asset>.link.txt` with the generation link. Per file, against its own step in the folder's `run.json`: RECEIPT
(present, for this step, on the sheet's model), PROMPT (word for word, whitespace and the step's own element
placeholders aside; the diff when not), INPUTS (every reference in, in order, by refs/ name, element name or id, or
bytes; a receipt's url is fetched only when it is public https; missing or extra named), LOOKS (image-production's
judge door, `judge.seen` + `route.judge_entry()`, with the step's references beside the file: built on its reference,
the product against its sheet, each cast face against its cast picture; a clip's first frame against its start
picture). ✓ proven, ✗ wrong, – not proven (no receipt, a link only, no key or network, or a product too small to tell),
n/a for a words-only step. Writes `reference-check.json` + `REFERENCE-CHECK.md` beside `returned/` and each file's
verdict into `delivery.json` (`reference_check`); a judged file is not judged again until it changes. `delivery.py`
brings receipts in beside their files and runs it after every bring-in, never stopping it. Command:
`reference_check.py <hand-off folder> [--no-judge]`. Tests: `python3 tests/test_reference_check.py`.
**Higgsfield's own record outranks the maker's word (2026-10-28).** An agent saves `<asset>.record.json`: the
generation record exactly as its Higgsfield tool returns it (`show_generation_by_ids`; the bare record or the tool's
`{"items": [...]}` reply, one generation). When it is there it is what gets checked: its id, status and model; PROMPT
against `params.prompt` (a "Words set on top afterwards" block in it is ✗ "words appended to the prompt", with its own
word diff against the sheet's words; an element put in for its files is allowed only in briefs
`runsheet.element_swap_line`'s exact wording; a `<<<id>>>` or number one character off is ✗ "text altered in transit
(Drive connector?)"); INPUTS from `params.medias` (matched by the downloaded bytes, or the same picture re-encoded,
against the `refs/` file) and `params.reference_elements` (by id or name); SETTINGS (aspect, quality, resolution, the
variant = `params.model`) against the step's; and whether the returned file is the record's raw result. Higgsfield's
public API cannot read a web-app or MCP generation back (`/requests/<id>/status` "Not found", `/v1/job-sets/<id>` "Job
set not found", probed 2026-10-28), so the agent that made it saves it. First real catch: generation dec7526e against
brief 0232 step 2 (fixture `tests/fixtures/`): plate ✓ by bytes, element ✓, settings ✓, prompt ✗ in 11 places plus
the appended words ("Shaved" sent as "Shared").

## The handoff (`handoff.py`, 2026-10-27)

the owner, 2026-10-27 (Tella, 15:00): *"focus on getting from swipe into draft. And then from here we're just gonna hand off
brief for Higgsfield execution because [the designer] is gonna go into Supercomputer and handle the rest of the
variations, and checking"*; later: *"we need to do that hand off and deliveries situation ... on the video side,
everything needs to run through the same process"*; and on the page: *"make this name agnostic. and the name of the
folders need to be the same for both repo and drive ... briefs should come from final stages of the chains, not some
random set up"*, *"standardization is the default"*. A chain ends at its draft; the rest goes to a role as one folder.

- **One front door, every lane:** `handoff.py <brief ID | run>` reads the brief's type from the register (`resolve`) and
  names the lane by its ROLE, never the person: a picture brief → `graphic-designer` (this package); a video brief →
  `video-editor` (video-edit's own command, `tools/video-edit/handoff.py <production run>`, its output passed
  through). A number two brands or products share is refused by name: give the full brief key. Who fills a role is one
  setting, `delivery.json` `roles` (lesson L-24 (roles, not people)).
- **One place, the same words in the repo and on the Drive:** `runs/handoffs/<role>/<brand>/<brief key>/` here and
  `Shared Assets/runs/handoffs/<role>/<brand>/<brief key>/` there (the Hand-off Standard's home; `drive_parts` is the
  repo path, word for word; lesson L-25 (one name, repo and Drive)). Moved from `Shared Assets/handoffs/` on 2026-10-28; the old folder keeps a
  README pointing here. **The front door:** `handoff_index.py` writes `runs/handoffs/INDEX.md` + `index.json` (one row
  per hand-off: brand, brief key, role, made, files out, returned, card) and `START-HERE.md` for the role, here and on
  the Drive; every hand-off and every delivery check rebuilds it. The finished work comes back into that folder's
  `returned/`, named `<brief key>-<variation>`, where the delivery check reads it.
- **Only a brief from the chain's final stage** (`final_stage`, lesson L-26 (final-stage briefs only)): the picture
  chain filed the run (`runs/image-teardown/<brand>/<run>/run.json` `state: filed`), the writing chain's last stage
  (image-writing `writing.STAGES`, today `06-brief.md`) is among its stages and on disk, and `out/variations.json` is
  the one stage 5 wrote (`source: stage5`). A test run (dryrun, batchtest, v2test, -test) or anything short of that is
  refused by name before anything is written.
- **The picture package:** from the approved picture (its newest `.liked.json` under
  `runs/image-production/<brand>/prompt-bench/`, or `--picture`) and the variation list; spends nothing: the prompts
  come from `vary_recipe(..., dry_run=True)`, the chain's own path (lesson L-23 (handoff carries the chain's prompts)).
  `HANDOFF.md` (for the graphic designer: what to make, the settings, the check, the words and finish, where to save,
  naming), `00-approved/` (the approved ad, its clean picture = IMAGE-1, the swipe, a see-through bars overlay), one
  folder per variation (`prompt.md` verbatim, `IMAGE-n` named as the prompt numbers them, `words-guide.png`; a
  words-only row's guide IS the finished picture), `rules.md` (the model-inputs lessons), `returned/`, `handoff.json`
  (repo-relative paths and the Drive id only; `runs/handoffs/` is git-ignored, the Drive is its home).
- **Self-contained on the Drive** (2026-10-28): every hand-off folder, both lanes, also carries `BRIEF.md`, the run
  sheet (`RUN.md` + `run.json`, components/briefs `runsheet.pack`) and `refs/` with every reference file the run sheet
  names, so someone in Higgsfield Supercomputer with Google Drive and GitHub opens one folder and needs nothing from
  this Mac. `--role <role>` names the lane outright and, when the full package cannot be made yet (no approved picture,
  no production run), writes the run-sheet hand-off alone and says why:
  `handoff.py <brief key> --role graphic-designer`. A carousel (sequence brief) has no variation list, so its hand-off
  is that run-sheet hand-off, one step per slide. `mirror_folder` is the Drive copy (gdrive-creator by key).
- **Asked from:** the Make a Picture Ad board: "Hand off to the graphic designer" in a picture's batch panel and "Hand
  off to the video editor" on a video's last step, both `/api/prompt-handoff` into this front door; the board only
  presses it and shows the Drive link. Command: `handoff.py <brief ID | run> [--brand <b>] [--role <role>] [--no-drive]`.
  Tests: `python3 tests/test_handoff.py`.

## The designer's delivery (`delivery.py`, 2026-10-27)

the owner, 2026-10-27 (Tella, 15:27): *"what I want to be able to do is just go into my tool and be like, okay, check for
the team's recent delivery"*; 16:10: *"right now image edit is where the final images go for the runs."* Pictures a designer
makes outside the chain (Higgsfield) come back here, matched to their brief.

- **The folder is one setting:** `delivery.json` `folder` (`Shared Assets/…/{brand}`). the team confirms it; until then
  `state` is `awaiting-pm` and every check says so. Changing the folder is that one line.
- **Matching:** every picture under the folder (subfolders too) by the brief ID in its file name, else in the nearest
  folder name above it (`brief-0325`, `brief_0325`, `Brief 0325`), looked up for the brand in image-teardown's register
  (`tools/briefs.py`); a number two products share is decided by the product named in the path. No ID, an unknown ID,
  or two IDs: listed as not tagged, left where it is, asked about again next check.
- **Filing:** each brief's new pictures are read by Drive id into `runs/image-edit/<brand>/<run>--delivery/` (media
  git-ignored), mirrored to `Shared Assets/runs/image-edit/<brand>/<run>--delivery/`, recorded in its `delivery.json`
  (repo-relative paths and `{drive_id, label}`) and `run.json`. `runs/image-edit/<brand>/deliveries.json` is the
  ledger of Drive ids already filed: "new" is everything not in it.
- **The card:** `delivery.py --brand <b> --send <brief>` (the board's "Send to the Meta approval page") files the
  brief's pictures as one card in To check through meta-upload `to_check.py`; a second send updates that card.
- **Walls:** Drive by key only (`GDRIVE_SA_KEY`, gdrive-creator `reach.list_tree` / `engine.get_media` /
  `reach.put_ids`); nothing on the Drive is deleted, moved or renamed; nothing is sent to anyone.
- **Asked from:** the Make a Picture Ad board (`components/model-inputs/prompt_bench.html`), "Check the team's delivery" on
  step 1; the board only asks and shows. Command: `delivery.py --brand <b> [--dry-run]`. Tests:
  `python3 tests/test_delivery.py`.

## `region` — the only thing that makes "nothing else moved" a fact

`region` is `left,top,right,bottom` in PERCENT. With it, the shared engine
masks the call (`image_production.providers.edit_in_region`): the picture is
the canvas, the mask exposes that rectangle alone, and the original is pasted
back outside it — so nothing outside can differ, whatever the model did.

Measured on one line of type, 2026-09-22, four live attempts:

| | what happened |
|---|---|
| no region | the product's own label redrew itself every roll ("Morings"→"Moringa", "180 g"→"188 g"); held |
| region, paste-back only | the label held — and the model had re-composed the frame, so the band carried a SHIFTED copy of the headline; held |
| region, masked call, keep-clause prompt | nothing drifted, and the model filled the hole with what was already there — the change never landed |
| region, masked call, hole-prompt | nothing drifted; the model painted the band black |

So: a masked edit says what goes IN the hole (`discipline.region_instruction`),
never what to keep — the mask does the keeping. And **type is not a job for a
model**: the `text` fix is deprecated (fixes-v3, 2026-10-07; parked 2026-09-22), agreeing with the standing doctrine (type
is composited over a clean plate, never generated). Wrong words are changed
in the brief's type layer and recomposed — exact, and free.

## The two libraries — the prompts designers run from

| File | Rows | What a row is |
|---|---|---|
| `library/fixes-vN-owner.json` | logo · product · layout · background · remove (· text, deprecated in v3 — type belongs to the compositor) | a spot fix on a finished picture: one delta template with `{slots}`, the keeps it adds, what it needs, which brand file rides along (the logo, the product photo), the test the judge adds |
| `library/variations-vN-owner.json` | headline · angle · person · product · colour · background · reframe | a variation off a baseline: the same shape. Stage 4e of image teardown writes its variation list against these ids |

Every row carries `status` (draft / approved / deprecated). **A changed row
is a NEW file `-v<N+1>-owner.json`** beside the old one; the highest number
wins. Never edited in place. `edit.py --fixes` and `vary.py --library` print
them verbatim; the Skill Library page renders them.

## The two judges

1. **image-production's** — one picture: is this a good picture (nothing
   grossly broken, no competitor mark, the direction is there, the words read).
2. **`compare.py`, this component's** — two pictures, the reference beside the
   result, the change that was asked for, and two standing tests: **CHANGE
   PRESENT** and **NOTHING ELSE MOVED** — plus the fix's or variation's own
   test. Prompt: `prompts/compare-judge-vN-owner.md`, highest wins. A result
   that moved anything else is held under `rejected/` with its reason.

The judge not running is a HOLD, never a pass.

## The four questions

- **Engine + owner:** `image_edit/` — `discipline` (the band, the count,
  the instruction), `engine` (`resolve` → the image engine → both judges →
  filing; `vary`), `compare` (the two-picture judge), `paths` (found by
  walking up; the image engine imported from BESIDE this folder, appended,
  never inserted at 0). `edit.py` and `vary.py` are thin CLIs. **the owner.**
- **Definitions + curator:** `splits.json`, `library/*.json`, `prompts/*.md`.
  **the owner** holds the approval gate; rows carry `status`.
- **The plane it emits:** `runs/image-edit/<brand>/<label>/` on both
  planes — `edit.json` (the record: asked, instruction, chars, changes,
  refused, both judges' verdicts, versions), the result as
  `<stem>--<fix|edit>-v<N>.png`, `rejected/*-why.md`, and `engine/` (the image
  engine's own record, prompt-as-sent, check.json), and `qc-log/` (QC-LOG.md
  plus each round's raw findings, filed through marketing-chain-checks'
  qc_log). Pictures mirror to
  `Shared Assets/runs/image-edit/<brand>/<label>/`.
  Not this plane: image-teardown's variation drops (`variations.py`) file at
  `runs/image-teardown/<brand>/<drop>/` since 2026-10-08 (image-edit#9, #14;
  SI-48 (teardown drops home)); the edit records inside a drop's `working/`
  are this engine's, written there through `--out`. The one drop filed before
  (`runs/image-edit/<brand>/260923a/`) stays, frozen.
- **Manifest per entry:** `edit.json`, `state` ∈ refused · dry · filed · held · waiting-for-set.
  `variations.json` for a set.

**A LIBRARY — the public surface** (the team, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line). Besides the three commands (`edit.py`, `vary.py`, `sequence.py`), callers APPEND `tools/image-edit` to `sys.path` and may use only:
1. **`image_edit`:** `edit(req, …)` → the edit record (`edit.json` shape); `vary_recipe(req)` → a brief's variations of an approved picture on the picture path (`variations.json`); `resolve(req)` → `{instruction, …}` with nothing spent; `deltas_from(source)` → the slide-delta rows of a brief.
2. **`image_edit.discipline`:** `DELTA_MIN`, `DELTA_MAX` (the instruction band, chars), `MAX_CHANGES`; `count_changes(change)` → int; `instruction(keep, change, element_ids=)` → the delta instruction; `guard(change, text)` → why it is refused, or `None`.
3. **`image_edit.engine`:** `thread_check(n)` → the slide-thread check row; `P.runs(brand, label)` → the run folder.
4. **SEAM, not public:** `engine._file_batch(root, summary, name)` (image-teardown's `carousel.py`). A seam renamed keeps its old name as an alias until its callers move.
Everything else — `split_for`, `region_instruction`, `compare`, the rest of `engine` — is internal and may change without notice.

## Rules this component holds itself to

1. **The original is never written to.** A result is a new version, counted
   up per stem under the brand's run root. A test enforces it.
2. **No brand, product, person or model in code, prompts or library.** A test
   reads the real `brands/` tree and checks.
3. **Refused, never guessed.** An unknown fix, variation, kind or slot stops
   the work and names the real ones.
4. **Keys by name, never by path.** This component reads none itself; the
   image engine's doors read theirs.
5. **The band is measured on the delta.** The keep clause is a list, and a
   longer list is a tighter edit — capped separately at 700 for the whole
   instruction (found on the first variation run: five keeps + one change
   refused a clean headline swap). The 700 counts the approval-page learnings
   lines too, measured raw; the hook keeps only the lines that fit (B8 (seven
   B3 calls), 2026-10-08).
6. **`sys.path.append`, never insert at 0.**

## The frame (the owner, 2026-10-26): 9:16 from the start

An edit leaves at 9:16 like every other picture: the engine asks the model for 9:16 with the centre 4:5 as the safe zone,
the judge measures the zone, and nothing is outpainted or finished afterwards.

Attaching the real product photo (`--ref`, or `--product` when the brand
declares a cutout) stopped the tube label garbling on most rolls — the edit
rule from the video side, proven again: when the change touches a banked
thing, the bank's own reference rides along. The compare judge still holds a
roll whose tiny label text drifted (live: "3.53 OZ" came back "4.52 OZ") —
the next step is the same taping idea for edits, masking only the region the
delta names.

## What the first live run taught the engine (2026-09-22)

The headline swap on a real draft came back with the right headline — and a
pair of hands and a towel the reference never had, at 2:3 instead of 4:5.
Three defects, all in `tools/image-production`, all fixed there with
tests: the brand's matched assets rode along on an edit (now `assets: False`
by default for `from_image`, and a declared field); the cropping-composition
clause told the model to compose a scene (now skipped for edits); and OpenAI
answers 4:5 with 1024x1536, which the engine's own check then held (now
centre-cropped back to the request before the judge, `providers.conform`).

`edit.py` on the video side still carries its own banked-asset table with ids
by name; that is its file, untouched beyond the import.

Tests: `python3 tools/image-edit/tests/test_image_edit.py` (its own
run prints the count) — stdlib `unittest`, stubbed provider and both judges, temp dirs only.

## Two things that are open, not settled (stated 2026-09-23)

- **The Drive carve-out (O9): does not apply here.** This machine mirrors to
  `Shared Assets/runs/image-edit/<brand>/<label>/` — the standard path, not
  a lab one. It is named rather than left silent so a reader does not assume
  the carve-out five of its neighbours carry applies to this one too.
- **A records adapter (O12): none yet.** The convention allows "an adapter or
  'none yet' stated"; this states it. What this machine does emit, since
  2026-09-23, is a `run.json` beside every `edit.json` — without it the index
  read fourteen runs as having no record at all, which made a machine that
  files carefully look stateless.

## `skills/` — the editing skills people pull into Higgsfield (the owner, 2026-09-29)

*"Anything that's actually doing editing needs to just live in the image
editing component … my editors can just pull in those different skills easily
and then make changes, make swaps, make adjustments really fast."* One file per
targeted edit (`logo-swap`, `avatar-swap`, `element-swap`),
indexed in `skills/README.md` with the one paste that loads them into
Higgsfield. Each names its model and, before every run, looks for a newer
version of that same model and uses it — never a different maker on its own.
They run in Higgsfield on the Higgsfield catalogue's models, so they follow the
same one-change discipline as `edit.py` but not its code; the resize is the
recorded FLUX exception to one-door-per-job (the owner: "we're literally
resizing"). Video versions live in `tools/video-edit/skills/`.
