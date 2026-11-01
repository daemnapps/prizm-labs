# The visual lexicon

One controlled vocabulary for the way a picture is described, used at both
ends of every chain: **the teardown records in it, the generator builds from
it.** Without it, "casual selfie vibe" gets translated into camera terms fresh
in someone's head on every single run, and the translation is different every
time.

This is the visual twin of the customer language bank. Same discipline: a
closed list of terms, each one a thing a camera can actually do, grown from
real runs rather than invented up front.

**Two rules govern it.**

**Record the term, not the impression.** A teardown that writes "moody" has
recorded a reaction. A teardown that writes `low-key chiaroscuro` has recorded
a lighting setup a generator can execute. If what you see is not on a list
below, write the plainest camera-visible description you can and flag it — the
list grows from real gaps, never from guesses.

**Every slot gets filled or explicitly marked empty.** Whatever is left unsaid
is filled in by the training-data average, and the average is what everyone
else's ads look like. `[NONE: grain]` is a decision. Silence is not.

---

## 1 · Shot size

How much of the subject the frame holds.

| Term | What it means |
|---|---|
| `ECU` | Extreme close-up — part of a face, a hand, a texture. No context. |
| `CU` | Close-up — head and a little shoulder. |
| `MCU` | Medium close-up — head to mid-chest. The talking-head default. |
| `MS` | Medium shot — head to waist. |
| `MWS` | Medium-wide — head to knee, room readable behind. |
| `WS` | Wide — whole body, the space is the point. |
| `EWS` | Extreme wide — the figure is small in a large space. |
| `insert` | A prop or detail alone in frame, no person. |

## 2 · Camera angle and height

Two separate facts. Height is where the lens is; angle is where it points.

**Height** — `floor` · `hip` · `chest` · `eye` · `above-eye` · `overhead`

**Angle** — `level` · `low-angle` (looking up — power, scale) ·
`high-angle` (looking down — vulnerability, survey) · `overhead-flat` ·
`dutch` (tilted horizon — use rarely)

Say height as a fraction of the subject where it matters:
"chest height, roughly 45% of her standing height."

**Where the camera stands in the room is a third fact, and it is the one that
decides the picture.** Height and angle say how the lens is held; they say
nothing about which corner it is held in. Name the position against the
furniture and the direction it shoots: "from the corner at the foot of the bed,
shooting lengthwise along the room" is a different photograph from "beside the
bed, shooting across it" at the identical height and angle. Measured cause,
2026-08-26: a record carrying shot size, height and angle but no camera position
rebuilt with the camera on the wrong side of the bed, twice.

## 3 · Subject orientation to camera

**The single fact a rebuild gets wrong most often.** Named in these words, and
face visibility stated separately and always.

| Term | What it means |
|---|---|
| `frontal` | Facing camera square on. |
| `three-quarter-front` | Turned partly away, both eyes still visible. |
| `profile` | Side on, one eye visible. |
| `three-quarter-back` | Turned mostly away, a sliver of cheek at most. |
| `back` | Back to camera, no face. |

Then, always, one of: `face fully visible` · `face partly visible` ·
`face not visible`. **`face partly visible` is never written alone** — say how
much, in the same breath: "a sliver of cheek only", "the far eye and nothing
else", "the jaw, no eyes". Measured cause, 2026-08-26: a subject whose face was
a hard edge of profile was recorded as `face partly visible`, the plate prompt
carried that phrase unqualified, and the rebuild rendered a full three-quarter
face. Between "partly" and a fraction, a generator takes the generous reading
every time.

Measured cause, 2026-08-19: an ad whose subject was `three-quarter-back,
face not visible` was rebuilt frontal with the face fully visible, and the two
pictures were unmistakably different ads. Recorded in these terms, it survives.

**Head direction and gaze are separate facts.** A head can point one way while
the eyes go another, and it reads completely differently.

## 4 · Lens feel

Not a focal length claim — the way the space reads.

`wide-close` (24–35mm, near — space stretches, edges bend) ·
`natural` (40–55mm — space reads as the eye sees it) ·
`portrait-compressed` (85mm — background pulls forward, subject separates) ·
`tele-compressed` (135mm+ — planes stack flat) ·
`macro` (texture fills the frame)

Depth of field as its own term: `deep` · `moderate` · `shallow` ·
`razor` (a single plane sharp).

## 5 · Light

**The highest-leverage slot.** Three facts every time: source, direction,
quality.

