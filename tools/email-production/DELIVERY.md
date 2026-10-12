# Final delivery — what leaves the machine, and how it reaches the designer

**RULED 2026-09-09 (the owner), and this supersedes every earlier version of this
page: the machine does not design emails.** It maps out the month and writes
the copy. What the designer gets, per email, is a brief in Figma: the copy,
the real reference email it was written off, that reference torn down into
its framework, and our copy injected into that framework. She designs it.

> "The actual designing of what you're doing looks like dog shit, and it's not
> worth the time because the editor can just go do it herself… It's more about
> just mapping out that month. We can still put the copy in Figma and pull in
> a reference email we've already created, so the designer has something to
> work with. Then look at the construct of that email, do a teardown on that,
> and see how we can inject copy based on the framework of those emails."

```
CALENDAR  →  COPY  →  BRIEF IN FIGMA (copy + reference email + teardown + injection)  →  EVE designs  →  EVE → KLAVIYO
```

## What lands in Figma, per email

`python3 figma_brief.py results/<slot>` writes the code; the session runs it
through the Figma connector. On the page **"Briefs - YYYY-MM (machine)"**, per
slot, side by side:

| | What it is |
|---|---|
| **The brief card** | Slot, date, segments, type, voice · subject and preview · the teardown and the injection · open facts · pictures |
| **The reference email** | An untouched copy of the real email this one was written off, named `SEP-04 \| REF <name> (do not edit)` |

**The teardown** is that reference read as a framework, off the frame itself:
every slot in reading order — display / subhead / body / button / picture —
with its size and how long the reference's own line ran there. It is true of
that email and no other.

**The injection** puts this month's copy into that framework slot by slot. A
framework slot our copy does not fill says so. Copy the framework has no slot
for is listed at the end as the extra this email needs room for.

**The teardown is of the source email itself**, parsed from the file the
chain swiped (`brands/<brand>/email-sms/sends/<file>.md`), not of a Figma frame
that merely resembles it. RULED after the owner caught the first version doing
exactly that on 2026-09-09: the Brand B file's campaign designs stop at
January 2026 while the swipe sources are mostly 2026 spring sends, so no
design of the source exists to point at. The brief names the source by
subject, date, campaign and file path, and no frame is cloned.

Every brief also ships as Markdown in the run folder
(`results/<slot>/brief-for-design.md`) for the team.

## What the machine no longer does

- No cloning templates and typing into their layers (retired 2026-09-09).
- No HTML render as a deliverable (retired earlier the same day; the rebuild
  sweep stays only as a design record).
- No Figma → Klaviyo automation: Eve puts the finals into Klaviyo herself.
- The machine never schedules or sends (RULED 2026-09-01).

## One brand at a time (RULED 2026-09-09, the owner: "let's focus on one brand at a time")

**Brand B only.** The Brand A briefs were deleted from its Figma file on the
same ruling; Brand A's own design pages were not touched. Brand A's calendars,
send library and copy stay on disk, unused, until he comes back to it.

## A send is not a version (the owner, 2026-09-09: "our calendar tool shows only 2 but you have 4")

The calendar plans **sends**. Where a send goes to an audience that carries
more than one avatar, the chain writes **a version per avatar** — same slot,
same date, same segments, different voice. The board shows that shape: one
heading per send, its versions side by side under it. A slot's tag is its
**send date**, never its ordinal — SEP-01 read as the 1st when it is the first
send of a run that starts on the 14th.

## The world, not just the argument (RULED 2026-09-10)

> "This literally has nothing to do with football." … "If you were taking a
> basketball email and turning it into a football email, you needed to actually
> think."

A source is **an argument running through a world** — the trade, the Finals,
the holiday, the season. The machine was replacing the argument and keeping
nothing of the world, because the world never reached it: a slot's moment was
handed over as a filing label to the first pass and the brief header, and not
one of the six passes that write a word ever saw it. So a send scheduled on NFL
season came out with no football in it, and one scheduled on school photos had
no school.

Three things now hold that shut:

1. **The moment and the send day are inputs the writing passes obey**, in the
   brand's own words from its moments file — what the moment is, when its
   window runs, why it lands for this audience — not the key.
2. **The injection pass opens with a written world swap**: the source's world,
   ours, what carries across, what does not. The copy has to match it. An
   email that would read the same with the moment deleted has failed.
