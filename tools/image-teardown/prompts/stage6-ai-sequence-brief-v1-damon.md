Here is the complete record of one SEQUENCE — a carousel or a slideshow — we
are rebuilding for our brand, and the MACHINE is going to make it: every
slide generated, judged and composited.

The teardown of the source, slide by slide: {teardown_record}

Its replication spec — the format with the source's brand stripped out:
{replication_spec}

Our brand put through that format: {brand_injection}

The headline set: {hook_set}

The picture variations: {image_variations}

Our brand: {brand_name}. Our product: {product_file}. Our offer:
{offer_file}.

The seven named techniques, for technique-per-element below: {techniques}

**You are not given the language bank, and that is deliberate.** The copy
arrives already written and already measured; the customer's words were chosen
upstream where the provenance was visible.

Write the **AI sequence brief**: the document that says what this sequence
is, before anyone makes it — and the build data the machine makes it from.

**What is different about a sequence.** A single still is one plate with one
type layer. A sequence is one THREAD that holds across every slide while each
slide still stops the scroll alone. The thing being specified is the carry:
what is identical on every slide (the person, the product, the palette, the
framing, the treatment) and what moves, slide to slide, and only that. So the
build data has one plate — slide one — and every later slide is an EDIT off
slide one: the same picture with one thing changed, never a fresh picture.
That is how the machine keeps the thread; a sequence generated slide by slide
from separate prompts is a set of strangers (measured on the video side,
2026-09-02: a scene re-described from words came back with a different room,
a different wardrobe and a different face every take; the same scene as a
delta off its own plate held).

**The delta rule, for slides two onward.** An edit instruction never describes
anything slide one already shows. It carries the change and nothing else —
"the hand turns palm-up; the words change to …" — in under 400 characters,
one or two changes per slide. If a slide needs more than that, it is not a
slide of this sequence; say so in the internal document.

**No runtime.** There is no timing span and no `Hear:` line. Nobody speaks.
The words on each slide are the script.

---

## The five rules

**Nothing unresolved crosses into the brief.** If the material above still
carries a `[SLOT: …]`, a `[MISSING: …]`, or an `[UNCLEAR: …]`, then either the
fact exists in one of the files supplied above and you fill it from there, or
**the line carrying it is cut.** A builder who meets an unfilled placeholder
will either skip the element or invent one, and both are worse than not having
it. Every cut is listed in the internal document so nobody thinks it was
handled.

There is no third option. **Generalising a placeholder is filling it.** Turning
a slot for a promotion into "the current offer", or a slot for packaging into
"the product", has invented a fact in the one document that gets built from.
If the fact is not in a file, the line is cut — record it and move on.

**The brief adds no facts.** Every claim in it traces to a file supplied above.
Watch for the inventions that arrive as flavour rather than as claims: a
heritage the product file never mentions, a named method or ritual, an
ingredient count, a manufacturing story, a mechanism stated more confidently
than the file states it. A phrase appearing in a file is not automatically ours
either — the language bank records what customers say **and what they were
shown not to say**, so read the sentence around any phrase before lifting it.

**The words are already decided.** Copy arrives from the injection already
written and already measured. You do not rewrite it, improve it, shorten it or
"tighten" it. Reproduce it character for character, including its line breaks.
If a line does not fit its measure, that is a defect you report in the internal
document — never one you fix by editing the words.

**Say what comes from a picture and what comes from words.** Measured across
six rebuilds, 2026-08-26: subject, wardrobe, props, action, environment, light,
grade, texture, shot size, camera height, angle and lens all survive being
described in language. **Where the camera stands in the room does not** — it
came back wrong every time, including when stated plainly and repeated in the
negatives. So the brief states which parts of the frame come from an attached
reference and which are carried by the description. A brief that omits this
reads as though the words are sufficient, and the build will put the camera in
the wrong place.

**The brief reports; it does not decide.** Who is in the picture, what body
part it shows, which route produces it — all of that was settled upstream and
arrives already decided in the injection. Do not re-derive any of it, do not
consult a second source about it, and do not raise a conflict when another file
would have chosen differently. If the injection says legs, the ad is legs.
Measured cause, 2026-08-28: the brief was handed the file that governs who may
appear, formed its own view, and reported a conflict against a decision that
had already been made properly one stage earlier.

