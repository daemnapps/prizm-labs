#!/usr/bin/env python3
"""The avatar feed backend — how a social feed is actually built.

One folder per avatar feed, three layers:

    records/avatar-feeds/<brand>--<avatar>/
      sources.json        what we pull and WHY — every source has a receipt
      items.json          the CATALOG: one record per post ever seen, with
                          the post's own publish date (relevance), who made
                          it, which source found it, and when we first saw it
      observations.jsonl  append-only HISTORY: every sweep writes one line
                          per item observed (views/likes at that moment) —
                          a post's growth is the difference between lines
      sweeps.jsonl        the run log: when each sweep ran, what it pulled,
                          what failed. The feed's own memory.

    python3 feed.py --avatar brand-b--avatar-two [--per 10] [--dry-run]

Organic only: declared ads never enter. Host-agnostic: needs only
APIFY_TOKEN (env var or local keys file). Scheduling is a deployment
choice on top — cloud routine, any machine — never baked in here.
Frontends read this store; they never own data.
"""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import apify as A

HERE = Path(__file__).resolve().parent

def tiktok_posted(post_id):
    # a TikTok id's top 32 bits are the unix timestamp it was posted
    try:
        ts = int(post_id) >> 32
        if 1_300_000_000 < ts < 4_000_000_000:
            return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        pass
    return None

AD_MARKERS = ("#ad", "#sponsored", "paid partnership", "#tiktokshop", "link in bio to buy")
QUARANTINE = "no receipt (SI-159 (organic pool honest))"

def quarantine_unreceipted(items):
    """Mark every row filed with no receipt (SI-159 (organic pool honest)):
    the row stays, it is never re-pulled, and it says why it is not trusted.
    A row already quarantined is left as it is. Returns how many it marked."""
    n = 0
    for rec in items.values():
        if rec.get("receipt") or rec.get("quarantine"):
            continue
        rec["receipt"] = ""
        rec["quarantine"] = QUARANTINE
        n += 1
    return n

