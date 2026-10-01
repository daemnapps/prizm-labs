# Running caption over borrowed cutaways — rebuild sheet

A 44s teeth video built almost entirely from other people's clips: four unrelated strangers play inside one unmoving desk plate while a one-word-per-beat narration runs underneath, and the product only appears in the last beat. 1,556,660 views · 20,609 likes · @nexova_beauty.

## Why it works

The caption is only ever one word wide, so it is always mid-sentence and there is never a clean place to leave — the viewer stays to finish a sentence rather than to see a product. The plate never moves while four visibly different people, rooms and cameras pass through the band inside it, so unrelated strangers read as one accumulating argument instead of a scrapbook, and the product arrives at the end as the answer to a claim already accepted.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 3.54s | Tight close-up of a young man with dark curly hair, one finger pointing up — only his face and hand in frame. A white message-screenshot card sits over the top half. No plate yet. | "Marlon Finally Reveals What He Uses…" / "1:19 PM" / "Break my fuckin back" / "girls" |
| 10.62s | The plate is established — dark panelled wall along the top, laptop keyboard filling the bottom third, and a full-width band between them carrying a clip of a young man in a white tee standing side-on in a white bathroom doorway. | "everything" |
| 17.69s | Plate identical. Inside the band: a blonde woman in a cap cheek-to-cheek with a man outdoors on grass, both laughing wide with teeth showing. | none visible |
| 24.77s | Plate identical. Inside the band: two people on the floor of a cluttered bedroom, one in a green cap gesturing at the other. | "yeah" |
| 31.85s | Plate identical. Inside the band: a young man in a dark tee in a messy room, holding a fan of white sachets up to his own camera. | none visible |
| 38.92s | Plate gone. A hand holds a whitening-strips box (GuruNanda, 32 strips, extra value pack, with natural coconut oil) over a real bathroom sink, toiletries behind. A large red arrow points straight down. | "out" |

**What the frames don't show:** whether the camera moves inside any beat — stills can't tell you. What they do show is that the plate is in exactly the same position at 10.62s, 17.69s, 24.77s and 31.85s, so the plate itself is fixed; the clips inside it each carry their own camera. Two beats (17.69s and 31.85s) have no caption in the sampled frame — the narration is presumably still running between words, but that is not visible here. I also can't tell from stills whether the middle band is a real laptop screen being filmed or a composited mock-up; structurally it makes no difference.

## What carries the value

The never-finished one-word narration. It's always mid-sentence, and it's the only thing binding four unrelated strangers into a single claim — the parade of other people's faces does the proving, and the product is only produced at the very end.

## Shoot it

You barely shoot this one. Only the last beat is yours.

- **Record the voiceover first.** One continuous sentence-y monologue, then caption it one word at a time, same low-centre position, same size, all runtime. It must never land as a completed sentence on a beat.
- **Build one plate and never touch it.** A dark textured wall along the top, a laptop keyboard filling the bottom third, a full-width band between them. Shoot it once, lock it, and reuse the identical frame for every clip. Nothing in the plate is allowed to move or reframe between beats.
- **The clips go inside the band.** Four of them, each a visibly different person in a visibly different room with a visibly different camera. Do not colour-match them to each other — the mismatch is what makes them read as found rather than staged.
- **The hook beat breaks the plate.** Open full-frame on one face, with a white message-screenshot card composited over the top half: a headline, a timestamp, a chat bubble.
- **The last beat is yours.** Phone, handheld, your own bathroom, plain bathroom light, product held up over the sink with the shelf of real toiletries behind it. Unstyled — the mess is the point. Red arrow added in post.
- **Wardrobe:** nothing to direct. You are not casting anyone; every person on screen except the hand at the end came from someone else's footage.

## Or generate it

```
vertical 9:16 phone-camera photograph, a fixed desk plate: a dark textured
panelled wall filling the top strip, a laptop keyboard filling the bottom third
of the frame seen from slightly above, and between them a full-width band
carrying a clip of {SUBJECT} in a real domestic room — that band lit by its own
source and visibly a different camera from the plate, plain even room light on
the keyboard, slight grain, no retouching, no on-screen text

· closing beat: a bare hand holding {PRODUCT} up over a real bathroom sink,
toiletries on a shelf behind, plain bathroom light, phone-camera look, no
on-screen text
```

**Motion:** the plate is absolutely static across every beat — generate it from the same seed each time so the wall, the keyboard and the band edges never shift — and only the clip inside the band swaps, each carrying whatever camera it was shot with.

**Text overlay:** one word of the spoken narration per beat, in the identical low-centre position for the whole runtime, never completing a sentence and never pinned — `{word}` → `{word}` → `{word}` → `{word}`. The opening beat additionally carries a white message-screenshot card over the top half: `{NAME} Finally Reveals What He Uses…` with a timestamp and a grey chat bubble reading `{quoted line}`.

**Reference:** https://www.instagram.com/p/DTYHAsWiAI4/
