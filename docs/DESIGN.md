# PRIZM — the design system for daemn.co

One system. Every page loads `studio.css` and adds nothing but layout.
`tools/design-check.py` runs on every commit and refuses a page that drifts.

Chosen 2026-09-22 after four directions were put side by side
(the moodboard artifact is recorded in `context/artifacts.md`).

## The idea

**Light through a prism.** One white beam goes into the glass and a full
spectrum comes out. The old LLC was Gradient Media; this one is Prizm, and the
name is also the colour rule.

So the page is **bone paper and warm ink**, the objects on it are **chrome**,
and **colour carries meaning** — every stop of the spectrum owns a job. That is
the whole reason this never becomes a rainbow.

Two registers, and a page needs both:

| | |
|---|---|
| **Surreal** | chrome objects floating in hard light at impossible scale, one soft spectral bloom, grain over everything |
| **Terminal** | mono labels, hairline rules, exact tabular numbers, tight radii — precise and unglamorous |

Take either half away and it reads generic: objects alone are a screensaver,
the instrument alone is a dashboard.

## The paper

Bone, never pure white. Warm near-black ink, never `#000`.

| Token | Value | For |
|---|---|---|
| `--bone` | `#EFE9E1` | the ground |
| `--paper` | `#F7F4EF` | a recessed panel, a table head, code |
| `--card` | `#FFFFFF` | a card that has to lift off the page |
| `--ink` | `#171512` | all reading copy |
| `--ink-2` | `#4B453E` | secondary copy — the floor; never dim below this |
| `--ink-3` | `#716960` | labels and signage only, never a sentence |

## The spectrum, with jobs

In the order light leaves the glass. A pill or a card edge in one of these
tells the reader what kind of thing it is **before** they read it.

| Token | Value | Job |
|---|---|---|
| `--violet` | `#6D3BF5` | swipes — what we took |
| `--indigo` | `#2F5BFF` | actions and links; the only hue that means "press this" |
| `--cyan` | `#00A8CC` | video |
| `--green` | `#12A06F` | ready · live · done |
| `--amber` | `#F09000` | waiting on you |
| `--coral` | `#F04A2E` | a stop, a rule, a refusal |
| `--magenta` | `#DB2A8C` | briefs |
| `--prism` | the sweep | **once per page**, as a hairline or a card's top edge |

`--hue` is whichever stop the current block owns; `.pill`, `.card.hued` and
`.label.hue` all read it, so a section sets one variable and its parts follow.

## Type

Three faces. There is no fourth.

| Token | Face | For |
|---|---|---|
| `--display` | **Unbounded** 600/800 | headings, the mark, a card's title |
| `--body` | **Plus Jakarta Sans** | everything read in sentences |
| `--mono` | **DM Mono** | every label, number, eyebrow, button and pill |

The **eyebrow** is the device that makes a page read as an instrument: a mono
label with the prism as its leading rule. Every section opens with one.

## Spine

- Spacing: `--s1` 4 → `--s9` 96, on an 8px spine. Gutter is `--gutter`.
- Radii: `--r1` 3 · `--r2` 8 · `--r3` 16 · `--r4` pill. Nothing else.
- One shadow, `--float`, and **only a floating object gets it**. Panels are flat.
- Numbers are tabular. `01/02/03` only where order actually carries meaning.
- Reading measure `--measure` (66ch). Grain sits at 4.5% over the whole page.

## The primitives

Shell `nav.bar` · `footer.bot` · `.wrap` (`.wrap-narrow`) · `.room` for a
full-bleed 3D layer · `.bloom`.
Type `h1–h4` · `.lede` · `.eyebrow` · `.label` · `.mono` · `.num` · `hr.prism`.
Blocks `.card` (`.hued`) · `.panel` · `.grid` (`.tight`) · `ol.steps` · `.rule`
· `details` · `.tablewrap` + `table` · `.pill` (`.swipe .video .brief .ready
.wait .stop`) · `.meta` · `code` · `pre`.
Controls `.btn` (`.ghost`) · `.btns` · `.go`.
Brief kits `.tabs/.tab` · `.acct/.post` · `.strip` · `.vgrid/.v` (`.torn`) ·
`.bwrap/.brief` · `.src/.vsrc` — a generated kit page carries markup and no CSS.

## Never

- Pure white or pure black.
- A second display face, or a font from anywhere but the system's Google Fonts line.
- The prism sweep as a background fill, or anywhere behind type.
- A colour used for decoration rather than its job.
- Dimming body copy to make hierarchy — size and the mono labels do that.
- A shadow on anything that is not floating.
- A page styling itself: raw hex, `rgb()`, `font-family`, radius or shadow in a
  page is what the check refuses.

## How a new page starts

Copy `_template.html`, keep the nav and footer, write the content with the
primitives, and keep page CSS to layout only (under 60 lines). Then:

```bash
python3 tools/design-check.py
```

The same check runs on commit. If a rule is genuinely wrong, **change the
system** — `studio.css` and this file — not the page.

## When the system changes

Bump the version on the stylesheet link in every page (`/studio.css?v=prizmN`).
Visitors cache the file aggressively; without the bump, a returning reader gets
the old system against new markup, which is how a page looks broken for exactly
the people who have been here before.

## Darker ink, real objects (2026-09-23)

Damon: the grey copy read too light. `--ink-2` and `--ink-3` are darker, labels
went from 10px to 11px, and sections have more air.

The chrome and glass objects are no longer only stills. `/objects3d.js` renders
each one in real 3D wherever a page puts `<div class="obj" data-obj="torus">`,
with the still inside as its poster. One renderer serves the whole page. Kinds:
prism, lens, ribbon, cube, torus, sphere, monolith, cards, and `glb:<file>` for
the desk models. Icons are `<i class="ib" data-i="name"></i>`, drawn by
`/studio.js` from one set, and wear the block's `--hue`.

