# Running-caption borrowed cutaways — rebuild sheet

A dental hygienist talks straight to a propped phone in her bathroom for 75 seconds, holding up a lineup of electric toothbrushes, while burned-in captions track what she is saying and two pieces of borrowed evidence cut in — a plaque/tartar stat card and a macro of the brush head. 3,088,441 views · 26,329 likes · @tiffkimmm, paid partnership.

**Why it works**

The credential lands in the first line ("I am a dental hygienist"), so everything after it is read as information rather than a pitch — and the concession at beat two ("all of these can be effective") buys the rest of the runtime by refusing to trash the alternatives. The persuasion is then carried by material she didn't shoot: a hard number and a clinical before/after photo pair establish a problem the viewer didn't know they had, and the product arrives at the end as the answer to a problem already proven.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 5.97s | Chest-up selfie framing, bathroom, pale door and tile behind. Cream cardigan, layered necklaces. She fans five or six electric toothbrushes across the bottom of frame and talks to camera. | "I am a dental hygienist and I get a lot of questions about electric toothbrushes" |
| 17.92s | Identical frame. She pulls one black display-screen brush out of the lineup and looks down at it. | "all of these can be effective" |
| 29.87s | Same frame, but a graphic card is composited over the lower half: a headline band plus a split teeth photo labelled "Tartar" vs "Plaque". Her hand rises at frame right. | "Plaque reforms within 24 hours and hardens into tartar in 48 hours" / "the plaque often hides in between the teeth deep along the gum line" |
| 41.82s | Full cutaway, no face. Macro on a purple-and-white bristle head pressed into a white dimpled surface filling the frame. | "a vibrating and sweeping motion for effective cleaning" |
| 53.76s | Back to the identical selfie frame, hands out of shot, mid-sentence. | "then" |
| 65.71s | Same frame; a single brush with a pale blue-violet head enters from the right and is held beside her face — the hero unit isolated out of the opening lineup. | "and leaves my teeth feeling so squeaky clean and fresh" |

Where the frames don't tell us: I have six stills 12 seconds apart, so **the cut rhythm between these beats is unknown** — there may be many more cuts than six. **There is no audio here**, so I'm inferring from the caption style that these are her spoken words captioned rather than written titles; treat that as likely, not confirmed. And at 41.82s **the white dimpled surface the brush is on cannot be identified from the frame** — tooth model, towel, tile, all possible. Don't invent one; decide it at shoot time.

**What carries the value**

The borrowed clinical evidence. The credential opens the door, but the thing doing the actual persuading is the 24h/48h stat and the tartar-vs-plaque photo pair — material sourced from outside the shoot, which makes the problem feel like a fact rather than a claim. The product never has to sell itself; it only has to be the last thing on screen after the problem is proven.

**Shoot it**

- **Camera:** one phone, vertical, propped at chest height on a bathroom shelf or counter. It does not move — no pan, no zoom, no reframe — and the framing is identical in every talking beat, so the returns to face feel like one continuous take. Chest-up, subject centred, plenty of headroom.
- **Light:** whatever the bathroom has, front-on and even. No hard shadow on the face, no ring-light glare. It should look like a phone left on a shelf, not a set.
- **Wardrobe:** ordinary clothes, soft neutral layer, small everyday jewellery. Nothing branded, nothing costume. The look is "a professional at home", not "a creator on camera".
- **Talent:** this one needs a person with a real credential to state — it is the whole opening. Do not fake a qualification; if nobody on hand has one, the honest swap is stating years of use or a role you actually hold.
- **Props:** the full lineup of competing units in shot at beat one — the abundance is what makes the concession credible — and the hero unit held up alone at the end.
- **The evidence card:** built in post, not shot. A headline band with a hard number, and a two-up photo labelled either side of a "vs". Source it from real published material and keep the number accurate — this is the part carrying the persuasion, so a made-up stat breaks the whole format.
- **Captions:** small white type, low-centre, one clause at a time, replacing itself as she speaks. Not pinned, not a title — it should read as subtitles.

**Or generate it**

The generatable beat is the hook (5.97s). The evidence card at 29.87s is a graphics job, not a generation job — build that in an editor.

```
vertical 9:16 phone-camera photograph, chest-up selfie framing of {SUBJECT} talking
to camera in a real domestic bathroom, a plain pale door and tiled wall filling the
background, soft even indoor light from the front with no hard shadows, {SUBJECT}
holding up a fan of five or six units of {PRODUCT} across the bottom third of the
frame so each one is separately readable, everyday clothes and simple jewellery,
unstyled skin and hair, slight sensor grain, no on-screen text, no retouching
```

**Motion:** camera fixed at chest height as if propped on a bathroom shelf — no pan, no zoom, no push; only the head, hands and the held units move. Generate every talking beat from the same seed so the room and framing match exactly across returns.

**Text overlay pattern:** running spoken-word captions, small white type low-centre, one clause per beat replacing the last —
`{credential} and I get a lot of questions about {category}` → `{concession about the alternatives}` → `{hard stat about the problem}` → `{how the mechanism works}` → `{the result claim}`.
At the stat beat, a separate composited card sits over the lower half: headline band plus a labelled two-up evidence photo.

**Reference:** https://www.instagram.com/p/DRgI3PJEXse/
