#!/usr/bin/env python3
"""the owner's saved posts — the human-taste intake stream.

He curates by saving on Instagram, exactly as he always has. A sweep
(via his own logged-in Chrome) drops the URLs into records/damon-saves/captured-urls.json;
this scrapes each post publicly and writes one intake row per save with
its receipts. Grading (bucket: viral | novel-format | market-opportunity,
awareness grade, route) is a judgment layer on top — the session proposes,
the owner overrides.

    python3 saves.py [--inbox records/damon-saves/captured-urls.json] [--dry-run]
"""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import apify as A

HERE = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", default="records/damon-saves/captured-urls.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    urls = json.loads((HERE / args.inbox).read_text())
    print(f"{len(urls)} saved posts in the inbox")
    if args.dry_run:
        return
    items = A.run(A.POSTS_IG, {"directUrls": urls, "resultsType": "posts",
                               "addParentData": True})
    posts = [A.as_post(i, "instagram") for i in items if i.get("shortCode")]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = HERE / "records/damon-saves/catalog.json"
    prior = json.loads(out.read_text()) if out.exists() else {"rows": []}
    seen = {r["url"] for r in prior["rows"]}
    added = 0
    for p in posts:
        if p["url"] in seen:
            continue
        prior["rows"].append({
            "url": p["url"], "author": p["author"], "scraped": now,
            "views": p.get("views"), "likes": p.get("likes"),
            "comments": p.get("comments"),
            "caption": (p.get("caption") or "")[:400],
            "hashtags": p.get("hashtags") or [],
            "sound": p.get("music"),
            "bucket": None, "grade": None, "route": None,
            "note": None, "status": "fresh"})
        added += 1
    out.write_text(json.dumps(prior, indent=1) + "\n")
    print(f"{added} new rows -> {out.relative_to(HERE)} "
          f"({len(prior['rows'])} total; grading is a separate judgment pass)")

if __name__ == "__main__":
    main()
