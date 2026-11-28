#!/usr/bin/env python3
"""The swipe feed: one list of posts worth swiping, organic and paid, each post once.

    python3 feed.py show  --brand B [--show organic|paid|pasted] [--profile P]   the feed, as lines
    python3 feed.py dead  --brand B                                               what is waiting to be cleared
    python3 feed.py paste --brand B <link>                                        save a link and tear it down
    python3 feed.py tear  <job>                                                   (the background run itself)
    python3 feed.py torn  --brand B                                               swipes already torn down, each once

What goes in (read only, never changed here):
  organic   the profile feeds: <root>/<feed>/sources.json · items.json · observations.jsonl · covers/
  paid      shop videos picked from the product finds: runs/product-tracker/<brand>/picks/*.json
            ad-library sweeps: <root>/<advertiser>/_raw/*.json
  pasted    links pasted on the feed (runs/my-feeds/jobs/) and Studio "Add a swipe" asks (runs/studio-asks/)
  torn      teardowns: runs/video-teardown/_work/*/run.json

Where the folders are: runs/my-feeds/sources.json on this computer only ({"organic": [..], "paid": [..]}); with none,
this repo's own components/swipe-organic/records/avatar-feeds and components/swipe-paid.

One identifier per post (post_id): the platform and the post's own id, read off its link. The same post pulled by two
feeds, pasted again, or torn down twice is one row.

Clearing: posts and sources that look dead (old, last season's, an advertiser or feed nobody pulls any more) are kept
off the feed and listed for the owner's yes. A yes is recorded in runs/my-feeds/decisions.json and the rows leave the
feed for good. Nothing is deleted from the folders this reads.

A picked or pasted post goes to the teardown in code: the post is downloaded (yt-dlp) and handed to
components/video-teardown/machine/run.py, which runs the teardown stages (to stage 2, Spec) and nothing after them.
A post the teardowns already hold is never torn down twice.

Python 3.9, standard library.
"""
from __future__ import annotations

import datetime as _dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]
STORE = WS / "runs" / "my-feeds"
MACHINE = WS / "components" / "video-teardown" / "machine"
SAFE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\Z")
PY = sys.executable

# How old is old. A post older than this, never torn down, waits for the owner's yes to leave the feed.
OLD_DAYS = 365
# A seasonal post (winter, the holidays) older than this is last season's.
SEASON_DAYS = 60
# A feed or an advertiser not pulled for this long is no longer tracked.
STALE_DAYS = 45
SEASONAL = re.compile(r"\b(christmas|xmas|santa|holiday|holidays|thanksgiving|halloween|winter|snow|snowing|"
                      r"new year|new years|nye|valentine|valentines|black friday|cyber monday|easter|"
                      r"stocking stuffer|gift guide)\b", re.I)

_LOCK = threading.Lock()
_CACHE = {}


def now():
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(s):
    if not s:
        return None
    s = str(s).strip().replace("/", "-")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return _dt.datetime.fromisoformat(s).replace(tzinfo=_dt.timezone.utc)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?", s):
            return _dt.datetime.fromisoformat(s.replace(" ", "T")).replace(tzinfo=_dt.timezone.utc)
        d = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:  # noqa: BLE001 — a broken file reads as nothing
        return None


def _write(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, p)


def _cached(key, paths, build):
    """Rebuild only when one of the files under it changed."""
    stamp = []
    for p in paths:
        try:
            stamp.append(os.path.getmtime(p))
        except OSError:
            stamp.append(0)
    stamp = tuple(stamp)
    hit = _CACHE.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    val = build()
    _CACHE[key] = (stamp, val)
    return val


# ---------------------------------------------------------------- the one identifier
def post_id(url, platform=None, native=None):
    """platform:id for a post, read off its link. The same post always gets the same id."""
    if platform and native:
        return "%s:%s" % (platform.lower(), str(native).strip())
    u = str(url or "").strip()
    if not u:
        return None
    m = re.search(r"tiktok\.com/.*?/(?:video|photo)/(\d{8,})", u) or re.search(r"tiktok\.com/.*?[?&]item_id=(\d+)", u)
    if m:
        return "tiktok:" + m.group(1)
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]{5,})", u)
    if m:
        return "instagram:" + m.group(1)
    m = re.search(r"youtube\.com/shorts/([A-Za-z0-9_-]{6,})", u) or re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", u)
    if m:
        return "youtube:" + m.group(1)
    if "youtube.com" in u:
        v = parse_qs(urlparse(u).query).get("v")
        if v:
            return "youtube:" + v[0]
    m = re.search(r"facebook\.com/ads/library/\?id=(\d+)", u)
    if m:
        return "meta:" + m.group(1)
    p = urlparse(u)
    if not p.netloc:
        return None
    return "link:" + (p.netloc.lower().replace("www.", "") + p.path.rstrip("/")).lower()


