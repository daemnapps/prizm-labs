Here are the sections an argument is built from — the only labels a scene
may carry: {sections}

Take this individual video and break it down completely so I can
reverse-engineer it. Break down the scenes, the script, the characters, and
what the characters are doing and how they're doing it — each and every
element individually, timestamped, scene by scene. Go deep. A long,
heavily detailed output is what I want — do not compress or summarize.

You are building a reproduction spec: someone who has never seen this video
must be able to re-create it — the person, the clothes, the room, the shots,
the words — from your teardown alone. If a detail would matter to someone
re-creating the video, it belongs in your output.

**Describe the subject in front of you, not a default.** Every example in
this prompt is illustrative only — an age bracket, a garment, a style
reference — and none of them describe the video you are looking at. Take
gender, age, register and aesthetic from what is actually on screen. Never
carry over the framing of a previous teardown, and never reach for the
category's stock subject. A record that describes someone other than the
person in the video is worthless no matter how detailed it is.

**Every video is scenes.** A scene is a section of the asset — one of the
functional phases named in THE SCENE MECHANICS below. A scene has
frames: one frame per distinct visual change, same as the objective
record's rows have always been. Frame is the new name for that row;
nothing about when a new one starts has changed.

**This is observation, not evaluation.** You are recording what is
demonstrably there so it can be analysed later — not judging whether it is
good, not recommending anything, not writing about the brand. Record brand
names when they appear on products in frame, because that is a fact about
the video. Never editorialise about the brand, never assess the product, and
never describe the video as effective or ineffective outside the sections
that explicitly ask for mechanism. **Abstraction happens downstream; your job
is an accurate record.**

Three laws govern everything:

**Accuracy law.** Never guess. If you cannot see or hear something clearly,
write `[UNCLEAR at 0:12]` instead of a plausible guess. Mark anything you
inferred rather than directly observed with `(inferred)`. A confident wrong
detail is worse than a marked gap — wrong details get built into real
briefs.

**Consistency law.** Every element gets ONE name, used identically
everywhere it appears. Every detail cited anywhere in your output must
exist in the objective record. State the age range ONCE, in brackets
(e.g. `[50-55]`), and reuse that exact range everywhere.

**Depth law.** The record's detail demands must never thin the analysis.
Sections 2 and 3 go as deep as the record goes precise: every phase's
"Why it works" names the exact words, visual choice, or pacing doing the
work; every "What it sets up" names the specific next move it enables,
never a generic outcome. If length becomes a pressure, cut nothing —
write longer.

I need four things.

**1. THE OBJECTIVE RECORD**

**Open with one line, labeled `Sound form:`** — SPOKEN, SUNG, RAPPED,
MUSIC ONLY or SILENT, and say which for how much of the runtime. LISTEN
for this; it is not visible on screen. If the words are SUNG or RAPPED,
the piece is a song and its script is lyrics, not narration — say so
plainly in this line, because everything downstream is written from it.
Describing the delivery as "melodic" or "musical theater style" without
naming the form is the miss this line exists to prevent: a sung ad became
a spoken brief that way, and the format that made it worth swiping was
lost (2026-09-02).

Where the form is SUNG or RAPPED, also give: the structure (verse,
chorus, bridge — and which lines repeat), roughly where the hook line
lands, and whether the vocal is one voice or several.

Then a Character & Setting profile:

- Who appears — age range in brackets, physical description, hair
  (color, style), makeup (be specific: what look, what products/effects
  are visible), and voice: accent or nationality cues if audible, energy,
  pace.
- Exactly what they are wearing — every garment with its color,
  material, pattern, trim, and fit ("red beaded dress" is not enough —
  what pattern do the beads make, what's the neckline, what's the
  outline). Every piece of jewelry: rings, bracelets, earrings, watches —
  and the brand if identifiable.
- Style label — name the aesthetic with a real reference point
  ("Dolce & Gabbana-style baroque," "athleisure") rather than a vague
  mood word. If it matches a known style, say which.
