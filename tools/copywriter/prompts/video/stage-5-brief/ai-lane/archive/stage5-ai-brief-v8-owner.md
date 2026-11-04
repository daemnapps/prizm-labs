Here are the transformed scripts, one per source format: {stage4_outputs}
Here is the hook set, with every variation and its scroll stopper: {hook_set}
Here is the record of the source video, shot by shot: {teardown_record}
Here is the injection — our script with the characters, the scenes and the
production instructions for this route: {baseline_injection}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here is our language bank: {language_bank}
Here is the brand's banked cast — the people it has already built and
approved, with their descriptions and their generation handles: {casting}
Here is the spice sheet — the format-relevance line, the voice direction, the
lookalike-type B-roll character, the styling notes and the delivery dials per
section, every item sourced: {spice_sheet}
Here are the taste and delivery dials — the values a scene's Delivery line is
spelled in: {delivery}
This run's production route: {production_route}

Write the shot list the AI video machine generates from.

**Print the lane first.** The first line of your output, before the concept
name and before anything else, is:

```
LANE: ⟨the production route above, in caps⟩
```

One line, nothing after it on that line. The lane is decided per run and a
brief that does not carry it is a brief nobody can tell was written for the
right hand.

**Nobody is filmed on this route.** The field is called `Shot:` and not
`Film:` for that reason — it names a picture that has to exist, not an
instruction to a person holding a camera. The creator lane's brief is a
different document written for a different hand; nothing in it belongs here. Every person, place and shot in this
document gets generated — a cast station makes each character once, a voice
station speaks the lines, a scenes station composes one still per frame, a
motion station turns stills into clips. This brief is the only thing those
stations read, so everything they need must be on the page as generatable
text. **A detail this document does not carry does not exist downstream** —
there is no set to glance at and no person to ask.

**This prompt supplies no content — the run supplies all of it.** The chain
has already produced everything this brief needs, stage by stage, and your
job is to move each piece into its slot in generatable form. In the shape
below, everything inside ⟨angle brackets⟩ is a slot naming what goes there;
the map below says which input fills it. No angle bracket may survive into
your output — a bracket left in means a slot went unfilled.

## THE SOUND FORM DECIDES WHAT `Say:` IS

The teardown's `Sound form:` line rules this, and it is not a stylistic
note — it changes what you are writing.

- **SPOKEN** — `Say:` lines are spoken lines, exactly as elsewhere in this
  prompt. This is the default and most sources are this.
- **SUNG or RAPPED** — **the script is LYRICS, not narration.** The piece
  is a song. Then:
  - Write the lines as lyrics with their structure marked — `[verse]`,
    `[chorus]`, `[bridge]` — following the source's own structure as the
    teardown recorded it, including which lines repeat.
  - Keep the hook line where the source put it, and repeat it as often as
    the source repeats it. A chorus that lands once is not a chorus.
  - Say-lines still carry the source's meaning in the source's order; you
    are not writing a jingle over the story, you are writing the story AS the
    song, which is what the source did.
  - Add one line at the top of WHAT TO SAY: `FORM: SUNG` (or RAPPED), plus
    the style in a short phrase — genre, tempo feel, the vocal. Downstream
    the song is generated from these words, so an absent style line means
    somebody guesses.
  - Do NOT also write a spoken version. A sung piece has one script.

A sung source that produces a spoken brief has lost the format that made
it worth swiping — the failure this section exists to prevent
(2026-09-02).

## WHERE EVERYTHING COMES FROM

Every slot has exactly one source. Never fill a slot from anywhere else,
and never from imagination.

- **The character's body, face, hair, makeup, wardrobe, jewelry** — the
  teardown record's Character & Setting profile. It was written so someone
  who never saw the video could re-create the person; that someone is now a
  generator.
- **Who fills each role** — the injection's CHARACTERS section. Where it
  names a real identity, that person appears only through the machine's
  banked, approved references for them. Where it left a role unassigned
  (`[SLOT: identity_anchors — role]`), you cast: an original character in
  the observed subject's mold — never the source creator themself, never
  anyone recognisable.
- **The character's voice** — the teardown record's voice observations:
  register, energy, pace, accent cues. Written as a persona in the mold,
  never an imitation of the source creator's voice.
- **The places** — the teardown record's setting and room inventory,
  location by location.
- **The camera** — the teardown record's camera work: phone or high-res,
  front or rear, how it is held or propped, the framing habits.
- **What happens in each frame** — the teardown record's Visuals column,
  carried through the injection's SCENES section, which already wrote the
  production instruction for this route, scene by scene.
- **Every spoken line** — the transformed scripts, word for word; the
  opening lines and scroll stoppers — the hook set.
- **Every caption** — the teardown record's On-Screen Text column,
  verbatim.
- **The product's name** — the product file. **The product's appearance** —
  the real packshot, as a reference image, never words.
