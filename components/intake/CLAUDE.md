# intake — one front door for every swipe

**intake** — takes **every swipe already saved** (a video, an image or
carousel, words, a page, an email — paid or organic, ours or a competitor's),
makes **one swipe record per swipe**: its `source`, its asset kind, where the
asset is, the brand it was swiped for, its format if its pool knows one, and
which teardown it goes to — filed as one index under
`runs/intake/<brand>/<label>/`. Does not **tear anything down, fetch, scrape,
label a format, or call a model**. Triggered by
`python3 components/intake/tools/run.py --brand <brand>`.

**Owner:** the owner. Built 2026-09-20, rollout Step 4 (BLUEPRINT.md §6): *"We
shouldn't be organic swipes and paid swipes… where a swipe came from is a
field, not a tool."*

**Front door — the swipes index (2026-10-28):** one living row per swipe across every pool, with its teardown run and brief numbers, at `runs/intake/<brand>/SWIPES-INDEX.json` (machines) and `runs/intake/<brand>/SWIPES.md` (people); it also regenerates the Drive front door `Shared Assets/SWIPE LIBRARY.md`. Built by `tools/swipes_index.py`, rebuilt by every intake run; besides the pools it reads every other place a swipe is kept (`PLACES`: picture-teardown sources, the strategist's picks, research rounds, copy swipes, the lab registries), one row per swipe with `also_in` for a second place, and the Drive page lists today's `swipe/` pool folders. **Tools read it first** (`swipes_index.find_swipe(brand, id_or_url)`) instead of re-reading the pools. Tests: `tests/test_swipes_index.py`.

## The two swipe folders are still where swipes LIVE

`components/swipe-paid/` and `components/swipe-organic/` are live tools with
their own boards (My Feeds on 8820 — which carries the saves since Swipe
Studio was retired 2026-09-22 — the paid library on
8780), their own morning jobs and other sessions working in them. **Swipes are
still SAVED there, by those tools, in the shape those tools write.** Nothing
was moved, renamed, or reshaped, and this tool never writes to either folder.

**This folder is the one place they are READ from as one.** Anything that needs
"every swipe, whatever its source" asks intake; anything that finds or saves a
swipe still does it in the swipe folder it always did.

## What a record is

| field | what it says |
|---|---|
| `id` | `swipe:<lane>:<where>:<ref>` — the same id `swipe-paid/corpus.py` mints, so it joins the paid library |
| `source` | `paid` · `organic` · `own` — where we found it |
| `owner` | `competitor` · `own` · `creator` — whose it is (`--source competitor` matches this) |
| `kind` | `video` · `image` · `carousel` · `copy` · `page` · `email` — read off the asset; `unknown` when the asset does not say |
| `route` | `video-teardown` · `image-teardown` (images and carousels) · `copy-teardown` · `page-teardown` · `email-teardown` · `unrouted` |
| `swiped_for` | the brand, discovered from the folders (a feed named `<brand>--…`, an item's `brand_fit`, the ad account in `brands/<brand>/meta/account.json`) — or `shared` when the pool does not say |
| `asset` | `url` · `file` (repo path) · `drive` (Shared Assets path or link) · `thumb` |
| `format` / `format_state` | the label its pool carries · `known` / `empty` / `unknown-format` |
| `structure` / `structure_state` | organic videos only — the organic-structure read · `known` / `empty` / `unknown-structure` |

**Format and structure are different elements.** A paid ad's `format` is
checked against `format/<kind>`. What swipe-organic calls a post's "format" is
an organic **structure** and is checked against `structure/video`. Neither list
is asked the other's question.

## Gates

Both run through `quality_checks.hold`; `check.json` is keyed by gate.

| Gate | Sits | Asks | Mode |
|---|---|---|---|
| **inputs** | before anything is read into an index | are both swipe pools where they live, holding something readable? is every pool file readable (an unreadable one holds, named, intake#4 (corrupt pool holds))? with `--source own`, is the own-ads cache here (intake#5 (own cache hold))? is `--brand` a real folder under `brands/`? | always holds |
| **elements** | after every swipe is normalised | is every `format` (and organic `structure`) a swipe carries a real row in the element library? | `--gates hold\|warn` — **default `warn`** |

**Why `warn` is the default, plainly:** today's pools carry labels the library
has never seen (one judged paid format, ~50 organic structure reads named
`new:…`). On `hold` no index could be built until those are fixed at their
source or signed into the library — the owner's call, not this tool's. On `warn`
the index still files, **each such swipe is marked `unknown-format` /
`unknown-structure` with the real ids beside it, and `check.json` still says
HELD.** Never silently passed, never invented. Flip to `--gates hold` once the
pools are clean.

## Rules for working here

- **Read-only on both pools.** No write, move, rename or reshape — ever, from here.
- **No format is ever filled in here.** An empty format stays empty and is
  counted. Labelling is a separate pass that needs a model and the owner's sign-off.
- **No brand in code.** Brands come from `brands/`, advertisers and feeds from
  the pool folders.
- **No model, no network.** Kind comes from the asset. Every run is free.
- Paths are found by walking up; `AI_WORKSPACE` points it at another workspace
  (a worktree reading the live pools; the tests' fake one).
- Tests: `python3 components/intake/tests/test_intake.py`,
  `tests/test_label_guard.py` and `tests/test_pool_fixes.py` — a temp workspace
  with tiny fake pools; never the real pools, `runs/` or `brands/`.

## The four questions

Answered 2026-09-23, when this folder owed them as a resident
(`components/CLAUDE.md`).

- **Engine + owner:** `tools/run.py` — reads both swipe pools and every other
  saved source, writes one record per swipe, runs two gates. Nothing here
  fetches, scrapes, labels a format or calls a model. **the owner.**
- **Definitions + curator:** none of its own. The asset kinds and the routes
  come from the pools it reads; a format, where one is known, comes from
  `components/naming/`, which is the only decider of `format`. Inventing a
  kind or a route here would create a second vocabulary that drifts.
- **The plane it emits:** `runs/intake/<brand>/<label>/` — one index per run,
  a row per swipe carrying its source, kind, asset location, brand and
  destination teardown. No media: this tool points at assets where they already
  are and copies nothing.
  A label is one plain folder name; anything else, or one that resolves
  outside `runs/intake/<brand>/`, is refused with exit 2 (intake#1).
- **Manifest per entry:** the index row itself, with `source` and `kind`
  required. A swipe whose asset cannot be located is reported, never dropped
  — counted as `asset_not_located` by source and kind in summary.md and
  run.json (intake#8 (asset not located)).

## Two things that are open, not settled

- **The Drive carve-out (O9).** The media stayed on Drive at its lab path when
  the code moved into `components/`, so the mirror above still reads as a lab
  path. The standing ruling is that Drive is reached by fileId through the API,
  not by the mounted folder. Migrating is its own card; until it lands, the lab
  path is deliberate, and this file says so rather than leaving it to look like
  an oversight.
- **A records adapter (O12): none yet.** The convention allows "an adapter or
  'none yet' stated"; this states it. Worth knowing for whoever builds one:
  `chain_records.py` is cheap because it did not mint a kind — it files onto an
  existing one and distinguishes itself with a single constant. One shared kind
  behind one adapter is 50–100 lines per component; a kind of its own is
  450–650 plus a manifest plus worker wiring.
