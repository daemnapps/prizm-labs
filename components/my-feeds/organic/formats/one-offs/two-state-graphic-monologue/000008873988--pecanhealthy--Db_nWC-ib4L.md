# Two-state graphic monologue — rebuild sheet

A man stands in his own kitchen and talks to camera for 49 seconds; for the first third, one anatomical cross-section sits at his chest and quietly changes from healthy to ruined. 8,873,988 views · 383,956 likes · @pecanhealthy.

**Why it works**
The whole argument is made in the first twelve seconds by one image shown twice — same shape, same position on screen, visibly eaten through the second time — so the viewer reaches the conclusion before anyone has explained anything. The rest of the runtime is a person confirming a picture you already believe, which is why a locked, unstyled talking head holds for another 35 seconds without a single cut or camera move.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 3.94s | Locked medium shot, waist-up, presenter centred in a home kitchen — plates along the wall soffit, pale cabinets, mug and knife block on the counter, recessed downlights. A large oval cross-section (dense red muscle, thin pale rim) sits at his chest, overlapping his torso. | who does not |
| 11.82s | Identical frame, identical room. The cross-section has changed state: the red is broken into islands with heavy pale marbling through it. Same size, same screen position — the swap is the only change in frame. | lift weights |
| 19.7s | Same locked frame, graphic gone. Talking to camera, both hands open, palms up. | into your 70 |
| 27.58s | Same locked frame. Talking, one hand pointing, the other a loose fist — a step-by-step gesture. | go up the stairs |
| 35.46s | Same locked frame. Talking, hands closed together at waist height. | enough age |
| 43.34s | Same locked frame. Talking to camera, hands loosely clasped, closing out. | eat more protein |

What the frames do not show, and I have not filled in:
- Whether he is physically holding a printed board or the graphic is composited on top of the shot. It reads as an overlay sitting over his torso, but six stills cannot settle it.
- Whether there are cuts between the sampled beats. The framing, room and light are identical in all six, so if there are cuts they are invisible ones.
- What he actually says. The captions are speech captions caught mid-phrase ("into your 70" is clearly a chunk of a longer line), so the six strings above are fragments, not the script.
- The bottom fifth of every frame is a plain light surface with soft shadows — a counter edge in the foreground, or padding under the video. Can't tell which from stills.
- Whether the graphic changes state on a hard swap or animates between the two. Only the two end states are visible.

**What carries the value**
The two states of the one graphic. The second image is the first image ruined — identical shape, identical position, visibly hollowed out — so the loss registers as a fact rather than a claim. The presenter is not carrying this; he is the voice attached to it. If the two states don't read at a glance, side by side in time, the video has nothing.

**Shoot it**
- **Camera:** phone on a tripod or propped on a shelf, vertical, chest height, three or four feet back, waist-up. It never moves and never cuts — set it once and let the whole take run.
- **Room:** a real kitchen or living space with depth behind the subject. Lived-in, not styled — the clutter is what makes it read as a person rather than an ad.
- **Light:** flat, even, whatever the room already has (ceiling lights plus daylight). No fill, no key, no colour. Faces should look ordinary.
- **Wardrobe:** plain solid short-sleeve polo or tee, jeans, belt. Nothing branded, nothing patterned — anything busy competes with the graphic.
- **The graphic:** one asset, two states, same shape and same size, held at chest height and filling about a third of the frame width. State two must be state one degraded, not a different picture. Everything hangs on that.
- **Talent:** you need someone who can hold a 50-second unbroken take to camera and sound like they know the subject. No acting, no script performance — but this is the one part you cannot skip or fake, which is why it's marked not replicable without talent.
- **Text:** burn in rolling speech captions from the audio, two to four words a card, mid-frame, white bold with a dark outline. Nothing pinned.

**Or generate it**

```
vertical 9:16 photograph, {SUBJECT} standing waist-up and centred in a real lived-in home kitchen, plain heather-blue short-sleeve polo, jeans, brown leather belt, no styling; behind them pale cabinets, a run of decorative plates along the wall soffit, a counter with a white mug and a knife block, a framed picture, recessed ceiling downlights; camera at chest height a few feet back, flat even indoor light, phone-camera look, slight softness, no retouching; {PRODUCT} presented large and flat at the subject's chest, filling roughly a third of the frame width, overlapping the torso, sharp and evenly lit against the soft room; no on-screen text
```

**Motion:** camera absolutely still — tripod or propped phone, identical framing for the entire runtime; only the subject's hands move and {PRODUCT} swaps to its second state in place, so generate both states from the same seed frame.

**Text overlay:** rolling speech captions, two-to-four words per card, centred at mid-frame height, white bold sans with a dark outline, changing with the delivery — `"{spoken words}"`. Never pinned, no line held across beats.

**Reference:** https://www.instagram.com/p/Db_nWC-ib4L/