- **Every price, claim, offer and guarantee** — the offer and product
  files, and nowhere else.
- **Any styling detail, B-roll lookalike character, or voice register** —
  the spice sheet, cited. The spice sheet never changes what is said or
  the offer; only how a beat looks, sounds, or who fills a B-roll moment.

# THE SHAPE

The piece block first — aspect and resolution, declared ONCE and never
again — then six locked blocks (cast, world, camera, product, product lock,
composition), then the openings, then the scenes. Each concept:

```
# ⟨concept name — short, the way you'd say it in conversation⟩

⟨One to three sentences: the core idea this concept runs on, pulled from its
own material.⟩

## THE PIECE

**Aspect:** ⟨the aspect every still and every clip in this piece carries —
one value, declared here and nowhere else⟩
**Resolution:** ⟨the resolution every still and every clip carries — one
value, declared here and nowhere else⟩
**Style:** ⟨the one grade sentence, the same words in every frame of the
piece — the camera block's own grade, in a single line the machine can
carry into a prompt⟩

**These three are never written on a scene.** A scene that restates the
aspect, the resolution or the grade is a scene that will disagree with its
neighbours the first time one of them is edited.

## THE CAST

**⟨CHARACTER NAME, in caps — an original name, never the source creator's⟩**
— ⟨age⟩, ⟨build⟩, ⟨skin tone and texture — always natural, visible pores, no
beauty-filter look⟩, ⟨face⟩, ⟨hair — colour, length, how it is worn⟩,
⟨makeup, if the record shows any⟩. An original character resembling no real
person.
Load-bearing: ⟨any body part a frame depends on, and the state it is in —
named because the shots show it close⟩.
**Voice:** ⟨the persona paragraph the voice station speaks from — age,
register, energy, pace, accent character, from the teardown record's voice
observations⟩.
**Outfit:** ⟨every garment, colour, material, fit, sleeves, hair, jewellery
— the teardown record's wardrobe, and only that⟩.

## THE WORLD

**⟨LOCATION NAME, in caps⟩** — ⟨the place written so it can be generated
from this text alone: the surfaces, the furniture, where the window is and
what the light is doing, the believable clutter — the teardown record's
setting and room inventory, described sharper, never relocated, never added
to⟩.

## THE CAMERA

⟨One paragraph, from the teardown record's own camera character: phone or
film, how it is held or propped, framing, colour, grain, skin texture — with
the negatives spelled out: no cinematic grading, no studio light, no beauty
retouching.⟩

## THE PRODUCT

⟨The product's exact name from the product file.⟩ Every job with the product
in frame carries the real packshot as a reference image, and the render must
match it, label crisp and legible. Nothing about its label, shape or colour
is generated from words.

## PRODUCT LOCK

⟨Every scene the product appears in, listed by scene number, with the
exact label phrase from the product file copied verbatim and the
instruction: "no garbled text, no morphing, product identical to the
reference packshot." A scene with no product in it does not appear in
this list.⟩

## COMPOSITION

⟨For every scene, the measured frame the character or product must
occupy — subject at ⟨L–R⟩% width, ⟨T–B⟩% height — read from the teardown
record's own Visuals column, so a generated frame lands where the source
frame did, not wherever looks nice.⟩

## WHAT TO GENERATE

### The openings — generate every hook in the set

**Opening 1 · Control**
**Shot:** ⟨the control's scroll stopper, copied from the hook set — the
frame itself in the third person: the character by name, the place by its
world block, what fills the frame⟩
**Say:** ⟨the spoken line, word for word from the hook set⟩

![Opening 1](—)

…every hook, control first, each variation under its own name.

### The scenes

**This route generates video, not stills.** A scene is a clip that has to
exist, described so it can be made — never a picture described so it can be
rebuilt.

### A SCENE IS A PARAGRAPH — AND TWO FRAMES (ruled 2026-09-18)

the owner, that day: *"the scenes are not generated with detail — that is what
causes the poor scene output and frames within them; there is no clean
voice-over — shooting line by line comes out choppy. Fewer scenes, more
frames within the scene describing what happens, then the end of the scene;
audio in each scene — each section reads as a paragraph, a few sentences."*

So the unit is the scene, and a scene is:

- **one setting** — a scene never changes place;
- **one section of the argument** — one of the nine, named;
- **one PARAGRAPH of voice** — a few sentences, the whole continuous run of
  speech, written once. Not a line. The voice station speaks the piece as
  ONE continuous read and chunks it per scene, so the paragraph is the unit
  of the performance as well as of the picture;
- **ONE clip**, with exactly **TWO stills**: a FIRST FRAME, written in full,
  and a LAST FRAME, written as a delta from it;
- **BEATS** between them — what happens across the clip, one line each, one
  verb each. **A beat is not a picture.** It is a timed instruction inside
  the clip, and its timestamps come from the voice track, never from you.

**Fewer scenes, more beats.** A script that used to come out as eighteen
scenes of the same person saying consecutive sentences is a handful of
scenes, each playing out a whole thought. Every scene split is a new
generation, a new chance for the face, the room and the light to drift, and
a new seam in the voice.

**Cutaways are not scenes.** When the source cuts to a bottle in a hand or a
diagram, the voice does not stop — the picture changes *over* a take that
keeps running. An insert is written as a beat inside the scene it covers, or
listed under it for the edit. It is never its own scene.

**A scene is `to camera` when the speaker is on screen saying the
paragraph.** Then its audio is its own slice of the one continuous track,
and the clip lip-syncs to that slice. A scene where nobody is on screen is
silent: the same paragraph plays over it at the edit.

**Two things the world block must not sand off, because they are usually the
mechanic rather than the set dressing.**

**The place is doing work.** A format built on a credentialed person
disqualifying things borrows its authority from where they are standing — the
shop floor, the counter, the wall of stock behind them with its prices and its
slightly-out-of-line boxes. Take that away and put them against clean
shelving in flat even light and the shot reads as a stock photo, which is the
one thing an authority format cannot afford. Write the room as the real,
ordinary, commercial place it is: crowded, coloured, lit by whatever is on the
ceiling, with its own business visible behind.

**Named products are shown, not blanked.** When the script says a competitor's
name, the hand holds that competitor, label square to camera and legible. The
recognition IS the argument — the viewer has that exact bottle in their own
bathroom, and that is why the beat lands. A brief that writes "plain
unlabelled bottle, no logo" while the line says the name has removed the
mechanic and left the sentence: the source's whole hook works because you know
the blue tin on sight.

**Never name the camera. Describe what the shot looks like.**

A generator has no concept of a camera it is looking *through* — everything you
name is an object it can put *in* the picture. Write "shot on a phone on a
tripod at chest height" and it renders a phone on a tripod, standing in the
room, in the middle of the ad. Write "handheld", "gimbal", "35mm", "webcam",
"lit with a softbox", and the same thing happens with those.

Say the result instead: how it is framed, how high, how flat the light is, how
much depth there is. "Framed square on at chest height, flat even overhead
light, little depth" gets the phone-ad look with no phone in it.

And in any scene with a person talking to camera, say the negative out loud:
**no camera, no phone, no tripod, no lights, no microphone, no filming
equipment in frame.** The one place this does not apply is a scene whose
subject genuinely is someone filming — then the gear is the content.

**The rule that governs all of it: never describe anything a reference
already shows.** The cast block holds the face; the world block holds the
room; the FIRST FRAME holds the framing, the blocking and the light. The
LAST FRAME therefore names ONLY what changed, and a beat names only what
happens. Re-describing tells the model to rebuild, which is the generation we
are avoiding, and it is how a lead ends up wearing another character's
jacket.

So: **the cast block and the world block are written once, at the top, and
never repeated in a scene.** A scene names the character; it does not
re-describe them.

```
**Scene ⟨n⟩ · ⟨THE SETTING, by its world-block name⟩**

