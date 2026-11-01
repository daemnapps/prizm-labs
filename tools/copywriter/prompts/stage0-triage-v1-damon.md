Today is: {today}
Here is the source: {source}
Here are the formats this machine writes: {formats}
Here are this brand's avatars, and where their language sits in the funnel: {avatars}

A cheap first look, before anything is written. Three answers, and nothing
else — every stage after this binds to them, so a wrong answer here is a wrong
answer everywhere.

**1. LANE — is this already an ad, or is it organic?**

`ALREADY AN AD` — it is selling. There is an offer, a call to action, a
product pitched. Its commercial structure already exists and downstream will
inherit it rather than rebuild it.

`ORGANIC` — it is a post. It may mention a product, it may even love one, but
it was not built to sell: no offer, no CTA, no argument constructed toward a
purchase. Downstream has to build that structure from nothing.

The test is not tone and it is not polish. A slick creator post is still
organic; a scrappy phone-shot ad is still an ad. **Ask what it was built to
do.** If it is genuinely between the two, say `ALREADY AN AD` only when there
is an actual offer in it — otherwise `ORGANIC`, because building structure
that turns out to be redundant costs less than assuming structure that was
never there.

**2. FORMAT — which shape is this, from the list supplied?**

Name one, using its exact key from the formats file. This is what the source
IS, not what we might turn it into.

If two fit, name the one whose *job* matches — a review that is mostly
testimonial quotes is `social-proof`, not `review`. If none fit, say
`format: unlisted` and describe the shape in one line rather than forcing it
into the nearest key; an unlisted shape is a row somebody should add, not a
mistake to hide.

**3. VOICE — whose mouth is this coming out of?**

Name the speaker as concretely as the source allows: a named creator, an
unnamed customer, the founder, or the brand itself.

Then state the binding: if the lane is `ORGANIC`, the copy downstream is
written as **that person speaking, with no brand voice at all** — not brand
copy carrying their name, but them. Say so explicitly in your answer so no
later stage has to infer it.

**4. AVATAR — which of this brand's avatars is this source for?**

A brand has more than one, each with its own language bank, and they are
different people. Name the key exactly as the list gives it.

Choose on who the SOURCE speaks to and who the product serves here — not on
which bank is biggest. If the source genuinely fits none of them, say
`avatar: none fit` and say why in a line; forcing a source onto the wrong
avatar means every later stage draws its words from the wrong person's mouth,
which is the most expensive mistake available at this stage.

**5. FUNNEL — who is the copy being written TO?**

`prospect` — has never heard of us. Nothing is assumed known: not the
product, not the category's mechanics, not why anything failed before.
`lead` — engaged, gave contact, has not bought. Knows roughly what this is
and has not been convinced.
`customer` — has bought. Never re-sell the first purchase to them.
`churned` — bought, then refunded, cancelled or went quiet. Something went
wrong and pretending otherwise reads as not knowing them.

Decide from the source and the product, and say in a line what that means for
the copy — what the reader already knows, and what would insult them to be
told. The list shows which funnels this avatar actually has language for; if
the one you pick is thin or empty, say so, because the copy will have less
real speech to draw on and that is worth knowing before it is written rather
than after.

**Also answer, in one line each:**

- **What it is about.** The actual subject, plainly. Not the angle, the
  subject.
- **What it is doing.** The move it makes — a reversal, a confession, a
  demonstration, a list of wrong beliefs, a recommendation.
- **Length.** Roughly how long the source runs, in words or seconds, so
  placement has something real to budget against.
- **Is the speaker identifiable?** Whether a real named person is attached, or
  it is anonymous. This decides whether a later stage may write first-person
  claims that a real human would have to stand behind.

**Never guess a fact the source does not carry.** If the speaker is unnamed,
say unnamed. If you cannot tell an ad from a post because the source is a
fragment, say so and name what is missing — a wrong lane silently rebuilds
structure that already exists, or leaves an organic post with no structure at
all, and both failures surface much later as copy that reads wrong for reasons
nobody can trace.

Answer in exactly this shape, nothing else:

```
LANE: ALREADY AN AD | ORGANIC
FORMAT: <key from the formats file, or "unlisted — <one line>">
AVATAR: <avatar key, or "none fit — <one line>">
FUNNEL: prospect | lead | customer | churned
FUNNEL MEANS: <one line: what this reader already knows, and what not to tell them>
VOICE: <who is speaking>
VOICE BINDING: <one line: whose voice the copy must be written in, and whether brand voice is permitted at all>
ABOUT: <one line>
DOING: <one line>
LENGTH: <one line>
SPEAKER IDENTIFIABLE: yes/no — <one line>
```