**Setups** — `hard-single-source` · `soft-key-large-source` ·
`overcast-softbox` (flat, no visible shadow edge) ·
`golden-hour-backlight` · `rembrandt` (key at 45°, triangle on the far cheek) ·
`rim-against-dark` · `practical-only` (lamps, screens, neon in shot doing the
lighting) · `on-camera-flash` (hard shadow behind subject — the UGC/anti-ad
look) · `window-side-light` · `caustic-dappled`

**Direction** — `front` · `side-left` · `side-right` · `back` · `top` ·
`under`

**Quality** — `hard` (sharp shadow edges) · `soft` (gradual) ·
`mixed` (say which source does which)

Name the practicals separately and place them: "one warm table lamp,
midground, left of subject."

## 6 · Colour and grade

`low-key-chiaroscuro` (deep shadow, small bright area — luxury, drama) ·
`high-key` (bright, shadowless — clinical, clean) ·
`warm-natural` · `cool-natural` ·
`teal-orange` (blockbuster; saturated and very common) ·
`bleach-bypass` (desaturated, crushed, gritty) ·
`monochrome-brand` (one hue family throughout — recall) ·
`kodak-portra` (warm skin, gentle contrast) ·
`kodak-gold` (warm, nostalgic, slightly green shadows) ·
`cinestill-night` (halated highlights, tungsten glow)

State the black point when it matters: `crushed blacks` · `lifted blacks`.

## 7 · Texture and stock

The authenticity markers. **Leave these empty and the picture looks generated**
even when everything else is right.

`clean-digital` (no grain — the AI default, and it reads as the default) ·
`fine-grain-35mm` · `heavy-grain-pushed` ·
`point-and-shoot-flash` (1990s compact — soft corners, hard flash, slight
overexposure) · `phone-front-camera` (slight distortion, digital noise in
shadow) · `medium-format-clean` (very high detail, shallow falloff) ·
`vhs-soft` · `print-halftone`

Plus the physical tells where present: `fingerprints on glass` ·
`dust in the light beam` · `condensation` · `visible skin texture and pores` ·
`fabric pilling` · `surface scuffs`.

## 8 · Composition

`dead-centre-symmetry` (iconic, formal) ·
`thirds-subject-left` / `thirds-subject-right` (leaves room for copy) ·
`extreme-negative-space` (premium) ·
`tight-crop-edges-cut` (urgency, immediacy) ·
`leading-lines-to-subject` ·
`foreground-framing` (shooting past an object in the near plane)

Say what the room's own lines do and which edge they enter and leave by. Say
what sits at each of the four frame edges — an edge inventory is what stops a
rebuild silently re-cropping the scene.

**Percentages are not composition terms.** A percentage band is an instruction
for the compositor that sets the type. An image model dilutes its attention
across them and renders the picture from the words instead. Record geometry in
percentages for the type layer; describe the picture in the terms above.

## 8b · What language wins, and what it does not

Measured on 2026-08-26 across four rebuilds of the same photograph, words only,
Nano Banana Pro.

| Slot | From language alone |
|---|---|
| Subject, wardrobe, props | **reliable** |
| Action | **reliable** |
| Environment and its furniture | **reliable** |
| Light — setup, direction, practicals | **reliable** |
| Grade and black point | **reliable** |
| Texture and stock | **reliable** |
| Face visibility | **reliable only in the strong form** — see below |
| **Camera position in the room** | **not reliable** — attach the reference |

**Face visibility** is won by contradicting the default three times over: say
what the camera sees of the body, name each feature that is not visible
individually, and repeat it in the negatives. The lexicon term alone
(`three-quarter-back, face partly visible`) rendered a full face.

**Camera position** was wrong in every run, including when stated plainly and
repeated in the negatives. Shot size, height, angle, lens and depth of field all
land; *which corner of the room the lens is in* does not. Generate the plate with
the layout reference attached and let the words carry everything else.

## 9 · Style anchor

One phrase naming the kind of picture it is:
`editorial product photography` · `35mm documentary still` ·
`fashion editorial` · `architectural photography` ·
`1990s point-and-shoot snapshot` · `catalogue studio still` ·
`phone snapshot, unstyled` · `still from a film`

---

## The order it gets written in

A generator reads a shot list, not a description. Written in this order, in
the terms above:

**subject → action → environment → composition → camera → light → grade →
style → texture**

The weird idea lives in subject, action and environment. **The credibility
lives in everything after.** A surreal concept in rigorous photographic
language reads as "how did they shoot that." The same concept in vague
language reads as AI slop.

---

## Growing this file

A term enters when a real run needed it and it was not here. Add it to the
right list with a one-line definition a camera could act on, and — where it
came from a failure — the date and the failure, the way the entries above do.
Never add a term speculatively; an unused term is a term nobody agrees on.
