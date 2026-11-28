---
name: promo-pack
description: Build and start a promotion pack for any brand and moment, the same way every time — one offer change in, one pack out, with the offer words from the bank, the stock that blocks it, and one hand-off per workflow (video, static, email, SMS, store promo, funnel offer) with its role, brief count and dates from the calendar, each started where it has a door. Runs after a month's calendar is planned. Use for "make a promo pack", "promotion pack for <moment>", "run the <brand> <moment> promo pack", "new offer", "change the free gift", "Black Friday / Christmas / New Year / Valentine's / Mother's Day pack", "where is the promo pack", or any offer change that has to reach store, funnels, emails, ads and the warehouse.
---

# Promo pack

> **Activates component:** `components/promo-pack` (`machine/pack.py`: tick, build, hand, status). Read its
> `CLAUDE.md` first.

Whoever triggers it, it runs. No approval step.

1. **The offer is in the bank first** (Offer change workflow): the offer's lines word for word in
   `brands/<brand>/products/offer-bank.md`, and a row in its `promo-calendar` table with the dates. No row, no pack.
2. **The month is on the calendar** (`marketing-calendar`); its skill runs step 4 after every planned month.
3. **Stock:** run the component's `skills/stock-check.md` and keep the read as a file.
4. **Run:** `python3 components/promo-pack/machine/pack.py tick --brand <brand> --month <YYYY-MM> --stock <file>`.
   It builds the pack, starts every hand-off that has a door (plans and drafts only), and says `loading` or `loaded`.
5. **Report in one line:** the pack, its state, the stock blockers and the flagged sends. Gaps stay listed in the pack.
6. Each workflow then runs through its own skill. Going live, sending and scheduling stay inside those workflows.

## Rules

- Roles only, never people: video-editor, graphic-designer, retention-strategist, page-builder, brand-operator.
- Every word comes from the offer bank and the language bank. A missing line is fixed in the bank, then run again.
- New winner-swipe ads are not in the pack; it carries winner variations, redone statics, the month's sends,
  the store and funnel switch, and the stock.
