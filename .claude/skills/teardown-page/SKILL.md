---
name: teardown-page
description: Run the page teardown — a landing page already saved to a file goes in; its section-by-section read, its element labels and its name-free, figure-free construct come out. Use whenever someone says "tear down this page for <brand>", "tear down this landing page", "strip this sales page to its structure", "page teardown", "what's the construct of this pre-sell", or hands over a saved .html page or a text capture and names a brand.
---

# Page teardown

> **Not a component:** runs lab code in `lab/the owner/page-teardown` — runs lab code.


External dependencies: `lab/the owner/page-teardown/` (the machine), `brands/<brand>/` (the run folder; `products/store.json` when the brand keeps one, for its own names), `components/elements` (the library), `components/naming/classify_pages.py` (called for a free second opinion on the format).

**One command. The page must already be saved — this tool never fetches.**

```
python3 lab/the owner/page-teardown/tools/run.py <saved-page.html or .txt> --brand <brand> [--source-url <where it was saved from>]
python3 lab/the owner/page-teardown/tools/run.py <saved-page> --brand <brand> --dry-run
```

- The source is an `.html` save or a `.txt`/`.md` capture. A link alone is
  not a source: save the page first, then run. `--source-url` is recorded
  (to know the seller's name) and never requested.
- `--brand` is required; there is no default.
- **`--dry-run` spends nothing** — reduces the page, resolves and fills every
  prompt, shows sizes and the model per step, makes no model call, leaves no file.
- After a hold: fix the prompt (a new `-vN-` file) or the saved page, then
  `--rerun-from tear1|tear2|tear3`. A plain re-run of a held construct holds
  again — a finished step is reused as it stands.

## What it does

The free reduce (scripts, styles, tracking and the phone-sized duplicate
dropped; menu, footer, cookie bar, pop-ups and legal lines flagged) → the
read (sections `S1…`, page furniture `F1…`, defects `D1…`) → element labels
(the page's format, its framework, one label per section) → the construct.

## The rules the command enforces — do not work around any of them

1. **It does not fetch.** Ever.
2. **The strip is done in code.** The furniture section is taken out of the
   record before the labelling and construct steps run; they see item
   numbers, never the words.
3. **Every label is a real library row** or an honest `none-fits` with a
   proposed row. An unknown id is refused with the real ids named. A section
   the record numbered and the answer skipped holds the run.
4. **The construct carries no money figure at all** — any `$`, `£`, `€`
   amount holds it, the source's or not. A construct carries a slot for a
   figure, never a figure. Also: none of the source's own figures, none of its
   names, no furniture phrase, no UNFILLED note; it ends on its LEFT OUT line.
5. **Three gates:** inputs · elements · copy (twice). A held run says why in
   `check.json`.
6. **No brand in this folder. No default brand.**

## What comes back

`runs/page-teardown/<brand>/<label>/` — `source--as-read.md`,
`tear1--record.md`, `elements.json`, `tear3--construct.md`, every prompt as
sent, `run.json`, `check.json`.

Report: the format and framework it labelled, the section count, the
construct in one line, and whether it was held and why.

Reply with the result and the folder it landed in (repo path or Drive folder name).
