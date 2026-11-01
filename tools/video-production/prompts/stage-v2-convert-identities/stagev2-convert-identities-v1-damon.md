Convert this production's approved assets into the target style — the
characters, the world, and the product — WITHOUT redesigning any of them.

**Every example in this prompt is illustrative only.**

This is the step where a variation goes wrong. The failure is always the
same: generating a "new base" from a written description instead of
converting the asset that already exists. That produces characters who are
not the approved people, and a product that is not the real product. The
correction is absolute — **convert the refined source, never re-describe
it.**

You are writing the conversion instruction for each asset. You are not
generating anything; the machine does that from what you write.

---

THE STYLE FORMULA

{style_formula}

THE PRODUCTION

{production_document}

THE ASSETS THAT ALREADY EXIST

{approved_assets}

---

Return exactly these sections.

## SOURCE CHECK

A table, one row per asset that must be converted — every character, the
location plate, the product, and any load-bearing prop.

| Asset | The approved source | Kind |
|---|---|---|

**The approved source** is the actual thing being converted: a character's
trained identity or canonical master, the location plate from the original
film, the real product photograph. Name the file or record.

If an asset has NO approved source — nothing to convert from — mark it
`⚠ NO SOURCE` and stop the row there. **Do not invent one.** A missing
source is a person's job to supply, and the variation waits.

## THE CONVERSION INSTRUCTIONS

One block per asset, in this shape:

> **<asset name>** — convert from `<source>`
> <the style formula, verbatim>
> Keep unchanged from the source: <the specific things that make this
> asset itself — a character's face, hair, features and proportions; the
> room's exact spatial layout and every object's position; the product's
> shape, label wording and colour>.
> Change only: the rendering.
> <this style's own must-nots, from the formula's failure list>

The "keep unchanged" line is the load-bearing one and it is different for
every kind of asset:

- **Characters** — same face, same hair, same features, same build, same
  locked wardrobe. The person is recognisable as themselves, drawn
  differently.
- **The location** — every fixture in the same place. The blocking ledger
  is written against this geometry; move the sink and the blocking breaks.
- **The product** — same shape, same label wording, same colours. The label
  stays legible. A restyled product is still THIS product.

## WHAT THE CONVERSION MUST PRESERVE ACROSS ALL ASSETS

A short list of the invariants that survive any restyle, taken from this
production: the wardrobe locks, the room's geometry, the product's identity,
and each character's recognisability. This list is what the QC gate checks
against.

---

Write the three sections and nothing else.
