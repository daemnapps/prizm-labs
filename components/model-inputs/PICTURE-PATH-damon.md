# The Picture Path

Mirror of the artifact (private page) (27 Oct 2026).

This page traces every station the grandma picture went through, where each station lives, and what it did. The same path is the one the owner and Amit will run by hand, one picture at a time.

The picture: `runs/image-production/<brand>/prompt-bench/<brand>-batch-grandma-dark-spots-not-growing-old-20261027-001821.png`. It was made with GPT Image 2.5 on the first try, for 2.75 credits.

## What went in

- **IMAGE 1, the swipe:** @witchy.lashes, 3.46M views. It sets the pose, the light and the look.
- **IMAGE 2, the cast photo:** Two More Years Mama. It sets the face.

## The path

| # | Station | Where it lives | This picture |
|---|---|---|---|
| 1 | The swipe is broken down | image teardown chain: `tools/image-teardown/runs/<swipe>/out/` `swaps.json`, `controls-swipe.json`, `elements.json`, `06-brief.md` | 4 swaps: the woman becomes our grandma, the lips become 3 dark spots, the pendant becomes a K-GLOW parody pouch, and the caption becomes our words. 12 things stay. |
| 2 | You make the choices (by hand for now) | the board, `components/creative-controls/controls.json`, `components/model-inputs/picture-dials.json` | Cast: Two More Years Mama. Product out. Words set on top. Stray hairs and fur edges kept. Preset: maxed. Feeling: disgust. Dials: intensity 4, absurdity 3, humor 3, dramatisation 3, realism 3, stopping power 4, parody marks 3, valence 1. |
| 3 | The builder writes the prompt | `components/model-inputs/preview.py` `build_picture` | A 30-line prompt and 2 pictures. |
| 4 | The check, before any spend | `picture-sheet.json`, `inputs/gpt-image-2.5.json`, `input_rules.py` | 76 of 76 inputs settled: 59 filled, 17 not needed. |
| 5 | The Model House makes it | `components/models/models.json`, image-production `plain.make`, Higgsfield | GPT Image 2.5 on the first try. Backups not needed. Words set on top afterwards. |
| 6 | Saved with its recipe | `runs/image-production/<brand>/prompt-bench/` `.png`, `.recipe.json`, `generated/….prompt.txt` | Picture saved with its recipe and its prompt. |

## The line to tighten

The prompt carries "Warm light, an easy, relieved face." That line comes from the valence dial at level 1 (`picture-dials.json`). It contradicts "the strongest reaction", "hard, direct light" and the feeling "disgust".

## The line, start to finish (27 Oct 2026)

1. **image teardown — the records.** What's in the swipe, its format with the brand stripped, its labels, its level on every dial. It writes nothing of ours.
2. **image writing — our version.** The swaps, the words, the brief, and the 5 variations as data (`out/variations.json`), one change each. It became its own component on 27 Oct (`tools/image-writing`).
3. **image-production — the first picture.** The concept picture, made from the brief with the words set on top. the owner approves it.
4. **image-edit — the 5 variations.** Each is the approved picture plus one change, made as an EDIT (the approved picture is IMAGE 1, and the prompt carries only the change). Each is checked against the approved picture, with up to 2 tries and the best kept (`vary.py --from-brief`).
5. **Meta card — approval.** All 6 go on one card in `meta/<brand>/1-check/image/`. Nothing goes live until the owner presses Approve.

Under steps 3 and 4 is one engine: **model-inputs** (the prompt and the 76-input check), then **Model House** (GPT Image 2.5, then the backups), then **Higgsfield**. The board is a window onto model-inputs, not a step.