**Section:** ⟨this scene's section label, from the teardown record's own
section list — or its plain description if the record flagged it as a
candidate⟩ · **Technique:** ⟨the technique this scene runs, as the expansion
pass's depth ledger named it⟩ · **Delivery:** ⟨this scene's delivery dials,
from the spice sheet's block for this section, spelled exactly as the
delivery dials spell them: `humor · delivery style · register · pacing`,
then `world: …` and `avoid: …` where the spice sheet filled them. A dial the
spice sheet left `[UNFILLED]` is written `unfilled` here — never guessed, and
never chosen at this stage.⟩ · **Emotion:** ⟨one feeling the viewer carries
during this scene⟩ · **Outcome:** ⟨where the viewer lands at this scene's
end⟩
**Setting:** ⟨the world block this scene plays in, by its name — one place,
for the whole scene⟩
**Who:** ⟨character names only⟩ · **To camera:** ⟨yes | no⟩

> **Voice:** "⟨THE PARAGRAPH — the whole continuous run of speech for this
scene, every sentence of it, as one block, word for word from the script. Do
not break it where the source cuts to an insert; do not split it into lines.
Its punctuation is the pacing direction.⟩"

**FIRST FRAME**
**Subject:** ⟨who is in it, by name, and what their body is doing — never a
re-description of the face⟩
**Composition:** ⟨how it is framed and how much of the frame each thing
occupies⟩
**Action:** ⟨the single action visible at this instant⟩
**Location:** ⟨the world block, by name, plus the one detail that anchors
it⟩
**Style:** ⟨the piece's grade sentence⟩
**Camera:** ⟨the result — how high, how close, how much depth. Never a
device.⟩
**Lighting:** ⟨where the light comes from and how flat it is⟩
**Refs:** ⟨the references this frame is built from, in order — the cast
sheet, then the packshot where the product is in frame, then the style
frame. A reference beats a description.⟩

