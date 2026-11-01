# image-teardown — a static ad in, its records out

**image-teardown** — takes **a static ad**, makes **its records: the
teardown, the format with the brand stripped, its element labels and the
swipe's dial read**, then hands off to `tools/image-writing` for the
brief (steps 3 to 6) and makes the pictures (through image-production, since
2026-10-23: `tools/pictures.py`). Does not **write the brief** (image-writing,
since 2026-10-27) or **draw the image itself**. Triggered by
`python3 chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe>`.

**The split (2026-10-27).** The writing — steps 3 (injection and the swaps
record), 4 (headlines), 5 (the variations, as data) and 6 (the brief) — moved
to `tools/image-writing` with its code (`tools/writing.py`,
`tools/swaps.py`, `tools/variation_rows.py`), its prompts and the standard
brief template, the way video-writing left video-teardown. This component
keeps the RECORDS (steps 1, 2, 2b and `out/controls-swipe.*`) and the one
chain engine; `tools/run.py` hands each writing step to image-writing and the
writing goes into this same run.

**One home for a run (2026-10-28, components/naming/WHERE-EVERYTHING-GOES-damon.md
item 4).** A run WORKS in `runs/image-teardown/<brand>/<label>/` — its `out/`,
`vars/`, `assets/`, `finals/` beside its filed record — found by
`tools/paths.py` `run_dir(label[, brand])` and listed by `all_runs()`. The
working folders stay out of git (`runs/image-teardown/.gitignore`). The old
lane folder `tools/image-teardown/runs/<label>/` is read for one release
and an old path handed in is forwarded to the new home. The 242 working
folders were merged into their record folders that day
(`runs/system-integration/moves-2026-10-28/repo-moves.jsonl`).

**The writing seam** — the names image-writing uses here, and nothing else:
`tools/run.py` (`Missing`, `later`, `prompt_for`, `route_of`,
`swipe_controls`, `main`, handed over as the engine `E`), `tools/paths.py`
(every path, incl. `WRITING`, `WRITING_PROMPTS`, `WRITING_TOOLS`,
`BRIEF_STANDARD`), `tools/gates.py` (`copy_gate`, `_gate`, `quality`). A
change to one of those is a change to image-writing.

**Owner:** the owner. **Group:** teardowns. **Spoken name:** "image teardown".
How to run it for a brand: `RUN.md`.

**A component since 2026-10-01** — moved out of `lab/damon/image-teardown/`
on the owner's word ("move image teardown to components"). Everything moved with
it: `chain.py`, `tools/`, the prompts, the brief register `briefs.json`, the
tests and the pages. Runs still file at `runs/image-teardown/<brand>/<label>/`.
The old lab folder is a one-release shim (README + forwarding `chain.py` /
`serve.py`); readers look here first and fall back to it; working files a
checkout still holds there are carried over by `tools/paths.py` `carry_over()`.
The Drive copy is `Shared Assets/runs/image-teardown/<brand>/<run>/`, the same path as the repo (components/naming/WHERE-EVERYTHING-GOES-damon.md, fix 4);
drafts and worksheets at `Shared Assets/runs/image-teardown/<brand>/drafts|worksheets/`. The older copies under
`Shared Assets/lab/damon/image-teardown/` and `Shared Assets/tools/image-teardown/` were moved there on
2026-10-28 (`runs/system-integration/moves-2026-10-28/drive-moves.jsonl`); `lab/damon/mirror.py` writes the new place.

| New-resident question | Answer |
|---|---|
| Engine + owner | `chain.py` + `tools/` (`run.py` the steps and the engine image-writing runs on, `paths.py` every path, `briefs.py` the brief register, `elements_label.py` the labels, `gates.py` the gates and the filing) — the owner |
| Definitions + curator | `prompts/` (steps 1, 2, 2b and the draft prompts; one file per step, `-vN-damon.md`, highest number wins), `templates/`, `reference/visual-lexicon.md` — the owner. Steps 3 to 6 and the standard brief: `tools/image-writing` |
| Plane | `runs/image-teardown/<brand>/<label>/` at the repo root (the run record: `01…06-*.md`, `elements.json`, `run.json`, `check.json`); variation drops at `runs/image-teardown/<brand>/<drop>/` (`working/`, `deliverable/`, `drop.json`, `run.json`), Drive mirror at the same path (SI-48 (teardown drops home), 2026-10-08); the brief register `briefs.json` here — one id per brief, read by the hand-off, naming, the asset ledger, clipping and production. Numbers count per brand and product (the owner, 1 Oct 2026: "brief numbers count per brand AND product — each product starts at 1 inside its brand."); new briefs are keyed `<brand>_<product>_brief-NNNN`, old ones keep `pNNN` |
| Manifest | `run.json` per run (machine, brand, label, steps on file, `state` filed/held and why); `briefs.json` per brief (brand, type, product, avatar, run, links) |
| Runs by | person |

