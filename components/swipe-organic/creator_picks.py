#!/usr/bin/env python3
"""Creator picks — the ONE door from picked swipes to creator briefs.

    python3 creator_picks.py pick  --brand <b> [--max 10] [--sources trendtrack,tiktok-shop]
                                   [--min-days 30] [--floor 500000] [--no-fetch] [--dry-run]
    python3 creator_picks.py add   --brand <b> (--feed <feed> --item <key> | --url <post> | --video <file>)
                                   [--product <p>] [--why "..."] [--label <l>] [--by hand|desk|tsv|briefs]
    python3 creator_picks.py fetch --brand <b> [--label <l>]      # download any pick still without its video
    python3 creator_picks.py mark  --brand <b> --label <l> --state <state> [--run <dir>] [--brief <path>] [--note "..."]
    python3 creator_picks.py list  --brand <b> [--week <w>] [--json]

Every way a swipe becomes a creator brief writes its pick here first, so there is
one list per brand:
  - `pick`   — this week's picks from PROVEN sources only (2026-11-15: no organic
               viral posts): TrendTrack ads already swept (runs/trendtrack/market/
               */ALL.json, the brand's category domains in records/desk/
               proven-sources.json; running 30+ days, ranked on estimated spend,
               days, duplicates) and TikTok Shop videos (tiktok-shop/*.json for the
               brand; ranked on sales, then views). Never padded; each video
               downloaded free with yt-dlp (an ad from its Ad Library page).
  - `add`    — one pick by hand: a card on My Feeds, a post link, or a video file.
  - the desk's "Tear down" click with route = creator (desk.py `/api/tear`),
    `briefs.py --route creator`, and `video-teardown/machine/general_run.sh`
    all register their run here as they start it, and mark it when it ends.

THE QUEUE (the hand-off to brief writing) — one file per brand:
    runs/swipe-organic/<brand>/creator-picks/picks.json   {brand, made, updated, items: [...]}
Each item — the fields brief writing reads first:
    swipe_id (stable; the teardown label), brand, source_url, video (repo-relative
    path to the downloaded file; null until fetched), views, creator_handle,
    product, format (an id from components/elements/library/format.video.json when
    the swipe's own kind is one, else null), swipe_kind (the sift's free-text kind),
    avatar (core avatar), sub, awareness, picked (YYYY-MM-DD), week (ISO),
    state, status, brief, pick_source (trendtrack · tiktok-shop · my-feeds · hand),
    proof (the numbers it was ranked on: days_running/estimated_spend/duplicates/
    reach for an ad; views/sales/gmv/engagement for a Shop video)
  and the detail: why, picked_by, picked_at, winning_format, avoid_format,
    teardown{label, run, state}, source{kind, feed, item, platform, caption, cover,
    what, …}.
state:  picked → tearing → torn | failed → briefed;  dropped
status: draft until the owner's yes (`mark --approve` = approved; dropped = deprecated).
Progress lives in `state`. Brief writing takes items with state `picked` (video set) or `torn` (its teardown
already ran; `teardown.run`), and when the brief is written:
    creator_picks.py mark --brand B --label <swipe_id> --state briefed --brief <path>
Only this file writes the queue; every other station acts through `mark`.

THE WINNERS SLOT (read only, never written here) — the numbers loop's file:
    runs/winners/<brand>/brief-next.json
    {basis, formats: [{format, videos, purchases, ...}], avoid: [{format, ...}], ...}
A swipe whose words carry a `formats` entry (every word of it, in its kind,
what-line or caption) goes to the front of its source, best-selling format first; one
that carries an `avoid` entry goes to the back. The item names the hit. Absent
file, or basis "none yet" = proof only.

Spends nothing: no pull, no model. The only network call is the free download.
"""
import argparse, datetime as dt, fcntl, json, re, subprocess, sys, tempfile
from contextlib import contextmanager
from pathlib import Path
import desklib as D

WS = D.WS
sys.path.append(str(WS / "components" / "brandpath"))
import brandpath as BP  # noqa: E402  anything under brands/<brand>/

STATES = ("picked", "tearing", "torn", "failed", "briefed", "dropped")
FLOOR = 500_000
LANE_AWARENESS = {"entertainment": "unaware", "educational": "problem-aware"}
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
ROLE_FILE = D.HERE / "strategist.json"   # who fills the picker role — a definition, edited by hand
PROVEN_FILE = D.HERE / "records" / "desk" / "proven-sources.json"   # per brand: TrendTrack domains, Shop product tags
MIN_DAYS = 30   # a paid ad counts as proven once it has run this long
CATCH_ALL = {"other", "others", "unknown", "mixed", "misc", "none", "n-a", "na", "unclear", "unread"}


