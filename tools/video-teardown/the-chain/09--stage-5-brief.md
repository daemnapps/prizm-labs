Here are the transformed scripts, one per source format: {stage4_outputs}
Here is the hook set, with every variation and its scroll stopper: {hook_set}
Here is the record of the source video, shot by shot: {teardown_record}
Here is the injection — our script with the characters, the scenes and the
production instructions for this route: {baseline_injection}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here is our language bank: {language_bank}

Write the shot list the AI video machine generates from.

**Nobody is filmed on this route.** Every person, place and shot in this
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
  - Say-lines still carry meaning beat for beat; you are not writing a
    jingle over the story, you are writing the story AS the song, which is
    what the source did.
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

# THE SHAPE

Four locked blocks first — cast, world, camera, product — then the openings,
then the frames. Each concept:

```
# ⟨concept name — short, the way you'd say it in conversation⟩

⟨One to three sentences: the core idea this concept runs on, pulled from its
own material.⟩

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

## WHAT TO GENERATE

### The openings — generate every hook in the set

**Opening 1 · Control**
**Film:** ⟨the control's scroll stopper, copied from the hook set — the
frame itself in the third person: the character by name, the place by its
world block, what fills the frame⟩
**Say:** ⟨the spoken line, word for word from the hook set⟩

![Opening 1](—)

…every hook, control first, each variation under its own name.

### The frames

**Frame 1 · ⟨start–end⟩**

**Source:** ⟨the source shot this frame replaces, quoted from the teardown
record's Visuals column, shortened to its first few words⟩

**Film:** ⟨the picture, in the third person: the construction first if the
frame is built; then the character by name, the place by its world block
plus the one detail that anchors it, and the single action — the injection's
scene instruction for this route, made seeable⟩

**Hear:** ⟨what the clip's audio is — a talking frame: "her line, lip-synced
— nothing else"; a silent frame: the ambience from what is physically in the
frame, with the negatives: "room tone only — no music, no dialogue"⟩

**Wearing:** ⟨the outfit, spelled out in full, word for word from the cast
block⟩

**On screen:** ⟨the caption, verbatim from the teardown record's On-Screen
Text column — or: nothing⟩

> **Say:** ⟨the exact spoken words, in quotes — or: nothing — picture only⟩

![Frame 1](—)
```

## THE FOUR LOCKED BLOCKS — AND WHAT GETS GENERATED FROM THEM

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
frames never argue with it. Making a self-shot format look like a film is
the same mistake as relocating its opening — it deletes the reason the
source worked.

**THE PRODUCT — real packshot, never described.** The product's appearance
is never generated from words. The block names the product — its exact name
from the product file — and states the requirement: every generation job
with the product in frame carries the real packshot as a reference image,
and the render must match it, label crisp and legible. If no packshot exists
at generation time, that is a stop for the owner, not a licence to describe
one.

## EVERY OPENING GETS A PICTURE

Openings are written as numbered units — `**Opening 1 · Control**` — in the
same shape the frames use, each followed by its own image placeholder. This
is not cosmetic: the picture stage finds what to illustrate by matching that
shape, so an opening written any other way silently gets no picture.

The opening is the shot being tested and the most important image in the
document. A brief where every frame has a picture and no opening does is
backwards — the openings are all the same moment shot differently, which is
exactly the difference a picture carries and a paragraph does not.

## THE SHOT LIST IS AUDITED AGAINST THE SOURCE BEFORE YOU FINISH

Last thing before you return anything. Walk the teardown record's rows in
order against your frames, and satisfy yourself of these things:

1. **Every shot in the record has a frame.** None dropped.
2. **Every frame is accounted for** — either by a shot in the record, or by
   a line in the script that runs past where the source ends. A frame with
   neither behind it is invented; delete it. On an organic source most
   frames will be script-backed, and that is correct: the post was the hook
   and the script is the ad.
3. **The script is covered to its last line.** If your final frame lands
   before the script does, the brief is unfinished.
4. **Each frame is doing what its source shot did** — same place, same
   action, same construction. Ours substitutes the brand, never the
   behaviour. If the source is in a shop, ours is in a shop. If the source
   applies something to her face, ours applies something. If the source is a
   keyed talking head, ours is keyed.