def platform_of(pid):
    return (pid or "").split(":", 1)[0]


def safe_key(pid):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", pid or "").strip("-")[:80]


# ---------------------------------------------------------------- where things are
def settings():
    s = _read(STORE / "sources.json") or {}
    organic = [Path(p) for p in s.get("organic") or []] or [WS / "components" / "swipe-organic" / "records" / "avatar-feeds"]
    paid = [Path(p) for p in s.get("paid") or []] or [WS / "components" / "swipe-paid"]
    return {"organic": [p for p in organic if p.is_dir()], "paid": [p for p in paid if p.is_dir()]}


def decisions():
    d = _read(STORE / "decisions.json") or {}
    d.setdefault("cleared", {})      # group id -> {at, ids, said}
    d.setdefault("hidden", [])       # post ids hidden by hand
    return d


def _cleared_ids(dec):
    out = set()
    for g in dec["cleared"].values():
        out.update(g.get("ids") or [])
    return out


def brands():
    return sorted(p.name for p in (WS / "brands").iterdir() if p.is_dir() and not p.name.startswith("_")) \
        if (WS / "brands").is_dir() else []


# ---------------------------------------------------------------- organic: the profile feeds
def _feed_posts(fdir):
    S = _read(fdir / "sources.json") or {}
    items = (_read(fdir / "items.json") or {}).get("items") or {}
    last = {}
    obs = fdir / "observations.jsonl"
    if obs.is_file():
        with obs.open(errors="replace") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                k = o.get("item")
                if not k:
                    continue
                cur = last.setdefault(k, {})
                for f in ("views", "likes", "shares"):
                    if o.get(f):
                        cur[f] = o[f]
    sweeps = (fdir / "sweeps.jsonl")
    pulled = None
    if sweeps.is_file():
        tail = sweeps.read_text(errors="replace").strip().splitlines()[-1:]
        if tail:
            try:
                pulled = json.loads(tail[0]).get("at")
            except ValueError:
                pulled = None
    feed = {"id": fdir.name, "brand": S.get("brand"), "profile": S.get("avatar") or None,
            "title": S.get("title") or fdir.name.split("--", 1)[-1].replace("-", " "),
            "pulled": pulled, "sources": len([s for s in S.get("sources") or [] if s.get("status") != "retired"])}
    posts = []
    for key, it in items.items():
        sift = it.get("sift") or {}
        pid = post_id(it.get("url"), it.get("platform"), it.get("id"))
        if not pid:
            continue
        cid = re.sub(r"[^A-Za-z0-9_-]", "", str(it.get("id")))
        local = (fdir / "covers" / (cid + ".jpg")).is_file()
        ob = last.get(key, {})
        posts.append({
            "id": pid, "url": it.get("url"), "platform": it.get("platform"), "author": it.get("author") or "",
            "caption": (it.get("caption") or "")[:280], "tags": (it.get("hashtags") or [])[:12],
            "posted": (it.get("posted") or "")[:10] or None, "seen": it.get("first_seen"),
            "views": ob.get("views"), "likes": ob.get("likes"), "shares": ob.get("shares"),
            "followers": it.get("followers"),
            "cover": ("o/%s/%s" % (fdir.name, cid)) if local else None, "cover_url": it.get("cover"),
            "kind": "organic", "feeds": [fdir.name], "profiles": [S.get("avatar")] if S.get("avatar") else [],
            "brand": S.get("brand"),
            "format": None if str(sift.get("format") or "").lower() in ("", "unread", "unknown", "?", "none") else sift.get("format"),
            "what": sift.get("what"), "why": sift.get("why"), "lane": sift.get("lane"), "kept": sift.get("keep"),
        })
    return feed, posts


def organic():
    """Every profile feed and every post in it (dropped by the feed's own sift: left out)."""
    feeds, posts = [], []
    for root in settings()["organic"]:
        for fdir in sorted(root.iterdir()):
            if not (fdir / "sources.json").is_file():
                continue
            files = [fdir / n for n in ("sources.json", "items.json", "observations.jsonl", "sweeps.jsonl")]
            files.append(fdir / "covers")
            f, ps = _cached("feed:" + str(fdir), files, lambda d=fdir: _feed_posts(d))
            feeds.append(f)
            posts.extend(ps)
    return feeds, posts


