"""Audit: a brand's proven ads for a time frame, ranked, tagged and on one study board.

The steps behind `winners.py audit | tag | videos`, which is the command to use. One step on its own:

    python3 components/winners/audit.py pull   --brand <brand> --since YYYY-MM-DD --until YYYY-MM-DD [--label L]
    python3 components/winners/audit.py rank   ...   one row per script (every re-cut merged); core (60% of purchases), top 50, top 10%
    python3 components/winners/audit.py media  ...   picture, headline, opening line, watch link for the ranked set
    python3 components/winners/audit.py dedupe ...   merge creatives whose opening picture is the same footage
    python3 components/winners/audit.py sheets ...   contact sheets + to_tag.json for creatives the brand's tag memory lacks
    python3 components/winners/audit.py remember ... --tags <file>   save tags into the brand's tag memory
    python3 components/winners/audit.py build  ...   board.html, summary.md, board.json
    python3 components/winners/audit.py videos ... --top N   download the top N videos for teardowns
    python3 components/winners/audit.py all    ...   pull, rank, media, dedupe, sheets, build

Read only. The warehouse copy of the Meta data covers what it holds; anything older is read from Meta with the
brand's own Meta connection (meta-upload). Nothing in an ad account is changed. Tagging (what's on screen, the lead
message) is done by a person's Claude from the contact sheets and the copy, into the brand's tag memory
`runs/winners/<brand>/tags.json`, so a creative is tagged once and reused every week.
Output: runs/winners/<brand>/audit/<label>/ (pictures, videos and sheets gitignored). Process: skill `winners`.
"""
import argparse, base64, collections, datetime as dt, io, json, os, re, subprocess, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
sys.path.append(str(HERE.parent / "funnel-tracking" / "machine"))
sys.path.append(str(HERE.parent / "meta-upload"))
from run_kit import paths  # noqa: E402

REPO = paths.repo(__file__)

# the one fixed list of on-screen types, and the four groups they fall into (statics = any image)
ON_SCREEN = ["Founder to camera", "Creator talking to camera", "Creator using the product", "Actor skit", "Podcast set",
             "Product shot", "Product animation", "Product unboxing", "Sale graphic", "Product graphic", "Comparison graphic",
             "Before and after", "Skin close-up", "Review or article", "Animation", "AI person poster", "AI illustration",
             "AI cartoon character", "AI person video", "Meme or edit", "Unclear"]
FOUNDER = {"Founder to camera", "Founder letter"}
CREATOR = {"Creator talking to camera", "Creator using the product", "Creator using the brush", "Actor skit", "Podcast set",
           "AI person video", "Before and after", "Presenter with whiteboard"}


def run_dir(brand, label):
    d = REPO / "runs" / "winners" / brand / "audit" / label
    d.mkdir(parents=True, exist_ok=True)
    return d


def memory_path(brand):
    return REPO / "runs" / "winners" / brand / "tags.json"


def load(p, default=None):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def save(p, obj):
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def base(name):
    """One name per creative: landing-page suffixes, copy marks and partnership prefixes come off."""
    n = re.sub(r"^PARTNERSHIP \| ", "", name or "")
    n = re.sub(r"\s*-\s*\d{12,}.*$", "", n)
    n = re.sub(r"\s*-\s*[a-z0-9.-]+\.[a-z]{2,}/\S*$", "", n)   # a landing-page address on the end is the same ad
    n = re.sub(r"\s*-\s*(Parasites? LP( #\d)?|Actually Works? LP|Icon LP|Founder LP|Aging LP|Wrinkles? LP|Barber LP)\b.*$", "", n, flags=re.I)
    n = re.sub(r"\s*[-–]\s*Copy.*$", "", n)
    n = re.sub(r"\s+Copy( \d+)?$", "", n)
    n = re.sub(r"^\d+[A-Z]{3}\d+ \| ", "", n)
    n = re.sub(r"_(icon|cpk)-[a-z0-9-]+$", "", n)
    return n.strip()


