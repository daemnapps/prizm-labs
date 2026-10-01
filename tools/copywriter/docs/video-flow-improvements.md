# What the copy build learned that the video build should take

Written 2026-08-26, after building `ad-copy` against the same
problem the video chain already solved. Damon's ask: identify the creative
and copy improvements the video flow can take from it, especially at
**injection, hooks and expansion**.

Everything below was checked against the live prompts in
`components/video-teardown/prompts/` and its `chain_config.json` — not
assumed. Where the video chain already does something better, that is said.

---

## What the video chain already does better, and copy took from it

Stated first so the rest reads as exchange rather than critique.

- **The hook ledger is enforced, not mentioned.** 4b binds `{hook_ledger}`
  and treats a spent verbatim as ground it may not build on again, with a
  status table per hook. The copy build only *tells* a stage to respect a
  ledger — the video chain gives it a structured record. Copy should adopt
  this shape.
- **Six hooks, all ship, machine never picks.** Copy took this verbatim.
- **Gated moves in expansion.** Copy took this too, including the
  ad-vs-organic route that decides whether expansion runs at all.
- **A dedicated audit stage** (4f) that reports and gates nothing.

---

## 1 · The language layer moved and the video chain did not follow

**The biggest one, and it is a wiring change before it is a prompt change.**

`chain_config.json` binds, at stages 3, 4b, 4c, 4e and 5:

```
language_bank : brands/<brand>/customer/language-bank.md     (39 KB of prose)
avatar        : brands/<brand>/customer/avatar.md
```

Damon rebuilt the language layer on 2026-08-25/26. It now holds **14,593
sourced rows** at `brands/<brand>/core-avatars/<avatar>/
language/*.json`, every row carrying `use`, `topics`, `speaker`, `funnel`,
`source{name,type,date}`, `signal{likes,tier}` and an `attribution` flag.

The video chain cannot see any of it. Every stage that writes is reading a
prose file the new layer supersedes.

**What to do:** point the config at the new tree and query it. `language.py`
in the copy build already does this and is brand-agnostic — it takes
`(brand, stage, avatar, funnel, topics)` and returns ranked rows.

---

## 2 · Each stage should get different rows, not the same file

Right now stages 3, 4b, 4c, 4e and 5 all receive the **same**
`{language_bank}`. They are doing different jobs and need different evidence.

The rows are tagged for exactly this. Suggested mapping — the same one the
copy build runs:

| Video stage | Should pull (`use`) |
|---|---|
| 3 · injection | `problem-language` · `self-descriptor` · `identity` · `tried-and-failed` |
| 4b · hooks | `hook` · `hook-headline` · `caption-hook` · `competitor-annoyance` |
| 4c · expansion | `why-bought` · `buying-criteria` · `competitor-annoyance` |
| 4d/4e · close | `objection` · `refund-reason` · `expectation-gap` · `churn-risk` |
| 5 · brief | `why-bought` · `post-use-feeling` · `result-language` |

**Ranking matters as much as filtering.** With hundreds of candidates, which
forty a stage sees decides the copy. Rank by: the stage's primary tags first,
then topic overlap with the source, then how loud the row was
(`signal.likes`), then measured over `attribution: assumed`. Otherwise file
order decides, which is the same as arbitrary.

---

## 3 · Provenance has to travel into the prompt

This is the one that matters most for what Damon actually wants — *"it needs
to be 100% real words."*

The brand files deliberately record the difference between:

- a **customer verbatim** — a real person's recorded words
- an **angle / source card** — a line a marketer drafted
- a **paid panel** quote — in-demographic, but contracted to help market the
  brand (recorded in the caveats)
- rows flagged `attribution: assumed`

A stage that receives a flat file cannot tell these apart, and will present a
copywriter's invention as something a customer said. That is worse than
obviously invented copy, **because nobody checks it**.

The copy build renders every row as the sentence plus who said it, from
where, how loud, and flags assumed attribution — then tells the stage that a
paid panellist is not a customer speaking, and to weigh them differently.

Found in practice: the copy build lifted *"that's from the lake house"* as
though it were customer speech. It is a source-card angle line sitting one
line away from a real verbatim in the same file.

---

## 4 · No stage knows what day it is

`{today}` appears in **zero** video prompts.