Which brief STYLE each of this register's types (`tools/briefs.py` `TYPES`) is lives in `components/briefs/briefs.json` `teardown_types`, read by that component's `tools/briefs.py` `style_for()` (SI-137 (brief vocabulary map)).

History and why each part exists: `README.md`. The draft pictures that follow a
brief are the draft standard (`DRAFT-STANDARD.md`) — a separate job that reads
this tool's briefs.

## The branch — who makes it × what it is (2026-09-22)

the owner, 2026-09-15: *"a creator video brief is different than an AI video
brief"* and *"a creator static brief is different than a creator video
brief."* The video chain solved it once — one teardown, the last stage
branches by who makes it. This chain now has the same shape (The Build List,
builds 1–4; TEARDOWN-CHAINS.md has the survey that found the hole).

`chain.py start --route ai|creator --form auto|single|sequence`. The route is
who makes it: `ai` (the machine — the designer work order, the default and
exactly what this chain always wrote) or `creator` (a person with a phone).
The form is what it is: `single` (one still) or `sequence` (a carousel or a
slideshow); `auto` reads it off the swipe — several stills in the post's
photos folder means a sequence. Written to `vars/route.json` when the run
opens; `vars/production_route.md` carries the matching prose into stage 3.

Two stages read it, and only two:

| | ai · single | ai · sequence | creator · single | creator · sequence |
|---|---|---|---|---|
| 1 read | `stage1-image-teardown` | `stage1-sequence-teardown` — every slide, in order, plus the thread | `stage1-image-teardown` | `stage1-sequence-teardown` |
| 6 brief | `stage6-image-brief` — the three-document work order | `stage6-ai-sequence-brief` — the work order for slide one + slide deltas for two onward | `stage6-creator-static-brief` — one page to a person: the shot, the words, no plate, no type layer | `stage6-creator-sequence-brief` — one page per slide, no runtime, no Hear:, the close from the captions |
| after | drafts → work order → draft standard | drafts slide one → work order → draft standard; slides two onward: `tools/image-edit/sequence.py` | the draft standard makes the REFERENCE PICTURE the person matches; no work order | nothing drafted — a person makes it |

Stages 2–5 are identical on every branch. A run opened before the branch
existed carries no `route.json` and is `ai · single`, byte for byte. The
video chain's triage, on `STATIC` or `SEQUENTIAL`, now prints the exact
`start … --form` command instead of a dead end.

## The swaps record — `out/swaps.json` (every run)

One structured file per run says what the picture swaps and what goes into it; every picture maker (the static chain, the
Prompt Bench) reads it and nothing else to decide the pictures. It is written by stage 3, so since 2026-10-27 it is the
writing station's: `tools/image-writing/tools/swaps.py` owns it (`show` · `check` · `stage` · `backfill`); its
docstring states the shape and the rules. It still lands in this run's `out/`; `tools/pictures.py` reads it from there.

