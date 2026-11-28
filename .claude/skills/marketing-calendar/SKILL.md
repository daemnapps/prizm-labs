---
name: marketing-calendar
description: Plan a brand's month of sends — a brand and a month go in; the month's slots (date, audience, argument, offer, with the reason beside each) come out under runs/marketing-calendar/<brand>/<YYYY-MM>/. Plans only; writes no email copy. Use whenever someone says "plan the <month> calendar for <brand>", "make the <brand> email calendar for next month", "what should <brand> send in November", "dry-run the <brand> calendar", "can <brand> run a calendar for December", "re-order the <brand> month", "what holidays and moments land in <month> for <brand>", "show me the <brand> slots", or "check the <brand> calendar".
---

# Marketing calendar

> **Activates component:** `components/marketing-calendar` — `machine/marketing_calendar.py <YYYY-MM> --brand <brand>`, nine layers that place a month of sends at real dates.

External dependencies: `components/marketing-calendar/` (the engine: `machine/marketing_calendar.py`, `machine/chain.py`; `prompts/` the two AI layers; `definitions/send-types.seed.json` the starter type catalogue; `CONTRACT.md` everything a run emits), `components/run-kit/` (picks the model for the two AI layers), `components/elements/` (the email-format library the sends are typed against), `brands/<brand>/` (the brand record, its moments, email types and offer bank, read-only), `runs/marketing-calendar/<brand>/` (where the month lands).

For activation/review transitions and reuse of existing work, follow `components/WORKFLOWS.md` → Activation and review cycle. Showing an existing month reads it without a new planner call.

Where it sits: this is stage one of the email line. The month's slots come out here; `email-production` turns each slot into an email.

**One command, then its free form first.**

```
python3 components/marketing-calendar/machine/marketing_calendar.py <YYYY-MM> --brand <brand> --dry-run
python3 components/marketing-calendar/machine/marketing_calendar.py <YYYY-MM> --brand <brand>
python3 components/marketing-calendar/machine/chain.py --check <brand>
```

- `--dry-run` spends nothing and writes nothing: checks the brand, runs layers 1-2, resolves both prompts and every field they would be handed, and prints READY or what is missing. Always run it first and show the person the result in one line.
- `chain.py --check <brand>` is also free: which of the nine layers can run for this brand (full, degraded, blocked).
- The real run (no `--dry-run`) calls a paid model on layers 3 and 5. Run it only when the person has said to.
- `--reorder` re-runs layer 9 only; `--from-anchors` re-runs layers 4-9. Both are free (no model) and work from a month already on disk.
- `--start-day <N>` drops slots dated before that day of the month. `--model <name>` forces one model onto both AI layers. Leave `--out` alone: the default is the repo's `runs/marketing-calendar/`.
- If usage runs out mid-run, the run stops with one line and keeps what it wrote; run the same command again later.

## What it reads

The brand's own record under `brands/<brand>/` (segments, moments, avatars, offer bank, `email-sms/email-types.json`, affiliate roster) and the public holidays for the month. A brand that has never sent an email has no formats of its own, and its month comes out unfilled unless its `email-sms/format-sources.json` declares where to borrow shapes.

## The rules the component enforces — do not work around any of them

1. **The prompt is the product.** Both AI layers write the prompt as sent beside the output, and `run.json` stamps its sha. Do not hand-edit a month's prompt copy.
2. **Brand-agnostic.** Every fact (segments, moments, offers, avatars) comes from `brands/<brand>/`, read-only.
3. **The planner never writes the person's layer.** `slots.json` is the machine's record; `review.json` is the person's. Re-planning must never quietly re-approve a month, and a reviewer's rewrite is never lost to a re-run.
4. **Nothing here writes copy.** The calendar picks dates, audiences, arguments and offers; it does not write a sentence for a customer.
5. **Offers come only from the brand's offer bank.** An offer no variant can carry is stripped.
6. **Types are never invented.** A send type the brand's catalogue does not know is dropped; a type in neither the element library nor the brand's `email-types.json` is a Break.
7. **A gate is recorded, never raised.** A month that fails a check is still written, `check.json` says `HELD` with the problems, and a person decides. Adoption stays a human act: an unapproved send is never handed off.
8. **One send a day; the only thing ever refused is an exact duplicate.** No send budget exists.
9. **Every write goes under `--out`** (default `runs/marketing-calendar/`).

## Then the promo pack (every real run)

When a month has been planned (a real run, or the person says the month is approved), start the promo pack for it:

```
python3 components/promo-pack/machine/pack.py tick --brand <brand> --month <YYYY-MM>
```

   Add `--stock <file>` when a stock read is on hand (`components/promo-pack/skills/stock-check.md`).
- It builds one pack per promotion touching the month (the offer bank's promo-calendar rows). A month with no promotion builds nothing.
- It starts every hand-off that has a door (plans and drafts only: nothing goes live, sends or spends money) and says `loaded` when all are in. There is no approval step.
- Report in one line: the packs built, and whether each is loading or loaded, plus any stock blockers and flagged sends. The pack is `runs/promo-pack/<brand>/<moment>/PACK.md`.

## What cannot be done from one command by a person

The review step (approve, needs work, cut, per send) is a person's act on `review.json`; the component's own review board is a local page started by a separate command, and this skill does not use it. If the person wants a slot changed, tell them to say which one and what to change; do not edit `review.json` for them without being asked. Also: no single command both plans and writes the emails; writing is `email-production`.

## What comes back, and where it lands

`runs/marketing-calendar/<brand>/<YYYY-MM>/` — `slots.json` (the month's sends), `review.json`, `checks.md` and `check.json` (Breaks and Warnings; Breaks are listed first), `run.json` (prompt versions, gates, element types used), one folder per layer (`1-holidays`, `2-cultural`, `3-cells`, `4-anchors`, `5-concepts`, `6-catalogue`, `7-offers`, `8-affiliate`, `9-order`) and `board.html`. Beside the months, `runs/marketing-calendar/<brand>/EMAILS.md` is the read-only list of every email and where it stands (Idea, Written, Klaviyo draft, Scheduled, Sent). Its writer is not part of this component, so read it, never edit it.

Report: ready or not (dry run), then for a real run the count of slots, the Breaks in one line each, and whether `check.json` says `HELD`. Next step is the person's review, then `email-production`.

Reply with the result and the folder it landed in (repo path or Drive folder name).
