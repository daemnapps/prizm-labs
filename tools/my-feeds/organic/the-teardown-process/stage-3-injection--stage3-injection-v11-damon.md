Today is: {today}
Here is real language selected for this stage: {language}
Here is a complete teardown of a video asset: {teardown_record}
Here are the body techniques and what each one is for: {techniques}
Here is our brand's declared position — its LINE, SPINE, MECHANISM, the MARKET STAGE it sells
into and what that stage LEADS WITH, as labelled slots: {position}
Here is our brand's story — who tells our version and what happens to them: its SPINE, TELLERS, STORIES with their beats and who each fits, and, once stage 1b has run, the story and teller this run picked (THIS RUN'S STORY), as labelled slots; `[UNFILLED]` when the brand has no story yet: {story}

*v11 (2026-09-19, Damon: "storytelling and intent over volume" — the Conscious Bar swipe): reads `{story}`, the brand's story file beside its position. The swipe keeps its structure; THIS RUN'S STORY decides whose it is: the teller on screen and the before, turn and after they tell. New check 4.*

**The language above is QUERIED, not dumped.** These rows were chosen
because of what they ARE — the kind of thing this stage needs — and ranked by
topic fit, how loud the row was, and how well sourced. Each is a real sentence
a real person said, carrying who said it and where it came from.

Use their words. Weigh the provenance: a row flagged `ATTRIBUTION ASSUMED` is
weaker evidence, and a paid panel is not a customer speaking — never present
either as something a customer said. If nothing in the rows fits, say so; an
empty result is a fact about the bank, not a licence to write the sentence
yourself.

**The bank is evidence, not a script. Interpret it; do not transplant it.**
Everything in it was true of a particular person, at a particular moment, in a
particular conversation — none of it was written for the asset you are making.
Re-judge every line before using it: does it fit what this is about, who is
speaking, and when this runs. **Keep the truth, drop the frame.**

**A month must be the real one.** Today's date is at the top and it is data,
exactly like the avatar and the banks. The banks record months because real
people name them — but they recorded when the speaker spoke, not when this
runs. Do not inherit theirs; substitute ours. A genuine historical reference — a decade,
an age, "when the kids were small" — is a fixed point and stays.


And here is its replication spec: {replication_spec}

Our brand: {brand_name}. Our avatar: {avatar}. Our product details:
{product_file}. Our offer: {offer_file}. Our language bank:
{language_bank}. Our identity anchors: {identity_anchors}. We are
producing this via {production_route}.

Rebuild this exact video for our brand and turn it into a production
brief.

**THIS IS A SUBSTITUTION, NOT A REWRITE.**

Work through the teardown record's transcript one line at a time, in
order. For each source line, output one line for us. The source script is
the template — you are swapping the brand-specific words out of it and
our brand-specific words in, and changing nothing else.

Hold all of this exactly as the source has it:

- **Sentence structure and word order.** If the source says "And not
  because it's loaded with X to do Y to the thing it acts on," ours
  says "And not because it's loaded with [our X] to [our Y] to the thing that
  looks like this."
- **The connectives and their sequence.** "And not because…" / "Or
  because…" / "And definitely not because…" is three lines with those
  three openers, in that order. Never collapse them into one.
- **Line count.** One output line per source line. Never merge two source
  lines, never split one, never drop one, never reorder them, never add
  one.
- **Length and rhythm.** Each line stays about as long as the source line.
  If the source rambles, ours rambles. If it repeats a phrase four times,
  ours repeats it four times.
- **Register and filler.** Keep the slang, the contractions, the asides,
  the "yeah," the "I don't know if," the profanity if it's there. Do not
  make it more polished than the source. **This is camouflage, in the
  technique list supplied above** — believability borrowed from the medium
  the asset lives in, by holding the host format's own register and
  phrasing so there is no gear-shift into ad voice. Polishing the register
  is not a small stylistic edit; it removes the technique the source was
  running, and the viewer's skepticism arrives with it.
- **Lines with no brand content stay identical.** Copy them across
  verbatim and mark them unchanged.

Swap only what is genuinely brand-specific: the brand name, product name,
ingredients and actives, the mechanism, the problem and the body part it
affects, the competitor or procedure being displaced, the origin story,
the offer, and any numbers.

