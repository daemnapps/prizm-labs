# Dropped hook, fixed monologue — rebuild sheet

A 69-second selfie monologue: a guy in a hoodie points at his own hairline under a "Day 30" line, shows the bottle and his scalp in close-up, then spends the whole back half talking to camera with the product in his hand. 213,829 views, 566 likes, by officialbodywise.

**Why it works**

The day stamp turns a pitch into a trial report — the viewer arrives as an auditor checking a result rather than an audience being sold to, and the line is dropped once it has done that job so nothing competes with the face for the rest of the runtime. The evidence is the speaker's own head shown in macro with the hair pushed back, which is the one proof nobody can accuse of being staged for a brand, because the before-state was volunteered.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 5.52s | Arm's-length selfie, head and shoulders, grey hoodie, home room with a pendant light behind. Mid-speech, hand raised into frame pointing back at his own hairline. | Day 30 hair growth journey |
| 16.57s | Insert: a hand holds the white-and-blue roll-on up to the lens, label readable. Shot into a mirror — a hooded figure with a phone in the reflection. A different, more cluttered room. | Day 30 hair growth journey |
| 27.62s | Extreme close-up of his own brow, temple and hairline, fingers pushing the hair up and back to expose it. Skin unretouched. | Day 30 hair growth journey |
| 38.67s | Back to the opening framing, same room, same distance. Still talking; the bottle now raised beside his face, roller ball to camera. | — |
| 49.72s | Identical framing held. Bottle still up, pendant light in the same spot behind him. | — |
| 60.77s | Identical framing to the end, bottle at cheek height, label to camera. The hook line never returns. | — |

**What carries the value**

His own head under a day stamp. He points at the hairline, then shows it in macro with the hair pushed back — his scalp is the evidence, and the product held beside his face is the named cause.

Say plainly what the frames do not show:
- **No before-state.** There is one macro of the current hairline under a "Day 30" label. No Day 1 frame, no split, no comparison anywhere in the sample. The stamp asserts the change; the picture does not prove it.
- **No application.** The product is never shown going on. It is held up twice and that is all.
- **No audio and no subtitles.** He is clearly speaking in four of the six beats, but there is no sound here and no burned-in speech captions at any beat, so what he actually says is unknown. Do not assume a script.
- **Beat 2's room is unidentifiable** from a single still — it is a mirror shot in a visibly different, more cluttered space than the monologue room.

**Shoot it**

- **Camera:** one phone, front camera, held at arm's length. Head and shoulders. Set that distance and angle once and return to it exactly — the back half is the same frame three times over, and its sameness is what makes the piece read as one continuous take.
- **Inserts:** two, both shot on the same phone. One product shot — bottle up close, label sharp and readable, into a mirror or against any real surface. One macro of the treated area, hair physically pushed back by the subject's own fingers, no retouching, no filter, no flattering angle. The macro must be a real result on a real body; if there is no result, this format has nothing to run on.
- **Light:** ordinary indoor light on the face. The source video is lit by whatever the room has — a ceiling fixture visible behind him. Do not add a ring light; the flatness is part of why it reads as a person rather than an ad.
- **Wardrobe:** plain, unbranded, one garment, no change across beats. A grey hoodie in the original. The wardrobe must not draw attention or imply a shoot day.
- **Room:** one real domestic room for every monologue beat, unchanged. Lived-in, not styled.
- **Text:** one line, small, low centre, same pixel position every time it appears. Runs the first third, then goes and does not come back.
- **Needs a person.** This one cannot be made without talent: it requires someone willing to put their own body on camera as the evidence and talk to the lens for a minute.

**Or generate it**

The anchor is the monologue frame — the beat that occupies most of the runtime. Generate that. Do not generate the macro evidence beat; a rendered scalp is a fabricated result, and that beat is the only thing doing the persuading.

```
vertical 9:16 phone front-camera photograph, {SUBJECT} in a plain grey hoodie,
arm's-length selfie framing with head and shoulders filling the frame, talking
directly to the lens, holding {PRODUCT} raised beside their own face with the
label toward the camera, seated in a real lived-in home room with a dark ceiling
and a multi-bulb pendant light behind them, soft mixed indoor light on the face,
slight sensor grain, no retouching, no on-screen text
```

**Motion:** camera fixed at arm's length for the whole beat — no zoom, no reframe, only the small unsteadiness of a hand-held phone; the speaker talks and raises {PRODUCT} into frame, and the identical framing is regenerated for every monologue beat (same seed) so only the hand and the face change.

**Text overlay:** `Day {N} {GOAL} journey` — one small white sans-serif line, low centre, identical position on every beat it appears, held for roughly the first third of the runtime and then dropped for good. Nothing replaces it and it never returns.

**Reference:** https://www.instagram.com/p/DVwbeZ9CDLf/