def script_key(name):
    """Agencies number their scripts and re-cut each with new hooks ("Scrub Task 30 (Hook 2)", "..._project-86-hook-5",
    "..._p086_h1_..."); every cut of one script is one creative here. Names without a script number stay as they are."""
    l = (name or "").lower()
    m = re.search(r"(?:scrub )?task (\d+)", l) or re.search(r"project-(\d+)", l) or re.search(r"_p0*(\d+)_", l)
    if m:
        return "Script %s" % m.group(1)
    return name


def act(lst, kind):
    for a in lst or []:
        if a.get("action_type") == kind:
            return float(a.get("value", 0))
    return 0.0


def accounts(brand):
    import views as V
    rows = V._psql("select key_pattern from brand_sources where source_table = 'meta_ad_insights' "
                   "and key_column = 'account_id' and brand = :'b';", b=brand)
    return [r["key_pattern"] for r in rows]


def _in_list(accts):
    return ",".join("'%s'" % x.replace("'", "") for x in accts)


def warehouse_first(brand):
    """The first day the warehouse holds for the brand's accounts, or None."""
    import views as V
    accts = accounts(brand)
    if not accts:
        return None
    return (V._psql("select min(date)::text d from meta_ad_insights where account_id in (%s);" % _in_list(accts)) or [{}])[0].get("d")


def warehouse_ads(brand, since, until, monthly=False):
    """Per ad (per ad per month with monthly=True), read only, for the brand's accounts:
    ad_id, ad_name, spend, purchases, value, last (the last day with data), and month when asked for."""
    import views as V
    accts = accounts(brand)
    if not accts:
        return []
    rows = V._psql("""select ad_id, max(ad_name) ad_name, %s m, max(date)::text l, sum(spend) sp,
        sum(coalesce(purchases,0)) b, sum(coalesce(purchase_value,0)) v from meta_ad_insights
        where account_id in (%s) and date >= :'a' and date <= :'z' group by 1%s;""" % (
        "to_char(date,'YYYY-MM')" if monthly else "''::text", _in_list(accts), ",3" if monthly else ""), a=since, z=until)
    out = []
    for r in rows:
        row = dict(ad_id=r["ad_id"], ad_name=r["ad_name"], spend=float(r["sp"] or 0), purchases=float(r["b"] or 0),
                   value=float(r["v"] or 0), last=r["l"])
        if monthly:
            row["month"] = r["m"]
        out.append(row)
    return out


# ------------------------------------------------------------------------------------------------------- pull --
def pull(a):
    """Per ad per month: the warehouse where it has days, Meta (read-only) for anything earlier."""
    out, since, until = [], a.since, a.until
    first = warehouse_first(a.brand)
    lo = max(since, first) if first else None
    if lo and lo <= until:
        for r in warehouse_ads(a.brand, lo, until, monthly=True):
            out.append(dict(ad_id=r["ad_id"], ad_name=r["ad_name"], month=r["month"], spend=r["spend"],
                            purchases=r["purchases"], value=r["value"], source="warehouse"))
    meta_until = min(until, (dt.date.fromisoformat(first) - dt.timedelta(days=1)).isoformat()) if first else until
    if since <= meta_until:
        from meta import Meta
        m = Meta(a.brand)
        acct = m.ACCOUNT if str(m.ACCOUNT).startswith("act_") else "act_" + str(m.ACCOUNT)
        for r in m.paged(acct + "/insights", level="ad", time_increment="monthly", limit=500,
                         fields="ad_id,ad_name,spend,actions,action_values,date_start",
                         time_range=json.dumps({"since": since, "until": meta_until})):
            out.append(dict(ad_id=r["ad_id"], ad_name=r["ad_name"], month=r["date_start"][:7], spend=float(r["spend"]),
                            purchases=act(r.get("actions"), "purchase"), value=act(r.get("action_values"), "purchase"), source="meta"))
    cells = collections.defaultdict(lambda: {"spend": 0.0, "purchases": 0.0, "value": 0.0, "ids": collections.Counter()})
    for r in out:
        c = cells[(base(r["ad_name"]), r["month"])]
        c["spend"] += r["spend"]; c["purchases"] += r["purchases"]; c["value"] += r["value"]; c["ids"][r["ad_id"]] += r["spend"]
    rows = [dict(name=k[0], month=k[1], spend=round(v["spend"], 2), purchases=int(v["purchases"]), value=round(v["value"], 2),
                 ids=[i for i, _ in v["ids"].most_common(3)]) for k, v in cells.items() if v["spend"] > 0]
    d = run_dir(a.brand, a.label)
    save(d / "cells.json", rows)
    win = {"brand": a.brand, "since": since, "until": until, "warehouse_from": first,
           "pulled_at": dt.datetime.now().isoformat(timespec="seconds")}
    if getattr(a, "title", None):
        win["title"] = a.title   # so a later build, from `tag`, keeps how the brand's name reads
    save(d / "window.json", win)
    print("pull: %d creative-months, %d creatives, $%s spend, %d purchases" % (
        len(rows), len({r["name"] for r in rows}), format(round(sum(r["spend"] for r in rows)), ","), sum(r["purchases"] for r in rows)))


