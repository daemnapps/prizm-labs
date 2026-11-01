#!/usr/bin/env python3
"""The research round for any avatar — evidence, plan with the coverage gate, pull, rank, file.

    round.py worlds --brand <b> --avatar <a> --label <l>     what his feeds already show (free)
    round.py plan   --brand <b> --avatar <a> --label <l> --search "..." --search "..." [--max 85]
    round.py pull   --brand <b> --avatar <a> --label <l> --approved-by <name>
    round.py rank   --brand <b> --avatar <a> --label <l> [--top 50] [--since 2026-01-01]

The order and the why are RESEARCH-ROUND.md (the owner, 2026-10-17). Every run lives in
runs/swipe-organic/<brand>/research-<avatar>-<label>/. Between `worlds` and `plan` the
session writes worlds.json there — his worlds, biggest first, each with the posts
that carry it and the keywords a search must contain to cover it:

    [{"world": "NBA / NFL", "count": 106, "keywords": ["nba", "nfl", "basketball"]}, ...]

`plan` holds (exit 1) while any of his top worlds has no search: the coverage gate.
`pull` refuses a plan that is held, or one nobody approved. Nothing here names a brand.
"""
import argparse, json, os, re, socket, statistics, subprocess, sys, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import desklib as D  # noqa: E402  (FEEDS = records/avatar-feeds)

REPO = HERE.parents[1]
TIKTOK = REPO / "components" / "apify" / "tiktok.py"
PER_ROW = 0.0035                      # the trends door's price per row (components/apify/tiktok.py)
NOISE = {"fyp", "foryou", "foryoupage", "viral", "fy", "fypシ", "fypシ゚viral", "trending", "explore",
         "reels", "parati", "xyzbca", "foru", "viralvideo", "tiktok", "funny", "fypage", "blowthisup"}


def home(a):
    for v in (a.brand, a.avatar, a.label):
        if not v or "/" in v or v.startswith("."):
            raise SystemExit(f"REFUSED: {v!r} cannot name a folder")
    return REPO / "runs" / "swipe-organic" / a.brand / f"research-{a.avatar}-{a.label}"


def items_of(feed_dir):
    d = json.loads((feed_dir / "items.json").read_text())
    it = d.get("items", d) if isinstance(d, dict) else d
    return list(it.values()) if isinstance(it, dict) else it