**Beats**

- **B1** · **At:** ⟨the span from the voice timing sheet, e.g. 0.0–2.54 —
  or leave this out and the machine fills it from the track⟩ · **Do:** ⟨ONE
  verb, one action⟩ · **Camera:** ⟨only where the camera moves; otherwise
  `held`⟩ · **Over:** "⟨the words from the paragraph playing over this
  beat⟩" · **Beat:** ⟨the feeling this moment carries⟩
- ⟨…one line per beat, in order, as many as the paragraph has moments and
  never more than fifteen⟩

**LAST FRAME**
**Camera:** ⟨`same` · `push-in` · `new angle` — whether the camera has moved
on the face by the end of the scene. This one word decides which door makes
this frame, so it is never left out: a push-in or a new angle rescales the
face and needs the door that holds a face through a move.⟩
**Change:** ⟨what is different from the FIRST FRAME, and nothing else. Never
the room, the wardrobe, the light or the framing again.⟩
**Beat:** ⟨the feeling the scene ends on⟩

**On screen:** ⟨the caption, verbatim from the teardown record's On-Screen
Text column — or: nothing⟩
**Hold:** ⟨anything that must not change from the previous scene — the same
skin, the same light, the same crop. Continuity is the proof; a different
angle on a before-and-after reads as a different person.⟩
```

**No length, anywhere.** A scene has no duration, no start and no end time,
and neither does a beat unless the voice track has already been made and you
were handed its timing sheet. The paragraph decides how long the scene is;
the machine reads that off the track and cuts the clip to it.

**Aspect and resolution are the piece's**, declared in THE PIECE and never
on a scene.

**Delivery stays on the first line.** It is one continuous line with
Section, Technique, Emotion and Outcome — it never starts a line of its own,
because two labels at the start of a line are two labels nothing can tell
apart.

This brief is where Section, Technique, Delivery, Emotion and Outcome are
authored — from the teardown record's per-scene contract, the depth ledger
that named the technique and the spice sheet that named the dials. The scene
prompts copy these lines verbatim; they never re-derive them, and they never
choose a dial.

**Count the scenes against the argument, not the clock.** A scene per
section, and a second one only where the section genuinely moves somewhere
else. If your scene count is anywhere near the number of sentences in the
script, you have split paragraphs into lines — merge them back and write the
difference as beats.

## THE LOCKED BLOCKS — AND WHAT GETS GENERATED FROM THEM

**THE PIECE is the first of them** (2026-09-18): aspect, resolution and the
one grade sentence, declared once for everything the piece produces. Every
station reads them from there — the stills door resolves a size from the
aspect, the clip door carries the same aspect and resolution, and the edit
that makes a last frame holds both. A scene that restates any of the three
is a scene that will disagree with its neighbours.

Written once per concept, before any frame. These blocks are the next
stage's input: the cast station generates each character's sheet and
identity images from THE CAST — if a character sheet needs to be generated,
it gets generated there, from your block — the voice station takes its
persona from the Voice line, the scenes station pastes THE WORLD and THE
CAMERA into every job, and the product's packshot rides as a reference. So
the blocks are the consistency of the whole piece: a frame never restates
what a block holds, and a block never leaves a gap a station would have to
improvise around.

**THE CAST — who exists.** One block per person on screen, filled per the
map above: the injection's CHARACTERS section decides who fills each role;
the teardown record's profile supplies the physical truth. A cast character
is an original person in the observed subject's mold — the same age range,
the same presence, the same wardrobe — never the source creator themself,
and never anyone recognisable: this document must not direct the generation
of any real person's likeness beyond the machine's banked, approved
references. Each block, in concrete physical detail: age, skin tone and
texture, face, hair, makeup, build; always natural skin with visible pores,
no beauty-filter look. Name the character in caps, and that name is how
every frame refers to them. **Load-bearing body details:** before writing
the cast, read your own shot list — any part of the body a frame depends on
gets named in the block, with its state. A demo shown close on a body part
the block never described gets regenerated differently in every scene, and a
demo on an inconsistent body is not a demo. **The Voice line** is the voice
station's whole input — a persona paragraph, not a casting note. **Wardrobe
lives in the cast block:** every outfit the source has, garment by garment,
and only those. Anyone else on screen gets a smaller block, named by their
role in the story — THE FRIEND, THE PERSON WHO SENT IT.

**THE WORLD — where it happens.** One named block per distinct location in
the source, written so the place can be generated from the text alone: the
surfaces, the furniture, where the window is and what the light is doing,
the believable clutter. Outdoors works the same way. The locations are the
source's: same places, described sharper, never relocated somewhere easier,
never added to.

**THE CAMERA — the realness dial.** One paragraph that decides whether this
looks like a phone or a film, taken from the teardown record's own camera
character, not from taste — with the negatives spelled out: no cinematic
grading, no studio light, no beauty retouching. One camera per concept;
scenes never argue with it. Making a self-shot format look like a film is
the same mistake as relocating its opening — it deletes the reason the
source worked.

**THE PRODUCT — real packshot, never described.** The product's appearance
is never generated from words. The block names the product — its exact name
from the product file — and states the requirement: every generation job
with the product in frame carries the real packshot as a reference image,
and the render must match it, label crisp and legible. If no packshot exists
at generation time, that is a stop for the owner, not a licence to describe
one.

**PRODUCT LOCK** — every frame the product touches, named, so the generation
bench and QC both read the same checklist.

**COMPOSITION** — the measured frame per scene, read from the teardown
record, never invented — what keeps a scene from looking right while landing
somewhere the source never did.

## EVERY OPENING GETS A PICTURE

Openings are written as numbered units — `**Opening 1 · Control**` — in the
same shape the scenes use. This
is not cosmetic: the picture stage finds what to illustrate by matching that
shape, so an opening written any other way silently gets no picture.

The opening is the shot being tested and the most important image in the
document. A brief where every frame has a picture and no opening does is
backwards — the openings are all the same moment shot differently, which is
exactly the difference a picture carries and a paragraph does not.

## THE SHOT LIST IS AUDITED AGAINST THE SOURCE BEFORE YOU FINISH

Last thing before you return anything. Walk the teardown record's rows in
order against your scenes, and satisfy yourself of these things:

1. **Every shot in the record has a frame.** None dropped.
2. **Every frame is accounted for** — either by a shot in the record, or by
   a line in the script that runs past where the source ends. A frame with
   neither behind it is invented; delete it. On an organic source most
   scenes will be script-backed, and that is correct: the post was the hook
   and the script is the ad.
3. **The script is covered to its last line.** If your final frame lands
   before the script does, the brief is unfinished.
4. **Each frame is doing what its source shot did** — same place, same
   action, same construction. Ours substitutes the brand, never the
   behaviour. If the source is in a shop, ours is in a shop. If the source
   applies something to the face, ours applies something. If the source is a
   keyed talking head, ours is keyed.
5. **The blocks cover the scenes.** Every body part a scene shows close is
   named in the cast block; every place a frame uses has a world block;
   every outfit written on a frame exists in the cast block; every speaking
   character has a Voice line. A frame that needs something the blocks do
   not hold means the block is unfinished, not the frame.

Where the source's own product had to be swapped for ours, the *action*
still holds: a demo is still a demo, a reveal is still a reveal, a reaction
shot is still that reaction. **Substituting the product never licenses
changing what the person is doing.**

If a source shot genuinely cannot be reproduced with our product — the
mechanic does not exist for us — say so in one line under that frame and
keep the frame. That is a finding for the owner, not something to quietly
paper over with a different shot.

## THIS DOCUMENT IS SENDABLE AS IT STANDS

**Nothing unresolved reaches this document.** Not a `[SLOT: …]`, not a
bracket, not a note to whoever fills something in, not a checklist at the
top. It goes to the generation bench and it has to read as finished.

Upstream stages write `[SLOT: …]` wherever a fact was needed and the brand
files did not hold it. That is the anti-invention rule working, and you do
not undo it. **You never fill a slot in.** What you do instead depends on
what kind of slot it is, and there are only two kinds.

**A slot asking who someone is — cast it from the bank, then invent.** On
this route, who someone is is a decision this brief makes — but it is not a
free one when the brand keeps a cast. Read `{casting}` first: it holds the
people this brand has already built and approved, each with a role, a lane, a
physical description and generation handles that other assets are already
using. **If one of them fits the role, cast them: use their name, and copy
their description into the block unchanged.** That is what banked means. A
brief that reinvents a banked person breaks the face across every asset that
has already shipped with it, and the brand ends up with three different women
answering to the same job.

Only when the bank holds nobody for the role do you write an original
character in the observed subject's mold, the way THE CAST says — and say in
the block that the bank had no one, so whoever reads it knows a new person is
being introduced rather than an existing one forgotten.

Two things stay true either way. A frame is never held up waiting for a name.
And **no real person is ever the answer** — not the source creator, not one
of ours. Where the brand's own footage carries a role, the injection will have
said so and that role is cut, not generated: a banked synthetic person is for
the beats the footage does not contain. Never give a banked character a name
that could be mistaken for a real person the brand works with.

**A slot asking for a brand fact — cut the line.** A price, a promotion, a
date, a guarantee wording: if it is not in one of the files above, the
sentence carrying it does not appear. Say nothing rather than something
unapproved.

There is no third option. **Generalising a slot is filling it.** Turning
`[SLOT: current promotion]` into "the bundle deal" or "today's sale" has
announced a promotion nobody approved, in a document that generates a voice
saying it out loud.

**Where the idea came from is credit, not a gap.** If naming the source is
useful, it goes at the end as one line of inspiration — "built from a format
that ran on [platform]" — never as a task, never as a blank to fill.

## Naming and describing the concept

**The `# ` heading names the concept.** Short, the way you'd refer to it in
conversation — not a slogan, not a headline.

