Today is: {today}
The month being composed: {month}
Here is what a slot is, and the rules a composed month obeys: {slot_spec}
Here are the kinds of email this brand knows, each with its role in the arc: {types}
Here are the eight segments, with their sizes and their caveats: {segments}
Here are the cultural moments, per avatar, in four streams: {moments}
Here is what the sending has taught, in numbers: {learnings}
Here is every email already sent — its file, its type, its subject: {sent_corpus}
Here are the avatars and their sub-avatars: {avatars}
Here are the products: {products}
Here are the offers, per avatar: {offers}

Compose one month of email slots. A slot is a move in a sequence, never a
standalone send — it knows what it earns, what it sets up, and what has to
follow it.

**What you decide, and on what evidence:**

- **How many sends.** Cadence is not a rule. Read it off the history — the
  corpus averages roughly fifteen a month — and off what the learnings say a
  send earns per segment. State the number you chose and why.
- **The mix.** Balance the five categories against the learnings' numbers and
  the coverage gaps, not against a formula. A well that has fuel and no use is
  an argument for a slot; a category that costs more than it earns is an
  argument for fewer.
- **The timing.** The hour comes from the learnings. Day of week is not a
  lever — do not pretend it is.
- **Coverage over repetition.** Fill toward the cells that have been cold
  longest: the sub-avatar never spoken to, the pain point never addressed, the
  type never sent, the proven moment left unused. The corpus above is the
  record of what has already been covered.

**The rules, restated as they bind you:**

- **One avatar per slot, or explicitly `none`.** Never two. A `none` slot
  addresses everyone and must genuinely address everyone.
- **Every ask is earned.** A slot with `role: asks` needs at least one `earns`
  slot to the same segment scheduled before it in this month — or name the
  specific already-sent email that earned it, from the corpus above.
- **Every obligation is met.** If a slot's type names a `then`, schedule the
  follow-up or do not schedule the slot. Recovery types (`last-chance`,
  `objection-shot`, `guarantee`) are contingent — schedule them with
  `follows` naming the ask they recover, and mark them contingent in `why`.
- **Nothing repeats spent ground.** The corpus above is the ledger. A slot
  whose occasion-and-angle a sent subject already covered is a different slot
  or no slot.
- **Fit before granularity.** Nine-tenths of the customer language is
  unsegmented. A slot may target a lifecycle segment commercially (the offer
  fits Returning customers), but it may not claim language finer than the
  brand can carry.
- **Three streams planned, one held open.** Fixed, sports and seasonal moments
  are scheduled. Live ones cannot be — leave at least two slots explicitly
  open, dated, with `occasion` set to `HELD OPEN — live`, so a trend or a
  player moment has somewhere to land without displacing the plan.
- **gift-buyer has no offers.** That is a recorded hole, not an oversight to
  paper over. A gift-buyer slot either carries no offer or does not exist.
- **Never invent.** No product, offer, moment, segment or customer that is not
  in the material above. A slot that needs something missing marks it
  `[UNFILLED: what it needed]` and stands.

**What a slot is not:** it carries no copy, no subject line, no layout. Those
are production's job. You are deciding what exists and when — not what it says.

**Return exactly this, in this order:**

First, `SLOTS JSON` — one fenced ```json block, a list of slots, each:

```
{
  "id": "sep-01",            // <mon>-<nn>, in date order
  "date": "YYYY-MM-DD",
  "hour": 17,                // 24h; the learnings' evidence, stated per slot in why if it departs
  "local": true,             // each person's local time, or one fixed time
  "segment": "...",          // one of the eight, by its Core | name
  "avatar": "...",           // fed-up-king | glow-up | gift-buyer | none
  "category": "...",         // Promotional | Educational | Cultural | Community | Brand
  "type": "...",             // a key from the catalogue
  "role": "...",             // the type's role, carried
  "occasion": "...",         // the specific reason this exists NOW, or HELD OPEN — live
  "product": "...",          // a product key, or none
  "offer": "...",            // an offer key from the bank, or none
  "follows": "...",          // a slot id this answers, or null
  "then": "...",             // the slot id that meets this slot's obligation, or null, or "contingent"
  "spent": "...",            // one line: the nearest ground already covered, so production knows what to avoid
  "source": "...",           // a filename from the corpus whose shape this takes, or "[UNFILLED: no source fits]"
  "why": "..."               // one or two sentences: why this slot, here, to these people
}
```

Then **THE MONTH, READ ALOUD** — a short section, in prose: the send count and
why, the mix against the learnings, which cold cells this month warms, what
was deliberately left out, and every `[UNFILLED: …]` collected in one place.

Rank nothing. Recommend no slot over another. The machine composes; choosing
is a human act.
