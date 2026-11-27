# Research fill

**Keys this tool needs:** none to run it. It reports which of the brand's own keys are set (`APIFY_TOKEN`,
`DATABASE_URL`, `GDRIVE_SA_KEY`, the review key, `KALODATA_API_KEY` / `TRENDTRACK_API_KEY`), never their values.

The research system as one repeatable process, the same for every brand and every avatar. It answers two
questions: **what has this brand given us access to**, and **which research step comes next**.

The front door is the `brand-research` skill. Say **set up research for &lt;brand&gt;**, **what does &lt;brand&gt; need to give us for research**, **where is &lt;brand&gt;'s research**, or **what's next
for &lt;avatar&gt;'s research**.

| Command | Does |
|---|---|
| `python3 components/research-fill/fill.py access --brand <b>` | each source the brand can grant: granted or missing, and how to grant it |
| `python3 components/research-fill/fill.py status --brand <b> [--avatar <a>]` | the nine steps per avatar, done or not, with counts |
| `python3 components/research-fill/fill.py next --brand <b> [--avatar <a>]` | the one next step and the command that runs it |
| `python3 components/research-fill/connect.py <source> --brand <b> ...` | connects reviews, surveys, helpdesk, ad comments, interviews or feedback, then dry-runs it |
| `python3 components/research-fill/connect.py test --brand <b>` | a dry run of every connected source |
| `python3 components/research-fill/connect.py schedule` | the daily free pull for every brand in this copy, 05:30 (macOS) |

## What a brand grants

| Source | Unlocks | How |
|---|---|---|
| Scraping account (required) | rooms, outside research, research rounds | its own Apify token on the setup page |
| Ad comments | what people say under its ads | its ads database, or its Meta ad account in `operations/brand.json` |
| Support inbox | customers' words from tickets | `accounts.helpdesk` in `operations/brand.json`, read through its ads database |
| Store reviews | verified buyers' words | review app and key name in `operations/language-pulls.json` |
| Customer surveys | answers from buyers, refunds, leads | response sheets in `language-pulls.json`, shared with its Drive service account |
| Interviews and calls | customer turns from calls | an inbox folder in `language-pulls.json` |
| Market data (optional) | what's selling, competitors | Kalodata or TrendTrack key |

## The fill, in order

1. Name the avatar · 2. Connect the brand's own words · 3. Fill the language bank (25+ lines) · 4. Find where he
talks · 5. Build and gate the profile · 6. Research round: what he watches · 7. Research round: his problem ·
8. Build the matrix · 9. Owner picks concepts.

Steps 4–7 spend money: each shows its price first and runs only on the owner's go. The process lives in
`process.json`; change it there. Each step's check reads what the owning component wrote: the language layer
counts the bank, `components/profiles` (`profiles.init`) says what stands between a profile and ads, research
rounds and the matrix are read from `runs/swipe-organic/`. Reads only: it spends, runs and writes nothing.

| File | What it is |
|---|---|
| `process.json` | the access list and the steps |
| `fill.py` | the check (a ↻ marks a round or matrix older than 30 days) |
| `connect.py` | the connections and the daily schedule |
| `test_connect.py` | tests for the connections |
| `test_fill.py` | tests, on a synthetic brand |

Neighbours: [research gatherer](../research-gatherer/), [language layer](../language-layer/),
[profiles](../profiles/), [swipe organic](../swipe-organic/), [brand sync](../brand-sync/), [setup page](../onboarding/).
