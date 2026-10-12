# Avatar feeds — the team's window into each avatar's world

The goal (the owner, 2026-08-29): a custom IG / TikTok / YouTube feed **per
avatar**, pulled continuously, presented visually, so the creative
strategist — not just the owner — selects what goes to teardown. the owner's
saves stream (SAVES.md) is the personal version; this is the team
version, and the two feed the same pools.

## How a feed is built

1. **Sources are receipts, not guesses.** Each avatar's feed pulls from
   `records/avatar-feeds/<brand>--<avatar>.json`: the accounts and hashtags
   PROVEN for that avatar (from its profile receipts, swipe-organic
   members, and graded saves). avatar-two starts with its 4 clipper
   accounts + the core hashtag family. New sources enter only with a
   receipt line saying where they came from.
2. **Pull** — `python3 feed.py --avatar <brand>--<avatar>` reads recent
   top posts per source (TikTok + Instagram today; YouTube needs an
   actor picked before it joins), dedupes against the avatar's seen
   ledger, and writes `records/avatar-feeds/<brand>--<avatar>/feed.json`.
3. **The board** — `python3 feedboard.py --avatar …` renders the feed as
   a visual page (thumbnails embedded, receipts on every card) published
   as a shareable artifact. **The page saves selections into itself**:
   the strategist ticks "queue for teardown", hits save, and the page
   republishes with the picks recorded — no terminal, no repo access
   needed on their side.
4. **The handoff** — a session reads the board's saved picks and drops
   them into the teardown intake. Statuses stay human-owned end to end.
5. **Real time** — the pull is re-runnable and cheap per avatar
   (dedup makes re-sweeps incremental); scheduled daily sweeps come once
   the sources stabilize. A weekly delta would be the same muscle
   (`watch.py` was removed unused 2026-10-07, SI-60 (swipe export cleanup)).

## Rules

- One feed per avatar; avatars never blend (their sources don't either).
- Every card carries its receipts (views/likes + which source pulled it).
- Nothing auto-deletes: unpicked cards age out of the board but stay in
  the ledger.
- Grading to awareness stage happens at teardown intake, not in the feed
  — the feed's job is surface, the strategist's job is taste.

## The backend — how the feed is actually built (reset 2026-08-29)

the owner's step-back ruling: foundation first, repo-first, nothing tied to
one machine, no frontend until the backend is clear.

One folder per avatar feed, four files:

```
records/avatar-feeds/<brand>--<avatar>/
  sources.json        what we pull and WHY — every source has a receipt
  items.json          the CATALOG — one record per post ever seen:
                      its own publish date (relevance), author, caption,
                      hashtags, which source found it, first_seen,
                      category (empty until the categorization layer),
                      status (human-owned)
  observations.jsonl  append-only HISTORY — every sweep, one line per
                      item observed with its counts at that moment; a
                      post's growth = the difference between its lines
  sweeps.jsonl        the RUN LOG — when each sweep ran, what it
                      observed, what was new, what failed
```

Principles:
- **Items are permanent; metrics are observations.** The catalog never
  shrinks; history accrues. That is the historical view.
- **Organic only, in code** — declared ads never enter.
- **Host-agnostic**: `python3 feed.py --avatar <a>` needs only an
  APIFY_TOKEN (env var first, local key file fallback). It runs the same
  from a cloud routine, a teammate's machine, or the owner's — scheduling is
  a deployment choice layered on top, never baked in. (The earlier
  Mac-local launchd job was removed for exactly this reason.)
- **Frontends read the store, never own data.** The page layer comes
  after the backend is ruled clean: it will render the catalog with
  posted dates, paginate ("show more"), and read history for trends.

Open deployment decision: where the daily schedule lives — a cloud
routine (needs APIFY_TOKEN provisioned there) or a designated machine.
Parked for the owner/the developer.

## The curation loop — how the feed learns (designed 2026-08-30, the owner's brief)

The goal, in his words: know what the avatar is watching over time, so
marketing evolves to fit it in real time. The mechanism, honestly stated:
no platform shows us a person's watch history — what we CAN measure is
what is accelerating in the avatar's own spaces. The loop:

1. **Velocity, not size.** Because every sweep re-observes known posts,
   growth-per-hour-since-posted is computable from observations.jsonl.
   A 50k-view post that doubled overnight in the avatar's space beats a
   5M-view post that stopped moving. Velocity is the watch signal.
2. **Sources earn their seats.** Every item carries its source. Each
   cycle, sources are scored by the winners they delivered; producers
   get pulled deeper, dead sources get retired — recorded in
   sources.json with receipts, never silently.
3. **Winners reveal new sources.** Hashtags on winning posts, creators
   who appear 2+ times, formats that repeat — proposed as candidate
   sources with receipts ("found because 3 winners carried it"), run on
   probation, earn permanence by performance. Affinity logic, applied
   to feeds.
4. **No human in the loop** (the owner's ruling, 2026-08-30 — supersedes
   the taste-filter point above): the feed curates itself on signal
   alone. Velocity decides winners; sources live or die by what they
   deliver; discovery runs on receipts. The page is a window, never a
   control panel — nobody's picks feed the learning.
5. **The other shelves feed it.** Culture-dig room members become
   candidate sources; the saves catalog's categories define what a
   "win" looks like per avatar.

Every cycle's changes (scores, retirements, adoptions) are appended to
the feed folder's log — the feed's evolution is itself a record.

## Graph hops — discovery follows edges, not search (built 2026-08-30)

the owner's ruling: people don't find content by search; they follow
edges — post → creator → who that creator runs with. Platform APIs do
not expose recommendations (the FYP is each platform's crown jewel), so
the system walks the edges that are open without a login:

- **creator hop** — creators behind winners become candidate sources
- **mention hop** — @handles inside winning captions
- **cross hop** — a TikTok winner's handle verified on Instagram
  (follower check throws out fake matches)

`hops.py --avatar <a>` seats candidates in sources.json with status
**probation** and a receipt naming the exact winner that surfaced them;
every adoption logs to discoveries.jsonl. Probation sources get swept
like any other and earn a permanent seat — or retirement — by what they
deliver. The feed's own handles live in sources.json `exclude` (data,
never code). YouTube hops wait on a channel puller (display names
aren't pullable handles). IG suggested-accounts and the FYP itself wait
on persona accounts.

## Persona accounts — the FYP as a source (kits built 2026-08-30)

A persona account is a real, dedicated account (never a brand account)
trained until its For You page IS the avatar's feed — the platforms'
own recommendation engines working for us. `personakit.py` builds each
account's starter pack from data we own: the feed's sources, winners'
creators, the owner's saves in the avatar's categories (per-kit
config.json — data, not code), and the sounds those saves ran on.
Kits live in `records/persona-kits/<brand>--<avatar>/` with a warm-up
protocol. Account creation is a human step; once live, the FYP gets
captured into the feed backend as `kind: persona-fyp`. Flagged
honestly: platforms fight automated reading — dedicated accounts only.

## Entry rules + page controls (the owner 2026-08-30)

His review: IG pulled off-avatar/low-reach content; old posts undated;
no sorting. Fixed: (1) IG #glowup retired with receipt — it pulls
K-beauty, not the avatar; (2) entry rules live in sources.json as data
(max_age_days 120; hashtag/search finds must clear 10K views or 1K
likes; account sources enter freely — we chose the creator); (3) TikTok
post dates decoded from the post id itself when the scrape lacks them;
(4) the page has sort (Rising / Newest / Most viewed) and time windows
(30d / 90d / all), defaulting to Rising x 90d.