def week_of(day=None):
    y, w, _ = (day or dt.date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def queue_file(brand):
    return WS / "runs" / "swipe-organic" / brand / "creator-picks" / "picks.json"


def slot_file(brand):
    return WS / "runs" / "winners" / brand / "brief-next.json"


def media_dir(label):
    # the same gitignored folder briefs.py downloads into, so a teardown reuses it
    return D.HERE / "records" / "desk" / "media" / label


def rel(p):
    """A stored path is repo-relative (builder card rule 4), never a machine path."""
    p = Path(p).resolve()
    try:
        return str(p.relative_to(WS.resolve()))
    except ValueError:
        raise SystemExit(f"{p} is outside the workspace — copy it under the workspace first "
                         "(a record never holds a machine path)")


def brand_ok(brand):
    if not re.fullmatch(r"[a-z0-9-]+", brand or "") or \
            not BP.brand_root(brand, root=WS / "brands").is_dir():
        raise SystemExit(f"no brand folder for '{brand}'")


def product_for(brand, core):
    f = D.HERE / "records" / "desk" / "products.json"
    m = (json.loads(f.read_text()) if f.exists() else {}).get(brand) or {}
    return m.get(core) or m.get("_default")


def feed_label(feed, key):
    """The label briefs.py gives an avatar-feed teardown — kept identical so a
    desk click and a queued pick name the same run."""
    who = feed.get("sub") or feed.get("core") or feed["id"]
    return re.sub(r"[^a-z0-9]+", "-", f"feed-{who}-{key.split(':')[-1]}".lower()).strip("-")[:60]


def slug(s, n=60):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n]


_FORMATS = None


def format_id(kind):
    """The elements video-format id for a swipe's kind, only on an exact id/alias hit."""
    global _FORMATS
    if _FORMATS is None:
        f = WS / "components" / "elements" / "library" / "format.video.json"
        rows = json.loads(f.read_text()).get("rows", []) if f.exists() else []
        _FORMATS = {}
        for r in rows:
            for k in [r.get("id"), r.get("name"), *(r.get("aliases") or [])]:
                if k:
                    _FORMATS[slug(k)] = r["id"]
    return _FORMATS.get(slug(kind or "")) if kind else None


# ------------------------------------------------------------------ the file
@contextmanager
def opened(brand):
    """Read-modify-write the brand's queue under a lock (desk clicks run in threads)."""
    f = queue_file(brand)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(Path(tempfile.gettempdir()) / f"creator-picks-{brand}.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        q = json.loads(f.read_text()) if f.exists() else {
            "what": "Creator picks for one brand — the queue brief writing takes. "
                    "Written only by components/swipe-organic/creator_picks.py.",
            "brand": brand, "made": D.now(), "items": []}
        yield q
        q["updated"] = D.now()
        tmp = f.parent / ".picks.tmp"
        tmp.write_text(json.dumps(q, indent=1, ensure_ascii=False))
        tmp.replace(f)


def items(brand):
    f = queue_file(brand)
    return json.loads(f.read_text()).get("items", []) if f.exists() else []


def find(brand, label):
    return next((r for r in items(brand) if r["swipe_id"] == label), None)


def put(brand, row):
    """Add an item, or return the one already there for the same swipe (no doubles)."""
    with opened(brand) as q:
        for r in q["items"]:
            if r["swipe_id"] == row["swipe_id"] \
                    or (row["source"].get("item") and r["source"].get("item") == row["source"]["item"]) \
                    or (row["source_url"] and r["source_url"] == row["source_url"]) \
                    or (row["video"] and r["video"] == row["video"]):
                return r, False
        q["items"].append(row)
        return row, True


# ------------------------------------------------------------------ the winners slot
def slot(brand):
    """(formats to favour, best first; formats to avoid) from the numbers loop's file."""
    f = slot_file(brand)
    if not f.exists():
        return [], []
    try:
        s = json.loads(f.read_text())
    except ValueError:
        print(f"  winners slot unreadable, ignored: {rel(f)}", file=sys.stderr)
        return [], []
    if s.get("basis") in (None, "none yet") or s.get("status") == "deprecated":
        return [], []
    # a catch-all bucket ("other") names no format: it would lift every untagged swipe
    real = lambda x: x.get("format") and slug(x["format"]) not in CATCH_ALL
    return [x for x in s.get("formats") or [] if real(x)], [x for x in s.get("avoid") or [] if real(x)]