# ---------------------------------------------------------------- paid: shop videos and ad-library sweeps
def _picks(brand_dir):
    out = []
    for f in sorted((brand_dir / "picks").glob("*.json")):
        d = _read(f) or {}
        prod = (d.get("product") or {}).get("name")
        for v in d.get("videos") or []:
            url = v.get("link")
            pid = post_id(url)
            if not pid:
                continue
            out.append({
                "id": pid, "url": url, "platform": platform_of(pid), "author": v.get("belonged_creator_handle") or "",
                "caption": (v.get("video_title") or "")[:280], "tags": [],
                "posted": (str(v.get("publish_date") or "")[:10].replace("/", "-")) or None, "seen": d.get("read"),
                "views": v.get("views"), "revenue": v.get("revenue"), "roas": v.get("ads_roas"),
                "ran_as_ad": bool(v.get("ad")), "product": v.get("of") or prod, "says": v.get("says"),
                "cover": None, "cover_url": None, "kind": "paid", "source": "shop video",
                "feeds": ["finds:" + f.stem], "profiles": [], "brand": brand_dir.name,
                "format": None, "what": v.get("says"), "why": None,
            })
    return out


def _advertiser(adir):
    raws = sorted(adir.glob("_raw/*.json"), key=os.path.getmtime)
    # the sweep's own date is in its file name; a file's time changes when it is copied, so it is only the fallback
    dates = sorted(m.group(1) for m in (re.search(r"(20\d\d-\d\d-\d\d)", f.name) for f in raws) if m)
    pulled = dates[-1] if dates else _dt.datetime.fromtimestamp(os.path.getmtime(raws[-1]), _dt.timezone.utc).isoformat()[:10] if raws else None
    name = adir.name
    bf = adir / "_BRAND.md"
    if bf.is_file():
        head = (bf.read_text(errors="replace").splitlines() or [""])[0].lstrip("# ").strip()
        name = head or name
    ads = {}
    for f in raws:
        d = _read(f)
        its = d.get("items") if isinstance(d, dict) and isinstance(d.get("items"), list) else \
            [d] if isinstance(d, dict) and "id" in d else d if isinstance(d, list) else []
        for it in its:
            if isinstance(it, dict) and it.get("id"):
                ads.setdefault(str(it["id"]), {}).update({k: v for k, v in it.items() if v not in (None, "")})
    posts = []
    for a in ads.values():
        mid = str(a.get("meta_ad_id") or "")
        if not mid.isdigit():
            continue
        try:
            days = int(a.get("days_total") or 0)
        except ValueError:
            days = 0
        posts.append({
            "id": "meta:" + mid, "url": "https://www.facebook.com/ads/library/?id=" + mid,
            "media": a.get("video_url") or a.get("image_url"), "platform": "meta",
            "author": name, "caption": re.sub(r"\s+", " ", (a.get("title") or "") + " — " + (a.get("description") or ""))[:280],
            "tags": [], "posted": (a.get("first_seen") or "")[:10] or None, "seen": (a.get("last_seen") or "")[:10] or None,
            "days_running": days or None, "copies": int(a.get("meta_group_ads_count") or 1),
            "cover": None, "cover_url": a.get("image_url"), "kind": "paid", "source": "ad library",
            "advertiser": adir.name, "feeds": ["adv:" + adir.name], "profiles": [], "brand": None,
            "format": None, "what": None, "why": None, "video": bool(a.get("video_url")),
        })
    return {"id": adir.name, "name": name, "pulled": pulled, "ads": len(posts)}, posts


def paid():
    advertisers, posts = [], []
    for root in settings()["paid"]:
        for adir in sorted(root.iterdir()):
            if not adir.is_dir() or not (adir / "_raw").is_dir() or adir.name.startswith(("_", ".")) or adir.name in ("own", "organic"):
                continue
            raws = list(adir.glob("_raw/*.json"))
            a, ps = _cached("adv:" + str(adir), raws + [adir / "_raw"], lambda d=adir: _advertiser(d))
            advertisers.append(a)
            posts.extend(ps)
    pt = WS / "runs" / "product-tracker"
    for bdir in sorted(pt.iterdir()) if pt.is_dir() else []:
        if bdir.is_dir() and not bdir.name.startswith("_") and (bdir / "picks").is_dir():
            files = list((bdir / "picks").glob("*.json"))
            posts.extend(_cached("picks:" + str(bdir), files + [bdir / "picks"], lambda d=bdir: _picks(d)))
    return advertisers, posts