def origin(src, values, p):
    """The one source value a post came from, or None. A batch call returns
    posts for many values under one label, so the value is read off the post
    itself (SI-159 (organic pool honest))."""
    batch, _, one = src.partition("=")
    if one:
        return one                                # a per-value call: the label names it
    vals = values or []
    if batch.endswith("-accounts"):
        who = (p.get("author") or "").lstrip("@").lower()
        return next((v for v in vals if v.lstrip("@").lower() == who), None) if who else None
    if "hashtag" in batch:
        tags = {(h or "").lstrip("#").lower() for h in p.get("hashtags") or []}
        return next((v for v in vals if v.lstrip("#").lower() in tags), None)
    if batch.endswith("-search"):
        return vals[0] if len(vals) == 1 else None   # many terms: which one found it is unknown
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--per", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quarantine-unreceipted", action="store_true",
                    help="mark this feed's rows that carry no receipt; no pull")
    args = ap.parse_args()
    root = HERE / "records/avatar-feeds" / args.avatar
    items_f, obs_f, log_f = root / "items.json", root / "observations.jsonl", root / "sweeps.jsonl"
    if args.quarantine_unreceipted:
        if not items_f.exists():
            print(f"{args.avatar}: no items.json — nothing to mark")
            return
        catalog = json.loads(items_f.read_text())
        n = quarantine_unreceipted(catalog["items"])
        items_f.write_text(json.dumps(catalog, indent=1) + "\n")
        print(f"{args.avatar}: quarantined {n} of {len(catalog['items'])} rows with no receipt")
        return
    S = json.loads((root / "sources.json").read_text())
    catalog = json.loads(items_f.read_text()) if items_f.exists() else {"items": {}}
    items = catalog["items"]

    def pick(kind, plat):
        return [s["value"] for s in S["sources"] if s["kind"] == kind and s["platform"] == plat]
    receipt = {s["value"]: s["receipt"] for s in S["sources"]}
    tt_tags, tt_accts = pick("hashtag", "tiktok"), pick("account", "tiktok")
    ig_tags, yt_terms = pick("hashtag", "instagram"), pick("search", "youtube")
    ig_accts = pick("account", "instagram")
    tt_search = pick("search", "tiktok")      # plain-word searches (asked feeds)
    print(f"{args.avatar}: tt {len(tt_tags)}+{len(tt_accts)}+{len(tt_search)}s · ig {len(ig_tags)} · yt {len(yt_terms)} · {args.per}/source")
    if args.dry_run:
        return

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_ids, observed, errors = [], 0, []
    E = S.get("entry", {})
    max_age = E.get("max_age_days")
    def too_old(posted):
        if not (max_age and posted):
            return False
        try:
            d = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            if not d.tzinfo:
                d = d.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - d).days > max_age
        except ValueError:
            return False

    by_source = {}
    def take(raw, src, platform, values=None):
        nonlocal observed
        tally = by_source.setdefault(src, {"returned": 0, "new": 0, "ad": 0, "too_old": 0, "too_small": 0,
                                           "no_receipt": 0})
        tally["returned"] += len(raw)
        with obs_f.open("a") as OB:
            for it in raw:
                p = A.as_post(it, platform)
                if not p.get("id"):
                    continue
                cap = (p.get("caption") or "").lower()
                if any(m in cap for m in AD_MARKERS):
                    tally["ad"] += 1
                    continue                      # organic only
                key = f'{p["platform"]}:{p["id"]}'
                if key in items:
                    # backfill details a fresh pull carries that the record lacks
                    rec = items[key]
                    for f_src, f_dst in (("posted","posted"),("cover","cover"),("author","author")):
                        if not rec.get(f_dst) and p.get(f_src):
                            rec[f_dst] = p[f_src]
                    if p.get("cover"):
                        rec["cover"] = p["cover"]   # thumbnail links expire — keep the live one
                    if p.get("author_followers") and not rec.get("followers"):
                        rec["followers"] = p["author_followers"]
                    if not rec.get("caption") and p.get("caption"):
                        rec["caption"] = p["caption"][:300]
                if key not in items:
                    posted = p.get("posted") or (tiktok_posted(p["id"]) if p["platform"] == "tiktok" else None)
                    if too_old(posted):
                        tally["too_old"] += 1
                        continue                  # entry rule: nothing older than max_age
                    if src.split("=")[0] not in ("tt-accounts", "ig-accounts"):
                        # hashtag/search finds must clear one signal floor
                        v, l = p.get("views") or 0, p.get("likes") or 0
                        if v < E.get("hashtag_min_views", 0) and l < E.get("hashtag_min_likes", 0):
                            tally["too_small"] += 1
                            continue
                    value = origin(src, values, p)
                    if not (value and receipt.get(value)):
                        tally["no_receipt"] += 1
                        continue                  # every row carries its receipt, or is not written
                    items[key] = {
                        "platform": p["platform"], "id": p["id"], "url": p["url"],
                        "author": p["author"], "followers": p.get("author_followers"),
                        "posted": posted,
                        "caption": (p.get("caption") or "")[:300],
                        "hashtags": p.get("hashtags") or [],
                        "cover": p.get("cover"), "kind": p.get("kind"),
                        "source": f'{src.partition("=")[0]}={value}', "receipt": receipt[value],
                        "first_seen": now, "category": None, "status": "fresh"}
                    new_ids.append(key)
                    tally["new"] += 1
                OB.write(json.dumps({"item": key, "at": now,
                                     "views": p.get("views"), "likes": p.get("likes"),
                                     "comments": p.get("comments"),
                                     "shares": p.get("shares"), "saves": p.get("saves")}) + "\n")
                observed += 1

    if tt_tags:
        try:
            take(A.run(A.POSTS_TT, {"hashtags": tt_tags, "resultsPerPage": args.per}), "tt-hashtags", "tiktok", tt_tags)
        except Exception as e:
            errors.append(f"tt-hashtags: {str(e)[:70]}")
    if tt_search:
        try:
            take(A.run(A.POSTS_TT, {"searchQueries": tt_search, "resultsPerPage": args.per,
                                    "searchSection": "/video", "shouldDownloadVideos": False}),
                 "tt-search", "tiktok", tt_search)
        except Exception as e:
            errors.append(f"tt-search: {str(e)[:70]}")
    if tt_accts:
        try:
            take(A.run(A.POSTS_TT, {"profiles": tt_accts, "resultsPerPage": args.per,
                                    "shouldDownloadVideos": False}), "tt-accounts", "tiktok", tt_accts)
        except Exception as e:
            errors.append(f"tt-accounts: {str(e)[:70]}")
    for tag in ig_tags:
        try:
            # "reels" returns the hashtag's TOP reels with real play counts; the default
            # returns whatever was posted in the last hour (found 2026-09-19: 20 of 20 had 0 views)
            take(A.run(A.POSTS_IG_TAG, {"hashtags": [tag], "resultsLimit": args.per,
                                        "resultsType": "reels"}),
                 f"ig-hashtag={tag}", "instagram", [tag])
        except Exception as e:
            errors.append(f"ig {tag}: {str(e)[:70]}")
    if ig_accts:
        try:
            take(A.run(A.POSTS_IG, {"directUrls": [f"https://www.instagram.com/{h}/" for h in ig_accts],
                                    "resultsType": "posts", "resultsLimit": args.per}), "ig-accounts", "instagram", ig_accts)
        except Exception as e:
            errors.append(f"ig-accounts: {str(e)[:70]}")
    if yt_terms:
        try:
            take(A.run(A.POSTS_YT, {"searchQueries": yt_terms, "maxResults": args.per,
                                    "maxResultsShorts": args.per, "maxResultStreams": 0}), "yt-search", "youtube", yt_terms)
        except Exception as e:
            errors.append(f"yt: {str(e)[:70]}")

    items_f.write_text(json.dumps(catalog, indent=1) + "\n")
    with log_f.open("a") as L:
        L.write(json.dumps({"at": now, "sources": len(S["sources"]), "observed": observed,
                            "new": len(new_ids), "catalog": len(items), "errors": errors,
                            "by_source": by_source}) + "\n")
    print(f"observed {observed} · new {len(new_ids)} · catalog {len(items)}"
          + (f" · errors {errors}" if errors else ""))
    import feedpage
    feedpage.build(args.avatar)   # the page rebuilds itself after every sweep

if __name__ == "__main__":
    main()