def _words(s):
    return [w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) >= 3]


def slot_hit(card, entries):
    """The first entry whose every word is in the swipe's kind, what-line or caption."""
    text = set(_words(" ".join(str(card.get(k) or "") for k in ("kind", "format", "what", "caption"))))
    for i, x in enumerate(entries):
        ws = _words(x["format"])
        if ws and all(w in text for w in ws):
            return i, x
    return None, None


# ------------------------------------------------------------------ items
def _flat(label, brand, week, url, video, views, handle, product, kind, core, sub, awareness):
    return {"swipe_id": label, "brand": brand, "source_url": url,
            "video": rel(video) if video else None, "views": views, "creator_handle": handle,
            "product": product, "format": format_id(kind), "swipe_kind": kind,
            "avatar": core, "sub": sub, "awareness": awareness,
            "picked": dt.date.today().isoformat(), "week": week,
            "state": "picked", "status": "draft", "brief": None}


def item_from_card(brand, week, feed, c, why, by, product=None, label=None, good=(), bad=()):
    label = label or feed_label(feed, c["key"])
    lane = c.get("lane")
    r = _flat(label, brand, week, c["url"], None, c.get("views"), c.get("author"),
              product or product_for(brand, feed.get("core")), c.get("kind"), feed.get("core"),
              feed.get("sub"),
              LANE_AWARENESS.get(lane or "entertainment") if feed.get("core") else None)
    _, g = slot_hit(c, list(good))
    _, b = slot_hit(c, list(bad))
    r.update(why=why, picked_by=by, picked_at=D.now(), pick_source="my-feeds", proof={"views": c.get("views")},
             winning_format=g and {k: g.get(k) for k in ("format", "videos", "purchases", "roas")},
             avoid_format=b and {k: b.get(k) for k in ("format", "videos", "spend", "purchases")},
             teardown=None,
             source={"kind": "feed", "feed": feed["id"], "item": c["key"], "platform": c["platform"],
                     "caption": c.get("caption"), "cover": c.get("cover"), "sent": c.get("sent"),
                     "punch": c.get("punch"), "age_days": c.get("age"), "lane": lane,
                     "what": c.get("what")})
    return r


def bare_item(brand, week, label, by, why, product, url=None, video=None, handle=None):
    r = _flat(label, brand, week, url, video, None, handle, product or product_for(brand, None),
              None, None, None, None)
    r.update(why=why, picked_by=by, picked_at=D.now(), pick_source="hand", proof=None,
             winning_format=None, avoid_format=None,
             teardown=None, source={"kind": "url" if url else "file", "feed": None, "item": None})
    return r


def download(label, url):
    """yt-dlp into the desk's media folder (free, never Apify). Returns the file or None."""
    d = media_dir(label)
    have = [v for v in d.glob("video.*") if v.suffix.lower() in VIDEO_EXT] if d.exists() else []
    if have:
        return have[0]
    d.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["yt-dlp", "-o", str(d / "video.%(ext)s"), "--no-playlist", "-f", "mp4/best", url],
                       capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    got = [v for v in d.glob("video.*") if v.suffix.lower() in VIDEO_EXT]
    return got[0] if got else None


def download_direct(label, url):
    """Plain HTTP copy of a video file (a TrendTrack media link, which expires: only
    fresh from a pull). Free. Returns the file or None."""
    d = media_dir(label)
    d.mkdir(parents=True, exist_ok=True)
    out = d / "video.mp4"
    try:
        subprocess.run(["curl", "-sfL", "--max-time", "120", "-o", str(out), url], capture_output=True, timeout=150)
    except (OSError, subprocess.TimeoutExpired):
        pass
    if out.exists() and out.stat().st_size > 10_000:
        return out
    if out.exists():
        out.unlink()
    return None


