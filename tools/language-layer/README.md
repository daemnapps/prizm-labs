# language-layer

## How to use it → https://dashboard.the company.com/atlas#c-components-language-layer

The customer-language query engine, and the tools that keep a brand's
language bank named, sourced and labelled. Contract, rules and ownership:
`CLAUDE.md`. The bank rules: `brands/language-schema.md`. Why the rules are
what they are: `docs/STANDARD.md`.

## Fed daily (2026-09-29)

The banks are fed every morning from the free sources of our own customers'
words — warehouse ad comments and Gorgias tickets, Google Form answers, store
reviews (Junip, Judge.me), interview transcripts dropped in a brand's inbox —
by `components/research-gatherer/daily.py` (launchd `com.daemn.language-daily`,
05:30 on the owner's Mac). After the pulls it runs `tools/map_sources.py` per
brand (a proposal the gatherer applies) and `tools/bank_page.py` for every
brand, so `runs/language-layer/_system/bank.html` and `BANK.md` are rebuilt daily.
Apify sources stay on request.

| Source | Mode | Schedule | State file |
|---|---|---|---|
| Ad comments (warehouse) + Gorgias tickets | `gather.py ownvoice --no-scrape` | daily 05:30 | `runs/research/<b>/ownvoice-state.json` |
| Google Form surveys | `gather.py surveys` | daily 05:30 | `runs/research/<b>/surveys-state.json` |
| Store reviews (Junip / Judge.me) | `gather.py reviews` | daily 05:30 | `runs/research/<b>/reviews-state.json` |
| Interview / panel transcripts | `gather.py interviews` | daily 05:30 | `runs/research/<b>/interviews-state.json` |
| Source registry | `tools/map_sources.py` → `gather.py apply` | daily, after the pulls | — |
| Bank page | `tools/bank_page.py` | daily, last | — |

What each brand pulls: `brands/<brand>/operations/language-pulls.json`.
The full table and the rules: `components/research-gatherer/README.md`,
"Daily language pull".