**THE LINE IS THE SPINE OF EVERY SWAP.** `{position}` is the brand's declared
reason to exist for this reader, and it decides what fills the slots the source
opened — it never adds a line the source did not have.

- Where the source carried **its** mechanism — the how, the why-it-works, the
  why-everything-else-failed — ours carries `MECHANISM`, named in
  `MECHANISM NAME`'s own words. Never a generic "formula", never an
  ingredient list standing in for the how.
- Where the source named **its** problem, ours uses `PROBLEM WORD` — the
  reader's dominant word, not the category's synonym.
- Where the source displaced **its** competitor or procedure, ours displaces
  from `DISPLACES` — a thing this reader has actually tried, per the bank.
- Where the source's line was **its** brand's one sentence — the claim it
  hangs on — ours is `LINE` or `SPINE`, cut to the source's length and rhythm.
- Anything in `NEVER` is never written, even when the source's structure
  invites it; write the swapped line the structure demands with the banned
  word replaced by the bank's, and record the substitution in CONFLICTS.

**THE STORY CARRIES THE PERSON.** `{story}` says who tells our version and what
happens to them. The swipe supplies the structure; the story decides whose it is.

- Where the source had **its** person, ours is the `TELLER` in THIS RUN'S STORY,
  cast through {identity_anchors}. Never a person the anchors do not allow.
- Where the source told **its** before, turn and after, ours tells the picked
  story's beats in that order: `BEFORE` where the source set up, `TURN` where the
  source turned, `AFTER` where it paid off. The source's timing stays; the story
  fills it.
- Where the source gave **its** reason to switch, ours is `REASON TO SWITCH`, which
  points at `DISPLACES` in `{position}`.
- The product enters where `PRODUCT ENTERS` says, inside the slot the source gave
  its product. If the source shows it earlier, keep the source's timing and record
  the clash in CONFLICTS.
- A story's receipt is a real person's words: quote it only as the story file quotes
  it, tagged `VERBATIM`. A beat the story describes but no receipt or bank row
  supports is written from the bank and tagged as the bank tags it.
- Anything in the story's `NEVER` is never written.

If `{story}` is `[UNFILLED]`, or 1b picked `none fit`, keep the source's own arc,
swap facts only, and print `STORY: none` in check 4.

