# components/model-inputs — what each picture and clip model takes, and what works

**model-inputs** — for **pictures and video both** — answers **what can go into a model, within what limits, and what prompt structure the
maker says works**: one definitions file per model (`inputs/<model>.json`): every input with its allowed
values and what we send, the limits (images, prompt length, size rule, formats), the structure rules, the
avoid list, each with its source URL. It does not **make** a picture or a clip: chains bind its slice, the
engine reads its limits and calls its checker.

the owner, 2026-10-26: *"we need to have the full awareness of all the inputs we can put in ... install this into
our system itself, similar to marketing doctrine and the creativity dials ... we are also going to do this for
seedance too so we always get the best quality image and image to video."*

## Connected to the Generative Model House

The house (`components/generative-model-house`) says which model does which job; this component says what that
model takes and what works. They meet at the registry id: `input_rules.for_job("pictures.edit")` asks the house
which model that job uses and loads that model's file (`inputs/<registry id>.json`), so no chain names a model to
find its rules. `input_rules.coverage()` lists every picture and clip job in the house and whether its model has a
file yet and is filled; a job whose model has no file is refused by name, never guessed. Each file says its
`medium` (`image`, `video`, or for the jobs behind the line `voice`, `music`, `upscale`, `3d`, `judge`; `coverage(everything=True)` lists those too, with each sheet's depth and whether every rule names its source). All video, voice, music, upscale, 3D and judge sheets are filled (draft, 2026-10-27); `suno.json` is a by-hand sheet with no Model House row. Page for the owner: `context/model-input-sheets-owner.html`, mirror `MODEL-INPUT-SHEETS-owner.md`.

## The rule for every chain

- A chain or tool asks for a JOB (`for_job`), never names a model, and never restates a limit, a size rule or a structure rule in its own code or prompt. It reads
  `input_rules.limits()` / `valid_size()` / `check()`, and a prompt binds `slices/<model>.md`.
- `image_production/plain.py` calls `check()` before every picture: an **error** (too many images, a bad size or
  quality, a prompt over the limit, a wrong file type) stops the call; a **warning** (an unnumbered image, studio
  wording, no safe zone, quoted words with no "no other writing") is recorded on the picture's record and shown on
  the Picture Bench.
- **A product is cast like a person** (2026-10-27: *"very similar to the concept of the casting sheet ... same
  thing applies for products ... for all product generation or any image that is using a product in it, we must use
  reference ... if product is in use, the realism and ... the physics, like how it's used, needs to be 100% accurate"*).
  Every picture with a product in it carries that product's sheet, its kit (`runs/ai-elements/<brand>/products/<kit>/kit.json`):
  in a hand or on skin (`in_use(swaps)`), its in-use pictures (`in_use.refs`: its back and a real hand holding it);
  shown on its own, its front photos (`shown.refs`); always its true size and, from `behaviour`, how it is held and
  what it never does (image-production `plain.product`). A product in frame with none of its photos ticked is
  MISSING (`product_sides`). A kit with no in-use pictures falls back to its own photos; the product sheets page
  (`context/product-sheets-owner.html`) shows which kits are thin.
  Find any product asset in `runs/ai-elements/PRODUCT-INDEX.json` (`product_index.find`, video-production) before
  searching folders or the Drive.
- To change a rule: edit `inputs/<model>.json`, then `python3 input_rules.py render`.
- `components/video-production/machine/model-inputs.json` is the field-level contract that maps OUR scene fields
  onto each maker's field names (stations `still-generate`, `motion`, `talking`). It stays there. This component
  says what each model takes and what works; a later step makes that contract read its limits from here.

## The board is an interface, never a brain (2026-10-27)

the owner: *"the board is just a visual representation of the chains themselves, never its own brain, it's just an
interface to track the steps / elements."* `prompt_bench.html` / `prompt_bench.py` show the chain's steps and let a
person set its choices; every rule that shapes a picture lives in the chain (`preview.py` here, the builder the chain's
first picture — image-teardown `tools/pictures.py` — and image-edit's variations call). A chain run with no board
makes the same picture: `pictures.plain_pictures` takes the same filled sheet (`full_brief(fill_defaults(...))`) and
the same black bars as the board's make step. Logic found only in the board is a bug: move it into the chain.

**The board runs no job itself** (2026-10-28: *"we need to move actual jobs to other sessions, the board is
literally just to keep this process organized and streamlined"*). Every make, keep (with its upscale), scene remake and
swipe-frame open starts as its own process (`board_job.py`, through `prompt_bench._spawn`) and writes its state to
`runs/prompt-bench/jobs/<id>.json`; the board only starts jobs and reads those files, so restarting the board never
stops one. The scenes page opens with what needs review: every scene with a take made in the last day, newest first.

## Feedback becomes a lesson for every ad (`lessons.json`, 2026-10-27)

the owner: *"all of these notes must be agnostic feedback ... if we can get any level of automation out of this, feedback
needs to be rolled up into the chain and agnostic so the next run is even better."* A note from any review (a Tella
recording, the board, the approval page, chat) is never kept for one ad. In the same change: one row in `lessons.json`
(`said` word for word with its source, `rule` written for any brand, product, avatar or ad, `enforced_by` the
`file :: line` where the chain applies it, `status` draft until the owner approves) and the code or prompt line that
makes the chain obey it. The board shows the lessons on steps 2 and 3. `test_preview.py` fails a lesson whose
enforcing line is gone or whose rule names a brand.

## The four new-resident questions

- **Engine + owner:** `input_rules.py` (library: `load`, `limits`, `qualities`, `valid_size`, `check`, `render`;
  stdlib, no credential, no network). Owner the owner.
- **Definitions + curator:** `inputs/gpt-image-2.5.json` (read from OpenAI's references, 26 Oct 2026) and
  `inputs/seedance-2.5.json` (filled 2026-10-26 from BytePlus's Seedance 2.5 prompt guide: limits, every input,
  structure rules and avoid list; its field contract is the video-production file above). Curator the owner.
- **Plane:** none. `slices/*.md` is a rendered projection of the definitions, not run output.
- **Manifest per entry:** every input, structure rule and avoid item carries `status` (draft / approved /
  deprecated); every file carries its source URLs and the date read.
- **Runs by:** both.

## The preflight (`preview.py`, 2026-10-26)

`preview(job, brief)` shows, for free and without generating anything: the House's model and door, the exact prompt (built
by each chain's OWN builder from the real brief fields), each numbered file with its job, the settings, the rulebook
findings, the Higgsfield cost quote and the backup ladder. `python3 preview.py <job> <brief.json>` exits 1 on a rulebook error and
2 when the job cannot be built, so a chain runs it first and refuses to spend. A job's builder is a line in `builders.json`
(`{"clips.backup": "video-production/machine/kling_prompt.py:preview_builder"}`; a builder takes the brief and returns
`{prompt, inputs, settings, fields, medium}`) or `register(job, fn)`: a backup clip builder plugs in with no change to
`preview.py`. The Prompt Bench page is `prompt_bench.html`, served by the Picture Bench at `/prompt` (`prompt_bench.py`).

## The picture sheet and the gate (`picture-sheet.json`)

In: a brief or a recipe. Out: a filled sheet, the exact prompt, and a verdict. The rules live in `picture-sheet.json`
`rules`:
- PSH-1 (inputs all set): every variable FILLED with an allowed value or NOT_APPLICABLE with an allowed reason; a
  MISSING one stops before any spend with one plain line (`gate`).
- PSH-2 (defaults first): `fill_defaults(recipe)` fills everything the brief, its brand step and house files state.
- PSH-3 (guard dials set) and PSH-4 (sterile floor): the guard-read dials are never N/A, never under the floor.
- PSH-5 (chosen references): a made picture goes in only with a chosen record (`chosen_record`); its below_criteria
  flag travels downstream (`flags`, amber, never a stop).
- PSH-6 (every input sent): `full_brief` sends every filled dial, feeling, technique and keep item in labelled lines.
- PSH-7 (one sheet per scene): `make_frame_pair(recipe, delta)`, `validate_pair(a, b)`.
- PSH-8 (outputs never stop): output checks score attempts (`pick_best`, `choose_pair`); after
  `output_checks.max_attempts` the best is chosen and marked below_criteria.
- PSH-11 (inputs from the swaps): the pictures that go in are worked out from the run's swap list
  (`runs/image-teardown/<brand>/<run>/out/swaps.json` since 2026-10-28, written by the teardown's `swaps.py`): the swipe as the layout,
  one cast photo per cast swap (`runs/ai-elements/<brand>/casting/<ref>/master.jpg`, plus `reference/master-sheet.webp`
  when the rulebook takes webp), product photos only when the product is in the frame and only the sides named, one
  library photo per library swap, nothing for a drawn or words swap. The sheet rows: the swap list, product in this
  picture (`yes: <where>` / `no: <reason>`), the swaps, what stays, the words. No swap list, or a cast or library
  swap whose picture is not on file, is MISSING. A cast swap's THE PEOPLE names the cast member in IMAGE n and keeps
  the face (`plain.prompt(people="cast")` with `people_lines`; each cast photo's line by `ref_says`). Words set on top:
  no writing in the picture, no words block. `brief["swap_file"]` previews against a sample list (`fixtures/`).
Clips: `clip-sheet.json` (rules CSH-1 to CSH-7), `fill_defaults_clip`, `make_clip(recipe, approved_by, dry_run)` through the
chain's own Seedance door with exactly the previewed prompt. Picture dials: `picture-dials.json` (PSH-10 (dials as picture words)).
Commands: `preview.py check <recipe>` (exit 1 on any blank), `preview.py make <recipe>` (refuses unless the check
passes and the recipe carries a cost approval).

Public surface (a LIBRARY, callers append this folder to `sys.path`): `input_rules.load`, `limits`, `qualities`,
`valid_size`, `check`, `render`, `write_slices`, and `preview.preview` / `register` / `swap_list` / `swap_rows` / `fill_defaults` / `full_brief` / `validate` / `flags` / `gate` / `chosen_record` / `pick_best` / `make_frame_pair` / `validate_pair` / `choose_pair` / `make_picture` (an optional `out_dir`) / `variation_brief` / `needs_picture` (a brief's variation of an approved picture as the brief this builder takes; image-edit's `vary_recipe` is the caller, 2026-10-27). Tests: `python3 test_input_rules.py`, `python3 test_preview.py`.

## Opening variations on the board (2026-10-28)

The scene page links active opening batches and displays `video-production/machine/hook_workflow.py` stages. Start-picture recipes open in the existing element matrix. Their approved base is resolved from the repo and shown as the actual first input; a missing base refuses instead of falling back to the swipe. Workflow actions run in `board_job.py`. Job lookup keys survive board restarts. One-attempt clips remain visible even when no numbered takes folder exists.

The opening board's Change one element panel delegates to hook_workflow.revise; it does not regenerate. Clip, picture, edit and check jobs prevent overlapping input changes. Deep links retain the run in the URL so separate opening tabs do not reopen whichever run last wrote localStorage. Picture regeneration saves the actual recipe and preserves the previous frame; failed opening pictures return for review without automatic paid retries.
