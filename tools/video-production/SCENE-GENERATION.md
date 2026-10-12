# How a scene is generated

**The one place the process lives.** Written 2026-09-18 evening, from the
scene that went through the door by hand that day and came back right — one
clip, nine seconds, the words exactly as written. Everything below is what
that call did, generalised so it runs on any scene, any brand, any format.

If a prompt, a profile or a tool disagrees with this page about HOW a scene
is made, this page is the process and that one is stale.

**Superseded for clips and voices, 2026-10-03 (the owner) — `THE-CHAIN.md` is the process.** Clips are Omni Flash on fal at 1080p animating the approved GPT Image 2.5 picture (`run.py start … --clips` → `machine/omni_clips.py`); a person's clip always starts from the approved picture, never a clip's last frame; on-camera lines are said by Omni and turned into the cloned voice (speech-to-speech), off-camera lines are text-to-speech in the cloned voice — the voice-first workflow is retired. What follows is the 2026-09 per-scene method, kept as the record of the legacy doors (`--legacy-clips`).

**Amended 2026-09-22** — the clip door moved to MiniMax H3 through
Higgsfield after a live bake-off (the owner: *"MiniMax H3 looks pretty good and
is super cheap… lip sync looks good… big savings. We'll use the 15-second
pricing; most scenes should be 4–6 seconds with a few frames/movements."*).
Step 4 below is that door; the stills and the voice are unchanged. Seedance
2.5 is the alternate, for a scene that genuinely needs 15–30 s in one take.

---

## 0. The brief is the prompt (2026-09-19)

the owner, that day: *"this brief is for the AI system to interpret, not for me
as the human to read — format these briefs in a way that AI is able to
directly build what it needs to build."*

So a brief is no longer a page a session reads and types up. **Its truth is
the fenced `json` block at the end of it**, in the shape
`machine/model-inputs.json` holds as `brief_schema`, and the fields in that
block ARE the model inputs:

| The brief's field | Where it goes, verbatim |
|---|---|
| `first_frame` — its seven keys, in order | the image door, as the whole still prompt |
| `last_frame.change` | the same door, as the edit prompt — the delta, then the one keep-line |
| `voice` | the voice door, as the text it speaks |
| `beats[]` | the motion door, as the clip's own timeline, one line each |

The Markdown above the block is the readable view for a person, rendered from
those same fields. **Nothing downstream parses it** — `machine/scenes.py`
reads the block first and falls back to the old Markdown parse only for a
brief written before the block existed. `run.py start` writes the view out as
`brief-view.md` beside the brief, from the block, so the page a person opens
and the prompt a door receives can never be two documents.

**Every key is present on every object.** A string stays a string, a list
stays a list, `to_camera` is `true` or `false`. A key with nothing to say
carries an empty string rather than being dropped, because a dropped key is a
gap the gate cannot tell from an omission. Preflight rule 12 checks the block
against the schema and names the key.

**A scene the brand's files cannot fill is `held`.** It carries `id`,
`section`, `setting_id` and `held` — the one fact that would release it — and
nothing else. It keeps its place in the order, the machine builds nothing for
it, and the run prints it as a finding for the owner.

---

## 1. What a scene is

**One setting. One paragraph. One clip. Two stills. The middle is beats.**

| | |
|---|---|
| **One setting** | a scene never changes place. A new place is a new scene |
| **One paragraph** | a few sentences of the script, spoken straight through — not a line, and never one clip per line, which is what made the old cut feel choppy |
| **One clip** | the whole scene, start to finish, in a single take |
| **Two stills** | the FIRST FRAME (generated) and the LAST FRAME (an edit of the first). A third still is a third chance to drift |
| **The middle** | beats — what happens between the two frames, one action each, written onto the clip's own timeline and timed off the voice. **A beat is never a picture** |

**No length is ever a number anybody chose.** The paragraph is read, the
read says how long it is, and the clip is cut to that. A format says how a
scene should feel, never how many seconds it runs.

**The last frame does two jobs.** It is where the camera ends up, and it is
what the next scene opens from — so a piece that lands every last frame is a
piece whose cuts already match.

### B-roll is a scene (ruled 2026-09-19)

the owner, reading a brief in which every scene was the same person talking to
the lens: ***"there is no B-roll."***

Where the argument SHOWS something — the product in the hand, the jars on the
shelf, the closet rail, the hands at the sink, a before and after, the
mechanism demonstrated — that is **a scene of its own**: `to_camera: false`,
its own `who` (the hands · the product · the speaker seen and not speaking ·
nobody), its own setting, its own two frames, its own beats, and its own
slice of the paragraph — the words that play OVER it.

| | a to-camera scene | a B-roll scene |
|---|---|---|
| the voice | attached to the clip as `audio_references`, and the clip lip-syncs to it | recorded and sliced like every other, and laid UNDER the picture at the edit |
| the prompt | carries the lip line | carries `Nobody speaks.` instead |
| the sheet | names the slice as audio | names it as `VO over: vo/<scene>.mp3` |
| everything else | identical | identical |

**Never an insert.** No `(insert …)` inside another scene's beat, no
`Cutaways:` line under a scene. One clip cannot cut, so a picture wedged into
another scene's clip is a picture nobody makes — the gate refuses both by
name. The rhythm a piece runs is a to-camera scene, then a B-roll scene
carrying the next paragraph, the voice running unbroken across both; the
sections that show (proof, product, failed solutions, the unique-mechanism
demonstration) are the ones that take it.

### B-roll after A-roll, `to_camera` always, cards as plates (ruled 2026-09-23)

the owner: *"We need to ensure b-roll makes it into the actual production brief
too, clearly AFTER a-roll is detailed, and it's carried through our process
properly."* B-roll is ideated from the swipe and MADE here; so are cards.

- **The brief's order.** The AI brief (v13) writes the A-roll first, then a
  headed B-ROLL section — each scene with the swipe make-list row it comes
  from, what it shows and the exact words under it — then CARDS, then a
  ROLL SHEET CHECK. Its block stays ONE `scenes` list in play order.
- **`to_camera` is said on every scene.** Missing, the scene is refused by id
  before the voice is made. It used to default to talking whenever the scene
  had a voice, so a B-roll scene could quietly become a face.
- **No B-roll inside a talking scene, in any wording.** A shot that cuts away
  from the speaker is its own `to_camera: false` scene over its slice of the
  voice (the three-doctors run wrote two inside talking scenes; neither was made).
- **A card is a scene of `kind: "card"`** — a text-free `plate`, its exact
  `lines`, `lands_on` and `sfx`. It becomes ONE still, `<scene>-PLATE`, on the
  first-frame door with the contract's clean line, and no clip. The words
  travel in `plan.json` as `scene.card` for the edit to set on top.
- **The roll sheet is checked.** Every make-list row maps to a scene of the
  matching kind (B rows → `to_camera: false`, C rows → a card) or a drop
  reason; otherwise the run stops, naming the row. A brief without the table
  is older and is warned, not refused.

### Every element, made here (ruled 2026-09-23 — `ELEMENTS.md`, brief v14)

the owner: *"all these elements need to be green."* The teardown names every
element, the brief carries it, **this machine makes it or pulls it from a
bank**, the edit only assembles.

- **Every scene names its `kind`** (talking · broll · card · screen · split ·
  greenscreen · endcard) and `opens` (exactly one), `module`, `priority`
  (1–3). A kind that disagrees with `to_camera` is refused by id.
- **A screen** is one text-free plate (`<S>-PLATE`), like a card; its
  `surface` and `lines` travel for the edit.
- **A split** is two B-roll pictures: each side gets its own first frame,
  last frame and one silent clip (`<S>-L`, `<S>-R`), timed off the split's
  own slice of the read, which is laid under the pair once.
- **A greenscreen is a talking scene** — its own frames, beats and voice —
  plus one text-free background still (`<S>-BG`). The edit keys one over
  the other.
- **An endcard is an EDIT of the brand's real packshot** (`<S>-PACKSHOT`,
  the fidelity door) — never a product drawn from words. Its offer lines and
  guarantee must be in the brand's offer bank or say `[UNFILLED]`.
