# The variable contract

**What each `{variable}` IS.** Not where a brand's files live — that is the
brand map's job (`brand-maps/<brand>-email-marketing-variables.md`), one per
brand per surface. This file defines the vocabulary; the map resolves it.

Same rule as every other lane: **no prompt names a brand, product, category or
customer.** Brand context enters only through these variables, and where each
one resolves is stated in exactly one place. A run pulling from a path not
listed here is a defect.

Variable names are shared with the copy and image lanes wherever the thing is
the same thing. Only the contents differ — `{record}` is an email record here,
`{spec}` is the same brand-free construct it is everywhere.

## Produced by the chain

| Variable | Made by | Consumed by |
|---|---|---|
| `{triage}` | stage 0 — lane, format, voice, sender | every stage after it |
| `{record}` | stage 1 — the objective record of the source email | 2, 3, 5, 6, 7, 8, 9 |
| `{spec}` | stage 2 — the construct; structure is read from it, never re-derived | 3, 4, 5, 6, 7, 8 |
| `{brand_context}` | stage 2b — the files this source needs, and what was left out | 3, 5, 6, 7, 8 |
| `{injection}` | stage 3 — the only source of copy lines downstream | 4, 5, 6, 7, 8 |
| `{placement}` | stage 4 — scroll budget, CTA plan, image plan | 5, 6, 7, 8 |
| `{subject_set}` | stage 5 — control + variations, each a subject/preview pair; all ship | 8, 9 |
| `{expansion}` | stage 6 — gated on ORGANIC; empty when skipped | 7, 8 |
| `{close}` | stage 7 — the whole email assembled, end to end | 8, 9 |
| `{blocks}` | stage 8 — the typed block list, plus its BLOCKS JSON | 9, `render.py` |

## Supplied per brand

| Variable | Canonical role | Used by |
|---|---|---|
| `{avatar}` | the core avatar file | 3, 5 |
| `{language_bank}` | how this customer talks — the rules, not the verbatims | 3, 5, 6, 7, 8 |
| `{objection_bank}` | the objection bank | 4, 7 |
| `{product_file}` | the product spec for the product being sold | 3, 4, 7, 8 |
| `{offer_file}` | prices, guarantee wording, never-pair rules | 4, 7, 8 |
| `{hook_ledger}` | every subject line already sent; human-owned statuses | 5 |
| `{brand_name}` | literal value, supplied as a one-line file | 3 |
| `{sender_identity}` | who the email comes from, and what they may claim | 3, 5, 7 |
| `{customer_language}` | real sentences real customers said, **queried per stage** — never a dumped file | 5, 6, 7 |

`{customer_language}` is not a file. It is a query against the brand's verbatim
bank, run per stage against what that stage needs, and it comes from the copy
lane's `language.py` — one implementation, both lanes. A brand with no bank
gets a stage that says so rather than a stage that writes the sentence itself.

## Supplied per run

| Variable | What it is |
|---|---|
| `{today}` | the date, so a stage never guesses at one |
| `{source}` | the swiped email, or a teardown record from another lane |
| `{source_reference}` | where the source came from, for the brief |
| `{subject_count}` | how many subject variations beyond the control |

## Where a brand resolves

Per brand, in `brand-maps/<brand>.md`, one `variable | path` row each. The map
lives in the **build**, not in the brand folder: the brand tree is read-only to
this tool, so pointing at it is our business and how it is organised is theirs.

Anything a map does not declare falls back to the conventional layout in
`email.py`. Anything neither declares arrives as `(none supplied)` and the
stage says so rather than inventing it.