def fetch(brand, label=None):
    """Download every item that has a link and no video yet; record the path."""
    todo = [r for r in items(brand) if not r.get("video") and r.get("source_url")
            and r["state"] in ("picked",) and (not label or r["swipe_id"] == label)]
    done = 0
    for r in todo:
        v = download(r["swipe_id"], r["source_url"])
        if not v and (r.get("source") or {}).get("media"):
            v = download_direct(r["swipe_id"], r["source"]["media"])   # the source's own copy
        with opened(brand) as q:
            x = next(i for i in q["items"] if i["swipe_id"] == r["swipe_id"])
            if v:
                x["video"] = rel(v)
                x.pop("note", None) if x.get("note") == "the video would not download" else None
                done += 1
            else:
                x["note"] = "the video would not download"
        print(f"  {r['swipe_id']}: {'video saved' if v else 'would not download'}")
    return done, len(todo)


# ------------------------------------------------------------------ proven sources
def proven_map(brand):
    """The brand's proven-source settings (data, not code): which TrendTrack sweep
    domains sit in its category, and which product a TikTok Shop post's tag sells."""
    f = PROVEN_FILE
    return ((json.loads(f.read_text()) if f.exists() else {}).get(brand) or {})


def _taken(brand):
    return {r["source"].get("item") for r in items(brand)} | {r.get("source_url") for r in items(brand)}


def _ad_candidate(ad, src, file):
    """One Meta ad (sweep item or pull row, already flattened) as a candidate."""
    days, num = ad["days"], str(ad["id"]).split("_")[-1]
    proof = {"days_running": days, "estimated_spend": ad.get("spend"), "duplicates": ad.get("dups"),
             "reach": ad.get("reach"), "status": ad.get("status"), "first_seen": ad.get("first_seen"),
             src: rel(file)}
    return {"pick_source": "trendtrack", "item": f"trendtrack:{ad['id']}",
            "label": slug(f"tt-{ad.get('page') or 'ad'}-{num}"),
            "url": f"https://www.facebook.com/ads/library/?id={num}",
            "handle": ad.get("page"), "views": None, "proof": proof,
            "score": (days, ad.get("spend") or 0, ad.get("dups") or 0),
            "why": f"proven ad · running {days} days · est. spend ${ad.get('spend') or 0:,}"
                   f" · {ad.get('dups') or 1} duplicates · {ad.get('page')}",
            "what": (ad.get("what") or "")[:300], "caption": ad.get("caption") or "",
            "cover": ad.get("cover"), "media": ad.get("media"), "platform": "facebook", "tag": None}


def _tiktok_candidate(x, file):
    """One TrendTrack TikTok library row (shop-linked) as a candidate, ranked on views."""
    m, prof, c = x.get("metrics") or {}, x.get("profile") or {}, x.get("content") or {}
    views, handle, tid = m.get("views") or 0, prof.get("handle") or "", x.get("tiktokId") or str(x["id"]).split("_")[-1]
    shop = (x.get("shop") or {}).get("domain")
    return {"pick_source": "trendtrack", "item": f"trendtrack:{x['id']}",
            "label": slug(f"tt-{handle}-{tid}"), "url": f"https://www.tiktok.com/@{handle}/video/{tid}",
            "handle": handle, "views": views,
            "proof": {"views": views, "likes": m.get("likes"), "shares": m.get("shares"),
                      "days_running": x.get("daysRunning"), "type": x.get("type"), "shop": shop,
                      "pull": rel(file)},
            "score": (views, m.get("likes") or 0, 0),
            "why": f"TikTok ad · {views:,} views · {prof.get('name') or handle}" + (f" · sells via {shop}" if shop else ""),
            "what": (c.get("description") or "")[:300], "caption": c.get("description") or "",
            "cover": (x.get("media") or {}).get("thumbnailUrl"), "media": (x.get("media") or {}).get("videoUrl"),
            "platform": "tiktok", "tag": None}


def _pull_rows(brand):
    """Rows of the brand's paid pulls (runs/trendtrack/market/<label>/result.json whose
    label starts with one of the brand's `trendtrack_pulls`)."""
    prefixes = tuple(proven_map(brand).get("trendtrack_pulls") or [])
    if not prefixes:
        return
    for f in sorted((WS / "runs" / "trendtrack" / "market").glob("*/result.json")):
        if not f.parent.name.startswith(prefixes):
            continue
        try:
            rows = json.loads(f.read_text()).get("data") or []
        except ValueError:
            continue
        for r in rows:
            yield r, f


