#!/usr/bin/env python3
"""A Content Rewards campaign report -> our results snapshot + every clip in the swipe library.

    python3 content_rewards.py <report share link> --brand <brand> --pool <name>
    python3 content_rewards.py <report share link> --brand <brand> --pool <name> --no-media   numbers only

the owner, 2026-10-24, on the clipping campaign the partner runs for us: "digest all these assets ... download them ...
tracking their results internally". The report's share link is public; its own data feed (the one the report
page reads) gives every clip: the post link, views, likes, comments, shares, spend and the slide images.

Writes, per run:
  runs/content-rewards/<brand>/<pool>/<YYYY-MM-DD>/clips.json   every clip as the report has it today
  runs/content-rewards/<brand>/<pool>/<YYYY-MM-DD>/summary.md   totals, top clips, top accounts
and files each clip into the organic swipe pool `<pool>` through the save door (add.py: media, Drive, row),
lane own-campaign (source organic, owner creator), with all its slides kept beside the cover in the library.
Run it again any day: a new dated snapshot, and only clips not yet in the pool are downloaded.

`--deep` (the owner's go, 24 Oct 2026, ~$12 of Apify): every comment on every clip, then every commenter's profile
and last 10 posts, into `deep/` beside the snapshot (comments.json, commenters.json, commenter-posts.json) —
the raw material for the language index and the avatar profile of who actually engages.
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit.paths import repo  # noqa: E402


def _door():
    """The save door, loaded only when slides are filed: it reaches the Drive the moment it loads, and the
    numbers and comments need no Drive at all."""
    import add
    return add

UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def report(link):
    """Every clip in the report, newest numbers."""
    tok = link.rstrip("/").rsplit("/", 1)[-1]
    base = f"https://contentrewards.com/api/share/report/{tok}"
    now = datetime.now(timezone.utc)
    q = {"start": "2020-01-01T00:00:00.000Z", "end": now.strftime("%Y-%m-%dT23:59:59.000Z"),
         "platforms": "facebook,instagram,tiktok,x,youtube", "asOf": now.strftime("%Y-%m-%dT%H:%M:00.000Z")}
    rows, off = [], 0
    while True:
        page = json.loads(get(f"{base}/rows?" + urllib.parse.urlencode(dict(q, direction="desc", limit=100, offset=off, sortBy="views"))))
        got = (page.get("data") or {}).get("rows") or []
        rows += got
        if len(got) < 100:
            break
        off += 100
    accounts = json.loads(get(f"{base}/accounts?" + urllib.parse.urlencode(q))).get("data")
    return rows, accounts


def num(x):
    try:
        return int(float(x or 0))
    except (TypeError, ValueError):
        return 0


def summary(rows, name):
    v = sum(num(r.get("lifetimeViews")) for r in rows)
    spend = sum(num(r.get("spend")) for r in rows) / 100
    acc = {}
    for r in rows:
        h = (r.get("postingAccount") or {}).get("handle") or "?"
        a = acc.setdefault(h, {"posts": 0, "views": 0, "spend": 0})
        a["posts"] += 1; a["views"] += num(r.get("lifetimeViews")); a["spend"] += num(r.get("spend")) / 100
    top = sorted(rows, key=lambda r: -num(r.get("lifetimeViews")))[:10]
    out = [f"# {name.strip()} — {date.today()}", "",
           f"{len(rows)} clips · {v:,} views · ${spend:,.2f} spent · ${(spend / v * 1000) if v else 0:.2f} per 1,000 views", "",
           "## Top clips", "", "| Views | Likes | Shares | Spend | Account | Kind | Post |", "|---|---|---|---|---|---|---|"]
    out += [f"| {num(r.get('lifetimeViews')):,} | {num(r.get('likes')):,} | {num(r.get('shares')):,} | ${num(r.get('spend')) / 100:,.2f} | "
            f"@{(r.get('postingAccount') or {}).get('handle', '?')} | {'slideshow' if r.get('slides') else 'video'} | {r.get('postUrl')} |" for r in top]
    out += ["", "## Accounts", "", "| Account | Posts | Views | Spend |", "|---|---|---|---|"]
    out += [f"| @{h} | {a['posts']} | {a['views']:,} | ${a['spend']:,.2f} |" for h, a in sorted(acc.items(), key=lambda x: -x[1]["views"])]
    return "\n".join(out) + "\n"


def file_media(rows, brand, pool, work):
    """Each clip into the pool: the cover through the save door, every slide kept beside it."""
    A = _door()
    have = {p.get("id") for p in (json.loads(A.pool_file(pool).read_text()).get("posts", []) if A.pool_file(pool).is_file() else [])}
    todo = []
    for r in rows:
        code = (re.search(r"/(\d{15,})", r.get("postUrl") or "") or [None, None])[1]
        if not code or code in have:
            continue
        slides = r.get("slides") or []
        if not slides:
            continue                                   # a video clip: its file is not in the feed; left for the video pull
        lib = A.LIB / code / "slides"
        lib.mkdir(parents=True, exist_ok=True)
        for i, u in enumerate(slides, 1):
            f = lib / f"slide-{i:02d}.jpg"
            if not f.exists():
                f.write_bytes(get(u))
        work.mkdir(parents=True, exist_ok=True)
        cover = work / f"{code}.jpg"
        cover.write_bytes((lib / "slide-01.jpg").read_bytes())
        todo.append(str(cover))
    if todo:
        A.add(todo, [], pool, brand, "organic", "creator", "our Content Rewards clipping campaign (report pulled by content_rewards.py)")
    return len(todo)


def deep(rows, out, per_post=100, posts_each=10):
    """Comments, then the people who left them: their profiles and recent posts. Raw actor rows are kept."""
    sys.path.insert(0, str(repo() / "components" / "apify"))
    import apify as AP
    d = out / "deep"; d.mkdir(exist_ok=True)
    urls = []
    for r in rows:
        m = re.search(r"@([^/]+)/(?:photo|video)/(\d+)", r.get("postUrl") or "")
        if m:
            urls.append(f"https://www.tiktok.com/@{m[1]}/video/{m[2]}")
    comments = AP.run_async(AP.COMMENTS_TT, {"postURLs": urls, "commentsPerPost": per_post, "maxRepliesPerComment": 20},
                            run_id=os.environ.get("COMMENTS_RUN"))
    (d / "comments.json").write_text(json.dumps(comments, indent=1))
    people = sorted({c.get("uniqueId") for c in comments if c.get("uniqueId")})
    print(f"  {len(comments)} comments from {len(people)} people")
    posts = AP.run_async(AP.PROFILE_TT, {"profiles": people, "resultsPerPage": posts_each, "shouldDownloadVideos": False,
                                          "shouldDownloadCovers": False, "profileScrapeSections": ["videos"]}) if people else []
    (d / "commenter-posts.json").write_text(json.dumps(posts, indent=1))
    prof = {}
    for p in posts:
        a = p.get("authorMeta") or {}
        if a.get("name"):
            prof.setdefault(a["name"], {k: a.get(k) for k in ("name", "nickName", "signature", "fans", "following", "video", "heart", "avatar", "verified", "region")})
    (d / "commenters.json").write_text(json.dumps(prof, indent=1))
    print(f"  {len(prof)} commenter profiles · {len(posts)} of their posts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("link"); ap.add_argument("--brand", required=True); ap.add_argument("--pool", required=True)
    ap.add_argument("--no-media", action="store_true")
    ap.add_argument("--deep", action="store_true", help="also every comment, and every commenter's profile and posts (spends Apify)")
    a = ap.parse_args()
    rows, accounts = report(a.link)
    out = repo() / "runs" / "content-rewards" / a.brand / a.pool / str(date.today())
    out.mkdir(parents=True, exist_ok=True)
    (out / "clips.json").write_text(json.dumps({"pulled": datetime.now().isoformat(timespec="seconds"), "link": a.link,
                                                "clips": rows, "accounts": accounts}, indent=1))
    name = (rows[0].get("campaignName") if rows else a.pool) or a.pool
    (out / "summary.md").write_text(summary(rows, name))
    n = 0 if a.no_media else file_media(rows, a.brand, a.pool, out / "_covers")
    if a.deep:
        deep(rows, out)
    print(f"{len(rows)} clips · snapshot {out} · {n} new clips filed into the {a.pool} pool")


if __name__ == "__main__":
    main()