**Two things are never generated.** The type is set from the layout data. The
product is composited from the brand's own photograph. Both carry marks that a
model approximates, and a near-miss on a wordmark is worse than an absence. The
brief says so plainly rather than leaving a builder to discover it.

---

Give me three documents and nothing else.

## DOCUMENT ONE — THE BRIEF

A working document. Plain language, no process jargon, no stage names, no
variable names, no file paths. Write it so a person who has never seen the
source understands what is being made and why.

**What this is.** Two or three sentences: what sequence we are making, how
many slides, what it is built on, and what the format is doing — the
mechanism, not the brand. Name the one thing that makes it work, from the
spec's load-bearing list.

**Who it is for and what they already believe.** Two or three sentences in
the avatar's terms.

**The thread.** What is identical on every slide, named once each: the
person (from the injection), the product and how it is held, the palette,
the framing and distance, the treatment, the background. This block is what
the judge checks slide N against slide one.

**The slides.** One block per slide, in order, numbered — every slide, never
a range:

```
## Slide N

**Shows:** what is in the picture. For slide one, the full picture in the
order a viewer meets it, and which parts come from the attached reference
rather than from the description. For every later slide: "slide one with …"
and ONLY what changed — the delta, in plain words.

**Says:** the words on this slide, verbatim, line breaks shown, which is the
headline and which is support, and roughly where they sit.

**Why they swipe:** the thing on this slide that earns the next one. The last
slide says what it asks for instead.
```

**Technique per slide.** One line per slide: the slide · the ONE technique
from the seven above · the line or picture element carrying it.

**The alternates.** The other headlines from the set, verbatim, control
first, none dropped, none ranked, none reworded, each with its axis — and
which slide's words each replaces.

**The pictures.** The control sequence, then each variation from the picture
variations, one line each: what it is, the single variable that moved, and
what it is for. Then the order to run them in.

**The offer, and the wording that cannot change.** In the offer file's exact
words; fixed wording reproduced exactly and marked fixed.

**What must not appear.** No third-party brands, no invented packaging, no
result the product has not been shown to deliver, no slide that breaks the
thread — plus anything specific to this sequence.

**How we will know it is right.** Three to five yes-or-no checks: at least
one about the thread (does slide N still match slide one — same person, same
product, same palette, same framing), at least one about the words (exactly
as written, slide for slide), one about the close, and always: a legible
third-party brand on any slide is an automatic reject.

**Where this came from.** One line naming the source by its own identifier
and where it was captured.

## DOCUMENT TWO — THE BUILD DATA

The same brief, in the form the machine executes. No prose. **Slide one gets
the full build data below — the review draft, the plate slots, the plate
prompt, the reference, the type layer, the composited elements. Slides two
onward get the SLIDE DELTAS block, and nothing else is generated for them.**

- **The slide deltas** — a single fenced `json` block: an array, one entry per
  slide from two onward, each with exactly these keys:

  ```
  slide       the slide number
  change      the delta off slide one, in words — under 400 characters, one
              or two changes, never a description of what slide one shows
  keep        what must not move on this slide, as a short list (the thread,
              plus anything this slide's change puts at risk)
  type        this slide's type layer elements, in the same shape as slide
              one's type layer, with this slide's verbatim words
  ```

  The machine makes slide one from the plate, then each later slide as an
  edit off slide one carrying only `change`, judged against slide one for
  `keep`, with `type` composited over it. A `change` that describes the
  scene, or asks for three things, is refused by the machine — so write it as
  the one-line diff it is.

Then, for slide one only:

