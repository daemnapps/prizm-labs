# Black Friday statics lineup

Page: https://claude.ai/artifact/EujpTm942StAgH6pNtSvzv

Offer ads show the product and the offer only, with no people or scenes. Natives come from organic videos we already hold, with a caption on top. Two trial briefs have run. 26 are in the editor's queue: 14 FLEX and 12 body scrub. FLEX 08 and 15 were already sent to Meta on 3 Nov, so they are out of the hand-off. The 12 Brand B face scrub ads were dropped by the owner on 6 Nov and are out of the editor's queue.

## What's left before the editor

All 26 are done. the editor and the email lead cannot see them until the pages are shared.

### Calls

| Call | Facts | Pick |
|---|---|---|
| Share the pages | Hand-off to the editor, launch plan to the email lead | Share both |
| Dates on the ads | None of the 40 ads or their variations show a date or end time, so they can run past the sale. FLEX 13's "This deal can't go overtime" is the only line that hints at an end | Leave it; set the end date on the offer pages only |
| Ad start | Creative ready next week, offer opens Nov 25 | Load paused until Nov 25 |
| Who presses Approve | Approval page lists the email lead; the standing rule keeps Meta with the owner | the owner |
| Viewer check | Did not finish on 30 briefs; it only flags | Skip it |

### Words to read

- FLEX 02, base "Real Black Friday shit": "put me on", "It's real", "i believe this", "just plain rocks", "wanted to try".
- Body 01, base "64yo Black Friday Routine": "on my list", "sealed the deal", "two orders", "so worth it", "the best fit".

### Small flaws

Face scrub flaws are moot: the face scrub ads were dropped on 6 Nov. Face 06's tube label was already reprinted on 6 Nov (new picture on the board) before the drop.

- FLEX 08: SHOP FLEX needs centring. Already sent to Meta 3 Nov (approved ACTIVE), out of the editor's hand-off; nobody is fixing it. Scene fix is rendered, no print.
- FLEX 11: fixed 6 Nov, FIRST is below the safe line and FLEX is smaller; the text lines are tight.
- FLEX 15: the note touches FLEX. Already sent to Meta 3 Nov (approved ACTIVE), out of the editor's hand-off; nobody is fixing it. The note reads "Clear Your Razor Bumps This Black Friday"; the brief itself flags "Clear Your Razor Bumps" as a results claim. Reported as a fact, not decided.
- Body 05: fixed 6 Nov, the string no longer crosses the flag. New picture `Brand B-batch-bf-body-05-20261106-111927.png`.
- Body 10: the Y in FRIDAY folds over the curl: fixed 6 Nov, BLACK / FRIDAY sits whole on the receipt and the Y is clear. The receipt is now a smaller ribbon than before. New picture `Brand B-batch-bf-body-10-20261106-112510.png`.

### In hand

- Meta ad copy: 5 of 40 drafted, 35 run after the login resets Mon Nov 2. FLEX 03 still names no offer.
- 22 briefs have words printed in the picture. Their folders carry the old instruction; follow the hand-off page until they are corrected.

## Finished pictures

26 of 26 briefs in the editor's queue done, latest versions (face scrub dropped 6 Nov).

- **Brand A FLEX:** 16 done: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16.
- **Brand B face scrub:** dropped by the owner on 6 Nov, out of the queue.
- **Brand B body scrub:** 12 done: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12.

## First pictures only

One first picture per brief, about 100 credits in all. The graphic designer handles every variation. 5 credits spent so far.

Brief 07 is done: FLEX in an open shipping box with two handwritten notes, "Black Friday = FLEX starting at $49" and "Line up. Clean up." Built in 3D, printed, made on the board.

## Right product, right process

The ring, marks and base on briefs 12 and 13 now match the casting sheet, printed through the normal path with nothing pasted on. Brief 06 kept its print and moved up so product and words sit centred. 5 credits.

- Cause: the 3D stand-in for FLEX has a straight stripe and no marks, and the print copied it. One print also used a crop of the sheet.
- Fixes: `picture_sets.py` print words say the 3D product is only a stand-in, and a print cannot be kept unless the whole casting sheet was its reference. Lessons L-89 (blockout placeholder) and L-90 (whole casting sheet).
- Removed: the step that pasted the real photo on top, a side path.
- Open: nothing yet checks the ring and marks automatically.

## Review notes applied

Before and after for briefs 12 and 13. Brief 06 keeps its print.

| | All three | Per brief |
|---|---|---|
| Cached reads | 6.2M | 2.1M |
| Cache writes | 54K | 18K |
| Output | 24K | 8K |
| Steps | 14 | 5 |

Credits: 7.5, three prints.