3. **`check_month.py` refuses to let it ship quietly.** It reads a month's
   finished copy and flags a moment the copy never names, a weekday that is not
   the send day, art direction that leaked in as a sentence, walls, repeats and
   typos. Zero cost, no model calls.

## The calendar decides; the copy obeys (RULED 2026-09-10)

> "I still see some Labor Day email in the Figma for late September… **why are
> you not using the calendar in this chain to actually inform which emails to
> write?**"

He was right, and the fault was one thing in three places: the calendar made a
decision and nothing downstream was bound by it.

| The decision | What was happening | What holds now |
|---|---|---|
| **The moment** | reached triage and the brief header only; no writing stage saw it | a binding input in the brand's own words, plus a written world swap before any copy |
| **The offer** | `offer: none` meant the WHOLE offer bank was handed over and the writer chose — 13 of 29 September versions invented a price, a discount or a free gift | `none` is an instruction: no price, no percentage, no bundle, no gift, no deadline, no countdown. An assigned offer means that one and no other, and the holiday attached to the source's offer does not travel |
| **The angle** | the cells stage wrote one `labor-day` angle and gave it to every avatar-one variant for the month — Labor Day was the 7th, the sends run the 14th to the 30th | an angle naming a moment outside the send's window is refused. Where it names a live moment too, the angle keeps that and loses the dead one; where it names none, the slot's own recorded problem replaces it, and the break is written to `9-order/stale-angles.md` |

The third is where the Labor Day email actually came from. It was not the
copywriter reaching for it — **the plan told it to, seven times.**

Each is enforced twice: the chain cannot run without the input, and
`check_month.py` refuses to let a stale holiday, an unauthorised price or an
unnamed moment reach the board.

## One send a day (RULED 2026-09-10, the owner: "let's only do 1 send, not 2 on a day for now")

Two different sends never share a date. A send may still go out in several
versions, one per avatar — that is still one send. The ordering enforces it,
and when a month fills up the overflow spills past the month end and is named
for a human to keep or cut rather than quietly doubling up.

September runs the **14th to the 30th — seventeen days**, so it holds
**seventeen sends** and no more. The plan wanted nineteen. What changed:

| | |
|---|---|
| moved | `moment` (NFL season) to Core \| Lead: the 16th → **the 26th** |
| moved | `guarantee` to Core \| One-Time Customer: the 24th → **the 30th** |
| cut | `anticipation` to Core \| VIP Customer — the Prime Day tease |
| cut | `guarantee` to Core \| VIP Customer — the subscription arc's cool-down |

Both cuts are the warm-up and cool-down of the subscription-invite arc; its
ask still goes out on the 28th. Their copy is finished and parked, untouched,
in `results/_cut-2026-09/` — naming a day puts either one back. The checker
reports the missing warm-up and cool-down as breaks, which is correct: that is
the price of one send a day, and it is the owner's call to pay it.

Two days carry no brief: the **17th** and the **23rd** are affiliate sends,
which the chain has never written copy for.

Fifteen sends, twenty-nine versions, on the board.

## Where Brand B stands (2026-09-10)

| | |
|---|---|
| Calendar | September from the 14th, 17 slots — one send a day · October and November standing |
| Copy | September complete — 29 versions live, 2 parked in `results/_cut-2026-09/` |
| Figma briefs | **all 29 in**, on the page "Brand B - reference emails + briefs" in the Brand A account's Figma file, in a section called "Brand B September 2026 - the 14th to the 30th" |
| Reference emails | the five most recent Brand B campaign sections (Sep 2025 - Jan 2026, 113 emails) copied onto that page |
| Klaviyo | Eve, from Figma |

The Brand B file itself (`Brand B -> the owner (Copy)`) sits in the owner's own Figma
team, on the Starter plan, whose connector budget is spent — the session
cannot read or write it. That is why the Brand B work lives on its own page in
the other account's file, which the same designer already works in.

## Parked: a brand with no Klaviyo history

Kept as the record, not as live work. A brand whose Klaviyo history is not on
file still has every email it ever designed: `pull/sends_from_bank.py --brand
<brand>` turns the design bank into a send library, `pull/classify.py` tags
it (both proposed under `runs/email-production/<brand>/facts-<YYYY-MM-DD>/`
for a person to fold into the brand), and the calendar component's `--reorder` finds a source per slot without spending on
AI. That source is also what the brief uses as its reference email, which is
why the reference and the copy always belong to each other.
