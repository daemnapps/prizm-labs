Take this individual STATIC IMAGE AD and break it down completely so I can
reverse-engineer it. This is a single still frame, not a video: there is no
timeline, no scenes, no transcript, no pacing. Break down the frame, the
copy, the subject, and every design decision — each and every element
individually, zone by zone. Go deep. A long, heavily detailed output is what
I want — do not compress or summarize.

You are building a reproduction spec: a graphic designer who has never seen
this ad must be able to re-create it — the subject, the wardrobe, the set,
the crop, the type, the colors, the words, the exact positions — from your
teardown alone. If a detail would matter to someone rebuilding this file in
Photoshop or Figma, it belongs in your output.

**Describe the ad in front of you, not a default.** Every example in this
prompt is illustrative only — an age bracket, a typeface class, a color, a
layout — and none of them describe the ad you are looking at. Take gender,
age, register and aesthetic from what is actually in the frame. Never carry
over the framing of a previous teardown, and never reach for the category's
stock subject. A record that describes an ad other than this one is
worthless no matter how detailed it is.

**This is observation, not evaluation.** You are recording what is
demonstrably there so it can be analysed later — not judging whether it is
good, not recommending anything, not writing about the brand. Record brand
names when they appear in frame, because that is a fact about the ad. Never
editorialise about the brand, never assess the product, and never describe
the ad as effective or ineffective outside the sections that explicitly ask
for mechanism. **Abstraction happens downstream; your job is an accurate
record.**

Three laws govern everything:

**Accuracy law.** Never guess. If you cannot read or resolve something
clearly, write `[UNCLEAR: bottom-left badge]` instead of a plausible guess.
Mark anything you inferred rather than directly observed with `(inferred)`.
Typeface names in particular are almost always inferences — name the CLASS
you can see (high-contrast serif, condensed grotesque, humanist sans) and
mark any specific font name `(inferred)`. A confident wrong detail is worse
than a marked gap — wrong details get built into real briefs.

**Consistency law.** Every element gets ONE name, used identically
everywhere it appears. Every detail cited anywhere in your output must exist
in the objective record. State the age range ONCE, in brackets
(e.g. `[50-55]`), and reuse that exact range everywhere. Name each zone once
(`Zone A — top text block`) and use that name in every later section.

**Depth law.** The record's detail demands must never thin the analysis.
Sections 2 and 3 go as deep as the record goes precise: every zone's "Why it
works" names the exact words, the exact type treatment, the exact
compositional choice doing the work; every "What it sets up" names the
specific next move it enables, never a generic outcome. If length becomes a
pressure, cut nothing — write longer.

**Position is measured, not vibed.** Everywhere you give a position, give it
as a percentage of frame height from the top and frame width from the left
(e.g. `headline baseline ~14% from top, block spans 6-94% width`). "Upper
area" is not a position. A designer must be able to place it from your
numbers alone.

I need five things.

**1. THE OBJECTIVE RECORD**

Open with a Frame Spec:

- Aspect ratio and the placement it is cut for (1:1 feed, 4:5 feed, 9:16
  story/reel, 16:9). Say which, and say what evidence in the frame tells
  you — safe-zone margins, where the text sits, what is cropped.
- The full color palette actually used — every distinct color with a hex
  approximation and where it appears. Separate the background palette,
  the type palette, and the accent/highlight palette.
- Overall treatment — photographic, illustrated, composited, screenshot-
  style, meme-style, editorial-layout. Name the treatment and the specific
  evidence for it.
- **Generation tells.** State plainly whether the imagery appears
  photographic or AI-generated, and cite the specific evidence you can see
  (hand and finger structure, jewelry and fabric behaviour, background
  object coherence, text rendered inside the image, skin and hair
  micro-detail, lighting consistency). If you cannot tell, write
  `[UNCLEAR: generation]` — do not assert either way without evidence.

Then a Subject & Setting profile:

- Who appears — age range in brackets, physical description, hair (color,
  style), skin (tone, texture, any visible condition the ad is drawing
  attention to), expression, gaze direction (exactly where the eyes are
  pointed, and whether they meet the camera).
- Exactly what they are wearing — every garment with its color, material,
  pattern, trim, and fit. Every piece of jewelry: rings, bracelets,
  earrings, watches — and the brand if identifiable.
- Style label — name the aesthetic with a real reference point rather than
  a vague mood word. If it matches a known style, say which.
- The setting, as it actually is — what kind of space this really appears
  to be (judge from lighting, surfaces, object age and wear — don't
  upgrade an ordinary room into an "upscale" one). Then inventory the
  frame: what is on the surfaces, shelves, walls, and in the background —
  not just the focal props. The whole set is the set.
- Props — every object that appears, with color/material detail, and
  whether it is in the sharp plane or thrown out of focus.
- **The camera-and-light spec, in lexicon terms.** This is the block a
  generator rebuilds the photograph from, so it is written in the controlled
  vocabulary of `reference/visual-lexicon.md` — not in impressions. Every line
  below gets a term or an explicit `[NONE: <slot>]`. **Whatever you leave out
  is filled in by the training-data average, and the average is what every
  other ad in the category already looks like.**

  - **Shot size** — `ECU` / `CU` / `MCU` / `MS` / `MWS` / `WS` / `EWS` /
    `insert`.
  - **Camera height and angle**, as two separate facts: height (`floor`,
    `hip`, `chest`, `eye`, `above-eye`, `overhead`) — as a fraction of the
    subject's standing height where it matters — and angle (`level`,
    `low-angle`, `high-angle`, `overhead-flat`, `dutch`).
  - **Where the camera stands in the room, and which way it shoots.** Name it
    against the furniture: "from the corner at the foot of the bed, shooting
    lengthwise along the room." Height and angle do not contain this fact, and
    it is the fact that decides the picture — the same shot size at the same
    height from beside the bed rather than the foot of it is a different
    photograph.
  - **Subject orientation**, named: `frontal` / `three-quarter-front` /
    `profile` / `three-quarter-back` / `back` — **and face visibility as its
    own statement**: `face fully visible` / `face partly visible` /
    `face not visible`. **Never write `face partly visible` on its own** — say
    how much, in the same breath: "a sliver of cheek only", "the far eye and
    nothing else". Left unqualified, a rebuild reads it generously and renders
    a whole face. Head direction and gaze direction are separate facts;
    give both. This is the single fact a rebuild gets wrong most often, and
    getting it wrong changes the picture completely.
  - **Lens feel** — `wide-close` / `natural` / `portrait-compressed` /
    `tele-compressed` / `macro` — and depth of field: `deep` / `moderate` /
    `shallow` / `razor`.
  - **Light** — the setup by name from the lexicon, its direction, and its
    quality (`hard` / `soft` / `mixed`). Where practical lights are doing the
    work, name each one and place it: "one warm table lamp, midground, left of
    subject."
  - **Grade** — the named grade from the lexicon, plus the black point
    (`crushed blacks` / `lifted blacks`) where it reads.
  - **Texture and stock** — the authenticity markers: grain, flash look,
    camera type, and the physical tells actually visible (dust in a beam,
    condensation, skin texture and pores, fabric pilling, fingerprints,
    scuffs). **A picture recorded with this line empty rebuilds looking
    generated even when everything else is right**, so if it genuinely reads
    as clean digital with no grain, record `clean-digital` rather than
    leaving it blank.
  - **Composition** — the named pattern from the lexicon, what the room's own
    lines do and which edges they enter and leave by.
  - **Style anchor** — one phrase naming the kind of picture this is.

Then give me one table with exactly these five columns, in this order:

`Zone | Position | Visual Content | Text (verbatim) | Type & Treatment`

