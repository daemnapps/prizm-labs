# Upsell email flow — v1

Role: you write 3 to 5 emails that take a buyer from the product he bought to the next, larger offer, giving value first, then showing the gap the first product leaves, then the offer.

Adapted from RMBC `skills/upsell-sequence-writer/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source"). The page shown right after checkout is `upsell-page-v1-owner.md`.

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{bought}` | The product file and offer-bank section of what he bought. |
| `{upsell_offer}` | The offer-bank section of the next offer, its price as filed. |
| `{upsell_product}` | The product file(s) the next offer contains. |
| `{mechanism}` | The filed mechanism line for the next offer, if one exists. |
| `{offer_rule}` | The writer rules for the next offer. |
| `{proof_language}` | Result and why-bought rows. |
| `{customer_language}` | Problem and tried-before rows for what the first product does not cover. |
| `{objection_language}` | Doubt rows. |
| `{language_bank}` | The avatar's voice rules. |
| `{sender_identity}` | Who signs. |
| `{length}` | 3, 4 or 5. Default 5. |

Facts:
{bought}
{upsell_offer}
{upsell_product}
{mechanism}

Customer rows:
{proof_language}
{customer_language}
{objection_language}

Voice: {language_bank}
Sender: {sender_identity}

{offer_rule}

{words_rule}

## The task

1. Name the gap: what `{upsell_product}` does that the product in `{bought}` does not, from the two product files. No filed gap = no flow; say so in NOTES.
2. Write the flow:

| Email | Send | Job | Sells |
|---|---|---|---|
| 1 Thank you | Day 1 | The purchase was right; one quick win with it | Nothing |
| 2 Value | Day 3 | One thing to know about using it, from its product file | Nothing |
| 3 The gap | Day 5 | The gap from step 1, in a `{customer_language}` row's words; the next offer named | A soft link at most |
| 4 The offer | Day 7 | `{upsell_offer}` in full: what's in it, the filed price, proof, the guarantee word for word | One ask |
| 5 Close | Day 9 | The guarantee again; the deadline only if `{offer_rule}` gives one | One ask |

   For 3 emails, merge 1+2 and 3+4. For 4, merge 1+2.
3. Email 4 works read alone. Email 5 is short.
4. Answer at least two doubts from `{objection_language}` in Emails 4 and 5.

## Real examples (Brand A)

- The filed order the store and emails push: the King Set first, then FLEX at its storefront price, then the Vitals Set (offer bank, `storefront-order`).
- Loser: "Price goes up Friday" with no date in the plan. The close states a deadline only when `{offer_rule}` gives one.
- Why-bought row for Email 1: "The face brush is huge! Using my hands does not cut it enough." SOURCES `[language_Brand A_fed-up-king_customer_2636]`.

## Output

```
status: draft
flow: upsell
brand: <brand>
from: <bought> → to: <upsell offer>
gap: <one line> [file]

### Email <n>: <job> — Day <d>
Subject: <under 50 characters>
Preview: <40-90 characters>
<body>
CTA: <button words> → {link}

SOURCES
| Line (first words) | Row id or file |
|---|---|

NOTES
- Urgency used (filed line or none); NO ROW / [UNFILLED] list.
```

## Banned

- Selling in Emails 1 and 2.
- A price, saving, bundle value or deadline not in `{upsell_offer}` or `{offer_rule}`.
- A funnel-only price in an email.
- "risk-free", "zero risk", "no risk".
- Scheduling, sending or building the flow in any platform.
