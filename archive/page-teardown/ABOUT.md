# Page teardown

One of the five teardowns (video · image · copy · page · email). A landing page
goes in; what comes out is the page taken apart: what each section does, which
library rows the page is, and its construct — the argument's mechanics with the
seller, the product, the figures and the subject all stripped out, so any brand
can be injected into it later.

It reads a page that is **already saved to a file**. It never fetches one, never
writes a page, and never builds, lays out or deploys one. Steps, gates and where
everything lands: `CLAUDE.md`.

## One command

```
python3 tools/run.py <saved page file> --brand <brand> [--source-url URL] [--label L]
                     [--dry-run] [--rerun-from tear1|tear2|tear3] [--model M]
```

- `<saved page file>` — an `.html` save of the page, or a `.txt`/`.md` text
  capture (the `page.html` / `page.txt` pairs page production already keeps
  under a run's `source/` folder both work).
- `--brand` — required, no default. Where the run files
  (`runs/page-teardown/<brand>/<label>/`) and whose own names the construct is
  checked against.
- `--source-url` — where the page was saved from. Recorded, and used to know
  the seller's name. Never opened.
- `--label` — defaults to the saved file's folder name when the file is called
  `page.*` or `index.*`, otherwise the file's own name.
- `--dry-run` — free. Shows the page's size before and after the reduce, what
  the code flagged, the model each step would use and where it would file.
  Calls no model, writes nothing.

## What happens, in order

| | Who does it | What it costs |
|---|---|---|
| The page is reduced to readable, numbered lines: scripts, styles and tracking dropped; headlines, pictures, buttons and links kept in page order; a second phone-sized copy of the whole page dropped | code | nothing |
| Menu, footer, cookie bar, pop-up and legal lines are flagged; template tags and filler showing as text are flagged; the page classifier says what format it reads | code | nothing |
| **tear1 — the read**: sections `S1…` quoted exactly, page furniture `F1…`, source defects `D1…`, each under its own heading, plus the names and figures the page carries | the `reads` model | 1 call |
| The furniture section is cut out of the record before anyone else sees it | code | nothing |
| **tear2 — the labels**: format, framework, and one section label per `S`, each checked against the element library — an id the library does not hold is refused | the `checks` model | 1 call |
| **tear3 — the construct**: the moves, the sequence logic, proportion, the voice rules, what is load-bearing, what is page-bound | the `designs` model | 1 call |
| Gates: inputs · elements · copy (no names, **no money figure at all**, no furniture, no defect, no UNFILLED) | code | nothing |

A real run is **3 model calls**. A finished step is reused on the next run; a
changed saved page is read again from the top.

## Looking at the pieces without running anything

```
python3 tools/furniture.py lines <saved page file>      the page as the read step is handed it
python3 tools/furniture.py scan  <saved page file>      what the code flags, and the size before and after
python3 tools/elements_label.py candidates              the library rows the labelling step chooses from
python3 tools/gates.py <run folder>                     a run's gates, plainly
```

## Prompts

| Step | File |
|---|---|
| tear1 | `prompts/tear1-page-read-v1-damon.md` |
| tear2 | `prompts/tear2-element-labels-v1-damon.md` |
| tear3 | `prompts/tear3-construct-v1-damon.md` |

Each opens on the invented-example guard, names no brand and no product
category, and asks for its answer in labelled slots. A changed prompt is a new
`-v2-` file beside the old one; the highest number runs.

## Where this sits beside page production

Page production (`pages/`) reads a source page in its own first three
stages and then goes on to inject, close, vary, brief and lay out. This tool is
that reading, stood up on its own, the same way every teardown is built.

| Page production today | Here |
|---|---|
| stage 0 triage — page job, voice, funnel, length; binds the run's avatar, angle and hand-off page | folded into `tear1`'s THE PAGE AT A GLANCE — the source's facts only; nothing about our avatar, angle or hand-off, which belong to production |
| stage 1 read — sections, headline, turn, proof, asks, voice, absences | `tear1` — the same record, plus numbered sections, furniture and defects kept apart, and a STRIP block the gates check against |
| stage 2 spec — the brand-free construct | `tear3` — the same parts, plus: no figures at all, never shown the furniture, `from S…` on every move, a LEFT OUT line, and a copy gate that holds a leak |
| format from the classifier, looked up in `format/page` | `tear2` — the format labelled from the record against `format/page`, with the classifier's word recorded beside it; plus a framework and a section label per section, which production does not label today |
| reads a `page.txt` capture with menu and footer still in it | reads the `.html` save (or the same `.txt`), reduced and flagged in code first |

Nothing in `pages/` was changed. **A side-by-side test** before anyone
points production at this: run both on the same saved page, then compare (1)
production's `stage2--spec.md` against `tear3--construct.md` move for move;
(2) whether production's stage 3 injection, handed this construct in place of
its own spec, fills every slot; (3) the classifier's format against `tear2`'s
label; (4) cost — production spends three calls (checks, checks, designs) on its
reading; this spends three (reads, checks, designs).

## Tests

```
python3 tests/test_page_teardown.py
```

Standard library only, the model stubbed, everything in a temp workspace.
