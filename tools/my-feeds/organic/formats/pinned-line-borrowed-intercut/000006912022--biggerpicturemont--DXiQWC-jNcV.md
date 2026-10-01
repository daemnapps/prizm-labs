# Pinned-line borrowed intercut — rebuild sheet

A 9.29s reel by **biggerpicturemont**: one caption held word-for-word from start to finish while the picture flips between the poster's own plain outdoor shot and letterboxed cinematic close-ups of stern men in suits. **6,912,022 views · 371,834 likes.**

**Why it works**

The line does the setup and then never moves, so every cut is read as an answer to it — and because the answer is grave, expensive-looking footage of somebody else, the joke lands as a collision between two registers rather than as a performance. The maker's own shot is deliberately unremarkable, which is what leaves room for the borrowed footage to overreact on his behalf.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 0.74s | Full-frame vertical. Medium-wide, side profile: young man on a paved outdoor plaza, black flame-print tee, light baggy jeans, silver watch, hands at his waist. Tree, hedges, concrete steps, a rust-coloured sculpture, blue sky, low warm daylight. Camera at his height, no move. | When bro says “ebony” instead of dark skin |
| 2.23s | Hard cut to a second source — a 16:9 clip letterboxed inside the vertical frame. Cinematic close-up of a middle-aged man, stern and unblinking, dark suit over a pale blue shirt, near-black background with a cold blue gradient. | same line |
| 3.72s | Back to the plaza, same spot, same camera height, subject a little further into frame. *Whether this is one continuous take or a second take is not readable from the stills.* | same line |
| 5.20s | The seam: a cross-dissolve with both sources at roughly equal opacity — the suited man's eyes sitting over the trees and hedges. | same line |
| 6.69s | Letterboxed again, tighter: a second face, three-quarter profile, wide fixed eyes, hard side key, deep shadow on the far cheek. Smooth painterly rendering, not documentary. | same line |
| 8.18s | Letterboxed, a third face: older man, grey receding hair, same suit, same cold blue key. Each cutaway is a **different** person reacting — that's the escalation. | same line |

*Not readable from the frames:* the audio, whether the subject ever speaks or moves between stills, and what the borrowed clips are from. The caption carries **#anime**, and the close-ups have a rendered look consistent with that, but the frames alone don't prove the source.

**What carries the value**

The gap between the unchanging line and the borrowed footage cut against it. Not the location, not the wardrobe, not the person — the reaction faces do the punching, and the viewer supplies the joke in the space between the two sources.

**Shoot it**

- **The two-source rule is the format.** Half your runtime is your own footage, half is a clip from somewhere else, alternating, with one dissolve at the midpoint. Skip the second source and there is no format left.
- **Your own shot:** phone, vertical, full frame, no letterbox. Camera at the subject's chest height, static, medium-wide, subject in profile or three-quarter, outdoors in open daylight. Nothing styled — a plaza, a sidewalk, a parking lot. The shot should be boring on purpose.
- **Wardrobe for your shot:** everyday street clothes, one graphic piece for a bit of colour. No brand styling, no set dressing.
- **The cutaway:** a graded, letterboxed 16:9 close-up in a dark interior with one hard side key — it has to look like it came from something else. Three different faces beats one face held three times.
- **Text:** two lines, centred, upper third, bold white sans with a dark outline. Written once, positioned once, never moved, never animated, never changed.
- **Cutting:** hard cut in and out of the first cutaway, cross-dissolve into the second half, then stay in the borrowed footage to the end. Total runtime under 10s.
- **Rights:** this version reposts somebody else's footage. For a brand rebuild, generate the cutaway or use clips you own — see below.

**Or generate it**

The cutaway is the half you can't shoot on a phone, so generate that:

```
vertical 9:16 frame with black letterbox bars top and bottom containing a 16:9
cinematic close-up: {SUBJECT} framed chest-up in three-quarter profile, stern
unblinking expression, mouth closed, wearing a dark suit jacket over a pale blue
dress shirt and a muted tie, hair neat; background is an unlit interior falling
to near-black with a cold blue rim of light down one side; single hard key from
camera-left, deep shadow on the far cheek, shallow depth of field, high-contrast
film grade, smooth painterly rendering rather than documentary; no {PRODUCT} in
this beat — the source frames show none; no on-screen text baked into the image
```

**Motion:** no camera move at all — hold the close-up dead still for about a second and a half, only breath, arriving on it as a hard cut or a slow cross-dissolve out of the plain outdoor shot. Generate two or three different faces from the same lighting setup so the cutaways escalate.

**Text overlay pattern:** `When {someone} says “{the fancy word}” instead of {the plain word}` — identical wording and identical position in every beat.

**Reference:** https://www.instagram.com/p/DXiQWC-jNcV/