def trendtrack_candidates(brand, min_days):
    """Proven swipes from TrendTrack files already on disk (the door spends no credit):
    sweeps of the brand's category domains (ALL.json) and the brand's paid pulls
    (result.json). Meta ads: video only, running at least `min_days`, ranked on days
    running, then estimated spend, then duplicates; a pull keeps one ad per advertiser.
    TikTok rows: paid TikTok ads only (never organic posts), one per creator, ranked on
    views. Videos come free (Ad Library page,
    TikTok link)."""
    domains = set(proven_map(brand).get("trendtrack_domains") or [])
    out, seen = [], set()
    for f in sorted((WS / "runs" / "trendtrack" / "market").glob("*/ALL.json")):
        try:
            sweep = json.loads(f.read_text())
        except ValueError:
            continue
        if sweep.get("domain") not in domains:
            continue
        for ad in sweep.get("items") or []:
            days = ad.get("days_total") or 0
            if not ad.get("video_url") or days < min_days or ad["id"] in seen:
                continue
            seen.add(ad["id"])
            out.append(_ad_candidate({"id": ad["id"], "days": days, "spend": ad.get("estimated_spend"),
                                      "dups": ad.get("meta_group_ads_count"), "reach": ad.get("reach"),
                                      "status": ad.get("meta_status"), "first_seen": ad.get("first_seen"),
                                      "page": ad.get("meta_page_name") or sweep.get("domain"),
                                      "what": ad.get("description"), "caption": ad.get("title"),
                                      "cover": ad.get("image_url"), "media": ad.get("video_url")}, "sweep", f))
    best = {}
    for r, f in _pull_rows(brand):
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        if str(r["id"]).startswith("tiktok_"):
            # paid TikToks only (type "ad"): an organic post is the wrong source
            if (r.get("media") or {}).get("type") == "video" and r.get("type") == "ad":
                cand = _tiktok_candidate(r, f)
                key = "tiktok:" + (cand["handle"] or "").lower()
                if key not in best or cand["score"] > best[key]["score"]:
                    best[key] = cand
            continue
        days = r.get("daysRunning") or 0
        if (r.get("media") or {}).get("type") != "video" or days < min_days:
            continue
        m, c, adv = r.get("metrics") or {}, r.get("content") or {}, r.get("advertiser") or {}
        cand = _ad_candidate({"id": r["id"], "days": days, "spend": m.get("estimatedSpend"),
                              "dups": m.get("duplicates"), "reach": m.get("reach"), "status": r.get("status"),
                              "first_seen": r.get("firstSeenAt"), "page": adv.get("name"),
                              "what": c.get("transcript") or c.get("body"), "caption": c.get("body"),
                              "cover": (r.get("media") or {}).get("thumbnailUrl"),
                              "media": (r.get("media") or {}).get("mediaUrl")}, "pull", f)
        key = (adv.get("name") or "").lower()
        if key not in best or cand["score"] > best[key]["score"]:
            best[key] = cand
    return out + list(best.values())


def tiktok_shop_candidates(brand, floor):
    """TikTok Shop affiliate videos (tiktok-shop/*.json, the files whose `brand` is
    this one): ranked on sales when the file carries them, then views."""
    m = proven_map(brand).get("tiktok_shop_products") or {}
    out = []
    for f in sorted((D.HERE / "tiktok-shop").glob("*.json")):
        try:
            pool = json.loads(f.read_text())
        except ValueError:
            continue
        if pool.get("brand") != brand:
            continue
        for x in pool.get("posts") or []:
            views = x.get("views") or 0
            sales = x.get("sales") or x.get("units_sold")
            if views < floor and not sales:
                continue
            out.append({"pick_source": "tiktok-shop", "item": f"tiktok-shop:{x['id']}",
                        "label": slug(f"shop-{x.get('creator')}-{x['id']}"), "url": x.get("url"),
                        "handle": x.get("creator"), "views": views,
                        "proof": {"views": views, "sales": sales, "gmv": x.get("gmv"),
                                  "engagement": x.get("engagement"), "pool": rel(f)},
                        "score": (sales or 0, views),
                        "why": f"TikTok Shop video · {views:,} views" + (f" · {sales:,} sold" if sales else "")
                               + (f" · {x['structure_read']}" if x.get("structure_read") else ""),
                        "what": x.get("structure_read") or "", "caption": x.get("caption") or "",
                        "cover": None, "platform": "tiktok", "tag": x.get("product"),
                        "product": m.get(x.get("product") or "")})
    return out


SOURCES = {"trendtrack": lambda a: trendtrack_candidates(a.brand, a.min_days),
           "tiktok-shop": lambda a: tiktok_shop_candidates(a.brand, a.floor)}


