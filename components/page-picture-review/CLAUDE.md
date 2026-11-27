# components/page-picture-review — number a built page's pictures, and prove the copy

**page-picture-review** — takes **a page's `--state` folder and a page kit
that builds**, makes **`_preview-landing.html` with every picture slot numbered
and its decision painted, copies of `pic-index.js` and `pic-marks.js` beside
it, and fitted JPEGs in the kit's assets**. Does not **file a record on
`platform/data/`, commit or push**. Triggered by
`python3 components/page-picture-review/preview.py <cpk-root> --state <page-dir>`.

**Owner: the developer.** One owner, not two.

Rule 6 splits engine owner from definition owner where a component carries
curated content an engine executes. This one carries none. Geometry, the slot
table, decisions, notes and the list of tolerated absences are all a page's
property and live in its `--state` folder, which rule 5 puts outside the
component by definition. The component is code.

The face-scrub page's record is **the designer's** (2026-09-18) — that is ownership
of a page, not a role in here. A first pass at this file named her "definition
owner"; the developer asked what a definition owner would actually define, and the answer
was nothing, so the role came out and the one thing that looked like a definition
— the tolerated-absence list — moved to the page where it belonged.

Moved here 2026-09-18 from `runs/page-machine/Brand B/facescrub-cpk-01/review/`,
where it had grown by accident. A run folder holds the record of one execution;
this had become a reusable engine plus a live decision record, and both outlived
the run. the developer's ruling, same day: "why is this work in the runs folder in
general?" — it should not have been.

## What it is

A page kit builds a page. This numbers every picture slot on the built page,
paints the decision recorded against each one, and can prove a published copy
has the original's structure, fonts and image names (STRUCTURE MATCHES) — not
that every pixel is the same.

It is **the built page with an overlay added** — not a rebuild of it. The kit's
own build renders the page exactly as it deploys; the generator then rewrites the
built page's asset URLs so the file works from anywhere, strips the analytics
tags so a review does not fire pageviews into a live property, and appends the
overlay. Earlier versions reconstructed the page by resolving its template by
hand; that approximated it and quietly lost whatever the layout provided. Do not
go back to it.

## The contract

Every tool takes `--state <dir>`: a **page's own folder**, holding

| file | what |
|---|---|
| `page.json` | `kit`, `slug`, `page`, `assets_subdir` — which page this is |
| `slots.json` | filename → slot number, per breakpoint tree |
| `geometry.json` | per-slot target size, anchor, and fit mode, measured off the built page |
| `pic-state.json` | the decisions, one word per picture, absent = undiscussed — the words are the ones `pic-marks.js` writes and `pic-index.js` styles |
| `notes.json` | review notes drawn on a picture, keyed by badge id |
| `placements.json` | what was put where, from which master, fitted how, measured how |
| `known-missing.json` | references this page's kit makes and does not ship, with a reason each |

Without `--state`, `check` tolerates nothing: every unresolved reference fails
the gate. A page says what it is allowed to be missing; the engine has no opinion.

**Plane: none.** Every write goes to the caller's `--out` or into the page
repo it is pointed at; the `--state` folder is read, never written.

**Records (O12 (records adapter)):** none: no runs by design, for now — a decision stays in `--state` until RV-27 (per-asset feedback) settles a picture decision's record shape (the developer, 2026-10-07, triage page 7).

