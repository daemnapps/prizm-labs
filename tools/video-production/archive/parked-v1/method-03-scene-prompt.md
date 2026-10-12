# The scene prompt — eleven sections, six ledgers

Every scene in the piece is generated from one prompt with **eleven sections
in a fixed order**. Sections 1–8 are constants: identical, word for word,
in every scene of the piece. Section 9 is the scene's own script. Sections
10–11 close it. The six ledgers are pasted through so the model re-reads
the same facts on every generation.

Generation settings that hold for the whole film: vertical 9:16, 1080p,
4–15 seconds per scene, **audio generated in the same pass as the picture**,
and the cast's trained identities plus the reference plates attached to
every scene (`02-identities.md`).

---

## The reference set (attached to every scene, same order every time)

| Slot | What | Its only job |
|---|---|---|
| 1 | The set plate | The room: surfaces, anchors, light |
| 2… | One plate per character, in a fixed order | **Face identity ONLY — never wardrobe** |
| n−1 | The real product photograph | Label integrity |
| n | A texture plate, if the product has a look that must be right (the paste, the foam, the cream) | Colour and consistency |

**The hard rule, learned the expensive way:** the photographs carry FACES,
not clothes. Left alone, the model dresses a character in whatever the
reference photo happened to be wearing. Section 6 overrides wardrobe in
text on every single scene.

---

## The eleven sections

### 1 · Camera — sensor, lens, look
Fixes the image-making hardware so every scene reads as one camera.

```
Camera: <sensor>, <lens family> | <look: e.g. soft detail, warm skin, mild
highlight bloom, lifted blacks> | <focal length>, f/<stop>.
```

You may vary sensor and lens between scenes for texture. **Never vary the
grade language** — that lives in section 4 and is the piece's identity.

### 2 · Camera style — how it moves, and how it must not
The negations are load-bearing; write them as loudly as the positives.

```
Camera Style: <movement vocabulary>; <one or two positive manners>;
<negations: no jitter, no whip pans, no crossing the axis>.
```

### 3 · Lighting — one motivated scheme per group of scenes
Keeps the piece lit in the same room even as the story moves.

```
Lighting: <primary source> + <direction> + <what it does to the air,
the reflective surfaces, the practicals>.
```

Write one line per scene-group and let it evolve with the story (a set
that starts obscured and clears is one of the strongest visual arcs
available — but the evolution is scripted, never left to chance).

### 4 · Style and mood — the grade
**The single most repeated sentence in the production. Identical in every
scene, verbatim, no exceptions.** Choose it once in the director's cut.

```
Style & Mood: <the grade, in one specific sentence — era, skin tone,
contrast, bloom, micro-contrast>.
```

Then one short per-scene mood clause after it, which is the only part that
moves ("close and oppressive" → "tension at its peak" → "warm, settling").

### 5 · Performance and dialogue language
Sets the acting register, and the pace.

```
Performance: <pause before reactions, precise eyelines, alive eyes with
catchlights, visible breathing>.
Dialogue language: <language>. <profanity rule>.
```

Add a pacing clause per scene when a character must not rush — a slow,
deliberate delivery with a pause between sentences has to be *asked for*,
every time, or the model races.

### 6 · Wardrobe locks — pasted verbatim, every scene
This section exists because wardrobe drift is the most common and most
obvious break. Written as what each character wears **and an explicit
never-list** of what the reference photo might otherwise import.

```
Wardrobe locks (strictly consistent whole film; the photographs are
face-identity only, never wardrobe):
{LEAD}: <garment, colour, material> — never <the photo's clothes>, never
  <the neighbouring character's look>.
{FOIL}: <…> — never <…>.
{WITNESS}: <…> — must stay visually distinct from {LEAD}.
{AUTHORITY}: <…> — never <any accessory that keeps appearing>.
```

Two rules inside the rule: name the **specific** wrong garment you have
seen appear, and keep any two characters who share the frame visually
distinct from each other.

### 7 · Blocking — the iron rules for this scene
The section that stops impossible staging: a character entering twice, a
person teleporting across the room, someone appearing who is not in the
scene. State what **cannot** happen as flatly as what does.

```
Blocking — iron rules for this scene:
The door opens exactly ONCE in this scene [and it is {CHARACTER}'s only
  entrance in the piece].
{CHARACTER} is ALREADY inside in this scene; never re-enters, never
  approaches the door, is never shown outside.
Nobody enters or exits in this scene. The door stays closed.
<scene-specific exclusion: this scene is ONLY {CHARACTER} doing X; nobody
  applies anything to anyone else; nobody touches Y.>
```

