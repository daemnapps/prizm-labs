#!/usr/bin/env python3
"""The TikTok kit — four Apify actors from one maker (unseenuser), one door.

Hooked 2026-09-23 on owner's word: "let's hook tiktok trends scraper because it
also has the shop scraper and creator intelligence suite which we need."

    python3 tiktok.py trends  --mode popular_hashtags --region US --max 30 --out DIR [--dry-run]
    python3 tiktok.py trends  --mode search_keyword --q "skincare routine" --max 30 --out DIR
    python3 tiktok.py shop    --mode shop_search --q "face scrub" --max 20 --out DIR
    python3 tiktok.py shop    --mode creator_showcase --user hyram --out DIR
    python3 tiktok.py creator --profiles hyram @jamescharles --max 30 --out DIR [--transcripts]
    python3 tiktok.py sound   --clips 7664281509390813953 --pages 1 --out DIR

| door    | actor                                   | what it answers                                       | price / row |
|---------|-----------------------------------------|-------------------------------------------------------|-------------|
| trends  | unseenuser/TikTok-Search-Scraper        | what's trending: feed, hashtags, creators, searches   | $0.0035     |
| shop    | unseenuser/TikTok-Shop-Scraper          | TikTok Shop: products, GMV/sales, reviews, a creator's showcase | $0.0045 |
| creator | unseenuser/TikTok-posts                 | every video a creator posted, with stats (+ transcripts) | $0.005 (+$0.01 AI transcript) |
| sound   | unseenuser/tiktok-sound-tracker-scraper | one sound: its details and the videos using it        | $0.004      |

Every run states its price ceiling before it starts and is capped there with
Apify's own `maxTotalChargeUsd`, so a run can never spend past what it said.
Rows land in the CALLER's folder (`--out`), as `rows.json` + `run.json` — this
component keeps no plane of its own (see CLAUDE.md).

Trend Hunter's `trending_feed` is a random slice of the feed, not a ranking
(tested 2026-09-23: 30 videos, no sound repeated). For trending SOUNDS the
sounds pool uses automation-lab/tiktok-trends-scraper instead
(components/swipe-organic/sounds.py).
"""
import argparse, json, os, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify as A  # noqa: E402

DOORS = {
    "trends": ("unseenuser~TikTok-Search-Scraper", 0.0035),
    "shop": ("unseenuser~TikTok-Shop-Scraper", 0.0045),
    "creator": ("unseenuser~TikTok-posts", 0.005),
    "sound": ("unseenuser~tiktok-sound-tracker-scraper", 0.004),
}
TRENDS_MODES = ["trending_feed", "popular_hashtags", "popular_creators", "search_keyword",
                "search_hashtag", "search_users", "top_search", "song_intel"]
SHOP_MODES = ["shop_search", "shop_catalog", "product_details", "product_reviews", "creator_showcase"]


def payload(a):
    if a.door == "trends":
        p = {"mode": a.mode, "region": a.region, "maxResults": a.max}
        if a.mode in ("search_keyword", "search_users", "top_search"):
            p["queries"] = a.q
        if a.mode == "search_hashtag":
            p["hashtags"] = a.q
        if a.mode == "song_intel":
            p["songUrls"] = a.q
        rows = a.max * max(1, len(a.q or [1]))
    elif a.door == "shop":
        p = {"mode": a.mode, "region": a.region, "maxResults": a.max}
        p.update({"shop_search": {"searchKeywords": a.q}, "shop_catalog": {"shopUrls": a.q},
                  "product_details": {"productUrls": a.q}, "product_reviews": {"productUrls": a.q},
                  "creator_showcase": {"usernames": a.q}}[a.mode])
        rows = a.max * max(1, len(a.q or [1]))
    elif a.door == "creator":
        p = {"profiles": a.q, "max_items_per_profile": a.max, "sort_by": a.sort,
             "include_transcript": a.transcripts, "transcript_use_ai_fallback": False, "region": a.region}
        rows = a.max * len(a.q)
    else:
        p = {"clips": a.q, "max_video_pages": a.pages, "include_song_details": True}
        rows = len(a.q) * (1 + 30 * a.pages)   # a page of videos is ~30 rows
    return p, rows


