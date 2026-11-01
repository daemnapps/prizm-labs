#!/usr/bin/env python3
"""Ingest apidojo/tiktok-comments-scraper output (JSONL) into market.db.

Usage:
  python3 ingest_comments.py comments.jsonl --source "apidojo/tiktok-comments-scraper" \
      --query '{"startUrls":[...]}' --region US [--apify-run ID] [--dataset ID] \
      [--cost 0.05] [--purpose listening] [--notes "..."]

Writes a scan_runs row, then comments (PII posture: commenter handle stored
only as sha256 hash + region). Completeness check: per video, compares
ingested top-level comments against videos.comment_count and prints the
ratio — TikTok's failure mode is silent truncation, so this check is the
guardrail that makes longitudinal claims trustworthy.
"""
import argparse, hashlib, json, sqlite3, sys, time
from datetime import datetime, timezone
import adplexity_client  # same folder: _db() makes scan_runs on a fresh clone

DB = __file__.rsplit("/", 1)[0] + "/market.db"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl_file")
    ap.add_argument("--source", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--apify-run", default=None)
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--cost", type=float, default=None)
    ap.add_argument("--purpose", default="listening")
    ap.add_argument("--notes", default=None)
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.jsonl_file) if l.strip()]
    now = datetime.now(timezone.utc).isoformat()
    con = adplexity_client._db(DB)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO scan_runs (ran_at, source, query_json, region, items_returned,"
        " cost_usd, apify_run_id, dataset_id, purpose, notes)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (now, a.source, a.query, a.region, len(rows), a.cost,
         a.apify_run, a.dataset, a.purpose, a.notes))
    run_id = cur.lastrowid

    per_video = {}
    for r in rows:
        vid = str(r["awemeId"])
        is_reply = bool(r.get("parentId"))
        if not is_reply:
            per_video[vid] = per_video.get(vid, 0) + 1
        cur.execute(
            """INSERT OR IGNORE INTO comments
               (cid, video_id, text, likes, created_at, lang, commenter_hash, run_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (str(r["id"]), vid, r.get("text"), r.get("likeCount", 0),
             r.get("createdAt"), r.get("lang"),
             hashlib.sha256((r.get("user") or "").encode()).hexdigest()[:16] +
             ":" + (r.get("region") or "??"),
             run_id))

    print(f"run_id={run_id} comments_ingested={len(rows)}")
    print("completeness (top-level returned / video's own comment_count):")
    worst = 1.0
    for vid, n in per_video.items():
        row = cur.execute(
            "SELECT comment_count, author_handle FROM videos WHERE video_id=?",
            (vid,)).fetchone()
        if row and row[0]:
            ratio = n / row[0]
            worst = min(worst, ratio)
            flag = "  ⚠ LOW" if ratio < 0.8 else ""
            print(f"  @{row[1]}: {n}/{row[0]} = {ratio:.0%}{flag}")
    cur.execute("UPDATE scan_runs SET completeness_ratio=? WHERE run_id=?",
                (round(worst, 3), run_id))
    con.commit()

if __name__ == "__main__":
    main()
