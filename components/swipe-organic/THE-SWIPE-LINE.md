# The Swipe Line — every post has a lane

Artifact: (team page)
Read from the live board on 2026-10-03. Mirror of the page the owner reads.

The swipe board stopped being a pile and became an index: 5,278 organic posts,
every one sorted, filed under the avatar it speaks to.

## Two hours, 2 October — what shipped

| Time | What |
|---|---|
| 15:46 | Menu down to four. Objects folded into Light. |
| 16:14 | Paid Open goes to the AdPlexity creative, not the Facebook Ad Library. Thumbs 220px → 440px. |
| 16:17 | Avatar picker became a tree (brand → core → sub). |
| 16:28 | Looksmax moved under Glow Up — 264 cards that sat outside their avatar. |
| 16:42 | Picker tidied to one column. BASED and Clipper back under the avatar. |
| 16:48 | Mega menu: who the avatar is, five real posts, every source. |
| 16:59 | Views and likes on their own row. One signal per card, fixed slot. |
| 17:31 | Everything got a lane. Selling became visible. |

## The sort

A card with no lane passed **every** lane filter, so all of BASED, all of
Clipper Videos and all of the owner's saves showed under Entertainment and
Educational alike.

| Lane | What it is | Kept | Thrown out |
|---|---|---:|---:|
| Entertainment | Watched for its own sake | **3,105** | 95 |
| Educational | Teaches or explains | **645** | 18 |
| Selling | Partner tag, code, link, or the brand's own account | **222** | 595 |
| Junk | Nothing to read, or the search dragged it in | 16 | 581 |
| *(no lane)* | — | **0** | — |

Selling is kept only where the feed asks for it (`keep_lanes` in its
`sources.json`). An avatar feed wants what the person watches; BASED is a shop
and Clipper is a remake pool, so dropping their selling would empty them. His
own saves keep every lane — the save IS the keep decision.

## Where it stands

- **5** core avatars across two brands · 20 feeds under them · 2 saved scrolls
- **5,278** organic posts, all laned
- **1,124** competitor ads across 7 advertisers
- **50** formats banked · **211** posts matched to one · **5,067** unread

## How a swipe becomes an ad

1. **Swept** — each feed runs its own 20–25 searches and hashtags
2. **Sorted** — lane, keep/drop, and a format when the caption makes it plain (haiku, 40 at a time)
3. **Picked** — best untouched entertainment post per feed, ranked by sent rate, then punch past following, then views
4. **Torn down** — the video machine, 18 stages, **48m 09s median**, to a brief written for a person
5. **Queued** — one record per brief, waiting on the owner's yes or no
6. **Made** — generation, or a creator with a shot sheet

## What the sort changed downstream

`briefs.py` picks `lane in (None, "entertainment")`. Before the sort all 1,097
unlaned posts qualified through that `None` — including every BASED shop ad.
Now 3,105 entertainment posts feed the brief line and the 222 kept selling posts
do not. That `None` branch is dead code, and the open question is real: if
BASED's selling posts should reach briefs, that is a rule to write.

## Open

- **5,067 posts have no format.** The format is what a brief is built on, so
  this is the next bottleneck between the index and production.
- **The 1,097 were sorted by rules, not the model.** The `claude` CLI's OAuth
  session had expired. Rules are in `sift_rules.py`; records are tagged
  `feed-sift-rules-v1`. A re-login and `sift.py --redo` replaces them.
- **Organic thumbnails are still 200px.** Paid re-rendered at 440px because
  AdPlexity re-serves originals; organic media lives on the Drive.
