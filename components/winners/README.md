# winners

Owner: the owner


A brand's loop from ad results back to the writing prompts. Say "audit <brand>", "score <brand>" or "show me the winners" to Claude (skill: winners), or run one command:

```
python3 components/winners/winners.py <verb> --brand <brand>
```

| Step | What it does | Verb | Lands in `runs/winners/<brand>/` |
|---|---|---|---|
| **Results** | Reads what each ad spent and sold, from the warehouse. If the warehouse can't be reached, the newest media-buying file, and says so. | `score` (first half) | `score/<asof>/score.json` |
| **Audit** | Every creative that spent in a time frame, copies merged, ranked by purchases, tagged, on one board. Core = the fewest top creatives that make 60% of purchases. | `audit`, `tag`, `videos` | `audit/<since>_<until>/`, `tags.json` |
| **Bank** | One record per brand of every ranked creative with its numbers and words, one snapshot per window. Row ids never move and words are never dropped. | `bank`, `bar` | `bank.json` |
| **Taught** | Beside the feed, `taught.md`: the top ad per angle, the desk's calls, the send-back reasons, the score per prompt version (`feed_sections.py`). | `feed` | `taught.md` |
| **Messages** | Every winner by its teardown's own core message, what the brand's rules cut, what to brief next and what to tear down; the page. | `messages status\|next\|check\|page\|start` | `messages/` |
| **Feed** | The top rows of the widest audit window (longest since-to-until; tie, the newest), with numbers and words, plus one loser for contrast. A shorter audit adds snapshots and rows and never changes the ranking or Core. Once a bar is set, only rows that clear it in that window are listed. The hook prompt's `{winners}` slot reads this file. | `feed` | `feed.md` |
| **Score** | Gives every ad an origin and joins it to the prompts that wrote it through its brief number and the brief register. Rolls results up by origin, hook prompt, brief prompt, the winner each run borrowed from and the prompts on record elsewhere. | `score` (second half) | `score/<asof>/score.md` |
| **Creators** | Every creator video that ran as an ad: its results by trybe id since the program began, banked with the per-video read's format, angle and hook, judged on the creator bar (`bar --creators`; the bank's bar when unset). Writes what to brief next for the swipe pick. | `creators` | `creators/<asof>/trybe.json`, `bank.json`, `feed.md`, `brief-next.json`, `brief-next.md` |
| **Leaderboard** | Every creator and clipper, one row per person across Trybe and the paid-per-view campaigns: reach, paid out, sales, clips, rank, move since last week, tier. Pulls only what is free. | `leaderboard` | `leaderboard.json`, `leaderboard.md`, `leaderboard/<date>.json` |
| **Who** | Sales by who each ad was for: avatar, sub-avatar, demographic, desire, awareness, doubt, through each ad's brief (`components/briefs/aim.py`). Always an unknown row and the coverage; few-sales rows are labelled; no calls. Files on disk only: the newest score, or the newest desk report with `--source desk` (live ads only). | `who` | `who-<date>/{who,who-desk}.{json,md}` |
| **Views** | The same months in both years by group, what's on screen and message; whole-store revenue against ad spend by week. Facts only. | `yoy`, `store` | `views/` |

```
ad results ──→ audit ──→ bank ──→ feed.md ──→ hook prompt ({winners})
    ↑                      ↑                       │
    │                      │          run.json: prompt version per stage
    │                      │          4b-hooks.md: BORROWED_FROM lines
    │                      │                       │
    └──── score ←── ad name brief-NNNN ←── briefs.json ←┘
```

## Where every dollar came from

Every ad in a score gets one `origin` and a `family` (a readable creative name). The first that holds:

| Origin | What it means | Family |
|---|---|---|
| `chain` | Its brief leads to a writing or teardown run that records a hook or brief prompt version. | register title, else the run |
| `banked` | Its ad id is in a bank row, or its name reaches one through `base()`, `script_key()` and that window's `merges.json`. A proven creative still running. | the bank row's name |
| `brief, made outside writing` | Its name carries a brief, old spellings included (`p128` is brief-0128), with no writing run behind it. `made_in` is the register's lane and type, `unknown` when the brief isn't in the register. Prompts its run folder records go in `prompt_other` and the "Other prompts" roll-up. | register title, else the run, else the brief |
| `pre-system` | None of the above. Over $500 and it is listed under "Can't trace". | `base()` then `script_key()` |

`matched` in `score.json` holds the chain ads and `unmatched` all the others, so the chain rows the bank reads have not moved. A bare p-number the register gives to another brand is not read as this ad's brief.

## Commands

