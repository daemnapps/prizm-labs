#!/usr/bin/env python3
"""The creative matrix for any avatar — hooks × moments × bodies, every category and video clickable.

    matrix.py --brand <b> --avatar <a> --hooks <round>[,<round>] --problem <round> [--out <dir>]

Rounds are research rounds (round.py) under runs/swipe-organic/<brand>/research-<avatar>-<label>/;
pass the labels. It reads, never writes, the rounds:
  hooks    — the formats he watches: his posts from those rounds, 2026+, his top 3 searches by how
             many of their posts made his top 50 (typical views break ties)
  moments  — the problem round's worlds.json (his worlds, with counts), each shown with lines in
             his own words from brands/<b>/core-avatars/<a>/language/ that carry its keywords
  bodies   — the problem round's kept posts (My Feeds' sorter), grouped by what kind of post it is
The written concepts come from concepts.json in the out folder (a session writes it; a cell
without one shows its evidence and "not written yet"). Writes index.html + t/<id>.jpg into
runs/swipe-organic/<b>/matrix-<a>/ (or --out). Nothing here names a brand. RESEARCH-ROUND.md step 8.
"""
import argparse, glob, html, json, re, shutil, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import desklib as D  # noqa: E402

# what kind of post a body is, from My Feeds' sorter (sift "kind") — the post's shape, not its topic
BODY_OF = {"tutorial": "howto", "tips": "howto", "explainer": "howto", "routine": "routine",
           "pitch": "pitch", "review": "storytime", "storytime": "storytime", "reaction": "reaction",
           "satisfying": "satisfying", "monologue": "reaction", "skit": "skit", "meme": "reaction"}
BODY_NAME = {"howto": "The how-to", "routine": "The routine", "pitch": "The pitch", "storytime": "The storytime",
             "reaction": "The reaction / complaint", "satisfying": "The satisfying clip", "skit": "The skit"}


def rdir(brand, avatar, label):
    d = REPO / "runs" / "swipe-organic" / brand / f"research-{avatar}-{label}"
    if not (d / "rows.json").exists():
        raise SystemExit(f"no round at {d} — run round.py first")
    return d


def posts(rows, sift=None):
    seen = {}
    for x in rows:
        if x.get("rowType") != "video" or x.get("isAd") or x.get("videoId") in seen:
            continue
        if (x.get("postedAt") or "") < "2026-01-01":
            continue
        s = ((sift or {}).get(f"tiktok:{x['videoId']}") or {}).get("sift") or {}
        if sift is not None and not s.get("keep"):
            continue
        x = dict(x, score=sum(int(x.get(f) or 0) for f in ("viewCount", "likeCount", "commentCount")),
                 lane=s.get("lane"), kind=s.get("kind"), what=s.get("what"))
        seen[x["videoId"]] = x
    return sorted(seen.values(), key=lambda x: -x["score"])


def thumb_for(brand, vid, out):
    dst = out / "t" / f"{vid}.jpg"
    if dst.exists():
        return True
    pats = [str(REPO / "runs" / "swipe-organic" / brand / "*" / "thumbs*" / f"{vid}.jpg"),
            str(D.FEEDS / f"{brand}--*" / "covers" / f"{vid}.jpg")]
    for pat in pats:
        for f in glob.glob(pat):
            if Path(f).stat().st_size > 1000:
                shutil.copy(f, dst)
                return True
    return False


def card(x):
    return {"id": x["videoId"], "url": x["url"], "author": x.get("authorHandle"), "posted": (x.get("postedAt") or "")[:10],
            "views": x.get("viewCount"), "likes": x.get("likeCount"), "comments": x.get("commentCount"),
            "shares": x.get("shareCount"), "caption": x.get("caption") or "", "lane": x.get("lane"),
            "what": x.get("what"), "search": x.get("sourceQuery")}


def lines_for(brand, avatar, keywords, n=12):
    out = []
    for f in glob.glob(str(REPO / "brands" / brand / "core-avatars" / avatar / "language" / "**" / "*.json"), recursive=True):
        try:
            d = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for e in (d.get("entries") if isinstance(d, dict) else None) or []:
            t = (e or {}).get("text") or ""
            if 30 < len(t) < 180 and any(k.lower() in t.lower() for k in keywords):
                out.append({"text": t, "who": e.get("funnel") or e.get("speaker") or ""})
    seen, keep = set(), []
    for l in sorted(out, key=lambda l: len(l["text"])):
        if l["text"].lower() not in seen:
            seen.add(l["text"].lower())
            keep.append(l)
    return keep[:n], len(out)


