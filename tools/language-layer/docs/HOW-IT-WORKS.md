# How Language Works

Everything a customer or prospect says, from any source, is taken in, labelled, given an ID and stored once. Every tool then reads it from that one place. Brand-agnostic, product-agnostic.

**Why it exists: to make the business better.** Every line is there to improve marketing, products, operations, customer service, customer experience and the website.

Page: (team page)

## 1 · How it flows

```
IN                           THE MIDDLE                              OUT
surveys                      research gatherer (pull · clean)        video chain (hooks → scripts)
ad comments (Meta)      ──▶        │                                 copywriter
organic comments (Apify)           ▼                                 emails
support tickets (Gorgias)    labeller (lane · awareness · ID)        landing pages
reviews · forums                   │                                 briefs · stories
interviews · panels                ▼                  language  ──▶  marketing calendar
our own copy                 THE BANK  ──────────────▶  layer        customer service
                                   ▲  follows THE SCHEMA            avatar development
                                   └──── used lines marked "used" ◀──┘
```

## The actual chain, step by step (real run 2026-09-29, @brand-b TikTok post #1)

### Going in: words → bank
| # | Step | What happens | Code | Model | Result |
|---|---|---|---|---|---|
| 1 | Start | Command with brand, avatar, post link; up to 400 comments/post | research-gatherer/comments.py:102, ownvoice.py:46 | no | |
| 2 | Pull from Apify | TikTok/IG/FB comment scraper; key by name APIFY_TOKEN (spare on 403) | comments.py:52, components/apify/apify.py:91 | no | 400 pulled |
| 3 | Clean | Strip emails, phones, addresses, order numbers, @handles; exact-comment link, date said, source id | comments.py:32, annotate.py:98 | no | |
| 4 | Skip what's in the bank | Link already in the bank → skipped | comments.py:127, annotate.py:321 | no | post #2: 394 new |
| 5 | Intake read | 30 at a time vs the avatar's rules: keep/drop + why, use, topics, sub, ad use | annotate.py:186, prompts/annotate-row.md, claude-sonnet-5 | **yes** | kept 338, dropped 62 |
| 6 | Labeller | 20 at a time: awareness, sophistication, lane the words point to; split-retry on a bad reply. Origin + voice by rule | language-layer/tools/label.py:186, prompts/label-awareness-v2.md, label.py:55 | **yes** | product 130 · unaware 97 · unclear 52 · most 40 · solution 16 · problem 3 |
| 7 | Pick the lane | Ordered → customer/churned; else the words decide | annotate.py:261 | no | prospect 270 · lead 60 · customer 8 |
| 8 | Build the line | Names → [name]; source, signal, topics, use, labels attached | annotate.py:278 | no | |
| 9 | ID + file | language_<brand>_<avatar>_<lane>_NNNN (next after highest); into prospects/leads/customers | annotate.py:401, :337, :363 | no | 338 filed |
| 10 | Run record | filed/dropped/held, report, page with the intake prompt verbatim | comments.py:139 → runs/research/<brand>/comments-<time>/ | no | |
| 11 | Save to the repo | A session commits and pushes (the gatherer doesn't) | by hand | no | 497b7c89c, 611 lines |

Other ways in, same steps 5–9: **ownvoice** (Meta ad comments: warehouse, then Apify top 15 ads; Gorgias tickets: warehouse; since last run). 2026-09-28: Brand B 212 filed, Brand A 167. **deep** runs Reddit questions per sub-avatar, labeller only (no intake read).

### Coming out: bank → ad
| # | Step | What happens | Code |
|---|---|---|---|
| 1 | The prompt asks | `?hooks` slot; chain fills the avatar and lane; result-first hooks switch to result tags | video-teardown/machine/chain.py:842 |
| 2 | Chain's own map | Tags per stage, then hands off to the engine | video-teardown/machine/language.py:38 |
| 3 | Engine searches | Skip retired + used; collapse repeats ("said N×"); filter lane + awareness; rank | language-layer/language_layer/engine.py:383, :274 |
| 4 | Widen if thin | Under 8 matches → relax topics, then lane, then both | engine.py:402 |
| 5 | Hand to the model | `[id] "exact words"` + speaker, tags, source, date, likes | engine.py:351 |
| 6 | Mark as used | Cited/quoted IDs → used lane; bank never edited | video-teardown/machine/mark_used.py:122 → language/used/<run>.json |

Copywriter: same steps 1–5 through its own map; no awareness/used filter and no mark-used yet.

## What starts each source today (checked 2026-09-29)

Nothing puts language into the bank automatically right now. The only scheduled pull (nightly Reddit) is paused.

| Source | Tool that pulls it | What starts it | Last run | State |
|---|---|---|---|---|
| Surveys (Brand B 13,405) | none; 3 Google Form sheets imported once | nothing | 2026-08-25 | no tool |
| Meta ad comments | `gather.py ownvoice` | a person asks | 2026-09-28 | tool, no trigger |
| Organic comments | `gather.py comments --url` | a person asks | 2026-09-29 | tool, no trigger |
| Gorgias tickets (Brand A 218) | `gather.py ownvoice` | a person asks; Brand B off | 2026-09-28 | tool, no trigger |
| Reviews (Brand A 12, Amazon, secondhand) | none | nothing | 2026-08-25 | no tool |
| Reddit / forums | `gather.py deep` | was nightly 02:30, paused 2026-09-23 | 2026-09-23 (0 rows, Reddit blocked) | paused |
| Interviews / panels (Brand A 105 + 55) | none; transcripts imported once | nothing | 2026-08-25 | no tool |

On record: the nightly Reddit pull was switched off 2026-09-23, "no automatic Apify spend". Its last four runs never landed cleanly (three couldn't save, one blocked by Reddit).

## Putting every source on a trigger

Runs on the Mac mini (always on; already holds the Apify and Gemini keys under the run grant).

| Source | Cadence | What it takes | Size |
|---|---|---|---|
| Surveys | daily | sheet importer: new answers since last run → labeller → bank | build, small |
| Meta ad comments | daily | ownvoice on a schedule (Brand B free from warehouse; scrape uses Apify) | schedule, Apify spend |
| Organic comments | daily | watch own accounts for new posts; since-last-run record | build, small, Apify spend |
| Gorgias tickets | daily | same ownvoice run; Brand B needs its helpdesk named | schedule, one setting |
| Reviews | daily | puller for the store's review app (which app per brand?) | build, needs the app name |
| Reddit / forums | nightly | turn back on after fixing the save step and the Reddit block | fix, Apify spend |
| Interviews / panels | on arrival | transcript dropped in evidence folder → split, labelled, filed | build, small |
| After every pull | every run | refresh the source list, save to the repo, update the bank page | build, small |

Calls only the owner can make: lift "no automatic Apify spend" for scraping pulls; name Brand B's helpdesk and each brand's review app.

## 2 · The four places

| | Place | What it is |
|---|---|---|
| **The data: the bank** | `brands/<brand>/core-avatars/<avatar>/language/` | What people said. Files by lane (`prospects`, `leads`, `customers/`, `churned/`), plus `used/` |
| **The rules: the schema** | `brands/language-schema.md` | Lane, awareness, sophistication, internal vs external, voice, row IDs, source IDs, the used lane, repeats |
| **The machine: the language layer** | `tools/language-layer/` | Search (every tool asks it for words), the tools, `docs/STANDARD.md` |
| **The output: its runs** | `runs/language-layer/` | Each brand's state (`BANK.md`, the page), rename lookups, lane-move lists, test sets |

## 3 · What's on every line

| Field | What it says | Example |
|---|---|---|
| id | Permanent name, by the Naming Standard | `language_brand-b_avatar-one_customer_9607` |
| text | The exact words, typos and emoji intact | "<a joke reaction>" |
| lane | prospect · lead · customer · churned. A known order decides; otherwise the words do | prospect |
| awareness | The doctrine's five levels (plus unclear) | product-aware |
| sophistication | What they've already heard from the market | none · claim-heard · believes-none |
| origin | Internal (our customers, our properties) or external | internal |
| voice | The audience, or our own brand's copy | audience |
| source | Where it came from, with a link to the exact comment, ticket or answer | `post_tiktok_brand-b_7000000000000000001` |
| use · topics | What the words do and what they're about | objection · refund-reason · keyword-cta |
| signal | Likes, and how many times the same line was said | said 41× |

## 4 · Where it applies

| Use | Typical ask | Status |
|---|---|---|
| Ads: video hooks and scripts | hooks · problem-aware · unused first | Live: video chain |
| Copywriting | close → objection · refund-reason · expectation-gap | Live: copywriter |
| Emails | the avatar's language rules | Live: reads the rules file |
| Landing pages, briefs, stories | sub-avatar rows · story-shaped rows | Live: lab tools |
| Customer service | ticket · refund-reason · expectation-gap · churn-risk | Brand A tickets flowing in; no CS tool reads them yet |
| Avatar development | lane × awareness counts · loudest repeats | Live: the Language Bank page |

## 5 · What already talks to it, and how

| Tool | Direction | How |
|---|---|---|
| Research gatherer (`components/research-gatherer`) | writes in | deep research; `comments` (Apify: TikTok, Instagram, Facebook); `ownvoice` (Meta ad comments + Gorgias tickets). Every line is labelled and named before filing |
| Labeller (`language-layer/tools/label.py`) | proposes | Lane, awareness, sophistication, origin and voice, read in context. Called by the gatherer; can backfill a bank — as a proposal under `runs/language-layer/`, which the gatherer's `apply` writes |
| Bank tools (`rename_ids`, `map_sources`, `keyword_cta`) | propose | Ids, source ids + the registry, the `keyword-cta` tag — each a proposal under `runs/language-layer/`, written by `gather.py apply` |
| Video chain (`tools/video-teardown`) | reads out | Prompts carry `?stage:avatar:funnel`. The engine returns rows tagged for that stage, filtered by awareness, unused first, widening when thin. After a brief ships, the lines it used are marked used |
| Copywriter (`tools/copywriter`) | reads out | Same engine, with its own stage map |
| Landing pages (lab) | reads out | Per stage, plus rows for a named sub-avatar |
| Outlier brief (lab) | reads out | Customer words for creator briefs |
| Story builder (lab) | reads out | Story-shaped rows, no model |
| Marketing calendar (`components/marketing-calendar`) | reads out | The brand's avatar roster |
| Email production (`tools/email-production`) | reads rules | The avatar's `language/rules.md`, not the rows |
| Voice check (`components/qc-checks`) | checks | Copy was written against the right brand's language rules |
| CS metrics (`components/cs-metrics`) | same source | Reads Gorgias ticket stats from the warehouse; doesn't read or write the bank |

## 6 · Plugging in a source: Gorgias

Status: Brand A **on** (218 ticket lines in the bank). Brand B **off** (no helpdesk named).

1. **Read from:** the company data warehouse (the same Gorgias tables CS metrics reads).
2. **Turned on by:** `"helpdesk": "gorgias"` in `brands/<brand>/operations/brand.json`. Each `ownvoice` run then pulls every ticket message since the last run.
3. **Each message:** signatures, addresses and names stripped; labelled (lane, awareness, origin = internal); filed under source ID `ticket_<brand>_gorgias`, linked to its ticket and message number. Whether the sender has ordered comes along with it.
4. **Lands in:** the same bank as every other source, so ads, copy, email and CS all see it at once.

Any other source joins the same way: a way to pull it, a source ID by the Naming Standard, and the labeller. Nothing downstream changes.

## 7 · What's in it today (counted 2026-09-29 — counts blanked in the public copy)

| Source kind | Brand B | Brand A |
|---|---:|---:|
| Survey | n | n |
| Post comments (ads + organic) | n | n |
| Support tickets | n | n |
| Interviews | n | n |
| Panels | n | n |
| Community (forums, Reddit) | n | n |
| Reviews | n | n |
| Our own copy | n | n |
| Database | n | n |
| Source not yet linked | n | n |
| **Total** | n | n |

## 8 · The names: three words, one family

- **language**: the bank, the data inside each brand
- **language-schema**: the rules every line follows
- **language-layer**: the machine that does the work, and its output folder `runs/language-layer/`

The output folder is named after the machine, like every other machine's (`runs/video-teardown/`, `runs/copywriter/`). Renamed from `runs/language-bank/` on 2026-09-29.

## 9 · System check (the developer's fit → ready), 2026-09-29

Memos: `runs/system-integration/components-language-layer/`. No model calls.

| Level | Before | After |
|---|---|---|
| L1 · runs on the system | Blocked (O4, O5, O6, O7) | O5 closed 2026-09-29: the tools propose, the gatherer applies |
| L2 · anyone on the team can run it | Blocked | Pass |
| L3 · the Mac mini | n/a (runs inside its callers) | n/a |

- Video chain: 40 lines per stage for both brands, awareness filter holds, used lines held back.
- Copywriter: 40 lines per stage (injection, hooks, render, close) for both brands.
- Research gatherer reaches the labeller.
- Tests: layer 29/29; layer build tests 74/74; video chain 28 + 4; copywriter 19. All pass.
- Fixed: keys by name only (O6), output always under `runs/language-layer/` (O4), no brand names in code (O7), no guessed laptop paths, runs on Python 3.9, README with how to run it.
- **O5, closed 2026-09-29:** `label.py apply`, `rename_ids.py`, `map_sources.py` (and the new `label.py origin`, `keyword_cta.py`) no longer write into `brands/`. Each writes a proposal to `runs/language-layer/<brand>/<run>/` and hands it to `components/research-gatherer/gather.py apply` — the one machine with the carve-out — which checks it and writes it. One command still does both.
- **O10, closed 2026-09-29:** the labeller's default is `claude-sonnet-5`, the registry id (`sonnet` is its alias in `components/models/models.json`).
- Small, the developer or the ops lead: untagged `LL-1` (language layer) and an "assumption" ownership line in the layer's CLAUDE.md (gated) — proposed text in the handoff under `runs/system-integration/components-language-layer/`.

## Update 2026-09-29 (afternoon)

- System check: **L1 PASS, L2 PASS** (memo `runs/system-integration/components-language-layer/20260929-0906Z-fit/FIT.md`). Bank clean-up tools now write a proposal under `runs/language-layer/`; `gather.py apply` (research-gatherer, the one writer allowed in `brands/`) applies it. Labeller model: claude-sonnet-5.
- Ad comments on our own ads are internal: Brand B 212, Brand A 81.
- IDs and source IDs 0 off standard; Brand B unlinked sources 28 → 15. keyword-cta tagged: Brand A 47 ("recipe"), Brand B 2.
- Waiting on review: 21 hand-typed Brand B comment lines, 13 with linked twins pulled today (`runs/language-layer/<brand>/<run>`).
- Brand B awareness backfill running (12,053 unique lines).

## Next: our own feedback forms (idea, not built, 2026-09-29)

Brand B's Google Forms in the email flows built most of its bank:

| Form | Answers | Asked | Missing |
|---|---|---|---|
| Customers | n (Apr 2023 – Aug 2026) | 11 open questions (gut instinct, problem, likes, one thing to change, next-product wish…) | order count, subscription status |
| Followers | n (Mar 2023 – Sep 2025) | why interested, why not bought, unanswered questions, brands used, what would help | purchase status (about n said they'd bought) |
| Refunds | n (Feb 2024 – Jul 2026) | refund reason, unmet expectations, what we could've done, alternative | subscriber flag |

The plan: each brand runs its own branded, interactive forms. Questions are asked by lane at the moment it happens (prospect, lead, new, repeat, subscriber, refund, cancel), through email flows, after delivery, at cancel and on the site. Answers land already sorted (who was asked and what was asked are known, not guessed), go through the labeller into the bank daily, and are tagged for marketing, product, operations, CS, CX or the website.

## Update: daily trigger live (2026-09-29)

`com.daemn.language-daily`, 5:30am daily on the Mac (launchd → `components/research-gatherer/daily.py` from origin/main; log `~/Library/Logs/daemn/language-daily.log`; summaries `runs/research/_system/daily/`). Free sources only; Apify blocked inside the run.

| Source | Mode | Status | First run |
|---|---|---|---|
| Surveys | `surveys` | live (Brand B, 3 sheets) | 39 pulled, 34 filed |
| Reviews | `reviews` | live Brand B (Junip); Brand A waiting on Judge.me token + shop domain | 18 pulled, 17 filed |
| Meta ad comments (warehouse) | `ownvoice --no-scrape` | live | nothing new |
| Gorgias tickets | `ownvoice` | live Brand A; Brand B's separate Gorgias account isn't synced to the warehouse (the ops lead) | nothing new |
| Interviews / panels | `interviews` (drop in `language/evidence/inbox/`) | live | inbox empty |
| Organic comments, Reddit | `comments`, `deep` | on request (Apify) | — |

Per-brand settings: `brands/<b>/operations/language-pulls.json`.