- **Creativity dials:** they were not reaching the picture. Briefs asked for absurdity 2 to 3, humor 2 and world-building up to 4; the fixed print prompts and sets skipped them. Sets now read the concept and dials from the brand step.
- **FLEX shape:** sets shoot it flat and straight-on, turned only in its own plane, and refuse any other view unless asked. Briefs 12 and 13 look flat by eye; the measured check was not run on them.
- **Concept:** 12 is a coach's draft desk; 13 is a miniature arena.
- **Confetti:** set in 3D to stay out of the words area.
- **Brief 06:** the new print made FLEX thicker and failed the shape check, so the first print stays, with no extra creative yet.
- **Holidays:** new picture briefs now read the same dated moments list as email, nearest first; the order's moment still wins. Lesson L-88 (dated moments).
- **Prompt change, stage 3 v15, word for word:**
  - New: What is on the calendar (the dated moments for this brand and avatar, nearest first, from the marketing calendar): {moments}
  - Changed: crossed with the moment the order names (its season or holiday) or, when the order names none, the nearest fitting moment on the calendar above. A moment past its end date is never used.
  - Changed: **THE MOMENT:** the season or holiday from the order or the calendar, and its palette (three or four colours with hexes).
- Lessons L-85 (flat view), L-86 (concept in the set) and L-87 (clear words band) are in `components/model-inputs/lessons.json` as drafts.

## Type and FLEX shape test

Same three briefs. Designed type won; the product edit lost.

| | All three | Per brief |
|---|---|---|
| Cached reads | 8.4M | 2.8M |
| Cache writes | 66K | 22K |
| Output | 37K | 12K |
| Steps | 23 | 8 |

Credits: 8.25, all on the rejected edit.

- **Words in the print: keep.** Sticky notes and ribbon spelled every word right on the first print.
- **Designed layouts: keep.** `big-offer` and `headline-badge` run in the board's type step through `design_type.py`, set per set in `set.json`. Words auto-fit inside the safe zone, clear of the product.
- **Second pass on FLEX: rejected on all three.** The brushes moved, Brief 06 got ghost edges, and output was half the size. Plain prints stay.
- **Shape check: built, run by hand.** `shape_check.py` measures the print against the true outline. Briefs 06 and 13 pass; Brief 12 has 2 of 3 brushes over the limit.
- **Did not work:** the font files in the store theme folder are corrupted, so layouts read the licensed files from the company drive.
- **Open:** a confetti speck sits inside OVERTIME on Brief 13.

## Reusable 3D sets test

Three FLEX first pictures (briefs 12, 06, 13) from reusable sets, against Brief 07. Quality held and all words are spelled right.

| | Per picture | Sets, one time | Brief 07 |
|---|---|---|---|
| Cached reads | 2.9M | 3.6M | 14M |
| Cache writes | 41K | 145K | |
| Output | 12K | 31K | |
| Steps | 13 | 23 | 57 |

- Three prints cost 7.5 credits.
- With the build shared, each picture cost 4.1M cached reads, 29% of Brief 07.
- The biggest waste was the board's word placement: two of three needed positions set by hand.
- The print held every set's camera, positions and sizes.
- The product kept its shape and buttons but was not exact: small drift in the pad, and one measured FLEX about 4% wider.
- Laying the real product back in looked stuck on, so the plain prints stayed.
- Sets: `components/image-production/flex_sets_blender.py` and `scene_templates.py`; records in `runs/image-production/Brand A/sets/` (bf-notes, bf-ground, bf-float).

## Estimate

Balance: 5,488 credits. 40 ads. FLEX 16: 4 native, 12 product-focused. Face and body scrub 12 each: 4 native, 8 product-focused. Male-coded swipes for FLEX, female-coded for Brand B, no text-heavy ads.

| Option | Pictures | Credits | Left for video |
|---|---|---|---|
| All 40, with variations | 180 | 450 | 5,038 |
| All 40, one picture each | 40 | 100 | 5,388 |

- About 9.2M Claude tokens and 2 hours with six running at once, up to the first picture. Measured on two trial briefs.
- Variation writing and the final brief run after a first picture is approved. Not measured.

## Open

- The 4 FLEX natives now show the product and carry a caption line, so the offer has a place to go. Not yet run through the chain.
- Old white boxes are built as the current black and gold box.

## What sold, last 30 days (sales through 29 October)

| Ad | Sales | Per sale | Spent |
|---|---|---|---|
| Brand A still: warehouse of razors, FLEX in hand | 9 | $36 | $327 |
| Brand A video: bump check | 11 | $23 | $257 |
| Brand B video: body scrub | 52 | $52 | $2,717 |
| Brand B video: Grandma | 18 | $64 | $1,154 |

## Offers

