# The asks — what a brief wants made beyond the base cut

**Ruled 2026-09-22, Damon:** the editor or designer who picks up a brief
produces *"the extra scenes, variations, scroll stoppers, headlines, formats,
styles that the brief will detail."* Until now the brief detailed none of it —
the handoff ended at "here are the scenes, cut them." So every editor invented
their own list, or made nothing extra. This file fixes the list.

Brand-agnostic by construction: nothing here names a brand, a person or a
product. Those arrive from the brief.

---

## The six asks

Every handoff carries a section **`## THE ASKS`** with exactly these six lines,
in this order. Each line is either **specified** — a count and what drives it —
or **`none — <why>`**. A missing line is a missing decision, and the editor
falls back to the default below.

| ask | what it is | driven by | default when unspecified |
|---|---|---|---|
| **SCROLL STOPPERS** | alternative first three seconds | the brief's hook set — every hook not already the primary opener | 3, one per unused hook, same scene-1 setting |
| **HEADLINES** | on-screen headline lines for the opener card | the hooks, THE LOOP, the offer — the brief's own words | 5, under eight words each |
| **VARIATIONS** | alternate takes of a scene, same line, different framing | the opening and the offer scene | 1 each |
| **EXTRA SCENES** | inserts the base set does not cover | POST items and KNOWN ISSUES that leave a beat uncovered | one per uncovered beat |
| **FORMATS** | the 15-second cutdown map, and the 4:5 safe-crop check on every frame | the scene table | a 15 s cutdown map; a note per scene if any face, product or word sits outside the 4:5 window |
| **STYLES** | a visual restyle of the same film (`format-variation.md`) | only a style the brief names | none — a style nobody asked for is a remake |

## One ratio (ruled 2026-09-22, Damon)

9:16 only. Everything that carries meaning — faces, the product, every word on screen — sits inside the centred 4:5 crop (the middle 70% of the frame), so the one asset serves every placement. No 4:5 or 1:1 versions are made. When a swipe comes in 4:5 or 1:1, rebuild it at 9:16 with the subject inside the 4:5 window; if a choice between 4:5 and 1:1 is ever forced, 4:5 — 1:1 is never made.
The FORMATS ask is therefore two things only: the 15-second cutdown map, and
a check that every frame keeps its subjects inside the 4:5 window.

## The rules every ask obeys

1. **Same cast, same product.** Every ask is generated from the brief's cast
   references and product references — never from a fresh text-described
   person or product. That rule is the anchor rule from `BRIEF-SPEC.md`, and
   it does not relax for extras.
2. **Same locks.** Wardrobe, light, the skin rule and the do-not-include list
   carry into every ask unchanged.
3. **No new claims.** Headlines and stoppers use lines the brief already has.
   An ask is a re-arrangement of approved material, not new copy.
4. **Named to the brief.** `<brief>--<ask>--<n>` — `kzn03--stopper--2`,
   `kzn03--headline--4`, `kzn03--cutdown-15--1`. The queue and the delivery
   folder read the name.
5. **Owner rules on the extras too.** Asks are delivered into
   `briefs/delivered/<brief>/` with the base cut and listed in `DELIVERED.md`.
   Nothing is published from the asks folder directly.

## Where it is written and read

| who | does |
|---|---|
| `prompts/stage-6-handoff/` (v4) | writes `## THE ASKS` into every handoff from the production document |
| `tools/editor-onboarding/prompts/02-pull-briefs` | reads it; applies the default menu when a handoff predates v4 |
| `tools/editor-onboarding/machine/queue.py` | lists delivered asks per brief from the delivery folder |
