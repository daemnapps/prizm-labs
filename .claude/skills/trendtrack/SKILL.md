---
name: trendtrack
description: Look up ecom brands in TrendTrack and pull their ads — a brand or domain goes in; its active ads, reach, third-party pages or a sweep filed for the paid swipe pool come out. Use whenever someone says "check <brand> on TrendTrack", "what third-party pages is <brand> running", "sweep <brand> from TrendTrack", "what's scaling on TrendTrack", "how many TrendTrack credits are left".
---

# TrendTrack

> **Activates component:** `components/trendtrack` — `trendtrack.py` runs free lookups and capped paid pulls.

External dependencies: `components/keys/loader.py` (reads `TRENDTRACK_API_KEY` by name), `components/swipe-paid/build.py` (files a sweep into the pool).

## Spends credits — say so before you run

`check`, `lookup` and `pages` are free. `sweep` and `pull` spend credits, and a live query cost 5 credits for 3 rows. Show the filters and the credit cost, get a yes, then run with `--max-credits` set to that number.

## The steps

```
python3 components/trendtrack/trendtrack.py check
python3 components/trendtrack/trendtrack.py pages "<brand or domain>"
python3 components/trendtrack/trendtrack.py sweep <domain> --slug <competitor> --max-credits <n>
python3 components/swipe-paid/build.py cluster <the ALL.json it names> <competitor>
```

Then carry on with the `swipe-paid` steps. Sweep items already carry their landing page, so `resolve` spends no AdPlexity credit on them.
