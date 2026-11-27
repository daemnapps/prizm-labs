# Templates — the layout is ours, the words are the model's

Each file here is a finished, hand-tuned ad format: every position, size,
colour, measure and gap fixed by a person and adjusted until it looks right.
The chain never writes these numbers. Stage 6 names one of these templates
and fills its slots with copy; the builder draws it.

**Ruled 2026-09-01.** Before this, every brief authored its own geometry.
Every run invented a different layout and every run broke in a different
way — a missing ground colour, then a missing picture band, then missing
panels, then a black panel on every zone with white type on it. None were
copy problems; the words were fine every time. The formats repeat and the
words do not, so the formats get built once and kept.

## What is here

| Template | Shape | Use it when |
|---|---|---|
| `photo-strip` | Editorial top · photograph in a band · offer panel at the foot | The proof is a close-up of the product being used |
| `confession` | Warning mark · confession opener · reason · product cluster with sticker callouts · close | The angle is an admission or apology that turns into the offer |
| `full-photo` | Full-bleed photograph · wordmark · white frame around the damage · claim panel | The picture carries the proof and the copy is one hard claim |
| `confession-lora` | The `confession` shape, with the plate generated through the product's trained reference | The confession needs the real product rendered into the scene |
| `pedestal` | A rendered world · the product standing on a pedestal in the lower half · the claim across the sky | The pattern interrupt IS the ad — an unusual made world that stops the scroll |

These five files are the element library's `template/image` list
(`components/elements`). A batch or brief that names a template not in it is
refused before anything is made (`tools/gates.py`); after adding a file here,
rebuild the library (`components/elements/machine/elements.py build`).

## Slots

Every element carries a `slot`. Stage 6 supplies text per slot. A slot with
no copy is drawn as nothing — never as an empty box.

- `photo-strip`: `eyebrow` · `subhead` · `headline` · `offer_big` ·
  `offer_a` · `offer_b` · `cta` · `fineprint`
- `confession`: `opener` · `reason` · `sticker_a` · `sticker_b` · `cta` ·
  `fineprint`
- `full-photo`: `claim` · `kicker` · `offer_sticker`

Furniture — the wordmark, the frame, the warning mark, the sticker shapes —
is fixed by the template. The brief supplies only the words on a sticker,
never its position, colour or angle.

## Adding one

A new template is a design job, done by hand and looked at. Copy the closest
file, change the numbers, render it against a real plate, and keep adjusting
until it is right. Do not generate one from a teardown — that is exactly the
thing this folder exists to stop.

Keep-clear zones matter: `layout.keep_clear` tells plate generation where to
leave the picture empty, and tells the builder where the product goes.