**What the stage changes.** `MARKET STAGE` and `LEADS WITH` say what this
market still believes. A source that leads with a plain claim, swapped into a
market at *claims exhausted*, is a script whose opening the reader has already
discounted — you still swap it faithfully (the structure is the source's), and
you flag it in CONFLICTS as `STAGE: the source leads with <x>; our market leads
with <LEADS WITH>`. The hook and placement passes read that flag.

**Do not improve the source.** Do not soften a claim, fix a tone, correct
an exaggeration, replace a device you find distasteful, or restructure a
beat because a better version occurred to you. Your judgment about whether
the source is a good ad is not wanted here — it already performed, which
is why it was swiped.

**Do not invent.** If a line needs a fact we have not supplied — a price,
an offer, a user count, a study, a person — put `[SLOT: what's needed]`
inline exactly where the fact goes, and list it at the end. Never guess a
number.

The test for "supplied" is exact: **a fact is ours only if it is written
in one of the files above.** Not something you know about the category,
not something that is probably true of a brand like ours, and above all
not something you read in the source video. Three cases account for
nearly every leak, and each has one correct move:

- **The source's offer is the source's.** A sale, a discount, a price
  drop, a "cheapest it has ever been," a limited window — those are facts
  about *their* brand. Ours has exactly the offers written in
  {offer_file} and no others. Substitute a claimed promotion only if the
  offer file carries it; otherwise the swapped line keeps the source's
  shape with `[SLOT: current promotion — needs owner approval]` in place
  of the claim. An empty promo calendar means evergreen only; it does not
  mean you may describe a sale.
- **Only the supplied product is ours to describe.** If the script needs
  a second product — a bundle partner, a companion item, a follow-up
  step — you may name it if the offer file names it, but you may never
  state its ingredients, texture, mechanism or claims from memory. Write
  `[SLOT: <product name> — ingredients and claims]` and move on. Pulling
  an ingredient from the product file you *were* given and attaching it
  to a product you were *not* given is the most common version of this
  error and the hardest to spot on the page.
- **The source's actives are the source's.** Never carry a source
  ingredient into our line, and never invent one to fill the slot the
  source ingredient occupied. Ours come from {product_file} only.

A `[SLOT: …]` costs a reviewer thirty seconds. An invented sale or an
invented ingredient goes on camera.

**Conflicts get flagged, never fixed.** If a source line, once swapped,
would break a rule in {language_bank} or {product_file}, still write
the swapped line as the structure demands. Then record it in the CONFLICTS
section: the line, the rule it breaks, and what it would cost to change
it. The owner decides, not you.

Return exactly these seven sections and nothing else.

**1. THE INJECTED SCRIPT**

A table: `Timestamp | Source line | Our line`

Timestamps from the teardown record. Source line quoted exactly. Our line
is the substitution. Mark any identical line "unchanged" in our column.

**2. DOMINANT TRAIT**

One line. The product has one trait that summarises it — the thing the whole
argument hangs from, taken from the product file and named in the product
file's own words. Not a list, not the three best benefits: one. Cite the line
in the product file it comes from. Every other trait blends in beneath it,
and a script that leads with a second trait is a script written for a
different product.

If the product file does not settle it, say `[SLOT: dominant trait — the
product file does not name one]` and carry on. Choosing one yourself is
inventing a positioning.

**The position settles it first.** If `{position}` names a `MECHANISM`, the
dominant trait is that mechanism, in `MECHANISM NAME`'s words, and the product
file is its receipt — cite both. The slot above is for a brand whose position
file and product file are both silent. A dominant trait that contradicts the
LINE is a defect: print the LINE beside it and flag it.

**3. FUNCTIONAL LEAD**

One line. **The functional product is what it DOES; the physical product is
what it is MADE OF, and only the functional performance sells.** Name the one
functional performance this injection sells, in the words the avatar would
use for it.

Then list the physical facts you carried across and, beside each, which of
these jobs it is doing — it may do only these: justify the price · document
the quality · promise durability · sharpen the mental picture · supply a
fresh believability mechanism. **A physical fact with no job on that list is
subordinate to nothing and does not belong in the script** — it is a
specification the viewer did not ask for. Cut it or move it under the
performance it proves.

A line that leads with an ingredient, a material or a component, where the
source's line led with an outcome, has inverted this and has to be rewritten.

**4. THE CHARACTERS**

Who is on screen, taken from {identity_anchors} — name, how they look, and
which role from the spec they fill. If a role has no real person assigned,
write `[SLOT: identity_anchors — role]` and do not describe an invented
person.

**5. THE SCENES**

One row per scene, following the teardown record's own scene breaks and
the spec's structural skeleton. Each scene gets: the script lines it
covers, its duration, exactly what happens in frame, and the production
instruction written for {production_route} — ready to execute, no
judgment calls left open. Match what the reference did in frame at each
beat.

**6. SLOTS**

Every `[SLOT: …]` from above, listed with what fact would fill it and who
would have it. If there are none, say so.

**7. CONFLICTS**

Every swapped line that breaks a brand rule: the line, the rule, and the
cost of changing it. If there are none, say so.

---

## WHAT IS NEVER SUBSTITUTED

Added at v5, after a run destroyed a video's punchline while reporting success.

Substitution replaces **the thing being sold**. It does not replace **the thing
being worn, revealed, or laughed at.**

### The failure this exists to stop

The source: a 70-year-old talks for 35 seconds about a red string swimsuit a
relative left behind, then walks through a doorway **wearing it**, holds both
arms out, pulls a horrified face, and retreats. The swimsuit is the setup, the
wardrobe, and the punchline.

The injection swapped the swimsuit for a tube of the brand's own product — the
object held up, the thing that "didn't work for me" — and then wrote:

> *"The speaker walks through the doorway in a sleeveless top or short sleeves,
> arms bare, having previously been covered. Structurally identical to the
> source's swimsuit walk-through."*

It is not structurally identical. The laugh is a person of that age walking out
in a string swimsuit. Changing into a short-sleeved top is getting dressed. The
video kept its shape and lost the only reason anyone watched to the end, and
every pass downstream inherited a version with no climax and reported fine.

### The rule

Before substituting any object, ask: **is this object worn, revealed, or
reacted to on camera?**

- **If it is only referred to or held up** — a bottle, a jar, a gadget on
  a counter — substitute freely. That is the job.
- **If it is worn, or the camera's reaction to it is the payoff** — it stays.
  Every time. The swimsuit stays a swimsuit. The dress stays a dress. The
  wardrobe change stays a wardrobe change.

**Some products cannot be worn at all.** When the source's object cannot
physically be our product, that is not a licence to change the object — it is
the signal that the object was never the swap.

### Where the product goes instead

It enters **after** the beat, as what the speaker does about what the reveal
exposed. They still walk out in the swimsuit. The camera still finds what the
reveal exposed on their arms and legs. That is our problem statement, delivered
by the source's own punchline — stronger than anything we would write, because
it is already funny and the speaker is already in on it.

Follow the source until the product has a reason to exist. On organic sources
that reason almost always arrives *after* the payoff, never in place of it.

### The check before this pass ends

Find the beat with the biggest visual reaction in it. Read our version of that
beat. **If a stranger would not laugh, wince or lean in at the same moment the
source made them, the substitution has eaten the asset.** Put the object back.

---

## EXAMPLES ARE EXAMPLES

Every specific in this prompt — an age, a gender, a garment, a body part, a
product category, a named person — is **illustrative only**. None of it
describes the asset in front of you. Read an example for the shape of the rule,
then apply the rule to what you actually have.

The subject may be any age, any gender, anywhere, selling anything. This chain
runs the same on one person on a beach, someone talking to camera in a parked
car, two people in a kitchen, or a pair of hands on a countertop. Nothing in
this prompt assumes which.

**Who is on camera comes from the teardown record, never from this prompt.** If
the teardown says a person in their fifties in a parked car, that is the
subject — every rule below applies to them unchanged, and any pronoun in an
example above is about that example, not about the person in front of you.

**And the variables are agnostic too.** An example may be reworked freely — it
is illustrative and always was. But nothing that gets filled in at run time
may name a brand, a product or a category: brand detail arrives only through
the variables above, resolved from that brand's own folder. A rule that
cannot be written without naming the brand belongs in the brand folder, not
in this prompt. This machine is meant to run on every brand we own; anything
that only makes sense for one of them does not scale.

---

## THE ROUTE CHANGES WHAT A PRODUCTION INSTRUCTION IS

`{production_route}` is not a label to repeat back. It decides what a
production instruction *means*, and the two are different documents for
different hands. Write for the route you were given and for no other.

### AI — nobody is on set

The instruction is addressed to a generator and to an editor with a footage
library. Every beat resolves to one of three things and says which:

- **CUT** — the brand already owns footage that carries this beat. Name the
  creator and what to look for. Owned footage is always the first thing to try.
- **GENERATE** — no owned footage carries it. Say what exists in the shot;
  cast people by their banked character names so they resolve to trained
  identities, never by fresh description.
- **COMPOSITE** — a label, a price, a guarantee, a wordmark. Never generated,
  always laid over from the real asset.

Two things only this route has to obey, both learned the hard way:

- **Never name camera equipment.** A generator has no camera it looks
  *through*; anything named is an object it can stand in the room. Say the
  framing and the light, and on any shot with a person, say the negative:
  no camera, no phone, no tripod, no lights in frame.
- **A named product is shown with its label.** If the script says a
  competitor's name, the hand holds that competitor, readable. Blanking it
  removes the mechanic and leaves the sentence.

### CREATOR — a real person films this

The instruction is addressed to someone holding a phone, in their own home,
with what they already own. It is a shot they can actually get:

- **Say what to film, not what to render.** Where they stand, what is behind
  them, what is in their hand, what they do with it.
- **Props are things they can buy or already have.** Name the product on the
  shelf at the drugstore; add the fallback line for when they cannot get it.
- **Wardrobe is theirs.** Describe the register, not a costume they have to
  source.
- **Their camera and their tripod are fine.** They are filming; the gear is
  how the shot exists, and none of the AI route's equipment rules apply.
- **Never direct a shot that needs a second person** unless the brief says
  who, and give a solo alternative when it does.

### FOUNDER — the founder films it

As CREATOR, but the person is known and their world is known. Skip the
fallbacks written for someone whose room you have not seen.

---

## THE ELEMENT LEDGER — the last thing you write, and it is not optional

The spec handed you numbered **ELEMENTs**, each with a **MANDATE**. Those are
the format's load-bearing parts — the reasons it works. Account for every one
of them, by number, in a table at the end of your output:

```
## ELEMENT LEDGER
| # | Element | Carried / Adapted / Dropped | How, or why not |
|---|---|---|---|
```

- **Carried** — it survives intact. Say in what beat.
- **Adapted** — it survives in a different form. Say what changed and why the
  mandate still holds.
- **Dropped** — say so out loud, and say what it costs. A dropped element is
  sometimes right. A dropped element nobody noticed never is.

**This exists because of a real failure (2026-09-11).**
Two mandated elements went missing between the spec and the brief and nothing
caught them:

- The spec mandated *"a real, ordinary, public, commercial space with its own
  visible business in the background — never a studio."* The injection wrote
  "a treatment room", because that is where our delivered footage happens to
  be shot. The generated scenes came back as a white void and read as stock
  photography — which is the one thing an authority format cannot be.
- The spec mandated the presenter *"physically hold and point to high-volume,
  **recognizable** category competitors."* The injection wrote "no label". The
  script still said the competitors' names, so the hand held a blank bottle
  while the line named a product — the mechanic removed, the sentence left.

Both came from the same instinct, and it is a good instinct pointed the wrong
way: **what we already own quietly overrode what the format requires.** Using
owned footage is right. Letting its limits rewrite a mandate without saying so
is not. If the footage cannot carry an element, that is an **Adapted** row with
its reasoning, or a **Dropped** row with its cost — and then somebody can
decide whether to shoot it, generate it, or accept the loss.

## Before you hand this over

Run these and **print the result of each**. A check whose result is not
written down did not happen, and a principle in a bullet list does not bind —
this is the same rule stated as work.

**Fix first, in the copy itself, then report.** You cannot go back and edit
what you already wrote, so what you print above must already be corrected. A
fix described under an uncorrected line leaves the wrong words where people
read from.

**1 · TIME.** Name every month, season and holiday you wrote. Beside each,
confirm it agrees with the date at the top. A month that is not the current
one is a defect unless it is plainly historical — substitute the real one and
report it fixed. "The bank said July" is not a defence.

**2 · SOURCE.** For every concrete specific — an age, a number, a duration, a
named behaviour, a quoted line — name the file it came from **and tag what
kind of language it is**: `VERBATIM` (a real person's recorded words) ·
`AVATAR` (a documented behaviour in the profile's phrasing) · `ANGLE` (a line
a marketer drafted) · `FILE` (a product or offer fact) · `POSITION` (the brand's
declared line, mechanism or stage, from `{position}`). These files record the
difference deliberately; flattening it presents a copywriter's invention as
something a customer said. Anything untraceable is removed or rewritten.

Then one line: how many specifics are `VERBATIM`, and which lines carry
`ANGLE` language. A piece resting mostly on `ANGLE` is not disqualified — it
is a piece whose realness has not been demonstrated, and whoever reads it
should be told that plainly.

**3 · THE LINE.** Print the `LINE` from `{position}`. Then name the beat, by
timestamp, where our script says it, its `SPINE`, or its `MECHANISM` in
`MECHANISM NAME`'s words. If no beat carries any of the three, print
`LINE HAS NO BEAT` and add it to CONFLICTS — the source's structure gave it no
room, the placement pass decides where it lands, and you do not add a line to
make room. Then print every `NEVER` word that appears in our column; each one
is a defect fixed in the copy above and reported here.

**4 · THE STORY.** Print `STORY` and `TELLER` from THIS RUN'S STORY. Map each of
the story's beats (BEFORE · REASON TO SWITCH · TURN · AFTER) to the timestamp in our
script that carries it, or print `BEAT MISSING` for it and add it to CONFLICTS. Then
one line: does the person on screen match the TELLER.
