Assemble the generation prompt for every scene in this piece — one
complete, ready-to-send prompt each, built from the eleven sections in
fixed order.

**Every example in this prompt is illustrative only.** Sensors, garments,
rooms, positions — none of them describe this piece. Everything comes from
the production document below.

You are not writing new creative. Sections 1 through 8 already exist in
the production document and get copied **verbatim** into every scene.
Section 9 is the only place where this scene differs from the others. Your
job is assembly with exactness, and exactness is the whole value: the
model cannot remember, it can only read, so the same words in every scene
are what make the piece consistent.

---

THE PRODUCTION DOCUMENT

{production_document}

THE LEDGERS

{ledgers}

THE FORMAT PROFILE

{format_profile}

---

For **each scene** in the production document, output a block in exactly
this shape. Repeat it for every scene, including any marked ALT.

    ═══ SCENE <n> · <function> · <duration>s ═══

    Camera: <section 1, verbatim from the production document>

    Camera Style: <section 2, verbatim>

    Lighting: <section 3 for this scene's group, verbatim>

    Style & Mood: <section 4 — the grade sentence, verbatim, identical in
    every scene> <then this scene's one-clause mood>

    Performance: <section 5, verbatim> <then this scene's pacing clause,
    if the mechanics call for one>
    Dialogue language: <language>. <profanity rule>.

    Wardrobe locks (strictly consistent whole piece; the photographs are
    face-identity only, never wardrobe):
    <the wardrobe ledger, verbatim, every role — including the never-lists>

    Blocking — iron rules for this scene:
    <the entrance ledger's line for this scene>
    <who is already present and never approaches the entrance>
    <this scene's exclusions: who is not touched, what is not done>

    Scene: <the place, in the production document's own anchor vocabulary>
    Camera at <distance> from <anchor>, <height>, <side> — never crossing
    the axis.
    Positions (percent of frame): <this scene's row from the position
    ledger>
    Screen order locked: <this scene's order from the camera ledger>
    Each named character appears exactly once.

    <the shot-by-shot script — see the rules below>

    Audio: <room tone>; <dialogue>; <sound beats in order>; <music>.
    Every beat carries spoken dialogue or deliberate sound; no silent
    stretches.

    Positive locks: <wardrobe, screen order, product label legible,
    texture colour, the grade, the same place>.
    No subtitles. No text overlays. No captions. No title cards. No
    watermarks.

    ── attach ──
    identities: <the trained identities this scene needs, by name>
    plates: <the reference images, in fixed order — place, then each face
    in the same order every scene, then the product, then any texture>
    duration: <n>s · 9:16 · 1080p · audio generated in the same pass

---

## Writing section 9 — the shot-by-shot script

This is the only authored part. Turn the scene's mechanics from the
production document into a strict chain of shots:

    <WS/MCU/CU> <focal length> <angle> — <what is in frame>; <action>;
    <performance cue>.
    Hard Cut to <next shot> …
    <ROLE> [<performance bracket>]: 'the line'

Five rules, all of them load-bearing:

1. **The first frame is loaded.** The subjects are already in position in
   shot one. Never open on an empty room that someone then walks into,
   unless an entrance is exactly what the ledger says happens here.
2. **One action per hard cut, in strict order.** The sequence is a chain
   and the model follows the chain. Two actions in one shot become one
   blurred action.
3. **The camera is on the speaker.** Whoever talks is who is on screen for
   that line, or another character will be shown mouthing it.
4. **Dialogue carries a performance bracket** — `[eyes locked, jaw tight,
   voice sharp]`. The bracket is direction and it lands.
5. **Mechanics are separate beats.** "Squeezes the paste onto her forearm
   → **sets the container down on the counter** → rubs in small circles."
   Write the put-down as its own beat or the model welds the object to the
   hand for the rest of the scene.

## What you must not do

- **Never paraphrase sections 1–8.** If the production document says a
  sentence, that sentence appears in every scene, character for character.
  A synonym is a drift.
- **Never invent a fact the production document does not contain.** If a
  scene needs something undecided — a position, a garment, a line — stop
  and write `⚠ UNDECIDED: <what>` in place of that section rather than
  choosing for the production. An invented fact becomes an inconsistency
  the QC gate will catch expensively later.
- **Never omit a section** because it seems irrelevant to this scene. A
  format may make a section near-boilerplate; boilerplate still gets
  written, because its absence is what lets the model improvise there.

---

Output the scene blocks and nothing else: no preamble, no commentary
between them, no summary at the end.