- **Zone** — your canonical name and letter, top to bottom in reading
  order (`Zone A — eyebrow bar`, `Zone B — headline block`,
  `Zone C — image field`, `Zone D — proof line`, `Zone E — CTA`). One row
  per distinct compositional element. A headline and the subhead beneath it
  are two zones if they carry different jobs, one zone only if they are one
  typographic unit doing one job.
- **Position** — percentages as defined above: top edge, bottom edge, and
  horizontal span of the zone, plus alignment (left/center/right/justified).
- **Visual Content** — what is in this zone that is not type: imagery,
  background fill, bars, badges, rules, arrows, product shots, logos.
  Include color of any fill or container. No text content in this column.
- **Text (verbatim)** — every word in this zone, exactly as written,
  including punctuation and capitalisation as set. Line breaks marked with
  `/`. Nothing else in this column. Write "none" if there is none. If an
  element looks like a platform chrome artifact or a watermark rather than
  intentional design, mark it `[ARTIFACT: …]` — we must not copy junk into
  new ads.

  **In-world text is not a type element, and it never appears in this column.**
  Words that exist as an object inside the photograph — a label printed on the
  bottle, a sign on the wall, a logo on a garment — belong to the picture. They
  are recorded in the **Visual Content** column as part of the object that
  carries them (`clear pump bottle, yellow liquid, the word "evora" printed
  small in white near the base`), and **this column reads `none`.** A zone whose
  only words are in-world has `none` here — no exceptions, no parenthetical
  note explaining that the text is really in-world. Measured cause, 2026-08-19:
  a brand name printed on a bottle was recorded as a text zone, and a rebuild
  would have printed the logo twice — once in the photograph and once again in
  type over it.
- **Type & Treatment** — for every text element: typeface class (and any
  specific name marked `(inferred)`), **width class**, weight, case,
  approximate size as a percentage of frame height (cap height is fine),
  color, tracking, leading, and any treatment — outline, shadow, highlight
  box, knockout, gradient.

  **Judge width honestly, and name it.** Width is its own fact, recorded
  separately from the class: `compressed` (very narrow, heavy, letters nearly
  touching — Impact, Haettenschweiler), `condensed` (narrower than regular but
  still open — DIN Condensed, Avenir Next Condensed), `normal`, or `extended`.
  Then name **one fallback file a renderer will certainly have**. Measured
  cause, 2026-08-19: a headline recorded only as "condensed grotesque" was
  rebuilt in a condensed face when the original was compressed, and the clone
  read visibly lighter and wider until it was corrected to Impact.

  **Where one line carries more than one color, record the split as data.**
  Not prose. Write the line's fragments as an ordered list in reading order,
  each with its own color, so that concatenating the fragments reproduces the
  line exactly — spaces and final punctuation included:
  `["IT WORKS " → #FFFFFF] ["TOO WELL." → #F5A623]`. A single color on a
  two-color line silently loses the accent, and the accent is usually the
  thing carrying the brand.

Never merge zones. Never merge these columns.

Then, still inside the objective record, give me **THE LAYOUT SYSTEM**. The
zone table says where each element is. This says what the *rules* are — and it
is the section a new file gets built from, so measure it, never characterise
it.

- **The margins.** The left, right, top and bottom margin, each as a
  percentage of frame width or height, measured from the frame edge to the
  outermost edge of the nearest type or furniture — not to the image. Say
  whether left and right are equal. A margin that differs by more than half a
  percent from its opposite is a deliberate asymmetry: say so.
- **The alignment axis.** Which vertical lines elements align to, as
  percentages. For every text element say whether it is centred on the frame,
  centred on its own container, or set to a left or right axis — and **which
  elements share an axis**. Two blocks that both start at 10% are on one axis
  and must stay on it; a variation that moves one has broken the layout.
- **The vertical rhythm.** The gap between each adjacent pair of elements, top
  to bottom, as a percentage of frame height — the real gap, from the bottom
  of one block to the top of the next, not the difference between their stated
  positions. Then say which gaps are equal and which are deliberately
  different. This is the number a rebuild gets wrong most often.
