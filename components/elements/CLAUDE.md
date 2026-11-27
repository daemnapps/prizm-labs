# elements — the one element library

**elements** — takes every element list in the system (formats, structures,
frameworks, styles, delivery, templates, doctrine), makes **one library in one
shape** and the one lookup every tool asks *"is this a real one?"*. Does not
edit any list — a list is changed at its source. Triggered by
`python3 components/elements/machine/elements.py build`.

**Owner:** the owner (definitions and engine). Built 2026-09-20 on the owner's word:
*"If we have these different formats, structures, frameworks, styles, we need
to define all these unique elements… Things aren't enforced… Everything needs
to be green light."* Not the developer's; touches nothing of the developer's.

## The elements, defined — nothing interpreted

The source of truth for which lists exist is `library/index.json` (built from
`sources.json`); this table follows it, and `library.html` renders every list it
carries (SI-135 (elements rows truthful)).

| Element | The one question it answers | Lists (per asset) |
|---|---|---|
| **format** | what kind of asset is it — its shape and who carries it? | video · image · carousel · email · page · copy |
| **placement** | where does it run? (Meta primary text, a subject line, a landing page) | all |
| **structure** | what are its beats, in what order? | video |
| **framework** | what is the argument's plan? (PAS, story, mechanism-led…) | all |
| **style** | what does it look like? | image · video · caption |
| **delivery** | how does it sound? — one list per dial | humor · delivery style · register · pacing · reference world · avoid |
| **template** | which build layout? | image · email |
| **doctrine** | where the reader is, and how the argument works | awareness · sophistication · technique · section |
| **letterform** | what lettering does it use? | image |

Brand elements — avatar, sub-avatar, angle, offer, product, proof, story —
belong to each brand and live in `brands/<brand>/`, not here.

## The same fields on every row

`id · name · what · why_it_works · status · state · signed · examples · evidence · aliases · note ·
source · extra`. `status` is components rule 6's `draft` / `approved` / `deprecated` only; any other word a source carries (unreviewed, proposed, seed, proven) is its `state` (the developer, triage page 15, 2026-10-07; SI-79 (elements status words)). `approved` is true only when `status` is approved. Everything else is a draft until the owner signs it. `build` lists a row whose status is off rule 6 under `off_status`.

## Files

| File | What |
|---|---|
| `sources.json` | every list and where it lives — the only map |
| `additions.json` | rows the owner has named that no list holds yet (drafts) |
| `machine/elements.py` | `build`, `list`, `get`, `check`; import it to enforce; `use(library)` switches the library and clears the row cache (SI-100 (elements use seam)) |
| `machine/page.py` | the library page |
| `library/` | built — never edited by hand |

## The four questions

- **Engine + owner:** `machine/elements.py`, the owner.
- **Definitions + curator:** the source lists (each in its tool) and
  `additions.json`; the owner signs rows.
- **The plane it emits:** none. `library/` (one file per list plus
  `index.json`) and `library.html` are a regenerated projection of the
  definitions — rebuilt by `machine/elements.py build` and `machine/page.py`,
  read by import (`get`/`check`), never a run record.
- **Records (O12 (records adapter)):** none: no runs by design (the developer, 2026-10-07, triage page 7).
- **Manifest per entry:** the row fields above, with `source` naming the file
  it came from.
