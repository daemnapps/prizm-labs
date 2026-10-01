# The chain

Seven stages, mirroring the copy machine (`copy/docs/the-chain.md`)
stage for stage where a page and a piece of social copy do the same job, and
adding the one stage only a page needs. Established 2026-09-11.

## What goes in

A captured swipe page — the visible text of a competitor's landing page,
advertorial or listicle, from the swipe library's `landing-pages` pool, pulled
on a match (category or avatar; `swipes/SWIPES.md`). The source is
structure. Our brand, our avatar, our angle and our funnel are declared on the
run and never inferred from the source.

## The stages

### 0 · Triage — `stage0-triage-v1-damon.md`
Page job (`PRE-SELL` hands off, `OFFER` takes the money — this chain builds
pre-sells), the classifier's format confirmed or disputed but never overruled,
voice and its binding, funnel level read off what the source explains.

### 1 · Read — `stage1-read-v1-damon.md`
Observation only. Sections in order with lines **quoted, never paraphrased**;
the headline in full; the turn (or `no turn`); every specific proof; every ask
and what it says about price, guarantee and scarcity; voice markers; what the
page conspicuously never does.

### 2 · Spec — `stage2-spec-v1-damon.md`
The record abstracted into a **brand-free, category-free construct**: numbered
moves, each with its job, what it needs, its slots; sequence logic; proportion
as shares; the voice construct; what is load-bearing; what is page-bound (a
timer, a credential, a star row) and what job each was doing. The test: usable
for a supplement, a skincare product and a piece of software.

### 2b · Context scout — `stage2b-context-scout-v1-damon.md`
Indexes the brand tree at run time — every file with its own `status`,
`contested` and `known-issues` lines — and picks what *this* construct needs,
finishing "the page will be different because this was read" for every file
and publishing what it deliberately left out.

### 3 · Injection — `stage3-injection-v1-damon.md`
Fill the slots. Substitution, never rewriting. Every figure from the offer or
product file; reviews reused, never written; the narrator a cast persona; a
page-bound device the brand cannot honestly use is named and its job refilled
or left `[UNFILLED]`. Substitution log and collisions come out with the page.

### 4 · Close — `stage4-close-v1-damon.md`
The one objection at the flinch, from the objection bank; the handoff to the
offer page with the guarantee verbatim and its condition attached; no urgency
the offer file does not carry; no dated result promise. Assembles the base
page end to end.

### 5 · Variation — `stage5-variation-v1-damon.md` · **once per sub-avatar**
The stage the copy chain does not have. The base page speaks to the core
avatar; each variation speaks to one sub-avatar — the same woman plus the one
narrowing element her card names. Same moves, same proportions, same offer,
same mechanism; her way in, her delta vocabulary, her reviews, her card's
cautions. Reports what changed move by move.

### 6 · Brief — `stage6-brief-v1-damon.md` · one per page
What the builder opens: the manifest block (the page's key, from
`components/naming/PAGES.md`), the copy in page order under numbered section
headings, the offer it hands to verbatim, what to watch, what is unresolved.

### 7 · Layout — `stage7-layout-v1-damon.md` · once per page
The words are settled; this stage makes them a page. It reads the section
library (the kit's `_blocks.json`: every block, what it is, every slot) and
picks the block whose *job* carries each move, fills every slot from the words
(substitution — an empty slot beats an invented line), and writes a brief for
every picture slot: subject, action, framing, light, which brand photograph to
attach, what must not appear. It also says which library furniture it left
out and why (press strips, timers, before/afters the page cannot honestly use).

### 8 · Pictures — `machine/pictures.py`
Each brief becomes one generation on the general photoreal model, with the
brand's product photographs attached by id. Rules from the image lane's
method bind: no text drawn, no equipment named, nobody younger than the
avatar, the material from the reference. Results are pulled into the brand's
page-kit project by picture id, so a variation page reuses the base page's
pictures and generates only its own.

### 9 · Build — `machine/scaffold.py`, `machine/build_site.py`
The scaffold makes a page-kit project for the brand from the kit and the
brand's identity file (its web tokens, its marks). The build writes the page's
front matter from the layout, adds the funnel's legal strip, runs the kit's
build, rewrites asset paths to where the funnel serves them, points every ask
at the offer page with the funnel's own tracking, and places the page.

## What was dropped from the copy chain, and why

- **Placement** — a page's product enters where the construct's turn is; there
  is no separate length budget to argue, the proportions are the construct's.
- **Hooks** — a page has one headline, and it is a slot in the construct, not
  a set of openings to ship. Headline tests are a variant page, named as such.
- **Expansion** — a swipe page is always already selling. There is no organic
  lane for a landing page.
- **Render** — the brief carries the copy in page order; the funnel's repo
  renders it.