- **Sound comes from the banks.** `music` and each `sfx` cue are picked from
  `banks/` at `start`; a row that is not made yet stops the run, named.
- **Every clip is colour-matched** to the piece's first frame when it lands,
  the original kept in `media/versions/`.

### The beat grammar

**A beat is one visible action, one verb, present tense** — something a
camera can see happen: *taps the tube once* · *turns the forearm face-up* ·
*looks up to the lens*.

- **Never a delivery note.** `says`, `stops`, `slows`, `settles`, `pauses`,
  `begins` describe the read, not the picture. They go in the bracket at the
  end of the beat.
- **Never two actions.** Two verbs joined by "and", "then" or a comma are two
  beats. Two adjectives are not two actions, and a consequence is not a
  second action — what the frame looks like afterwards is the last frame's
  job.
- **A pause is a beat**, and its action is `holds`, with the silence named in
  `over`.
- **Every scene has at least one beat and a paragraph.**

The whole grammar — the words a beat never opens on, the pause verb, the
insert markers — is `beat_grammar` in `machine/model-inputs.json`, so the
prompt and the gate read the same list.

### The LAST FRAME's camera is one of exactly four

`same` · `push-in to <framing>` · `pull-out to <framing>` ·
`new angle to <framing>` — and a move names the framing it lands on, in the
same words the FIRST FRAME's composition used. `new angle` on its own is a
move with nowhere to go, and the gate refuses it rather than guessing.

