# PAGE WRITING — FIX WHAT BREAKS THE RULES (v2)

<!-- v2 (2026-11-13) = v1 + the bank check's problems ride in the same fix: a quote that is not a bank row word for word. -->

Our page breaks a rule at the places listed below. Two kinds:

- `identity` — the source page's identity survives (a name, place, offer, guarantee, call to action, nav or footer
  text, heading, claim or phrase of theirs). Rewrite the block so nothing of the source survives.
- `bank` — a quote that is not a language-bank row word for word, or a cited row ID that is not in the bank.
  Replace the quote with a row from the customer language below, word for word, with its ID (a shorter quote is one
  unbroken stretch of the row cut at a sentence end), or remove the quote if no row fits.

Rewrite ONLY those blocks, keeping each block's job and our offer, product and brand facts exactly as they are.
Every other block stays word for word.

Return the WHOLE page as ONE json block, the same shape as the page below, and nothing else.

## What breaks the rules, and where
```json
{survivors}
```

## Our page
```json
{page}
```

## Customer language you may draw on (raw bank rows, cite by ID)
{language}
