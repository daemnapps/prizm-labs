Today is: {today}
The month being planned: {month}
Here is the state of the brand, assembled from its own record: {state}
Here is the month's dated skeleton — every public holiday and cultural moment that actually lands in it, with its real dates: {skeleton}

Decide WHO gets spoken to this month. Nothing else — no emails, no
occasions, no copy, no counts. This is the decision everything after it is
built on, so it is decided from the record and defended against the record.
No human signs it off; the checker verifies it and the state sheet is the
only evidence that counts.

## The targeting model (RULED, the owner, 2026-08-31)

**The segment is the targetable unit.** Segments are real, live, and sized —
the platform knows exactly who is in them.

**Sub-avatars do not appear at this level at all** (RULED, the owner,
2026-08-31). No profile carries a sub-avatar tag and the language bank's sub
tags cover a fraction of rows too small to plan on. They are not a targeting
unit and not a variant unit. Do not name one.

**AVATARS ride as VARIANTS.** A segment holds every avatar mixed together
and nobody can tell who is who. So a send to a segment carries one variant
per avatar worth reaching — same occasion, same offer, the argument written
through that avatar's own world and language. Everyone in the segment gets
one of them; the split test reports which won.

**One variant addresses one avatar.** Never blend two — that rule holds
inside a variant exactly as it holds for a whole email.

**This is how the missing data gets made.** Which variant wins IS the
measurement of which avatar dominates that segment. Plan the month so it
produces that evidence, and say so in the why.

**Variant count is capped by two things, and you state both:**
1. **Audience** — each variant needs enough people to mean anything. Roughly:
   over 50,000 in the segment supports 4 · 10,000–50,000 supports 3 ·
   3,000–10,000 supports 2 · under 3,000 supports 1 (no test). Platform
   guidance is a maximum of 4 variants per test.
2. **Language depth** — a variant only exists for an avatar with language
   to write it from. An avatar with a few hundred rows cannot carry a
   variant against one with thousands; give it its own small send or let it
   rest. Never promise a voice the brand cannot carry.

**Variant count is therefore usually small: the number of avatars with real
depth, capped by the audience band.** Two honest variants beat four thin
ones.

## How to decide, and on what evidence

- The coldness table is the arithmetic. A cell or type never spoken to is
  the strongest claim on attention there is. Cite the line.
- The findings are the economics. Cite the finding id ([F3]).
- What sending EARNS per audience — revenue per recipient against
  unsubscribe cost — is the frequency signal. It decides which segments are
  live and which rest. It is not a quota.
- Serving every segment every month is not the goal. A deliberate rest with
  a reason beats a thin obligatory send.
- The skeleton tells you what the month IS — a month with Black Friday in it
  wakes segments a quiet month would let rest. Say so when it does.

**You do not decide how many emails anyone gets.** Email is programmatic;
there is no budget, no ceiling and no floor (RULED, the owner, 2026-09-01). The
month's volume is built later from what is actually happening — the dated
holidays, the moments, the cold ground. What you decide about a segment is
only this: is it live this month, or does it rest.

**Never invent.** No segment, avatar or sub-avatar that is not in the state
sheet. Nothing here proposes email content — that is a later stage's job.

## A dated angle must sit inside its own window

RULED 2026-09-10 (the owner: "I still see some labor day email in the figma for
late september"). An angle that names a holiday, a season or an event is a
promise about WHEN the send goes out. This stage wrote one `labor-day` angle
and handed it to every variant of that avatar for the whole month, including
sends three weeks after Labor Day.

- An angle may name a moment **only if that moment's window contains the dates
  this cell will actually be sent on.** The month's live windows are above.
- One angle per variant, written for THAT variant. Do not reuse a single angle
  across a month because it fits the avatar — it has to fit the send.
- An angle with no moment in it is always safe. Reach for a dated one only
  when the timing is the argument.
- The code drops any angle whose moment lies outside the send's window and
  records the break, so a stale one costs the send its argument entirely.

## Return exactly this

```json
{
  "serve": [
    {"segment": "...", "audience": 83871, "live": true, "avatar": "... or mixed",
     "variants": [
       {"avatar": "...", "angle": "the problem this variant argues from"}
     ],
     "variant_cap_reason": "audience N supports X; language depth allows Y",
     "why": "cites [F#] or a coldness line"}
  ],
  "cold": [
    {"cell": "segment or avatar", "why": "the reason it rests this month"}
  ],
  "learning": "which avatar dominates which segment — the thing the brand cannot currently measure"
}
```

Then **THE CALL, READ ALOUD** — four lines or fewer: which segments are live
and which rest, what the split tests will teach, and what the record says
about serving the live ones.
