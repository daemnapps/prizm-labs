# The cells decision — how many emails go to which segment

**The big domino** (the owner, 2026-08-31). Every later stage is downstream of
this one: the moves are chosen for these segments, the order sequences these
sends, production builds these emails. Get this wrong and everything after
it is a well-executed mistake. It runs on data end to end — no human signs
it off (the owner, 2026-08-31: "I don't need to be involved at all, this is
simply based on data").

Brand-agnostic by construction — everything below resolves through
`brands/<brand>/`. A brand with no segments gets them created; a brand with
no history gets an honest first month.

---

## 1 · The targeting model (RULED 2026-08-31)

Three levels exist in the brand's records. They are **not**
interchangeable, and confusing them is the failure this ruling prevents.

| Level | Real? | Targetable? | Role |
|---|---|---|---|
| **Segment** | yes — live rules in the platform, with exact counts | **YES** | the unit of targeting and of frequency |
| **Avatar** | yes — profiles + thousands of language rows | no | rides as a **variant** inside a send |
| **Sub-avatar** | profiles exist; population unknown | **no** | **not used at this level at all** |

**Why segments target.** The platform knows exactly who is in one and how
many. Nothing else about the audience is knowable at send time.

**Why avatars are variants, not targets.** A segment holds every avatar
mixed together and no profile says which is which. So a send carries one
variant per avatar worth reaching — same occasion, same offer, the argument
written through that avatar's own world. Everyone gets one; the split test
reports which won. **One variant addresses one avatar** — the never-blend
rule holds inside a variant exactly as it holds for a whole email.

**Why sub-avatars are excluded.** In the founding brand only 187 of 14,237
language rows carried a sub tag (1.4%), and no profile carries one at all.
Any claim that a segment "is" a sub-avatar was invented. They may return
when evidence supports them; until then they do not appear in planning.

**This makes the month an instrument.** Which variant wins IS the
measurement of which avatar dominates that segment — the thing no brand can
answer on day one. Plan so the month produces that evidence.

---

## 2 · What the stage reads (the state sheet, built by code)

| Input | Source in the brand | If absent |
|---|---|---|
| Segments + exact counts | `email/audience-matrix.json` | **stage refuses to run** — see §5 |
| Avatars + language depth | `core-avatars/language-index.json` | no variants possible; single-voice sends |
| Findings (what earns) | parsed from `email/learnings.md` | "(no measured sends yet)" — see §6 |
| Coldness (types, cells) | `email/classified.json` + adopted calendars | everything reads as cold; see §6 |
| Moments | `calendar/moments.json` | occasions come from problems, not seasons |
| Offers per avatar | `products/offer-bank.md` | avatars without a section carry no offers |

---

## 3 · The rules, at full nuance

### 3.1 Variant count is capped twice, and both are stated

**Cap A — audience.** Each variant needs enough people for the result to
mean anything:

| Segment size | Variants supported |
|---|---|
| over 50,000 | 4 |
| 10,000–50,000 | 3 |
| 3,000–10,000 | 2 |
| under 3,000 | 1 — no test |

Platform guidance caps a campaign test at 4 variants regardless of size.

**Cap B — language depth.** A variant only exists for an avatar with the
language to write it. An avatar of a few hundred rows cannot hold a variant
against one with thousands: it gets its own small send, or it rests.

**The binding cap wins, and the reason is recorded** in
`variant_cap_reason` — e.g. *"audience 83,871 supports 4; language depth
allows 2."* A test that cannot resolve is worse than no test: it spends
audience and returns noise.

### 3.2 There is NO send budget — volume is an output

**No cap, no floor, no invented count** (RULED, the owner, 2026-09-01: "email is
programmatic, there are no limits"). This stage decides only whether a
segment is **live or resting** this month. It does not decide how many
emails anyone gets, because a number invented here becomes a cap later, and
a cap drops real opportunities — that failure is on the record: a proven
holiday was dropped to satisfy an AI's own guess of "3 sends."

**The month's volume is built from what is actually happening**, in order:
every in-window moment served for every live segment it fits (a proven
holiday is not optional — run up every holiday opportunity), then the
coldest ground, then whatever the findings say is worth doing. Promotional
moments cost three sends each because an arc is three; that is arithmetic,
not a budget.

What sending EARNS — revenue per recipient against unsubscribe cost, from
the brand's own ledger and performance record — informs **which segments are
live and which rest**, not a quota. The per-person number is reported by the
checker as an OUTPUT so it is always visible, never as a constraint the plan
must fit.

**A segment with no measured history of its own** (newly created segments
have none) reasons from the closest evidence the sheet carries and says so;
that month is what creates the segment's record.

**Overlap is real and must be resolved.** A VIP is also a customer; a
churned buyer is also a one-time buyer. Two sends to two overlapping
segments can land on the same person. Where segments overlap, the plan says
which one owns that person for the month so the per-person number is true.

Cadence is derived, never set: no target number of sends, no fixed share
that may ask. The arc governs order; the brand's own measured data governs
frequency.

**One exception, and it is named as one.** The weekly affiliate slot (RULED
2026-09-01) is the single cadence this system sets itself rather than reading
off the record — a standing investor commitment, not a data signal. It runs
in code (layer 8, the affiliate floor), not as an AI stage's guess: one `affiliate-feature` a week,
every week, drawn from the brand's own `email/affiliates.json`. A brand with
no partners recorded gets nothing scheduled — the floor never invents a
partner to satisfy itself, it only activates once real ones exist.

### 3.3 Resting is a decision, not an omission

Every rested segment or avatar carries its reason. The standing ones:

- **Unengaged**: mailing a large non-opening population costs the
  deliverability every other send depends on. Resting it is usually right,
  and always explicit.
- **A thin avatar**: below roughly a thousand language rows, a variant
  written "as" that avatar is really the house voice wearing its name.
- **A thin avatar in a small segment**: depth that survives a 100k split
  will not survive a 7k one.

### 3.4 Every why cites

A finding id (`[F3]`), a moment key, or a coldness line. The checker flags
an uncited why as a hunch. Hunches are allowed to exist — they are not
allowed to hide.

### 3.5 The stage decides nothing downstream

No types, no occasions, no copy, no dates. Naming an email here would settle
by accident what the next stage should settle on evidence.

---

## 4 · No sign-off — but every decision is inspectable

The flow runs start to finish on the record. Nobody approves the cells.
What replaces a checkpoint:

- **The evidence is in the run**: the state sheet it read, the exact prompt,
  its full reasoning, and the decision as data — all saved per run.
- **The checker recomputes** the per-person numbers from the finished slots
  rather than trusting the stage's own claim.
- **A rule that is wrong gets changed in the prompt**, versioned, and the
  next run obeys — the fix belongs in the rules, not in a monthly veto.

Two escape hatches exist and are not the default: `--stop-at-cells` pauses
after this stage, and `--continue` resumes from a hand-edited
`3-cells/cells.json`.

### What a promotional moment always gets

A promotional moment costs **three** of a segment's sends, never one
(RULED 2026-08-31): warm-up, the ask, cool-down. The catalogue is indexed
with each type's legitimate warm-ups and cool-downs, so code assembles the
arc — it is a lookup, not a judgment. **There is no budget to hold it
against** (RULED 2026-09-01, after a proven Labor Day arc was dropped to
satisfy an invented "3 sends" ceiling): every promotional ask is completed
into its full arc, always. A lone ask is not a smaller promotion, it is a
worse one, and nothing here manufactures one.

One more rule runs in code at the same point: **a type is used once per
segment per month** (a repeat is the planner out of ideas). The only thing
CAL-4 ever drops is an exact duplicate — the same type, on the same
occasion, to the same segment, twice — and that is written down in
`9-order/dropped.md` rather than vanishing.

---

## 5 · A brand with no segments

The stage refuses to invent a segment vocabulary. The path:

1. **`pull/make_segments.py --brand <brand> --dry-run`** prints the eight
   core commercial segments it would create — Lead, One-Time, Returning,
   Loyal, VIP, Subscriber, Churned, Unengaged — as live rules that
   re-evaluate, never static lists.
2. **Metric ids resolve per account by name** (Placed Order, Started
   Subscription, Opened/Clicked Email). A brand missing a metric — no
   subscription product, say — **skips that segment rather than guessing**.
   A brand with two candidate metrics pins the real one in
   `pull/accounts.json`.
3. Drop `--dry-run` to create them, then **`pull/matrix.py --brand <brand>`**
   proposes `email/audience-matrix.json` under
   `runs/email-production/<brand>/facts-<YYYY-MM-DD>/`; once a person folds it
   into the brand, it is the vocabulary the stage reads.
4. The thresholds (1 / 2 / 3–4 / 5+ orders, 180-day churn, 120-day
   unengaged) are the founding brand's shape. **They are a starting point,
   not a law**: a brand whose repeat cycle is 18 months has a different
   churn window. Change the definition, re-create, re-pull the matrix.

The stage will run against any segment vocabulary — it reads names and
counts, and holds no opinion about what a brand's segments should be.

---

## 6 · A brand with no history

Nothing here degrades to invention.

| Missing | Behaviour |
|---|---|
| No sends ever | findings are empty; the stage says so and leans on audience size and language depth alone |
| No classified record | every type reads as never-sent — correct, not a bug |
| No adopted calendar | every cell reads as cold — also correct |
| One avatar only | no variants anywhere; single-voice sends, and the month teaches nothing about avatar dominance (say so) |
| No moments file | occasions come from recorded problems and seasons, not events |

A first month for a new brand is therefore **smaller and more cautious**,
and it should say why on its face.

---

## 7 · How this stage fails, and what catches it

| Failure | Caught by |
|---|---|
| A segment that does not exist | checker: not in the brand's vocabulary |
| An avatar not on the roster | checker: roster validation |
| A sub-avatar named anywhere | this prompt forbids it; review catches a stray |
| A test that cannot resolve | Cap A, stated in `variant_cap_reason` |
| A voice the brand cannot carry | Cap B, same field |
| Frequency out of step with what a segment earns | per-person report set against the brand's own revenue-per-recipient and unsubscribe record |
| A hunch dressed as evidence | citation check flags the why |
| A rest that was really an oversight | every rest carries a reason, or it is not a rest |

---

## 8 · The record it leaves

One numbered folder per stage, under `results/calendar-<month>/`:
`1-state-sheet/state.md` (the facts it read) · `2-cells/prompt-sent.md` (the
exact prompt) · `2-cells/reasoning.md` (its full reasoning) ·
`3-cells/cells.json` (the decision, editable by a human) · `run.json`, at
the month's root (timing, model, prompt version and hash).

The prompt version that ran is recorded, so a month can always be traced to
the rules that produced it.