def tracked(brand=None):
    """The paid brands tracked now: the shops in each brand's newest product finds (TrendTrack and Kalodata)."""
    out = {}
    pt = WS / "runs" / "product-tracker"
    for bdir in sorted(pt.iterdir()) if pt.is_dir() else []:
        if not bdir.is_dir() or bdir.name.startswith("_") or (brand and bdir.name != brand):
            continue
        for f in sorted(bdir.glob("*/list.json"), key=os.path.getmtime):
            d = _read(f) or {}
            for src, s in (d.get("sources") or {}).items():
                for p in (s.get("products") or {}).values() if isinstance(s.get("products"), dict) else []:
                    shop = (p.get("shop") or "").strip()
                    if not shop:
                        continue
                    k = shop.lower()
                    r = out.setdefault(k, {"shop": shop, "from": set(), "products": 0, "money": 0, "seen": None,
                                           "link": p.get("link"), "picture": p.get("picture"), "brand": bdir.name})
                    r["from"].add(src)
                    r["products"] += 1
                    r["money"] += float(p.get("month") or (p.get("totals") or {}).get("30") or 0)
                    r["seen"] = max(filter(None, [r["seen"], (d.get("ran_at") or "")[:10]]), default=None)
    rows = [dict(r, **{"from": sorted(r["from"])}) for r in out.values()]
    rows.sort(key=lambda r: -r["money"])
    return rows


# ---------------------------------------------------------------- pasted links
def jobs():
    out = []
    for f in sorted((STORE / "jobs").glob("*.json")):
        r = _read(f)
        if isinstance(r, dict):
            if r.get("state") in ("downloading", "tearing") and r.get("pid") and not _alive(r["pid"]):
                r["state"] = "failed"
                r["why"] = r.get("why") or "the run stopped before it finished"
            out.append(r)
    return out


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _asked_swipes():
    """Links pasted through the Studio's "Add a swipe" job before this feed had its own box."""
    out = []
    for f in glob.glob(str(WS / "runs" / "studio-asks" / "*" / "*" / "ask.json")):
        r = _read(f)
        if isinstance(r, dict) and r.get("kind") == "swipe" and post_id(r.get("input")):
            out.append({"url": r["input"], "brand": r.get("brand"), "at": r.get("asked"), "state": r.get("state"),
                        "ask": r.get("id")})
    return out


def pasted_posts():
    posts = []
    for j in jobs() + _asked_swipes():
        pid = post_id(j.get("url"))
        if not pid:
            continue
        posts.append({"id": pid, "url": j["url"], "platform": platform_of(pid), "author": "", "caption": "",
                      "tags": [], "posted": None, "seen": (j.get("at") or "")[:10], "cover": None, "cover_url": None,
                      "kind": "pasted", "feeds": ["pasted"], "profiles": [], "brand": j.get("brand"),
                      "format": None, "what": None, "why": None,
                      "job": {k: j.get(k) for k in ("key", "state", "label", "why", "at", "ask")}})
    return posts


# ---------------------------------------------------------------- torn down, each swipe once
def _run_row(f):
    r = _read(f)
    if not isinstance(r, dict):
        return None
    d = Path(f).parent
    st = r.get("stages") or {}
    pick = r.get("pick") if isinstance(r.get("pick"), dict) else {}
    keys = set()
    for u in (r.get("post_url"), r.get("origin_url"), r.get("video_url"), pick.get("post")):
        pid = post_id(u) if u and str(u).startswith("http") and "drive.google" not in str(u) else None
        if pid and not pid.startswith("link:"):
            keys.add(pid)
    v = str(r.get("video") or "")
    m = re.search(r"swipe-videos/([A-Za-z0-9_-]{8,})/", v)
    if m:
        keys.add("instagram:" + m.group(1))
    m = re.search(r"(\d{18,20})\.(?:mp4|mov)$", v)
    if m:
        keys.add("tiktok:" + m.group(1))
    if r.get("forked_from"):
        keys.add("run:" + str(r["forked_from"]))
    src = d / (r.get("source") or "source.mp4") if isinstance(r.get("source"), str) else d / "source.mp4"
    try:
        real = src.resolve()
        if real.is_file():
            h = hashlib.sha1(str(real.stat().st_size).encode())
            with real.open("rb") as fh:
                h.update(fh.read(256 * 1024))
            keys.add("file:" + h.hexdigest()[:16])
            if real.parent.name != d.name and real.parent.parent == d.parent:
                keys.add("run:" + real.parent.name)      # a run that reads another run's video is that swipe
    except OSError:
        pass
    keys.add("run:" + d.name)
    done = sum(1 for x in st.values() if isinstance(x, dict) and x.get("status") == "done")
    return {"label": d.name, "brand": r.get("brand"), "keys": sorted(keys), "done": done, "stages": len(st),
            "own": ((st.get("stage1") or {}).get("from") == "scratch"),
            "post_url": r.get("post_url") or pick.get("post"), "lane": r.get("triage_lane"),
            "brief": (st.get("stage5") or {}).get("status") == "done",
            "poster": "runs/video-teardown/_work/%s/%s" % (d.name, r["poster"])
            if isinstance(r.get("poster"), str) and (d / r["poster"]).is_file() else None,
            "at": os.path.getmtime(f)}


def torn_runs():
    rows = []
    for f in glob.glob(str(WS / "runs" / "video-teardown" / "_work" / "*" / "run.json")):
        row = _cached("run:" + f, [f], lambda f=f: _run_row(f))
        if row:
            rows.append(row)
    return rows


