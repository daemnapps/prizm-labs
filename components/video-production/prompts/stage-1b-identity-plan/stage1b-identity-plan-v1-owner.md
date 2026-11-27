Work out which identities this piece needs trained before generation can
start, which already exist, and how each missing one gets built.

**Every example in this prompt is illustrative only.** Take everything
from the material below.

An identity is a face or an object learned once into a trained model, so
any later generation returns the same person or the same packaging with no
reference photo attached. This stage decides what has to be trained; the
training itself is a separate machine.

---

THE PRODUCTION DOCUMENT

{production_document}

IDENTITIES THIS BRAND ALREADY HAS

{existing_identities}

THE BRAND'S CAST AND PRODUCTS

{brand_assets}

---

Return exactly these sections.

## THE ROSTER

A table, one row per subject that appears on camera — every role in the
cast, the product, and any object or body part the piece depends on
(hands, a forearm, a signature texture).

| Subject | Kind | Status | Source for training |
|---|---|---|---|

**Kind** is `character`, `creator`, `product` or `object`.

**Status** is one of:
- `TRAINED` — an identity already exists; name it and stop there.
- `TRAINABLE` — the source images exist; name exactly which ones.
- `BLOCKED` — no usable source. Say what is missing and who has to
  produce it. This is a person's job, not a machine's.

**Source for training** names the actual images. For a character, their
certified board set. For a contracted creator, her own published footage —
never a stand-in, never a lookalike. For a product, its clean packshots
plus close crops of the label bands.

## WHAT TO TRAIN, IN ORDER

A numbered list of the `TRAINABLE` rows, in the order they should be
trained, with the reason for the order. Faces that carry the piece come
first; a background object that appears once comes last, or is dropped in
favour of a reference photo.

For each, state the training set in one line: how many images, from where,
and any image that must be excluded and why — a shot containing two
products teaches both, a photograph with no clear face fails outright.

## WHAT MUST NOT BE TRAINED

Name anything in the piece that should stay a plain reference photograph
rather than an identity, and why. Small text is the usual case: a product's
label survives better composited from the real packshot than generated
from a trained model, at any size where the words are readable.

## BLOCKED — WHO HAS TO DO WHAT

If any row is `BLOCKED`, list what a person must supply, in one line each,
plainly. If nothing is blocked, write `NOTHING BLOCKED — training can
start.`

---

Write the plan and nothing else: no preamble, no summary, no offer to
continue.