# ------------------------------------------------------------------------------------------------------- rank --
def window_merges(d):
    """A window's merges. A new window, with no file of its own yet, starts from the brand's widest window's, so a
    person's merges carry over; `dedupe` saves what it ends with to the new window."""
    if (d / "merges.json").exists():
        return load(d / "merges.json", {})
    sys.path.insert(0, str(HERE))
    import bank as B
    others = [f for f in sorted(d.parent.glob("*/window.json")) if f.parent != d]
    if not others:
        return {}
    widest = max(others, key=lambda f: B.widest_key(load(f)))
    return load(widest.parent / "merges.json", {})


def rank(a, merges=None):
    """Rank creatives by purchases, one row per script (all its cuts merged) and per merged look-alike set.
    `merges` (from `dedupe`) maps a script to the script it duplicates."""
    d = run_dir(a.brand, a.label)
    cells = load(d / "cells.json")
    merges = merges if merges is not None else window_merges(d)
    def key(n):
        k = script_key(n)
        while k in merges:
            k = merges[k]
        return k
    g = collections.defaultdict(lambda: {"spend": 0.0, "purchases": 0, "value": 0.0, "months": set(), "ids": collections.Counter(),
                                         "variants": collections.Counter()})
    for c in cells:
        o = g[key(c["name"])]
        o["spend"] += c["spend"]; o["purchases"] += c["purchases"]; o["value"] += c["value"]; o["months"].add(c["month"])
        o["variants"][c["name"]] += c["purchases"]
        for i in c["ids"]:
            o["ids"][i] += c["spend"] / max(len(c["ids"]), 1)
    names = sorted(g, key=lambda n: (-g[n]["purchases"], -g[n]["spend"]))
    total = sum(v["purchases"] for v in g.values()) or 1
    cum, core = 0, None
    for i, n in enumerate(names):
        cum += g[n]["purchases"]
        if core is None and cum / total >= 0.60:
            core = i + 1
    top10 = max(1, round(len(names) * 0.10))
    top50 = min(50, top10)
    old = {r["name"]: r for r in (load(d / "ranked.json", {}) or {}).get("rows", [])}
    ranked = []
    for i, n in enumerate(names[:top10]):
        v = g[n]
        r = dict(rank=i + 1, name=n, spend=round(v["spend"], 2), purchases=v["purchases"], value=round(v["value"], 2),
                 first=min(v["months"]), last=max(v["months"]), months=len(v["months"]),
                 ids=[x for x, _ in v["ids"].most_common(3)],
                 variants=[x for x, _ in v["variants"].most_common()], cuts=len(v["variants"]))
        for k in ("pic", "format", "headline", "body", "link", "video_id"):
            if old.get(n, {}).get(k) is not None and old[n].get("ids") == r["ids"]:
                r[k] = old[n][k]
        ranked.append(r)
    save(d / "ranked.json", {"total_purchases": total, "total_spend": round(sum(v["spend"] for v in g.values()), 2),
                             "creatives": len(names), "names": len({c["name"] for c in cells}), "core": core or top10,
                             "top50": top50, "top10": top10, "rows": ranked})
    print("rank: %d ad names -> %d distinct creatives; core %d (60%% of purchases), top 10%% = %d (%.1f%% of purchases)" % (
        len({c["name"] for c in cells}), len(names), core or top10, top10, 100 * sum(r["purchases"] for r in ranked) / total))


