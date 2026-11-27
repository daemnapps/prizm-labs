# Static Ad Line — training (Brand A, retraced from the 23 Oct 2026 run)

Markdown mirror of the training page **Static Ad Line Training**:
https://claude.ai/artifact/Cx6FfX6rKh3eRcdEdz56Wy (the pictures live there).
Walkthrough video, narrated in the owner's voice (2 min 41 s):
`runs/image-teardown/Brand A/static-ad-training-1023/static-ad-workflow-training.mp4`
on the owner's machine (video files stay out of git).

How one competitor swipe becomes a finished, approved static. Every picture is
from the real first run made with the creative controls (the owner, 2026-10-23:
"this is what I'm talking about. These statics are brilliant").

- **the editor (graphic design):** pictures and variants, steps 6 and 7. Steps 1 to 5
  tell you what the picture has to do.
- **a creator (video editor):** the same dials, floor and "one idea" run in every
  video (video ruling V33 (controls in every video), `components/video-production/VIDEO-RULINGS.md`).
  Steps 3 to 5 are the thinking you need.

## The line

1. Swipe (Swipe Bank pick)
2. Chain (teardown, dials, swap, words)
3. Pictures (image production + compositor) — the editor
4. Variants (one change each) — the editor
5. Words for Meta + card
6. the owner's OK (nothing goes live before it)

## 01 · Pick a swipe

