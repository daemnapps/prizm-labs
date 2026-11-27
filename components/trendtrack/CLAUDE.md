# components/trendtrack — the TrendTrack door

Owner: **the owner** (engine and definitions both). Runs by: person.

Finds the ecom brands and ads that are scaling, and a brand's third-party pages. Its sweeps land in the same paid swipe pool as AdPlexity's, so intake and both teardowns read them unchanged. AdPlexity stays; this does not replace it.

## The four new-resident questions

- **Engine + owner.** `trendtrack.py`. Owner the owner.
- **Definitions + curator.** None. The API contract is at `https://api.trendtrack.io/v1/openapi.json`.
- **The plane it emits.** `runs/trendtrack/market/<label>/`: `run.json` (credits spent and left) plus `ALL.json` for a sweep or `result.json` for a pull. `check`, `lookup` and `pages` write nothing. Not on the shared runs filer yet.
- **What the manifest declares.** No manifest.

## The contract

- `check`, `lookup`, `pages` cost 0 credits.
- `sweep <domain> --slug <competitor> --max-credits N` writes an `ALL.json` that `components/swipe-paid/build.py cluster` reads. Items carry their landing page, so `build.py resolve` spends no AdPlexity credit on them.
- `pull <path> --max-credits N --label <label>` is any other paid route. It refuses a pull with no limit, or a limit over the ceiling.
- The docs say 1 credit per row, but a live `/v1/ads/query` cost 5 credits for 3 rows (2026-11-05). Sales history and image search are listed at 4. `sweep` sizes its calls from the measured cost and stays under the ceiling. Show the filters and the cost and get a yes before a paid pull.

## Open

- `TRENDTRACK_API_KEY` is read by name through the key loader, and is in the keys file on the owner's Mac only. It is not yet in `components/keys/names.json`, so teammates' files and the mini do not have it. Their counts in `test_ld37_names_registry.py` are ruled, so adding it is the keys curator's change.
- TrendTrack's reach can read 0 for a brand with active ads. Do not rank on reach alone.