---

## 2. The sequence — in this order, every time

Nothing here is optional and nothing can be reordered: each step is the
input to the next.

### Step 1 · The voice, first, as ONE read

**Station:** voice · ElevenLabs, direct.
**In:** the whole script, chunked one paragraph per scene, plus the
character's own voice.
**Out:** `vo/track.mp3` (the whole piece, read once), `vo/timing.json`
(where every scene and every sentence sits on that one timeline), and
`vo/<scene>.mp3` — the slice for each scene.

One read for the piece, stitched request to request, so the performance
never restarts between scenes. **Nothing else in the run starts until this
exists**, because every timestamp downstream is read off it.

### Step 2 · The first frame

**Station:** still · GPT Image 2.5, direct, a generation.
**In:** the scene's FIRST FRAME written in the stills order —
subject · composition · action · location · style · camera · (viewpoint, required on a frame with no face in it: whose eyes the camera is + which edge every limb enters from, 2026-09-22) · lighting —
plus the framing sentence for the piece's aspect, with the **cast sheet** as
the identity reference.
**Out:** one still. This is what the clip starts on, and what carries the
face, the wardrobe, the room and the light for everything after it.

### Step 3 · The last frame

**Station:** edit · GPT Image 2.5, direct, `images/edits`, input fidelity
high.
**In:** **the delta and nothing else** — only what changed — plus the one
line that says what may not change, and **two references, in this order:
the first frame, then the cast sheet**. With the frame alone the face
drifts; that was measured, not assumed.
**Out:** one still, then **colour-matched back to the first frame** —
resized to it and matched per channel — so the pair share exposure, white
balance and size. Two stills that disagree about any of those read as two
different shots the moment a clip runs from one to the other.

### Step 4 · The clip

**Station:** motion / talking · **MiniMax H3 through Higgsfield**
(`minimax_h3`, ruled 2026-09-22). One call, one clip, the whole scene. 2K
only (1440×2560 at 9:16), 4–15 s, 2 credits a second — 6 s = 12 cr ($__),
10 s = 20 cr ($__), 15 s = 30 cr ($__).

**The door takes TWO shapes, and the scene decides which.** The backend's
own refusal, verbatim: *"start_image/end_image cannot be mixed with
reference media; audio_references require at least one image or video
reference."* So:

| | a TALKING scene (to camera) | a SILENT scene (B-roll) |
|---|---|---|
| the first frame | `image_references` | `start_image` |
| the last frame | **not on the call** — still made (the next scene opens from it), but it travels as words: the last beat ends on its Change | `end_image` — the designed camera move lands on it |
| the voice | `audio_references` — the scene's slice of the one voice track | none; the slice is laid under the picture at the edit |
| `prompt` | the four blocks below, @Image1 + @Audio1 in the asset line | the four blocks, @Image1 + @Image2 in the asset line |
| `duration` | the slice, rounded up. Floor 4 s, **ceiling 15 s** | the beats' own end, same floor and ceiling |
| `aspect_ratio` | the piece's | the piece's |
| `resolution` | `2K` — the only one this door makes; the piece's Resolution sizes the stills | `2K` |

**The cost of no last frame on a talking scene:** the model decides where
the clip ends, and with nothing to land on it can hold the final gesture
longer than the brief wanted (the bake-off's scene 1 held the hand up). The
last beat's *ending on …* words are the one place the clip is told where to
stop — write them as the frame, not as a mood. A talking scene that must
land an exact frame goes to the alternate.

**The 15-second rule.** A scene longer than 15 s is refused by rule 12 by
name — *split at a beat, or route to the alternate door (seedance_2_5, up to
30 s)* — never quietly shortened. the owner's planning number: most scenes are
4–6 s with a few movements.

**The alternate: Seedance 2.5 on the same connector** — takes the first
frame, the last frame and the voice slice together on one call, mode
`omni_reference`, up to 30 s, 7 credits a second (3.5× the price). Chosen by
flipping the registry's `doors.<station>.model`, never per scene; the
machine builds the 2026-09-18 shape from that door's own row.

**The cast sheet and the style frame do NOT travel on the clip.** The first
frame already IS the cast, the wardrobe, the room and the light. A reference
attached beside it is a second opinion about the same face, and the gate
refuses it.

**The subject zone holds at both ends, and Motion QC watches the middle**
(2026-09-23). Every frame is measured into the centred 4:5 zone of the 9:16
frame before a clip is made from it (`machine/safezone.py`; a frame still
outside after one fix edit is held and no clip is made). The clip starts on
the first frame and ends on the last, so the zone holds at both ends; what
happens between them — a head rising into the top band on a push-in, a
product sinking below — is checked by Motion QC, check 7 "Subject zone"
(`prompts/stage-5b-motion-qc/stage5b-motion-qc-v2-damon.md`).

### Step 5 · The line check

Every talking clip is transcribed and compared to the paragraph it was
supposed to say. Below 85% it is a FLAG, not a pass — a clip can lip-sync
perfectly to the wrong words, and has.

### Step 6 · The director

The scene read as a viewer sees it: the half-second answer, the scroll
stopper, the delivery across the whole paragraph with no restart between
sentences, and the motion read ACROSS its frames — the first frame held, the
last frame reached, the delta actually happened. Two director flags on one
scene means the scene is rewritten in the script, not re-rendered.

---

## 3. The prompt — four blocks, in this order

1. **The assets** — what travels: @Image1 and @Audio1 on a talking scene;
   @Image1 and @Image2 on a silent one. Never a media the call does not
   carry.
2. **One clean sentence** — who, where, what they do, the style, the camera.
   Built from labelled slots against a fixed template, never by gluing raw
   fields end to end.
3. **The timeline** — one line per beat, one action each, its span read off
   the voice track. The first beat names the frame at @Image1; the last
   settles on the framing of @Image2 where @Image2 travels, and otherwise
   *ends on* the LAST FRAME's Change, in words.
4. **What holds** — the take, the setting, the light, the wardrobe, and the
   two negatives every clip carries.

**The call that worked, verbatim** (a real scene, 9 s, line check 100% —
the 2026-09-18 shape with @Image2 attached, which is now the alternate
door's; on the settled door a talking scene drops the @Image2 sentence and
its last beat reads *…, ending on <the LAST FRAME's change>*):

```
@Image1 is the first frame: the woman at her kitchen table, medium-close, left forearm resting on the table, eyes on the lens. @Image2 is the last frame: the camera has pushed in close, her left forearm face-up filling the lower half of the frame with her right fingertip resting on one brown spot, her face in the upper third looking straight into the lens. @Audio1 is her voice; she speaks the words in @Audio1 exactly, nothing else is said.

A woman in her mid-60s at her kitchen table tells the camera how her own sun spots keep coming back, plain phone footage, one slow push-in from medium-close to close.

0-2.5s: she speaks to the lens, still, hands resting on the table, the frame at @Image1.
3.2-4.6s: she turns her left forearm face-up on the table.
4.6-6.7s: her right fingertip comes down onto one brown spot as she says the words about the same brown spot in the same place, the camera beginning a slow push in.
7.1-8.9s: she looks straight into the lens and holds, fingertip still on the spot, the push-in settling on the framing of @Image2.

One continuous take, no cuts, the only camera movement is the slow push in. Same kitchen, same morning daylight from the left, same grey top throughout. Natural lip movement matching the voice. No subtitles. No background music.
```

**The same shape, as the chain writes it** for any scene:

| Block | The template |
|---|---|
| assets (talking) | `@Image1 is the first frame: <the first frame in one line>. @Audio1 is <who>'s voice; they speak the words in @Audio1 exactly, their lips moving with every word, nothing else is said.` |
| assets (silent) | `@Image1 is the first frame: <the first frame in one line>. @Image2 is the last frame: <the delta>.` |
| summary | `<who> at <setting> <what they do>, <the style>, <the camera in one phrase>.` |
| timeline | `<start>-<end>s: <one action>` — plus the words playing over it on a silent scene, the frame at @Image1 on the first, and on the last either `settling on the framing of @Image2` (silent) or `ending on <the LAST FRAME's change>` (talking), then the performance in brackets at the end |
| consistency | `One continuous take, no cuts, <the camera sentence>. Same <setting>, same <light>, same wardrobe throughout. Natural lip movement matching the voice. No subtitles. No background music.` |

The camera is one phrase, read off the LAST FRAME's own camera word:

| The word | In the sentence | In what holds |
|---|---|---|
| `same` | a locked frame | the camera does not move |
| `push-in to <framing>` | one slow push-in from <where it starts> to <where it lands> | the only camera movement is the slow push in |
| `new angle to <framing>` | one move to a new angle, <where it lands> | the only camera movement is the one move onto the new angle |

**The words are never written twice.** On a to-camera scene the paragraph
arrives as attached audio and no beat restates it. Writing the line into the
prompt as well is how a clip ends up saying something slightly different.

**The stills prompts, for completeness:**

- **First frame** — the stills order (subject · composition · action ·
  location · style · camera · lighting), then the framing sentence for the
  piece's aspect.
- **Last frame** — `<the delta>. Keep the person, wardrobe, setting, colour,
  white balance and light exactly as in the reference. Change nothing else.`

---

## 4. What the gate refuses

Every item is checked against the model input contract
(`machine/model-inputs.json`, printed for reading as
`machine/MODEL-INPUTS.md`) before anything is sent. Each refusal names its
own field, and **nothing submits red**:

- a brief whose **json block is missing a key**, or carries a string where a
  list belongs, or a `to_camera` that is not true or false — named key by key;
- a beat naming **two actions**, **no action**, or **a delivery note**;
- a scene carrying **`Cutaways:`** or an **`(insert`** inside a beat —
  B-roll is a scene, not an insert;
- a **B-roll scene with audio attached** to the clip;
- a scene with **no `to_camera`** (named by id), a **card whose plate has
  words in it** or that has no `lines`, and a **swipe make-list row** carried
  to no scene with no drop reason, or to a scene of the wrong kind
  (2026-09-23 — these three also stop `run.py start` before the voice);
- a LAST FRAME whose **camera move names no framing** to land on;
- a piece whose **aspect is not a value the doors take**, or whose
  resolution is a **pixel pair** — the clip door makes 2K and the still size
  is resolved from the aspect;
- a scene with **no first frame** — the clip has nothing to start on;
- a scene with **no last frame** — nothing to land on;
- a to-camera scene with **no slice of the voice track**;
- a clip carrying **any other reference** — a cast sheet or a style frame
  attached beside the first frame;
- a talking clip carrying an **`end_image` beside its audio** — the door's
  own 422, quoted back;
- **no duration**, or a paragraph **past 15 seconds** — *split at a beat, or
  route to the alternate door (seedance_2_5, up to 30 s)*; never quietly
  shortened;
- a beat naming **two actions**, or none;
- **more than two stills** in one scene;
- an edit with **one reference**, or whose first reference is not the frame
  it edits;
- a **frame with no delta** — an edit that names nothing re-generates the
  frame instead of changing it;
- **a prompt that cannot be built** — a missing labelled field is a refusal
  by name, and no prompt is written at all. A block assembled around a gap
  is a fragment, and a fragment is how a clip ends up being about something
  else.

---

## 5. The three edit rules

1. **Two references, in order** — the frame being edited first, the cast
   sheet second. The first reference is the one whose detail is preserved.
2. **The delta only** — never describe what the source image already shows.
   Describing the room again tells the door to rebuild the room.
3. **Colour-match back to the first frame**, mechanically, every time,
   before anyone looks at it.

---

## 6. What is deliberately NOT done

- **No middle stills.** What happens inside a scene is beats on the clip's
  timeline. Generating them as pictures is the drift this shape removes.
- **No scene length as a number in the brief.** The read decides; a profile
  gives the philosophy, never the seconds.
- **No second door.** One image door for every still and every edit; one
  motion door for every clip. The alternate (Seedance 2.5, 15–30 s in one
  take) exists in the registry for the scene that needs it — it is a flip of
  the registry, not a choice made per scene.
- **No line-by-line voice.** One read for the piece, sliced. A call per line
  restarts the performance and the cut hears it.

---

**Where this is enforced:** `machine/model-inputs.json` (the contract, which
now also holds `brief_schema` and `beat_grammar`) · `machine/scenes.py`
(reads the brief's block, and renders the human view from it) ·
`machine/model_inputs.py` (assembles every prompt, runs the gate) ·
`machine/run.py` (builds the two stills and the one clip per scene) ·
`machine/preflight.py` rule 12 · `machine/test_frames.py` (`TheGoldenCall`
holds the chain to the settled door's two shapes; `TheSeedanceAlternate`
holds the 2026-09-18 shape the alternate still takes).

## The spoken rule, ruled 2026-09-19 — the unit is the thought

the owner heard the first spoken paragraph read as three clipped statements and
said it did not feel like one complete sentence, because it wasn't one. The
rule that replaced "shorten and split":

**A person says one thought in one breath; the punctuation marks where they
breathe.** An ellipsis (`...`) is the mid-thought breath — the speaker pauses,
the thought is not over. A full stop ends a thought. An exclamation or a
question lifts it where the point lands. A comma is a breath that does not
stop. Never chop one thought into a row of short statements: a list is not a
person.

| | |
|---|---|
| the prose | This — the old surface still sitting on your hand — is why the sunscreen hasn't worked. |
| chopped, wrong | This is the old surface. It's still sitting on your hand. That's why the sunscreen hasn't worked. |
| **spoken, right** | **This is the old surface still sitting on your hand... That's why the sunscreen hasn't worked!** |

Measured on June's voice: the spoken line reads in 5 s with two breaths of
under half a second; the chopped one in 7 s with three full pauses. The rule
lives in `components/marketing-doctrine/spoken.json` (`the_thought`), the
spice pass writes to it (4g v3, rule 0), the brief's gate keeps the ellipsis
and refuses the dash, and `voice.py` reads the ellipsis as the breath. The
read the owner chose: stability 0.45 · style 0.3 · speed 1.0 · speaker boost off.