def torn(brand=None):
    """Swipes already torn down, each swipe once: runs that share a post, a video file or a fork are one swipe.
    The row kept is the furthest along; the others are listed under it."""
    rows = [r for r in torn_runs() if not brand or r["brand"] == brand]
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for r in rows:
        for k in r["keys"][1:]:
            parent[find(k)] = find(r["keys"][0])
    groups = {}
    for r in rows:
        groups.setdefault(find(r["keys"][0]), []).append(r)
    out = []
    for g in groups.values():
        g.sort(key=lambda r: (r["brief"], r["done"], r["at"]), reverse=True)
        top = dict(g[0])
        top["also"] = [x["label"] for x in g[1:]]
        top["post"] = next((k for x in g for k in x["keys"] if not k.startswith(("run:", "file:"))), None)
        top["at"] = max(x["at"] for x in g)
        out.append(top)
    out.sort(key=lambda r: r["at"], reverse=True)
    return out


def torn_index(brand=None):
    """post id -> the teardown that holds it."""
    idx = {}
    for t in torn(brand):
        if t["post"]:
            idx[t["post"]] = t["label"]
    for r in torn_runs():
        if brand and r["brand"] != brand:
            continue
        for k in r["keys"]:
            if not k.startswith(("run:", "file:")):
                idx.setdefault(k, r["label"])
    return idx


# ---------------------------------------------------------------- what is dead
def _age(d):
    t = _iso(d)
    return (now() - t).days if t else None


def dead(brand=None, feeds=None, advertisers=None, posts=None, torn_ids=None):
    """Groups waiting for the owner's yes. Each group: id, what, why, the posts it holds."""
    if feeds is None or posts is None:
        feeds, op = organic()
        advertisers, pp = paid()
        posts = op + pp
    torn_ids = torn_ids if torn_ids is not None else set(torn_index(brand))
    dec = decisions()
    done = set(dec["cleared"])
    groups = []
    live = [_norm(r["shop"]) for r in tracked()]          # an advertiser is tracked if any brand's finds hold it
    for a in advertisers or []:
        age = _age(a["pulled"])
        names = {_norm(a["id"]), _norm(a["name"])}
        in_finds = any(n and (n in s or s in n) for n in names for s in live if len(s) > 3)
        if (age is None or age > STALE_DAYS) and not in_finds:
            ids = [p["id"] for p in posts if p.get("advertiser") == a["id"]]
            groups.append({"id": "advertiser:" + a["id"], "kind": "advertiser", "name": a["name"],
                           "why": "Not pulled since %s, and not in the current TrendTrack or Kalodata finds"
                           % ((a["pulled"] or "")[:10] or "ever"), "n": len(ids), "ids": ids,
                           "last": (a["pulled"] or "")[:10]})
    for f in feeds:
        if brand and f["brand"] not in (brand, None) and f["brand"] in brands():
            continue
        age = _age(f["pulled"])
        if age is None or age > STALE_DAYS:
            ids = [p["id"] for p in posts if f["id"] in p["feeds"] and len(p["feeds"]) == 1]
            groups.append({"id": "feed:" + f["id"], "kind": "feed", "name": f["title"], "profile": f["profile"],
                           "why": "Profile feed not pulled since %s" % ((f["pulled"] or "")[:10] or "ever"),
                           "n": len(ids), "ids": ids, "last": (f["pulled"] or "")[:10]})
    seasonal, old = [], []
    for p in posts:
        if p["kind"] != "organic" or p["id"] in torn_ids:
            continue
        if brand and p.get("brand") not in (brand, None) and p.get("brand") in brands():
            continue
        age = _age(p.get("posted"))
        text = " ".join([p.get("caption") or ""] + list(p.get("tags") or []))
        if age is not None and age > SEASON_DAYS and SEASONAL.search(text):
            seasonal.append(p["id"])
        elif age is not None and age > OLD_DAYS:
            old.append(p["id"])
    if seasonal:
        groups.append({"id": "seasonal", "kind": "posts", "name": "Last season's posts",
                       "why": "Winter and holiday posts more than %d days old" % SEASON_DAYS,
                       "n": len(set(seasonal)), "ids": sorted(set(seasonal))})
    if old:
        groups.append({"id": "old", "kind": "posts", "name": "Old posts",
                       "why": "Posted more than a year ago and never torn down",
                       "n": len(set(old)), "ids": sorted(set(old))})
    for g in groups:
        g["cleared"] = g["id"] in done
    return groups


def _norm(name):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(name or "").replace("ø", "o").replace("Ø", "o"))
    t = re.sub(r"[^a-z0-9]", "", t.encode("ascii", "ignore").decode().lower())
    return re.sub(r"(usa|us|usstore|store|official|co|com|shop)$", "", t)


