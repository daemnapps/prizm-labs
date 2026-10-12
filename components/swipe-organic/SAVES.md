# The saves stream — the owner's taste as intake

the owner curates the way he always has: he saves posts on Instagram
(viral videos, novel formats, market/avatar opportunities). This makes
that habit machine-readable without changing it.

## The flow

1. **He saves.** Nothing changes about how he browses.
2. **Sweep** — on "sweep my saves", a session opens
   instagram.com/daemn.is/saved/all-posts/ in HIS logged-in Chrome
   (claude-in-chrome), scroll-collects the post links, and drops them in
   `records/damon-saves/captured-urls.json`. His saves are private; his own browser is
   the only honest door, so the sweep needs Chrome open on his machine.
3. **Scrape** — `python3 saves.py` reads the inbox, pulls each post's
   public data (author, reach, caption, hashtags, sound), and appends
   receipted rows to `records/damon-saves/catalog.json` (+ `.md` mirror).
   Already-seen URLs are skipped, so re-sweeps are cheap.
4. **Grade & route** — a judgment pass fills bucket
   (viral | novel-format | market-opportunity), awareness grade
   (rubric in brands/awareness-model.md), route and avatar fit.
   The session proposes; **the owner's taste overrides.**
5. **Route** — rows land where they work: the shared organic swipe pool
   (daemn/swipes/organic-posts), formats.py shape candidates, or the
   opportunity lane. A save with no clear read stays `hold`.

## Why this matters

Every save is taste ALREADY APPLIED — the highest-signal intake the
system has. First sweep (2026-08-29): 21 saves → 18 graded, 10 fed the
organic pool (its first real rows), 6 became shape candidates, 2 sit in
the opportunity lane.

## Sweep log

| Date | Swept | Reachable | Kept | Personal | Note |
|---|---|---|---|---|---|
| 2026-08-29 | 429 | 369 | 369 | 42 | first full capture |
| 2026-08-31 | +49 | 44 | 44 | — | batch 2026-08-31 |
| 2026-09-22 | +144 | 137 | 128 | 9 | stopped at the 08-31 set; 7 private/deleted |

**How the sweep actually loads (09-22):** the saved grid only fetches the
next page on real input — a mouse-wheel scroll or the End key — never on a
scripted `scrollTo`. Grab the links after every page (the grid drops rows
above the viewport), feed the new URLs to `saves.py --inbox <batch file>`,
then pull covers + kind from the run's dataset (`runs/last/dataset/items`),
grade, and `videos.py` for the reference files.