**The grandma batch (brief 0324):** the approved picture plus h1 (spots grouped tight), h2 (the phone's reflection in a spot), h3 (spots staged by age), h4 (fur pulled up to the cheek) and h5 (the pouch fully in shot). All 6 passed the check against the approved picture.

**Fixed on the way:**
- The pouch was deleted by "no lettering of any kind". Edits now keep any object that already carries lettering (`EDIT_NO_WORDS`).
- Words went missing when the words file moved mid-run. That now stops the run (`type_layer` raises), so a wordless picture can't ship.

## A round, in order (27 Oct 2026)

One brief at a time, all of it on the Make a Picture Ad board (the owner, 2026-10-27: "we're gonna run batches of ads through this tool right here"). After the approved picture, the board writes the 5 (image-writing stage 5), shows all 6 headlines to edit, makes the 5 on Approve (copy sign-off, then image-edit), and sends the 6 to the Meta approval page:

1. **Records:** image teardown, steps 1, 2 and 2b (already done for every swipe on file).
2. **Writing:** image-writing steps 3 and 4: our swaps and words, and the headline set. Language is the run's avatar at the swipe's awareness level, with spice.
3. **Pick the elements:** on the board ("Make a Picture Ad", step 2, "Pick the elements"). Every element of the swipe sits in one group: the person, the problem on screen, props and wardrobe, the set and the light, the camera and the frame, the words. Then the product, who is in it, and the dials. Every button carries a note on what it does.
4. **Copy sign-off:** the owner reads the first picture's words (`image-writing/tools/copy_ok.py show <run>`) and approves or changes them.
5. **First picture:** image-production through model-inputs (the board's Make, or the teardown's `tools/pictures.py`). the owner approves the picture (`.liked.json`).
6. **Variations:** image-writing steps 5 and 6. Step 5 prints the approved headline as a FORMAT, fills only its blanks from cited lines, and is checked by video's `hook_format`. Step 6 is the brief.
7. **Copy sign-off again:** the 5 variation headlines, approved or changed by the owner.
8. **The 5 pictures:** `image-edit/vary.py <approved.png> --brand <b> --from-brief <run>/out/variations.json`. Each is an edit of the approved picture, judged against it, with up to 2 tries and the best kept.
9. **Meta card:** all 6 go on one card (`meta-upload/to_check.py --lane image`). Nothing goes live until the owner presses Approve.

The grandma batch (brief 0324) ran this way. Headline 4 was changed by the owner to AGE SPOTS before approval.

## How the brief and image-edit work together

The brief decides the variations and image-edit makes them.

**The brief** (image teardown) writes the variations and makes nothing:

- Step 4 writes the headline options (`out/04-headlines.md`).
- Step 5 writes the picture options (`out/05-image-variations.md`).
- Step 6 puts both in the brief: section 6 "Headline options" (5) and section 7 "Picture options" (4), with the order to run them.

**image-edit** makes the pictures. It's called by the brief's variation step, `tools/image-teardown/tools/variations.py`, which does this:

1. Finds the brief's judged draft and uses it as the starting picture.
2. Makes one call per option:
   - A headline option is re-lettered into the picture (`image-edit/vary.py`).
   - A picture option is the one change, sent in words (`image-edit/edit.py`).
3. A two-picture judge checks each result: the change is there and nothing else moved, or the result is held back.
4. Every result is named, listed in `drop.csv` and copied to Drive. On request, it's filed as a Meta approval card in `meta/<brand>/1-check/image/`.

**The hand-off between them** is the brief's number in the brief list (`tools/image-teardown/briefs.json`) plus its judged draft.

**Where it breaks from the picture path:**

- **Can't see it.** The grandma brief has no number in the brief list and no judged draft, so the variation step would skip it.
- **Not the same path.** image-edit never goes through the prompt builder, the 76-input check, the dials or the swap list.
- **Words drawn in.** A headline option is re-lettered into the picture, while the grandma had its words set on top.
- **One kind only.** The step runs the headline options or the picture options, never both (`variations.py` `wanted()`). This brief has both, so its 4 picture options would be dropped.

**Same path, as the owner ruled:** approved recipe + one change from the brief → prompt builder → 76-input check → Model House → words on top → Meta card.

## Where the picture went

Nowhere yet. It is on this Mac only:

- It isn't in the swipe's finals, the queue, Outlier or Drive.
- Pictures are kept out of git on purpose (`.gitignore: runs/**/*.png`).

## What runs through this path today

| Door | Status |
|---|---|
| Pressing Make by hand | Full path. Every station uses the person's choices. |
| Image teardown chain (`tools/image-teardown/tools/pictures.py`) | Same builder (stations 3 to 6), but station 2's choices aren't saved with the swipe, so the chain gets the teardown's defaults only. |
| Video chain | Its own builders: start pictures in `tools/video-production/machine/run_v2.py`, clips in `clips_run.py` and `seedance_prompt.py`. It takes only each model's limits from model-inputs (`clip_limits.py`). This is the next job. |

## The loop (by hand, one picture, no batches)

1. Pick one swipe that's already broken down.
2. Read its swaps and dials.
3. Set ours: keep or swap, cast, dials, words.
4. Read the exact prompt before it sends.
5. Make one picture.
6. Look at it, fix the prompt line that's off, then make again.

## Then video, on the same principles

The six video rules are V48–V53 in `tools/video-production/VIDEO-RULINGS.md`:

- **V48:** scenes, each with one picture and one short prompt that names its references.
- **V49:** one face, headless bodies.
- **V50:** a whole-room set reference.
- **V51:** a motion reference video.
- **V52:** the photo look is a variable set by format and style (grainy iPhone only when they call for it).
- **V53:** references named the same way in every chain.