**Under the heading, one to three sentences describing what this concept is** —
the core idea it runs on, in plain language. Pull this from the concept's own
material (the placement plan, the injection, the stage-4 passes); never invent
a rationale that isn't already there. It's the only place in the document
where the "why" appears, and it stays to one paragraph.

## The opening section — the part that gets mangled

Every hook in the hook set goes in, control first, then each variation under
its own name. For each one, two labeled lines — never blended into one
paragraph, never left for the stations to infer:

- **`Shot:`** the scroll stopper — the frame itself, exactly as the hook set
  describes it, in the third person: the character by name, the place by its
  world block, the action.
- **`Say:`** the spoken line, word for word. If the format has no speech,
  label it **`Card:`** instead and give the on-screen text.

A `Say:` line is a voice take; a `Shot:` line is a picture. The two must
never blend: `Shot:` never contains a spoken line.

**The scroll stoppers are already written. You are copying them, not writing
them.** The hook set hands you each one as a described frame. Reproduce that
frame — the angle, the distance, where the subject is, what is in shot, the light.

This is the single thing that goes wrong most. On one run the source was a
woman lying on a towel on a beach in midday sun, the hook set said exactly
that, and the brief opened on a bathroom counter in the morning instead. A
frame was then generated of the bathroom, and the entire reason the source
stopped anyone scrolling was gone. **The scroll stopper is the swipe.** It is
the most valuable thing in the teardown and the least replaceable.

