Here is a complete teardown of a STATIC IMAGE AD: {teardown_record}

And here is its replication spec: {replication_spec}

Our brand: {brand_name}. Our avatar: {avatar}. Our product details:
{product_file}. Our offer: {offer_file}. Our customer language bank:
{language_bank}. Our identity anchors: {identity_anchors}. We are producing
this via {production_route}.

Rebuild this exact static ad for our brand and turn it into a production
brief.

**THIS IS A SUBSTITUTION, NOT A REWRITE.**

Work through the teardown record's zone table one zone at a time, in reading
order. For each source zone, output one zone for us. The source layout is the
template — you are swapping the brand-specific words out of it and our
brand-specific words in, and changing nothing else.

Hold all of this exactly as the source has it:

- **Sentence structure and word order.** If the source says "Do not use my X
  on the Y on your body more than twice a week," ours says "Do not use my
  [our X] on the [our Y] on your body more than twice a week."
- **Zone count and order.** One output zone per source zone. Never merge two
  zones, never split one, never drop one, never reorder them, never add one.
- **Length.** Each line stays about as long as the source line, because the
  source line was set at a type size that fits the space it occupies. A
  substitution twice the length is a layout change wearing a copy change.
  Where our words genuinely will not fit, write the line anyway and record it
  in CONFLICTS with the zone and the overflow.
- **Register and case.** Keep the all-caps, the sentence case, the period at
  the end of the fragment, the contractions, the plain words. Do not make it
  more polished than the source.
- **Zones with no brand content stay identical.** Copy them across verbatim
  and mark them unchanged.

Swap only what is genuinely brand-specific: the brand name, product name,
ingredients and actives, the mechanism, the problem and the body part it
affects, the competitor or procedure being displaced, the origin story, the
offer, and any numbers.

**Never swap the subject out of a frame whose mechanic depends on what the
subject is.** Read the replication spec's LOAD-BEARING list before you touch
the subject. If any mechanic there rests on the subject's kind — a neoteny or
cute response (the animal, the baby), a child's scale, a body part the proof
is performed on, a face whose age is the claim — the subject stays exactly
what it is, and you swap around it: the setting, the wardrobe, the props, the
words. A dog stays a dog. If SWAPPABLE says otherwise, LOAD-BEARING wins and
you record the contradiction in CONFLICTS.

Measured cause, 2026-09-14: a dog standing over the photographer's lap became
a woman because the spec listed the subject in both lists, and the draft lost
the only mechanic the source had.

**Do not improve the source.** Do not soften a claim, fix a tone, correct an
exaggeration, replace a device you find distasteful, or restructure a zone
because a better version occurred to you. Your judgment about whether the
source is a good ad is not wanted here — it already performed, which is why
it was swiped.

**Do not invent.** If a line needs a fact we have not supplied — a price, an
offer, a user count, a study, a person — put `[SLOT: what's needed]` inline
exactly where the fact goes, and list it at the end. Never guess a number.

The test for "supplied" is exact: **a fact is ours only if it is written in
one of the files above.** Not something you know about the category, not
something that is probably true of a brand like ours, and above all not
something you read in the source ad. Three cases account for nearly every
leak, and each has one correct move:

- **The source's offer is the source's.** A discount percentage, a guarantee
  length, a price drop, a limited window — those are facts about *their*
  brand. Ours has exactly the offers written in {offer_file} and no others.
  Substitute a claimed promotion only if the offer file carries it; otherwise
  the swapped zone keeps the source's shape with `[SLOT: current promotion —
  needs owner approval]` in place of the claim. A source ad carrying
  `SAVE UP TO 25%` does not license ours to carry a number.
- **Only the supplied product is ours to describe.** If the ad needs a second
  product, you may name it if the offer file names it, but you may never
  state its ingredients, texture, mechanism or claims from memory. Write
  `[SLOT: <product name> — ingredients and claims]` and move on.
- **The source's actives are the source's.** Never carry a source ingredient
  into our line, and never invent one to fill the slot the source ingredient
  occupied. Ours come from {product_file} only.

A `[SLOT: …]` costs a reviewer thirty seconds. An invented sale or an
invented ingredient goes into the feed.

**Conflicts get flagged, never fixed.** If a swapped line would break a rule
in {language_bank} or {product_file}, still write the line as the structure
demands. Then record it in the CONFLICTS section: the line, the rule it
breaks, and what it would cost to change it. The owner decides, not you.

Return exactly these five sections and nothing else.

**1. THE INJECTED FRAME**

A table: `Zone | Position | Source copy | Our copy`

Zones and positions from the teardown record, carried unchanged. Source copy
quoted exactly. Our copy is the substitution. Mark any identical zone
"unchanged" in our column.

**2. THE SUBJECT**

Who is in frame. **Cast one man from the roster below, by name.** On a static
the face is the entire casting decision and there is no performance to carry
it, so this section is load-bearing, not administrative.

<roster>
{roster}
</roster>

Pick on the `problem` field first — the man whose stated problem is the one
this ad is about — then on lane, then on age. **Name him, and copy his
`reads` and `face` lines verbatim as the description.** Never describe a man
who is not on that list: a brief that asks for someone the roster does not
have is a brief that cannot be produced, and the substitution then happens
silently at generation time by whoever is holding it.

If the ad shows no person, write `none`. If the roster genuinely has nobody
for this problem and lane, say so and name the closest — that is a casting
gap worth knowing about, not a reason to invent a man.

{identity_anchors} still rules what may be generated of him.

State explicitly whether {production_route} permits a generated likeness. If
it does not, say so here in one line — the build sheet downstream must not
discover it.

**3. THE ART DIRECTION**

One row per zone that carries imagery, following the spec's image mandate.
Each gets: what is in frame, the light, the lens and distance, the depth of
field, the set, the props, and the production instruction written for
{production_route} — ready to execute, no judgment calls left open. Match
what the reference did in frame.

Where the spec's image mandate says the frame must **demonstrate** the
mechanism on the problem, say how ours does it, using only what
{product_file} documents about how the product is applied and what it
visibly does. If the product file does not document a visible action, write
`[SLOT: what the product visibly does on application]` rather than inventing
one.

**4. SLOTS**

Every `[SLOT: …]` from above, listed with what fact would fill it and who
would have it. If there are none, say so.

**5. CONFLICTS**

Every swapped line that breaks a brand rule, and every line that overflows
its zone: the line, the rule or the overflow, and the cost of changing it. If
there are none, say so.


## Their structure. Our words. Never their words.

You are given the swiped ad's own copy so you can see the *role* each line
plays — what an eyebrow does, what a sub-headline promises, how a headline
lands. You are never given it to reuse.

**No run of three or more consecutive meaningful words from the swiped ad may appear in
anything you write.** Not in the headline, not in the eyebrow, not in the
body, not in the offer block. Rewrite the line so it makes our claim about
our product with our evidence behind it.

Measured cause, 2026-08-31: a headline came back as "becomes your perfect
skin" — the swiped ad's headline, word for word. It reads fine and it is
worthless: it is their promise about their product, in their language,
sitting in our ad. The build now checks for this and flags it, so a
verbatim line will be caught — but being caught late costs a whole run.

The test to apply to every line you write: **if the swiped brand could run
this line unchanged, it is not injection.**

## The furniture carries the offer. Fill it.

`marks` and `stickers` in the layout data are slots exactly like the text
zones, and the same rule applies: **fill every one.**

- A **mark** keeps its role. A warning triangle that carried urgency stays a
  warning triangle; it is recoloured to ours, never deleted.
- A **sticker** keeps its shape, its angle and its position, and takes our
  offer. Theirs says "60% OFF" and "FREE Mystery Gift"; ours says what is
  actually true — the multi-tube saving, the guarantee, the price, the free
  shipping threshold.

Measured cause, 2026-08-31: a rebuild dropped a warning icon and two sticker
callouts because they were not text. The words were all correct and the ad
still did not read like the ad — the stickers were where the offer lived.

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
