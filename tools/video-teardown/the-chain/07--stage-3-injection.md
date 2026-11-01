Today is: {today}
Here is real language selected for this stage: {language}
Here is a complete teardown of a video asset: {teardown_record}

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
people name them — but they recorded when SHE spoke, not when this runs. Do
not inherit hers; substitute ours. A genuine historical reference — a decade,
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
  make it more polished than the source.
- **Lines with no brand content stay identical.** Copy them across
  verbatim and mark them unchanged.

Swap only what is genuinely brand-specific: the brand name, product name,
ingredients and actives, the mechanism, the problem and the body part it
affects, the competitor or procedure being displaced, the origin story,
the offer, and any numbers.

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

Return exactly these five sections and nothing else.

**1. THE INJECTED SCRIPT**

A table: `Timestamp | Source line | Our line`

Timestamps from the teardown record. Source line quoted exactly. Our line
is the substitution. Mark any identical line "unchanged" in our column.

**2. THE CHARACTERS**

Who is on screen, taken from {identity_anchors} — name, how they look, and
which role from the spec they fill. If a role has no real person assigned,
write `[SLOT: identity_anchors — role]` and do not describe an invented
person.

**3. THE SCENES**

One row per scene, following the teardown record's own scene breaks and
the spec's structural skeleton. Each scene gets: the script lines it
covers, its duration, exactly what happens in frame, and the production
instruction written for {production_route} — ready to execute, no
judgment calls left open. Match what the reference did in frame at each
beat.

**4. SLOTS**

Every `[SLOT: …]` from above, listed with what fact would fill it and who
would have it. If there are none, say so.

**5. CONFLICTS**

Every swapped line that breaks a brand rule: the line, the rule, and the
cost of changing it. If there are none, say so.

---

## WHAT IS NEVER SUBSTITUTED

Added at v5, after a run destroyed a video's punchline while reporting success.

Substitution replaces **the thing being sold**. It does not replace **the thing
being worn, revealed, or laughed at.**

### The failure this exists to stop

The source: a 70-year-old talks for 35 seconds about a red string bikini her
niece left her, then walks through a doorway **wearing it**, holds her arms
out, pulls a horrified face, and retreats. The bikini is the setup, the
wardrobe, and the punchline.

The injection swapped the bikini for a tube of body scrub — the object she
holds up, the thing that "didn't work for her" — and then wrote:

> *"She walks through the doorway in a sleeveless top or short sleeves, arms
> bare, having previously been covered. Structurally identical to the source's
> bikini walk-through."*

It is not structurally identical. The laugh is a woman of that age walking out
in a string bikini. Changing into a short-sleeved top is getting dressed. The
video kept its shape and lost the only reason anyone watched to the end, and
every pass downstream inherited a version with no climax and reported fine.

### The rule

Before substituting any object, ask: **is this object worn, revealed, or
reacted to on camera?**

- **If it is only referred to or held up** — a serum, a supplement, a gadget on
  a counter — substitute freely. That is the job.
- **If it is worn, or the camera's reaction to it is the payoff** — it stays.
  Every time. The swimsuit stays a swimsuit. The dress stays a dress. The
  wardrobe change stays a wardrobe change.

Our product is a scrub. **Nobody can wear a scrub.** When the source's object
cannot physically be our product, that is not a licence to change the object —
it is the signal that the object was never the swap.

### Where the product goes instead

It enters **after** the beat, as what she does about what the reveal exposed.
She still walks out in the bikini. The camera still finds the spots on her
arms and legs. That is our problem statement, delivered by the source's own
punchline — stronger than anything we would write, because it is already funny
and she is already in on it.

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
runs the same on a woman on a beach, a man talking to camera in his car, two
people in a kitchen, or a pair of hands on a countertop. Nothing in this prompt
assumes which.

**Who is on camera comes from the teardown record, never from this prompt.** If
the teardown says a man in his fifties in a parked car, that is the subject —
every rule below applies to him unchanged, and any pronoun in an example above
is about that example, not about him.

**And the variables are agnostic too.** An example may be reworked freely — it
is illustrative and always was. But nothing that gets filled in at run time
may name a brand, a product or a category: brand detail arrives only through
the variables above, resolved from that brand's own folder. A rule that
cannot be written without naming the brand belongs in the brand folder, not
in this prompt. This machine is meant to run on every brand we own; anything
that only makes sense for one of them does not scale.

---

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
a marketer drafted) · `FILE` (a product or offer fact). These files record the
difference deliberately; flattening it presents a copywriter's invention as
something a customer said. Anything untraceable is removed or rewritten.

Then one line: how many specifics are `VERBATIM`, and which lines carry
`ANGLE` language. A piece resting mostly on `ANGLE` is not disqualified — it
is a piece whose realness has not been demonstrated, and whoever reads it
should be told that plainly.
