# What every file here is

Kept because the build grew fast and a repo nobody can read is a repo nobody
can correct.

## Read these to understand the system

| File | What it is |
|---|---|
| `README.md` | How to run it, and what state it is in |
| `DOCTRINE.md` | The nine rules that make a lane trustworthy |
| `CONTRACT.md` | What each `{variable}` IS — the vocabulary |
| `STAGE-DELTAS.md` | What each stage changes from the copy chain, and what it does not |
| `PARKED.md` | Delivery, feedback and flows — real, deliberately out of scope |

## The chain

| File | What it is |
|---|---|
| `prompts/` | One file per stage. Highest `-vN-` wins; retired ones go to `superseded/` |
| `email.py` | The runner. `--dry-run` resolves everything and spends nothing |
| `render.py` | Draws a run into a real 600px email |
| `paths.py` | Where the brand tree is |

## The vocabularies — one each, on purpose

| File | What it is |
|---|---|
| `email-types.json` | **The only list of email kinds.** 38 types in 5 categories, each with its role in the arc and what follows it. Triage reads this rendered; the page reads it too |
| `brand-maps/<brand>-email-marketing-variables.md` | Where one brand's files live, for THIS surface. Video scripts and static ads get their own |
| `brand-maps/<brand>-email-sender-identity.md` | Who an email comes from and what they may claim |

`formats.md` was deleted 2026-08-28 — it was a second list of email kinds for
the same question, and two lists is how a source gets triaged as one thing and
written as another.

## Pulled facts — data, never typed

| File | What it is | Made by |
|---|---|---|
| `calendar/derive.py` | Orders by month, day, hour | — |
| `calendar/ledger.py` | Every subject line sent | — |
| `calendar/index_sends.py` | Every email sent, whole | — |
| `calendar/products.py` | A profile per product, from the live catalogue | — |
| `calendar/accounts.json` | Which sending account a brand uses | hand-kept |
| `brands/<brand>-ledger.md/.json` | 308 subject + preview lines | `ledger.py` |
| `brands/<brand>-sends/` | 309 emails, whole — copy, images, buttons | `index_sends.py` |
| `brands/<brand>-catalogue.json` | The storefront product feed, cached | `products.py` |
| `brands/<brand>-segments.md` | The campaign segment audit | hand-written |

## The page

| File | What it is |
|---|---|
| `model.py` | The categories, the wells, the gaps — the page's data, not the chain's |
| `build_system.py` | Renders `model.py` + the prompts into the artifact |

## Not committed

`results/` (runs), `email-production.html` and `.md` (regenerated), and
`*-derived.json` (re-pullable).