So:

- **Never relocate the opening.** If the source's first frame is outdoors, the
  opening is outdoors. Do not move it somewhere easier to generate.
- **Never substitute a product shot for a scroll stopper.** A product held up
  to camera is not an attention device; it is what the source spent its
  opening earning the right to show.
- **Never paraphrase it into a summary.** "Relaxing outside" is not the
  frame. The angle, the distance and what fills the frame are the frame.
- **Scene 1 IS the control's scroll stopper**, written out
  as a frame with its wardrobe line. The two must describe the same picture.
  If Scene 1 and the control disagree, Scene 1 is wrong.

Check the teardown record if a scroll stopper is unclear — it holds the source
shot by shot, and the opening frame is in its first row. All hooks get
generated; nobody picks.

## THE UNIT IS THE SCENE — AND THE SCRIPT DECIDES HOW MANY

**Every scene exists because a section of the argument calls for it, and
every beat inside it exists because a moment in that scene's paragraph calls
for it.** No scene without a thought to carry; no beat without something
that happens.

Two different sources come through here and they are not the same job.

**A source that is already a finished ad** is a format to replicate. Its
shots are the plan. Transcribe them: the teardown's Visuals column, split
where a row holds several shots — a row describing a person in one place,
**a cut** to a second person, and **a close-up** of an object is three
shots — and that count is your count. Writing more means inventing footage
nobody filmed.

**A source that is an organic post** is a hook, not an ad. It is a few
seconds long and the ad you are briefing is not. The close pass hands you
the full script; **your shot list covers all of it, to the last line.** The
source's shots cover the opening and then run out, and where they run out
you keep going — the script is still talking, so there are still scenes.

### Count against the script, not the clock

Before writing, read the script the close pass produced and count what it
needs: every section of the argument it moves through, every place it goes,
every held moment. **The sections are your scene count; the moments inside
each paragraph are its beats.** Then check the teardown: wherever the source has a shot for that
moment, the frame is the source's shot. Wherever it does not, the frame
comes from what the line needs — plainly, one shot, nothing invented around
it.

Finishing at the source's runtime when the script runs longer is the failure
this rule exists to stop. A run on 2026-08-26 briefed a nine-second post as
a nine-second ad: seven scenes, no body, nothing after the hook. The script
was there and the shot list stopped short of it.

### Why the opposite rule exists too

A run on 2026-08-25 turned a source describing eighteen shots into a brief
of forty-one scenes, on a source that was already a finished ad. The extra
scenes had nothing to describe, so each was filled with plausible invention:
a wardrobe change nobody called for, a prop nobody filmed. **Every fault in
that brief lived in a frame that should not have existed.**

Both failures are the same mistake — the frame count coming from somewhere
other than the script. Invented frames are not extra value; a shot list that
stops before the script does is not restraint.

### What "every shot" includes

If the source cuts to a shop, you have a shop. If it cuts to B-roll of
somewhere abroad, you have that B-roll. If it goes back to the keyed talking
head for one line, that is a frame too. **A shot you find awkward to
generate is still a shot** — describe it and let the owner decide. Never
silently drop one because it is inconvenient; a dropped shot is as wrong as
an invented one, and it is the reason a swiped format stops working.

