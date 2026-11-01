# Subtitled monologue, evidence cutaways — rebuild sheet

A man talks to camera in a black studio and runs through a numbered list of foot symptoms, each one answered by a small proof clip dropped into the corner of his own frame — 338,934 views, 9,003 likes, 47.8s, posted by drewcanole with the caption "What do your feet need?"

**Why it works**
The speaker never argues a claim; he names a symptom and a picture of that exact symptom appears in the same second, so the viewer diagnoses themselves instead of being sold to. The numbered list makes them wait for their own item to come up, and the speech caption underneath is always cut off mid-sentence, so there is no clean place to leave between items.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 3.83s | Locked mid-shot, dark studio, podcast mic across the lower-left. Speaker looking down and off-lens. A white-bordered inset in the lower-left corner: macro of a dry, deeply cracked heel with a gloved hand working a yellow tool over it. | `1  Dry cracked heels` |
| 11.48s | Presenter gone — full-frame white explainer graphic. A line-art figure with water droplets, captioned; below it two outlined boxes naming nutrients. | `Dehydration` · `Zinc` · `Omega 3` |
| 19.13s | Identical studio frame, same seat, same mic. Speaker to lens, hand mid-gesture. New inset in the same corner: bare feet on a weathered wooden deck. | `2  Cold feet at night` |
| 26.78s | Transition frame — the studio shot blurred and doubled, red glow across the top, hand smeared by motion. | none |
| 34.44s | Identical studio frame, no inset. Speaker smiling, hand raised to the lens. Speech caption low-centre, one word boxed in red. | `that in the past.` |
| 42.09s | Full-frame cutaway in a rounded frame, visibly not the studio: gym floor, weight plates against the wall, a surfboard behind, a person rolling a small ball under one bare foot. | `and peppermint and focus` |

Where the frames don't tell us: the symptom words at 3.83s sit *behind* the big red numeral and are partly hidden — `D_y _ra__ed / hee_` is all that is actually legible, so "Dry cracked heels" is a read, not a certainty. The 26.78s frame is clearly a transition but the stills cannot say whether it is a whip cut, a cross-dissolve or an applied effect. Nothing in the stills shows whether the speech captions also run underneath the numbered list beats, or whether the numbered label simply replaces them. And the gym clip at 42.09s is framed differently from everything else — it may be borrowed, it may be his own B-roll; the still can't settle it. No audio was available, so every caption here is what is written on screen, not what is said.

**What carries the value**
The proof inset. A symptom named in text and a real close-up of that exact symptom in the same frame, in the same second — unglamorous, unretouched, recognisable. Everything else in the video is scaffolding around that pairing. The numbered list is what makes the viewer sit through items that aren't theirs.

**Shoot it**

- **Camera.** One phone on a tripod, chest height, locked. It does not move, not once, not between items. Every studio beat must be the identical framing — same seat, same distance, same mic position — so the only thing that changes on screen is the label and the inset.
- **Light.** One soft source front-left of the subject. Nothing behind them. Shoot in a room where the back wall can go black — turn off every light behind the subject and stand well clear of it. Black falloff is the whole look; a lit wall kills it.
- **Wardrobe.** A patterned short-sleeve shirt reads casual-expert on camera, which is the register the piece runs in. Glasses help. No branded clothing.
- **Prop.** A podcast microphone on a boom arm crossing the lower-left of frame. It is doing credential work, not audio work — it stays in shot the whole time.
- **The insets.** Shoot these separately and dirty: real close-ups of the actual problem, phone macro, plain light, no styling. One per list item. Composite each into the lower-left quadrant of the locked frame with a thin white border. Frame the speaker leaving that corner empty so nothing is covered.
- **The graphic beat.** One full-frame white card with a simple line icon and two or three named boxes. Take the presenter off screen for it entirely.
- **Captions.** Burn in the speech track low-centre, one clause per beat, always breaking mid-sentence. One word per card knocked out in a red highlight box. On the list beats, a huge red numeral with the symptom in white across the chest.

**Or generate it**

```
vertical 9:16, {SUBJECT} seated in a dark windowless studio, mid-shot from chest
up, background unlit and falling off to pure black with no visible set behind
them, a large black podcast microphone on a boom arm entering across the
lower-left of frame, {SUBJECT} in a patterned short-sleeve shirt and
clear-rimmed glasses, looking slightly off-lens mid-sentence, soft key light
from front-left with a cool rim along the shoulders, studio look with slight
grain, no retouching, no on-screen text, and the lower-left quadrant left empty
and unobstructed for a white-bordered inset clip of {PRODUCT} being used on the
named problem area
```

**Motion.** Camera absolutely locked — same seat, same distance, same mic position at every beat (generate every studio beat from the same seed); only {SUBJECT}'s face and hands move, while the inset plays inside its fixed white-bordered box in the lower-left.

**Text overlay pattern.** List beats: a huge red numeral `{N}` over the speaker's chest with `{symptom, 2-4 words}` in white beside it, same position every item. Non-list beats: running speech subtitles low-centre in the same position all runtime, one clause per beat, always cut off mid-sentence, with `{one word}` knocked out in a red highlight box.

**Reference:** https://www.instagram.com/p/DUtzJRSkS4q/
