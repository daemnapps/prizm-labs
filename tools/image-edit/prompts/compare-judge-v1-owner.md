# compare judge — v1 — 2026-09-22

Two pictures are attached. IMAGE 1 is the REFERENCE. IMAGE 2 is the RESULT of
an edit that was asked to change exactly one thing.

The change that was asked for:

> {change}

Answer every test below by looking at both pictures. A test PASSES only if you
can see it is true; if you are not sure, it FAILS. Judge the way a viewer
scrolling past would — a partly hidden hand or a one-pixel shift is not a
change; a different face, a moved element, a re-lettered word or a new colour is.

**Two corrections, both from real verdicts that came out backwards
(2026-09-25).**

**Micro-print on a product label is not a change worth failing.** The tiny
ingredient and weight lines on packaging are unreadable at feed size and are
usually garbled to begin with; a picture was thrown out for
correcting one misspelled ingredient word. Judge the product by its SHAPE, COLOUR, EMBLEM and
BRAND NAME. Ignore the small print unless the whole label has become a
different label.

**A doubled element or a seam is a FAIL, whatever else is true.** A picture
was recorded as passing while its headline was printed twice across a mask
boundary, because nothing outside the edited box had moved. Before any other
test: look for an element that appears twice, a hard horizontal or vertical
line where the picture changes character, or type overlapping type. Any of
those fails every test at once — say so plainly.

{tests}

Reply with JSON only, in this shape:

{"results": [{"test": 1, "verdict": "PASS", "evidence": "one line"}, ...]}
