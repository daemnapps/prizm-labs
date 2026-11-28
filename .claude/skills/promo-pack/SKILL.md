---
name: promo-pack
description: Build or hand off a promotion pack for any brand and moment, the same way every time — one offer change in, one pack out, with the offer words for the owner to approve, the stock that blocks it, and one hand-off per workflow (video, static, email, SMS, store promo, funnel offer) with its role, brief count and dates from the calendar. Use for "make a promo pack", "promotion pack for <moment>", "run the <brand> <moment> promo pack", "new offer", "change the free gift", "Black Friday / Christmas / New Year / Valentine's / Mother's Day pack", "hand the promo pack off", or any offer change that has to reach store, funnels, emails, ads and the warehouse.
---

# Promo pack

> **Activates component:** `components/promo-pack` (`machine/pack.py`: build, approve, hand, status). Read its
> `CLAUDE.md` first.

The owner gives the first 10%: the offer and the moment. This skill does the 80% and stops at the owner's call.

1. **The offer is in the bank first** (Offer change workflow): the offer's lines word for word in
   `brands/<brand>/products/offer-bank.md`, and a row in its `promo-calendar` table with the dates. No row, no pack.
2. **The month is on the calendar** (`marketing-calendar`). The pack takes its dates from it.
3. **Stock:** run the component's `skills/stock-check.md` and keep the read as a file.
4. **Build:** `python3 components/promo-pack/machine/pack.py build --brand <brand> --month <YYYY-MM> --stock <file>`.
5. **Show the owner one page:** the offer words with one approve click, the stock blockers, the hand-offs as tiles.
   No timelines in prose, no narrative.
6. **His approval only:** `pack.py approve --brand <brand> --moment <moment> --by <who> --said "<his words>"`, when
   he has approved on the page or in chat. Never on anyone else's word.
7. **Hand off:** `pack.py hand --brand <brand> --moment <moment>`. It runs the doors that spend nothing, writes the
   ones that spend for the role's holder, and lists the gaps.
8. Each workflow then runs through its own skill and stops at its own gates. Report each hand-off as:
   done · waiting on whom · next step.

## Rules

- Roles only, never people: video-editor, graphic-designer, retention-strategist, page-builder, brand-operator.
- One call per hand-off: an approval of the offer words is not a go on the store, a send or a spend.
- Every word comes from the offer bank and the language bank. A missing line is asked for through the bank.
- New winner-swipe ads stay the owner's; the pack carries winner variations, redone statics, the month's sends,
  the store and funnel switch, and the stock.
