# Pinned-headline monologue — rebuild sheet

One man in a plain room talks straight to his phone for 62 seconds under a single unchanging headline — 1,427,240 views, 21,222 likes, by @urolderbroandunc.

**Why it works**

The headline is a narrow, oddly specific accusation — not "bad bosses" but "a 35-40 year old fit single dude" — so the viewer recognises a real person from their own life in the first second and then stays to hear whether the rest of the rant matches him. Because nothing on screen ever changes, there is nothing to look at and nothing to argue with except the headline, which means every spoken line is read as another item of evidence for a claim the viewer already nodded at.

**The beats**

| Time | What happens | On-screen text |
| --- | --- | --- |
| 4.95s | Chest-up front camera on a man in a rust-brown crew tee, curly greying hair, already mid-sentence to the lens. Off-white wall, a large wooden frame or mirror leaning against it behind his left shoulder, a small dark picture on the wall. Flat soft daylight from the front. | Pinned: "Worst boss to have is a 35-40 year old fit single dude" · Caption: "SINGLE DUDE. THE" |
| 14.86s | Same room, same framing, a fraction closer to the lens, mouth open mid-word. | Same pinned line · "LIFE, OKAY?" |
| 24.77s | Same framing, settled back slightly; the small dark picture visible at frame left. | Same pinned line · "HAVE TO ALSO." |
| 34.68s | Same framing, head turned very slightly, still straight to the lens. | Same pinned line · "TRIP, RIGHT?" |
| 44.59s | Same framing, shifted marginally to frame left so more of the leaning wooden frame shows on the right. | Same pinned line · "6, 7 PEOPLE." |
| 54.5s | Identical to the first frame — same tee, same wall, same leaning frame — still mid-sentence, no closing gesture, no reframe. | Same pinned line · "40, SINGLE, OKAY?" |

The caption cards are ALL CAPS with one word of each card boxed in red — the standard word-by-word highlight that tracks the speech. At contact-sheet resolution I can see the red box on the cards but cannot reliably read *which* word is boxed on every one, so treat "one word highlighted per card" as the pattern rather than a specific word list.

**What carries the value**

The pinned headline. One narrow, specific accusation held on screen for the entire runtime while the monologue itemises it. Nothing else on screen changes at any point — no product, no cutaway, no graphic, no second location — so the line and the argument under it are the whole payload. That also means the line has to be the strongest sentence in the piece; if it does not land in the first second, nothing later in the video can rescue it.

**Shoot it**

- **Camera:** one phone, front camera, arm's length or propped at seated eye level. Chest-up. Set it once and do not touch it — same distance, same angle, first frame to last. No cutaways, no second angle, no b-roll.
- **Light:** soft and flat from the front, daylight-looking. Nothing dramatic; his face is evenly lit with no hard shadow and no visible lamp.
- **Room:** a plain domestic wall with exactly one large object behind for depth — here a big wooden frame or mirror leaning against the wall, plus one small picture. Not styled, not empty. No product on the shelf, nothing to read behind him.
- **Wardrobe:** a plain solid-colour crew-neck t-shirt. No logo, no jewellery on show, no prop, nothing in his hands at any point.
- **Performance:** one unbroken rant delivered straight to the lens. He opens already mid-sentence — there is no greeting and no intro beat in any frame — and the last frame is still mid-sentence, so do not write a sign-off.
- **Post:** burn the headline into a white box in the top third and never change it. Burn ALL-CAPS speech captions underneath, one clause at a time, with the spoken word boxed in red.
- **This needs a performer.** The whole minute is one person being funny and specific on camera; there is no product footage or demo to hide behind.

Not visible in the frames, and not invented here: whether the take is genuinely unbroken or cut within the same setup (the framing shifts slightly between beats, which could be either him moving or hidden cuts); whether the phone is handheld or mounted; what is said between the six sampled caption cards; and anything below chest height, which is never in shot.

**Or generate it**

```
vertical 9:16, {SUBJECT} chest-up at arm's length from a fixed front camera in a plain domestic room, plain solid-colour crew-neck t-shirt, no props and nothing in their hands, an off-white wall behind with one large wooden frame or mirror leaning against it at frame left and a small dark picture on the wall, soft flat frontal daylight, phone front-camera look, slight grain, no retouching, no on-screen text — {PRODUCT} never appears in frame in this format; it exists only in the pinned headline
```

*Motion:* camera fixed at the same distance and angle for the whole runtime, no zoom and no reframe — only the speaker's head, mouth and shoulders move as they talk to the lens. Generate every beat from the same seed so the room and the framing are identical.

*Text overlay:*

- Pinned, top third, white box, black text, unchanged from first frame to last: `Worst {ROLE} to have is a {NARROW SPECIFIC IDENTITY}`
- Underneath, changing every beat: `{SPOKEN CLAUSE IN ALL CAPS}` with one word of each card boxed in red.

**Reference:** https://www.instagram.com/p/DUcCjGoDY6h/