def clear(group_id, said=None, brand=None):
    """The owner's yes on one group: its rows leave the feed for good. Nothing is deleted on disk."""
    g = next((x for x in dead(brand) if x["id"] == group_id), None)
    if not g:
        raise ValueError("that group is no longer on the list")
    with _LOCK:
        dec = decisions()
        dec["cleared"][group_id] = {"at": now().isoformat(timespec="seconds"), "ids": g["ids"], "name": g["name"],
                                    "kind": g["kind"], "said": (said or "yes")[:200]}
        _write(STORE / "decisions.json", dec)
    return {"ok": True, "cleared": group_id, "n": len(g["ids"])}


def unclear(group_id):
    with _LOCK:
        dec = decisions()
        dec["cleared"].pop(group_id, None)
        _write(STORE / "decisions.json", dec)
    return {"ok": True}


def hide(pid, on=True):
    with _LOCK:
        dec = decisions()
        h = set(dec["hidden"])
        (h.add if on else h.discard)(pid)
        dec["hidden"] = sorted(h)
        _write(STORE / "decisions.json", dec)
    return {"ok": True}


# ---------------------------------------------------------------- the one feed
def _merge(a, b):
    for k in ("feeds", "profiles"):
        a[k] = sorted(set(a.get(k) or []) | set(b.get(k) or []))
    kinds = set(a.get("kinds") or [a["kind"]]) | set(b.get("kinds") or [b["kind"]])
    a["kinds"] = sorted(kinds)
    for k, v in b.items():
        if a.get(k) in (None, "", []) and v not in (None, "", []):
            a[k] = v
    for k in ("views", "likes", "shares"):
        if (b.get(k) or 0) > (a.get(k) or 0):
            a[k] = b[k]
    return a


def all_posts():
    feeds, op = organic()
    advertisers, pp = paid()
    by = {}
    for p in op + pp + pasted_posts():
        if p["id"] in by:
            _merge(by[p["id"]], dict(p))
        else:
            q = dict(p)
            q["kinds"] = [p["kind"]]
            by[p["id"]] = q
    return feeds, advertisers, by


def feed(brand=None, show="all", profile=None, q=None, sort="new", offset=0, limit=60, waiting=False):
    """The one feed for a brand. show: all · organic · paid · pasted. profile: one profile (avatar) feed's avatar.
    waiting=True shows only the rows waiting for the owner's yes."""
    feeds, advertisers, by = all_posts()
    posts = list(by.values())
    real = set(brands())
    tidx = torn_index(brand)
    dec = decisions()
    gone = _cleared_ids(dec) | set(dec["hidden"])
    groups = dead(brand, feeds, advertisers, posts, set(tidx))
    waiting_ids = set()
    for g in groups:
        if not g["cleared"]:
            waiting_ids.update(g["ids"])
    jobs_by = {}
    for p in pasted_posts():
        jobs_by[p["id"]] = p["job"]

    def mine(p):
        return not brand or p.get("brand") == brand or p.get("brand") not in real or "pasted" in p["kinds"] and p.get("brand") in (brand, None)

    rows, counts, profiles = [], {"all": 0, "organic": 0, "paid": 0, "pasted": 0}, {}
    for p in posts:
        if not mine(p) or p["id"] in gone:
            continue
        if p.get("kept") is False and "pasted" not in p["kinds"]:
            continue                                         # the feed's own sift dropped it
        if (p["id"] in waiting_ids) != bool(waiting):
            continue
        p["torn"] = tidx.get(p["id"])
        p["job"] = jobs_by.get(p["id"])
        counts["all"] += 1
        for k in p["kinds"]:
            counts[k] = counts.get(k, 0) + 1
        for pr in p.get("profiles") or []:
            profiles[pr] = profiles.get(pr, 0) + 1
        if show != "all" and show not in p["kinds"]:
            continue
        if profile and profile not in (p.get("profiles") or []):
            continue
        if q and q.lower() not in " ".join(str(x) for x in (p.get("caption"), p.get("author"), p.get("what"),
                                                             p.get("format"), p.get("product"), " ".join(p.get("tags") or []))).lower():
            continue
        rows.append(p)
    if sort == "views":
        rows.sort(key=lambda p: -(p.get("views") or 0))
    else:
        rows.sort(key=lambda p: ((p.get("job") or {}).get("at") or "",      # what he pasted comes first
                                 p.get("posted") or p.get("seen") or ""), reverse=True)
    names = _profile_names(brand)
    return {"posts": rows[offset:offset + limit], "total": len(rows), "counts": counts,
            "profiles": [{"id": k, "name": names.get(k, k.replace("-", " ")), "n": n}
                         for k, n in sorted(profiles.items(), key=lambda x: -x[1])],
            "waiting": sum(g["n"] for g in groups if not g["cleared"]),
            "tracked": tracked(brand)[:24], "brand": brand}


