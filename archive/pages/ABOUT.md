# page-production — the page machine

**page-production** — takes **a source page and a brief** (brand, avatar, signed
angle, funnel, product, offer), makes **the page — copy, layout, pictures**.
Does not **deploy**. Triggered by `python3 machine/run.py <page.txt> --brand <brand> …`.

One swipe page in, one page out in our avatar's own words, then one variation
per sub-avatar — each laid out on the section library with a picture brief per
section. How the chain is shaped and why: `CLAUDE.md`, `docs/the-chain.md`.

## The commands

Everything runs from this folder. `--brand` is always said; nothing here has a
default brand.

**See what would be sent, spending nothing**

    python3 machine/run.py <page.txt> --brand <brand> --avatar <avatar> --angle <angle> \
        --funnel <funnel> --next <offer page> --label <label> --source-url <url> \
        --product brands/<brand>/products/<card>.md --dry

Fills every stage's prompt from the brand's files and writes each one as
`stageN--sent.md` in the run folder. Calls no model. The copy gate does not run
(there are no words yet).

**Run it**

Same command without `--dry`. Useful extras:

| Flag | What it does |
|---|---|
| `--offer <file> [<file> …]` | the offer files the page's prices come from (default: `brands/<brand>/offers/offer-bank.md`) |
| `--subs <sub> [<sub> …]` | one variation per sub-avatar |
| `--swipe <id>` | the swipe registry id of the source page |
| `--context-drop <fragment> …` | files the context scout may not load (a sister product's card) |
| `--no-gate` | skip the copy gate |
| `--model <model>` | force one model for every stage (default: each stage's tier — reading stages on the checks model, writing stages on the designs model) |

**Pick a run back up**

    python3 machine/run.py … --label <same label> --resume

Keeps every finished stage whose prompt is unchanged and whose inputs did not
rerun; reruns the rest. A bumped prompt version reruns that stage and everything
it feeds. This is also what to run after the account runs out of usage — the run
stops with one line and loses nothing.

**Hand the words over**

    python3 machine/deliver.py <label>            # refused if the run is HELD
    python3 machine/deliver.py <label> --force    # carry a held run anyway; the page says so

**Then**

    python3 machine/layout.py <label> [--only base|<sub>] --product-dir brands/<brand>/products/<product>
    python3 machine/pictures.py <label> …         # writes the picture requests, records the results
    python3 machine/build_site.py <label> …       # renders the page on the section library
    python3 machine/copy_page.py <label> [--title …] [--lede …] [--before-label …] [--after-label …]
    python3 machine/board.py                      # redraws the board: every run, every prompt as sent, every output
    python3 machine/page_gates.py <label>         # why a run is held, plainly

## Gates

| Gate | When | What it checks | If it fails |
|---|---|---|---|
| **inputs** | before anything runs | the angle is signed active in `brands/<brand>/strategy/angles.json`; the brand and an offer file exist | refused, nothing called |
| **elements** | before anything runs | the page format the classifier read is a real row in the element library (`format/page`) | refused, naming the real formats |
| **elements (recorded)** | after stage 3 | the doctrine sections the page says it carries, against `doctrine/section` | unknown ones are written into `run.json` as unknown — never a stop |
| **copy** | after the words are final | the base page and every variation: no `UNFILLED` note left. A figure the offer files don't sell is FLAGGED in `check.json` (a page carries "$7 Value" and "Save $26", which are not sale prices) — never a hold | **HELD** — everything is saved, `check.json` says why, the run exits 2, `deliver.py` refuses it |

The checks and the hold are the shared ones (`components/quality-checks`); the
lists are the shared library (`components/elements`). This folder owns neither.

## Where a run lives

`runs/page-machine/<brand>/<label>/` at the repo root: `run.json` (what was
declared, the elements picked, every stage's model, prompt name and hash), the
source as read, every `stageN--sent.md` and output, `check.json`, and from
layout on the layout and picture records. The old `runs/` beside the code is
still read by every script here; nothing new is written to it.

## Tests

    python3 machine/test_rollout.py

No network, no model. They file into a temp folder and never touch a real run.
