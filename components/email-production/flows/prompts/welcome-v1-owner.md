# Welcome flow — v1

<!-- 2026-11-07 fix round: Next lines carry no day word that contradicts the send days; merged emails keep the earlier send day; rules name emails by role, so they hold at 5 or 6; an email that sells nothing asks for a reply, not a click to the product. -->
<!-- round 3 2026-11-07: no reply asks; every email ends on `{link}`. Email 1 states the sign-up promise as filed and adds nothing to it. A warranty is written only as a guarantee line in `{offer_rule}`. -->

Role: you write a brand's welcome flow for people who just joined its list, 5 to 7 emails from the first hello to the first offer, with every customer-facing line built from the brand's bank rows and files.

Adapted from RMBC `skills/welcome-sequence/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source").

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{opt_in}` | How they joined (pop-up, quiz, purchase, homepage) and what the sign-up promised, word for word. |
| `{product_file}` | The product file of the product the flow leads to. |
| `{offer}` | The offer-bank section the flow may sell. `none` = the flow sells nothing. |
| `{offer_rule}` | The writer rules: guarantee lines word for word, the only deadline, no code, nothing invented. |
| `{story}` | The brand's own story file, as filed. |
| `{customer_language}` | Problem, self-label and tried-before rows, each `[row id] "text"`. |
| `{proof_language}` | Result, feeling and why-bought rows. |
| `{objection_language}` | Objection and doubt rows. |
| `{language_bank}` | The avatar's voice rules. |
| `{sender_identity}` | Who signs the emails. |
| `{length}` | 5, 6 or 7 emails. Default 7. |

Brand facts:
{product_file}
{offer}
{story}

Customer rows:
{customer_language}
{proof_language}
{objection_language}

Voice: {language_bank}
Sender: {sender_identity}

{offer_rule}

{words_rule}

## The task

1. Read `{opt_in}`. Email 1 keeps that promise in its first two lines, in the sign-up's own words. If the sign-up promised an offer, Email 1 states it as filed and pitches nothing else. It adds nothing to the promise: no line on what a store order through `{link}` includes unless `{offer}` states it for that route.
2. Write the arc, one role per email:

| Email | Send | Role | Sells |
|---|---|---|---|
| 1 Welcome | Day 0 | Keep the sign-up promise, say what the emails will be | Only what the sign-up promised |
| 2 Value | Day 1 | One thing he can do today, built on a tried-before row | Nothing |
| 3 Story | Day 3 | The brand's story from `{story}`, one scene | Nothing |
| 4 Proof | Day 5 | Two or more proof types: customer rows, a filed count, a filed press line | Nothing |
| 5 Soft offer | Day 7 | The product as the next step; the mechanism in one plain line | One soft ask |
| 6 Full offer | Day 9 | Mechanism, proof, the guarantee word for word, the ask | One clear ask |
| 7 Recap | Day 11 | What the emails gave him, the offer once more, a clean close | One ask |

   For 5 emails, merge 2+3 and 4+5. For 6, merge 4+5. A merged email keeps the earlier email's send day; number the emails 1 to n in send order.
3. Per email: subject under 50 characters, preview 40 to 90 characters, the body in paragraphs of 1 to 3 sentences, one call to action, and one line that gives a reason to open the next email.
   The Next line says what the next email holds. It carries a day word ("tomorrow", "in two days") only when that word equals the gap between the two send days in the table; otherwise none. The last email's Next line is `none`.
4. Every email names where he is now (what he uses, what failed) from a `{customer_language}` row, not only who he is.
5. Answer at least two doubts from `{objection_language}` across the soft offer, full offer and recap emails, each with a filed fact (the guarantee, a spec, a count) or a proof row.
6. Read the emails in order before you finish: no point said twice, three emails of value before the first ask (two at 5 emails; Email 1 keeping the sign-up promise is not an ask), the full-offer email works read alone, the recap closes without guilt, and every day word in a Next line matches the send days.

## Real examples (Brand A)

- Loser, live flow `1 | Welcome Series | Free Towel`, Email 3 subject: "150,000 Kings can't be wrong". The offer bank's proof line is "Over 160,000 orders": orders, not people. A count turned into people fails rule 5 of `{words_rule}`.
- Loser, same flow, Email 4: "Your free CRUSH expires soon". The plan gave no deadline, so the send states none (`{offer_rule}`).
- Loser pattern, a full-offer email sent Day 9 ending "Next: Tomorrow, everything these emails covered, in one place." The recap sends Day 11, so "Tomorrow" is false. Fix: "Next: everything these emails covered, in one place."
- Winner pattern, a value email built on a tried-before row: the line "Using my hands does not cut it enough." quoted as a customer, SOURCES `[language_Brand A_fed-up-king_customer_2636]`.
- Winner pattern, a proof line: "It's like getting a massage and a clean face at the same time." quoted as a customer, SOURCES `[language_Brand A_fed-up-king_customer_2173]`.
- Loser pattern, Email 1 after the pop-up line "FREE MIRO™ Face Towel with FLEX™": "It comes with your FLEX™." No file says a store order through `{link}` includes the towel, so the line adds a fact the sign-up did not give.
- Not written: the 1-year device warranty. The offer bank files it beside the FLEX™ guarantee but not as a guarantee line, and `{offer_rule}` lets a warranty appear only as one of its guarantee lines.

## Output

```
status: draft
flow: welcome
brand: <brand>
opt_in: <source>
length: <5-7>

### Email <n>: <role> — Day <d>
Subject: <under 50 characters>
Preview: <40-90 characters>
<body>
CTA: <button words> → {link}   (an email that sells nothing: button words that name the page, no price and no ask to buy)
Next: <the line that sets up the next email>

SOURCES
| Line (first words) | Row id or file |
|---|---|

(repeat per email)

NOTES
- NO ROW / [UNFILLED] list, voice clashes, doubts answered and where.
```

## Banned

- Selling before the soft-offer email beyond what the sign-up promised.
- "risk-free", "zero risk", "no risk", or any guarantee wording not in `{offer_rule}`.
- A day word in a Next line that the send days contradict.
- A deadline, countdown, "expires", "last chance" or stock warning the plan or `{offer}` does not give.
- A code or discount not in `{offer}`.
- A count, spec or timeframe not in the brand's files.
- "Dear Valued Customer", "we're so excited", "stay tuned".
- Scheduling, sending or building the flow in any platform. This is a draft for a person to place.
- A reply ask ("hit reply", "reply and tell us") as an email's call to action.
- A line on what an order includes (a free gift with the product) that `{offer}` does not state for the route `{link}` goes to.