def proven_rank(c, good, bad):
    gi, _ = slot_hit(c, good)
    bi, _ = slot_hit(c, bad)
    return (bi is None, gi is not None, -(gi or 0), c["score"])


def default_picks(a, good, bad):
    """The role's default filling: proven ads and TikTok Shop videos, never organic
    viral posts (2026-11-15). Each source ranked on its own proof, the winners slot
    on top; the sources then take turns so neither crowds the other out."""
    taken = _taken(a.brand)
    per = []
    for name in a.sources.split(","):
        cs = [c for c in SOURCES[name](a) if c["item"] not in taken and c["url"] not in taken]
        # one lane per source and platform: a TikTok's views and an ad's days are not one scale
        for plat in sorted({c["platform"] for c in cs}):
            lane = [c for c in cs if c["platform"] == plat]
            per.append(sorted(lane, key=lambda c: proven_rank(c, good, bad), reverse=True))
    picks = []
    while any(per) and len(picks) < a.max:
        for lst in per:
            if lst and len(picks) < a.max:
                picks.append(lst.pop(0))
    return picks


def item_from_proven(brand, week, c, by, good=(), bad=()):
    r = _flat(c["label"], brand, week, c["url"], None, c.get("views"), c.get("handle"),
              c.get("product") or product_for(brand, None), None, None, None, None)
    _, g = slot_hit(c, list(good))
    _, b = slot_hit(c, list(bad))
    r.update(swipe_kind=c.get("what") or None, why=c.get("_why") or c["why"], picked_by=by,
             picked_at=D.now(), pick_source=c["pick_source"], proof=c["proof"],
             winning_format=g and {k: g.get(k) for k in ("format", "videos", "purchases", "roas")},
             avoid_format=b and {k: b.get(k) for k in ("format", "videos", "spend", "purchases")},
             teardown=None,
             source={"kind": c["pick_source"], "feed": None, "item": c["item"], "platform": c["platform"],
                     "caption": c.get("caption"), "cover": c.get("cover"), "what": c.get("what"),
                     "tag": c.get("tag"), "media": c.get("media")})
    return r


def role():
    """The picker is a named role, the creative strategist. strategist.json says who
    fills it: `command` null = the built-in default (proven sources, ranked on proof,
    the winners slot on top); a repo-relative script = that system picks instead,
    printing [{"item", "why"}] (an item key from a proven source, e.g.
    "tiktok-shop:<id>" or "trendtrack:<ad id>") for `--brand B --max N` on stdout.
    `owner_yes` true = picks wait as draft until `mark --approve`. Filling the role
    never changes the door."""
    r = {"role": "creative strategist", "filled_by": "default", "command": None, "owner_yes": True}
    if ROLE_FILE.exists():
        r.update(json.loads(ROLE_FILE.read_text()))
    return r


# THE PICK MIX (logic layer W1, 2026-11-18). Nothing set how a week's picks split between what the market is
# watching now and adjacent markets and competitors. The split is a rule on the picker role (strategist.json
# `mix`), counted on this queue: every pick already says which source it came from. It is printed with every
# pick run and written on each pick. It changes which picks are taken only when the rule says `applies`.
MIX_SIDE = {"my-feeds": "market_now", "trendtrack": "adjacent", "tiktok-shop": "adjacent"}   # a hand pick is on neither side


def mix_rule(r=None):
    """(market_now parts, adjacent parts, applies) from the role file, or None when it carries no usable rule."""
    m = (r if r is not None else role()).get("mix") or {}
    try:
        now_, adj = int(m.get("market_now")), int(m.get("adjacent"))
    except (TypeError, ValueError):
        return None
    if now_ < 0 or adj < 0 or now_ + adj == 0:
        return None
    return now_, adj, m.get("applies") is True