def dedupe(a):
    """Creatives whose opening picture is the same footage (the hook band at the top ignored) are one ad: merge them,
    keep the merges, rank again, and fetch media for anything new in the top set."""
    from PIL import Image
    d = run_dir(a.brand, a.label)
    merges = window_merges(d)
    for _ in range(3):
        rk = load(d / "ranked.json")
        def dh(p):
            im = Image.open(p).convert("L"); w, h = im.size
            px = list(im.crop((0, int(h * 0.25), w, h)).resize((17, 16)).getdata())
            return [px[r * 17 + c] > px[r * 17 + c + 1] for r in range(16) for c in range(16)]
        rows = [r for r in rk["rows"] if r.get("pic") and (d / r["pic"]).exists()]
        hs = {r["name"]: dh(d / r["pic"]) for r in rows}
        new = 0
        for i, x in enumerate(rows):
            for y in rows[i + 1:]:
                if x["name"] in merges or y["name"] in merges:
                    continue
                if sum(p != q for p, q in zip(hs[x["name"]], hs[y["name"]])) <= 6:
                    merges[y["name"]] = x["name"]; new += 1
        save(d / "merges.json", merges)
        if not new:
            break
        rank(a, merges)
        media(a)
    print("dedupe: %d look-alike merges kept in merges.json" % len(merges))


# ------------------------------------------------------------------------------------------------------ media --
def shrink(src, dst):
    """A JPEG no larger than 320 on its long side."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im.thumbnail((320, 320))
    im.save(dst, "JPEG", quality=85)


def description_of(vd, ld, af):
    """The ad's description line (the small text under the headline): video link description, link description,
    else the first of a flexible ad's descriptions."""
    return (vd.get("link_description") or ld.get("description")
            or ((af.get("descriptions") or [{}])[0] or {}).get("text") or "")


def words(a):
    """Read-only: fill each ranked row's description (and a missing headline or body) from its ad's creative —
    one creative read per row that has no description yet, no pictures. The copy library on the approval page
    offers winners' descriptions with their sales (the owner, 8 Nov 2026)."""
    from meta import Meta
    d = run_dir(a.brand, a.label)
    rk = load(d / "ranked.json")
    m = Meta(a.brand)
    done = 0
    for r in rk["rows"]:
        if "description" in r:
            continue
        for i in r["ids"]:
            try:
                ad = m.get(i, fields="creative{title,body,object_story_spec,asset_feed_spec}")
                c = ad.get("creative", {}); oss = c.get("object_story_spec") or {}
                vd, ld, af = oss.get("video_data") or {}, oss.get("link_data") or {}, c.get("asset_feed_spec") or {}
                r["description"] = description_of(vd, ld, af)
                r["headline"] = r.get("headline") or c.get("title") or vd.get("title") or ld.get("name") or ""
                r["body"] = r.get("body") or c.get("body") or vd.get("message") or ld.get("message") or ""
                done += 1
                break
            except BaseException as e:  # noqa: BLE001 — the Meta helper exits on an error; try the next copy
                r["err"] = str(e)[:120]
    save(d / "ranked.json", rk)
    print("words: %d row(s) read, %d with a description" % (done, sum(1 for r in rk["rows"] if r.get("description"))))


