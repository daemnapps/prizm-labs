#!/usr/bin/env python3
"""His saves, as a feed on My Feeds.

The saves catalog (records/damon-saves/) is his taste already applied — the
highest-signal intake the system has — and until now it was only readable on
the old Swipe Studio board. My Feeds is THE board (his ruling, 2026-09-19),
so the catalog is projected into the feed store like any other feed and shows
up beside the avatar feeds as **damon · my saves**.

    python3 saves_feed.py [--dry-run]

Free: no model, no network. Reads the catalog, writes the feed store.
Idempotent — run it after every sweep, it rebuilds the feed in place.

Note the other feed: `damon--saves` is NOT this. That one is *dug* from the
creators he saves two or more times — a room built out of his taste. This one
is the saves themselves.
"""
import argparse, json, shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAVES = HERE / "records/damon-saves"
FEED = HERE / "records/avatar-feeds/damon--my-saves"
FEED_ID = "damon--my-saves"


def build(dry=False):
    rows = json.loads((SAVES / "catalog.json").read_text())["rows"]
    items, obs = {}, []
    for r in rows:
        code = r["url"].rstrip("/").split("/")[-1]
        key = f"instagram:{code}"
        seen = f"{r.get('scraped') or '2026-08-29'}T00:00:00+00:00"
        items[key] = {
            "platform": "instagram", "id": code, "url": r["url"],
            "author": r.get("author") or "", "posted": None,
            "caption": r.get("caption") or "", "hashtags": r.get("hashtags") or [],
            "cover": None, "kind": r.get("kind"),
            "source": "damon's saved folder",
            "receipt": f"saved on instagram.com/daemn.is/saved — {r.get('note') or 'first capture'}",
            "first_seen": seen,
            # his read, carried across so the page can search and filter on it
            "category": r.get("category"), "brand_fit": r.get("brand_fit"),
            "swipe_lane": r.get("lane"), "status": r.get("status"),
            # no sift: nothing here was judged by a model. He saved it — it stays.
            "sift": {"keep": True, "lane": None, "kind": r.get("kind"),
                     "what": r.get("category"), "format": None,
                     "why": f"he saved it · {r.get('lane') or '?'} · {r.get('brand_fit') or '?'}"},
        }
        obs.append({"item": key, "at": seen, "views": r.get("views") or 0,
                    "likes": r.get("likes") or 0, "comments": r.get("comments") or 0})
    if dry:
        print(f"{len(items)} saves would be projected into {FEED_ID}")
        return
    FEED.mkdir(parents=True, exist_ok=True)
    (FEED / "sources.json").write_text(json.dumps({
        "feed": FEED_ID, "title": "damon · my saves",
        "ask": "Everything I saved on Instagram, newest sweep first.",
        "whose": "damon", "brand": "damon",
        "note": "Not dug — projected from the saves catalog by saves_feed.py. "
                "A new sweep of the saved folder needs his own Chrome; this "
                "rebuild only re-reads what the sweep already filed.",
        "pull": "saves",
        "sources": [{"platform": "instagram", "kind": "saved-folder",
                     "value": "daemn.is/saved/all-posts",
                     "receipt": "his own saved folder, swept in his logged-in Chrome"}],
    }, indent=1) + "\n")
    (FEED / "items.json").write_text(json.dumps({"items": items}, indent=1) + "\n")
    (FEED / "observations.jsonl").write_text(
        "".join(json.dumps(o) + "\n" for o in obs))
    sweep = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "sources": 1, "observed": len(items), "new": len(items),
             "catalog": len(items), "errors": [], "by_source": {"saved-folder": {"returned": len(items)}}}
    with (FEED / "sweeps.jsonl").open("a") as f:
        f.write(json.dumps(sweep) + "\n")
    cov = FEED / "covers"
    cov.mkdir(exist_ok=True)
    n = 0
    for r in rows:
        cf = r.get("cover_file")
        if not cf:
            continue
        src, dest = SAVES / "covers" / cf, cov / cf
        if src.exists() and not dest.exists():
            shutil.copy2(src, dest)
            n += 1
    print(f"{len(items)} saves → {FEED_ID} ({n} covers copied, {len(list(cov.glob('*.jpg')))} on the feed)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    build(ap.parse_args().dry_run)