def mix_read(brand, week, r=None):
    """Where the week stands against the mix: {market_now, adjacent, room, applies, line}. `room` is how many
    more adjacent picks keep the split (one adjacent pick is always allowed, so a week can start on either
    side). None when the role carries no rule."""
    rule = mix_rule(r)
    if not rule:
        return None
    now_, adj, applies = rule
    rows = [x for x in items(brand) if x.get("week") == week and x.get("state") != "dropped"]
    have = {"market_now": 0, "adjacent": 0}
    for x in rows:
        side = MIX_SIDE.get(x.get("pick_source") or "")
        if side:
            have[side] += 1
    allowed = max(1, (have["market_now"] * adj) // now_) if now_ else 10 ** 6
    room = max(0, allowed - have["adjacent"]) if adj else 0
    line = (f"pick mix {now_} in {now_ + adj} from the market's own feeds, {adj} in {now_ + adj} from adjacent markets and "
            f"competitors · this week so far: {have['market_now']} and {have['adjacent']} · "
            + (f"applies: room for {room} more adjacent pick(s)" if applies else "printed only (the rule is not switched on)"))
    return dict(have, room=room, applies=applies, line=line, rule=f"{now_}:{adj}")


def strategist_picks(r, a, good, bad):
    """The role filled by a system: its picks, looked up in the proven sources."""
    out = subprocess.run([sys.executable, str(WS / r["command"]), "--brand", a.brand, "--max", str(a.max)],
                         capture_output=True, text=True, timeout=1800)
    if out.returncode != 0:
        raise SystemExit(f"the creative strategist ({r['filled_by']}) stopped: {out.stderr[-300:]}")
    pool = {c["item"]: c for name in SOURCES for c in SOURCES[name](a)}
    picks = []
    for x in json.loads(out.stdout or "[]"):
        c = pool.get(x.get("item"))
        if c:
            picks.append(dict(c, _why=x.get("why")))
    return picks[:a.max]


def cmd_pick(a):
    brand_ok(a.brand)
    week = a.week or week_of()
    good, bad = slot(a.brand)
    r = role()
    mix = mix_read(a.brand, week, r)
    if mix and mix["applies"]:
        a.max = min(a.max, mix["room"])       # this picker fills the adjacent side; its share of the week, no more
    picks = (strategist_picks(r, a, good, bad) if r.get("command") else default_picks(a, good, bad)) if a.max > 0 else []
    print(f"{a.brand} · {week} · {len(picks)} picks · sources {a.sources} · creative strategist: {r['filled_by']}"
          f"{' · waits for the owner' + chr(39) + 's yes' if r['owner_yes'] else ''} · winners slot: "
          + (f"{len(good)} formats to favour, {len(bad)} to avoid" if good or bad else "empty — proof only"))
    if mix:
        print(f"  {mix['line']}")
    for c in picks:
        print(f"  {c['label']}  [{c['pick_source']}]  {c.get('_why') or c['why']}")
        if not a.dry_run:
            row = item_from_proven(a.brand, week, c, "pick", good=good, bad=bad)
            row["picker"] = f"creative strategist · {r['filled_by']}"
            if mix:
                row["mix"] = {"side": MIX_SIDE.get(row.get("pick_source") or ""), "rule": mix["rule"], "applies": mix["applies"]}
            row["status"] = "draft" if r["owner_yes"] else "approved"
            put(a.brand, row)
    if not picks and mix and mix["applies"] and a.max <= 0:
        print("  the adjacent side of the mix is full for this week: the next picks come from the market's own feeds")
    elif not picks:
        print("  no proven swipe waiting: a TrendTrack pull is needed (plan + credit cost first, never automatic)")
    if picks and not a.dry_run:
        if not a.no_fetch:
            done, n = fetch(a.brand)
            print(f"  videos: {done} of {n} downloaded")
        print(f"queue: {rel(queue_file(a.brand))}")


def cmd_add(a):
    brand_ok(a.brand)
    week = a.week or week_of()
    if a.feed:
        f = next((x for x in D.feeds() if x["id"] == a.feed), None)
        c = next((x for x in D.cards(a.feed) if x["key"] == a.item), None) if f else None
        if not c:
            raise SystemExit("that card is not in that feed")
        good, bad = slot(a.brand)
        row = item_from_card(a.brand, week, f, c, a.why or D.hand_pick_why(c), a.by,   # the card's own read, not a stock line
                             product=a.product, label=a.label, good=good, bad=bad)
    elif a.url:
        label = a.label or slug(f"pick-{a.url.rstrip('/').split('/')[-1]}")
        row = bare_item(a.brand, week, label, a.by, a.why or "picked by hand", a.product, url=a.url, handle=a.author)
    elif a.video:
        if not Path(a.video).exists():
            raise SystemExit(f"no video at {a.video}")
        label = a.label or slug(f"pick-{Path(a.video).parent.name}")
        row = bare_item(a.brand, week, label, a.by, a.why or "picked by hand", a.product, video=a.video, handle=a.author)
    else:
        raise SystemExit("say what was picked: --feed and --item, --url, or --video")
    got, new = put(a.brand, row)
    print(f"{'added' if new else 'already in'}: {got['swipe_id']}")


def cmd_fetch(a):
    brand_ok(a.brand)
    done, n = fetch(a.brand, a.label)
    print(f"videos: {done} of {n} downloaded")


def cmd_mark(a):
    brand_ok(a.brand)
    with opened(a.brand) as q:
        r = next((x for x in q["items"] if x["swipe_id"] == a.label), None)
        if not r:
            raise SystemExit(f"{a.label} is not in {a.brand}'s creator picks")
        r["state"] = a.state
        if a.approve:                  # the owner's yes on a pick
            r["status"], r["approved_at"] = "approved", D.now()
        if a.state == "dropped":
            r["status"] = "deprecated"
        if a.state in ("tearing", "torn", "failed") or a.run:
            td = r.get("teardown") or {"label": a.label}
            if a.state in ("tearing", "torn", "failed"):
                td["state"] = a.state
            if a.run:
                td["run"] = rel(a.run) if Path(a.run).is_absolute() else a.run
            r["teardown"] = td
        if not r.get("video"):          # a teardown path already downloaded it
            v = [x for x in media_dir(a.label).glob("video.*") if x.suffix.lower() in VIDEO_EXT] \
                if media_dir(a.label).exists() else []
            if v:
                r["video"] = rel(v[0])
        if a.brief:
            r["brief"] = rel(a.brief) if Path(a.brief).is_absolute() else a.brief
        if a.note:
            r["note"] = a.note[:500]
        r["marked_at"] = D.now()
    print(f"{a.label}: {a.state}")


def cmd_list(a):
    brand_ok(a.brand)
    rows = [r for r in items(a.brand) if not a.week or r.get("week") == a.week]
    # brief writing keeps its own ledger (one writer per file); show its "briefed" here
    led = WS / "runs" / "video-writing" / a.brand / "creator-briefs.json"
    briefed = (json.loads(led.read_text()).get("briefed") or {}) if led.exists() else {}
    for r in rows:
        if r["swipe_id"] in briefed and r["state"] != "dropped":
            r["state"], r["brief"] = "briefed", briefed[r["swipe_id"]].get("brief") or r.get("brief")
    if a.json:
        return print(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"{a.brand} · {len(rows)} picks · {rel(queue_file(a.brand))}")
    for r in rows:
        print(f"  [{r['state']:7}] {r['swipe_id']}  {r.get('views') or '':>10}  {r.get('week')}  "
              f"{'video' if r.get('video') else 'no video'}  {r['source_url'] or ''}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="The one door from picked swipes to creator briefs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick", help="this week's picks from the proven sources")
    p.add_argument("--brand", required=True)
    p.add_argument("--week")
    p.add_argument("--max", type=int, default=10)
    p.add_argument("--sources", default="trendtrack,tiktok-shop", help="comma list: trendtrack, tiktok-shop")
    p.add_argument("--min-days", type=int, default=MIN_DAYS, help="days a paid ad has run to count as proven")
    p.add_argument("--floor", type=int, default=FLOOR, help="views a TikTok Shop video needs when it carries no sales")
    p.add_argument("--no-fetch", action="store_true", help="leave the videos for `fetch`")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("add", help="one pick by hand")
    p.add_argument("--brand", required=True)
    p.add_argument("--week")
    p.add_argument("--feed")
    p.add_argument("--item")
    p.add_argument("--url")
    p.add_argument("--video")
    p.add_argument("--author")
    p.add_argument("--product")
    p.add_argument("--why")
    p.add_argument("--label")
    p.add_argument("--by", default="hand", choices=["hand", "desk", "tsv", "briefs", "pick"])
    p = sub.add_parser("fetch", help="download any pick still without its video")
    p.add_argument("--brand", required=True)
    p.add_argument("--label")
    p = sub.add_parser("mark", help="move a pick along (the only way other stations write here)")
    p.add_argument("--brand", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--state", required=True, choices=STATES)
    p.add_argument("--approve", action="store_true", help="the owner's yes: status approved")
    p.add_argument("--week", help="ignored; kept so older callers still run")
    p.add_argument("--run")
    p.add_argument("--brief")
    p.add_argument("--note")
    p = sub.add_parser("list", help="the brand's queue")
    p.add_argument("--brand", required=True)
    p.add_argument("--week")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    {"pick": cmd_pick, "add": cmd_add, "fetch": cmd_fetch, "mark": cmd_mark, "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    main()