The copy build hit this hard: it wrote *"a cardigan in July"* into ads
rendered in late August, because the avatar file records that behaviour with
its month attached. The bank recorded when **she spoke**, not when the ad
runs.

The video chain reads the same avatar file at stage 3 and has no date to
check it against. The bug is live there now.

**The rule that worked**, after one that did not: an absolute ban was wrong —
Damon's correction was *"use the context of months but it needs to be the
real month."* So:

> A month in the copy must be the real one. Today's date is data, exactly
> like the avatar and the banks. Do not inherit the bank's month —
> substitute ours. A genuine historical reference (a decade, an age) is a
> fixed point and stays.

And it only binds when it is **a printed check**, not guidance in a bullet
list — see §6.

---

## 5 · Two decisions nobody is making: which avatar, which funnel

**Avatar.** The config names one avatar file. <brand> has **three** core
avatars — Fed-Up King (13,254 rows), Glow-Up Kid (753), Gift Buyer (230) —
and they are different people. Pointing the video chain at <brand> today means
whichever avatar the config happens to name.

Copy moved this into triage: the roster with real row counts goes into the
prompt, a single-avatar brand is chosen in code, and an avatar that does not
exist is rejected loudly.

Worth having: on the first run this produced **`AVATAR: none fit`** — it
refused to write a body-confidence source against a spot-hider bank rather
than force the wrong person's mouth onto the copy. Whether that should halt a
run is an open question, but the refusal is the behaviour you want.

**Funnel.** The bank splits language by `prospect / lead / customer /
churned` on purpose. Nothing in the video chain targets one. Writing to
someone who has never heard of us is not writing to someone who refunded.
Copy asks triage for the funnel plus one line: *what this reader already
knows, and what would insult them to be told.*

---

## 6 · Checks only bind when they are printed

The video chain has an audit at 4f that reports and gates nothing — good, and
worth keeping. But a stage-level check catches things a downstream audit
cannot, and only if the stage must **write its result down**.

The copy build ends its writing stage with four checks it must print:

```
1 TIME    every month/season, against today's date, or fixed
2 FORM    word count vs the format's range; reads as prose, not a shot list
3 MEDIUM  no unit from the source's own medium survived
4 SOURCE  every specific traced to its file — and tagged
          VERBATIM / AVATAR / ANGLE / FILE
```

Two things learned the hard way:

- **A principle in a bullet list does not bind.** The month rule was written
  as guidance and "in July" came straight back — in the body *and* a
  headline. Written as *"name every month in the copy; confirm each against
  today's date"*, it held.
- **Fix in place, then report.** A model cannot retroactively edit what it
  already wrote. The first version described corrections underneath the
  uncorrected copy — so the wrong words sat where people paste from. The rule
  became: count and fix each body **as it is written**, and the receipt is a
  tally, not a place to publish rewrites.

For video the four would differ — FORM becomes runtime against the format's
budget, MEDIUM is not needed since video→video keeps its medium — but TIME
and SOURCE transfer unchanged.

---

## 7 · The interpretation rule

Copy's stage 3 carries this, and video's stage 3 is the same job:

> **The bank is evidence, not a script. Interpret it; do not transplant it.**
>
> Everything in these files was true of a particular person, in a particular
> body, at a particular moment. None of it was written for the thing you are
> writing.

Every piece gets re-judged before use — does it fit what this is about, when
it runs, who is speaking, what format it is in, and is it what it appears to
be. **Keep the truth, drop the frame.**

---

## Ordered by value per unit of work

| | Change | Where | Effort |
|---|---|---|---|
| 1 | Point the config at the new language tree | `chain_config.json` | small |
| 2 | Query rows per stage rather than passing a file | config + `language.py` | medium |
| 3 | Render provenance into every row | `language.py` (done) | none — reuse |
| 4 | Add `{today}` and the real-month rule | 3, 4b, 4c, 4e, 5 | small |
| 5 | Avatar + funnel decided at triage | stage 0 + runner | medium |
| 6 | Printed per-stage checks | 3, 4c, 4e | small |
| 7 | The interpretation rule | stage 3 | small |

1, 3, 4 and 7 are cheap and independent. 2 and 5 are the ones that change
what the chain can do.

`ad-copy/language.py` is brand-agnostic and reusable as-is — it was
written against the schema, not against <brand>.