- **The type scale.** Every text element's cap height as a percentage of frame
  height, and as a ratio against the smallest one. State the series (for
  example `1 : 2 : 7.5`). If two elements share a size they are one step of
  the scale and must move together.
- **Measure and line count.** For each text block: how many lines it actually
  runs, and its measure — characters per line, counted. **This is the number
  that controls whether new copy fits**, and a rebuild that ignores it is how
  a two-line subhead becomes five.
- **The keep-clear regions.** Where the subject's face, hands and every
  load-bearing prop actually sit, each as a box in percentages. Type must
  never enter these. Say plainly which parts of the frame are quiet enough to
  carry type — the shadow, the wall, the empty table — and how much of the
  frame that leaves.
- **The pictorial geometry.** The type layout is only half the layout. This is
  the picture's own **measured** geometry — the numbers, and only the numbers.
  The camera, the subject's orientation, the lens, the light and the grade were
  already recorded in the camera-and-light spec above; **do not repeat them
  here.** This block adds what a percentage can say and a word cannot:
  - **Where every major element sits**, as a box in percentages — each person,
    each load-bearing prop, the furniture that defines the space, the window or
    light source. Not just the quiet zones: **the occupied ones**. A record that
    says where type may go but not where the subject is cannot be rebuilt.
  - **Where the subject is cut by the frame** — at the knee, the hip, the chest
    — and how much of the frame's height they occupy.
  - **The lines of the room**: which way the bed, table, counter or floor runs
    across the frame, and the percentages where its edges enter and leave.
  - **What sits at each of the four frame edges**, one line each. An edge
    inventory is what stops a rebuild re-cropping the scene.

- **Optical corrections.** Anything not on the grid, and why: a badge nudged
  off centre, a line hung past the margin, a cap height reduced for one word,
  extra leading under a heading. If there are none, say none — but look, since
  an uncorrected layout is rarer than an unnoticed correction.

**2. THE FRAME MECHANICS**

**The reading path.** Number the order a viewer's eye actually travels
through the frame — 1, 2, 3 — naming the zone at each stop, and state the
specific reason it lands there in that order: size, contrast, color, face,
gaze direction, leading line, negative space. Then state what the viewer has
understood after stop 1 alone, and after stop 2 alone. This is the static
equivalent of the hook: the frame gets one stop and one glance, and this
section is where you record what that glance buys.

**The scroll-stop mechanism.** In one paragraph: name the single element
most responsible for arresting the scroll, and the mechanism it uses
(pattern interrupt, face and eye contact, anomaly in the image, a violation
of expectation in the copy, high-contrast type mass, color break against
feed norms). Cite the element by its zone name. Then name the second
strongest, and say what would remain if the first were removed.

