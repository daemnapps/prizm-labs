# Stage 8b — Read-back v1

*v1 (2026-10-09, the owner, reading the first copy the machine wrote for a face ad: "if you know it's a face ad, why in the world would you have anything about my legs? … it doesn't look like it actually gets spice or levels of humanization like I have with the video scripts … it feels very, very staccato. Again, not like full sentences that a human is delivering. Remember, all this copy is so that real people read it and can visualize what's being read."): the pass between the render and the copy gate. Stage 8 writes the argument correctly; this stage makes it read like a person wrote it to one person, keeps it on this product, and gives it the picture and the spice the video scripts get. It changes the SHAPE and the TEXTURE of the words, never what they claim.*

Today is {today}.

Here is the copy stage 8 wrote — every body under its format, then the headlines and descriptions: {render}

Here is the product — what it is, where on the body it is used, what it may claim: {product_file}

Here is the brand: {brand_context}

Here is the record of the source — who is speaking, what happens, what the viewer sees: {record}

Here is the finished ad these words sit beside, when there is one: {the_ad}

Here is what the market says — real sentences from real people, each with its id: {language_bank}

Here is what the last reader said about this copy, when it was read before (the stage 8c copy check — fix exactly what it names): {reader_notes}

Here is the culture read of the source and the avatar's culture map — what they recognise, what they laugh at, what is off-limits: {culture_read}

{culture_map}

---

## Who reads this

One woman, on her phone, at night, scrolling. She reads the first line, and if it reads like a person talking to her about her own face, she taps "…more". She reads every word after that the way she would read a text from a friend who found something that worked. She is not a marketer. She has tried everything. She can smell an ad.

Everything below is for her.

## For each body, fill these slots, in this order

Print each slot with its label. A slot you cannot fill from the inputs above says `[UNFILLED]` and the body is written without it — never with an invented stand-in.

```
FORMAT: <the format, as stage 8 named it> · BODY <letter>

SCOPE
  The product is used on: <the body area the product file names — face, body, hands…>
  Lines in the stage 8 body about any other body area: <quote each, or "none">
  → every such line is cut. A face product talks about the face. Nothing about legs, arms or
    hands in a face ad, even when the market row says it — the row is about a different product.

THE READ (stage 8's body, read aloud as her)
  <each sentence of the stage 8 body, numbered, with one tag each:>
  FULL — a complete sentence a person says
  CLIPPED — a fragment or a list of fragments ("Twice a week. Sixty seconds.") that reads like
            a label, not a person
  NARRATED — a person announcing, not saying
  AD — a line she would recognise as marketing

THE PICTURE
  The one thing she sees in her head while she reads this body: <one concrete image, drawn ONLY
  from the record or the finished ad — what is on screen, what the product does on skin, a
  moment from the source. Never invented.>

THE SPICE
  <at most two touches that make it hers: a phrase from a market row (quote it, with its id),
  or a reference from the culture read / culture map (quote the line it comes from). Or "none —
  the rows don't give one". Never a joke on the claim or the offer. Never a word the rows
  don't contain.>

KEPT EXACTLY
  <every fact the body carries — each claim, number, ingredient, the offer line, the guarantee
  sentence, the call to action — listed, so the rewrite can be checked against it>

READ-BACK
<the body, rewritten. Full sentences, joined the way a person joins them ("so", "and", "because",
"which is why"), a breath where a person would breathe. Every CLIPPED line becomes part of a
sentence. Every NARRATED or AD line is said plainly or cut. THE PICTURE is in it. THE SPICE is
in it, if there is any. Everything in KEPT EXACTLY is in it, in the same order, the offer and
the guarantee word for word. Nothing from SCOPE's cut list. Inside the format's word range.
The last line is the call to action stage 8 ended on.>
```

## Then the headlines and descriptions

Exactly three headlines, 40 characters or fewer: (1) the angle as a plain statement, (2) what the product does, (3) the offer. Exactly two descriptions, 30 characters or fewer: (1) the offer, (2) the guarantee. Keep stage 8's where they already do that job; replace the rest from the product file and the offer only. Each is something a person would say, not a slogan.

## Rules that never bend

- **Same claims, same offer, same order.** This stage changes how the words read, never what they say. No new claim, no new number, no new ingredient, no price that is not in the offer line.
- **Full sentences.** A fragment is allowed only where a person would really stop short for effect, at most once per body. A run of fragments is a list, and a list is not how a friend talks.
- **She can picture it.** Every body carries one image she can see. An abstract body ("works on the skin underneath") gets the picture next to it, or it does not land.
- **On the product.** The scope line is a cut list, not a suggestion.
- **No em-dashes** (people don't write them to friends either), no stacked rhetorical questions, no alliteration, no "Here's the thing".
- **Same number of bodies as stage 8, same formats, same letters.** This stage rewrites; it does not add or drop a body.

## Return

After every body's slots, print the finished copy ONCE more, clean, in exactly the shape stage 8 used, so the next stage reads it unchanged:

```
**FORMAT: <format>**

**BODY A**

<the READ-BACK text>

*<n> words.*

---
```

…one block per body, then:

```
**HEADLINES**

1. **<headline>**
2. **<headline>**
3. **<headline>**

**DESCRIPTIONS**

1. **<description>**
2. **<description>**
```
