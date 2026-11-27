# The swaps record (26 Oct 2026)

One file per run, `out/swaps.json`, says what the picture swaps and what goes into it. Every picture maker reads it and
nothing else. Built by `tools/swaps.py`; stage 3 (v6) writes it, stage 6 (v10) carries it, and every older run is backfilled.

```json
{"product_in_frame": true|false, "product_where": "<where it sits>"|null,
 "product_sides": ["front"|"three-quarter"|"back"],
 "stays": ["..."],
 "swaps": [{"from": "<in the swipe>", "to": "<what it becomes>", "kind": "cast"|"product"|"library"|"drawn"|"words", "ref": "<cast id | product kit | library path>"|null}],
 "words": "set_on_top"|"drawn",
 "source": "stage3"|"backfill"}
```

Optional: `evidence` (why each call was made) and `unclear` (a backfill the text did not settle; `product_in_frame` is then null).

## The rules

- swaps rule 1 Every swap is its own entry with a kind (cast: a banked character's photo; product: the product's real pictures; library: a banked prop or set; drawn: made from words; words: the caption).
- swaps rule 2 `product_in_frame` is yes or no; yes carries where it sits and which sides show.
- swaps rule 3 The pictures sent are the swipe, one photo per cast swap, one per library swap, and the product's pictures only on yes.
- swaps rule 4 `words: set_on_top`: the picture is made with no caption, headline or overlay text; the brief's own type layer is set over it afterwards and the plate is kept.
- swaps rule 5 What the text does not settle is `unclear` and listed, never guessed.

## One prompt, before and after: "Grandma Yai, three spots" (Brand B-batch-grandma-dark-spots-not-growing-old)

The brief says: no product in frame, the woman is Grandma Yai (cast photo exists), the words are set on top. Nothing was sent.
This is the prompt each way, built without any picture call.

```
BEFORE: 4 pictures in
  IMAGE 1: source.jpg — the reference
  IMAGE 2: reference-front.png — the real BRILLIANCE-FACE-SCRUB: the FRONT view
  IMAGE 3: reference-34.png — the real BRILLIANCE-FACE-SCRUB: the THREE-QUARTER view
  IMAGE 4: reference-back.png — the real BRILLIANCE-FACE-SCRUB: the BACK view

INPUTS
IMAGE 1 is the reference. Make ours from it: the same layout, look, light, photo style and text style and placement, changed only as THE PICTURE says.
IMAGE 2 is the real BRILLIANCE-FACE-SCRUB: the FRONT view. IMAGE 3 is the real BRILLIANCE-FACE-SCRUB: the THREE-QUARTER view. IMAGE 4 is the real BRILLIANCE-FACE-SCRUB: the BACK view.

THE PICTURE
THE SWAPS: the woman in IMAGE 1 becomes Grandma Yai. A Thai grandmother, 72, Isaan-born: a small, round-shouldered woman with a broad flat-bridged nose, high wide cheekbones, deep smile lines bracketing the mouth, a soft full jaw and a slight double chin. Warm olive-tan skin, weathered, with real pores, a scatter of sun freckles across the cheekbone and three distinct dark spots on the cheek she is turning to camera. Steel-grey hair, thick and coarse, pulled straight back into a low flat knot with stray wire-grey hairs catching the top-left light. Heavy-lidded dark brown eyes, no eyeliner. She is in IMAGE 1's exact pose, crop and silhouette: head tilted back and away, only the right cheek, one eye, nose and lip in profile, gaze down and off to the right, mouth slightly open.
The overfilled lips and distended cheek become the dark spots, blown monumental. Yai's cheek carries IMAGE 1's exact swollen silhouette, but what is pushing out past the profile line is not filler: it is three dark spots raised to the size of coins, dome-shaped, brown-black, sitting proud of the skin and casting their own little shadows in the top-left light, with the skin around them stretched taut and faintly ruddy. The profile bulge sits exactly where IMAGE 1's filled lip and cheek sat.
The round silver pendant becomes a parody-brand sheet-mask foil pouch pendant. Same size, same round-into-rectangle silver glint at the left edge, same chain. The foil is printed "K-GLOW · 12 STEP" in tiny Korean-pastiche lettering, hanging off the ball chain like a medallion.
The stray hairs and the fur edge pick up a faint turmeric-yellow dusting at the jawline. A scatter of fine golden-ochre powder on the skin at the jaw and caught in the black fur, as if she has just been working with it.
The caption words swap. Same two lines, same length, same case, same band.

THE WORDS ON THE PICTURE (exactly these words, in IMAGE 1's own type style and places; nothing else written; no long dashes):
Caption text: write exactly "DARK SPOTS? YOU AND ME" then, on the next line, "ARE NOT A PACKAGE DEAL". It sits 74% to 84% from top, 9% to 91% width. Center-aligned. White #FFFFFF, bold uppercase humanist sans, hard black stroke.
Nothing else is written anywhere in the picture.

THE PRODUCT
The product images are photographs of the real BRILLIANCE-FACE-SCRUB, each marked with the side it shows. Preserve its geometry, colour and label legibility exactly, whichever side faces the camera; do not restyle it, relabel it or invent any side that is not shown.
The real BRILLIANCE-FACE-SCRUB is 10.5 cm tall and 6.3 cm wide: draw it at that true size against hands and faces, never smaller.

THE PEOPLE
Every person is a LOOKALIKE of the person in that same spot in IMAGE 1: the same look, age, build, hair, style and energy. A celebrity or known influencer stays recognisable as a nod, with a slightly different face, never the real person. No other brand names or logos.

THE FRAME
This picture is 9:16, vertical, made at that size from the start. Its centre 4:5 (full width, from 15% to 85% of the height) is the SAFE ZONE: every face, hand, product, headline, word and badge sits inside it, clear of its edges. The top 15% and the bottom 15% are bleed: more of the same scene (wall, floor, ceiling, sky, counter), nothing that must be seen. The scene continues naturally to the top and bottom edge; never a band, never empty space.

RULES
Apart from what THE PICTURE changes, do not change anything else in IMAGE 1. No writing in the picture except the exact words THE PICTURE gives.
```

