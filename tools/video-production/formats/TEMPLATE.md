# Format · <name>

<!-- Fill every field. A field that does not apply says so — "none", with the
     reason — rather than being deleted, because its absence is what lets the
     next reader assume. When the profile is written, add the row below to
     bank.json and run `python3 formats/render_bank.py`. -->

**The bank row** — copy into `bank.json`:

    {"id": "<slug, kebab-case — the value run.json carries as format>",
     "name": "<Name>",
     "what": "<what a scene contains, one line — the same line as below>",
     "profile": "<this file>",
     "status": "draft", "signed": null,
     "proven_on": null,
     "notes": ""}

**Shape.** <What this format is, in one sentence. What the words do, what
the pictures do.>

| | |
|---|---|
| **Cast** | <Which roles, how many faces. Every face is a reference from the brand's AI cast — a format consumes a character, never builds one (`../building-the-cast.md`).> |
| **Places** | <One continuous set, several, or none that matter.> |
| **Scenes** | <What drives a scene here — a section of the argument, a place, a paragraph. FEWER scenes, more beats inside them. Length is never a number: every scene carries the contract below, and its length falls out of its own paragraph.> |
| **Sound** | <Dialogue in the same pass, a song laid over, narration at the edit, texture only.> |

**What a scene contains.** <One line. This is the `what` of the bank row —
write it once and copy it there.>

**The beat shape.** <How the piece moves: hook → turn → proof → offer, or
line → line → line, or before → during → after. Where it slows down.>

**Stations used.** <Which of cast · still · restyle · motion · voice ·
audio this format actually runs. A song ad skips voice; a demonstration
often skips cast.>

**The references it needs.** <What is pointed at rather than described —
the cast sheet, the skin panels, the packshot, a source frame, a style
frame. A reference beats a description; list every one this format
depends on.>

**The sections that carry the weight.** <Which of the eleven sections do
the heavy lifting here, and which are near-boilerplate.>

**Ledgers that apply.** <Which of the six, and which do not, and why.>

**Post (edit-time).** <What the finished piece shows that the editor
builds and the model never generates — captions, picture-in-picture,
keying, push-ins, music. This is what the scene prompts' `Post` slot
carries for this format.>

**Gates it adds.** None — `RUN-PROTOCOL.md` carries them. <If this format
genuinely needs a check no other format needs, write it here as a line
that points at the protocol gate it extends, never as its own gate.>

**The failure this format invites.** <Every format has one thing it gets
wrong first. Name it, and the fix.>

**The run it was proven on.** <`runs/video-machine/<brand>/<label>/`, with
the date, or: not yet run end to end.>

**What still fails.** <Named honestly rather than quietly shipped: the
ceilings hit, the things the cut still gets wrong.>

## The scene contract (universal) — rewritten 2026-09-18

**A scene is one setting, one section of the argument, one PARAGRAPH of
voice — and ONE clip.** Damon's ruling that day: "the scenes are not
generated with detail — that is what causes the poor scene output and
frames within them; there is no clean voice-over — shooting line by line
comes out choppy. Fewer scenes, more frames within the scene describing
what happens, then the end of the scene; audio in each scene — each
section reads as a paragraph, a few sentences."

So a scene carries these slots, and no model, provider or brand word
appears in any of them:

**And since 2026-09-19 the brief carries those slots as a fenced `json`
block, which IS the brief** (Damon: *"format these briefs in a way that AI is
able to directly build what it needs to build"*). The Markdown above the
block is the readable view; nothing downstream parses it. The block's shape
is `brief_schema` in `machine/model-inputs.json`, printed in
`machine/MODEL-INPUTS.md`; a profile never restates it.

| Slot | Block key | What it is |
|---|---|---|
| Section | `section` | which of the nine sections of the argument this scene is |
| Technique | `technique` | the technique it runs, and with it the scene shape the doctrine gives that technique |
| Delivery | `delivery` (four named dials: humor · style · register · pacing) | the dials it is performed on, copied from the brief, never chosen here |
| Emotion | `emotion` | one feeling the viewer carries during it |
| Outcome | `outcome` | where the viewer lands at its end |
| Setting | `setting_id` | the one world block it plays in — a scene never changes place |
| Who | `who` | who is in it, by name; the cast block already describes them |
| **Voice** | `voice` | **the paragraph** — a few sentences, byte-identical to the script. Not a line. This is the unit the one continuous voice track is chunked on |
| **FIRST FRAME** | `first_frame` | a full still description in the stills order — subject · composition · action · location · style · camera · lighting — with the references it uses (cast sheet, packshot, style frame) |
| **BEATS** | `beats[]` | what happens between the two frames: one line each, ONE verb, the camera only where it moves, the words from the paragraph playing over it, the feeling it carries. Their timestamps come from the voice track, never from a guess. **A beat is not a picture** — it is written into the clip's timeline |
| **LAST FRAME** | `last_frame` | a still description written as a DELTA from the first, and nothing else — plus its camera, one of exactly `same` · `push-in to <framing>` · `pull-out to <framing>` · `new angle to <framing>` |
| To camera | `to_camera` | whether this scene is spoken to the lens. True: its audio is its own slice of the one continuous track and the clip lip-syncs to it. False: it is a B-roll scene and the same slice is laid under it at the edit |

### B-ROLL IS A SCENE (ruled 2026-09-19)

Damon, that day: ***"there is no B-roll."*** Where a format's argument SHOWS
something — the product in the hand, the row of things already tried, the
mechanism demonstrated, a before and after, a behaviour ending — that is a
scene of its own, not a note inside somebody else's:

- `to_camera: false`, its own `who` (the hands · the product · the presenter
  seen and not speaking · nobody), its own setting, its own two frames, its
  own beats;
- its own `voice` paragraph — the slice of the ONE read that plays OVER it,
  recorded like every other and laid under the picture at the edit;
- the clip carries **no audio**, its prompt says *Nobody speaks*, and the
  submit sheet marks it `VO over: vo/<scene>.mp3`.

**Never an insert.** No `(insert …)` in a beat, no `Cutaways:` line — one
clip cannot cut, and the gate refuses both by name. A piece alternates: a
to-camera scene, then a B-roll scene carrying the next paragraph, **unless
this profile says otherwise** — which is what the profile's own beat shape
and "sections that carry the weight" are for. The sections that show (proof,
product, failed solutions, the unique-mechanism demonstration) default to
B-roll or to a to-camera + B-roll pair.

### A BEAT IS ONE VISIBLE ACTION

One verb, present tense, something a camera sees: *taps the tube once*,
*turns the forearm face-up*, *looks up to the lens*. How a line is delivered
— `says`, `stops`, `slows`, `settles` — is not an action and goes in the
beat's bracket. Two verbs joined by "and" or "then" are two beats. A pause is
a beat whose action is `holds`. The list the gate reads is `beat_grammar` in
`machine/model-inputs.json`; a profile never restates it either.

**The LAST FRAME's camera is one of exactly four** — `same` ·
`push-in to <framing>` · `pull-out to <framing>` · `new angle to <framing>` —
and a move always names the framing it lands on.

**Two stills a scene, never more.** The first frame is generated; the last
frame is an edit of the first naming only what changed. Everything between
them is beats. A third generated still is a third chance to drift.

**No length, anywhere.** A scene's length falls out of its paragraph — the
voice track says how long it is, and the clip is cut to that. A format
profile gives the length philosophy, never a number.

**Aspect and resolution are declared ONCE for the whole piece**, never per
scene, and every still, clip and crop carries the same values.

THE NAMING RULE: if a scene cannot name its Emotion and its Outcome, it
is a transition — merge it or cut it. This rule outranks the profile.

What each door does with these slots — the exact request fields, the
assembly order, the maker's limits — is `machine/MODEL-INPUTS.md`, rendered
from `machine/model-inputs.json`. A profile never restates it.
