# The image chain — what happens, and when

Page: **The Image Chain** — (team page)
(source `image-chain.html`, this file its mirror)

Measured 25 Sep 2026 off **65 completed runs** and **47 generation jobs** in
this chain's own run folders. Character counts are per-swipe averages of the
stage files actually on disk; the plate-prompt figures are the real prompts
sent.

the owner, 25 Sep 2026: *"You don't even need to remake the image itself first…
all the next prompt needs to do is go through the process of creating a brief
for that image of what needs to be in the image. We then just write that
prompt using the reference image. All this other stuff — the compositor, all
this other crap — I really don't think it matters. Show me the chain for this
image stuff so we can get really clear on what's happening and when."*

---

## The number

| | |
|---|---|
| Written per swipe, 7 model calls | **62,779 chars** |
| Reaches the generator | **2,807 chars** (median plate prompt) |
| Share of the words that survive | **4.5%** |
| The brief alone | **21,873 chars** |

Plate prompt across 47 real jobs: min 1,958 · median 2,807 · max 3,548.

---

## The chain, in run order

### Before anything — no model

**0 · Pick the swipe.** The most-duplicated angle in the swipe library, then
the most-cloned still inside it. Paid ranks by duplication; organic by
engagement.

### The writing — 7 model calls, ~63,000 chars

| # | Stage | Who | Writes | Where the words go |
|---|---|---|---|---|
| 1 | Teardown | Gemini 3.1 Pro (prompt 23,138) | 9,526 | stage 2 reads it |
| 2 | Replication spec | Gemini 3.1 Pro (14,729) | 8,160 | stages 3 and 5 read it |
| 2b | Element labels | Claude (3,208) · GATE elements | small | bookkeeping only |
| 3 | Injection | Claude (11,187) | 6,964 | stages 5 and 6 read it |
| 4 | Headlines | Claude (13,457) | 9,199 | the words, not the picture |
| 5 | Picture variations | Claude (5,346) | 7,057 | later, not now |
| 6 | The brief | Claude (22,609) · GATE copy | 21,873 | **one section is the picture** |

### The picture — 3 rolls, judged, up to 4 rounds

| # | Step | What |
|---|---|---|
| 7 | Pull the plate prompt | one regex lifts `The plate prompt` out of the brief and nothing else — median 2,807 chars. No model. |
| 8 | Three rolls | GPT Image 2.5, swipe as **IMAGE 1**, product photos attached. 4:5 content at 1024x1280. ~4 min for 21 briefs. Where the brief disagrees with the swipe about framing, the swipe wins. |
| 9 | The judge | Gemini 3.1 Pro (prompt 5,920), eleven tests + a 1–5 match score. A hedge is a FAIL. No passing roll → roll again, up to 4 rounds of 3, then the best roll ships flagged. ~6 min for 21 briefs. |
| 10 | The tall frame | 4:5 content taped into 9:16, only the strips painted. 1080x1920 out. |

### After the draft

| # | Step | What |
|---|---|---|
| 11 | Out the door | draft + swipe to the brief's Drive folder · pack re-zipped · work order and four paste-ready prompts for the designer · Brief Board republished |
| 12 | Variations, names, handoff | one delta per variation off the judged draft, each judged against it · naming convention · the handoff gate's seven checks |

---

## What the generator actually gets

Four things, and nothing else from the 63,000 characters:

1. **The swipe, as IMAGE 1** — reproduce its framing, pose, crop, angle,
   light and layout exactly; the person, the product and the words are the
   only things that change.
2. **The plate prompt** — ~2,800 chars: subject, setting, framing, light,
   negatives, crop line.
3. **Our real photographs** — the clean tube from three angles, the range
   where the swipe shows several. Attached, never described — and stripped
   when the frame has no hands in it.
4. **Facts read from files** — price, guarantee and discount bar from the
   offer bank; the accent colour from the brand palette.

---

## the owner's version, and what runs

