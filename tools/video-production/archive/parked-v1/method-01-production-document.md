# The production document — write this before you generate anything

One document per piece, written first, holding every fact it needs.
Its shape is the same whatever the format; a format profile
(`formats/`) says which parts of it a piece of that shape uses.
Nothing gets generated from a beat list: a beat list leaves a thousand
decisions to the model, and the model makes a different one every scene.
This document makes them all once, and every scene prompt reads from it.

Fill the slots from the brand's own folder. Characters are named by ROLE
here — `{LEAD}`, `{FOIL}`, `{WITNESS}`, `{AUTHORITY}` — so the structure
survives a recast; your production replaces them with its cast's names.

---

## The header

```
{brand} — "{concept name}"
PRODUCTION DOCUMENT · format: {format}

Delivery: 9:16 vertical · <placement> · 1080p · ~<n>s · <k> scenes
Grade:    <the look, in one sentence — this becomes section 4, verbatim>
Audience: {avatar} · Tone: <the register, and where it resolves>
Language: <language> · <profanity rule> · No dead air
```

The grade sentence written here is the sentence pasted into every scene
prompt for the rest of the production. Choose it with that in mind.

## The story, or the through-line

One paragraph. What happens, who is wrong about what, what turns, and how
it lands on the offer. Written as prose, not beats — you are checking that
the story *works* before it costs anything to find out.

Underneath it, in capitals, **any claim boundary the story flirts with**.
If the story's emotional truth sits near a claim the brand cannot legally
or honestly make, write the line that must never be crossed here, in the
loudest place in the document, and check it again at the offer.

> Example shape: THE RECIPE COMES FROM HOME. THE OFFER NEVER CLAIMS THE
> PRODUCT IS MADE THERE.

## Cast — identity locks, zero tolerance

| Role | Locked appearance | Never |
|---|---|---|
| `{LEAD}` | age, build, skin, hair, distinguishing marks · the one outfit | the outfits their reference photo might import |
| `{FOIL}` | … | … |
| `{WITNESS}` | … | must never read as the same person as `{LEAD}` |
| `{AUTHORITY}` | … | any accessory that keeps sneaking in |

Then **voice locks** in one line: each character's register, and the
instruction that the voices never blur into each other.

The appearance column becomes the wardrobe block in section 6 of every
prompt. The "never" column is not padding — it is the part that works.

## The product — always legible

- **Full product name** — packaging, colour, cap, label text, exactly as
  it reads on the real thing. Never redrawn, never approximated.
- **Its physical character** — if what comes out of it appears on camera,
  name its colour and consistency here and nowhere else.
- **The offer** — guarantee, discount, scarcity, call to action, and the
  claim boundary repeated.

## The set — one continuous space

A drawn plan, in plain text, of the one room the film happens in:

```
  BACK WALL
  [ <anchor 1 — the thing the camera orients on> ]
  [ <anchor 2 — where the product lives when nobody holds it> ]
  LEFT: <role> zone · CENTER: <role> · RIGHT: <role>
  <edge feature>
  <the open floor where confrontation happens>
  <entrance>, backlit
```

Then name the **zones** (three or four, no more) and the **anchors**. Every
scene prompt uses this vocabulary and no other, which is why the room never
rebuilds itself between scenes.

## The continuity matrix

### Entrances
For every scene: does the entrance open, and whose entrance is it? A
character enters **once in a film, ever.** Write that here and it stops
being negotiable.

### Position ledger
The first-frame position of every character, in every scene:

| | Scene 1 | Scene 2 | Scene 3 | … |
|---|---|---|---|---|
| `{LEAD}` | THRESHOLD | CORRIDOR, advancing | CORRIDOR, stopped | … |
| `{FOIL}` | ANCHOR | ANCHOR | ANCHOR | … |
| … | | | | |

### Object, camera and atmosphere ledgers
- **Object** — who holds the product in each scene, its state (capped,
  open, set down), and the single scene where it changes hands.
- **Camera** — the axis that is never crossed, and the left-to-right
  screen order per scene.
- **Atmosphere** — how the air, light or mess changes across the film, as
  numbers, so the arc is scripted: `80% → 70% → 40% → 10%`.

## Per-scene mechanics

One paragraph per scene. Duration, what happens physically, the dialogue in
full with speaker names, and the mechanical rules unique to that scene —
especially the exclusions:

> **SCENE n — <FUNCTION> (<n>s)** — <who is where at the first frame; what
> the entrance does>. Dialogue: "<line>" / "<line>" / "<line>". Mechanics:
> <the action chain, with each step separated — including the beats a
> model would otherwise glue together>. End: <the last frame>.

Write **alternate openings as their own scenes** (a mystery-first version of
scene 1, for instance). The edit picks between them later; generating both
costs one scene and buys a real choice.

## The anti-drift checklist

Close the document with a numbered list of every invariant, phrased as a
check. This list gets read before every batch ships:

1. Wardrobe locks verbatim — the photographs are face-identity only.
2. `{LEAD}` enters once, in scene n, and is never near the entrance again.
3. `{AUTHORITY}` enters once, in scene n, and never mouths another
   character's line.
4. Product label legible; its texture the right colour and consistency.
5. The scene-specific exclusions — who is *not* touched, what is *not* done.
6. The camera stays on its side of the axis; motivated moves only.
7. No morphing hands, no flicker, reflections stable.
8. The offer contains no claim the story's boundary forbids.

---

When this document is finished, the scene prompts are assembly, not
authorship — `03-scene-prompt.md` is the assembly instruction.
