# Stage 3 · Scene prompts — v6

*v6 (2026-09-18): the scene is a PARAGRAPH and TWO FRAMES. Section 9 is no
longer a shot chain: it is a FIRST FRAME written in the stills door's own
order, a TIMELINE of beats written in the motion door's own order, and a
LAST FRAME written as a delta. One new variable, `{model_inputs}` — the
rendered model input contract, bound by path — so this prompt READS what
each door takes instead of restating it. The `duration · ratio · resolution`
line is gone: a scene's length comes from its paragraph and the ratio and
resolution are the piece's, declared once. Every other variable and slot is
v5's, unchanged.*


*v5 (2026-09-18): the taste and delivery layer — one new slot in every scene
block, `Delivery:`, and one new variable, `{delivery}`. The brief names the
dials per scene; this carries them into the performance bracket and into the
shot. No dial is chosen here. Every other variable and slot is v4's,
unchanged.*

*v4 (2026-09-18): three new slots in every scene block after `Lines
covered:` — `Section:`, `Emotion:` and `Outcome:` — and two new rules
under "Writing section 9": the scene lands, the copy is the spine (the
scene-authoring and intimate-copy rulings, 09-17/09-18). No new
variables; the session pastes the same three as v3.*

*v3 (2026-09-17): one new slot after `Lines covered:` — `Result budget:` —
and one new line in the `Post` slot's guidance, both from the course
write-up (Damon, 09-14), §2 and §3. No new variables; the session pastes
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

THE DELIVERY DIALS (the doctrine — the values a scene's Delivery slot is
spelled in; read them, never restate them, and never choose one here)

{delivery}

THE MODEL INPUT CONTRACT (what each door actually takes, the order it wants
the words in, and its limits — read it, never restate it, and never write a
field it does not have)

{model_inputs}

---