# ---- 1. what his feeds already show -------------------------------------------------
def worlds(a):
    out = home(a)
    out.mkdir(parents=True, exist_ok=True)
    feeds = sorted(p for p in D.FEEDS.glob(f"{a.brand}--{a.avatar}*") if (p / "items.json").exists())
    if not feeds:
        raise SystemExit(f"no feeds for {a.brand}--{a.avatar} in My Feeds — dig one first")
    tags, kinds, n = Counter(), Counter(), 0
    for f in feeds:
        for x in items_of(f):
            if "research round" in (x.get("receipt") or ""):
                continue              # a round's own pull is not evidence of what he watches
            n += 1
            for h in {t.lower().lstrip("#") for t in (x.get("hashtags") or [])}:
                if h and h not in NOISE:
                    tags[h] += 1
            kinds[(x.get("sift") or {}).get("kind") or "?"] += 1
    prof = REPO / "brands" / a.brand / "core-avatars" / a.avatar / "profile.md"
    lines = [l.strip() for l in prof.read_text().splitlines()
             if re.search(r"creator|show|sport|music|watch|cultur|follow|scroll", l, re.I)] if prof.exists() else []
    ev = {"brand": a.brand, "avatar": a.avatar, "feeds": [f.name for f in feeds], "posts": n,
          "top_hashtags": tags.most_common(40), "kinds": kinds.most_common(), "profile_lines": lines[:20]}
    (out / "evidence.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False))
    print(f"{n} posts in {len(feeds)} feeds: {', '.join(f.name for f in feeds)}")
    print("top hashtags:", ", ".join(f"{t} {c}" for t, c in tags.most_common(30)))
    print("kinds:", ", ".join(f"{k} {c}" for k, c in kinds.most_common()))
    for l in lines[:12]:
        print("profile:", l[:160])
    print(f"\nNext: write {out / 'worlds.json'} — his worlds, biggest first, with keywords. Then `plan`.")


# ---- 2. the plan and the coverage gate ----------------------------------------------
def coverage(ws, searches, top):
    """Each of his top worlds -> the searches that cover it (a keyword inside the search)."""
    low = [s.lower() for s in searches]
    return [{**w, "covered_by": [s for s in searches if any(k.lower() in s.lower() for k in w["keywords"])]}
            for w in ws[:top]], low


def plan(a):
    out = home(a)
    wf = out / "worlds.json"
    if not wf.exists():
        raise SystemExit(f"HELD: no {wf} — run `worlds` and write his worlds first (step 1)")
    ws = json.loads(wf.read_text())
    if not ws or not all(w.get("keywords") for w in ws):
        raise SystemExit("HELD: every world in worlds.json needs keywords")
    cov, _ = coverage(ws, a.search, a.top_worlds)
    missing = [w["world"] for w in cov if not w["covered_by"]]
    rows = a.max * len(a.search)
    p = {"brand": a.brand, "avatar": a.avatar, "label": a.label, "searches": a.search, "max": a.max,
         "rows": rows, "cap_usd": round(rows * PER_ROW, 2), "coverage": cov,
         "ask": a.ask, "keep_rule": a.keep_rule, "drop_rule": a.drop_rule,
         "keep_lanes": [x.strip() for x in a.lanes.split(",") if x.strip()],
         "state": "held" if missing else "ready", "missing": missing,
         "made": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / "plan.json").write_text(json.dumps(p, indent=1, ensure_ascii=False))
    for w in cov:
        print(f"  {'✓' if w['covered_by'] else '✕'} {w['world']} ({w.get('count', '?')}) ← {', '.join(w['covered_by']) or 'NO SEARCH'}")
    print(f"{len(a.search)} searches × {a.max} = {rows} posts · cap ${p['cap_usd']}")
    if not a.ask:
        raise SystemExit("HELD: --ask says whose scroll this is and what the round is for (My Feeds sorts every post against it)")
    if missing:
        raise SystemExit(f"HELD (coverage gate): no search for {', '.join(missing)}. Add one per world, then plan again.")
    print("READY — show this plan and the price, and wait for the yes.")


# ---- 3. the pull, only on a ready plan someone approved ------------------------------
def pull(a):
    out = home(a)
    p = json.loads((out / "plan.json").read_text()) if (out / "plan.json").exists() else None
    if not p:
        raise SystemExit("REFUSED: no plan.json — run `plan` first")
    if p["state"] != "ready":
        raise SystemExit(f"REFUSED: the plan is held — no search for {', '.join(p['missing'])}")
    if not a.approved_by:
        raise SystemExit("REFUSED: --approved-by names who said go (credits are spent on a person's yes)")
    p["approved"] = {"by": a.approved_by, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / "plan.json").write_text(json.dumps(p, indent=1, ensure_ascii=False))
    cmd = [sys.executable, str(TIKTOK), "trends", "--mode", "search_keyword", "--max", str(p["max"]),
           "--out", str(out), "--q", *p["searches"]]
    env = dict(os.environ, RESEARCH_ROUND_PLAN=str(out / "plan.json"))
    raise SystemExit(subprocess.call(cmd, env=env))


# ---- 4. rank, thumbnails, file into My Feeds ----------------------------------------
def k(n):
    n = n or 0
    return f"{n / 1e6:.1f}M" if n >= 1e6 else (f"{n / 1e3:.0f}K" if n >= 1e3 else str(n))


def thumb(x, dest):
    if dest.exists() and dest.stat().st_size > 1000:
        return True
    socket.setdefaulttimeout(12)
    for get in (lambda: x.get("thumbnailUrl") or x.get("videoCoverUrl"),
                lambda: json.load(urllib.request.urlopen("https://www.tiktok.com/oembed?url=" + x["url"]))["thumbnail_url"]):
        try:
            u = get()
            data = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})).read()
            if len(data) > 1000:
                dest.write_bytes(data)
                return True
        except Exception:  # noqa: BLE001 — a missing thumbnail shows as "no preview"
            pass
    return False