**Functional zones.** Take the zones from your table and group them into the
blocks of work the ad performs. Name each block for what it does to the
viewer, not for where it sits (e.g. "Prohibition Hook", "Authority
Transfer", "Proof of Result", "Risk Reversal", "Offer & Urgency").

Use ONE canonical name per technique: if the detailed analysis calls it "the
prohibition hook", the block-level view calls it the prohibition hook too —
keep the high-level and detailed layers, but never two names for one thing.
Where a technique is an established term from psychology or direct-response
marketing, use the established term.

For every block, give me all four of these as separate labeled lines:

- **Block name and zones covered**
- **Mechanical purpose** — one line: what this block is engineered to do to
  the viewer.
- **Why it works** — the detail. Name the specific thing doing the work: the
  exact words, the exact type treatment, the compositional choice, the
  color. Name the technique it belongs to. Say what the viewer feels or
  concludes. Then end the line with the labeled clause `Breaks if cut:`
  followed by the specific thing that fails without this block — every
  block, no exceptions.
- **What it sets up** — the next block this one makes possible, or, for the
  final block, the action it hands to the click.

Then two more sub-sections:

- **Copy beats.** Every line of text that does real work gets its own entry
  — not a selected few, and a block with three working lines gets three
  entries. Each entry is four labeled lines, in this order and no other
  shape:

  ```
  Line: "<the words, quoted exactly>"
  Device: <the named technique this line is performing>
  Why it lands: <why it works on the specific audience this ad is aimed at
  — name who that is and what they already believe>
  Trigger words: <the individual words carrying the charge, listed>
  ```

  A one-line summary in place of the four is a failed entry. `Device` and
  `Trigger words` are never the same content: the device is what the line
  does, the trigger words are which words do it.
- **Hierarchy and weight.** How the frame allocates attention: the
  percentage of frame area given to imagery versus type versus empty
  ground; the size ratio between the largest and smallest type; how many
  distinct type sizes are in play; where contrast is highest and where it
  is deliberately let go. Then state what the ad is willing to make
  illegible at thumbnail size, and what it protects — and say which zones
  survive if the ad is viewed at 25% scale.

**3. THE PSYCHOLOGY**

Use the same subsection structure every time, in this order — formats may
add extras at the end, but these six always appear with these names:

- **The thesis** — one line naming the whole psychological play, in quotes
  (e.g. "The Withheld Folk Remedy vs. The Failed Commercial Product").
- **Character archetype** — who the person in the frame is being, using
  established archetype language (e.g. "the sage", "the aspirational self",
  "the everywoman") rather than invented labels, and the specific signals
  that build it: wardrobe, styling, setting, hands, gaze, props. Cite only
  details already in the objective record.
- **Aesthetic archetype** — what the look itself signals, and what it
  borrows credibility from. Name the visual genre it is imitating
  (editorial magazine spread, documentary photograph, native feed post,
  infomercial, packaging, screenshot) and the exact design choices that do
  the imitating.
- **The setting** — what the location does for believability.
- **The psychological plays** — numbered. Name each one — established terms
  referenced where they exist — then say how it is executed in this specific
  ad. End every play with the labeled line `Belief shift:` naming what the
  viewer now believes (or no longer believes) because of this play — every
  play, no exceptions.
- **The viewer's end state** — what the viewer believes, feels, or fears
  after the glance that they did not before it.

**4. THE INDEX**

Close with two short registries:

- **Definitions index** — every named technique and play used above, one
  line each: the canonical name, a one-line definition, and whether it is an
  established term (say from where) or our working label.
- **Element registry** — every reusable design element (bars, badges,
  highlight boxes, arrows, rules, gradients, overlays) with its canonical
  name, shape, size as a percentage of frame, color, and the zone it
  appears in. This registry is what a designer builds the template from.

**5. MARKET STATE**

This chain has no separate audience stage, so this is the only place the
ad's own market position gets named — read off the ad itself, not guessed
from the category. An objective reading of the swipe's own choices, same
standard as everywhere above: `[UNCLEAR: which]` beats a guess.

- **Awareness level** — name the ONE rung, from the five named levels below,
  this ad's own opening assumes the reader already stands on:

  {awareness_levels}

  Cite the specific words or zone that prove it — does the headline name the
  product and the price cold (most-aware), or open on pure identification
  with no product, no price, no direct claim named anywhere in frame
  (unaware)?
- **Sophistication stage** — name the ONE stage, from the five named stages
  below, this ad's claim occupies:

  {sophistication_stages}

  Cite the exact claim, or mechanism language, that shows it — a plain claim
  stated simply, the same claim pushed to the edge of belief, a named
  mechanism leading the headline, an enlarged mechanism, or a field so
  exhausted the ad sells on identification with no claim and no mechanism at
  all.
- **Lead desire** — the one desire this ad's own copy is actually selling,
  tested against the three dimensions below:

  {desire_dimensions}

  Cite the zone or line that carries it, and say in one line why the other
  desires the ad could have led with did not win.

If the ad genuinely gives no evidence for one of the three, write
`[UNCLEAR: which]` rather than inferring from the category's default.

Give me a really clean output. I'm going to turn this into a brief that
takes in my brand principles and then creates content for that.
