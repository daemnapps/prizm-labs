# The input standard — one skeleton for every picture prompt

RULE STD-1 (inputs): every picture prompt has the same labelled sections in the same order; a section with nothing in it
is left out. Rendered by `image_production/plain.py` `prompt()`. Shape follows OpenAI's guidance (label each input by number
and role; scene, subject, details, constraints; preserve the product exactly; say what not to change).

```
INPUTS
IMAGE 1 is the reference. Make ours from it: the same layout, look, light, photo style and text style and
placement, changed only as THE PICTURE says.                                  (only when there is a reference)
IMAGE 3 is the real {PRODUCT}: the FRONT view. IMAGE 4 ...: the THREE-QUARTER view. IMAGE 5 ...: the BACK view.

THE PICTURE
{what the caller asks for: scene, subject, details, the exact words, any real pieces with their roles}

WHAT STAYS · THE FEELING · THE DIALS · TECHNIQUES            (the brief's own lines, each only when filled)
{any other filled variable of the sheet: a section named after itself}

THE PRODUCT                                                                  (only when a product is in frame)
The product images are photographs of the real {PRODUCT}, each marked with the side it shows. Preserve its
geometry, colour and label legibility exactly, whichever side faces the camera; do not restyle it, relabel it or
invent any side that is not shown.
{the kit's own lines} The real {PRODUCT} is {h} cm tall and {w} cm wide: draw it at that true size ...

THE PEOPLE
Every person is a LOOKALIKE of the person in that same spot in IMAGE 1: ...   (with a reference)
Every person is a realistic made-up person, never anyone from a reference picture. ...   (without)

THE FRAME
This picture is 9:16, vertical, made at that size from the start. Its centre 4:5 (full width, from 15% to 85% of
the height) is the SAFE ZONE: every face, hand, product, headline, word and badge sits inside it, clear of its
edges. The top 15% and the bottom 15% are bleed: more of the same scene, nothing that must be seen. The scene
continues naturally to the top and bottom edge; never a band, never empty space.

RULES
Apart from what THE PICTURE changes, do not change anything else in IMAGE 1.  (only with a reference)
No writing in the picture except the exact words THE PICTURE gives.
```

RULE STD-2 (output frame): every photo and video asset (not email) is generated at 9:16
(1152x2048) with the safe zone in the prompt; nothing is made at 4:5 and painted out. The judge measures the zone
(`judge.SAFE_ZONE`). An EDIT of an existing picture still keeps its own frame and is finished the old way.

Reference order: the swipe or plate first, real pieces next, the product's three views, then cast.
Callers (`tools/pictures.py`, `tools/slides.py`, the scene stills) fill THE PICTURE; they do not write the
other sections. `make.py` and the engine now make 9:16 natively too; only `gpt_drafts.py` (the oldest draft path) is not on this standard yet.

**The recipe (2026-10-26).** Every picture can carry its variable sheet: `plain.make(..., recipe={variable: value | {"na": reason}})`
and the engine's request field `recipe`. A blank variable, or a not-applicable without a reason, is refused by name before any
door (`recipe.py` `gate`; the validator is components/model-inputs' `validate_recipe` when it exists, the blank rule until
then). Filled variables each get their own labelled section; not-applicable ones are left out of the prompt and kept in
`<picture>.recipe.json` beside the picture, which also holds the request and the prompt so a later run can replay it.
`people_lines` and `rules_lines` add lines to THE PEOPLE and RULES. `models.json` `gate.recipe_required` (off today) makes a call
with no recipe refused as well, once every caller supplies one.

## HISTORY

- 2026-10-26, the owner: "we need to simply standardize our input prompts ... so we can really test image production at scale."
- 2026-10-26, the owner: made 9:16 from the start with the safe zone assumed; 4:5 then painted out "comes out like shit and inconsistent".