TYPES = [  # creative type -> the make job that writes its brief (components/funnel-tracking ASKS.md)
    {"id": "video-ad", "name": "Video ad", "action": "make-ad-videos"}, {"id": "image-ad", "name": "Image ad", "action": "make-ad-images"},
    {"id": "carousel", "name": "Carousel", "action": "make-ad-images"}, {"id": "email", "name": "Email", "action": "make-emails"},
    {"id": "landing-page", "name": "Landing page", "action": "make-landing-page"}]


def controls(brand):
    """What the matrix's dials offer for a brand: its products, its live offers, every avatar, the swipe sources."""
    offers = []
    boards = sorted(glob.glob(str(REPO / "runs" / "offer-board" / "all-brands" / "*" / "board.json")))
    if boards:
        try:
            for b in json.loads(Path(boards[-1]).read_text()).get("brands", []):
                if b.get("brand") == brand:
                    offers = [{"id": o["id"], "name": o.get("name") or o["id"], "status": o.get("status"),
                               "sign": (o.get("math") or {}).get("sign")} for o in b.get("offers", []) if o.get("status") in ("live", "test", None)]
        except (OSError, ValueError):
            pass
    # products = what the brand's offers sell (runs/business-review/offer-products.json, kept fresh by the owner's Outlier)
    prods = []
    try:
        _op = REPO / "runs" / "business-review" / "offer-products.json"
        if not _op.is_file():
            _op = REPO / "lab" / "owner" / "business-review" / "definitions" / "offer-products.json"
        op = json.loads(_op.read_text())["offers"]
        for o in offers:
            for pr in (op.get(o["id"]) or {}).get("products", []):
                if pr not in prods:
                    prods.append(pr)
    except (OSError, ValueError, KeyError):
        pass
    avatars = []
    for d in sorted(glob.glob(str(REPO / "brands" / "*" / "core-avatars" / "*" / "profile.md"))):
        av, br = Path(d).parent.name, Path(d).parents[2].name
        avatars.append({"brand": br, "avatar": av, "built": (REPO / "runs" / "swipe-organic" / br / f"matrix-{av}" / "index.html").exists()})
    paid = sorted(p.name for p in (HERE.parent / "swipe-paid").iterdir() if p.is_dir() and (p / "blocks.json").exists()) if (HERE.parent / "swipe-paid").is_dir() else []
    sources = [{"id": "organic", "name": "His organic formats (research rounds)"},
               {"id": "paid", "name": f"Competitor paid swipes ({len(paid)} advertisers)"},
               {"id": "ours", "name": "Our proven winners"}]
    return {"products": prods, "offers": offers, "avatars": avatars, "sources": sources, "types": TYPES}


def make(body):
    """The matrix's Make brief: one concept (hook × moment × body) with its dials -> a make job whose brief lands in
    the Queue at Brief · needs you. The job writes the BRIEF only (the outlier-brief skill); nothing is produced or spent."""
    t = next((x for x in TYPES if x["id"] == body.get("type")), None)
    for k in ("brand", "avatar", "hook", "moment"):
        if not body.get(k):
            raise ValueError(f"pick a {k} first")
    if not t:
        raise ValueError("pick a creative type")
    sys.path.insert(0, str(REPO / "components" / "funnel-tracking" / "machine"))
    import asks as K
    c = body.get("concept") or {}
    title = c.get("title") or f"{body['hook']} × {body['moment']}"
    note = (f"From the creative matrix (Outlier → Create). Write the BRIEF for this one concept and stop for the owner's OK — "
            f"use the outlier-brief skill (.claude/skills/outlier-brief) and file it in the brief register so it shows in the "
            f"Queue at Brief · needs you. Do not make the finished {t['name'].lower()} and spend nothing. "
            f"Concept: {title}. {c.get('idea') or ''} Type: {t['name']}. Avatar: {body['avatar']}. "
            f"Product: {body.get('product') or 'the brand default'}. Offer: {body.get('offer') or 'the brand default'}. "
            f"Swipe source: {body.get('source') or 'organic'}.")
    make_row = {"from": "matrix", "concept": title, "idea": c.get("idea"), "beats": {k: c.get(k) for k in ("open", "turn", "cut")},
                "angle": c.get("angle"), "hook": body["hook"], "moment": body["moment"], "body": body.get("body"),
                "body_how": body.get("body_how"), "type": t["id"], "avatar": body["avatar"], "product": body.get("product"),
                "offer": body.get("offer"), "source": body.get("source"), "lines": body.get("lines") or [],
                "proof": body.get("proof") or []}
    r = K.add_ask({"brand": body["brand"], "ad": f"matrix · {title}"[:300], "action": t["action"], "note": note, "make": make_row})
    return {"ok": True, "said": f"Brief job filed: {title} as a {t['name'].lower()}. It writes the brief and stops for your OK in the Queue.",
            "ask": r.get("id") if isinstance(r, dict) else None}


