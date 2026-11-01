"""social_pull.py: pull a brand's own social posts (Instagram, TikTok, Facebook) into its proof folder.

the owner, 2026-10-09: "pull it" (the brand's live accounts, about $6 on Apify).

    python3 machine/social_pull.py --brand <brand> --ig <handle> --tt <h1,h2> --fb <page>
                                   [--ig-limit 500] [--tt-limit 200] [--fb-limit 200] [--label live-YYYY-MM-DD]

Handles come from the caller (for a brand, its channels/own-accounts.json); nothing here names
a brand. APIFY_TOKEN by name from the environment. Each post's media is written beside its
details file on the Shared Assets drive under brands/<brand>/intake/organic/<label>/<platform>/,
named <IG|TT|FB>_<post|reel|video>_<handle>_<YYYY-MM-DD>_<id>.<ext>, which proof.py index reads
as a social post. The raw results land at runs/asset-index/<brand>/social/<label>/.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shared_paths as SP  # noqa: E402

API = "https://api.apify.com/v2"
ACTORS = {"ig": "apify~instagram-scraper", "tt": "clockworks~tiktok-scraper", "fb": "apify~facebook-posts-scraper"}


def _req(url, body=None, tok=None, timeout=120):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "token=" + tok, data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run_actor(key, payload, tok, say):
    run = _req("%s/acts/%s/runs" % (API, ACTORS[key]), payload, tok)["data"]
    rid, ds = run["id"], run["defaultDatasetId"]
    say("%s: started run %s" % (key, rid))
    while True:
        time.sleep(15)
        st = _req("%s/actor-runs/%s" % (API, rid), tok=tok)["data"]
        if st["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    items = _req("%s/datasets/%s/items?clean=true&format=json" % (API, ds), tok=tok, timeout=600)
    cost = (st.get("usageTotalUsd") or 0)
    say("%s: %s, %d posts, $%.2f" % (key, st["status"], len(items), cost))
    return items, cost


def _day(v):
    if not v:
        return "undated"
    if isinstance(v, (int, float)):
        return datetime.datetime.utcfromtimestamp(v if v < 1e12 else v / 1000).strftime("%Y-%m-%d")
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v))
    return m.group(1) if m else "undated"


def media_of(key, it):
    """(kind, handle, day, id, [urls]) for one post."""
    if key == "ig":
        urls = [it.get("videoUrl")] if it.get("videoUrl") else ([c.get("displayUrl") for c in it.get("childPosts") or [] if c.get("displayUrl")] or [it.get("displayUrl")])
        kind = "reel" if it.get("type") == "Video" else ("carousel" if it.get("childPosts") else "post")
        return kind, it.get("ownerUsername") or "", _day(it.get("timestamp")), str(it.get("shortCode") or it.get("id")), [u for u in urls if u]
    if key == "tt":
        a = it.get("authorMeta") or {}
        urls = list(it.get("mediaUrls") or [])
        if not urls and (it.get("videoMeta") or {}).get("downloadAddr"):
            urls = [it["videoMeta"]["downloadAddr"]]
        cover = (it.get("videoMeta") or {}).get("coverUrl")
        return "video", a.get("name") or a.get("nickName") or "", _day(it.get("createTimeISO") or it.get("createTime")), str(it.get("id")), urls + ([cover] if cover else [])
    urls = [m.get("photo_image", {}).get("uri") or m.get("thumbnail") or m.get("url") for m in it.get("media") or []]
    return "post", it.get("pageName") or (it.get("user") or {}).get("name") or "", _day(it.get("time") or it.get("timestamp")), str(it.get("postId") or it.get("id")), [u for u in urls if u]


def save_post(key, it, dest):
    kind, handle, day, pid, urls = media_of(key, it)
    tag = {"ig": "IG", "tt": "TT", "fb": "FB"}[key]
    stem = "%s_%s_%s_%s_%s" % (tag, kind, re.sub(r"[^A-Za-z0-9._-]", "", handle) or "unknown", day, re.sub(r"[^A-Za-z0-9]", "", pid)[:24])
    got = []
    for i, u in enumerate(urls):
        ext = ".mp4" if (key == "tt" and i == 0 and "cover" not in u) or ".mp4" in u.split("?")[0] else ".jpg"
        name = stem + ("" if i == 0 else "-%d" % i) + ext
        out = dest / name
        if out.exists():
            got.append(name); continue
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=180) as r:
                out.write_bytes(r.read())
            got.append(name)
        except Exception:
            pass
    (dest / (stem + ".json")).write_text(json.dumps(it, indent=1, default=str))
    return len(got)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--ig", default=""); ap.add_argument("--tt", default=""); ap.add_argument("--fb", default="")
    ap.add_argument("--ig-limit", type=int, default=500); ap.add_argument("--tt-limit", type=int, default=200); ap.add_argument("--fb-limit", type=int, default=200)
    ap.add_argument("--label", default="live-" + datetime.date.today().isoformat())
    o = ap.parse_args()
    tok = os.environ.get("APIFY_TOKEN")
    if not tok:
        raise SystemExit("APIFY_TOKEN is not in the environment")
    say = lambda m: print(m, flush=True)  # noqa: E731
    jobs = {}
    if o.ig:
        jobs["ig"] = {"directUrls": ["https://www.instagram.com/%s/" % h for h in o.ig.split(",")], "resultsType": "posts", "resultsLimit": o.ig_limit, "addParentData": False}
    if o.tt:
        jobs["tt"] = {"profiles": o.tt.split(","), "resultsPerPage": o.tt_limit, "shouldDownloadVideos": True, "shouldDownloadCovers": True,
                      "profileScrapeSections": ["videos"], "profileSorting": "latest"}
    if o.fb:
        jobs["fb"] = {"startUrls": [{"url": "https://www.facebook.com/%s" % h} for h in o.fb.split(",")], "resultsLimit": o.fb_limit}
    raw = SP.runs_root() / o.brand / "social" / o.label; raw.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(3) as ex:
        res = dict(zip(jobs, ex.map(lambda k: run_actor(k, jobs[k], tok, say), jobs)))
    total = 0.0
    for key, (items, cost) in res.items():
        total += cost
        (raw / (key + ".json")).write_text(json.dumps(items, indent=1, default=str))
        dest = SP.brand_root(o.brand) / "intake" / "organic" / o.label / {"ig": "instagram", "tt": "tiktok", "fb": "facebook"}[key]
        dest.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(8) as ex:
            n = sum(ex.map(lambda it: save_post(key, it, dest), items))
        say("%s: %d media files saved to %s" % (key, n, dest))
    (raw / "summary.json").write_text(json.dumps({k: len(v[0]) for k, v in res.items()} | {"usd": round(total, 2)} if sys.version_info >= (3, 9) else {}, indent=1))
    say("done: $%.2f" % total)


if __name__ == "__main__":
    main()