- Brand A: FLEX starting at $49, 90-day money-back guarantee.
- Brand B: Buy 2, get 1 free, starting at $19 a tube, free pouch, free shipping. Body scrub or face scrub is still to be picked.

## Brief list

| Brief | Look | Type | Offer | Swipe |
|---|---|---|---|---|
| BF-FLEX-01 | native | Our UGC | FLEX starting at $49 | IG_story_artiemaxwelltara_2024-12-03.heic |
| BF-FLEX-02 | native | Our UGC | FLEX starting at $49 | IG_story_richestmanofbaltimore_2025-01-23.jpg |
| BF-FLEX-03 | native | Our UGC | FLEX starting at $49 | IG_reel_iamroyaljones_2024-07-31.mp4 |
| BF-FLEX-04 | native | Our UGC | FLEX starting at $49 | IG_reel_adixovic_2025-04-24.mp4 |
| BF-FLEX-05 | product | Design promo | FLEX starting at $49 | marsmen 163750816 |
| BF-FLEX-06 | product | Design promo | FLEX starting at $49 | Brand D 158222713 |
| BF-FLEX-07 | product | Design promo | FLEX starting at $49 | sprtn 161068514 |
| BF-FLEX-08 | product | Design promo | FLEX starting at $49 | sprtn 164846105 |
| BF-FLEX-09 | product | Design promo | FLEX starting at $49 | marsmen 151889609 |
| BF-FLEX-10 | product | Design promo | FLEX starting at $49 | sprtn 171111848 |
| BF-FLEX-11 | product | Design promo | FLEX starting at $49 | Brand D 111942099 |
| BF-FLEX-12 | product | Design promo | FLEX starting at $49 | Brand D 158666839 |
| BF-FLEX-13 | product | Design promo | FLEX starting at $49 | marsmen 110461560 |
| BF-FLEX-14 | product | Design promo | FLEX starting at $49 | sprtn 168904029 |
| BF-FLEX-15 | product | Design promo | FLEX starting at $49 | Brand D 141236531 |
| BF-FLEX-16 | product | Design promo | FLEX starting at $49 | Brand D 157004515 |
| BF-FACE-01 | native | Organic native | Buy 2, get 1 free | https://www.tiktok.com/@skincare.enthusia0/video/7604544198888475925 |
| BF-FACE-02 | native | Organic native | Buy 2, get 1 free | tiktok 7675732008068205842 |
| BF-FACE-03 | native | Organic native | Buy 2, get 1 free | https://www.tiktok.com/@grandma_droniak/video/7697352586357165343 |
| BF-FACE-04 | native | Organic native | Buy 2, get 1 free | https://www.tiktok.com/@sidandlisten/video/7663189584481635615 |
| BF-FACE-05 | product | Design promo | Buy 2, get 1 free | Brand C 157282404 |
| BF-FACE-06 | product | Design promo | Buy 2, get 1 free | Brand C 157373230 |
| BF-FACE-07 | product | Design promo | Buy 2, get 1 free | froya 59476313 |
| BF-FACE-08 | product | Design promo | Buy 2, get 1 free | Brand C 151624241 |
| BF-FACE-09 | product | Design promo | Buy 2, get 1 free | Brand C 157282375 |
| BF-FACE-10 | product | Design promo | Buy 2, get 1 free | Brand C 157277690 |
| BF-FACE-11 | product | Design promo | Buy 2, get 1 free | Brand C 169832698 |
| BF-FACE-12 | product | Design promo | Buy 2, get 1 free | Brand C 171338266 |
| BF-BODY-01 | native | Organic native | Buy 2, get 1 free, starting at $19 a tube | https://www.tiktok.com/@korea_grandma/video/7677233047170796831 |
| BF-BODY-02 | native | Organic native | Buy 2, get 1 free, starting at $19 a tube | https://www.tiktok.com/@all.things.amari/video/7676695246922665246 |
| BF-BODY-03 | native | Organic native | Buy 2, get 1 free, starting at $19 a tube | https://www.tiktok.com/@lala_dela/video/7649133087821008159 |
| BF-BODY-04 | native | Organic native | Buy 2, get 1 free, starting at $19 a tube | https://www.tiktok.com/@hannah.grabau/video/7612331471197572383 |
| BF-BODY-05 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | froya 156472305 |
| BF-BODY-06 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | froya 156637346 |
| BF-BODY-07 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | Brand C 156983211 |
| BF-BODY-08 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | Brand C 157368643 |
| BF-BODY-09 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | froya 157764378 |
| BF-BODY-10 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | froya 156453518 |
| BF-BODY-11 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | froya 157489037 |
| BF-BODY-12 | product | Design promo | Buy 2, get 1 free, starting at $19 a tube | Brand C 157283159 |
