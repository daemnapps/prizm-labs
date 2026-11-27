"""`gather.py person`: fill ONE person's profile from Reddit, YouTube and TikTok (owner, 2026-11-25).

    gather.py person --brand B --avatar A --sub S --plan               the searches and the price; spends nothing
    gather.py person --brand B --avatar A --sub S --pull --cap 2 --go "<the owner's words>"
    gather.py person --brand B --avatar A --sub S --file rows.json     rows pulled another way (id, text, src, url), same filing

The searches come from what the person's profile does not know yet (creative-strategist who.py), never from the card's
own phrases. A pull needs the owner's words and stops at the cap: each platform's share is enforced by the actor itself
(maxTotalChargeUsd). Every line is filed with its permalink under runs/research/<brand>/person-<sub>-<date>/rows.json,
the dataset the profile reads; brands/ is never written.
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import engine

HOME = Path(__file__).resolve().parents[1]
# dollars per run, at most; they add up to the cap of a full pull ($1.90). TikTok's scrapers refuse a limit under $0.50.
DOLLARS = {"reddit": .25, "yt_search": .1, "yt_comments": .5, "tt_search": .5, "tt_comments": .5}
# 2026-11-25: trudax~reddit-scraper-lite, the old Reddit door, now refuses every search without a session token.
ACTORS = {"reddit": "harshmaur~reddit-scraper", "yt_search": "streamers~youtube-scraper", "yt_comments": "streamers~youtube-comments-scraper",
          "tt_search": "clockworks~tiktok-scraper", "tt_comments": "clockworks~tiktok-comments-scraper"}


PRICE = DOLLARS["reddit"] * 2 + sum(v for k, v in DOLLARS.items() if k != "reddit")      # two rooms


def who():
    p = str(engine.WORKSPACE / "components" / "creative-strategist" / "machine")
    if p not in sys.path:
        sys.path.append(p)
    import who as W
    return W


def folder(brand, sub, when=None):
    return engine.WORKSPACE / "runs" / "research" / brand / ("person-%s-%s" % (sub, when or dt.date.today().isoformat()))


def plan(brand, avatar, sub, caller=None):
    W = who()
    key = W.resolve(brand, avatar, sub)[0]
    person, missing, lines = W.unknowns(brand, avatar, key)
    p = (HOME / "prompts" / "person-queries-v1.md").read_text()
    for k, v in {"person": person, "missing": "\n".join("- " + x for x in missing) or "- everything beyond the lines below", "lines": "\n".join('- "%s"' % x for x in lines[:14]) or "- none yet"}.items():
        p = p.replace("{" + k + "}", v)
    d = W.S.parse(W.S.ask_model(p, caller=caller))
    d["sub"], d["missing"], d["where"] = key, missing, W.spot(brand, avatar, key)
    return d


SPENT = []


def capped(actor, payload, dollars, timeout=900):
    """One paid run, never past `dollars` (the platform enforces it): start it, wait, read what it found. A run that
    stops at its cap still hands back its lines. What it cost is kept in SPENT."""
    ap = engine.apify_layer()

    def api(tok, url, body=None):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403):
                raise
            raise RuntimeError("%s: %s" % (e.code, e.read().decode(errors="replace")[:200]))

    def call(tok):
        run = api(tok, "%s/acts/%s/runs?maxTotalChargeUsd=%.2f&timeout=%d" % (ap.API, actor, dollars, timeout), payload)["data"]
        t0 = time.time()
        while run["status"] in ("READY", "RUNNING", "TIMING-OUT", "ABORTING") and time.time() - t0 < timeout + 120:
            time.sleep(8)
            run = api(tok, "%s/actor-runs/%s" % (ap.API, run["id"]))["data"]
        SPENT.append({"actor": actor, "run": run["id"], "state": run["status"], "usd": run.get("usageTotalUsd")})
        rows = api(tok, "%s/datasets/%s/items?clean=true" % (ap.API, run["defaultDatasetId"])) or []
        if not rows and run["status"] != "SUCCEEDED":
            raise RuntimeError("%s %s" % (run["status"], run.get("statusMessage") or ""))
        return rows
    return ap.each_account(call)


def line(text, src, url, likes=None, date=None):
    return {"text": " ".join(str(text or "").split())[:1200], "src": src, "url": url, "likes": likes, "date": date}


def pull(p, cap, run=capped):
    """[lines], [what could not be read]. Every platform is tried; one that fails is named and the rest go on."""
    out, notes, left = [], [], cap

    def spend(k, payload):
        nonlocal left
        if left < DOLLARS[k]:
            raise RuntimeError("the cap is reached")
        left -= DOLLARS[k]
        return run(ACTORS[k], payload, DOLLARS[k])
    try:
        if "reddit" not in p:
            raise KeyError("not asked for")
        q, rows = p["reddit"]["searches"], []
        for room in (p["reddit"].get("rooms") or [""])[:2]:          # inside the rooms where they are: a search of all of Reddit wanders
            rows += spend("reddit", {"searchTerms": q[:6], **({"withinCommunity": room} if room else {}), "searchPosts": True, "searchComments": True, "searchSort": "relevance", "searchTime": "all",
                                     "crawlCommentsPerPost": True, "maxPostsCount": 5, "maxCommentsCount": 25, "maxCommentsPerPost": 6, "includeNSFW": False})
        for r in map(engine.reddit_door().as_row, rows):
            t = " — ".join(x for x in (r.get("title"), r.get("body") or r.get("text") or r.get("selftext")) if x)
            out.append(line(t, "reddit r/%s" % re.sub(r"^r/", "", str(r.get("parsedCommunityName") or r.get("communityName") or r.get("subreddit") or "")), r.get("url"), r.get("upVotes"), r.get("createdAt")))
    except Exception as e:  # noqa: BLE001
        notes.append("reddit: %s" % str(e)[:160])
    for plat, sk, ck, sp, cp, url_of, row in (
            ("youtube", "yt_search", "yt_comments", lambda q: {"searchQueries": q, "maxResults": 3, "maxResultsShorts": 2, "maxResultStreams": 0}, lambda u: {"startUrls": [{"url": x} for x in u], "maxComments": 40, "sortCommentsBy": "TOP_COMMENTS"},
             lambda r: r.get("url"), lambda c: line(c.get("comment") or c.get("text"), "youtube comment", "%s&lc=%s" % (c.get("pageUrl") or c.get("videoUrl") or "https://www.youtube.com/watch?v=" + str(c.get("videoId")), c.get("cid") or c.get("commentId") or ""), c.get("voteCount") or c.get("likes"), c.get("publishedTimeText"))),
            ("tiktok", "tt_search", "tt_comments", lambda q: {"searchQueries": q, "resultsPerPage": 6, "shouldDownloadVideos": False, "shouldDownloadCovers": False}, lambda u: {"postURLs": u, "commentsPerPost": 50, "maxRepliesPerComment": 0},
             lambda r: r.get("webVideoUrl"), lambda c: line(c.get("text"), "tiktok comment", c.get("videoWebUrl"), c.get("diggCount"), c.get("createTimeISO")))):
        try:
            found = [u for u in (url_of(r) for r in spend(sk, sp(p[plat]["searches"]))) if u]
            out += [row(c) for c in spend(ck, cp(list(dict.fromkeys(found))[:16]))] if found else []
        except Exception as e:  # noqa: BLE001
            notes.append("%s: %s" % (plat, str(e)[:160]))
    return [x for x in out if len(x["text"]) >= 15 and x["url"]], notes


def file_rows(brand, avatar, sub, lines, note=""):
    """Every line in the bank's own shape, with its permalink; a line already filed is not filed twice."""
    d = folder(brand, sub)
    f = d / "rows.json"
    had = json.loads(f.read_text())["entries"] if f.is_file() else []
    seen = {(x["text"], x["source"]["ref"]) for x in had}
    for x in lines:
        if (x["text"], x["url"]) in seen:
            continue
        seen.add((x["text"], x["url"]))
        had.append({"id": "research_%s_%s_%04d" % (sub, dt.date.today().strftime("%Y%m%d"), len(had) + 1), "text": x["text"], "avatar": avatar, "sub": sub, "funnel": "prospect", "speaker": "prospect",
                    "source": {"name": x["src"], "type": "community", "date": str(x.get("date") or ""), "ref": x["url"]}, "signal": {"likes": x.get("likes"), "tier": "community"}, "topics": [], "use": [], "status": "active", "origin": "external"})
    d.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"schema": 1, "brand": brand, "avatar": avatar, "sub": sub, "note": note, "entries": had}, indent=1, ensure_ascii=False) + "\n")
    return f, len(had)