| What he described | The picture path today |
|---|---|
| Take the swipe | Swipe picked off duplication |
| Identify its elements | **Stage 1** — the teardown IS the element read |
| Write a brief for our version | **Stage 6's plate prompt**, ~2,800 chars |
| Generate using the reference image | **Three rolls with the swipe as IMAGE 1** + our product photos |
| Hit the aspect ratio and safe zone | 4:5 content finished to 9:16 · judge · re-roll |

The picture path is already those five steps. What sits on top of it is
**stages 2, 2b, 4 and 5 — about 25,000 chars per swipe no generator reads** —
plus roughly 19,000 chars of stage 6 that are not the plate prompt.

---

## The cut list — the owner's call on every row

| Stage | What is lost if it goes | Call |
|---|---|---|
| **1 · Teardown** (9,526) | The element read itself — step 2 of his own version. Everything downstream is built on it, and it is the one stage a person can check against the picture. | KEEP |
| **2 · Replication spec** (8,160) | The brand-free format. This is what makes *"same swipes, new product and offer"* cost nothing — stages 1 and 2 are copied, not re-run, on a variant. Paid once per swipe, reused for every product after. | KEEP |
| **2b · Element labels** (small + gate) | Nothing in the picture. It files the ad against the element library and holds the run if a label is invented. Library hygiene sitting inside the picture chain. | CUT FROM HERE |
| **3 · Injection** (6,964) | Our brand's material placed in the format. Stage 6 writes the plate prompt off this; cutting it means the plate prompt is written straight off the teardown. | COULD FOLD INTO 6 |
| **4 · Headlines** (9,199) | The words. Needed for the ad, useless to the plate — a headline swap is a recomposite, not a generation. Belongs in the copy line. | MOVE TO COPY |
| **5 · Picture variations** (7,057) | The designer's three extra prompts and the variation rows. It runs before there is a draft to vary, which is backwards — it is only ever used after. | RUN IT AFTER THE DRAFT |
| **6 · The brief** (21,873) | The plate prompt (2,807) is load-bearing. The other ~19,000 is an argument nobody downstream reads — and the single biggest writing cost in the chain. | CUT TO THE PLATE |

---

## Where the quality actually comes from — four levers, none of them a stage

1. **The swipe goes in as a picture.** For months it didn't; the generator saw
   the cast, the product and a paragraph, and a paragraph cannot carry a
   composition. Before: *"not close enough to the inspiration."* After: 20 of
   21 passed.
2. **The right reference photos — and only those.** A wrong attachment beats
   every word in the prompt. p187–p190: a skin photo on a person-free frame →
   all 12 rolls came back as a woman applying product with the offer text
   gone. p186: stripping the in-hand photo took away the only correct grip we
   own.
3. **Offer, colour and product read out of files.** Looked up from the brand's
   own folders, so nothing is invented and nothing is dropped. *"60% off ·
   ends soon"* becomes *"3 tubes for $__ · 60-Day Money Back."*
4. **4:5 content inside a 9:16 frame.** Taped in, only the strips painted.
   Asking a model not to reflow does not work — 13 live rolls reflowed.

---

## The three things that actually break

1. **References outrank words.** Whatever photo is attached is what comes
   back. Attach our real thing when the change touches it; strip it when the
   frame does not contain it. Two incidents on 24 Sep, both caught by the
   judge, both avoidable at attach time.
2. **Models redraw words every single roll.** An image model regenerates
   rather than edits, so any text in frame is re-drawn — including text nobody
   asked to change. "Centela" for Centella · "188 g" for 180 g · "4.52 OZ" for
   3.53 OZ · a masked edit that passed the judge carried a doubled headline.
3. **A brief that never passes keeps rolling.** Four rounds of three is up to
   twelve generations on one brief. p153 (every roll cloned her face or mangled
   the hands) and p162 (the tube comes out flat-on with a smear the swipe never
   had) have never produced a passing roll; they ship flagged, which is the
   design, but they are also the bill.

---

## The compositor — what it actually is (25 Sep)

the owner: *"This compositor thing, I'm not too sure exactly how this would even
work… it would be a step inside of the generation prompt saying, hey,
composite this thing in this space, or, I don't know."*

