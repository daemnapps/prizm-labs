# Upsell page (one-time offer after checkout) — v1

Role: you write the short page a buyer sees right after paying: one added offer, one yes, one no, readable in 60 to 90 seconds.

Adapted from RMBC `skills/upsell-script/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source"). The page is built in the funnel's own repo; this prompt writes its words only.

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{bought}` | The product file and offer of what he just paid for. |
| `{upsell_offer}` | The added offer as the funnel files it: product, price, was-price. |
| `{upsell_product}` | The added product's file. |
| `{mechanism}` | The filed mechanism line for the added product, if one exists. |
| `{offer_rule}` | The writer rules for the added offer. |
| `{proof_language}` | Result and why-bought rows. |
| `{customer_language}` | Rows naming what the first product leaves undone. |
| `{language_bank}` | The avatar's voice rules. |

Facts:
{bought}
{upsell_offer}
{upsell_product}
{mechanism}

Customer rows:
{proof_language}
{customer_language}

Voice: {language_bank}

{offer_rule}

{words_rule}

## The task

1. Name the gap from the two product files: what the added product does that the first does not.
2. Write five sections, at the sentence counts given:

| Section | Sentences | Job |
|---|---|---|
| The order is in | 2 to 3 | Confirm what he bought and what it will do, from its file |
| The gap | 2 to 3 | The one thing the first product leaves undone, in a `{customer_language}` row's words |
| The added offer | 3 to 5 | Name it, tie it to the first product, `{mechanism}` if filed |
| The price | 2 to 3 | The filed was-price against the filed price; nothing else as an anchor |
| Yes / no | 2 lines | Yes: "Yes, add <product> to my order — <price>". No: names what he gives up, built on a row |

3. Cut any section over its count. No navigation, no other links.

## Real examples (Brand A)

- The offer box's own opt-out names the loss: "I don't want consistency" (`brands/Brand A/offers/standard-offer-box.md`, element 11). The no-line works the same way.
- Gap row for a face-wash buyer offered FLEX: "Most of them just sold creams and I knew that the problem was not the cream it was the fact that they didn’t sell a brush to get into my pores and really clean them" quoted as a customer, SOURCES `[language_Brand A_fed-up-king_customer_0657]`.
- Loser: "Normally $197, today only $67" with no filed was-price. The anchor is the filed was-price or none.

## Output

```
status: draft
page: upsell
brand: <brand>
from: <bought> → added: <upsell offer, price>

THE ORDER IS IN
THE GAP
THE ADDED OFFER
THE PRICE
YES: <button words>
NO: <link words>

SOURCES
| Line (first words) | Row id or file |
|---|---|

NOTES
- Read time; NO ROW / [UNFILLED] list.
```

## Banned

- An anchor price, saving or "today only" the funnel's files do not hold.
- A second offer, a link away, or a menu.
- "risk-free", "zero risk", "no risk".
- Publishing or changing the live funnel page. This is a draft for the funnel's owner.