5. **The blocks cover the frames.** Every body part a frame shows close is
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

**A slot asking who someone is — cast it.** On this route, who someone is
was never a fact to look up; it is a decision this brief makes. The
injection's `[SLOT: identity_anchors — role]` means no real person was
assigned: write that role's block as an original character in the observed
subject's mold, the way THE CAST says, and the slot is resolved. A frame is
never held up waiting for a name, and no real person is ever the answer.

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

- **`Film:`** the scroll stopper — the frame itself, exactly as the hook set
  describes it, in the third person: the character by name, the place by its
  world block, the action.
- **`Say:`** the spoken line, word for word. If the format has no speech,
  label it **`Card:`** instead and give the on-screen text.

A `Say:` line is a voice take; a `Film:` line is a picture. The two must
never blend: `Film:` never contains a spoken line.

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
- **Frame 1 of the shot list IS the control's scroll stopper**, written out
  as a frame with its wardrobe line. The two must describe the same picture.
  If Frame 1 and the control disagree, Frame 1 is wrong.

Check the teardown record if a scroll stopper is unclear — it holds the source
shot by shot, and the opening frame is in its first row. All hooks get
generated; nobody picks.

## THE UNIT IS THE FRAME — AND THE SCRIPT DECIDES HOW MANY

**Every frame exists because a line or a beat in the script calls for it.
One shot, one frame. No frame without something to carry.**

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
you keep going — the script is still talking, so there are still frames.

### Count against the script, not the clock

Before writing, read the script the close pass produced and count what it
needs: every spoken line, every card, every held beat. **That is your frame
count.** Then check the teardown: wherever the source has a shot for that
moment, the frame is the source's shot. Wherever it does not, the frame
comes from what the line needs — plainly, one shot, nothing invented around
it.

Finishing at the source's runtime when the script runs longer is the failure
this rule exists to stop. A run on 2026-08-26 briefed a nine-second post as
a nine-second ad: seven frames, no body, nothing after the hook. The script
was there and the shot list stopped short of it.

### Why the opposite rule exists too

A run on 2026-08-25 turned a source describing eighteen shots into a brief
of forty-one frames, on a source that was already a finished ad. The extra
frames had nothing to describe, so each was filled with plausible invention:
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

- **A keyed or composited frame** — she is cut out against footage that is
  not the room she is in, laid over other material. Say what she occupies,
  and what is playing behind her.
- **Picture-in-picture** — her talking head in a corner over a full-frame
  plate. Say which corner and roughly how much of the frame she takes.
- **Split screen** — say how it divides and what is on each side.
- **A screen recording** — a phone or a browser being captured. Say what is
  on the screen.
- **A plain shot** — say nothing about construction; just describe it.

Formats live or die on this. Reproducing the words of a keyed talking-head
opener as a plain selfie throws away the thing that made it work.

## Every frame

Eight labeled lines, always in this order, never merged into one paragraph:

1. **`**Frame N · start–end**`** — bold, the word Frame, number, middle dot, span.
2. **`Source:`** the source shot this frame replaces, quoted from the
   teardown record's Visuals column, shortened to its first few words.
   **Frame N replaces source shot N — the order never changes.**

   This line is what makes the brief checkable. Anyone can read down the
   two columns and see instantly whether the shot list still tracks the
   video it came from. Without it, one dropped shot silently shifts
   everything after it by one and the second half of the brief quietly
   stops being the format at all.

   If you find yourself unable to write this line for a frame, that frame
   has no source shot and should not exist — unless it is script-backed
   past where an organic source ends, in which case write
   `Source: none — script-backed` and nothing else.
3. **`Film:`** how the frame is built (above) and then the picture, **in the
   third person**: the character by name, the place by its world block plus
   the one detail that anchors it, and the single action described so a
   generator can produce it — she turns to the window, never "you turn to
   the window". **Never "you" — there is no you.** This document directs a
   generator, not a maker, and a "you" in a Film line is a person the
   machine will put in the picture. It never contains a line she says out
   loud — a spoken line always goes under `Say:`, never folded into the
   direction.
