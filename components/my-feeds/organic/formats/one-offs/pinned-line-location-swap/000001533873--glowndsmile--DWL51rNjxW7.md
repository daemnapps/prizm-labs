# Pinned line, location swap — rebuild sheet

A 9.6s front-camera selfie video by glowndsmile: one age-claim caption pinned unchanged the whole way through while the same man appears in five different places and five different outfits, applying a small skincare product and finally holding it to the lens — 1,533,873 views, 6,378 likes.

**Why it works**

The caption makes one specific, checkable claim (21 at almost 32) and borrows a celebrity's name for it, then never argues the point again — so every beat afterwards is the viewer looking at his face to test the line rather than reading a pitch. The place and outfit change on every cut while the line does not, which reads as the same person doing the same thing on a lot of separate days, so the product looks like a habit that fits anywhere instead of a shoot that happened once.

**The beats**

| Time | What happens | On-screen text |
| --- | --- | --- |
| 0.77s | Car in daylight, black puffer. Close front-camera selfie, tilted. He presses a short purple applicator flat against the skin under his eye. | The pinned line |
| 2.30s | Train interior — window blind, luggage rail, pale headrest, earbud in. Grey-navy puffer. Hand at the hairline applying the same applicator to his forehead; a small purple mark is visible on it. | The pinned line, unchanged |
| 3.83s | At home — white tiled edge at frame right, open doorway onto a cluttered room behind. White-and-red football shirt. Hand up at the side of his head, mouth parted. No product in shot. | The pinned line, unchanged |
| 5.36s | Bathroom — beige tiles, toilet and toilet roll behind. Black embroidered formal jacket. Chest-up selfie, mouth parted. No product in shot. | The pinned line, unchanged |
| 6.89s | Back in a car, white puffer. His face pushed to the left edge while his hand holds a slim magenta pump bottle up to the lens, filling the centre. | The pinned line, unchanged |
| 8.42s | Same frame held to the end, the bottle slightly higher and closer. | The pinned line, unchanged |

The line, verbatim: **"POV: You tried this Korean wrinkle stick after Cardi B hyped it and now you look 21 at almost 32 lol"** followed by two emoji that are not legible at this resolution.

What the frames do **not** show, and I am not filling in: whether he is speaking (his mouth is parted at 3.83s and 5.36s but there are no speech captions, so there is no evidence either way); whether the beats are hard cuts or one continuous take; whether the purple applicator in beats 1–2 is the same unit as the magenta pump bottle held up at the end — the bottle's label is mirrored by the front camera and only partly legible; and any before/after, because nothing about his face visibly changes across the six frames.

**What carries the value**

The caption. One specific age swap attached to a famous name, pinned unchanged for the entire runtime, with the same face appearing under it in five unrelated places and outfits so it reads as repeated real use. The product held to the lens at the end is the receipt, not the argument — and no visible transformation is ever offered.

**Shoot it**

- **Camera:** phone front camera, held at arm's length, chest-up. Handheld with natural sway, no tripod, no zoom, no gimbal. One shot per location, nothing longer than about a second and a half.
- **Locations:** five ordinary ones you already pass through in a week — a parked car, public transport, a hallway at home, a bathroom, the car again. They must look plainly different from each other. No styling, no tidying, no set dressing: the clutter behind the doorway and the toilet roll in the bathroom are doing work.
- **Light:** whatever is there. Window light in the car, train window, ceiling light in the bathroom. Do not add lights — mixed and slightly ugly light is what makes the days read as separate.
- **Wardrobe:** a different jacket or shirt in every single beat, and they should not coordinate — a puffer, a football shirt, a formal embroidered jacket. The wardrobe change is the only thing telling the viewer that time has passed, so it has to be obvious.
- **Product:** applied on camera in the first two beats only — pressed to the face, not demonstrated or explained. Held up to the lens for the last third and simply held there to the end.
- **Text:** one caption, set once, never touched again. Same words, same position, every beat, top-middle third.
- **The claim has to be true enough to survive the face on screen.** This format has no transformation, no before/after and no proof of any kind — the only evidence is the person looking the way the caption says. Pick someone whose face supports the line.

**Or generate it**

The hook beat — the car, self-application:

```
vertical 9:16 front-camera selfie photograph, {SUBJECT} chest-up in the passenger seat of
a parked car, seat headrest and a bright daylight window behind, {SUBJECT} in a black
puffer jacket, one hand raised into the top of frame holding {PRODUCT} pressed flat
against the skin high on the cheek under the eye, head tilted slightly, eyes to the lens,
flat daylight from the car window, phone front-camera look, slight grain, no retouching,
no on-screen text
```

**Motion:** camera held at arm's length in the free hand with a small natural sway, no zoom and no cut — the only movement is the hand pressing {PRODUCT} against the skin.

**Text overlay:** `POV: You tried this {PRODUCT_TYPE} after {FAMOUS_NAME} hyped it and now you look {YOUNGER_AGE} at almost {REAL_AGE} lol {emoji}{emoji}` — white, four short lines, upper-middle third, identical wording and identical position on every beat, never changed and never completed into a second line.

Generating the other five beats means keeping the same face across every one (same seed) while changing the room, the light and the wardrobe completely each time. If the face drifts between beats, the format breaks — the whole point is that it is one person in five places.

**Reference:** https://www.instagram.com/p/DWL51rNjxW7/