### 8 · Scene setup — anchors, coordinates, zone logic
Fixes the geography with the same vocabulary every scene, and everyone's
position with **numbers**, because measurable positions stop invented
staging.

```
Scene: <the set in one sentence>; <anchor> at <position>; <second anchor>
at <edge>; <entrance> at <position>, backlit.
Camera at <distance> from <anchor>, <height>, <side> — never crossing the
axis.
Positions (percent of frame): {LEAD} x≈78% y≈38%; {FOIL} x≈52% y≈60%; …
Screen order locked: <left-to-right order for this scene>.
Each named character appears exactly once.
```

### 9 · Dynamic description — the shot-by-shot script
The piece inside the prompt: a strict chain of shots with hard cuts, the
first frame already loaded, one action per cut, and the dialogue with
acting cues in brackets.

```
<WS/MCU/CU> <focal length> <angle> — <what is in frame>; <action>;
<performance cue>.
Hard Cut to <next shot> …
{CHARACTER} [eyes locked, jaw tight, voice sharp]: 'the line'
```

Five rules make this section work:
- **The first frame is loaded** — the subjects are already in position; no
  empty establishing beat while the scene warms up.
- **One action per hard cut, in strict order** — the sequence is a chain
  and the model follows the chain.
- **The camera is on the speaker** — whoever talks is the one on screen,
  or another character will be shown mouthing the line.
- **Dialogue carries [performance] brackets** — the bracket is direction,
  and it lands.
- **Mechanics are spelled as separate beats** — "squeezes the paste onto
  her forearm → **sets the tube down on the counter** → rubs in small
  circles". Write the put-down as its own beat or the model glues the
  actions together and the object stays welded to the hand.

### 10 · Audio
The sound generated in the same pass as the picture.

```
Audio: <room tone>; <dialogue>; <SFX beats in order>; <music per the
emotion map>.
Every beat carries spoken dialogue or deliberate sound; no silent stretches.
```

### 11 · Positive locks and negations — the closing block
Re-states the invariants and bans artefacts. The repetition is the point.

```
Positive locks: <wardrobe, screen order, product label legible, texture
colour, the grade sentence, the same set>.
No subtitles. No text overlays. No captions. No title cards. No watermarks.
```

---

## The six ledgers

Written **once** in the director's cut, pasted into every scene that needs
them. They are the anti-drift backbone.

1. **Entrance ledger** — for every scene, whether the door opens, and whose
   entrance it is. An entrance happens once in a film, ever.
2. **Position ledger** — the first-frame position of every character, per
   scene, as percentages.
3. **Wardrobe ledger** — section 6, verbatim, every scene.
4. **Object ledger** — for the product and any hand-prop: who is holding
   it, what state it is in (capped, open, set down), and the single scene
   where it changes hands. Plus the label-legibility requirement.
5. **Camera ledger** — the axis that is never crossed, and the screen
   order per scene.
6. **Atmosphere ledger** — how the air, the fog, the light or the mess
   changes across the piece, as numbers ("70% → 40% → 10%"), so the
   progression is scripted rather than random.

---

## When something drifts — grades of fix

| Symptom | The fix |
|---|---|
| Wardrobe changed between scenes | Strengthen section 6: name the exact wrong garment in the never-list; re-attach the face plates |
| A character entered twice, or teleported | Rewrite section 7 with the entrance ledger, and section 8 with coordinates |
| Speech is rushed | Raise the scene duration and add an explicit pacing clause to section 5 |
| Morphing hands, flicker, general slop | Simplify section 9 — fewer limbs in frame, one action per cut — and keep section 11's negations |
| The product's label is garbled | The product must be a photo reference, not a description, and legibility demanded verbatim in sections 8 and 9. If it still garbles at hero size, composite the real packshot rather than generating the label |
| Two characters look alike | Section 6: make them visually distinct by explicit contrast, not by hoping |

---

## Scaling this to N pieces

1. **Write the director's cut first.** Never generate from a beat list.
2. **Lock the reference set once** — one identity per character, one set
   plate, one product plate, one texture plate. Register them; reuse the
   same ones everywhere, forever.
3. **Assemble each prompt from this template** — sections 1–8 copied
   verbatim, section 9 written for the scene.
4. **Keep the negations as loud as the directions.**
5. **Generate the whole film in one batch**, same model, same run — voice
   and look stay consistent within a batch and drift between them. Never
   mix old and new renders in one film.
6. **QC the batch before it goes anywhere**: wardrobe per character,
   entrance and blocking logic, the speaker's face on the speaker's line,
   label legibility, set stability. Regenerate only the failing scenes,
   from the same template.