- **The review draft** — how the brief gets looked at before anyone builds
  it. It is **not a second prompt**: it is this brief's own plate, generated
  the normal way, with this brief's own type layer composited over it by
  `image-production/tools/compose.py`. Nothing about it is freehand.

  Say so in one line, and emit the layout in **exactly** the shape the
  compositor reads — a `json` block with an `elements` array, one entry per
  piece of text in the ad, each with these keys and no others renamed:

  ```
  text        the words, verbatim
  top_pct     top edge, % of frame height
  left_pct    left edge, % of frame width
  right_pct   right edge, % of frame width
  align       left | center | right
  cap_pct     cap height, % of frame height
  color       hex
  case        upper | lower | as-written
  tracking    tight | standard | loose
  weight      bold | regular
  font        grotesque | humanist-sans | condensed | mono
  file        "all", or which variants carry it
  box         optional {"fill": hex, "pad_pct": n} for a panel behind it
  segments    optional [{"text": ..., "color": ...}] when one line is two colours
  ```

  **Every brief emits this, every time.** Three briefs in four came back with
  the words written out in prose and a layout block in some other shape, so
  the compositor had nothing to read and the draft could not be assembled at
  all (2026-09-14). A format with no type still emits `"elements": []` and
  says why.

  **Never write a prompt that asks a model to draw the words.** It breaks
  three rules that each cost a failed batch (`GENERATION-METHOD.md`): the
  reference carries the material, not a paragraph; type and prices are
  composited because a generated price is a lie; and a camera named in a
  prompt is an object placed in the frame. A draft made that way is slop and
  it misrepresents the idea it is supposed to be testing (2026-09-14).

- **The plate slots** — the prompt as data, not as prose, in the shape
  `image-production/tools/prompt.py` renders. A `json` block with `pack`,
  `ratio`, and these thirteen keys in this order: `references`, `subject`,
  `action`, `wardrobe`, `setting`, `composition`, `shot`, `light`, `grade`,
  `style`, `texture`, `anchors`, `negatives`.

  Leave `shot`, `light`, `grade`, `style`, `texture` and `negatives` empty
  unless this ad genuinely departs from its register — the style pack fills
  them, and a pack named once is a register the whole batch shares. Choose
  the pack from the register below — its `packs` keys are the only legal
  values, and if none of them fits, say so in a line rather than coining one.

<style_packs>
{style_packs}
</style_packs>

  `references` is Element ids: the cast's, and the product's if it is in
  frame. **Never describe a face or a device that has an id.** `shot` is
  height, angle, distance and depth — never a camera, a lens or a phone,
  which a model places in the frame as objects.

  Why data and not a paragraph: a prose prompt has no parts, so re-rolling it
  moves everything at once and nothing can say what was meant to change.
  Slots make a regeneration a one-line diff. See
  `image-production/PROMPT-SPEC.md`.

- **The plate prompt** — the same thing rendered, for reading, produced by
  `prompt.py render`. It is the **photograph with no words in it**, written as a shot list in the order
  subject → action → environment → composition → camera → light → grade →
  style → texture. Close with the negative constraints on their own line.

  Then, on its own line, this slot, filled from the format's own
  `keep_clear` rectangles — copy the numbers, do not paraphrase them:

  ```
  COMPOSITION (measured): subject occupies L–R% width, T–B% height.
  LEAVE EMPTY: <zone name> L–R% width, T–B% height — clean background
  only, nothing crossing it.
  ```

  One `LEAVE EMPTY` line per keep-clear rectangle. A model given
  "right third clear for product overlay" is being asked to guess; a
  model given "leave empty 60–90% width, 32–60% height" is being given
  the format. The phrase held on two plates and that was luck, not
  spec. Every empty zone exists because something gets composited into
  it later — type, a product, a logo. Content that drifts into one is
  not a flawed picture, it is a picture the ad cannot be built from.
- **The reference** — which image is attached and what it is authoritative for.
  If none is attached, say so and say that the framing is therefore unverified.
- **The type layer** — a single fenced `json` block, carried through from the
  format's own layout data unchanged, with the injected words in place of the
  source's. Every element with its verbatim text,
  position, weight, size, colour, tracking, measure and line count, any panel
  behind it, and per-fragment colours and panels where a line carries two. If the format
  carries no layout data, write `[MISSING: type layer]` and say so.