- The setting, as it actually is — what kind of space this really
  appears to be (judge from lighting, furniture age and color, finishes —
  don't upgrade an ordinary room into an "upscale" one). Then inventory
  the room: what is on the shelves, cabinets, walls — not just the focal
  props. The whole setting is the set.
- Props — every object that appears, with color/material detail.

Then give me one table with exactly these six columns, in this order:

`Timestamp | Roll | Visuals | On-Screen Text | Transcript | Sound`

- **Timestamp** — start and end, e.g. `0:00 - 0:11`
- **Roll** — what the PICTURE is doing against the words in this row. One
  label, from this list only — it is the first thing production and the
  edit read, because it decides what has to be made and what gets laid over
  what:
  - `A` — **A-roll.** The person whose words we hear is on screen saying
    them. Lips visible, moving with the words.
  - `B-over` — **B-roll over a speaker.** The words carry straight on from
    an `A` row, in the same voice, but the picture has left the speaker to
    show something — the problem, the product, the hands, the proof. When the
    picture goes back to the speaker it is another `A` row.
  - `B-vo` — **B-roll under a voice we never see.** A narrator or a
    voiceover; nobody in the video is ever shown saying these words.
  - `B-silent` — **B-roll with no words at all.** Picture, with only music,
    sound effects or room sound under it.
  - `C` — **a card.** Not footage: a packshot on a plain ground, a title
    card, a full-screen graphic, a screenshot, a text-only frame.
  If the speaker is in frame but the words belong to someone else, or the
  lips are hidden the whole row, it is `B-vo`, not `A` — say who is in frame
  in Visuals. Never leave this column blank and never invent a label.
  For every `B-over`, `B-vo` and `B-silent` row, the Visuals column must
  open with **what the picture is there to show** in three or four plain
  words before the description — `[shows: the problem, close]`,
  `[shows: product in hand]`, `[shows: before and after]` — so the row can
  be re-made as its own shot.
- **Visuals** — only what is in frame, at the same level of detail as the
  profile above: who is there, what they are doing, their facial
  expression and reaction, camera work for this row — shot type, camera
  angle, front-facing or rear camera, phone-grade or high-res — setting,
  props, and effects. Every effect or transition gets its shape, size,
  color, and a canonical name you reuse every time it recurs
  (`Transition-1: pink glowing heart, ~1/3 screen height`). No on-screen
  text in this column.
- **On-Screen Text** — every overlay and caption, word for word, in
  order, separated by `|`. Nothing else in this column. Write "none" if
  there is none. If a text element looks like an app or editor watermark
  rather than intentional content, mark it `[ARTIFACT: …]` — we must not
  copy junk into new videos.
- **Transcript** — exactly what is SPOKEN, word for word. The transcript
  is never the on-screen text — if they differ, the spoken words go here
  and the overlay stays in its own column. Label every line with its
  speaker (`Creator:`, `Doctor:`, name them if named) and, where it
  carries meaning, the tone (`[skeptical]`, `[excited]`). If there is no
  speech, describe the music or sound design in brackets — and if you can
  identify the actual track, name it. If speech is inaudible or garbled,
  mark `[UNCLEAR]` — never fill the gap with the overlay text or a guess.
- **Sound** — everything in this row that is NOT speech, in three parts
  separated by `|`, each written out or `none`:
  `music: … | effects: … | room: …`
  - *music* — is a track playing under this row? Name it if you can;
    otherwise its feel, its tempo in a word, and whether it is rising,
    holding, dropping out or hitting a beat on a cut.
  - *effects* — every added sound, in order, tied to what it lands on:
    `whoosh on the cut in`, `pop on the caption`, `ding as the product
    appears`, `record scratch on her line`. An added sound is one that was
    put there in the edit, not one the room made.
  - *room* — the real sound of the place: tap running, product squeezed,
    a lid clicked, street noise, silence.
  The Transcript column still carries the words and, when nobody speaks,
  the one-line description it always has; this column is where the music
  and the effects are itemised so they can be re-made.

One row per frame — a change of speaker, camera setup, on-screen text, or
**Roll** (the picture leaving the speaker, or coming back) starts a NEW frame; never merge adjacent moments into one frame, and
never merge these columns. A speaker's single sentence that runs across
an `A` row, a `B-over` row and back to `A` is three rows, with the words
split where the picture actually changes. Frames group into scenes at the phase level
in THE SCENE MECHANICS below; this table does not change because of that
grouping.

**2. THE SCENE MECHANICS**

Break the video into its functional phases — the blocks of work, not the
individual rows. Name each phase for what it does to the viewer, not for
what is on screen (e.g. "Visual Destruction & Negative Bait Hook",
"Agitation / Problem Definition", "The Magic Mechanism", "Benefit Stacking
& Objection Handling", "Incentive Escalation", "Scarcity CTA").

Use ONE canonical name per technique: if the detailed analysis calls it
"the vulnerability hook," the phase-level view calls it the vulnerability
hook too — keep the high-level and detailed layers, but never two names
for one thing. Where a technique is an established term from psychology or
direct-response marketing, use the established term.

**Every scene carries a section label** — which part of the argument it
is doing, from the fixed list supplied at the top of this prompt. Use the
section ids exactly as that list spells them. Pick the one it actually
is; do not force a fit. If none of them describes this scene, write your
own plain description of what it is doing and mark it
`(candidate for the bank)` — a finding for a human, never a decision to add
to the list yourself.

**The labels are a vocabulary, not a sequence.** The asset carries whichever
sections it carries, in whatever order, with repeats — read that off the
video, never impose an order on it.

For every phase, give me all four of these as separate labeled lines:

- **Phase name and timestamp range**
- **Mechanical purpose** — one line: what this phase is engineered to do to
  the viewer.
- **Why it works** — the detail. Name the specific thing doing the work:
  the exact words, the visual choice, the pacing, the order. Name the
  technique it belongs to. Say what the viewer feels or concludes. Then
  end the line with the labeled clause `Breaks if cut:` followed by the
  specific thing that fails without this phase — every phase, no
  exceptions.
- **What it sets up** — the next phase this one makes possible.
- **Section:** the label from the list above (or the plain description
  plus `(candidate for the bank)`).
- **The scene contract, as observed** — eight labeled lines, exactly as
  the video plays it, never as it should be: `Duration:` (start–end, from
  this phase's own timestamps) · `Event:` (what physically happens, in
  order) · `Emotion:` (the one feeling the viewer carries through it) ·
  `Outcome:` (where the viewer lands by its end) · `Camera:` (operator
  behavior over the scene — height, distance, movement) · `Staging:`
  (who is where, who moves, who does not) · `Delta:` (what visibly
  changes first frame to last) · `Boundary:` (what this scene does NOT
  do, as observed — no text yet, no product yet, no resolution yet).
- **Elements present** — characters (by the names already fixed in the
  Character & Setting profile) · props and products · words said ·
  on-screen text · sounds · the pain or the proof it shows, if either is
  in it. An element with nothing to report says "none" rather than being
  left out.

Then two more sub-sections:

- **Script beats.** Every line that does real work gets its own entry —
  not a selected few, and a phase with three working lines gets three
  entries. Each entry is four labeled lines, in this order and no other
  shape:

  ```
  Line: "<the words, quoted exactly>"
  Device: <the named technique this line is performing>
  Why it lands: <why it works on the specific audience this video is
  aimed at — name who that is and what they already believe>
  Trigger words: <the individual words carrying the charge, listed>
  ```

  A one-line summary in place of the four is a failed entry. `Device` and
  `Trigger words` are never the same content: the device is what the line
  does, the trigger words are which words do it.
- **Pacing and rhythm.** How often it cuts, how long each phase runs, where
  the tempo shifts, and what each shift is buying.

**3. THE PSYCHOLOGY**

Use the same subsection structure every time, in this order — formats may
add extras at the end, but these six always appear with these names:

- **The thesis** — one line naming the whole psychological play, in quotes
  (e.g. "The Maverick Insider vs. The Stagnant Institution").
- **Character archetype** — who the presenter is being, using established
  archetype language (e.g. "the aspirational self," "the sage") rather
  than invented labels, and the specific signals that build it: wardrobe,
  styling, cadence, eye contact, props. Cite only details already in the
  objective record.
- **Aesthetic archetype** — what the look itself signals, and what it
  borrows credibility from.
- **The setting** — what the location does for believability.
- **The psychological plays** — numbered. Name each one — established
  terms referenced where they exist — then say how it is executed in this
  specific video. End every play with the labeled line `Belief shift:`
  naming what the viewer now believes (or no longer believes) because of
  this play — every play, no exceptions.
- **The viewer's end state** — what the viewer believes, feels, or fears at
  the end that they did not at 0:00.

**4. THE VOICE FINGERPRINT**

The record above says how the speaker *looks and sounds*. This section says
how they **build a sentence** — because a downstream stage writing copy in
their name has nothing else to go on, and copy that gets the argument right
and the voice wrong reads as a brand wearing a person's face.

Every line here quotes the source. No inference, no adjectives about their
"tone" — the mechanics, evidenced:

- **Sentence shape.** Their typical length in words, and whether they speak
  in full sentences or fragments. Quote the shortest complete thought they
  say and the longest.
- **How they open a thought.** Do they front the noun ("Dark, gritty, heavy
  in the hand") or narrate their way in ("The first thing I noticed
  was…")? Quote two openings.
- **Their own nouns.** What do they call the problem, the product, the body
  part — in their words, not the category's. If they name the problem with
  a phrase harsher than a brand would use, quote it exactly; that phrase is
  the most valuable line in the record.
- **Energy and punctuation.** Where do they land emphasis — exclamations,
  repetition, a flat full stop? If they repeat a structure ("my hands, my
  arms, my chest"), quote it; that rhythm is theirs.
- **How they hedge, qualify or withhold.** The exact words they use when
  they are NOT sure, or when they refuse to claim something. Quote it.
- **Their tics.** Connectives, filler, asides, the way they start a
  correction. Two or three examples, verbatim.
- **How they close.** Their actual sign-off, quoted — verdict, thanks,
  question to the audience, or nothing.

**Then one line, labeled `Fingerprint:`** — the voice in one sentence a
writer could hold in their head while writing. Not a compliment about them;
a set of constraints. *"Fragments, noun-first, refuses to claim what they
have not proven, signs off with a verdict."*

**5. THE INDEX**

Close with three short registries:

- **Definitions index** — every named technique and play used above, one
  line each: the canonical name, a one-line definition, and whether it is
  an established term (say from where) or our working label.
- **Element registry** — every recurring visual element (transitions,
  effects, overlays) with its canonical name, shape, size, and color, and
  the timestamps where it appears.
- **Roll sheet** — first, one line of counts: how many rows and how many
  seconds sit under each Roll label (`A` · `B-over` · `B-vo` · `B-silent` ·
  `C`). Then the make-list: every row that is NOT `A`, in order, one line
  each — its timestamp, its label, its `[shows: …]` tag, the first and last
  spoken words it covers (or `no words`), and its length. This is the list
  of shots someone has to go and make besides the speaker; if a row is
  missing from it, that shot never gets made.

Give me a really clean output. I'm going to turn this into a brief that
takes in my brand principles and then creates content for that.
