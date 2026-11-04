Write the production document for this piece. Every fact it needs, decided
now, before a single frame costs money.

**Every example in this prompt is illustrative only.** Ages, garments,
rooms, colours, products — none of them describe this brief. Take
everything from the material below. A document describing someone other
than this piece's cast is worthless no matter how detailed it is.

This document is read by the machine that writes every scene prompt. What
you decide here gets pasted into those prompts verbatim, so an
under-decided line here becomes a drifting scene there. Decide everything.
Where the brief genuinely leaves something open, choose — and mark the
choice `[CHOSEN]` so a human can overrule it — rather than leaving a gap
for a model to fill differently in every scene.

---

THE BRIEF

{brief}

THE FORMAT READ

{format_read}

THE FORMAT PROFILE

{format_profile}

THE BRAND

{brand_name}

THE PRODUCT

{product_file}

WHO THIS IS WRITTEN TO

{avatar}

THE WORDS THIS AUDIENCE USES

{language_bank}

TODAY

{today}

---

Return the document as clean Markdown, exactly these sections, in order.

## HEADER

```
{brand_name} — "<concept name, short, the way you'd say it out loud>"
PRODUCTION DOCUMENT · format: <the ruled format>

Delivery: 9:16 vertical · <placement> · 1080p · ~<n>s · <k> scenes
Grade:    <the look, in ONE specific sentence>
Audience: <the avatar, in a phrase> · Tone: <register, and where it lands>
Language: <language> · <profanity rule> · No dead air
```

The grade sentence you write is pasted into every scene prompt for the
rest of the production, unchanged. Write it knowing that: specific enough
to be one look, short enough to survive a hundred repetitions. Name the
era or reference, the skin tone, the contrast, the bloom, the sharpness.

## THE THROUGH-LINE

One paragraph of prose. What happens, who is wrong about what, what turns,
and how it arrives at the offer. Prose, not beats — you are checking the
piece works before it costs anything to find out.

Then, in CAPITALS on its own line, **any claim boundary this story runs
near**. If the emotional truth of the piece sits close to something the
product cannot claim, write the line that must never be crossed, here, in
the loudest place in the document. Repeat it at the offer. If the format
read found no boundary, write `NO CLAIM BOUNDARY IDENTIFIED` — never leave
this silent.

## CAST — IDENTITY LOCKS

A table. One row per role.

| Role | Locked appearance | Never |
|---|---|---|

**Locked appearance** is everything a generator needs to draw this person
identically every time: age, build, skin and its real texture, hair
(colour, length, how it is worn), any distinguishing marks the piece
depends on, and the ONE outfit they wear — garment by garment, with colour
and material.

**Never** is the column that actually works. Name the specific wrong
things: the clothes their reference photograph is wearing, the garment a
neighbouring character wears that they must not echo, the accessory that
keeps appearing uninvited. Vague nevers do nothing; name the item.

Under the table, **voice locks** — one line per speaking role: register,
pace, energy. Close with the instruction that the voices never blur into
each other.

## THE PRODUCT

- **Full name and packaging**, exactly as the real thing reads — container,
  colour, closure, every line of label text in order.
- **What comes out of it**, if that appears on camera: colour, consistency,
  behaviour on skin or surface.
- **The offer**: guarantee, discount, scarcity, call to action — and the
  claim boundary repeated verbatim.
- **Label handling**: name the scenes where the product is at hero size.
  Those scenes composite the real packshot rather than generating the
  label.

## THE PLACE

If the format uses one continuous space, draw its plan in plain text:

```
  BACK WALL
  [ <anchor 1 — what the camera orients on> ]
  [ <anchor 2 — where the product lives when nobody holds it> ]
  LEFT: <role> · CENTER: <role> · RIGHT: <role>
  <edge feature>
  <the open floor>
  <entrance>, backlit
```

Then name the **zones** (three or four, no more) and the **anchors**.
Every scene prompt uses this vocabulary and no other.

If the format uses several places, list them instead — one line each,
enough that each can be generated from the words alone — and say which
scene happens where.

## THE LEDGERS

Fill only the ledgers this format uses; the profile says which. For each
one you skip, write the ledger name and `— not used in this format`, so a
reader knows it was considered rather than forgotten.

**Entrances** — per scene: does anyone enter, and who? A character enters
once in a piece, ever.

**Positions** — a table: every role's first-frame position, per scene, as
percentages of frame (`x≈28% y≈62%`).

**Objects** — per scene: who holds the product, its state (capped, open,
set down), and the single scene where it changes hands.

**Camera** — the axis never crossed, and the left-to-right screen order
per scene.

**Atmosphere** — how the air, light, or mess changes across the piece, as
numbers, so the arc is scripted: `80% → 70% → 40% → 10%`.

**Wardrobe** — the cast table's appearance and never columns, written as
the block that gets pasted into every scene prompt.

## PER-SCENE MECHANICS

One block per scene:

> **SCENE n — <FUNCTION> (<n>s)** — <who is where at the first frame; what
> the entrance does, if anything>. Dialogue: "<line>" / "<line>".
> Mechanics: <the action chain, each step separated — including the beats
> a model would otherwise glue together, like setting an object down
> before using both hands>. End: <the last frame>.

Write the dialogue in full, with the speaker named. Write mechanics as a
chain with arrows. Where a scene has an exclusion — who is NOT touched,
what is NOT done, who does NOT appear — state it, because the exclusions
are what stop invented action.

Where the brief wants a variant opening, write it as its own scene marked
`ALT`. It costs one scene and buys a real choice at the edit.

## ANTI-DRIFT CHECKLIST

A numbered list of every invariant in this piece, phrased as a check
somebody runs before the set ships. Derive them from what you just
decided — this list is specific to this production, never boilerplate.
Include at minimum: wardrobe per role, each entrance happening once, the
scene-specific exclusions, product label legibility, the camera axis, and
the claim boundary at the offer.

---

Write the document and nothing else: no preamble, no summary, no closing
commentary. Your entire response IS the production document.