def rank(a):
    out = home(a)
    rows = json.loads((out / "rows.json").read_text())
    since = a.since or f"{datetime.now().year}-01-01"
    seen, old = {}, set()
    for x in rows:
        if x.get("rowType") != "video" or x.get("isAd") or x.get("videoId") in seen:
            continue
        if (x.get("postedAt") or "") < since:
            old.add(x.get("videoId"))
            continue
        x["score"] = sum(int(x.get(f) or 0) for f in ("viewCount", "likeCount", "commentCount"))
        seen[x["videoId"]] = x
    ranked = sorted(seen.values(), key=lambda x: -x["score"])
    top = ranked[:a.top]
    for i, x in enumerate(top, 1):
        x["rank"] = i
    by = defaultdict(list)
    for x in ranked:
        by[x["sourceQuery"]].append(x)
    c = Counter(x["sourceQuery"] for x in top)
    med = {q: int(statistics.median([y.get("viewCount") or 0 for y in xs])) for q, xs in by.items()}
    order = sorted(by, key=lambda q: (-c[q], -med[q]))
    (out / "thumbs").mkdir(exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(lambda x: thumb(x, out / "thumbs" / f"{x['videoId']}.jpg"), top))
    keep = ["rank", "score", "viewCount", "likeCount", "commentCount", "shareCount", "saveCount", "sourceQuery",
            "authorHandle", "caption", "hashtags", "duration", "postedAt", "url", "videoId"]
    res = {"since": since, "dropped_old": len(old), "kept": len(ranked), "top_n": a.top,
           "formats": [{"search": q, "in_top": c[q], "posts": len(by[q]), "median_views": med[q],
                        "best_views": max(y.get("viewCount") or 0 for y in by[q])} for q in order],
           "top": [{f: x.get(f) for f in keep} for x in top]}
    (out / "ranking.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"{len(ranked)} posts from {since} on ({len(old)} older dropped) · top {a.top} · thumbnails {sum(got)}/{len(top)}")
    for i, q in enumerate(order, 1):
        print(f"  {i:2d}. {q:28s} {c[q]:3d} in top {a.top} · median {k(med[q])} · best {k(max(y.get('viewCount') or 0 for y in by[q]))}")
    file_feed(a, out, ranked)


def file_feed(a, out, ranked):
    """Every kept post into My Feeds as its own feed under the avatar, keyed the way desklib reads it."""
    d = D.FEEDS / f"{a.brand}--{a.avatar}-{a.label}"
    (d / "covers").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    receipt = f"research round {a.label} (RESEARCH-ROUND.md)"
    items = {}
    for x in ranked:
        items[f"tiktok:{x['videoId']}"] = {
            "platform": "tiktok", "id": x["videoId"], "url": x["url"], "author": x.get("authorHandle"),
            "followers": None, "posted": x.get("postedAt"), "caption": x.get("caption") or "",
            "hashtags": x.get("hashtags") or [], "cover": x.get("thumbnailUrl"), "kind": "video",
            "source": f"tt-search={x['sourceQuery']}", "receipt": receipt, "first_seen": now, "category": None,
            "status": "fresh"}
        t = out / "thumbs" / f"{x['videoId']}.jpg"
        if t.exists():
            (d / "covers" / t.name).write_bytes(t.read_bytes())
    old = json.loads((d / "items.json").read_text()).get("items", {}) if (d / "items.json").exists() else {}
    (d / "items.json").write_text(json.dumps({"items": {**old, **items}}, indent=1, ensure_ascii=False))
    with (d / "observations.jsonl").open("a") as f:
        for x in ranked:
            f.write(json.dumps({"item": f"tiktok:{x['videoId']}", "at": now, "views": x.get("viewCount"),
                                "likes": x.get("likeCount"), "comments": x.get("commentCount"),
                                "shares": x.get("shareCount"), "saves": x.get("saveCount")}) + "\n")
    p = json.loads((out / "plan.json").read_text())
    (d / "sources.json").write_text(json.dumps({
        "brand": a.brand, "avatar": a.avatar, "core": a.avatar, "kind": "research-round", "languages": ["en", "none"],
        "title": f"{a.avatar} · research {a.label}", "ask": p.get("ask") or "", "keep_rule": p.get("keep_rule") or "",
        "drop_rule": p.get("drop_rule") or "",
        "keep_lanes": p.get("keep_lanes") or ["entertainment", "educational", "selling"],
        "sources": [{"kind": "search", "platform": "tiktok", "value": s, "receipt": receipt} for s in p["searches"]]},
        indent=1, ensure_ascii=False))
    (d / "plan.json").write_text(json.dumps({"NAME": a.label, "TITLE": f"{a.avatar} · research {a.label}",
                                             "TIKTOK_SEARCHES": p["searches"]}, indent=1))
    with (d / "sweeps.jsonl").open("a") as f:
        f.write(json.dumps({"at": now, "sources": len(p["searches"]), "observed": len(ranked), "new": len(items),
                            "catalog": len(items), "errors": [], "note": f"research round, {out.relative_to(REPO)}"}) + "\n")
    print(f"filed {len(items)} posts into My Feeds: {d.name} — sorting them into entertainment / educational / selling")
    # My Feeds' own reader sorts every post into its side (sift.py, prompt feed-sift-v3); a round never labels them itself
    subprocess.call([sys.executable, str(HERE / "sift.py"), "--avatar", d.name], cwd=str(HERE))
    cat = json.loads((d / "items.json").read_text())["items"]
    lanes = Counter((cat.get(f"tiktok:{x['videoId']}", {}).get("sift") or {}).get("lane", "unsorted") for x in ranked[:a.top])
    print(f"top {a.top} by side: " + ", ".join(f"{k} {v}" for k, v in lanes.most_common()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["worlds", "plan", "pull", "rank"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True, help="the core avatar's folder name under brands/<brand>/core-avatars/")
    ap.add_argument("--label", required=True, help="this round's name, e.g. 2026-10-17-sports")
    ap.add_argument("--search", action="append", default=[], help="one search (repeat)")
    ap.add_argument("--max", type=int, default=85, help="posts per search")
    ap.add_argument("--top-worlds", type=int, default=5, help="how many of his top worlds must be covered")
    ap.add_argument("--approved-by", help="who said go")
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--ask", help="whose scroll and what this round is for, in a sentence (plan)")
    ap.add_argument("--keep-rule", default="", help="what a post must be to stay (plan)")
    ap.add_argument("--drop-rule", default="", help="what gets thrown out (plan)")
    ap.add_argument("--lanes", default="entertainment,educational,selling", help="sides this round keeps (plan)")
    ap.add_argument("--since", help="earliest post date kept (default 1 Jan this year)")
    a = ap.parse_args()
    {"worlds": worlds, "plan": plan, "pull": pull, "rank": rank}[a.step](a)


if __name__ == "__main__":
    main()
