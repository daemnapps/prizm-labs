# image-edit — an edit is a delta off a reference, never a fresh shot

**image-edit** — takes **a reference picture and ONE change** (free words,
a named fix, or a variation row) — makes **the edited picture, judged against
the reference, filed as a new version**. Does not **describe the scene,
generate fresh, rewrite the words, or write over the original**. Triggered by
`python3 tools/image-edit/edit.py <picture> --brand <b> --change "…"`,
`… --fix <row>`, or `python3 tools/image-edit/vary.py <baseline> --brand <b> --v <row:args>`
(`--dry-run` on both spends nothing).

**Owner:** the owner (engine and definitions both). Built 2026-09-22, build 5 on
The Build List (`the team notes/BUILD-LIST.md`).

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
    fix       one of     a row in library/fixes-vN-damon.json; `args` fills its slots
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
On a Mac without the owner's Team Drive Drive mount, set `META_CARDS_ROOT` to that
drive's `meta/` folder first: `sequence.py` passes no `--root`, so without it the
card is refused by name (`components/meta-upload/to_check.py:52-59`).

## `region` — the only thing that makes "nothing else moved" a fact

`region` is `left,top,right,bottom` in PERCENT. With it, the shared engine
masks the call (`image_production.providers.edit_in_region`): the picture is
the canvas, the mask exposes that rectangle alone, and the original is pasted
back outside it — so nothing outside can differ, whatever the model did.

Measured on one line of type, 2026-09-22, four live attempts:

| | what happened |
|---|---|
| no region | the product's own label redrew itself every roll ("Centela"→"Centella", "180 g"→"188 g"); held |
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
| `library/fixes-vN-damon.json` | logo · product · layout · background · remove (· text, deprecated in v3 — type belongs to the compositor) | a spot fix on a finished picture: one delta template with `{slots}`, the keeps it adds, what it needs, which brand file rides along (the logo, the product photo), the test the judge adds |
| `library/variations-vN-damon.json` | headline · angle · person · product · colour · background · reframe | a variation off a baseline: the same shape. Stage 4e of image teardown writes its variation list against these ids |

Every row carries `status` (draft / approved / deprecated). **A changed row
is a NEW file `-v<N+1>-damon.json`** beside the old one; the highest number
wins. Never edited in place. `edit.py --fixes` and `vary.py --library` print
them verbatim; the Skill Library page renders them.

## The two judges

1. **image-production's** — one picture: is this a good picture (nothing
   grossly broken, no competitor mark, the direction is there, the words read).
2. **`compare.py`, this component's** — two pictures, the reference beside the
   result, the change that was asked for, and two standing tests: **CHANGE
   PRESENT** and **NOTHING ELSE MOVED** — plus the fix's or variation's own
   test. Prompt: `prompts/compare-judge-vN-damon.md`, highest wins. A result
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
  `Team Drive/runs/image-edit/<brand>/<label>/`.
  Not this plane: image-teardown's variation drops (`variations.py`) file at
  `runs/image-teardown/<brand>/<drop>/` since 2026-10-08 (image-edit#9, #14;
  SI-48 (teardown drops home)); the edit records inside a drop's `working/`
  are this engine's, written there through `--out`. The one drop filed before
  (`runs/image-edit/<brand>/260923a/`) stays, frozen.
- **Manifest per entry:** `edit.json`, `state` ∈ refused · dry · filed · held.
  `variations.json` for a set.

**A LIBRARY — the public surface** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line). Besides the three commands (`edit.py`, `vary.py`, `sequence.py`), callers APPEND `tools/image-edit` to `sys.path` and may use only:
1. **`image_edit`:** `edit(req, …)` → the edit record (`edit.json` shape); `resolve(req)` → `{instruction, …}` with nothing spent; `deltas_from(source)` → the slide-delta rows of a brief.
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

## The frame (the owner, 2026-09-22): 9:16 only, content in the 4:5 zone

A 4:5 or 9:16 reference leaves at 9:16. The image engine edits the CONTENT at
4:5 and finishes it — content taped down in the middle, only the strips above
and below painted (`image_production.providers.finish_9x16`). Both judges see
the 4:5 content; the delivered file is the 1080x1920 asset. Thirteen live
rolls before the finish existed had shown both doors reflow a 4:5 layout to
fill a 9:16 frame when merely asked not to (`the team notes/SAFE-ZONE.md`, 22 Sep).

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
  `Team Drive/runs/image-edit/<brand>/<label>/` — the standard path, not
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
targeted edit (`resize-9x16`, `logo-swap`, `avatar-swap`, `element-swap`),
indexed in `skills/README.md` with the one paste that loads them into
Higgsfield. Each names its model and, before every run, looks for a newer
version of that same model and uses it — never a different maker on its own.
They run in Higgsfield on the Higgsfield catalogue's models, so they follow the
same one-change discipline as `edit.py` but not its code; the resize is the
recorded FLUX exception to one-door-per-job (the owner: "we're literally
resizing"). Video versions live in `tools/video-edit/skills/`.