- The **Brand A Swipe Bank** (https://claude.ai/artifact/Pny1RFec8rvXAkwBarvfvz)
  holds every competitor static not on the board yet: 299 on 23 Oct,
  longest-running first.
- the owner ticks **Make this**. Whatever he ticks gets opened and briefed. No
  confirmation step.
- Statics come from static swipes. Video covers go to the video line.
- The swipe followed here: a meme page's Curry airball on the moon
  (`components/image-teardown/runs/Brand A-batch-pick-tt-7629746340792110357/assets/source.jpg`).

## 02 · Run the image chain

From `components/image-teardown`:

```
python3 tools/pick_run.py --brand Brand A --product flex --avatar fed-up-king \
    --pick tt-7629746340792110357 \
    --ask runs/creative-strategist/Brand A/flex-top-native-quiz/ask.json
```

| Stage | What | Writes |
|---|---|---|
| 1 | teardown | `01-teardown.md` |
| 2 | the format | `02-replication-spec.md` |
| 2b | element labels | `02b-elements.md` |
| 3 | injection: picture swap, dials, our words | `03-injection.md` |
| 4 | headlines | `04-headlines.md` |
| 5 | picture variations | `05-image-variations.md` |
| 6 | the brief | `06-brief.md` |
| → | pictures | `tools/pictures.py` |

- The order file (`--ask`) sets the offer and funnel stage.
- The three prompts that did the work: `stage3-image-injection-v4`,
  `stage4b-image-hook-v3`, `stage6-image-brief-v9` (in `prompts/`, highest
  version number runs).
- Every stage prompt, verbatim: Image Chain Prompts,
  https://claude.ai/artifact/KbYjWui95KSFeCiEx5eqqF

## 03 · Read the swipe's dials, set ours

Stage 3 scores the swipe on every creative dial (0 to 4) first
(`out/controls-swipe.md`), then sets ours at the run's preset. This run:
**native-unaware** (upper funnel, no offer, no call to action). The default
preset is **maxed**. Dials are defined once in
`components/creative-controls/slices/controls.md`.

| Dial | Swipe | Ours |
|---|---|---|
| intensity | 2 | 4 |
| absurdity | 3 | 4 |
| humor | 2 | 3 |
| specificity | 3 | 4 |
| dramatisation | 3 | 3 |
| stopping power | 3 | 4 |
| relevance | 0 | 4 |

From the run's `out/03-injection.md`, THE DIALS.

> **How the owner thinks · never sterile.** "We don't want any sterile ads at all.
> This is Q4 money season." The floor holds under every preset, bottom funnel
> and offers included: intensity 3+, absurdity 3+, humor 2+, dramatisation 3+,
> stopping power 4. Proof goes inside an absurd picture, never a plain product
> shot.

> **How the owner thinks · the bar.** The five first-run ads (step 9) are "the
> bar": the level to reach. Copy the move, never the ad.

## 04 · Swap the picture

Keep the swipe's picture: pose, light, crowd, frame. Swap only the objects
that carry the meaning, for ours of the same shape and role (a visual rhyme).
It reads as the swipe at a glance, as ours a second later. Stage 3 opens with
four labelled lines: THE SWIPE'S PICTURE, STAYS, SWAPS, WHY IT STILL READS.

| | |
|---|---|
| Stays | the shooter's pose, the ball, the light from top right, the horizon line, the four-line caption block |
| Swaps | cratered moon ground → a bumped-up neck; the Earth → one giant razor bump with the hair curled back inside |
| Why it reads | the shooter-on-the-moon meme in one look, then the moon is a neck |

> **How the owner thinks · his own examples.** Curry airball on the moon: keep the
> jump shot and the ball, the moon surface becomes skin with razor bumps, the
> Earth becomes FLEX in the same light. Kyrie with the fans: keep the player and
> the crowd, the basketball becomes FLEX. Examples teach how to think; the chain
> reads each swipe and finds its own swap.

## 05 · Make the words and the picture one idea

| | |
|---|---|
| Theirs | THE STEPHEN CURRY AIRBALL MEME JUST GOT AN UPDATE |
| First try (failed) | ~~THE BRAILLE NECK ROAST AT THE SHOP JUST LEVELED UP~~ |
| Shipped | THAT'S NOT THE EARTH. IT'S ONE RAZOR BUMP WITH A HAIR CURLED BACK INSIDE, RISING OVER MY NECK. |

> **How the owner thinks · one idea.** "The text on that image doesn't make sense,
> but the image is actually great." Tie the picture and the copy together: a
> stranger who reads the line, then looks at the picture, gets why the picture
> is there.

> **How the owner thinks · no word games.** Never fill the swipe's sentence with our
> nouns. Keep the line's job (the news hook, the reveal), say our thing plainly.
> It has to read cold, to a stranger, on one read.

## 06 · Make the pictures, then set the words (the editor)

```
python3 tools/pictures.py <run> --brand Brand A --product flex
python3 components/image-production/static/tools/compose.py \
    --plate plate.png --layer type-layer.json --file 1 --out ad.png
```

- The swipe is the picture reference. When FLEX is in frame it comes from the
  **real product photo**, never a drawn one.
- If the safety filter refuses the swipe (close-up skin), it retries once from
  the written direction alone.
- The ad judge holds a picture whose words and picture are not one idea.
- Words are set by the **compositor** over a clean plate, letter for letter.
  Never ask the model to re-letter.
- Brand colours only (ink, gold, emerald, bone). No long dashes in on-ad words.
  Upper funnel stays native: no quiz, no call to action.

## 07 · Variants: one change each (the editor)

Off the approved picture: "keep image 1 exactly, change only this one thing".
Then the words go back on with the compositor.

- Problem aware (braille neck): no product · one swipe later · every hair
  curling back · along the jaw
  (`runs/image-teardown/Brand A/first-dial-run-1023/problem-aware/variants/v1`–`v4`).
- Most aware (Black Friday warehouse): what he hides his neck with · every
  half-used bump product · his own bathroom (`most-aware/variants/v1`, `v2`, `v4`).
- Unaware (Curry moon): the landscape moves to the Adam's apple
  (`unaware/variants/v3`).

## 08 · Words for Meta, a card, the owner's OK

```
python3 components/copywriter/machine/brief_words.py \
    --brand Brand A --brief <brief> --product flex
python3 components/meta-upload/to_check.py --brand Brand A \
    --lane image --brief <brief> --media ad.png --links <page ids>
```

- The copywriter writes the words Meta shows beside the ad (primary text,
  headlines, descriptions). If a card arrives with none, `to_check` runs it first.
- Each ad becomes a card in `Shared Assets/meta/Brand A/1-check/image/`. Nothing
  here talks to Meta.
- A card that sends only to a quiz gets the product's live offer page beside
  it, automatically.
- the owner approves every card. Only the owner launches, pauses or changes anything in
  Meta.

> **How the owner thinks · quiz and offer.** "Anything that is tested with a quiz
> should also get tested with the offer page too."

## 09 · Same process, every awareness level

All in `runs/image-teardown/Brand A/first-dial-run-1023/`; swipes and written
frames in `components/image-teardown/runs/<run>/assets/source.jpg` and
`out/03-injection.md`.

| Level | Ad | File | Swipe run |
|---|---|---|---|
| Unaware | the moon is a neck | `unaware/first-dial-unaware-01-v3a.png`, `-v3b.png` | Brand A-batch-pick-tt-7629746340792110357 |
| Problem aware | "Ur neck like braille bro" | `problem-aware/first-dial-problem-aware-01.png` | Brand A-batch-pick-tt-7680608523276832014 |
| Solution aware | tier list, the winner wasn't a razor | `solution-aware/first-dial-solution-aware-01.png` | Brand A-batch-pick-penrose-160559510 |
| Product aware | whiteboard, the hair comes off the board | `product-aware/first-dial-product-aware-02.png` | Brand A-batch-pick-marsmen-122200990 |
| Most aware | Black Friday, a warehouse of blamed razors | `most-aware/first-dial-most-aware-01.png` | Brand A-batch-pick-marsmen-122203312 |

## Where things are

- Swipe Bank: https://claude.ai/artifact/Pny1RFec8rvXAkwBarvfvz
- Image Chain Prompts: https://claude.ai/artifact/KbYjWui95KSFeCiEx5eqqF
- Creative Controls: https://claude.ai/artifact/XRDxT6HRWkPi6HbQTzYcHi
- Brand A Finished Statics: https://claude.ai/artifact/BTT3UH3NyjDFukR2wGkgmv
- The chain: `components/image-teardown` (rules: CLAUDE.md)
- The dials: `components/creative-controls/slices/controls.md`
- Pictures: `components/image-production`; words: `static/tools/compose.py`
- Words for Meta: `components/copywriter/machine/brief_words.py`
- Cards: `components/meta-upload/to_check.py`
