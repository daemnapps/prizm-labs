# Soap-opera flow — v1

Role: you write a 5 to 7 email story told in chapters, each ending on an open question, where the product's mechanism arrives as the story's turn rather than as a pitch.

Adapted from RMBC `skills/soap-opera-sequence/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source").

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{protagonist}` | Whose story: `founder` (from `{story}` only) or `customer` (from one before-and-after or customer record, as filed). |
| `{story}` | The brand's story file, or the one customer record the story follows. |
| `{mechanism}` | The brand's filed mechanism line for this product (its position file), word for word. |
| `{product_file}` | The product file. |
| `{offer}` | The offer-bank section the last email sells. |
| `{offer_rule}` | The writer rules. |
| `{customer_language}` | Problem and tried-before rows. |
| `{proof_language}` | Result and feeling rows. |
| `{objection_language}` | Doubt rows. |
| `{language_bank}` | The avatar's voice rules. |
| `{sender_identity}` | Who signs. |
| `{length}` | 5, 6 or 7. Default 5. |

Story and facts:
{story}
{mechanism}
{product_file}
{offer}

Customer rows:
{customer_language}
{proof_language}
{objection_language}

Voice: {language_bank}
Sender: {sender_identity}

{offer_rule}

{words_rule}

## The task

1. Before writing, fill five lines from the inputs only: the protagonist; the struggle (a `{customer_language}` row that matches the protagonist's filed situation); what failed (a tried-before row or a filed fact); the turn (`{mechanism}`); what changed (a filed before-and-after or a `{proof_language}` row). A line no input fills is `[UNFILLED]` and the story is cut to what is filed.
2. Write the chapters:

| Email | Beat | Ends on |
|---|---|---|
| 1 Backstory | The struggle, in a scene the reader recognises | Something changes |
| 2 Things get worse | What was tried and failed | He nearly stops |
| 3 The turn | `{mechanism}`, found inside the story | What it led to |
| 4 What else changed | A second result, from a different row | One more thing |
| 5 The offer | The story closes; `{offer}`, the guarantee word for word, one ask | The ask |

   For 6, split Email 2 into the build-up and the low point. For 7, add a "what didn't work" email after 2 and a proof email after 4.
3. Every email opens by answering the last one's open question. Paragraphs of 1 to 3 sentences. Name the product no earlier than Email 3. Emails 1 and 2 sell nothing.
4. A founder story uses only what `{story}` says happened. A customer story uses only that customer's filed words and record; nothing is added to their life.
5. Read the chapters as one story. If the story falls apart without the product, it is a pitch: rewrite.

## Real examples (Brand A)

- Tried-before row for Email 2: "They were only temporary solutions to a permanent problem" quoted as a customer, SOURCES `[language_Brand A_fed-up-king_customer_4181]`.
- The turn for Email 3, the filed position line (`brands/Brand A/brand-identity/position.md`, quoted in brief 0322 stage 4i): "What you wash with now can't reach it. The FLEX does."
- Loser: a founder chapter that adds a detail `{story}` does not hold (a year, a place, a family member). Invented biography fails `{offer_rule}`.

## Output

```
status: draft
flow: soap-opera
brand: <brand>
protagonist: <founder|customer>
story engine: protagonist · struggle [row] · failed [row|file] · turn [file] · changed [row|file]

### Email <n>: <beat> — Day <d>
Subject: <under 50 characters, story words, no pitch>
Preview: <40-90 characters>
<body>
Ends on: <the open question>   (Email 5: CTA: <button words> → {link})

SOURCES
| Line (first words) | Row id or file |
|---|---|

NOTES
- Open-question strength 1-5 per email, the weakest named; NO ROW / [UNFILLED] list.
```

## Banned

- Naming the product before Email 3; any ask in Emails 1 and 2.
- A scene, name, date, place or result no input holds.
- A cliffhanger the next email does not pay off.
- "risk-free", "zero risk", "no risk", a deadline or a stock warning not given by `{offer_rule}`.
- Scheduling, sending or building the flow in any platform.
