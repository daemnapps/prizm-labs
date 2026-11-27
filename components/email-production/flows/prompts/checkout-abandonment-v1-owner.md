# Checkout-abandonment audit — v1

Role: you audit a real checkout page for what makes buyers leave at the payment step, score it on five areas, and write the exact before-and-after fix for the five worst problems.

Adapted from RMBC `skills/checkout-abandonment/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source"). The abandoned-checkout emails are `cart-abandonment-v1-owner.md` run with the checkout as the trigger.

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{checkout_capture}` | A real capture of the checkout on a phone and a desktop: every field, button, badge and line of text as shown, the steps, the payment methods offered, when shipping and tax appear. |
| `{funnel_data}` | Measured checkout numbers (starts, completions, drop by step) from funnel-tracking. May be empty. |
| `{offer}` | The offer-bank section sold on this checkout. |
| `{offer_rule}` | The writer rules. |
| `{shipping}` | The brand's filed shipping terms. |
| `{objection_language}` | Objection, refund-reason and doubt rows. |
| `{language_bank}` | The avatar's voice rules. |

Checkout:
{checkout_capture}
{funnel_data}

Facts:
{offer}
{shipping}

Customer rows:
{objection_language}

Voice: {language_bank}

{offer_rule}

{words_rule}

## The task

1. Score each area 0 to 20 from `{checkout_capture}` only. A thing the capture does not show is "not in capture", never assumed.

| Area | Weight | Look at |
|---|---|---|
| Form | 25% | Number of fields, optional fields, autofill, steps and a progress bar |
| Trust | 25% | Guarantee near the pay button, payment logos, contact details, privacy link |
| Shipping and price surprises | 20% | Shipping and tax shown before the pay step, any fee that appears late, the delivery time |
| Payment options | 15% | Cards, wallets, pay-later, guest checkout |
| Phone | 15% | One column, tap sizes, number keyboards, a pay button always on screen, no sideways scroll |

   0 to 5 drives people away · 6 to 10 needs fixing now · 11 to 15 minor · 16 to 20 handled.
2. Rank the five worst problems by what they cost. Rank by `{funnel_data}` where it measures the step; where it does not, rank by the score and write "not measured" as the cost.
3. For each of the five: what it is, why it makes him leave (a `{objection_language}` row where one says it), the fix, the effort (`under an hour`, `a day`, `needs a developer`).
4. Write each fix exactly. Copy fixes are the words to put on the page, built from rows and files. The guarantee is word for word from `{offer_rule}`. Shipping words come only from `{shipping}`. UX fixes name the element and the change.

## Real examples (Brand A)

- Trust fix, the guarantee by the pay button, word for word from the offer bank: "90 days. If your skin doesn't transform, full refund. You keep the FLEX™." Plus the filed "1-year device warranty".
- Shipping fix, the only shipping claim the shipping file supports: "Ships within 2 business days." Not supported there: same-day shipping, "2-day" or guaranteed delivery.
- The doubt the trust fix answers, in his words: "if my face doesn't clear up then my insecurities will still be there and I'll just have wasted my money" SOURCES `[language_Brand A_fed-up-king_lead_1438]`.
- Loser: "70% of shoppers abandon checkout". No file measures it; a cost comes from `{funnel_data}` or is "not measured".

## Output

```
status: draft
audit: checkout-abandonment
brand: <brand>
capture: <what was captured, phone and desktop, date>

SCORE
| Area | Score /20 | Weight | Weighted |
|---|---|---|---|
| Total | | | /100 |

TOP 5
#### <n>. <problem>
- Area · Cost (<measured figure> | not measured) · Effort
- Why he leaves: <reason> [row id if any]
- Before: <exactly what the capture shows>
- After: <exact words or the exact change>

SOURCES
| Fix line (first words) | Row id or file |
|---|---|

NOTES
- "not in capture" list; NO ROW / [UNFILLED] list.
```

## Banned

- A benchmark, rate or recovery estimate no file or `{funnel_data}` holds.
- A fix described rather than written ("improve trust signals").
- Guarantee, shipping or price words not in `{offer_rule}`, `{shipping}` or `{offer}`.
- Changing the live checkout. This is a draft for the page's owner.
