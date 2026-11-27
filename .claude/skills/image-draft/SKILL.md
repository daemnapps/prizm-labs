---
name: image-draft
description: Run the draft standard — turn a brand's finished static-ad briefs into judged drafts that match their swipes, then ship them to Drive, the pack and the draft folder; or run the same swipes for a new product or offer (the variant). Use whenever the owner says draft, drafts, redo the drafts, swipe and inject, match the swipe, the drafts aren't close enough, run the image chain, the brief pack, the draft folder, judge the rolls, new product on the same swipes, face scrub ads, a variant, or names a brief id like p152. Ruled 2026-09-17: "THIS IS THE STANDARD WE OPERATE WITH. DO NOT DEVIATE."
---

# The draft standard

> **Activates component:** `components/image-teardown` — `chain.py draft` (and `chain.py variant`).


External dependencies: `components/image-teardown/` (the machine), `brands/<brand>/offers/` (offer bank, guarantees), `brands/<brand>/brand-identity/palette.md`, `brands/<brand>/products/` (product files, `images.json`).

**One command. No options that change how it works.**

```
python3 components/image-teardown/chain.py draft --brand <brand>
python3 components/image-teardown/chain.py draft --brand <brand> --briefs p152,p158
```

It is also the last step of `chain.py start`, so a new swipe run ends with
judged drafts in the draft folder without anyone asking.

**A new product or offer on swipes already torn down** (the owner: "just use the
same swipes, we're just adjusting the product and offer"):

```
python3 components/image-teardown/chain.py variant --brand <brand> --product <slug>
```

Reuses stages 1–2, re-runs 3–6 with the new product and its offer, opens new
brief ids (`variant_of` set), then drafts, judges and ships — one pack per
product. The product needs its file, its offer-bank row and a picture first;
if the brand's product file has no parseable "treats"/"texture" line, the
note goes in `drafts/<brand>/products.json`, never in `brands/`.

It does, in order: three rolls per brief with the swipe as the reference →
every roll judged → best passing roll becomes the draft → Drive folders,
and the brand's pack zip (same link, updated in place). The round lands in
`components/image-teardown/drafts/<brand>/vN/`: `judge.json` (the scores),
`flags.json` (what failed) and `rejects.md` (why rolls were thrown out).

## The rules the command enforces — do not work around any of them

1. **The swipe is the picture.** It goes to the generator as IMAGE 1. The
   brief's picture paragraph never goes in.
2. **Organic post with no adult in it → left alone.** A doodle stays a
   doodle, a puppy a puppy, a baby a baby. No person added, no product, no
   words. The brand is not in the picture — that is the point of the swipe.
3. **Adult in the swipe → our woman**, generated fresh to fit each swipe
   from the brand's cast line. **No pinned photo of one person** — that put
   one face on 21 ads. Other people in the swipe are generated in place.
4. **The tube only where the swipe shows a product.** The product picture
   is attached only then. Other brands the swipe shows for comparison stay.
5. **Numbers only through THE WORDS**, which come from the offer bank. A
   swipe's own offer bar is dropped, never refilled. Nothing is invented.
6. **The judge decides.** Eleven tests — subject, different person, others,
   style, skin, product, words, offer, numbers, colour, anatomy — plus a
   match score. A hedge is a FAIL. No passing roll → roll again, up to four
   rounds; then the best roll ships **flagged** with what it failed. the owner:
   "if a draft didn't make it then you need to generate." Never an empty
   slot. An older unjudged draft never stands in.

The five quality rulings (2026-09-17, "lock in on the draft quality"), each
a line in the prompt and a test in the judge: a **different** woman (face,
structure, hair) who fits the swipe; the swipe's **medium** (an illustration
comes back drawn); the proof on the **skin the product is for**; the swipe's
**offer slots** filled from the offer bank and its accent **colour** replaced
by the brand's; the **product** from three angles rendered into the scene,
never the same cutout, the range where the swipe shows several.

The ruling in full: `components/image-teardown/DRAFT-STANDARD.md`.

## The prompts

Verbatim, the only copies, read by the tools at run time:

- `components/image-teardown/prompts/stage7-draft-match-swipe-v2-owner.md`
- `components/image-teardown/prompts/stage7-draft-leave-alone-v1-owner.md`
- `components/image-teardown/prompts/stage8-draft-judge-v2-owner.md`

**A change to a prompt is a new version file** (`-v2-owner.md`, and the tool
pointed at it), never an edit in place — and only on the owner's word. Every
prompt is listed in the prompt library (`components/image-teardown/build_prompt_library.py`
rebuilds it), so a change he cannot see there did not happen.

## The designer's side

Her prompts and references are the standard's (`worksheet.py` builds them
off `fal_drafts.assemble`); the walkthrough is `tools/walkthrough.py
--brand <brand>`, published as the designer walkthrough (URL in
`components/image-teardown/context/artifacts.md`; republish over it). When a
prompt or the standard changes, rebuild the work orders
(`tools/worksheet.py --brand <brand>`), re-deliver, re-pack and rebuild the
walkthrough.

## What the owner gets back

- One line: how many briefs, how many passed clean, which shipped flagged
  and what they failed (one clause each).
- A contact sheet — swipe left, our draft right, every brief — sent as an
  image so he sees it without opening anything.
- The draft folder (`components/image-teardown/drafts/<brand>/vN/`) and the pack link (unchanged).

No file paths, no code, no commands in the reply. He never runs any of this.

## When a brief keeps failing

The command already rolls it again (four rounds) and then ships the best
roll flagged. Read `drafts/<brand>/v<N>/flags.json` and `rejects.md`. Every
flag is a prompt defect: the picture is never edited by hand. If the same
defect repeats across briefs, that is a new prompt version, proposed to
the owner with the reason, not applied silently. Never quietly replace a flagged
draft with an older one.

## Cost and time

**GPT Image 2.5 through OpenAI** — one door for every picture (the owner, 2026-09-22; `--door fal` still runs the old fal Nano Banana Pro route so an old record is reproducible), 2K. About 4 minutes to generate 21 briefs × 3 rolls,
about 6 to judge them, then a few minutes of Drive uploads. Run the ship
step in the background if the session needs to keep moving.