- **swaps rule 1** Every swap is its own entry with a kind: `cast` (a banked character's photo, ref = the cast id), `product` (the
  product's real pictures), `library` (a banked prop or set, ref = its path), `drawn` (from words only), `words` (the caption).
- **swaps rule 2** `product_in_frame` is yes or no; yes carries where it sits and which sides show. Nothing is inferred downstream.
- **swaps rule 3** The pictures sent are the swipe, one photo per cast swap, one per library swap, and the product's pictures only on yes.
- **swaps rule 4** `words: set_on_top` means the picture is made with no caption, headline or overlay text, and the brief's own type
  layer is set over it afterwards (`image_production/words.py`, the compositor in `image-production/static/tools/compose.py`);
  the plate is kept. `drawn` means the words are part of an object in the scene.
- **swaps rule 5** What the text does not settle is `unclear` and listed, never guessed.

Stage 3 (v6) writes it as its section 6 and image-writing (`writing.after`) reads it into `out/swaps.json` (a record that breaks the contract is
sent back once); stage 6 (v10, v11) carries it unchanged in Document Two and image-writing says when it differs. A run made before it
existed is backfilled by `swaps.py backfill`: the plain signals in the text first (a "no product" sentence, a product
reference on the plate, the type layer), one fast reading call (image-writing `prompts/swaps-reader-v1-damon.md`) for the rest, cached in
`out/.swaps-reader.json`, `source: "backfill"`.

## Steps

Declared once: the records in `tools/run.py` `RECORDS`, the writing in
image-writing `tools/writing.py` `STAGES`; `tools/run.py` `STAGES` is the two
in chain order. `chain.py` is the entry; it opens runs and hands the stages to
`tools/run.py`, which hands 3 to 6 to image-writing.

| Step | What it does | Runs on | Writes (`runs/<run>/out/`) |
|---|---|---|---|
| 1 | teardown — the ad, as an objective record (a sequence: every slide, in order) | Gemini (reads the picture(s)) | `01-teardown.md` |
| 2 | the format — the ad with its brand stripped out | Gemini | `02-replication-spec.md` |
| 2b | **element labels** — which library rows the ad IS | Claude · `checks` tier | `02b-elements.md` → `elements.json` |
| 3 | injection — our brand through that format (**image-writing**) | Claude · `designs` tier | `03-injection.md` → `swaps.json` |
| 4 | headlines (**image-writing**) | Claude · `designs` | `04-headlines.md` |
| 5 | the brief's five variations, as data (**image-writing**; the approved picture + 5, the owner 2026-10-27) | Claude · `designs` | `05-image-variations.md` → `variations.json` |
| 6 | the brief — by route × form, see the branch above (**image-writing**) | Claude · `designs` | `06-brief.md` |
| pictures | ONE first picture, built by `components/model-inputs` `preview.py` exactly as the board builds it (the swipe as IMAGE 1, the cast member's headshot, the product's real photos when in frame, the swipe's look, grain and black bars, the words set on top; rules in `model-inputs/lessons.json`); then a person's look (Looks good), then the brief's five variations by `tools/image-edit` (`tools/pictures.py`, run by `tools/pick_run.py` after step 6; the old judge, paste and refusal retry run only on `--controlled`) | the House's picture model via `tools/image-production` `plain` | `runs/image-teardown/<brand>/<run>/pictures/` |

**The plain way is the default for pictures** (the owner, 2026-10-25: "there's a lot of control that I think is messing stuff up", then "literally 1000000x better than any flex implementation we had in the past"): `tools/pictures.py` and `tools/slides.py` (carousels, each slide from the swipe's own slide; a plan in `vars/slides.json`) make every picture in ONE call through `tools/image-production` `plain`: the swipe, the brand step's swap and words (or the slide's lines), each product's real in-use pictures and line from its kit. No house prompt, judge hold, paste or grain; `--controlled` keeps the old path.

**The shared work list and the always-on worker** (the owner, 2026-10-23: "if they start something, I can pick it right up ... we can just leave it on all the time"): `tools/work_list.py` keeps `runs/image-teardown/<brand>/queue.json` (add · list · next · done · open; unaware and problem-aware first; a claim older than 3 hours is taken back); `tools/worker.py --brand <b> [--sync] [--once]` takes the next ad, runs stages 3 → 6 and the pictures on whatever login the machine holds, and puts a sterile or failed ad back on the list (held after 3 tries). `--sync` moves the list between machines through git. Start-here for a teammate: `context/HANDOFF-eve-<brand>-image-ads.md`.

**The creative controls** (the owner, 2026-10-23): steps 3, 4 and 6 bind
`components/creative-controls/slices/controls.md` as `{creative_controls}`.
Step 3 reads the swipe's level on every dial first (`out/controls-swipe.md`,
`components/creative-controls/read.py one`) and aims at the run's preset
(`vars/controls-target.md`; `run.py --controls <preset>`, default `maxed`),
never below the never-sterile floor. Step 4 writes every headline for the
swapped picture (one idea, reads cold).

Model ids are not written in this folder: Claude steps name a tier and the id
comes from `components/run-kit` `model.TIERS`. `CLAUDE_MODEL` / `GEMINI_MODEL`
in the environment force one.

**The variation batch's last step** (`tools/variations.py`, opt-in): `--to-check --links <catalog link ids>`
files every ad of the drop as a card in `Shared Assets/meta/<brand>/1-check/image/` for the owner's approval —
words from the drop's copy.csv plus the copywriter's own HEADLINES/DESCRIPTIONS (components/meta-upload/feed_image.py).

**Dry run — spends nothing.** `chain.py start|fill|variant ... --dry-run` (or
`tools/run.py <run> all --brand <brand> --dry-run`) resolves every step's
prompt and every file and variable it would be handed, prints OK or MISSING
per step, and starts no model, opens no run, writes no file. Exit 1 if anything
is MISSING.

**Element labels.** Step 2b hands the model the teardown and the candidate rows
(id · name · what) rendered at run time from `components/elements/library/` —
`format/image`, `style/image`, `framework/all`, `doctrine/awareness`. The reply
is read by `tools/elements_label.py` and every id is asked of
`components/elements/machine/elements.py` `check()`. An id the library does not
hold is **refused and recorded, never guessed**. `none-fits` is a real answer
and carries a one-line proposed row — that is how the library grows; nothing
here edits the library. `chain.py fill ... --labels` labels runs torn down
before this step existed.

## The four questions

- **Engine + owner:** `chain.py` + `tools/` (`run.py` the steps, `paths.py`
  every path, `elements_label.py` the labels, `gates.py` the gates and the
  filing), the owner.
- **Definitions + curator:** `prompts/` — one file per step, `-vN-damon.md`,
  the highest NUMBER wins (`-v10-` beats `-v2-`); a changed prompt is a new
  file, never an edit. `superseded/` and `parked/` never run. the owner.
- **The plane it emits:** `runs/image-teardown/<brand>/<label>/` at the repo
  root — `01…06-*.md`, `02b-elements.md`, `elements.json`, `source.json`,
  `run.json`, `check.json` (and `variant.json` for a variant). Filed by
  `tools/run.py` whenever a run's steps finish, held or not. Since 2026-10-28
  the working files sit beside the record in that same folder (git-ignored)
  and every picture is on Drive at the same path; media never enters git. Variation drops (`tools/variations.py`) file at
  `runs/image-teardown/<brand>/<drop>/` — `working/`, `deliverable/`,
  `drop.json`, `run.json` (`machine: image-teardown`) — with the Drive mirror
  at `Shared Assets/runs/image-teardown/<brand>/<drop>/` (SI-48 (teardown
  drops home), 2026-10-08); the one drop filed before stays at
  `runs/image-edit/<brand>/260923a/`, read there as legacy.
- **Manifest per entry:** `run.json` — machine, brand, label, the steps on
  file, `state` (`filed` or `held`) and, when held, why.

## Gates

Two of the five shared gates (`components/marketing-chain-checks`, via `hold()` →
`check.json` in the run):

- **elements** — after step 2b. Every label is a row in the element library or
  an honest `none-fits` with a proposed row. An unknown id, a missing label or
  an unreadable answer holds the run before the brand-side steps start.
- **copy** — after step 6, on the brief. `unfilled_check`: no UNFILLED note
  left in it. `price_check`: every price in the part that gets built (documents
  one and two — document three quotes the source ad and the market) is a price
  the brand's own offer-bank entry for that product sells today.

**A held run says why**: printed when it happens, in `check.json`, and in the
filed `run.json`. A held run gets no brief id, so it does not travel on to
drafts. `python3 tools/gates.py <run>` prints it. `--gates warn` records the
same verdict and carries on — for when a person has read the hold and
overruled it.

Also checked before anything runs (not one of the five, and older than them):
`tools/preflight.py` — no brand named in code or prompts, every `{placeholder}`
supplied, every brand file present.

## Rules that bite here

- **No brand in code or prompts.** Brand facts arrive from `brands/<brand>/`
  via `--brand`. There is no default brand, avatar or product; a tool that
  needs a brand reads it off the run (`vars/brand_name.md`) or stops and says so.
- **Paths are found, not counted.** `tools/paths.py` walks up to the workspace;
  nothing uses `parents[N]` to find it.
- Tests: `/usr/bin/python3 -m unittest discover -s tests` — no network, no
  model. The swaps-record, standard-brief and hook-ledger tests moved to
  `tools/image-writing/tests/` with their code on 2026-10-27.