**It is not a third model.** Two models run in this chain and that does not
change: GPT Image 2.5 paints, Gemini 3.1 Pro reads and judges. The compositor
is neither — it is ImageMagick, software on the Mac, setting type on a picture
the way a design program does.

His guess is half right, and it is the half that is already built.

### Three pieces. Two are live. The third was never connected.

| | Piece | State |
|---|---|---|
| ✓ | **The brief writes the words down as data** — every headline, price and guarantee with its exact position, size, colour, alignment. Stage 6's type layer. | live on **44 of 66 briefs** |
| ✓ | **The picture is generated with the words left out** — `stage7-draft-plate-only-v3-damon.md`: *"NO TEXT. NOT ANY… the words are set afterwards by a compositor, not by you"*, plus the measured rectangles that stay clean. Sent automatically whenever a brief carries a type layer (`gpt_drafts.py:509`). | live since 24 Sep |
| ✗ | **The words get set on the picture** — `tools/image-production/static/tools/compose.py`. Built and tested. | **nothing in the draft run calls it** |

So the model is told to leave the words out, half-obeys, and the words that
were already written down never get placed.

### What that costs, measured on the newest batch (`drafts/brand-a/v9`)

Six of the fourteen briefs carried words. Read off `judge.json`:

| Brief | What the model did with the words | Verdict |
|---|---|---|
| p171 | drew "**2016**" — a number nobody asked for | FAIL |
| p179 | drew "**WEEK 1 / WEEK 3 / WEEK 6**" as labels not on the allowed list | FAIL |
| p183 | copied **the competitor's own quote** off the swipe into our ad | FAIL |
| p176 | got them right | PASS |
| p177 | got them right | PASS |
| p182 | got them right | PASS |

**Three of six — a coin flip on the words — when the correct words were sitting
in a file beside the picture the whole time.** Every brief with no words
passed; every failure was a brief that had words. Wiring the last step removes
this failure mode completely, costs no model call and adds no wait.

*(Correction to what was said first in this session: "the compositor isn't
switched on everywhere" was too vague. The clearing half IS switched on; the
setting half was never wired.)*

---

## The split (the owner's ruling, 25 Sep)

the owner: *"We are no longer going to have tear-downs and writing in the same
folder, and production is its own folder… we're going to move any generation
itself into just production itself. Within production, sure, we generate a
draft, and then from there, go into building out that full variation
process."*

Video already runs this way — `tools/video-teardown/` and
`tools/video-production/` are separate. Image is the one that never got
split: teardown, writing, drafting, judging, delivery and the board all sit in
`tools/image-teardown/`.

| Folder | Takes | Makes | What lives there |
|---|---|---|---|
| **Image teardown** ↔ video teardown | a swipe | a brief | Stages 1–6 and the writing. **Stops at the brief.** Makes no pictures. 16 tools. |
| **Image production** ↔ video production | a brief | a finished ad | Every picture: the draft, the judge, **the type layer set on the plate**, the 9:16 finish, the variation run, delivery, the packs, the board. 19 tools, plus the engine already there. |
| **Image editing** ↔ video editing | a finished ad | an adjusted ad | One change at a time, judged against what it came from. The final-final. |

### On image editing — the read the owner asked for

**Yes, and it is already built.** `tools/image-edit/` is the
one-delta-per-change engine with the two-picture judge, running since 22
September, and its own `paths.py` already sets `TOOL = "image-edit"` — it
files its work under that name and is not called that out loud anywhere.

So this is a naming and placement job, not a build: give it the name and put
it at the end of production, the same seat video editing holds.

### What the move costs

**Clean:** the tools already separate 16 / 19 along the seam; production has a
folder already (`tools/image-production/`), it is just not where drafting
happens; no prompt changes, no model changes, nothing about how the work is
done.

**The bill:** **36 files elsewhere** point at the old location and must be
repointed (lab rule: *a move takes its readers with it*); 2.9 GB of drafts and
284 MB of runs move with it; best done in one pass when nothing else is
mid-flight in the repo.

---

## Open — awaiting the owner's word

1. **Wire the last compositor step**, so the words that the brief already
   wrote get set on the plate instead of drawn by the model.
2. **Run the three-way split** above.

