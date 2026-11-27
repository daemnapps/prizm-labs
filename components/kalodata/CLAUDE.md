# components/kalodata — the Kalodata door

Owner: **the owner** (engine and definitions both). Runs by: person.

Reads what is selling on TikTok Shop: videos, products, creators and shops ranked by estimated revenue. Read only.
TrendTrack stays the door for Meta, partnership ads and TikTok ads by days running; it carries no TikTok Shop revenue.

## The four new-resident questions

- **Engine + owner.** `kalodata.py`. Owner the owner.
- **Definitions + curator.** None here. A watch list (the searches a brand runs) lives with the tool that uses it.
- **The plane it emits.** `runs/kalodata/<label>/`: `videos.json` (or products, creators, shops) and `run.json` (credits spent, ceiling). Runs filer: none yet.
- **What the manifest declares.** No manifest.

## The contract

- Every paid read names `--max-credits` and is refused before it is sent when it would pass it.
- Prices read from the vendor's page 2026-11-25: ranking 0.1 credit per 100 rows, detail 0.1, video link 0.5, 1 credit about $0.10.
- `KALODATA_API_KEY` is read by name through the key loader. Not in any keys file yet, so no live read has been made: the calls are built from the vendor's docs and tested against a stand-in.
- Revenue is Kalodata's estimate. Rank by it, never quote it.
