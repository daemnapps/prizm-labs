Today is: {today}
The month being composed: {month}
Here is what a slot is, and the rules a composed month obeys: {slot_spec}
Here are the kinds of email this brand knows, each with its role in the arc: {types}
Here are the eight segments, with their sizes and their caveats: {segments}
Here are the cultural moments, per avatar, in four streams: {moments}
Here is what the sending has taught, in numbers: {learnings}
Here is the evidence, read into numbered findings you will cite: {findings}
Here is how cold every type and every cell is, computed from the record: {coldness}
Here is every email already sent — its file, its type, its subject: {sent_library}
Here are the avatars and their sub-avatars: {avatars}
Here are the products: {products}
Here are the offers, per avatar: {offers}

Compose one month of email slots. A slot is a move in a sequence, never a
standalone send — it knows what it earns, what it sets up, and what has to
follow it.

**The unit of planning is the CELL, not the day.** A cell is segment × avatar
× sub-avatar. The email-per-day question is dead (the owner, 2026-08-29): what
matters is which cells exist in this database, which have been cold longest,
and what each is owed. Volume is an output — a database with eleven
sub-avatars across eight segments supports far more sends than a calendar
mindset would dare, because no one person receives more than their own cell's
stream. Plan cell by cell, then place the results on dates.

**What you decide, and on what evidence:**

- **Which cells this month serves.** Walk the matrix: every avatar, every
  sub-avatar under it, crossed with the segments that avatar actually
  occupies. Say which cells you are serving, and which you are deliberately
  leaving cold and why. A sub-avatar that has never been spoken to is the
  strongest claim on a slot there is.
- **How many sends.** Derived from the cells served — never from a per-day
  or per-month habit. State the per-person arithmetic: how many emails a
  single reader in each segment actually receives. That number, not the
  total, is the one that has to stay sane.
- **The mix.** Balance the five categories against the learnings' numbers and
  the coverage gaps, not against a formula. Draw from the WHOLE type
  catalogue above — a month that uses only proven types is repeating itself.
- **The timing.** The hour comes from the findings — cite the finding when you follow it, and state the reason when you depart from it. Day of week is not a
  lever — do not pretend it is.

**The rules, restated as they bind you:**

- **One avatar per slot, or explicitly `none`.** Never two. A `none` slot
  addresses everyone and must genuinely address everyone.
- **One sub-avatar per slot, or explicitly `none`.** A sub-avatar slot speaks
  to that person specifically — one sub-avatar's email is not another's.
  `none` means the whole avatar, and is a choice, not a default.
- **Every ask is earned.** A slot with `role: asks` needs at least one `earns`
  slot to the same segment scheduled before it in this month — or name the
  specific already-sent email that earned it, from the library above.
- **Every obligation is met.** If a slot's type names a `then`, schedule the
  follow-up or do not schedule the slot. Recovery types (`last-chance`,
  `objection-shot`, `guarantee`) are contingent — schedule them with
  `follows` naming the ask they recover, and mark them contingent in `why`.
- **Nothing repeats spent ground.** The library above is the ledger. A slot
  whose occasion-and-angle a sent subject already covered is a different slot
  or no slot.
- **Fit before granularity.** Sub-avatar targeting is carried by the language
  bank (rows are tagged by sub). Lifecycle language is NOT — nine-tenths is
  unsegmented — so a slot may target a lifecycle segment commercially but may
  not claim lifecycle-specific language.
- **Three streams planned, one held open.** Fixed, sports and seasonal moments
  are scheduled. Live ones cannot be — leave at least two slots explicitly
  open, dated, with `occasion` set to `HELD OPEN — live`.
- **An avatar with no section in the offer bank carries no offers.** That is
  a recorded fact about the brand, not an oversight to paper over. Such a
  slot either carries no offer or does not exist.
- **Never invent.** No product, offer, moment, segment, sub-avatar or
  customer that is not in the material above. A slot that needs something
  missing marks it `[UNFILLED: what it needed]` and stands.

**What a slot is not:** it carries no copy, no subject line, no layout. Those
are production's job. You are deciding what exists and when — not what it says.

**Return exactly this, in this order:**

First, `SLOTS JSON` — one fenced ```json block, a list of slots, each:

```
{
  "id": "sep-01",            // <mon>-<nn>, in date order
  "date": "YYYY-MM-DD",
  "hour": 17,                // 24h; per the learnings; departures explained in why
  "local": true,             // each person's local time, or one fixed time
  "segment": "...",          // one of the eight, by its Core | name
  "avatar": "...",           // one of this brand's avatars, or none
  "sub_avatar": "...",       // a sub key from that avatar's roster, or none
  "category": "...",         // Promotional | Educational | Cultural | Community | Brand
  "type": "...",             // a key from the catalogue
  "role": "...",             // the type's role, carried
  "occasion": "...",         // the specific reason this exists NOW, or HELD OPEN — live
  "product": "...",          // a product key, or none
  "offer": "...",            // an offer key from the bank, or none
  "follows": "...",          // a slot id this answers, or null
  "then": "...",             // the slot id that meets this slot's obligation, or null, or "contingent"
  "spent": "...",            // one line: the nearest ground already covered, so production knows what to avoid
  "source": "...",           // a filename from the library whose shape this takes, or "[UNFILLED: no source fits]"
  "why": "..."               // one or two sentences: why this cell, this move, now.
                             // CITE your evidence: a finding id like [F3], a
                             // moment key, or a coldness line. A why that
                             // cites nothing is a hunch, and hunches are
                             // flagged by the checker.
}
```

Then **THE MATRIX, READ ALOUD** — a short section, in prose:

- The cells served this month, and the cells deliberately left cold with the
  reason each stays cold.
- The per-person arithmetic: what one reader in each segment receives.
- The mix against the learnings, and which never-sent types get a first
  outing.
- What was deliberately left out, and every `[UNFILLED: …]` in one place.

Rank nothing. Recommend no slot over another. The machine composes; choosing
is a human act.
