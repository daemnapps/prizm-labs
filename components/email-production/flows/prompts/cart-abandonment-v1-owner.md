# Cart-abandonment flow — v1

<!-- 2026-11-07 fix round: the press example came from a test swipe and is not filed, so Email 2 uses a filed count; length outside 3-4 falls back to 4; no contradicting day words. -->
<!-- round 3 2026-11-07: the stock-line example is dropped, so Email 4 states urgency only from a line `{product_file}` or `{offer}` holds; no gift with the order, store credit or warranty unless `{offer}` and `{offer_rule}` state them. -->

Role: you write the 3 or 4 emails sent to someone who put a product in the cart and left, each taking away one reason he stopped, from a plain reminder to the last touch.

Adapted from RMBC `skills/cart-abandonment-flow/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source").

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{product_file}` | The product file of the item left in the cart. |
| `{offer}` | The offer-bank section for that item: its price, was-price and any filed offer. |
| `{offer_rule}` | The writer rules: guarantee lines word for word, the only deadline, no code, nothing invented. |
| `{shipping}` | The brand's filed shipping terms. Missing = `[UNFILLED: shipping terms]`. |
| `{press}` | Filed press lines, word for word with their credit. May be empty or `[UNFILLED]`: then no press line is written. |
| `{proof_language}` | Result, feeling and why-bought rows. |
| `{objection_language}` | Objection and doubt rows. |
| `{customer_language}` | Tried-before and comparison rows. |
| `{language_bank}` | The avatar's voice rules. |
| `{sender_identity}` | Who signs. |
| `{length}` | 3 or 4. Default 4. Any other value: write 4 and list it under NOTES. |

Facts:
{product_file}
{offer}
{shipping}
{press}

Customer rows:
{proof_language}
{objection_language}
{customer_language}

Voice: {language_bank}
Sender: {sender_identity}

{offer_rule}

{words_rule}

## The task

1. Name the main doubt by the price in `{offer}`:

| Price | Main doubt | Second doubt |
|---|---|---|
| Under $30 | Do I need this? | Shipping costs more than it's worth |
| $30 to $100 | Is this the best option? | Can I get it cheaper? |
| $100 to $300 | Can I justify it? | What if it doesn't work for me? |
| Over $300 | It's a big decision | I need to ask someone |

   Then find the `{objection_language}` and `{customer_language}` rows that say that doubt in his words.
2. Write the flow:

| Email | Send | Job | Rules |
|---|---|---|---|
| 1 Reminder | 1 hour | Show the item, one line on what it does, back to the cart | No offer, no urgency |
| 2 Others chose it | 24 hours | Two proof types: a customer row, a press line, a filed count | No offer |
| 3 The doubt | 48 hours | Name the main doubt in a row's words; answer it with a filed fact; the guarantee word for word, in the body | No new offer |
| 4 Last touch | 72 hours | The one urgency line on file, or none; any filed offer for this item | Only filed urgency and offers |

   For 3 emails, merge 2 and 3.
3. Every email shows the item he left by its catalogue name. The button goes back to the saved cart (`{cart_link}`), never to the product page.
4. Subject under 50 characters, preview 40 to 90, paragraphs of 1 to 3 sentences. He nearly bought: write to him as a customer, not a stranger. A day word ("yesterday", "tomorrow") appears only when the send times above make it true.
5. Check before you finish: forgetting (1), wanting others' word (2), the named doubt (3), a reason to act now (4, or written as "none on file").

## Real examples (Brand A, FLEX at $69.99, so the main doubt is "Is this the best option?")

- Loser, draft flow `TS | Abandoned Cart`, Email 1: "You left something behind / Return to your cart and keep building your routine." No item named, so it fails step 3.
- Comparison row for Email 3: "I used to have a Foreo, when that was first released. I far prefer this!" quoted as a customer, SOURCES `[language_Brand A_fed-up-king_customer_5198]`.
- Doubt row for Email 3: "Does it actually work tho?" SOURCES `[language_Brand A_fed-up-king_lead_2587]`, answered by the guarantee from `{offer_rule}`: "90 days. If your skin doesn't transform, full refund. You keep the FLEX™."
- Filed count for Email 2 when `{press}` is empty, word for word from `brands/Brand A/products/offer-bank.md` (Proof): "Over 160,000 orders". It counts orders, so it is never written as people.
- Urgency for Email 4 when `{product_file}` and `{offer}` hold no stock or deadline line: none. Email 4 keeps the item, the price and the guarantee, and NOTES says "Urgency: none on file".

## Output

```
status: draft
flow: cart-abandonment
brand: <brand>
item: <catalogue name> — <price from {offer}>
main doubt: <from the table> · rows: <row ids>

### Email <n>: <job> — <send>
Subject: <under 50 characters>
Preview: <40-90 characters>
<body>
CTA: <button words> → {cart_link}

SOURCES
| Line (first words) | Row id or file |
|---|---|

NOTES
- Where the guarantee sits; which filed offer, if any, and in which email; NO ROW / [UNFILLED] list.
```

## Banned

- An offer, discount or code in Emails 1 to 3; any discount not in `{offer}`.
- "Your cart is about to expire", "items are going fast", a countdown or a deadline not in `{offer_rule}`.
- "items in your cart" with no item named.
- A funnel-only price or offer that `{offer}` keeps off email.
- "risk-free", "zero risk", "no risk", or the guarantee only in a P.S.
- Scheduling, sending or building the flow in any platform.
- A gift with the order (a free towel), a store credit or a warranty that `{offer}` and `{offer_rule}` do not state for this item.