4. **`Hear:`** what the clip's audio is. A talking frame: `her line,
   lip-synced — nothing else`. A silent or b-roll frame: the ambience in
   words, taken from what is physically happening in the frame — the thing
   being opened, the water running, the room — **with the negatives spelled
   out**: no music, no dialogue.

   **Take it from what is physically happening in the frame**, never from
   atmosphere you imagine. The teardown record only describes sound where
   nobody is speaking, so for every other scene you are reasoning from the
   objects and actions already in the shot — not inventing a mood. If
   nothing in the frame would make a sound worth naming, write
   `room tone only — no music, no dialogue` and stop.
5. **`Wearing:`** on every single frame, spelled out in full — garment,
   colour, sleeves, hair, jewellery. Never "as before", never "same as frame 2",
   never "see cast", never left out. A frame with no wardrobe line is a broken
   frame: the picture for it gets generated from nothing and comes back as a
   stranger in clothes the subject does not own.

   **The outfits are the cast block's, and there are only as many as the
   source has.** Write the same outfit, word for word, on every consecutive
   frame until the source itself changes clothes.

   **A change of clothes is a change of time or place, and it must be
   visible in the story.** If you cannot point at the moment in the
   source where she changed, she did not change — repeat the previous
   wardrobe line exactly. Outfits drifting frame to frame for no reason is
   the single clearest sign a brief was invented rather than observed, and
   it reads as slop to anyone who watches it back.
6. **`On screen:`** the words burned into the picture at this moment, copied
   **verbatim** from the teardown record's own On-Screen Text column, in
   quotes. This is the caption the viewer reads, and it is very often not
   the same as what she is saying — it lags, it shortens, it stops
   mid-sentence. Copy what the source actually put on screen; never tidy it
   into a full sentence and never re-derive it from the spoken line.

   If the record shows nothing on screen for this frame, write
   `On screen: nothing`. That is a real instruction — it tells the editor to
   leave the picture clean.

   **A frame can have both a caption and speech at the same time, and most
   of these formats do.**
7. **On its own line, as a markdown quote (`> `):** **`> **Say:**`** followed
   by the exact words spoken in this frame, in quotes — the voiceover,
   nothing else. This line is the voice take: it goes to the voice station
   word for word, and its punctuation is the pacing direction. If nobody
   speaks in this frame, write `> **Say:** nothing — picture only`. Keep the
   leading `> ` always; it is what keeps the spoken line out of the picture
   the frame generates.
8. **`![Frame N](—)`** on its own line.

## EVERY FRAME STANDS ALONE — IT CANNOT SEE THE ONE BEFORE IT

**Each frame becomes its own generation job, run by something that has not
read any other frame.** So every Film line names the character, the place,
and what the body is doing, in full — every time, even when nothing has
changed since the last frame.

Continuation shorthand is the failure. "She stays exactly where she is",
"same as before", "back out to the seated wide", "same frame" — these are
references, and there is nothing there to refer to. A frame reading "she
stays exactly where she is, hands behind her head" will put the character
anywhere at all, because the only thing the line actually said was "hands
behind her head".

Write it as if it were the first frame: ⟨the character's name⟩, ⟨the place,
by its world block⟩, ⟨the body, in full⟩ — "lying on the towel on the sand,
hands behind her head, nothing moving." The identity details live in the
cast block and are never restated — the name carries them — but the name,
the place and the action are restated in full on every frame.

**Where the camera goes is not what the picture shows.** How the camera is
propped or held is part of the camera block's character — but in a Film line
it goes at the END, after the picture is described, never as the opening
words. Lead with what is in the shot.

## THE FILM LINE HAS TO BE SEEABLE

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

For every `Film:` line, name at least one of:

- the specific physical detail that makes it real — the state of the thing
  in her hands, the texture the shot is about, the mark it leaves
- what the light is doing — hard summer light, flat white light, one window
  on her left
- the movement that carries the beat — the tug, the pinch, the hand stopping

**This is description, not invention.** You are describing the frame the
source already earned, in sharper focus. You are not adding a prop, a
location, a person, or an action that was not there. If you find yourself
writing a shot the source did not have, stop — that is a different job and
it breaks the swipe.

## THE CONVERGENCE CHECK

Before this pass ends, find the single most important beat in the concept —
the one the whole thing is built to deliver.

Read its three lines together: `Film:`, `Hear:`, `Say:`.

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
what it sounds like, what she wears, what is on screen, what she says —
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
