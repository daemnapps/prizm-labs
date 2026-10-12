# image-production — a static brief in, finished pictures out

**image-production** — takes **a static brief** (a `batch.json`, or a teardown's
`06-brief.md`), makes **the finished pictures, judged and named**. Does not
**write the words**. Triggered by `python3 run.py runs/<brand>/<batch>` (a batch)
or `python3 machine.py <swipe> --brand <brand> --avatar <avatar> --product <product>`
(swipes, through their teardown steps and on into the build).

**Owner:** the owner. **Group:** production. Why each part exists, and every failure
it was built after: `README.md` (the eight steps of a build), `PIPELINE.md` (the
batch pipeline, ruled 2026-09-05), `PROMPT-SPEC.md` (prompts are slots, never
prose). the owner never runs any of this — a session runs it and hands him a link.

## Steps

Two ways in, one tail. The entry the board scores is `machine.py`.

**A batch** — `run.py runs/<brand>/<batch>` (`PIPELINE.md`):

| Step | What it does | Runs on | Writes (in the batch folder) |
|---|---|---|---|
| gates | **elements** and **copy**, before anything is made | code | `elements.json`, `check.json` |
| plates · prepare | the prompt for each ad, exactly as it will be sent, and the model it routes to | code (`tools/plates.py`) | `inbox/jobs.json` |
| plates · generate | the pictures | a session, on the Higgsfield MCP — there is no unattended path | — |
| plates · ingest | finishes each 4:5 frame to 9:16 — strips painted, content taped down (2026-09-22; the flat band is retired) | code | `inbox/<slug>.png` |
| finish | measured checks, then the judge, then the offer bar alone | code + a vision model (`tools/finish.py`) | `verdicts.json`, `rejected/<slug>-why.md` |
| **media gate** | a picture the judge failed is HELD from delivery, with the reason | code (`tools/gates.py`) | `check.json` |
| name · record · deliver | the 13-field name, the `made` record, Drive through the API | `components/naming`, `components/gdrive-creator` | `ads/<slug>/manifest.json`, `report.md` |
| file | the batch's record to the repo-root `runs/` | code | `runs/image-production/<brand>/<batch>/` |

**A swipe** — `machine.py <swipe> …` walks the swipe's teardown steps 2 → 6
(`../image-teardown/tools/run.py`) and then `tools/run_production.py`: elements
gate on the brief → plates → `tools/judge.py` → media gate → `tools/render.py`
(draft · finish · type) → deliver → file.

**Dry run — spends nothing.** `machine.py --dry-run <batch-folder | swipe …>`
(or `run.py <batch-folder> --dry-run`) resolves, per concept: the `batch.json`,
the brand's folder, the template, the style pack, the picture format, the
prompt as it would be sent and the model it routes to, the product elements it
references and what the brand says is true of them, the packshot, the logo, the
palette, the fonts, the roster, the offer bank — OK or MISSING — then what the
elements and copy gates would say and where the record and the pictures would
go. No model, no generator, no judge; nothing written to the batch, to `runs/`
or to Drive. Exit 1 if anything required is missing. For a swipe it also runs
the teardown steps' own dry run. **`tools/finish.py --dry-run` is NOT this** — it
still calls the judge; it only skips filing and delivery.

**Elements.** Before anything is made, every id a batch or brief names is asked
of `components/elements/machine/elements.py`:

| Named by | Asked of |
|---|---|
| `template` (ad, else batch; a brief's `template`) — `prompted` means no layout file | `template/image` (built from `templates/*.json`) |
| `pack` / `style_pack` (ad, else batch, else `slots/<slug>.json`) | `style/image` (built from `style-packs.json`) |
| `picture_format` (ad, else batch) | `format/image` (built from `format-bank.json` — this is its first reader) |

`letterform-bank.json` is an element-library source too (`components/elements/sources.json` builds `letterform/image` from it), like the three files above; each is changed here and the library rebuilt (SI-135 (elements rows truthful)).

An unknown id is **refused, naming the real ids**. A draft row whose `what`
starts `[TO DEFINE` is refused as **named but not defined yet**. What was picked
is recorded in the run's `elements.json`. The ad's `format` field is NOT a
picture format — it is the ad name's own vocabulary (`components/naming`) and is
left alone.

**The brand is never a default.** Packshot, logo, colours, offer bank, roster
and the judge's product tests are read from `brands/<brand>/` for the brand the
batch names (`batch.json` `brand`), `--brand`, or — for a swipe — the brand
teardown recorded (`vars/brand_name.md`). With none of those, the tool stops
and says so. The judge's product tests are built from
`brands/<brand>/element-facts.json` (`tools/brand_facts.py`); a brand with no
facts on file gets one plain test and a note saying so.

## The four questions

- **Engine + owner:** `machine.py`, `run.py` + `tools/` (`paths.py` every path,
  `plates.py` the jobs, `prompt.py` the slots, `finish.py` and `judge.py` the
  judges, `render.py` the compositor, `gates.py` the gates and the filing,
  `dryrun.py` the dry run, `brand_facts.py` the brand's product truth). the owner.
- **Definitions + curator:** `templates/*.json` (hand-tuned layouts),
  `style-packs.json` (eight rendering registers + the result budget),
  `format-bank.json` (25 picture shapes). The judge's standing tests live in
  `tools/finish.py` and `tools/judge.py`. This tool keeps no `prompts/` folder:
  a batch's prompts are its own, saved verbatim in `runs/<brand>/<batch>/prompts/`.
  the owner.
- **The plane it emits:** `runs/image-production/<brand>/<batch>/` at the repo
  root — `batch.json`, `jobs.json`, `prompts-as-sent/<slug>.txt`,
  `manifests/<slug>.json`, `verdicts.json`, `rejected/*-why.md`, `elements.json`,
  `check.json`, `report.md`, `run.json`. **Text only — never a picture.**
  A BATCH's working folder IS its record folder, `runs/image-production/<brand>/<batch>/`
  at the repo root (pictures gitignored there and on Drive), since 2026-10-08
  (image-production#12, SI-49 (static runs home)); batches made before stay in
  this folder's `runs/` on the machine that made them, frozen, and `queue/`
  reads them there. The swipe road's per-run folders (`run_production.py`)
  still work in this folder's `runs/<run>/` until they move with
  image-teardown's runs. Pictures go to
  Drive (`batch.json` `drive_root`, through the API). Filing never stops a
  delivery: a failure prints `SKIP` and the reason.
- **Manifest per entry:** `run.json` — machine, brand, label, the files on
  record, `state` (`filed` or `held`) and, when held, why.

## Gates

Three of the five shared gates (`components/quality-checks`, via `hold()` →
`check.json` in the batch folder). `python3 tools/gates.py <batch-folder>` prints
it. `run.py … --gates warn` records the same verdict and carries on.

- **elements** — before anything is made. Every template, style pack and
  picture format named is a real, defined row in the element library.
- **copy** — before anything is made, on the words burned into the picture
  (`offer.bar_text` and each ad's `copy` slots). `unfilled_check`: no UNFILLED
  note. `price_check`: every price is one the brand's offer bank sells today —
  the entry under `offer.id` when the bank has one, else every price in the bank.
- **media** — after the judge. A picture the judge failed is HELD from
  delivery, named with the judge's reason. **The gate does not judge** — the
  verdicts are `finish.py`'s and `judge.py`'s, unchanged. Survivors still ship;
  holding one picture never holds its siblings. A hold is a work item, not a
  verdict (`PIPELINE.md` §4b): fix the prompt, never the picture.

Tests: `python3 tests/test_image_production.py` — stdlib, no network, no model.

## Known and not fixed here

- `queue/` (the RUN-01 production queue) still names one brand throughout and
  counts its way to the workspace root. It is one brand's queue, not the tool.
- `tools/finish.py` `add_asset()` writes one run's Drive folder name into
  `_drive-ids.json` paths.
- `PRODUCTION-BRIEF.md` is a dated test plan; its run command is the retired
  `batch.py`.