def record(brand, avatar, sub, cap, go, lines, notes):
    f = folder(brand, sub) / "run.json"
    if f.is_file():
        SPENT[:0] = [x for x in json.loads(f.read_text()).get("spent") or [] if x not in SPENT]
    f.write_text(json.dumps({"brand": brand, "avatar": avatar, "sub": sub, "cap": cap, "go": go, "lines": len(lines), "could_not_read": notes, "spent": SPENT,
                             "usd": round(sum(x["usd"] or 0 for x in SPENT), 3), "date": dt.date.today().isoformat()}, indent=1) + "\n")
    SPENT.clear()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gather.py person", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("brand", "avatar", "sub"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--cap", type=float)
    ap.add_argument("--go", help="the owner's words for this pull")
    ap.add_argument("--only", nargs="*", help="reddit youtube tiktok: just these")
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    W = who()
    key, card, _, _ = W.resolve(a.brand, a.avatar, a.sub)
    avatar, _ = W.N.canon(a.brand, a.avatar)
    d = folder(a.brand, key)
    if a.file:
        rows = json.loads(Path(a.file).read_text())
        print(*file_rows(a.brand, avatar, key, list(rows.values()) if isinstance(rows, dict) else rows))
        return 0
    if a.plan:
        p = plan(a.brand, avatar, key)
        d.mkdir(parents=True, exist_ok=True)
        (d / "plan.json").write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
        print(json.dumps(p, indent=1, ensure_ascii=False))
        return 0
    if a.pull:
        if not a.cap or not a.go:
            raise SystemExit("refused: a pull needs --cap <dollars> and --go \"<the owner's words>\"")
        p = json.loads((d / "plan.json").read_text())
        lines, notes = pull({k: v for k, v in p.items() if not a.only or k not in ("reddit", "youtube", "tiktok") or k in a.only}, a.cap)
        f, n = file_rows(a.brand, avatar, key, lines, "go: %s; cap $%.2f" % (a.go, a.cap))
        record(a.brand, avatar, key, a.cap, a.go, lines, notes)
        print(f, n, notes)
        return 0
    ap.print_help()
    return 2
