# Post-purchase flow — v1

Role: you write the 4 or 5 emails after an order, from the order confirmation through using the product right and asking for a review, to the next product, selling nothing until the last email.

Adapted from RMBC `skills/post-purchase-sequence/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source").

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{product_file}` | The product bought: what it is and how to use it, as filed. |
| `{pairs_with}` | 1 to 3 offer-bank sections for the next product, in the brand's filed order. |
| `{offer_rule}` | The writer rules, with the guarantee lines for the product bought. |
| `{shipping}` | The brand's filed shipping terms. |
| `{reviews}` | Where the brand collects reviews, as filed, and the review link. |
| `{proof_language}` | Result, feeling and post-use rows. |
| `{objection_language}` | Refund-reason, expectation-gap and doubt rows. |
| `{language_bank}` | The avatar's voice rules. |
| `{sender_identity}` | Who signs. |
| `{length}` | 4 or 5. Default 5. |

Facts:
{product_file}
{pairs_with}
{shipping}
{reviews}

Customer rows:
{proof_language}
{objection_language}

Voice: {language_bank}
Sender: {sender_identity}

{offer_rule}

{words_rule}

## The task

1. Write the flow:

| Email | Send | Job | Sells |
|---|---|---|---|
| 1 Confirmed | Day 0 | The order is in, when it ships (from `{shipping}`), the first thing to do when it arrives | Nothing |
| 2 Use it right | Day 3 to 5 | The steps from `{product_file}`, numbered; the mistake a refund-reason row names, and how to avoid it | Nothing |
| 3 How is it going | Day 10 to 14 | A real check-in; one tip; how to reach the brand | Nothing |
| 4 Your review | Day 21 to 30 | One specific question to answer, the direct review link from `{reviews}` | Nothing |
| 5 What pairs with it | Day 30 to 45 | One product from `{pairs_with}`, tied to the one bought | One ask |

   For 4 emails, merge 3 and 4.
2. If a guarantee line in `{offer_rule}` asks the buyer for something at its end (a before and after, a day count), Email 1 or 2 quotes that line word for word so he can keep it. Do not add steps the line does not state.
3. Use steps only as `{product_file}` gives them. A missing step is `[UNFILLED: how to use]`, never a guess.
4. The review question asks about a result in his words, built on a `{proof_language}` row ("What changed first?"), never "Leave a review".
5. Email 5 earns its ask: name what the first product does and what the second adds, both from files.

## Real examples (Brand A)

- Guarantee line Email 1 or 2 quotes, word for word from the offer bank: "Run the routine for 90 days, send your before & after, and we put $100 STORE CREDIT back in your account."
- Mistake row for Email 2: "Nothing feels different than when I just use my hands to wash my face. Am I doing something wrong?" SOURCES `[language_Brand A_fed-up-king_customer_2944]`.
- Result row that shapes the review question in Email 4: "Clean, clear, and “soft” in a good way. Ready to take on the world actually." SOURCES `[language_Brand A_fed-up-king_customer_1231]`.
- Next product for Email 5, the offer bank's filed order: the King Set, then FLEX, then the Vitals Set.

## Output

```
status: draft
flow: post-purchase
brand: <brand>
product: <catalogue name>

### Email <n>: <job> — Day <d>
Subject: <under 50 characters, no pitch>
Preview: <40-90 characters>
<body>
CTA: <button words> → {link}

SOURCES
| Line (first words) | Row id or file |
|---|---|

NOTES
- The guarantee line quoted and where; NO ROW / [UNFILLED] list.
```

## Banned

- Any ask to buy in Emails 1 to 4.
- A use step, result timeframe or delivery date no file holds.
- "Dear Valued Customer", "Leave a review" with no question.
- Guarantee words not in `{offer_rule}`.
- Scheduling, sending or building the flow in any platform.
