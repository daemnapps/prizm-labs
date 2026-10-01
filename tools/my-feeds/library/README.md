# swipe-library

One front door to everything that has been swiped — organic formats, the
torn-down videos, one feed per customer type, every competitor's live ads —
written where the team already looks, and a public page for the half that
can be public.

**The page:** [daemn.co/feeds/](https://daemn.co/feeds/)

| | |
|---|---|
| `machine/library.py` | reads the private workspace and writes: `SWIPE LIBRARY.md` at the root of the shared drive, and a `FEED.md` in every feed's folder on Drive. It does not write the site — `docs/feeds/` comes from the team workspace's `feedsexport.py` |
| `context/artifacts.md` | the pages that show this work |

## What is in the library, and where each half lives

| What | Public (this repo) | Team (Drive, read through Higgsfield) |
|---|---|---|
| **Organic formats** — the structure under posts that worked | `tools/my-feeds/organic/formats/` · the zip on the site | — |
| **Swipe videos** — every post torn down, filed under its format | the rebuild sheets, text only | `lab/damon/swipe-organic/records/swipe-videos/<code>/` — the video, the sheet, the beat strip |
| **My Feeds** — one feed per person: what that person watches | [daemn.co/feeds/](https://daemn.co/feeds/) — public since 1 Oct 2026 (Damon reversed the earlier "never"): top posts per person, read-only, from a static export with a no-secrets scan | `lab/damon/swipe-organic/records/avatar-feeds/<feed>/FEED.md` — every kept post, linked |
| **Paid sweeps** — every competitor's live ads, blocked by angle | `tools/my-feeds/paid/angle-shapes/` — the recurring shapes, brands described not named | `lab/damon/swipe-paid/<brand>/angles/NN_…/` — video, photos, page captures |
| **The index** | this README | `SWIPE LIBRARY.md` — counts, every feed, every code by format, every sweep |

Nothing private crosses the line. The packs carry formats, angle shapes and
counts, and name nobody. My Feeds (daemn.co/feeds/) shows public posts and
competitors' public ads by name — never our own brands, our ad accounts, our
customers or our keys; its export refuses to write if its no-secrets scan
finds any of them.

## Run it

    python3 machine/library.py             # writes the Drive index and every FEED.md
    python3 machine/library.py --dry-run   # counts only

The two packs the page links to are built by their own tools in the private
workspace (`swipe-organic/bundle.py --public`, `swipe-organic/paidpack.py`);
this tool only indexes what they and the feeds produce. `AI_WORKSPACE` and
`DRIVE_ACCOUNT` pick the two planes.

## For editors, in Higgsfield

`../../editor-onboarding/prompts/03-library-v1-damon.md` — "open the
library for <brand>": reads the index and the brand's feeds, shows the
posts, and hands any one of them to the teardown.
