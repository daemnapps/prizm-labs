# Skit open, captioned pitch — rebuild sheet

A scripted family kitchen scene that hard-turns into a locked salon frame where a stylist talks straight to camera and ends holding a bottle — 1,776,339 views, 55,687 likes, 127s, by velmabrooks__.

**Why it works**

The skit spends the first half of the runtime buying attention with people and a scene, so by the time anything is sold the viewer is already in a story rather than in an ad. Then everything stops moving: one salon frame, held to the end, while the captions name the excuse the viewer has already been given ("it's just your age"), overturn it with a mechanism, and land on a dose — the stillness makes the argument the only thing happening, and the salon behind the stylist is what licenses her to make it.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 0:10 | Home kitchen, handheld two-shot. A woman in a maroon uniform at the stove, mid-sentence, facing a bald man in a white t-shirt. Behind them at the dining table a younger woman has both hands over her mouth; an older grey-haired woman watches. | — |
| 0:31 | Same kitchen, same vantage, cast rearranged: older woman in grey on the left, woman in a purple satin top centre, the same man in the white t-shirt right. | Just pull up to my salon to Let me get you right |
| 0:51 | Hard change of place. Locked frontal salon frame: a stylist with silver-grey chin-length hair and glasses, in a black t-shirt, stands behind a woman seated in a black cape, hands on her shoulders, both facing the lens. The same man in the white t-shirt stands back-right. Lit mirrors, product shelves, salon chairs behind. | They told you it's just your age |
| 1:11 | Identical frame. Nothing has moved but the faces. | for |
| 1:32 | Identical frame again. | It gotta be That goes down in there |
| 1:52 | Same frame; the stylist raises a green-olive bottle to head height beside her face, toward the lens. | Few drops at night |

Two things the frames actually prove, worth keeping: the same man in the white t-shirt appears in both the kitchen and the salon, so this is one scripted piece with one cast, not a borrowed clip stitched onto a pitch. And the caption wording is broken in the way auto-generated speech subtitles break ("to Let me get you right", "It gotta be That goes down in there") — these are burned-in speech captions, not written copy.

What the frames do **not** show, and should not be invented: what is said in the kitchen scene, where the cuts fall between the sampled beats, whether anything is ever applied to the client's hair, and any before/after or result. There is no result shot anywhere in the six frames.

**What carries the value**

The caption chain delivered from an authority tableau. The persuasion is entirely in the order of the lines — the dismissal named, the mechanism asserted, the dose given — spoken by someone standing over a client in a working salon. The room and the caped client are the credential; nothing is demonstrated and nothing is shown to have worked.

**Shoot it**

- **Act one (roughly the first half):** a real kitchen, handheld phone at standing height, square-on, waist-up. Four people: the one talking, the one being talked at, and two reacting in the background. Let the reactions be visible — the woman with her hands over her mouth is doing real work. No on-screen text here except the one invitation line that sends the scene to the salon.
- **Act two (the rest, and it is the whole pitch):** put the phone on a tripod in a salon, standing eye height, square-on. Operator standing behind the seated subject with both hands on their shoulders, both facing the lens. Put one more person in the back-right of frame — it makes the room read as working rather than borrowed. **Then never touch the camera again.** Same distance, same angle, no reframe, no cutaway, to the end.
- **Light:** whatever the room has. Both acts are plain interior light — kitchen ceiling downlights, salon mirror lights and pendants. No added light, no grade, no polish. The phone look is part of it.
- **Wardrobe:** plain and flat. Black t-shirt on the operator, plain white t-shirt on the man, a plain black cape on the subject. Nothing branded, nothing patterned — the frame has to stay boring so the captions are the only event.
- **Captions:** burn in speech subtitles, gold-yellow, centre-low, one clause per beat. Do not tidy the grammar into copy — the auto-caption look is what makes it read as someone talking rather than someone advertising.
- **Last beat:** the product comes up to head height beside the operator's face, held toward the lens, in the same unmoved frame. That is the only new thing that happens in the back half.

**Or generate it**

The single most important beat is the locked salon tableau at 0:51 — it is four of the six frames.

```
vertical 9:16, locked frontal salon frame at standing eye height: {SUBJECT} seated
chest-up in the centre, draped in a plain black salon cape, facing the lens; an older
woman with silver-grey chin-length hair, glasses and a plain black t-shirt stands
directly behind her with both hands resting on her shoulders, also facing the lens;
a bald man in a plain white t-shirt stands further back at the right edge. Behind them
a working salon: two lit mirror stations, open shelves of product bottles, black salon
chairs, warm tan walls, small pendant lights overhead. Even warm interior salon light,
phone-camera look, slight grain, no retouching, no on-screen text. {PRODUCT} out of
frame at this beat.
```

**Motion:** camera absolutely static — same distance, same angle, no reframe and no cut for the rest of the runtime; the only movement is the two faces talking and, on the final beat, one hand lifting {PRODUCT} to head height toward the lens. Generate every beat from the same seed so the room and the people match exactly.

**Text overlay pattern:**

- Act one, once: `Just pull up to my {PLACE} to Let me get you right`
- Act two, one clause per beat, changing every beat, never pinned: `They told you it's just {THE DISMISSAL}` → `{CONNECTING WORD}` → `It gotta be {THE MECHANISM}` → `{THE DOSE} at night`

A note on cast: the post's own caption tags it `#syntheticperformer`, so the performers may be generated rather than filmed — the frames cannot confirm that either way. Either route still needs performers who speak and are lip-synced; there is no version of this format that works as hands-only.

**Reference:** https://www.instagram.com/p/Db6bXdLyzki/
