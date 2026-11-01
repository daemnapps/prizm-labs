# The product locate — where the product goes, and how big it is there

Asked of the vision model about a scene that was made WITHOUT the product
(the product-space rule kept its spot clear), before the product is rendered
from its 3D model and placed. the owner's ruling behind it, 2026-10-14: the
product's size comes from its REAL size against a reference in the scene —
the first proof's shelf, scaled off a guessed sticky-note size, came out too
big.

The model is asked to NAME a reference object of known real size near the
spot and to box it; the code divides the box by the stated size to get pixels
per centimetre. A model is poor at guessing a scale outright and good at
boxing a thing it can name, so it is asked only for the second.

Slots: `{what}` the product in plain words, `{size}` its real size,
`{count}` how many units go in, `{where}` where the direction said it goes.

---

This picture was made with an empty spot where {count} of {what} ({size}) will be
placed later, resting on a surface. {where}

Answer in JSON only:

{
 "kind": "photo" or "graphic" — a real-looking scene with depth, or a flat
   graphic / interface / poster with no real surface,
 "spots": [ one per unit, {count} in all: {"box_2d": [ymin, xmin, ymax, xmax]} —
   the empty area where that unit should stand, its BOTTOM edge on the surface
   line where the unit touches down; numbers 0–1000 of the picture's height
   and width ],
 "reference": {
   "name": a common object in the picture, at about the same distance from the
     camera as the spot, whose real size is standard and well known (a power
     outlet cover plate, a standard sticky note, a sink tap, a toothbrush, a
     cabinet hinge, a dinner plate, a soap pump bottle) — never the spot itself,
     and never a thing whose size you would have to guess,
   "box_2d": [ymin, xmin, ymax, xmax] of that object, 0–1000,
   "measure": "height" or "width" — which side of the box the size below is,
   "real_cm": its real size along that side, in centimetres
 }
}

For a "graphic" there is no real surface and no reference: give "reference": null
and box the panel or area the product should fill.