For **each scene** in the production document, output a block in exactly
this shape. Repeat it for every scene, including any marked ALT.

    ═══ SCENE <n> · <function> · <THE SETTING> ═══

    (no duration, no span — a scene is as long as its paragraph, and
    the aspect and resolution are the piece's, declared once)

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

    Voice: <this scene's PARAGRAPH, verbatim from the production
    document — every sentence of it, one block. It is not split into
    lines here and it is never paraphrased.>
    To camera: <yes | no>

    <the FIRST FRAME, the TIMELINE and the LAST FRAME — see the rules
    below>

    Audio: <what is heard that is not the paragraph — room tone, the
    sounds the beats themselves make, the negatives. A `to camera` scene
    says: the scene's own slice of the one voice track, lip-synced,
    nothing else.>

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

    Delivery: <this scene's delivery dials, copied from the production
    document's own Delivery line for this scene, in this fixed order and
    spelled exactly as the delivery dials spell them —
    `humor · delivery style · register · pacing`, then `world: <what the
    reference world directs here>` and `avoid: <what is stripped here>` where
    the brief filled them. A dial the brief left unfilled is written
    `unfilled` and nothing is invented in its place. NOTHING IS CHOSEN HERE:
    this slot is a copy, exactly as sections 1–8 are a copy, and a dial that
    appears here without appearing in the production document is a dial
    nobody decided.>

    Lines covered: <the line ids from the production document this scene
    carries — L3, L4 — or: none. This slot feeds the run's lines.json; a
    line missing from every scene's slot is a line the piece will not say.>

    ── attach ──
    identities: <the trained identities this scene needs, by name>
    plates: <the reference images, in fixed order — place, then each face
    in the same order every scene, then the product, then any texture>
    frames: FIRST FRAME (generated) · LAST FRAME (an edit of the first) —
    exactly two, attached as the clip's start image and end image
    aspect · resolution: <the piece's, copied from its own block — never
    chosen here, never written per scene>

**On the product lock.** Never describe label text and hope. A label
written in prose comes back approximated, garbled or invented; a label
locked by the attached packshot plus the verbatim phrase comes back right.
If the product is in frame and no packshot exists, write
`⚠ UNDECIDED: packshot` in the slot rather than describing the label —
the run's preflight refuses the scene until the reference exists.

**On the result budget.** This is an accept test, not a style note — the
course write-up (Damon, 09-14) is explicit: a total fix reads as fake. A
transformation shown at 100% or a digital figure that lands on a round
number (`50%`, `100 people`) fails the same way an illegible label fails —
automatically, every time. If the result shown looks like a brochure, it
is wrong; write the irregular, non-round, partially-healed version instead.

---

## Writing section 9 — the first frame, the timeline, the last frame

This is the only authored part, and since 2026-09-18 it is three pieces, in
the orders the two doors themselves ask for. Read `{model_inputs}` for the
field names and the limits; write to them, never around them.

**1 — THE FIRST FRAME, in the stills door's own order.** One still, written
in the order the contract gives — subject · composition · action · location
· style · camera · lighting — then the references it is built from:

    FIRST FRAME
    Subject: <who is in it, by name, and what the body is doing>
    Composition: <how it is framed, and how much of the frame each thing
    occupies — from the position ledger>
    Action: <the single action visible at this instant>
    Location: <the place, in the production document's own anchor
    vocabulary>
    Style: <the piece's grade sentence, verbatim>
    Camera: <the result — how high, how close, how much depth. Never a
    device.>
    Lighting: <where the light comes from and how flat it is>
    Refs: <the cast sheet, then the packshot where the product is in
    frame, then any texture or style frame — in that fixed order>

**2 — THE TIMELINE, in the motion door's own order.** The motion paragraph
is assembled the way the maker asks: an asset line, one summary sentence,
the beats with their spans, then what holds. The machine assembles the
final string from these pieces; you write the pieces:

    TIMELINE
    Summary: <one sentence — subject, place, event, style, camera. Nothing
    else in it.>
    B1 · At: <the span from the voice timing sheet, or blank and the
    machine fills it> · Do: <ONE verb> · Camera: <only where it moves,
    else `held`> · Over: "<the words from the paragraph playing over this
    beat>" · Beat: <the feeling>
    B2 · …
    Holds: <what does not change across the clip — the angle, the room,
    the grade, the wardrobe — plus the negatives this piece always
    carries>

**3 — THE LAST FRAME, as a delta.** One line. What is different from the
FIRST FRAME, and nothing else:

    LAST FRAME
    Change: <what moved, what is now different — never the room, the
    wardrobe, the light or the framing again>
    Beat: <the feeling the scene ends on>

Nine rules, all of them load-bearing:

1. **The first frame is loaded.** The subjects are already in position.
   Never open on an empty room that someone then walks into, unless an
   entrance is exactly what the ledger says happens here.
2. **One verb per beat, in strict order, no gaps.** The timeline is a chain
   and the model follows it. Two actions in one beat become one blurred
   action, and the contract's gate refuses them — two actions are two
   beats. Never more beats than the contract's own panel limit.
3. **The camera is on the speaker.** Whoever talks is who is on screen for
   that paragraph, or another character will be shown mouthing it.
4. **Dialogue carries a performance bracket, and the bracket carries the
   dials** — `[eyes locked, jaw tight, voice sharp]`. The bracket is
   direction and it lands. Every bracket in this scene opens with the
   scene's delivery style and register, spelled as the Delivery slot spells
   them, before any line-specific direction:
   `[deadpan, plain-flat — eyes locked, no lift on the last word]`. Where
   the pacing dial names a pause, the pause is written as its own beat with
   something happening in it, never as a number of seconds. A bracket that
   contradicts the Delivery slot is the drift this slot exists to stop.
5. **Mechanics are separate beats.** "Squeezes the paste onto the forearm"
   → "**sets the container down on the counter**" → "rubs in small
   circles" — three beats, three verbs. Write the put-down as its own beat
   or the model welds the object to the hand for the rest of the scene.
6. **Composition beats prompting.** Hands gripping the product, mirrors,
   and intricate hardware — door handles, hinges, clasps — are where a
   model fails first and keeps failing. When a frame of that kind fails
   QC on anatomy or reflection, it gets ONE re-prompt with explicit
   negatives. If it fails again, the composition changes: the product on
   a surface, hands out of frame, a wider shot, no mirror, simpler
   hardware. Never a third attempt on the same composition — a third
   attempt is the same mistake at the same price. Write the simpler
   composition in the first place wherever the mechanics allow it.
7. **The scene lands.** The timeline carries the scene from its FIRST
   FRAME to its LAST — the visible change between the two is the scene's
   whole delta, and the final beat lands on the last frame exactly. The
   Emotion is carried by the performance and the camera, never stated in
   a line of dialogue or a caption. The Outcome is reached by the
   scene's end; if the scene has no change, no feeling and no landing,
   it is not a scene — rewrite it as part of its neighbour.
8. **The shot carries the delivery.** The Delivery slot is a direction for
   the camera as much as for the voice: the delivery style names a camera
   and a rhythm, and the timeline honours them — a `hands-and-voiceover`
   scene keeps the face out of frame, a `plain-testimonial` scene does not
   get a push-in it was never going to have, a `beat-and-pause` scene puts
   something in frame for the silence to sit on. Where the Delivery slot and
   the mechanics disagree, write `⚠ UNDECIDED: delivery vs mechanics` rather
   than choosing; a scene that quietly drops its register is the failure
   nobody catches until the clips exist.
9. **The copy is the spine.** The frames and the timeline render the
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