def run(actor, p, cap, timeout=600):
    """Run-sync, capped at `cap` dollars by Apify itself."""
    def call(tok):
        url = (f"{A.API}/acts/{actor}/run-sync-get-dataset-items?token={tok}"
               f"&timeout={timeout}&maxTotalChargeUsd={cap}")
        req = urllib.request.Request(url, data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout + 60) as r:
            return json.loads(r.read() or b"[]")
    return A.each_account(call)


SEARCH_MODES = ("search_keyword", "search_hashtag", "top_search")


def research_gate(a):
    """A paid search runs only from a research round whose plan passed the coverage gate and was approved
    (owner, 2026-10-17: a hand-made fight list skipped an avatar's biggest world; components/swipe-organic/
    RESEARCH-ROUND.md). The round sets RESEARCH_ROUND_PLAN; a dry run never spends, so it is let through."""
    if a.door != "trends" or a.mode not in SEARCH_MODES or a.dry_run:
        return
    f = os.environ.get("RESEARCH_ROUND_PLAN")
    try:
        p = json.loads(Path(f).read_text()) if f else None
    except (OSError, ValueError):
        p = None
    if not p:
        sys.exit("REFUSED: a paid search runs through the research round — "
                 "components/swipe-organic/round.py (worlds → plan → pull), see RESEARCH-ROUND.md")
    if p.get("state") != "ready" or not (p.get("approved") or {}).get("by"):
        sys.exit("REFUSED: the round's plan is held or not approved — run round.py plan, then pull --approved-by")
    if sorted(p.get("searches") or []) != sorted(a.q or []):
        sys.exit("REFUSED: these searches are not the approved plan's searches")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("door", choices=list(DOORS))
    ap.add_argument("--mode", default=None)
    ap.add_argument("--q", "--profiles", "--clips", "--user", dest="q", nargs="*", default=[],
                    help="search words, hashtags, URLs, handles or sound ids — whatever the mode takes")
    ap.add_argument("--region", default="US")
    ap.add_argument("--max", type=int, default=30, help="rows per query / profile")
    ap.add_argument("--pages", type=int, default=1, help="sound: pages of videos per sound")
    ap.add_argument("--sort", default="latest", choices=["latest", "popular"])
    ap.add_argument("--transcripts", action="store_true")
    ap.add_argument("--out", required=True, help="the caller's folder; rows.json + run.json go here")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.door == "trends":
        a.mode = a.mode or "popular_hashtags"
        if a.mode not in TRENDS_MODES:
            sys.exit(f"trends --mode is one of: {', '.join(TRENDS_MODES)}")
    if a.door == "shop":
        a.mode = a.mode or "shop_search"
        if a.mode not in SHOP_MODES:
            sys.exit(f"shop --mode is one of: {', '.join(SHOP_MODES)}")
    if a.door in ("creator", "sound") and not a.q:
        sys.exit(f"{a.door} needs --q (handles or sound ids)")
    research_gate(a)
    actor, price = DOORS[a.door]
    p, rows = payload(a)
    cap = round(rows * price + (rows * 0.01 if a.transcripts else 0) + 0.01, 2)
    print(f"{a.door}: {actor} · up to {rows} rows · at most ${cap}")
    print(f"  input: {json.dumps(p)}")
    if a.dry_run:
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec = {"at": at, "door": a.door, "actor": actor, "input": p, "cap_usd": cap}
    try:
        items = run(actor, p, cap)
        rec.update(rows=len(items), status="done")
    except urllib.error.HTTPError as e:
        items = []
        rec.update(rows=0, status="failed", error=f"{e.code}: {e.read()[:200].decode(errors='ignore')}")
    except urllib.error.URLError as e:          # no HTTP answer at all: DNS, refused, timeout
        items = []
        rec.update(rows=0, status="failed", error=f"no answer: {str(e.reason)[:200]}")
    (out / "rows.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (out / "run.json").write_text(json.dumps(rec, indent=1))
    print(f"  {rec['status']}: {rec['rows']} rows → {out}/rows.json" + (f" · {rec.get('error')}" if rec.get("error") else ""))
    # A failed run still leaves its artifacts above, then says so with its exit code.
    if rec["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