def media(a):
    from meta import Meta
    d = run_dir(a.brand, a.label)
    rk = load(d / "ranked.json"); pics = d / "pics"; pics.mkdir(exist_ok=True)
    m = Meta(a.brand)
    for r in rk["rows"]:
        if r.get("pic") and (d / r["pic"]).exists():
            continue
        for i in r["ids"]:
            try:   # the Meta helper exits on an error, so catch everything and try the next copy
                ad = m.get(i, fields="preview_shareable_link,creative.thumbnail_width(480).thumbnail_height(854)"
                                     "{thumbnail_url,image_url,video_id,title,body,instagram_permalink_url,object_story_spec,asset_feed_spec}")
                c = ad.get("creative", {}); oss = c.get("object_story_spec") or {}
                vd, ld, af = oss.get("video_data") or {}, oss.get("link_data") or {}, c.get("asset_feed_spec") or {}
                r["video_id"] = c.get("video_id") or vd.get("video_id") or ((af.get("videos") or [{}])[0].get("video_id"))
                r["format"] = "Video" if r["video_id"] else "Image"
                r["headline"] = c.get("title") or vd.get("title") or ld.get("name") or (af.get("titles") or [{}])[0].get("text") or ""
                r["body"] = c.get("body") or vd.get("message") or ld.get("message") or (af.get("bodies") or [{}])[0].get("text") or ""
                r["description"] = description_of(vd, ld, af)
                r["link"] = c.get("instagram_permalink_url") or ad.get("preview_shareable_link")
                f = pics / (re.sub(r"[^A-Za-z0-9]+", "-", r["name"])[:60] + ".jpg")
                urllib.request.urlretrieve(c.get("image_url") or c.get("thumbnail_url"), str(f) + ".src")
                try:
                    shrink(str(f) + ".src", str(f))
                finally:
                    os.remove(str(f) + ".src")
                if f.exists():
                    r["pic"] = str(f.relative_to(d))
                    break
            except BaseException as e:  # noqa: BLE001
                r["err"] = str(e)[:120]
    save(d / "ranked.json", rk)
    print("media: %d of %d with a picture" % (sum(1 for r in rk["rows"] if r.get("pic")), len(rk["rows"])))