**Before you start (page-picture-review#5, 2026-10-08):** node, and `npm ci` in the page kit (`make_demo.py` runs `npx campaign-build`); `ffmpeg`, `ffprobe` and mozjpeg's `cjpeg` on PATH (`fit.py` shells out to all three).

- **Takes:** a `--state` folder and a page kit that builds (`npx campaign-build`).
- **Makes:** `_preview-landing.html` with the overlay, copies of `pic-index.js`
  and `pic-marks.js` beside it, and fitted JPEGs in the kit's assets.
- **Never:** a record on `platform/data/`, a commit, a push.

**Nothing brand-specific lives in this folder.** No slug, no kit name, no
geometry, no default that names a brand — workspace rule 7, and it is checked:
`grep -E "Brand B|face-scrub" *.py *.js` returns nothing. A second page is a
second `--state` directory, not a fork.

## The tools

- `preview.py <repo> --state <dir> [--no-build]` — **the loop.** Regenerates,
  runs the publish gate, checks a server is rooted correctly, prints a
  cache-busted URL. About a second with `--no-build`.
- `fit.py <master> --slot N [--mobile] --repo <r> --state <dir>` — put a
  generated master into a slot: reproduce the browser's cover-crop at the slot's
  own anchor, encode, report what the fit cost. `--dry-run` shows the crop
  without writing. `--batch` only when order is genuinely arbitrary.
  **`--selftest` replays a recorded placement and must pass.**
- `bundle.py stage|check|compare` — stage a self-contained copy, refuse it if any
  local reference does not resolve, diff two rendered fingerprints.
- `fingerprint.js` — measures what the browser actually drew, for `bundle.py
  compare`.
- `make_demo.py`, `pic-index.js` — the generator and the overlay itself.

## Where output lands

Nothing here writes into this workspace. Every file lands inside the page
repo the tools are pointed at, or in the system temp folder:

- `fit.py` encodes into `<repo>/<kit>/src/<slug>/<assets_subdir>/`, through
  `/tmp/fit-stage.ppm`.
- `preview.py` runs `make_demo.py --out <repo>/review/`. That writes
  `_preview-landing.html`, copies the two overlay scripts and links the
  `--state` files there. Without `--out`, `make_demo.py` writes beside the built
  page in the kit's `_site/`, which `campaign-build` itself fills.
  `make_demo.py` refuses an `--out` inside the workspace that is not under
  `runs/` (K2 (brands write wall), page-picture-review#4); outside the
  workspace — the kit's repo, a temp folder — is unchanged.
- `bundle.py stage` writes only to its `--out`; `preview.py` stages it in the
  system temp folder.
- A mark saved on a published page goes to that page's own store
  (`pic-marks.js`), never the repo.

The page repo's origin is an outside vendor's (page-picture-review#8). Nothing in this component runs git. A
commit or push to that repo is a person's act, never a machine's: a push there
is an external send.

## THE BIRTH RULE (with the component, 2026-09-18)

**A page's geometry is measured off the built page, never copied from a brief.**

The brief for the face scrub said the hero box was 1440 wide. The browser said
1425. The brief had been generated from a hand-typed table, and every generation
target derived from it was wrong. `geometry.json` holds measured values and the
browser is the authority. A slot with no measured entry is an error, not a guess.

## Why `check` refuses rather than warns

A demo published with a regex over its HTML lost two brand webfaces: the page
names a stylesheet, which `@import`s a fonts stylesheet, which names four `.woff2`
files the page never mentions. It published clean and every line of type fell
back to a system sans. The asset set is a **graph**, not a list. `stage` walks it
transitively and `check` exits non-zero when a local reference does not resolve —
wire it before any publish and that class of bug cannot reach a reviewer.

Careful staging still cannot *prove* a copy matches. `fingerprint.js` +
`bundle.py compare` can: they read what the browser drew, at one viewport, and
diff it. Run it when a published copy looks wrong.

## Known limits

1. **Scripts are not statically analysable.** `check` does not follow `.js` —
   a script builds URLs at runtime. The render fingerprint covers them instead.
2. **Lazy images read as broken when measured cold.** `fingerprint.js` forces and
   scrolls first; anything else measuring images must do the same.
3. **Notes are inlined at build time; only decisions poll live.** Change
   `pic-state.json` and an open page updates within 2s. Change `notes.json` and
   you must regenerate.
4. **Not every slot is a cover box.** Some keep their own aspect and bleed;
   `geometry.json` carries `mode: native` for those.
5. **Publishing needs a Claude session**, and an artifact can only be updated by
   its owner. One publisher per link, until that is decided otherwise.