```
AFTER: 3 pictures in
  IMAGE 1: source.jpg — the reference
  IMAGE 2: master.jpg — Grandma Yai, our cast member
  IMAGE 3: master-sheet.webp — Grandma Yai's reference sheet

INPUTS
IMAGE 1 is the reference. Make ours from it: the same layout, look, light, photo style and text style and placement, changed only as THE PICTURE says.
IMAGE 2 is Grandma Yai, our cast member: use this face exactly, in the pose, place and light IMAGE 1 shows. IMAGE 3 is Grandma Yai's reference sheet: the same person from other angles, only to keep the face right. Do not copy its layout.

THE PICTURE
THE SWAPS: the woman in IMAGE 1 becomes Grandma Yai. A Thai grandmother, 72, Isaan-born: a small, round-shouldered woman with a broad flat-bridged nose, high wide cheekbones, deep smile lines bracketing the mouth, a soft full jaw and a slight double chin. Warm olive-tan skin, weathered, with real pores, a scatter of sun freckles across the cheekbone and three distinct dark spots on the cheek she is turning to camera. Steel-grey hair, thick and coarse, pulled straight back into a low flat knot with stray wire-grey hairs catching the top-left light. Heavy-lidded dark brown eyes, no eyeliner. She is in IMAGE 1's exact pose, crop and silhouette: head tilted back and away, only the right cheek, one eye, nose and lip in profile, gaze down and off to the right, mouth slightly open.
The overfilled lips and distended cheek become the dark spots, blown monumental. Yai's cheek carries IMAGE 1's exact swollen silhouette, but what is pushing out past the profile line is not filler: it is three dark spots raised to the size of coins, dome-shaped, brown-black, sitting proud of the skin and casting their own little shadows in the top-left light, with the skin around them stretched taut and faintly ruddy. The profile bulge sits exactly where IMAGE 1's filled lip and cheek sat.
The round silver pendant becomes a parody-brand sheet-mask foil pouch pendant. Same size, same round-into-rectangle silver glint at the left edge, same chain. The foil is printed "K-GLOW · 12 STEP" in tiny Korean-pastiche lettering, hanging off the ball chain like a medallion.
The stray hairs and the fur edge pick up a faint turmeric-yellow dusting at the jawline. A scatter of fine golden-ochre powder on the skin at the jaw and caught in the black fur, as if she has just been working with it.

NO WORDS IN THE PICTURE: no caption, headline, overlay text or lettering of any kind anywhere in it (the words are set on afterwards). Take the caption out of IMAGE 1 and paint what is behind it, so the band where it sat is plain picture. Lettering that belongs to an object named in THE SWAPS stays on that object.

THE PEOPLE
The person in IMAGE 2 is Grandma Yai, a Thai grandmother, 72, Isaan-born, in the exact same pose and crop. Keep Grandma Yai's face exactly: the same features, skin, age and hair, in the place of a woman in IMAGE 1. No other brand names or logos.

THE FRAME
This picture is 9:16, vertical, made at that size from the start. Its centre 4:5 (full width, from 15% to 85% of the height) is the SAFE ZONE: every face, hand, product, headline, word and badge sits inside it, clear of its edges. The top 15% and the bottom 15% are bleed: more of the same scene (wall, floor, ceiling, sky, counter), nothing that must be seen. The scene continues naturally to the top and bottom edge; never a band, never empty space.

RULES
Apart from what THE PICTURE changes, do not change anything else in IMAGE 1. No writing in the picture except the exact words THE PICTURE gives.
```

## Backfill result (234 runs, all valid)

- Product in frame: 80 yes · 151 no · 3 unclear (Brand A-batch-bottom-hims-172522392, Brand A-batch-glowup-habits-8k, Brand A-batch-glowup-one-tip-5k).
- Yes but the text names no kit, listed unclear: Brand A-batch-bottom-marsmen-122199960, Brand A-batch-bottom-marsmen-122685894, Brand A-batch-pick-tt-7683548232378567950.
- Cast swaps with a real cast id: 31 (none without one). About 50 runs swap in a made-up person (kind drawn).
- 131 runs have a teardown too old or incomplete to make (no SWAPS section, no dials, or no brief): the list is in the shared notes as swaps-runs-too-old-or-incomplete.txt.
