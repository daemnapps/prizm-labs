# The draft standard — how a swipe becomes our draft

**Ruled by Damon, 2026-09-17: "THIS IS THE STANDARD WE OPERATE WITH. DO NOT
DEVIATE THIS AT ALL. LOCK IN THE PROMPT / WORKFLOW."** This file is that lock.
A session that changes any step here, or the prompts it names, is changing a
ruling and needs his word first.

It is also a team skill — `.claude/skills/image-draft/` — so any session on
any machine that hears "drafts", "swipe and inject", "the pack", "the Brief
Board" or a brief id runs this and nothing else. It went straight into the
team folder on Damon's ruling (2026-09-17: "it needs to live in the repo
within the chain itself"), not through lab graduation; Dayu and Valentina
are told so in the commit.

**It is a step of the chain.** `chain.py start` runs it on every brief it
opens, after the six stages and the work orders (Damon, 2026-09-17: "put this
in chain"). On its own, for briefs that already exist:

```
chain.py draft --brand <brand>             every finished brief
chain.py draft --brand <brand> --briefs p152,p158
```

(`tools/draft.py` is the same thing; `chain.py draft` just calls it.)

## The quality rulings (v2, 2026-09-17 — "lock in on the draft quality")

After the first run passed 20 of 21, Damon read them and ruled five more
things, each now a line in the prompt and a test in the judge:

| Ruling, in his words | What the prompt does | What the judge checks |
|---|---|---|
| "people used look slightly different … new hair style, new facial structure but similar to fit the original" | THE PERSON: a different woman — different face, structure, hairstyle — same age, pose, distance, expression | DIFFERENT |
| "take note of the style of the original … the swipe is drawing style meanwhile we generated a real person" | THE MEDIUM, FIRST: the swipe is read for its medium; an illustration comes back drawn, a photo as a photo | STYLE |
| "we have the face shown which is technically correct, now we need contextual awareness" | THE SKIN: the proof (inset box, zoom, before/after) moves onto the skin our product is for, read off the product file; she keeps her place | SKIN |
| "the offer is missing and one of the guarantees is missing and the colour of the text is not on brand" | THE OFFER SLOTS: the swipe is read for price / guarantee / discount-bar slots and each is filled from the offer bank, never dropped. THE COLOUR: the swipe's accent is replaced by the brand's, off `identity/palette.md` | OFFER · COLOUR |
| "we are using the same product cutout over and over regardless of what the subject in the original" | THE PRODUCT: the clean tube from three angles (front, angled, in hand), rendered into the scene at the swipe's angle, never pasted; the range where the swipe shows several; texture only where the swipe has it | PRODUCT |

And a process rule (Damon, 2026-09-17: **"if a draft didn't make it then you
need to generate"**): a brief the judge passes nothing for **rolls again** —
another round of three, judged, up to four rounds. A roll is a dice throw; a
second throw is not a prompt change. What still has no passing roll after
four rounds ships its **best roll anyway** — highest match, fewest fails —
**flagged on the board with what it failed**. There is always a draft; there
is never a hole. The flag is the next prompt fix.

## A new product or offer on swipes already torn down — the variant

Damon, 2026-09-18: *"just use the same swipes, we're just adjusting the
product and offer … establish that so whenever in the future we need to run
a new product or offer with our swipes where we've already completed
teardown work it's easy."*

```
chain.py variant --brand <brand> --product brilliance-face-scrub
chain.py variant --brand <brand> --product brilliance-face-scrub --briefs p158,p159
```

Stages 1 and 2 — the teardown and the brand-free replication spec — do not
know what we sell, so they are **copied, not re-run**. Stages 3 to 6
(injection, headlines, variations, brief) are where the product and its
offer enter, so they **run again** with the new product's file and its row
in the offer bank. Each variant is its own run (`<run>--<product>`) and its
own brief id, `variant_of` pointing at the brief it came from; then the work
orders, the draft standard, a **pack per product** and the board follow as
for any brief. A product with no banked Element ships its clean picture in
the pack (`product.png`) and the work order says to attach it.

What a new product needs before the variant runs: its file in
`brands/<brand>/products/<slug>/product.md`, its row in the offer bank, a
picture in `products/images.json` — and, where the brand's file gives no
parseable line for what it treats or how its texture reads, the machine's
own note in `drafts/<brand>/products.json` (and a clean tube picture in
`drafts/<brand>/products/` if the brand's picture carries a smear).

## The designer runs the same thing (2026-09-18)

Damon: *"how would she trigger the variations and stuff in Higgsfield too.
I need literally a dumb simple process."* Her prompts are the standard's
prompts, word for word, with the same reference pictures — `worksheet.py`
builds them off `fal_drafts.assemble`, the one function the generator uses,
so what she makes and what we made can only differ by the roll. Each brief's
folder (Drive, and the pack) holds `refs/` — `1-swipe.jpg` first, then our
product from a few angles, then the range — and `prompts/`: `00-control`
(the standard's prompt) and each variation as the control plus one line that
moves one thing. In Higgsfield: Image → Nano Banana Pro → the brief's ratio →
attach `refs/` in order → paste → 4 → keep one → next tab. No Elements, no
presets. The walkthrough artifact (`tools/walkthrough.py`) is that page.

## The six steps

| # | Step | What goes in | What comes out |
|---|---|---|---|
| 1 | **The swipe is the picture.** The original post goes to the generator as reference IMAGE 1. The brief's picture paragraph does **not** go in — it was written before the swipe reached the generator and argues with it. | `runs/<run>/assets/source.jpg` | — |
| 2 | **Read the swipe once.** Kept in `drafts/<brand>/swipe-subjects.json`: is an *adult* the subject? does it show a *product*, how many, and its *texture*? what *medium* is it? which *skin* is the proof? which *offer slots* does it carry? what *accent colour*? Plus `swipe_kind` (organic / paid) from the brief's slot file. | the swipe | the read |
| 3 | **Organic + no adult → leave it alone.** A doodle stays a doodle, a puppy a puppy, a baby a baby. Our own version of the same photo: no person added, no product, no words. <brand> is not in the picture — that is the whole point of the swipe. | prompt `stage7-draft-leave-alone` | 3 rolls |
| 3′ | **Adult in the swipe → she becomes our woman.** The brand's cast line, generated fresh to fit each swipe — same pose, distance, expression; a *different* face, structure and hairstyle. **No pinned photo of one woman** (that put the same face on 21 ads). Other people in the swipe are generated in place. The medium, the skin the proof sits on, the offer slots and the colour follow the quality rulings above. | prompt `stage7-draft-match-swipe-v2`, every placeholder filled from the swipe read and the brand's own files | 3 rolls |
| 4 | **The product only where the swipe shows a product.** Then: the clean tube from three angles (never the tube-and-smear cutout), the range when the swipe shows several, rendered into the scene at the swipe's angle. Other brands the swipe shows for comparison stay. | `products/images.json` — the tube, hero, in-hand; the other products' heroes | — |
| 5 | **Offer slots filled from the bank.** Every price, guarantee or discount-bar slot the swipe carries is kept and filled with ours from `brands/<brand>/offers/` — price, multi-tube price, guarantee. A swipe's "60% off · ends soon" becomes "3 tubes for $74 · 60-Day Money Back". Nothing invented; nothing dropped. | the offer bank | — |
| 6 | **The judge, then the pick.** Every roll goes in front of a vision model with the swipe and the product pictures and answers eleven tests — SUBJECT, DIFFERENT, OTHERS, STYLE, SKIN, PRODUCT, WORDS, OFFER, NUMBERS, COLOUR, ANATOMY — plus a 1–5 match score. A brief with no passing roll rolls again, up to four rounds, then ships its best roll flagged. A hedge is a FAIL. The best passing roll becomes `draft.png`. No passing roll → **no draft**, and `rejects.md` says why per roll. An older unjudged draft never stands in. | prompt `stage8-draft-judge` | `draft.png` · `judge.json` · `rejects.md` |

Then `deliver.py` puts the draft in the brief's Drive folder, `pack.py` re-zips
the brand's pack in place, and the Brief Board is republished.

## The prompts, verbatim

They live beside the other stage prompts and are the only copies:

- `prompts/stage7-draft-match-swipe-v2-damon.md` (v1 kept for the record)
- `prompts/stage7-draft-leave-alone-v1-damon.md`
- `prompts/stage8-draft-judge-v2-damon.md` (v1 kept for the record)

`fal_drafts.py` and `draft_judge.py` read them from there. A change to a
prompt is a new version file (`-v2-`), never an edit in place, and it renders
onto the Brief Board under "How these drafts are made".

## What the judge is for, and what it is not

It is verification, not taste. Every reject in the 2026-09-17 run was a
checkable fact — an invented tube, a woman where a dog should be, a cloned
bystander, a price nobody set. Those are what it catches. It is told not to
fail a draft for the tube's fine print, for soft fingers, or for a guarantee
phrased naturally, because those are not what Damon rejects.

**Every reject is a prompt defect.** The picture is never fixed by hand; the
prompt is versioned and the roll re-run.

## The runs that set the standard

<brand>, 2026-09-17. v1: 21 briefs, 3 rolls each, 20 passed. v2 (the
quality rulings): 19 passed with eleven tests and a second round; p153 (the
drugstore selfie — every roll cloned her face or mangled the hands) and
p162 (the jar on sea buckthorn — the tube keeps coming out flat-on with a
smear the swipe never had) sit on the board with their reasons, which are
the next prompt fix, not a hold.

Model: `fal-ai/nano-banana-pro/edit`, 2K, the brief's ratio. Generation is
~4 minutes for 21 briefs; the judge ~6.
