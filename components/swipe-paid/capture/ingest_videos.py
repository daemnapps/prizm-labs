#!/usr/bin/env python3
"""Ingest apidojo/tiktok-scraper items into market.db.

Usage:
  python3 ingest_videos.py items.json --niche "sleep-earbuds" \
      --source "apidojo/tiktok-scraper" --query '{"keywords":...}' \
      --region US [--apify-run ID] [--dataset ID] [--cost 0.009] \
      [--purpose validation] [--notes "..."]

Every ingest writes a scan_runs row first (methodology transparency), then
upserts videos with derived metrics:
  posted_at_derived  — snowflake video id >> 32 (unix secs); ranking primitive
  timestamp_drift_s  — |reported - derived|; drift > 60s gets flagged
  velocity           — views / hours since derived post time
  engagement_rate, discussion_density, reach_surprise
"""
import argparse, json, sqlite3, sys, time
from datetime import datetime, timezone
import adplexity_client  # same folder: _db() makes scan_runs on a fresh clone

DB = __file__.rsplit("/", 1)[0] + "/market.db"

def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items_file")
    ap.add_argument("--niche", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--apify-run", default=None)
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--cost", type=float, default=None)
    ap.add_argument("--purpose", default="discovery")
    ap.add_argument("--notes", default=None)
    a = ap.parse_args()

    items = json.load(open(a.items_file))
    now = time.time()
    con = adplexity_client._db(DB)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO scan_runs (ran_at, source, query_json, region, items_returned,"
        " cost_usd, apify_run_id, dataset_id, purpose, notes)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (iso(now), a.source, a.query, a.region, len(items), a.cost,
         a.apify_run, a.dataset, a.purpose, a.notes))
    run_id = cur.lastrowid

    seen, dupes, flagged = set(), 0, 0
    for it in items:
        vid = str(it["id"])
        if vid in seen:
            dupes += 1
            continue
        seen.add(vid)
        derived = int(vid) >> 32
        reported = it.get("uploadedAt")
        drift = abs(reported - derived) if reported else None
        if drift is not None and drift > 60:
            flagged += 1
        views = it.get("views") or 0
        likes = it.get("likes") or 0
        comments = it.get("comments") or 0
        shares = it.get("shares") or 0
        bookmarks = it.get("bookmarks") or 0
        followers = it.get("channel.followers") or it.get("channel", {}).get("followers") or 0
        hours = max((now - derived) / 3600.0, 0.1)
        cur.execute(
            """INSERT INTO videos (video_id, niche, author_handle, author_followers,
                 caption, url, posted_at_reported, posted_at_derived, timestamp_drift_s,
                 play_count, digg_count, comment_count, share_count, collect_count,
                 velocity, engagement_rate, discussion_density, reach_surprise,
                 region, first_seen_run, last_seen_run)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(video_id) DO UPDATE SET
                 play_count=excluded.play_count, digg_count=excluded.digg_count,
                 comment_count=excluded.comment_count, share_count=excluded.share_count,
                 collect_count=excluded.collect_count, velocity=excluded.velocity,
                 engagement_rate=excluded.engagement_rate,
                 discussion_density=excluded.discussion_density,
                 reach_surprise=excluded.reach_surprise,
                 last_seen_run=excluded.last_seen_run""",
            (vid, a.niche,
             it.get("channel.username") or it.get("channel", {}).get("username"),
             followers, it.get("title"), it.get("postPage"),
             iso(reported) if reported else None, iso(derived), drift,
             views, likes, comments, shares, bookmarks,
             round(views / hours, 2),
             round((likes + comments + shares + bookmarks) / views, 4) if views else None,
             round(comments / views, 4) if views else None,
             round(views / followers, 2) if followers else None,
             a.region, run_id, run_id))
    con.commit()
    print(f"run_id={run_id} ingested={len(seen)} dupes_skipped={dupes} drift_flagged={flagged}")

if __name__ == "__main__":
    main()