def _profile_names(brand):
    out = {}
    for b in [brand] if brand else brands():
        f = WS / "brands" / (b or "") / "core-avatars" / "avatars.json"
        d = _read(f)
        rows = d.get("avatars") if isinstance(d, dict) else d if isinstance(d, list) else []
        for a in rows or []:
            if isinstance(a, dict) and (a.get("id") or a.get("key")):
                out[a.get("id") or a.get("key")] = a.get("name") or a.get("label") or a.get("id") or a.get("key")
    return out


# ---------------------------------------------------------------- tear down: a picked or pasted post
def _label_for(pid):
    return ("swipe-" + safe_key(pid).lower())[:48].strip("-")


def start(url, brand, why=None, by="the owner on the feed"):
    """Save a post and tear it down in the background. A post the teardowns already hold is never torn twice."""
    pid = post_id(url)
    if not pid:
        raise ValueError("paste the post's link")
    if not brand or not SAFE.match(brand) or not (WS / "brands" / brand).is_dir():
        raise ValueError("pick a brand")
    have = torn_index(brand).get(pid)
    if have:
        return {"id": pid, "state": "done", "label": have, "already": True}
    key = safe_key(pid)
    f = STORE / "jobs" / (key + ".json")
    with _LOCK:
        cur = _read(f)
        if isinstance(cur, dict) and cur.get("state") in ("queued", "downloading", "tearing") and \
                (cur.get("state") == "queued" or _alive(cur.get("pid"))):
            return dict(cur, already=True)
        rec = {"key": key, "id": pid, "url": url.strip(), "brand": brand, "label": _label_for(pid), "state": "queued",
               "at": now().isoformat(timespec="seconds"), "why": None,
               "picked_why": (why or "pasted by hand on the feed")[:400], "picked_by": by}
        _write(f, rec)
    p = subprocess.Popen([PY, str(Path(__file__).resolve()), "tear", key], cwd=str(HERE),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    rec["pid"] = p.pid
    _write(f, rec)
    return rec


def start_post(pid, brand):
    """Tear down a post already in the feed (the card's Tear down)."""
    _, _, by = all_posts()
    p = by.get(pid)
    if not p:
        raise ValueError("that post is no longer in the feed")
    url = p["url"] if p.get("platform") != "meta" else (p.get("media") or p["url"])
    bits = [x for x in ("format: " + p["format"] if p.get("format") else "",
                        "why the feed kept it: " + p["why"] if p.get("why") else "",
                        "what it is: " + p["what"] if p.get("what") else "",
                        "a shop video that made %s" % p["revenue"] if p.get("revenue") else "") if x]
    why = "picked on the feed" + (" — " + "; ".join(bits) if bits else "")
    rec = start(url, brand, why=why)
    if p.get("platform") == "meta":
        rec["id"] = pid
    return rec


def tear(key):
    """The background run: download, then the teardown machine to stage 2. Writes its state as it goes."""
    f = STORE / "jobs" / (key + ".json")
    rec = _read(f)
    if not isinstance(rec, dict):
        return 2
    rec.update(pid=os.getpid(), state="downloading", started=now().isoformat(timespec="seconds"))
    _write(f, rec)
    media = STORE / "media" / key
    media.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(["yt-dlp", "-q", "--no-playlist", "-o", str(media / "video.%(ext)s"), rec["url"]],
                           capture_output=True, text=True, timeout=600)
        vids = [v for v in media.glob("video.*") if v.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")]
        if not vids:
            if re.search(r"\.(mp4|mov)(\?|$)", rec["url"]):
                import urllib.request
                urllib.request.urlretrieve(rec["url"], str(media / "video.mp4"))
                vids = [media / "video.mp4"]
        if not vids:
            raise RuntimeError("the video would not download: " + ((r.stderr or r.stdout or "").strip().splitlines() or ["no video in that link"])[-1][:200])
        rec.update(state="tearing", video=str(vids[0].relative_to(WS)))
        _write(f, rec)
        with (media / "machine.log").open("w") as log:
            code = subprocess.run([PY, str(MACHINE / "run.py"), str(vids[0]), "--brand", rec["brand"],
                                   "--label", rec["label"], "--post-url", rec["url"], "--to", "2",
                                   "--picked-why", rec.get("picked_why") or "", "--picked-by", rec.get("picked_by") or ""],
                                  stdout=log, stderr=subprocess.STDOUT, cwd=str(MACHINE), timeout=3 * 3600).returncode
        tail = (media / "machine.log").read_text(errors="replace").strip().splitlines()[-1:] or [""]
        rec.update(state="done" if code == 0 else "failed", ended=now().isoformat(timespec="seconds"),
                   why=None if code == 0 else ("the teardown stopped: " + tail[0][:200]))
    except Exception as e:  # noqa: BLE001 — the reason goes on the page
        rec.update(state="failed", why=str(e)[:300], ended=now().isoformat(timespec="seconds"))
    _write(f, rec)
    return 0 if rec["state"] == "done" else 1


# ---------------------------------------------------------------- covers
def cover_file(key):
    """A cover on disk: o/<feed>/<id> (a profile feed's saved cover)."""
    m = re.fullmatch(r"o/([A-Za-z0-9_.-]+)/([A-Za-z0-9_-]+)", key or "")
    if not m:
        return None
    for root in settings()["organic"]:
        f = root / m.group(1) / "covers" / (m.group(2) + ".jpg")
        if f.is_file():
            return f
    return None


# ---------------------------------------------------------------- the Studio's /api/desk/feed/*
def handle(h, method, api, q, body):
    """api is the path after /api/desk/feed. h.send(code, data[, type]) answers."""
    brand = q.get("brand") if SAFE.match(q.get("brand") or "") else None
    try:
        data = json.loads(body or b"{}") if method == "POST" else {}
    except ValueError:
        return h.send(400, {"error": "could not read that"})
    try:
        if method == "GET":
            if api == []:
                return h.send(200, feed(brand, q.get("show") or "all", q.get("profile") or None, q.get("q") or None,
                                        q.get("sort") or "new", int(q.get("off") or 0), min(int(q.get("n") or 60), 200),
                                        waiting=bool(q.get("waiting"))))
            if api == ["dead"]:
                gs = dead(brand)
                _, _, by = all_posts()
                out = []
                for g in gs:          # a few of each group's posts, so he can look before he says yes
                    sample = [by[i] for i in g["ids"][:200] if i in by]
                    sample.sort(key=lambda p: -(p.get("views") or 0))
                    out.append(dict(g, ids=[], sample=[{k: p.get(k) for k in ("id", "url", "caption", "author", "posted",
                                                                              "views", "cover", "cover_url", "platform")}
                                                       for p in sample[:6]]))
                return h.send(200, {"groups": out})
            if api == ["torn"]:
                return h.send(200, {"swipes": torn(brand)})
            if api == ["jobs"]:
                return h.send(200, {"jobs": [j for j in jobs() if not brand or j.get("brand") == brand]})
            if api == ["cover"]:
                f = cover_file(q.get("k"))
                return h.send(200, f.read_bytes(), "image/jpeg") if f else h.send(404, {"error": "no cover"})
        if method == "POST":
            b = data.get("brand") if SAFE.match(str(data.get("brand") or "")) else brand
            if api == ["paste"]:
                return h.send(200, start(str(data.get("url") or ""), b))
            if api == ["tear"]:
                return h.send(200, start_post(str(data.get("id") or ""), b))
            if api == ["clear"]:
                return h.send(200, clear(str(data.get("group") or ""), data.get("said"), b))
            if api == ["unclear"]:
                return h.send(200, unclear(str(data.get("group") or "")))
            if api == ["hide"]:
                return h.send(200, hide(str(data.get("id") or ""), data.get("on", True) is not False))
        return h.send(404, {"error": "not found"})
    except ValueError as e:
        return h.send(400, {"error": str(e)})


# ---------------------------------------------------------------- command line
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["show", "dead", "paste", "tear", "torn"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--brand")
    ap.add_argument("--show", default="all")
    ap.add_argument("--profile")
    ap.add_argument("-n", type=int, default=20)
    a = ap.parse_args(argv)
    if a.cmd == "tear":
        return tear(a.arg)
    if a.cmd == "paste":
        print(json.dumps(start(a.arg, a.brand), indent=1))
        return 0
    if a.cmd == "dead":
        for g in dead(a.brand):
            print("%-34s %6d  %s%s" % (g["id"][:34], g["n"], g["why"], "  (cleared)" if g["cleared"] else ""))
        return 0
    if a.cmd == "torn":
        rows = torn(a.brand)
        print(len(rows), "swipes,", sum(len(r["also"]) for r in rows), "repeat runs folded in")
        for r in rows[:a.n]:
            print(" ", r["label"], r["post"] or "", ("+ " + ", ".join(r["also"])) if r["also"] else "")
        return 0
    f = feed(a.brand, a.show, a.profile, limit=a.n)
    print(json.dumps({k: v for k, v in f.items() if k not in ("posts", "tracked")}, indent=1))
    for p in f["posts"]:
        print(" ", p["id"], "/".join(p["kinds"]), (p.get("posted") or "")[:10], p.get("views"), (p.get("caption") or "")[:60])
    return 0


if __name__ == "__main__":
    sys.exit(main())