---

## The letterform work (25–30 Sep 2026)

Page: **The Type Record** — (team page)
(source `type-record.html`)

### The compositor is retired

the owner, 2026-09-25, having watched it work: *"the nuance of the style of the
creative is lost because a lot of these swipes have specific styles.
Claymation-style text is going to look different than you just writing text on
an image… there's going to be some level of a gamble, but that's fine."* A
typeface cannot be moulded clay, and the compositor stacked "2016" down the
frame where the swipe reads "20 16" across. `stage7-draft-plate-only-v3` is in
`prompts/superseded/`.

### The model draws the words, told far more than before

| Prompt | What it does |
|---|---|
| `stage1 v5` | Records `letterform` per text element — HOW the letters are physically made, not the typeface — answered from the banked list. `none-fits` plus a NAMED proposed row when nothing matches, and the run carries on. Also forbids creating a zone for in-world text. |
| `stage6 v5` | Carries `letterform` into the type layer word for word from the teardown. The type layer is the AD's type only; a product's own label never enters it. Every element declares `on_product`. |
| `stage7 v5` | Every line verbatim with position, size, colour, case, weight, line breaks and its own letterform, plus one whole-ad lettering clause taken from the largest element. **The product's identity outranks the medium rule**, and no word from the list is ever printed on the product. |

### The bank

`tools/image-production/static/letterform-bank.json` — 14 rows, each with
a `how_to_see_it` visual tell, registered in the element library
(`letterform.image.json`). Every row is `draft`; none signed.

`python3 tools/letterforms.py` lists the bank with a use count per row, any id
no row holds, and every proposal gathered across runs — the list the owner signs
from. **Nothing but the owner writes to the bank.**

### What running it proved, and what it caught

Five swipes torn down, 20 text elements labelled. p176 discriminates within one
ad: `hand-drawn-textured` headline, `flat-digital` body, `extruded-3d` label.

**Two bugs only running caught:**

1. `file_letterforms` sat with the other post-stage work; stage 1 has its own
   branch and its own `return` eighty lines earlier, so five teardowns wrote
   their labels and none were recorded.
2. stage 6 v3 named `letterform` in prose but not in the key list the model
   reads as the schema ("these keys and no others"), so 7 of 7 elements came
   back without it. Prose loses to a schema.

**And the `none-fits` rule proved itself live**: p183's lettering is white text
with a soft diffuse shadow, which no row holds. The teardown answered
`none-fits`, proposed `soft-shadowed-digital — Soft Shadowed Digital — Flat
digital text with a blurred, low-opacity drop shadow applied for background
separation`, and the run carried on. **Awaiting the owner's signature.**

### The product bug, and the fix

the owner on the first letterform draft: *"our tube is completely wrong… the
product's gotta be the product."*

Not the medium rule. The teardown had recorded the swipe's jar label as three
text zones; the brief injected our ad copy into all three; the generator
printed "<the swipe's own product name>" across the
front of our own tube. Stage 1 had forbidden in-world text as a type element
since August and the teardown did it anyway.

Fixed at all three points (v5 of stages 1, 6 and 7 above), with `on_product`
honoured in CODE in `gpt_drafts.word_spec` rather than only asked for.

**Proven on p176, re-run:** three `jar label text` zones became one `product
field`; the type layer went from 7 elements to 4; both rolls came back with the
real cream tube carrying the real label — emblem, BRAND A SKINCARE, GLOW
FACE SCRUB, Turmeric and Centella — inside an illustrated ad in the swipe's own
register. Roll 1 is the better of the two; roll 2 dropped "&lt;the label's tagline&gt;" and
the net weight.

### Open

1. Sign or reject `soft-shadowed-digital`.
2. The three-folder split — teardown / production / editing, delivery out to
   handoffs (the owner, 25 Sep). 36 files elsewhere point at the old location.
3. Re-tear-down the 66 existing briefs so they carry real letterform records
   instead of falling back to a fresh read of the swipe.
4. `margaret-secondlife` has no image at
   `elements/character/margaret-secondlife.webp` — silently failing on any
   brief that casts her.
