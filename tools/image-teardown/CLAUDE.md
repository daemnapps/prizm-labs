# image-teardown — a static ad in, its labels and brief out

**image-teardown** — takes **a static ad**, makes **its element labels and a
brief to remake it**. Does not **make the image**. Triggered by
`python3 chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe>`.

**Owner:** the owner. **Group:** teardowns. **Spoken name:** "image teardown".
How to run it for a brand: `RUN.md`.

**A component since 2026-10-01** — moved out of `the team notes/image-teardown/`
on the owner's word ("move image teardown to components"). Everything moved with
it: `chain.py`, `tools/`, the prompts, the brief register `briefs.json`, the
tests and the pages. Runs still file at `runs/image-teardown/<brand>/<label>/`.
The old lab folder is a one-release shim (README + forwarding `chain.py` /
`serve.py`); readers look here first and fall back to it; working files a
checkout still holds there are carried over by `tools/paths.py` `carry_over()`.
The Drive mirror stays at `the shared drive/image-teardown/` — the code
moved, the pictures did not (`the team notes/mirror.py` `MOVED`).

| New-resident question | Answer |
|---|---|
| Engine + owner | `chain.py` + `tools/` (`run.py` the steps, `paths.py` every path, `briefs.py` the brief register, `elements_label.py` the labels, `gates.py` the gates and the filing) — the owner |
| Definitions + curator | `prompts/` (one file per step, `-vN-damon.md`, highest number wins), `templates/`, `reference/visual-lexicon.md` — the owner |
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

## Steps

Declared once, in `tools/run.py` `STAGES`. `chain.py` is the entry; it opens
runs and hands the stages to `tools/run.py`.

| Step | What it does | Runs on | Writes (`runs/<run>/out/`) |
|---|---|---|---|
| 1 | teardown — the ad, as an objective record (a sequence: every slide, in order) | Gemini (reads the picture(s)) | `01-teardown.md` |
| 2 | the format — the ad with its brand stripped out | Gemini | `02-replication-spec.md` |
| 2b | **element labels** — which library rows the ad IS | Claude · `checks` tier | `02b-elements.md` → `elements.json` |
| 3 | injection — our brand through that format | Claude · `designs` tier | `03-injection.md` |
| 4 | headlines | Claude · `designs` | `04-headlines.md` |
| 5 | picture variations | Claude · `designs` | `05-image-variations.md` |
| 6 | the brief — by route × form, see the branch above | Claude · `designs` | `06-brief.md` |

Model ids are not written in this folder: Claude steps name a tier and the id
comes from `components/run-kit` `model.TIERS`. `CLAUDE_MODEL` / `GEMINI_MODEL`
in the environment force one.

**The variation batch's last step** (`tools/variations.py`, opt-in): `--to-check --links <catalog link ids>`
files every ad of the drop as a card in `Team Drive/meta/<brand>/1-check/image/` for the owner's approval —
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
  `tools/run.py` whenever a run's steps finish, held or not. Working files and
  every picture stay in this folder's own `runs/` and on Drive; media never
  enters the record. Variation drops (`tools/variations.py`) file at
  `runs/image-teardown/<brand>/<drop>/` — `working/`, `deliverable/`,
  `drop.json`, `run.json` (`machine: image-teardown`) — with the Drive mirror
  at `Team Drive/runs/image-teardown/<brand>/<drop>/` (SI-48 (teardown
  drops home), 2026-10-08); the one drop filed before stays at
  `runs/image-edit/<brand>/260923a/`, read there as legacy.
- **Manifest per entry:** `run.json` — machine, brand, label, the steps on
  file, `state` (`filed` or `held`) and, when held, why.

## Gates

Two of the five shared gates (`components/quality-checks`, via `hold()` →
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
- Tests: `python3 tests/test_image_teardown.py` — 38, no network, no model; plus
  `test_briefs.py` (25), `test_briefs_video.py` (4), `test_briefs_runs.py` (3)
  and `test_brief_standard.py` (3) — 73 test functions in five files.
