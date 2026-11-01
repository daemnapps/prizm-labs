# angle-pick v1 — read a brief, name its angle from the bank

<!-- Owner: the owner. Run by components/naming/angle_pick.py (model: the registry's
sonnet-class entry). Placeholders in {braces} are filled by the code; nothing
else in this file changes per brand. the owner, 2026-10-12: "The angle should be
derived from the brief itself through analyzing what the brief actually even
is. That's it. The angle should be in the notes of the brief." -->

INVENTED-EXAMPLE GUARD — read this first. Every example in these instructions
is invented to show a shape. No example names a real brand, product, person,
angle or line. Never carry an example's words into your answer. The only real
material is what sits between the BRIEF and BANK markers below; your answer
draws on nothing else.

## Your job

You are given ONE brief and the brand's bank of signed angles. Work out what
this brief actually IS — what claim the finished ad makes to the person
watching — and name the ONE angle in the bank that is that claim.

An angle is WHAT WE CLAIM: a sentence the customer could agree or disagree
with. It is not the format (song, skit, slideshow), not the style (animated,
photo), not the story's plot, and not the person it is for. A story about a
betrayal that ends on "it was never the tool you blamed" makes the claim
"it was never the tool you blamed" — the plot is the container, not the angle.

How to read the brief:
1. Find where the PRODUCT enters the story and what is SAID about the problem
   at that moment. That turn is where the claim lives.
2. Find what the brief says the person got wrong, or what was really going
   on, or what changes for them. Weigh the brief's own words over its title.
3. Match that claim to the bank by each angle's `what`. Pick the closest one
   whose claim the brief actually makes — not one it merely mentions.

## Rules

- Pick ONLY an `id` that appears in the BANK. Never coin, merge, rename or
  shorten an id.
- If no angle in the bank is the claim this brief makes, answer `no-fit`.
  Do not force the nearest one. A plain no-fit is a correct answer.
- `quote` is copied VERBATIM from the brief — one line or phrase, 4 to 30
  words, exactly as written (same words, same order). It is the line that
  shows the claim. It must be findable in the brief by search.
- `why` is ONE plain sentence, under 25 words, saying how the quoted line is
  that angle's claim. No jargon.

## Answer

Return ONLY this JSON object, nothing before or after it:

{"state": "picked", "angle": "<id from the bank>", "quote": "<verbatim from the brief>", "why": "<one sentence>"}

or, when nothing fits:

{"state": "no-fit", "angle": null, "quote": "<the line that shows the brief's real claim>", "why": "<one sentence naming the claim the bank lacks>"}

## The brief's header (facts filed with it)

{header}

## BRIEF

{brief}

## END BRIEF

## BANK — the brand's signed angles{bank_scope}

{bank}

## END BANK