### Do not write a transcript at the end

The finished brief ends with every spoken line laid out in order. **That
section is assembled from your `Say:` lines automatically — you do not
write it.** Writing your own would produce a second version of the script
that drifts from the frames. Put each line where it belongs, on its frame,
and the transcript takes care of itself.

## HOW THE FRAME IS PUT TOGETHER

A frame is not always one plain camera shot, and when it is not, **say so
first** — this is the part that makes a format reproducible. Read the
teardown record's own description and carry the construction across:

- **A keyed or composited frame** — the character is cut out against footage
  that is not the room they are in, laid over other material. Say what they
  occupy, and what is playing behind them.
- **Picture-in-picture** — the talking head in a corner over a full-frame
  plate. Say which corner and roughly how much of the frame it takes.
- **Split screen** — say how it divides and what is on each side.
- **A screen recording** — a phone or a browser being captured. Say what is
  on the screen.
- **A plain shot** — say nothing about construction; just describe it.

Formats live or die on this. Reproducing the words of a keyed talking-head
opener as a plain selfie throws away the thing that made it work.

## Every scene, slot by slot

The scene block above is the shape; these are the slots inside it that get
written wrong, and what right looks like.

1. **The header** — `**Scene N · THE SETTING**`. A number and a place. **No
   span, no duration, no TYPE letter**: a scene's length comes from its
   paragraph, and its kind comes from its `To camera:` line.
2. **`Source:`** where it applies — the source beat this scene replaces,
   quoted from the teardown record's Visuals column, shortened to its first
   few words. Anyone can then read down the two columns and see whether the
   brief still tracks the video it came from. A scene that is script-backed
   past where an organic source ends writes `Source: none — script-backed`
   and nothing else.
3. **`Voice:`** the paragraph, in the third person nowhere — these are the
   words the character actually says, word for word from the script, every
   sentence of the scene's continuous run of speech in one block. It is the
   voice take: it goes to the voice station exactly as written and its
   punctuation is the pacing. **Never split it into lines**, never write an
   ellipsis (it becomes a literal gap and reads as choppy), and never fold a
   spoken word into a picture slot.
4. **The FIRST FRAME** — the only place in a scene where the picture is
   described in full, and it is written in the stills order the door itself
   recommends: **subject · composition · action · location · style · camera
   · lighting**, then its references. Write it as if nothing before it
   existed: the character by name, the place by its world block, the body in
   full. Continuation shorthand — "same as before", "back out to the seated
   wide" — is a reference to something the generator cannot see.
5. **The wardrobe is the cast block's, and it is not restated per scene.**
   The FIRST FRAME names the character; the cast block holds the clothes. A
   change of clothes is a change of time or place and must be visible in the
   story — if you cannot point at the moment in the source where the
   wardrobe changed, it did not change.
6. **The beats** — one line each, one verb each. A beat says what HAPPENS,
   never what is in frame: "turns the forearm over", not "the forearm is
   turned over". The camera is named only where it moves; otherwise `held`.
   `Over:` carries the words from the paragraph that play across that beat,
   copied out of it, so the timing sheet can find them. Two actions joined
   by "and" are two beats.
7. **The LAST FRAME** — a delta from the first and nothing else. If you find
   yourself writing the room, the light or the framing again, the scene is
   being re-generated instead of moved.
8. **`On screen:`** the words burned into the picture, copied **verbatim**
   from the teardown record's own On-Screen Text column, in quotes. It is
   very often not the same as what is being said — it lags, it shortens, it
   stops mid-sentence. Copy what the source actually put on screen; never
   tidy it into a full sentence and never re-derive it from the spoken
   words. Nothing on screen is written `On screen: nothing`, which is a real
   instruction: leave the picture clean.
9. **`Hold:`** what must not change from the scene before — the same skin,
   the same light, the same crop.

**A scene's sound.** A `to camera` scene needs no sound slot: the paragraph
is its audio, as a slice of the one continuous read, and the clip lip-syncs
to it. A silent scene carries the same paragraph over it at the edit, and
anything else it should be heard to do — the thing being opened, the water
running — is written into the beat that does it, with the negatives spelled
out: no music, no other dialogue.

## THE FIRST FRAME STANDS ALONE — THE LAST ONE DOES NOT

**A scene's FIRST FRAME becomes its own generation job, run by something
that has read nothing else.** So it names the character, the place and what
the body is doing, in full — every time, even when nothing has changed since
the scene before it.

**Its LAST FRAME is the opposite job.** That one is an EDIT of the first
frame, handed the first frame itself, so it names only what changed. Writing
the room, the wardrobe or the framing there tells the model to rebuild them,
which is exactly the drift the two-frame shape removes.

Continuation shorthand is the failure. "Stays exactly where they are",
"same as before", "back out to the seated wide", "same frame" — these are
references, and there is nothing there to refer to. A frame reading "stays
exactly where they are, hands behind the head" will put the character
anywhere at all, because the only thing the line actually said was "hands
behind the head".

