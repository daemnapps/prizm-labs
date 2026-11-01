# Stage 3 · Scene prompts — v4

*v4 (2026-09-18): three new slots in every scene block after `Lines
covered:` — `Section:`, `Emotion:` and `Outcome:` — and two new rules
under "Writing section 9": the scene lands, the copy is the spine (the
scene-authoring and intimate-copy rulings, 09-17/09-18). No new
variables; the session pastes the same three as v3.*

*v3 (2026-09-17): one new slot after `Lines covered:` — `Result budget:` —
and one new line in the `Post` slot's guidance, both from the course
write-up (the owner, 09-14), §2 and §3. No new variables; the session pastes
the same three as v2.*

*v2 (2026-09-17): three new slots in every scene block after `Positive locks:` — `Product lock:`, `Post (edit-time, never generated):` and `Lines covered:` — and one new rule under "Writing section 9": composition beats prompting. No new variables; the session pastes the same three as v1.*

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

THE SCENE SHAPES AND THE MOOD RULES (the doctrine — a scene's Technique names one of these shapes; read them, never restate them)

{techniques}

{mood}

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

    Product lock: <only when the product is in this frame — the packshot
    is attached as a reference AND the label phrase copied verbatim from
    the production document, followed by "no garbled text, no morphing,
    product identical to the reference packshot". Otherwise the single
    word: none>

    Post (edit-time, never generated): <everything the finished piece
    shows that the editor builds, not the model — picture-in-picture,
    circles, borders, luma or chroma keying, captions and on-screen text,
    push-ins and zoom keyframes, transitions, music. Listed here so the
    editor owns it. Nothing in this slot may appear in the generation text
    above; if it does, the model bakes it in and the editor cannot undo it.
    A device screen this scene shows is generated dead black — "a blank
    black rectangle, no reflections, no UI, no icons, no text, no brand
    logos" — and the real screenshot is composited in at the edit; it is
    never generated. Otherwise: none>

    Result budget: <only when the scene shows a result or a before/after —
    60–70% improvement at most; 3–5 residual marks kept; no glow, no halo,
    no plastic skin; digital figures non-round, progress irregular.
    Otherwise: none>

    Section: <this scene's section label, verbatim from the production
    document — hook · problem · failed solutions · root cause · unique
    mechanism · solution · product · offer · call to action, or its plain
    description if the source flagged it as a candidate for the bank>

    Emotion: <one feeling the viewer carries during this scene — from the
    production document. If this scene cannot name one, it is a
    transition — merge it or cut it.>
    Outcome: <where the viewer lands at this scene's end — the next step
    of the emotional curve, from the production document.>

    Lines covered: <the line ids from the production document this scene
    carries — L3, L4 — or: none. This slot feeds the run's lines.json; a
    line missing from every scene's slot is a line the piece will not say.>

    ── attach ──
    identities: <the trained identities this scene needs, by name>
    plates: <the reference images, in fixed order — place, then each face
    in the same order every scene, then the product, then any texture>
    duration: <n>s · 9:16 · 1080p · audio generated in the same pass

**On the product lock.** Never describe label text and hope. A label
written in prose comes back approximated, garbled or invented; a label
locked by the attached packshot plus the verbatim phrase comes back right.
If the product is in frame and no packshot exists, write
`⚠ UNDECIDED: packshot` in the slot rather than describing the label —
the run's preflight refuses the scene until the reference exists.

**On the result budget.** This is an accept test, not a style note — the
course write-up (the owner, 09-14) is explicit: a total fix reads as fake. A
transformation shown at 100% or a digital figure that lands on a round
number (`50%`, `100 people`) fails the same way an illegible label fails —
automatically, every time. If the result shown looks like a brochure, it
is wrong; write the irregular, non-round, partially-healed version instead.

---

## Writing section 9 — the shot-by-shot script

This is the only authored part. Turn the scene's mechanics from the
production document into a strict chain of shots:

    <WS/MCU/CU> <focal length> <angle> — <what is in frame>; <action>;
    <performance cue>.
    Hard Cut to <next shot> …
    <ROLE> [<performance bracket>]: 'the line'

Six rules, all of them load-bearing:

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
5. **Mechanics are separate beats.** "Squeezes the paste onto the forearm
   → **sets the container down on the counter** → rubs in small circles."
   Write the put-down as its own beat or the model welds the object to the
   hand for the rest of the scene.
6. **Composition beats prompting.** Hands gripping the product, mirrors,
   and intricate hardware — door handles, hinges, clasps — are where a
   model fails first and keeps failing. When a frame of that kind fails
   QC on anatomy or reflection, it gets ONE re-prompt with explicit
   negatives. If it fails again, the composition changes: the product on
   a surface, hands out of frame, a wider shot, no mirror, simpler
   hardware. Never a third attempt on the same composition — a third
   attempt is the same mistake at the same price. Write the simpler
   composition in the first place wherever the mechanics allow it.
7. **The scene lands.** The shot chain renders the scene's Delta — the
   visible change from the first to the last frame of the scene. The
   Emotion is carried by the performance and the camera, never stated in
   a line of dialogue or a caption. The Outcome is reached by the
   scene's end; if the scene has no change, no feeling and no landing,
   it is not a scene — rewrite it as part of its neighbour.
8. **The copy is the spine.** The shot-by-shot script renders the
   production document's Emotion, Outcome and Section for this scene —
   its moment, its feeling, its landing — never improvises a new one. If
   the script could have been written without reading those three
   lines, it was written wrong.

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
- **Never let a Post item into the generation text.** A caption, a
  picture-in-picture, a push-in written into the shot list is baked into
  every clip and paid for again when the editor has to regenerate raw.

---

Output the scene blocks and nothing else: no preamble, no commentary
between them, no summary at the end.