def build(a):
    out = Path(a.out) if a.out else REPO / "runs" / "swipe-organic" / a.brand / f"matrix-{a.avatar}"
    (out / "t").mkdir(parents=True, exist_ok=True)
    C = json.loads((out / "concepts.json").read_text()) if (out / "concepts.json").exists() else {}
    names = C.get("names", {})

    # hooks
    hook_rows = []
    for lab in a.hooks.split(","):
        hook_rows += json.loads((rdir(a.brand, a.avatar, lab) / "rows.json").read_text())
    hp = posts(hook_rows)
    top = hp[:50]
    cnt = Counter(x["sourceQuery"] for x in top)
    by = defaultdict(list)
    for x in hp:
        by[x["sourceQuery"]].append(x)
    med = {q: int(statistics.median([y.get("viewCount") or 0 for y in xs])) for q, xs in by.items()}
    order = sorted(by, key=lambda q: (-cnt[q], -med[q]))[:a.n_hooks]
    hooks = [{"id": q, "name": names.get(q, q), "in_top": cnt[q], "posts": len(by[q]), "median": med[q],
              "best": max(y.get("viewCount") or 0 for y in by[q]), "videos": [card(x) for x in by[q][:8]]} for q in order]

    # moments + bodies
    pd = rdir(a.brand, a.avatar, a.problem)
    worlds = json.loads((pd / "worlds.json").read_text())
    feed = D.FEEDS / f"{a.brand}--{a.avatar}-{a.problem}"
    sift = json.loads((feed / "items.json").read_text())["items"] if (feed / "items.json").exists() else {}
    pp = posts(json.loads((pd / "rows.json").read_text()), sift)
    moments = []
    for w in worlds[:a.n_moments]:
        ls, total = lines_for(a.brand, a.avatar, w["keywords"])
        vids = [card(x) for x in pp if any(k.lower() in ((x.get("caption") or "") + " " + x["sourceQuery"]).lower() for k in w["keywords"])][:8]
        moments.append({"id": w["world"], "name": names.get(w["world"], w["world"]), "count": w.get("count"),
                        "lines": ls, "lines_total": total, "keywords": w["keywords"], "videos": vids})
    groups = defaultdict(list)
    for x in pp[:a.body_pool]:
        g = BODY_OF.get((x.get("kind") or "").lower())
        if g and g not in C.get("exclude_bodies", []):
            groups[g].append(x)
    gorder = sorted(groups, key=lambda g: -sum(y.get("viewCount") or 0 for y in groups[g][:5]))[:a.n_bodies]
    bodies = [{"id": g, "name": names.get(g, BODY_NAME.get(g, g)), "posts": len(groups[g]),
               "lanes": dict(Counter(y.get("lane") for y in groups[g])),
               "best": max(y.get("viewCount") or 0 for y in groups[g]), "videos": [card(x) for x in groups[g][:8]]} for g in gorder]

    got = 0
    for grp in (hooks, moments, bodies):
        for o in grp:
            for v in o["videos"]:
                v["img"] = thumb_for(a.brand, v["id"], out)
                got += v["img"]
    data = {"brand": a.brand, "avatar": a.avatar, "title": C.get("title") or f"{a.avatar} creative matrix",
            "lane": C.get("lane", ""), "product": C.get("product", ""), "hooks": hooks, "moments": moments,
            "bodies": bodies, "concepts": C.get("concepts", {}), "body_how": C.get("body_how", {}),
            "top": C.get("top", []), "notes": C.get("notes", []), "controls": controls(a.brand),
            "default_product": C.get("product", ""),
            "sources": {"hooks": a.hooks, "problem": a.problem, "hook_posts": len(hp), "problem_posts": len(pp)}}
    page = (HERE / "matrix.html").read_text()
    title = html.escape(data["title"])
    page = page.replace("{{TITLE}}", title).replace("{{DATA}}", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (out / "index.html").write_text(page)
    print(f"{out / 'index.html'} · hooks {len(hooks)} · moments {len(moments)} · bodies {len(bodies)} · thumbnails {got}")
    for o in hooks:
        print(f"  hook   {o['name']:34s} {o['in_top']} in top 50 · median {o['median']:,}")
    for o in moments:
        print(f"  moment {o['name']:34s} {o['count']} · {o['lines_total']} lines in his words · {len(o['videos'])} videos")
    for o in bodies:
        print(f"  body   {o['name']:34s} {o['posts']} posts · {o['lanes']}")


def matrices():
    """Every matrix built so far -> [(brand, avatar, built time)]."""
    out = []
    for f in sorted((REPO / "runs" / "swipe-organic").glob("*/matrix-*/index.html")):
        out.append((f.parent.parent.name, f.parent.name[len("matrix-"):], f.stat().st_mtime))
    return out


def serve_post(path, body):
    """For My Feeds (desk.py): POST /matrix/api/make -> make(body). Returns (body, content type) or None."""
    if path == "/matrix/api/make":
        try:
            return (json.dumps(make(body)), "application/json")
        except ValueError as e:
            return (json.dumps({"error": str(e)}), "application/json")
    return None


def serve(path):
    """For My Feeds (desk.py): /matrix is the picker, /matrix/<brand>/<avatar>/ a matrix, .../t/<id>.jpg its pictures.
    Returns (body, content type) or None."""
    import time
    if path in ("/matrix", "/matrix/"):
        rows = "".join(f'<a href="/matrix/{b}/{av}/"><b>{html.escape(av)}</b><span>{html.escape(b)} · built '
                       f'{time.strftime("%d %b %H:%M", time.localtime(t))}</span></a>' for b, av, t in matrices())
        return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                "<title>Creative matrix</title><link rel=stylesheet href='https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=Jost:wght@400;500&display=swap'>"
                "<style>body{font:15px Jost,system-ui;margin:0;padding:28px 22px;background:#f5f1e8;color:#1c1a16}"
                "h1{font:300 50px 'Cormorant Garamond',serif;margin:0 0 6px}p{color:#5f584c;margin:0 0 18px;max-width:60ch}"
                "a{display:grid;gap:2px;background:#fffdf8;border:1px solid #e6dfd0;padding:12px 14px;margin-bottom:8px;color:inherit;text-decoration:none;max-width:560px}"
                "a:hover{border-color:#1f3fd6}a b{font:400 22px 'Cormorant Garamond',serif}a span{font-size:12.5px;color:#5f584c}</style><h1>Creative matrix</h1><p>Pick an avatar. Each matrix is built from that "
                "avatar's research rounds: the formats he watches, the problem in his words, and the problem videos that pull. "
                "New one: say \"research &lt;avatar&gt;\" then \"build the matrix\".</p>" + (rows or "<p>No matrix built yet.</p>"),
                "text/html; charset=utf-8")
    m = re.match(r"^/matrix/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)/(?:(t/[0-9A-Za-z_-]+\.jpg))?$", path)
    if not m:
        return None
    root = REPO / "runs" / "swipe-organic" / m.group(1) / f"matrix-{m.group(2)}"
    if m.group(3):
        f = root / m.group(3)
        return (f.read_bytes(), "image/jpeg") if f.exists() else None
    f = root / "index.html"
    if not f.exists():
        return None
    body = f.read_text()
    # the page's code is always today's matrix.html (19 Oct 2026: the batch tray); only the matrix's data is the built one
    dm, tm = re.search(r"^const D=(.*);$", body, re.M), re.search(r"<title>(.*?)</title>", body)
    if dm:
        body = (HERE / "matrix.html").read_text().replace("{{TITLE}}", tm.group(1) if tm else "Creative matrix") \
            .replace("{{DATA}}", dm.group(1))
    # the page is authored for the artifact viewer (no <html> skeleton); give the browser one
    return ("<!doctype html><html data-theme=light><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "</head><body style='margin:0'>" + body + OUTLIER_SKIN + "</body></html>", "text/html; charset=utf-8")


# Outlier's look (lab/owner/suite/outlier.html): black field, white condensed type, one red signal — laid over the
# matrix when it is served inside Outlier, so the Create tab reads as the same instrument. The artifact copy keeps its own.
OUTLIER_SKIN = """<link rel=stylesheet href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500&family=Jost:wght@400;500;600&display=swap">
<style>:root,:root[data-theme=dark]{--bg:#f5f1e8;--panel:#fffdf8;--ink:#1c1a16;--soft:#5f584c;--line:#e6dfd0;--shade:rgba(20,20,26,.35);
--fmt:#1f3fd6;--fmt-soft:rgba(31,63,214,.07);--mom:#a8232b;--mom-soft:rgba(168,35,43,.07);--mix:#1f3fd6;--mix-soft:rgba(31,63,214,.06);
--display:"Cormorant Garamond",Georgia,serif;--body:"Jost",system-ui,sans-serif;--mono:"Jost",system-ui,sans-serif;color-scheme:light}
body{background:#f5f1e8}h1{font-weight:300}.eyebrow,.lab,.gh,.dial label{letter-spacing:.2em}
.opt,.mix,.dials,button.cell,.drawer{border-radius:2px}.make{border-radius:99px;color:#fff}</style>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--hooks", required=True, help="round labels for the formats he watches, comma-separated")
    ap.add_argument("--problem", required=True, help="the round label for his problem (worlds.json + sorted posts)")
    ap.add_argument("--n-hooks", type=int, default=3)
    ap.add_argument("--n-moments", type=int, default=5)
    ap.add_argument("--n-bodies", type=int, default=4)
    ap.add_argument("--body-pool", type=int, default=50, help="how many of his top problem posts the bodies come from")
    ap.add_argument("--out")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
