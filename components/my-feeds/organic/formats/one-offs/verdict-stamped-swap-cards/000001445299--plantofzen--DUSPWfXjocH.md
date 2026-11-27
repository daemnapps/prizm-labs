# Verdict-stamped swap cards — rebuild sheet

A 13.65s post that spends one second on a face and the rest on five flat graphic cards: real branded products crossed out in red, then named substitutes ticked in green. 1,445,299 views · 56,389 likes · @plantofzen.

**Why it works**

The persuasion is recognition, not argument — the viewer sees bottles they own personally condemned, so the video is about their bathroom before it is about anything for sale. Because the answer is interleaved (condemn, condemn, replace, condemn, replace) instead of held to the end, every red card is a debt the next card pays, which is what keeps someone watching a slideshow with no motion in it.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 1.09s | Front-camera selfie, chest-up: young woman, long curly hair, nose ring, gold chains, white top, looking straight down the lens. Warm indoor/porch space behind her, wooden railing, side daylight. She holds nothing and does nothing. | Hair products that are k!lling you 💀⚠️ |
| 3.28s | Hard cut to a flat card — no room, no person, no hands. One continuous rippled-sand backdrop. Six hair-care bottles and jars (As I Am, tgin, Camille Rose, Curl la la, Cantu) cut out and grouped in the lower half, labels readable. Thick hand-drawn red X stamped across the whole group. | Toxic / Phenoxyethanol, BHT, Propylene glycol, Methylisothiazolinone |
| 5.46s | Identical card unit — same backdrop, same header position. Product group swapped for a bigger cluster of about nine drugstore bottles (Dove, Garnier Whole Blends, TRESemmé, Herbal Essences "Hello Hydration", argan oil of Morocco). Same red X. | Toxic / Phenoxyethanol, BHT, Propylene glycol, Methylisothiazolinone |
| 7.64s | Same backdrop, same framing, header flips to white. Five different products (ACURE dry shampoo, ATTITUDE super leaves, RAW SUGAR, Phillip Adam, an auromère shampoo bar in its box) grouped the same way under a large green tick. No ingredient line on this card. | Replacement |
| 9.83s | Same backdrop and framing, header back to red. Four hair oils (Dr Teal's tea tree, argan oil of Morocco, Mielle, a Doo Gro knit-itch growth oil) under a red X. The ingredient line has changed. | Toxic / Phenoxyethanol, BHT, Propylene glycol, Petroleum, Soybean Oil |
| 12.01s | Same backdrop and framing, white header. Only two products — a Nutiva organic virgin coconut oil tub and a TooCut Crown Elixir dropper bottle — under a large green tick. | Replacement |

**What the frames do not show, and I have not guessed at:** whether there is a voiceover or spoken track, whether the cards drift or animate at all between the sampled moments, whether the face returns at the very end (the last sample is at 12.01s of 13.65s), and how the products are physically composited — real objects laid on a sand-textured board, or cut-outs pasted over a sand image. The small red ingredient lines were read off a downscaled contact sheet and are at the edge of legibility; check the exact chemical names against the source before reusing them as claims. The two emoji in the hook line read as a skull and a warning triangle at this resolution.

**What carries the value**

The branded product group under the red X. It is recognition doing the work — real bottles with readable labels that the viewer already owns — answered a beat later by a named substitute group under a green tick, with the ingredient line supplying the stated reason. Nothing is demonstrated, nothing is applied, no result is shown.

**Shoot it**

- **The hook beat (1s):** phone front camera, chest-up, arm's length, subject looking straight down the lens, neutral face, no performance, ordinary daylight in a real room. It exists only to put a human at the top of the feed — it is one second and it never returns in the sampled runtime.
- **The cards (everything else):** no camera work at all. Phone on a tripod straight down over one large sheet or board with a single texture — here rippled sand — and the products laid out on it in a group; or build the cards flat in an editing app over one backdrop image. Either way the backdrop and the framing must be **byte-identical from card to card**; the only things allowed to change are the product group and the header.
- **Light:** flat and even, no strong shadow direction, labels sharp and readable. This reads as a poster, not as a photograph of a place.
- **Wardrobe:** irrelevant after the first second — plain everyday clothes, nothing styled.
- **Rules that hold the format together:** one word in the header, never a sentence. Verdicts alternate, never escalate. The X and the tick are hand-drawn and sloppy, not clean graphics — that is what makes it read as someone's opinion rather than an ad. Group size can vary card to card (six, nine, five, four, two) and it does not hurt. Only the condemning cards carry the ingredient line; the replacement cards carry nothing but the word.

**Or generate it**

The card beat is the format. Generate one and reuse the same backdrop and framing for every card.

```
vertical 9:16 flat product card, a group of {PRODUCT} bottles and jars shot straight-on,
cut out and composited side by side across the lower two-thirds of one continuous
rippled-sand backdrop, no shelf, no surface line and no room, even soft light with no
strong shadow direction, labels sharp and readable, graphic-poster look rather than a
photograph of a place, no person in frame ({SUBJECT} appears only in the one-second
selfie beat that opens the video), no on-screen text
```

**Motion:** no camera at all — the card is a held still, framing and backdrop identical from card to card; only the product group and the header change on the cut. (The six sampled frames show no movement, so any subtle drift is not visible in the evidence.)

**Text overlay pattern:**

- Opening beat, pinned over the selfie: `{CATEGORY} that are k!lling you 💀⚠️`
- Every card after: `{VERDICT}` as a bold header in the same position — red for the condemned card, white for the replacement card
- Condemning cards only, a second red line beneath the header: `{INGREDIENT_1}, {INGREDIENT_2}, {INGREDIENT_3}`
- A hand-drawn red X stamped over each condemned group; a green tick over each replacement group

**Reference:** https://www.instagram.com/p/DUSPWfXjocH/
