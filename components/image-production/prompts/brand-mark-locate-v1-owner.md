# The brand mark locate — where the real logo goes

Asked of the vision model after a picture is made, before the real wordmark is
pasted (the owner, 2026-10-14). IMAGE 1 is the original ad the picture was made
from, when there is one; the last image is ours. The model leaves the mark's
place empty (brand-mark-space) but sometimes draws the name anyway, so both are
asked for: a drawn mark is cleared and replaced; an empty place is filled.

Slot: `{brand}` the brand's name.

---

The LAST image is our ad. {brand}'s real logo will be pasted onto it.

Find the ONE place the brand mark belongs:
- if our ad shows {brand} written as a logo, wordmark, sign-off or brand stamp
  (not inside a sentence of copy), that is the place — box the drawn mark;
- otherwise, if the first image (the original ad) shows its own brand's logo or
  sign-off, box the empty matching place in our ad, at the size that logo has there;
- otherwise there is no place: answer null.

Answer in JSON only:
{"box_2d": [ymin, xmin, ymax, xmax] in 0–1000 of OUR ad's height and width, or null,
 "drawn": true if our ad has the name drawn there, false if the place is empty,
 "why": one short line}

The box hugs the mark's letters (or the empty place's size) tightly — a logo
line, not the whole card.