# ----------------------------------------------------------------------------------------------------- sheets --
def sheets(a):
    from PIL import Image, ImageDraw
    d = run_dir(a.brand, a.label)
    rk = load(d / "ranked.json"); mem = load(memory_path(a.brand), {})
    todo = [r for r in rk["rows"] if r.get("pic") and r["name"] not in mem and not any(v in mem for v in r.get("variants", []))]
    for k in range(0, len(todo), 48):
        part = todo[k:k + 48]
        im = Image.new("RGB", (8 * 170, 6 * 320), "white"); dr = ImageDraw.Draw(im)
        for j, r in enumerate(part):
            if (d / r["pic"]).exists():  # a picture absent on this machine leaves its cell empty, label still on it
                p = Image.open(d / r["pic"]).convert("RGB"); p.thumbnail((166, 290)); im.paste(p, ((j % 8) * 170 + 2, (j // 8) * 320))
            dr.rectangle([(j % 8) * 170 + 2, (j // 8) * 320 + 292, (j % 8) * 170 + 70, (j // 8) * 320 + 310], fill="yellow")
            dr.text(((j % 8) * 170 + 5, (j // 8) * 320 + 295), "R%d" % r["rank"], fill="black")
        im.save(d / ("sheet_%02d.jpg" % (k // 48 + 1)), quality=78)
    save(d / "to_tag.json", [dict(label="R%d" % r["rank"], name=r["name"], format=r.get("format"), headline=r.get("headline"),
                                  opening=(r.get("body") or "").split("\n")[0][:300]) for r in todo])
    print("sheets: %d creatives to tag (%d already in the tag memory), %d sheet(s)" % (
        len(todo), len(rk["rows"]) - len(todo), (len(todo) + 47) // 48))


def missing_tags(a):
    """How many creatives the last `sheets` listed as still to tag and the tag memory still lacks."""
    d = run_dir(a.brand, a.label)
    mem = load(memory_path(a.brand), {})
    return sum(1 for t in load(d / "to_tag.json", []) if t["name"] not in mem)


# ------------------------------------------------------------------------------------------------------ build --
def group(fmt, screen):
    if fmt == "Image":
        return "Statics"
    if screen in FOUNDER:
        return "Founder"
    if screen in CREATOR:
        return "Creator"
    return "B-roll and cuts"


def build(a):
    from PIL import Image
    d = run_dir(a.brand, a.label)
    rk = load(d / "ranked.json"); mem = load(memory_path(a.brand), {}); win = load(d / "window.json")
    total = rk["total_purchases"]; rows = []
    for r in rk["rows"]:
        t = mem.get(r["name"]) or next((mem[v] for v in r.get("variants", []) if v in mem), {})
        img = None
        if r.get("pic") and (d / r["pic"]).exists():
            p = Image.open(d / r["pic"]).convert("RGB"); p.thumbnail((300, 534)); b = io.BytesIO(); p.save(b, "JPEG", quality=62)
            img = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        screen = t.get("on_screen", "Not tagged yet"); fmt = r.get("format") or ""
        rows.append(dict(rank=r["rank"], name=r["name"], message=t.get("message", "Not tagged yet"), screen=screen, format=fmt,
                         group=t.get("group") or group(fmt, screen), purchases=r["purchases"], spend=round(r["spend"]),
                         value=round(r["value"]), cpa=round(r["spend"] / r["purchases"], 2) if r["purchases"] else 0,
                         roas=round(r["value"] / r["spend"], 2) if r["spend"] else 0, share=r["purchases"] / total,
                         first=r["first"], last=r["last"], months=r["months"],
                         years=sorted({int(r["first"][:4]), int(r["last"][:4])}), headline=r.get("headline") or "",
                         opening=(r.get("body") or "").split("\n")[0][:260], link=r.get("link"), img=img,
                         teardown=bool(t.get("teardown")), cuts=r.get("cuts", 1), variants=r.get("variants", [])[:12]))
    window = "%s to %s" % (win["since"], win["until"])
    brand_name = getattr(a, "title", None) or win.get("title") or a.brand.upper()
    core, top50, n = rk["core"], min(rk["top50"], len(rows)), len(rows)
    core_min = rows[core - 1]["purchases"] if core <= len(rows) else 0
    h = (HERE / "board_template.html").read_text()
    for k, v in {"__ROWS__": json.dumps(rows, separators=(",", ":")), "__TOTAL__": str(total), "__BRAND__": brand_name,
                 "__WINDOW__": window, "__CORE_N__": str(core), "__TOP50_N__": str(top50), "__ALL_N__": str(n),
                 "__CORE_LINE__": "Core %d are the creatives worth breaking down first; each made %d or more purchases." % (core, core_min),
                 "__FOOT__": ("The top 10%% of every %s ad creative that spent from %s (%d of %d), ranked by Meta purchases, copies of the "
                              "same creative merged. Read only from the ad account (warehouse copy where it has the days, Meta for "
                              "earlier). Message tags come from each ad's copy; what's on screen from its picture.") % (
                     brand_name, window, n, rk["creatives"])}.items():
        h = h.replace(k, v)
    (d / "board.html").write_text(h)
    save(d / "board.json", [{k: v for k, v in r.items() if k != "img"} for r in rows])
    # a written copy for the team
    by = lambda key: sorted(((k, [r for r in rows if r[key] == k]) for k in {r[key] for r in rows}), key=lambda kv: -sum(r["purchases"] for r in kv[1]))
    L = ["# %s creative audit · %s" % (brand_name, window), "",
         "%d creatives spent; the top 10%% (%d) made %.1f%% of purchases. Core %d = 60%% of purchases." % (
             rk["creatives"], n, 100 * sum(r["purchases"] for r in rows) / total, core), ""]
    for key, title in [("group", "Type"), ("message", "Message"), ("screen", "On screen")]:
        L += ["## %s" % title, "", "| | Ads | Share of all purchases | Cost/purchase |", "|---|---|---|---|"]
        for k, rs in by(key):
            p = sum(r["purchases"] for r in rs); s = sum(r["spend"] for r in rs)
            L.append("| %s | %d | %.1f%% | $%s |" % (k, len(rs), 100 * p / total, round(s / p) if p else "—"))
        L.append("")
    L += ["## Core %d" % core, "", "| # | Type | Message | On screen | Purchases | Cost | ROAS | Ran | Name |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows[:core]:
        L.append("| %d | %s | %s | %s | %d | $%.0f | %.2fx | %s to %s | %s |" % (r["rank"], r["group"], r["message"], r["screen"], r["purchases"],
                                                                         r["cpa"], r["roas"], r["first"], r["last"], r["name"].replace("|", "/")))
    (d / "summary.md").write_text("\n".join(L) + "\n")
    nopic = sum(1 for r in rows if not r["img"])
    print("build: board.html (%d creatives, %d not tagged yet%s), summary.md" % (
        n, sum(1 for r in rows if r["message"] == "Not tagged yet"), ", %d without a picture on this machine" % nopic if nopic else ""))


# ----------------------------------------------------------------------------------------------------- videos --
def videos(a):
    """The top N videos as files, for teardowns: the Facebook video page gives the original size, Instagram is the backup."""
    from meta import Meta
    d = run_dir(a.brand, a.label); vd = d / "videos"; vd.mkdir(exist_ok=True)
    rk = load(d / "ranked.json"); m = Meta(a.brand); got = 0
    for r in rk["rows"][:a.top]:
        stem = vd / ("%02d-%s" % (r["rank"], re.sub(r"[^a-z0-9]+", "-", r["name"].lower()).strip("-")[:40]))
        if list(vd.glob(stem.name + ".*")):
            got += 1; continue
        if r.get("format") == "Image":
            continue
        urls = []
        if r.get("video_id"):
            try:
                pl = m.get(r["video_id"], fields="permalink_url").get("permalink_url")
                if pl:
                    urls.append("https://www.facebook.com" + pl)
            except BaseException:  # noqa: BLE001
                pass
        if r.get("link") and "instagram.com" in r["link"]:
            urls.append(r["link"])
        for u in urls:
            subprocess.run(["yt-dlp", "-q", "--no-warnings", "--socket-timeout", "30", "-o", str(stem) + ".%(ext)s", u], capture_output=True)
            if list(vd.glob(stem.name + ".*")):
                got += 1; break
        else:
            r["video_error"] = "no public copy to download"
    save(d / "ranked.json", rk)
    print("videos: %d of the top %d on disk in %s" % (got, a.top, vd))


# --------------------------------------------------------------------------------------------------- remember --
def remember(a):
    """Write tags into the brand's tag memory: --tags <file> holding {"R12": {"on_screen": .., "message": ..}, ...}
    (labels from to_tag.json) or {"<creative name>": {...}}; also takes {"group": ..} and {"teardown": true}."""
    d = run_dir(a.brand, a.label)
    todo = {t["label"]: t for t in load(d / "to_tag.json", [])}
    mem = load(memory_path(a.brand), {})
    new = load(a.tags)
    bad = []
    for k, v in new.items():
        name = todo[k]["name"] if k in todo else k
        if v.get("on_screen") and v["on_screen"] not in ON_SCREEN and v["on_screen"] not in FOUNDER:
            bad.append("%s: %s" % (k, v["on_screen"]))
        entry = mem.get(name, {})
        entry.update({x: y for x, y in v.items() if y is not None})
        if k in todo and todo[k].get("format"):
            entry.setdefault("format", todo[k]["format"])
        entry.setdefault("source", "tagged %s" % dt.date.today().isoformat())
        mem[name] = entry
    save(memory_path(a.brand), mem)
    print("remember: %d tags saved (%d in memory)%s" % (len(new), len(mem), ("; not on the fixed list: " + ", ".join(bad)) if bad else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["pull", "rank", "media", "words", "dedupe", "sheets", "remember", "build", "videos", "all"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--label")
    ap.add_argument("--title", help="how the brand's name reads on the board")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--tags", help="remember: a JSON file of tags")
    a = ap.parse_args()
    a.label = a.label or "%s_%s" % (a.since, a.until)
    steps = {"pull": pull, "rank": rank, "media": media, "words": words, "dedupe": dedupe, "sheets": sheets, "remember": remember, "build": build, "videos": videos}
    for s in (["pull", "rank", "media", "dedupe", "sheets", "build"] if a.step == "all" else [a.step]):
        steps[s](a)


if __name__ == "__main__":
    main()
