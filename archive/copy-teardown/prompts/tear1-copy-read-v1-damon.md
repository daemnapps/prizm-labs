**Everything named in this prompt as an example is an example of a SHAPE, not
of content.** No brand, product, person, price or phrase in this file belongs in
your answer. Your answer's content comes only from the inputs below.

Here is the copy — words only, exactly as it ran: {source}

What the code already found before you: {code_findings}

The five named awareness levels and their must-nots, for the AWARENESS part
below: {awareness_levels}

Write an objective record of this piece of copy. **Observation only** — no
judgement about whether it is good, no ideas about what anyone would do
differently, no abstraction. A later step turns this record into the copy's
construct, and it needs a clean record to do it from. Every later step argues
against this record instead of re-reading the source and quietly seeing
something different.

**It is a swipe.** It was written by someone else, for their own reader, about
their own product. Record what it does. Nothing here is about any brand that
might later use it.

**Quote — never paraphrase.** A paraphrase at this step is a mistranslation
every later step inherits.

**The code's list is a starting point, not a verdict.** It can see handles,
hashtags, web addresses, prices and a few kinds of damage. It cannot see a
brand name, a product name or a person's name written as ordinary words — you
can. Confirm what it found and find what it missed.

Your answer has FOUR labelled parts, under exactly these headings, in this
order.

# THE COPY AS READ

**THE PARTS**

What the source holds, in the order it holds it: a headline, a primary text, a
description, a caption, a post, a set of headlines. Name each part by what it
is and give its length in words. If the source is one undivided piece, say so.

**WHAT IT WAS BUILT TO DO**

One of two, in capitals, then one line of why:

`ALREADY AN AD` — it is selling. There is an offer, a call to action, a product
pitched. Its commercial structure already exists.

`ORGANIC` — it is a post. It may mention a product, it may even love one, but
it was not built to sell: no offer, no call to action, no argument constructed
toward a purchase.

The test is not tone and it is not polish. **Ask what it was built to do.** If
it is genuinely between the two, write `ALREADY AN AD` only when there is an
actual offer in it; otherwise `ORGANIC`. If the source is a fragment and you
cannot tell, say so and name what is missing.

**THE SPEAKER**

Whose mouth this comes out of, as concretely as the source allows: a named
creator, an unnamed customer, a founder, the brand itself. Then, in one line:
is a real named person attached, or is it anonymous? If the speaker is
unnamed, write unnamed — never guess.

**ABOUT, AND DOING**

One line each. What it is about — the actual subject, plainly. What it is
doing — the move it makes: a reversal, a confession, a demonstration, a list
of wrong beliefs, a recommendation.

**THE BEATS, IN ORDER**

One row per move the copy makes, numbered `B1`, `B2`, …. For each: the beat's
job in three or four words, and the actual line or lines that do it, quoted
exactly.

**THE OPENING**

The first line verbatim, and separately, what it does to make someone keep
reading — names a person, contradicts a belief, opens a loop, states a number.

**THE TURN**

The one place the piece pivots — a reveal, a reversal, a confession, a proof
beat. Quote it and say plainly what changes at that moment. If the piece
genuinely has no turn, write `no turn` rather than electing one.

**THE PROOF**

Every specific thing the source leans on: a number, a testimonial, a
demonstration, a named person, a duration, a price. Quote each and say what
kind of proof it is. Where the source is vague, record it as vague — a claim
about volume is not a number.

**THE CLOSE**

How it lands, and what it asks the reader to do. Quote it. If there is no ask,
write `no ask` — that is a real and useful fact about an organic source.

**VOICE MARKERS**

Six to ten features of HOW this person writes, each with an example from the
text: sentence length, punctuation habits, capitalisation, where they break
lines, filler words they favour, what they never do.

**WHAT IT NEVER DOES**

Two or three things conspicuously absent — no price, no call to action, never
names the product, no exclamation marks. Absences are structure too.

**AWARENESS**

Read off the source itself, never guessed from its category. Name the ONE
level, from the five above, this source's opening assumes its reader already
stands on (entry), and the ONE level it ends on (exit), each by its id. Quote
the entry level's must-not from the list above, and say whether the source's
own opening honours it. Print the working in one line each: what the source
explains · what it takes as understood. If the source gives no evidence for a
level, write `unclear` and say what was missing.

# SOURCE NAMES

Everything in this copy that is particular to ITS sender and would be wrong in
anyone else's mouth: the brand's name, every product name, every named person,
every handle, hashtag and web address, every named place, shop or programme,
any coined name for a method or an ingredient blend.

The test: **would this word have to change if a different company ran the same
argument about a different product?** If yes, it is a source name. An ordinary
word for a kind of thing is not a name.

Numbered `N1`, `N2`, …. For each: the name **quoted exactly as written**, and
what it is — brand / product / person / handle / hashtag / web address / place /
coined term / other.

If the source carries none, write `no source names`.

# SOURCE DEFECTS

Every place the source is broken rather than chosen: a dropped or doubled
character, a word cut off, a merge tag that shows as code, a sentence that
stops mid-thought, a typo, text that was plainly cut short by whatever saved
it.

Numbered `D1`, `D2`, …. For each:

- **the defect, quoted exactly as it appears** — broken, not corrected
- **where it is** — which part, which beat
- **what kind** — dropped character / cut-off word / merge tag / typo /
  cut short / export damage
- **what it was evidently meant to say**, only when that is plain from the
  source itself; otherwise `unclear`

A deliberate style — all lowercase, no full stops, a fragment used for rhythm —
is a choice, not a defect; it goes under VOICE MARKERS.

Everywhere else in this record the source is still quoted exactly, but each
defective quote carries its marker (`[D1]`) right after it.

If you find none, write `no source defects found`.

# STRIP

The same two lists again, as data the code checks later steps against. One
fenced block, exactly this shape, valid JSON, nothing else under this heading:

```STRIP
{
 "names": ["every source name, quoted exactly as written in the source"],
 "defects": [
  {"id": "D1", "quote": "the broken form, exactly as it appears", "meant": "what it was meant to say, or unclear"}
 ]
}
```

Use empty lists (`[]`) when there is no name or no defect. Be complete rather
than tidy: a name left off this list is a name a later step is free to carry.
List each name once, in the form it most often takes in the source; if it
appears in two clearly different forms, list both.