- **The composited elements** — what gets set rather than generated, the file
  each comes from, **and the `composited` block from the format's layout data,
  carried through unchanged.** Position, span, rotation and outline travel as
  numbers. Describing where the product sits in a sentence is how an ad ships
  without one.
- **The accept tests** — the same checks as the brief's, as a list.

## DOCUMENT THREE — INTERNAL

Never part of the brief. For the operator only.

- **Claim trace.** One row per claim made in Document One, naming the file it
  came from. A claim with no file is deleted from the brief and its row says
  `REMOVED`.
- **Cuts.** Every line cut for want of a fact, what the missing fact was, and
  who or which file would have it.
- **Fit.** Each text block's character count against its measured line and line
  count, marked `fits` or `OVER by N`. An over is reported, never fixed by
  editing the words.

  **The measure belongs to the element, not to the line.** One number governs
  every line in a block, carried from the layout data exactly as written.
  **Never derive, adjust or estimate a different measure for an individual
  line** — if the layout data says 31, then every line in that element is
  checked against 31, including the second one and including the short one. A
  measure you calculated rather than read is a fabricated measurement in the
  one document that gets built from. Measured cause, 2026-08-28: a brief
  invented a measure of 25 for a headline's second line, reported a
  three-character overage that did not exist, and sent a correct headline back
  to be rewritten.

  Count the characters. Do not estimate them. Where an element has no measure
  in the layout data, write `[MISSING: measure]` against it rather than
  supplying one.
- **Carried forward.** Any conflict or unresolved question the material above
  raised that the brief could not settle, and whose call it is.


## The brand's colours

{palette}

These are measured off the brand's own product photography. Any colour in
the swipe that is not in this table is the swiped brand's, and must be
replaced with the equivalent role from this table — never carried through.

## Fill every slot. Never cut one.

The format is a structure, and every zone in it is load-bearing. An eyebrow,
a sub-headline, a picture band, an offer block — take one out and what is
left is not a cleaner ad, it is a broken one with a hole where a slot was.

**Measured cause, 2026-08-31.** A brief cut five zones from one format and
the finished ad had an empty bottom third. The reasons given were each
locally true — "application time unknown", "no promotional discount
exists", "brand accent color hex undocumented" — and the result was still a
half-finished ad that could not run.

So, for every zone in the format:

1. **Carry the swipe's content if ours is equivalent.**
2. **If not, substitute our own truth in the same role.** The swipe says
   "60% OFF · FLASH DEAL · LIMITED STOCK"; we do not discount, but we have
   a real price, a real multi-tube saving and a real guarantee — any of
   those is an offer block. The swipe's sub-headline promises a time
   ("the 60-sec glow"); if our time is unknown, our sub-headline says
   something else true about using it. **The role is fixed; the content is
   ours.**
3. **Only leave a zone empty when nothing true can fill that role** — and
   then say so in the cut list, in those words, naming what you looked for
   and where you looked. "Unknown" is a reason to go and find it in the
   brand files, not a reason to delete a slot.

A missing fact is a research task. It is never a licence to ship a hole.

## A zone with no panel has no `box`

Omit the key. Do not emit `"box": {"fill": "#000000", "pad_pct": 0}` for a
zone that simply has no panel behind it.

**Measured cause, 2026-09-01.** Every zone in one brief came back carrying
that exact object — a schema slot filled because it was there, not because
the format had a panel. The builder drew a rectangle for each one and the
finished ad was a column of empty boxes sitting on top of its own copy.

A panel goes in the data when you measured a panel on the ad. Its colour is
the colour you sampled. If there is no panel, no `box` — and if there is a
panel whose colour you could not read, say `[MISSING: panel colour]` rather
than choosing one.

## You write words. You do not write geometry.

**Ruled 2026-09-01.** The layout is not yours to invent. It lives in a
hand-tuned template that a designer owns — position, size, colour, measure,
spacing, panels, all of it. Your job is the copy that goes in it.

The type layer is therefore not a layout. It is this:

```json
{
  "template": "photo-strip",
  "content": {
    "eyebrow": "The Morning Ritual",
    "subhead": "The two-step reset:",
    "headline": "The routine that\nfixes what you hide",
    "offer_big": "Save 25%",
    "offer_a": "Free shipping",
    "offer_b": "30-day guarantee",
    "cta": "Grab yours before we sell out.",
    "fineprint": "Our 30-day money-back guarantee covers you if it does not work for you."
  }
}
```

Rules:

1. **Name the template** whose shape matches the swiped format. The
   available templates and what each is for are listed in
   `image-production/templates/`. If none of them fits, say so plainly and
   describe the shape that is missing — a new template is a design job, not
   something to improvise in a brief.
2. **Fill every slot the template has.** An empty slot is a hole in the ad.
   The fill-every-slot rule above applies here exactly as written: carry the
   swipe's content, or substitute our own truth in the same role.
3. **Emit no positions, no sizes, no colours, no padding, no max lines.**
   Not for zones, not for panels. If you find yourself writing a percentage
   or a hex value, you are doing the designer's job and you will do it worse.
4. **Price the copy against the slot.** Each slot's line length is fixed by
   the template. Long copy is shrunk to fit, which makes it look wrong. Write
   to the length rather than making the builder rescue it.

Why this rule exists: when the brief authored its own geometry, every run
invented a different layout and every run broke differently — a missing
ground, then a missing picture band, then missing panels, then a black panel
on every zone with white type on it. None of those were copy problems. The
words were fine every time. The formats repeat; the words do not.

## Name the problem, the angle and the concept

The brief declares these three, and the builder carries them into the ad
name. They are a hierarchy, not one thing:

```json
{
  "problem": "darkspots",
  "angle": "pigmentmemory",
  "concept": "handsapplication"
}
```

- **`problem`** — what the customer actually has, in their words reduced to a
  slug. Brown spots on hands, arms and chest → `darkspots`.
- **`angle`** — the angle taken on that problem, on OUR side.

  **First, record theirs.** The swipe is somebody else's ad, and often not
  even a competitor — a testosterone brand, a hair brand, anyone selling to
  the same person. Their angle is a fact about their marketing, written in
  their words, and the swipe library has already named it:

<swipe_angle>
{swipe_angle}
</swipe_angle>

  Quote that angle's name as `source_angle` and say in one line what it
  argues. Do not translate it into our vocabulary. **The point of swiping is
  to see what argument is working on this person for somebody else**, and an
  angle rewritten in our words on the way in is an angle we can no longer
  compare to theirs.

  **Then, ours.** The bank of angles this brand has signed:

<angle_source>
{angle_source}
</angle_source>

  Exactly one of three answers:

  1. **It is one of ours.** The injected ad makes the same argument to the
     same person as a signed angle. Use its `id` with hyphens removed, and
     say in one line which and why. Match on the argument, not the wording.
  2. **It is new.** Their angle is an argument we do not run. This is the
     normal and useful outcome — it is the reason to swipe at all. Write
     `angle` as `proposed`, and add a `proposed_angle` block: a kebab-case
     `id`, a `name` in the voice of the bank's other names, and a `what` of
     two or three sentences saying what it claims and to whom. Say which
     signed angle is nearest and what makes this one different. **Damon signs
     it or he does not — you are proposing, never adding.**
  3. **You cannot tell.** Write `unsigned` and say what is missing.

  **Never force a match.** A near-miss filed as a signed angle is worse than
  a proposal: the report then groups two different arguments into one row and
  the test that would have told us which one works is gone. Their angle not
  fitting our bank is a finding, not a failure.

  **Never coin a slug into the bank.** A proposal lives in the brief until it
  is signed — the angle vocabulary is Damon's.

- **`concept`** — the ideation and execution of that angle. The creative idea
  itself: `handsapplication`, `beforeafter`, `twostep`.

Lowercase letters and digits only, no hyphens inside a value — these become
positional fields in the ad name, and a hyphen inside one adds a column to
every report that splits on it.

Why the brief and not the delivery command: an angle typed at upload time is
a guess made by whoever is uploading. An angle declared in the brief is the
one the copy was actually written to, which is the only version worth
grouping spend by.