```
winners.py audit  --brand <b> --since D --until D [--title T]   pull, rank, media, dedupe, sheets, build; bank and feed when nothing is left to tag
winners.py tag    --brand <b> --window L --tags FILE            save tags; build, bank, feed
winners.py videos --brand <b> --window L --top N                download the top videos, for teardowns (they spend: on a person's go)
winners.py bank   --brand <b> [--window L]                      bank an audit window, the newest if none is named
winners.py feed   --brand <b> [--window L]                      rebuild feed.md; --window prints another window and writes nothing
winners.py score  --brand <b> [--days 90]                       results, the join, bank the chain-made ads, rebuild feed.md
winners.py creators --brand <b> [--days 90] [--results F]          creator videos: results by trybe id, bank, feed, brief-next
winners.py leaderboard --brand <b> [--no-pull]                  creators + clippers ranked; free pulls first (campaign reports, Trybe all-time + 7 days)
winners.py who --brand <b> [--days N] [--source score|desk]     sales by who each ad was for; --days takes the score on disk whose window is nearest
winners.py five --brand <b>                                     the five always-on briefs: proven ads ranked by purchases, distinct format x angle
winners.py bar    --brand <b> [--min-spend N] [--max-cpa N] [--min-roas N] [--open]   set the bar and mark every row; no flags prints it; --open clears it
winners.py bar    --brand <b> --creators [--min-spend N] [--min-purchases N] [--min-roas N]   the creator bar: rows with a trybe id only; paid rows don't move
winners.py status --brand <b>|all                               one screen, no paths
winners.py system --brand <b>|all                               every step, ad results to a brief: state and the next command
winners.py messages --brand <b> status|next|check|page|start    winners by core message, gates to the next brief
winners.py shapes --brand <b> todo|check|build                  story shape per winner, by money, with the presets
winners.py statics --brand <b> [--days 30] [--min-spend 100]    the winning image ads
winners.py mirror --brand <b> --window L                        a window's pictures and videos to the Drive
winners.py yoy    --brand <b> [--window L] [--from-month MM --to-month MM]   the same months in both years; widest window, last 3 full months by default
winners.py store  --brand <b> [--weeks 12]                      store revenue against ad spend by week, from the warehouse
```

A window is its folder name, `<since>_<until>`. Python 3.9.6 and PIL. Reads ad accounts only; nothing in one changes.

## Limits

- Only runs that went through the writing chain count as `chain`. Everything else shows its origin and the reason.
- A new audit window starts from the widest window's merges until `dedupe` saves its own.
- Only the top 10% of an audit's creatives are in the bank and tagged, so `banked` and the `yoy` tags cover those; the rest read `pre-system` and "Not tagged yet".
- An ad counts under every winner id its run cites, so the borrowed-from roll-up can add up to more than the total.
- A window already on a row is not replaced: a second pull of the same window adds new rows and leaves numbers on existing rows as they were.

Prompt candidates: `stage5-creator-brief-v36-owner.md` sits in `proposed/`, so the picker doesn't read it. To wire it after the prompt owner picks it, add `"winners": "runs/winners/<brand>/feed.md"` to stage5's `stage_vars` in `components/video-teardown/machine/extra-stages.json`.

Core teardowns, written up per brand: `runs/winners/<brand>/audit/<window>/teardowns-<brand>.md`.

## The leaderboard file

`runs/winners/<brand>/leaderboard.json`, rebuilt on every `leaderboard` run (status `draft`).

It reads:
- The payout programs, `runs/creator-machine/<brand>/hub/programs.json` (rows with `"via": "content-rewards"`).
- Each campaign's newest report pull.
- Trybe, all-time and for the last 7 days.
- Creators' public handles from the creator inbox.
- Dated snapshots in `runs/winners/<brand>/sources/<source>-<date>.json`, for dashboards with no API (`kind: snapshot`, `read`, `totals`, `top`).

No report link is ever written out.

What's in it:
- `as_of`, `updated`, `week` {`from`, `to`, `basis`}. The basis is the change since the leaderboard of about a week ago. In the first week it is the clips posted in the last 7 days plus Trybe's last 7 days. A snapshot is never counted in the week.
- `totals`: `views`, `clips`, `paid`, `sales_driven`, `cost_per_1000_views`, `earning_this_week` (people paid this week) and `people`, all for all-time. Then `all_time` and `week`, each with `views`, `clips`, `paid`, `sales_driven`, `orders`, `trybe_gmv`, `ad_purchases`, `ad_purchase_value`, `cost_per_1000_views`. Then `by_platform` (`whop`, `trybe`, each snapshot source).
- `unattributed`: clips, payouts and sales no named person accounts for. They are counted in the totals.
- `creator_bar`.
- `sources`: `campaigns`, `snapshots` (`source`, `read`, `note`, `sales`, `orders`, `paid`, `ready_unpaid`, ...) and `trybe`.
- `people` (ranked), one entry per person: `rank`, `sales_rank`, `move` (places up since last week; `null` = new), `tier`, `name`, `handles`, `platforms`, `social`, `campaigns`, `proven_videos`, `snapshot_read` (the read date when the row comes from a snapshot), `all_time`, `week`, `key`.
- `creators`: the same people, flat, for pages: `rank`, `sales_rank`, `handle`, `platform`, `views`, `paid`, `sales_driven`, `tier`, `move` (whole number or `"new"`), `snapshot_read`.

What the numbers mean:
- Reach is clip views plus Trybe ad impressions.
- Paid is the Content Rewards payout plus Trybe earnings plus the snapshots' payouts.
- The cost per 1,000 views counts only the payouts made for views.
- Sales driven is what the store credits to a person (Trybe GMV, affiliate sales). The ads' platform purchases are a separate count and are never added to it.
- Ranking: `rank` is by reach, then paid, then sales driven. `sales_rank` ranks everyone with sales driven.
- Tiers: `top earner` is the top 3 by paid or by sales driven. `proven` means a video clears the creator bar, or the store credits them with sales. Everyone else is `rising`.
- A snapshot row always shows its read date: it is not live data.