Write the FIRST FRAME as if nothing existed before it: ⟨the character's
name⟩, ⟨the place, by its world block⟩, ⟨the body, in full⟩ — "lying on the
towel on the sand, hands behind the head, nothing moving." The identity
details live in the cast block and are never restated — the name carries
them — but the name, the place and the action are restated in full on every
scene's first frame.

**Where the camera goes is not what the picture shows.** How the camera is
propped or held is part of the camera block's character — but in a frame it
belongs in the `Camera:` slot, after the picture is described, never as the
opening words. Lead with what is in the shot.

## THE FRAME HAS TO BE SEEABLE

**This applies to the shot list only — never to the opening.** The hooks and
their scroll stoppers arrive already written and you copy them exactly, as
the rule above says. Sharpening a scroll stopper is rewriting it. If the
opening reads flat, that is a finding about the hook set, not licence to
improve it here — say so and move on.

For the body frames, which you do write: a frame description is not an
inventory. A bare list of what is in the room gives a generator nothing to
produce. Write the frame so something that has never seen the source can
make it. You have the teardown record — the source shot by shot — so the
detail is there to be used, not invented.

For every FIRST FRAME, and for every beat, name at least one of:

- the specific physical detail that makes it real — the state of the thing
  in the character's hands, the texture the shot is about, the mark it leaves
- what the light is doing — hard summer light, flat white light, one window
  on the left
- the movement that carries the beat — the tug, the pinch, the hand stopping

**This is description, not invention.** You are describing the frame the
source already earned, in sharper focus. You are not adding a prop, a
location, a person, or an action that was not there. If you find yourself
writing a shot the source did not have, stop — that is a different job and
it breaks the swipe.

## THE CONVERGENCE CHECK

Before this pass ends, find the single most important beat in the concept —
the one the whole thing is built to deliver.

Read that scene's three things together: the beat that carries it, the
sentence of the `Voice:` paragraph playing over that beat, and what the
frames show it landing on.

They must point at the same thing at the same moment. Picture, sound and
words converging is what carries a beat into the part of a viewer's
attention where it means something. The same three pulling in different
directions is where briefs go slack.

If they diverge at that beat, fix the beat — not by inventing, but by
deciding which of the three is wrong and bringing it back to the other two.

# WHAT DOES NOT GO IN

- No source link, no reference lines or timestamps into anyone else's footage.
- No real person's name or likeness, anywhere — no creator, no celebrity,
  nobody recognisable — beyond the machine's banked, approved references
  the injection's CHARACTERS section calls for.
- No angle bracket, no `[SLOT: …]`, no unfilled anything.
- No model names, no generation settings, no costs, no station mechanics.
  The brief says what to make; the machine decides how.
- No "Don't say" list, no compliance language, no guarantee wording. That is
  our review before anything ships, not something the page needs.
- No explanation of why anything was chosen, changed, cut or kept, beyond the
  one paragraph under the concept name.
- No runtime totals, beat counts or budgets.
- No sign-off, no thanks, no lengthy introduction.

# THE CLOSE

Nothing follows the last frame. This document goes to the generation bench,
not to a creator, so there is no notice and no questions line — it ends when
the shot list does.

# TONE

Short sentences. Every frame reads in three seconds flat: what the shot is,
what it sounds like, what the character wears, what is on screen, what is said —
nothing to parse, nothing left to a set that does not exist.

# WHAT AMPLIFICATION MEANS HERE

You may make the same thing land harder. You may not make a different thing.

**Free — how it is delivered:**

- the rhythm and syntax of a spoken line
- how vividly a frame or a block is described
- which physical detail gets named

**Locked — what is being said:**

- the beats, their order, and the structure they sit in
- every claim, number, price, offer, guarantee and timeline
- which product does what, and what is in it
- who is on camera — the observed subject's mold — and what they are wearing

The test: if a change alters what a viewer **learns**, it is out of scope.
If it only alters how hard that lands, it is the job.

---

## NOTHING IN THIS PROMPT IS CONTENT

As the top of this prompt says: every ⟨angle bracket⟩ is a slot, the map
says which input fills it, and the handful of plain examples in the rules —
a beach, a shop, a body part, a pronoun — are the shape of a rule, never the
content of your brief. The subject may be any age, any gender, anywhere,
selling anything. Who is on camera comes from the injection and the teardown
record — the mold, never the likeness — and what is sold comes from the
product file.

**And the variables are agnostic too.** Nothing that gets filled in at run
time may name a brand, a product, a category or an avatar: that detail
arrives only through the variables above, resolved from that brand's own
folder. A rule that cannot be written without naming the brand belongs in
the brand folder, not in this prompt. This machine is meant to run on every
brand we own; anything that only makes sense for one of them does not scale.
