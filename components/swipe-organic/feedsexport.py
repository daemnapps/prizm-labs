#!/usr/bin/env python3
"""My Feeds, public — the static export behind daemn.co/feeds/.

    python3 feedsexport.py                         # writes ~/Projects/prizm-labs/docs/feeds/data
    python3 feedsexport.py --site <data dir>       # anywhere else
    python3 feedsexport.py --records <records dir> # read another checkout's records
    python3 feedsexport.py --dry-run               # build + check, write nothing

the owner reversed the "never public" ruling on 1 Oct 2026: My Feeds goes on the
site as ONE read-only page. The same day he ruled the redesign wrong — the site
shows HIS board (desk.html, port 8820): same controls, same cards, same
behaviour, inside the site shell, read-only. So this export writes what the
desk's /api/state gives the board — feeds, cards, brands, avatars, lanes,
shapes, stats, the research chain and the prompts — as static JSON, plus the
paid lane on the same control bar. Our brand names are allowed on the page
since that ruling; everything else the scan refused still is.

What it does, and what it never does:

  * READS ONLY what is already pulled — the feed records (through
    desklib.feeds()/cards()/chain(), the functions the desk uses) and the paid
    sweeps' _raw files. It never pulls, never calls a model, and never imports
    apify.py (test_feedsexport.py fails if it does). Zero spend.
  * Writes an ALLOW-LIST of fields per row — nothing else from a record can
    leak, because nothing else is copied. No spend, no keys, no job log, no
    nightly-run panel, no verdicts, none of our own ad accounts.
  * Refuses to write if the no-secrets scan finds anything, or if the size
    check fails.

Output (inside --site):
  index.json                 the board: feeds, brands, advertisers, prompts,
                             formats, sounds, counts, "Updated <date>"
  cards/<feed>.json          every card in that feed (the desk's card shape)
  chain/<feed>.json          the research chain, stage by stage
  ads.json                   competitors' ads, longest running first
  sheets/<post>.json         the rebuild sheet, for posts that have one
  thumbs/<post>.webp         cover; thumbs/<post>-frames.webp = 6 frames
"""
import argparse, io, json, os, re, shutil, sys, tempfile, urllib.request
from datetime import date, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import desklib as D          # noqa: E402  (reads records; imports no apify at load)
import packs                 # noqa: E402  (the guard)

# Pictures are shown in cards that are 200-280 CSS px wide, so on any retina
# screen a 220px source was being upscaled — which is why the thumbnails
# looked soft (the owner, 2 Oct: "the quality of all these thumbnails is shit").
# AdPlexity serves its originals at 720x1280, so the detail was always there.
# Measured on a real ad: 220px/q38 = 3.1 KB, 440px/q56 = 8.6 KB — about what
# the average thumbnail already weighed, for twice the resolution.
ORGANIC_W, PAID_W, Q = 440, 440, 56   # picture width (px) and webp quality
ADS_PER_ADVERTISER = 200              # longest-running first
THUMBS_MAX = 70e6                     # every picture together
# 6,034 pictures at ~8.6 KB is ~52 MB. The old 40 MB ceiling was already
# being exceeded at the smaller size, so it was going to refuse the next
# full run either way.
DAILY_MAX = 3e6                       # what one run may change
DEFAULT_SITE = Path(os.environ.get("PRIZM_SITE", str(Path.home() / "Projects" / "prizm-labs"))) / "docs" / "feeds" / "data"

# ---------------------------------------------------------------- the people
# A plain line per feed, for the Paid lane's header (and the prompt's
# "who it's for"), read from the feed's own sources.json ("line") — never
# typed here (workspace rule 7). A feed without one shows no line.
def feed_line(fid):
    try:
        v = json.loads((D.FEEDS / fid / "sources.json").read_text()).get("line")
    except (OSError, ValueError):
        return None
    return v.strip() if isinstance(v, str) and v.strip() else None


# Our brands are read from the workspace's brands/ folder — never typed here
# (workspace rule 7).
OUR_BRANDS = tuple(sorted(p.name for p in (packs._workspace() / "brands").iterdir()
                          if p.is_dir() and not p.name.startswith(("_", "."))))

# ---------------------------------------------------------------- the scan
# On top of packs.OURS (our names, a person's disk, secrets): the things the
# plan names as never public. Since 1 Oct 2026 the two brand NAMES may show
# (the owner wants to see them); a brand-keyed folder id still may not.
OURS_PUBLIC = re.compile("|".join(a for a in packs.OURS.pattern.split("|")
                                  if a.lower() not in OUR_BRANDS), re.I)
NEVER = re.compile(
    r"act_\d+|meta_page_id|adplexity|prompts-as-sent|customer-base|receipt|"
    r"cloudfront\.net|damon--|desk/jobs|desk/briefs|apify|/Users/"
    + (r"|\b(?:" + "|".join(map(re.escape, OUR_BRANDS)) + r")--" if OUR_BRANDS else ""), re.I)


def own_account_ids(ws):
    own = ws / "components" / "swipe-paid" / "own"
    return {p.name for p in own.iterdir() if p.is_dir() and p.name.isdigit()} if own.is_dir() else set()


# The one AdPlexity address allowed through: the creative file itself on their
# CDN. the owner ruled it 2 Oct 2026 — Open must go to "the Adplexity file link",
# not the Facebook Ad Library — and the tool is already named on daemn.co's own
# cost table, so its name is not what this guard protects. Everything else about
# AdPlexity (our account, our searches, our API calls) stays refused below.
PUBLIC_FILE = re.compile(r"https://app\.adplexity\.io/storage/[\w./-]+", re.I)


def allowed(text):
    return PUBLIC_FILE.sub(" ", text)


def dirty(text, ids=()):
    text = allowed(text)
    return bool(OURS_PUBLIC.search(text) or NEVER.search(text) or any(i in text for i in ids))


def clean(s, ids=()):
    """A free-text field: kept whole when it is clean, blanked when it is not."""
    s = "" if s is None else str(s)
    return "" if dirty(s, ids) else s


def scan(root, ids):
    """Every file name and every text file under the export, against every
    pattern. Returns the hits; an empty list is the only pass."""
    hits = []
    for p in root.rglob("*"):
        if dirty(p.name, ids):
            hits.append(f"{p.relative_to(root)}: bad file name")
        if p.is_file() and p.suffix in (".json", ".md", ".txt", ".html"):
            t = allowed(p.read_text(errors="ignore"))
            m = OURS_PUBLIC.search(t) or NEVER.search(t) or \
                next((re.search(re.escape(i), t) for i in ids if i in t), None)
            if m:
                hits.append(f"{p.relative_to(root)}: …{t[max(0, m.start()-40):m.end()+40]}…")
    return hits


# ---------------------------------------------------------------- pictures
def webp(src_bytes, width, q=Q):
    from PIL import Image
    im = Image.open(io.BytesIO(src_bytes)).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=q, method=6)
    return out.getvalue()


def frames_webp(strip_dir, h=240):
    from PIL import Image
    shots = [Image.open(f).convert("RGB") for f in sorted(strip_dir.glob("*.jpg"))[:6]]
    if not shots:
        return None
    shots = [s.resize((round(s.width * h / s.height), h), Image.LANCZOS) for s in shots]
    sheet = Image.new("RGB", (sum(s.width for s in shots), h))
    x = 0
    for s in shots:
        sheet.paste(s, (x, 0))
        x += s.width
    out = io.BytesIO()
    sheet.save(out, "WEBP", quality=48, method=6)
    return out.getvalue()


FETCH_CACHE = os.environ.get("FEEDSEXPORT_CACHE")   # optional: raw pictures kept between runs


def blank(path):
    """True when a cover is one flat colour — Meta's grey play-box poster."""
    try:
        from PIL import Image
        lo, hi = Image.open(path).convert("L").getextrema()
        return hi - lo < 60
    except Exception:
        return False


def video_frame(url):
    """One real frame, two seconds into the ad's own video, as the cover."""
    import subprocess
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "f.jpg"
        try:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "2", "-i", url, "-frames:v", "1", str(out)],
                           timeout=60, check=True)
            return webp(out.read_bytes(), PAID_W)
        except Exception:
            return None


def fetch(url):
    if FETCH_CACHE:
        import hashlib
        f = Path(FETCH_CACHE) / hashlib.sha1(url.encode()).hexdigest()
        if f.is_file():
            return f.read_bytes()
        data = _fetch(url)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        return data
    return _fetch(url)


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read()


# ---------------------------------------------------------------- organic
def safe_id(platform, raw):
    p = {"tiktok": "tt", "instagram": "ig", "youtube": "yt"}.get(platform, "x")
    return f"{p}-{re.sub(r'[^A-Za-z0-9_-]', '', str(raw))}"


def iso_utc(s):
    """A record's date as the desk reads it (desklib.iso), to the minute, UTC."""
    d = D.iso(s) if s else None
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ") if d else None


def public_id(fid):
    """The feed's id on the site: its sources.json "public_id" when it names
    one (a folder name that says nothing on a page), else the part after "--"."""
    try:
        v = json.loads((D.FEEDS / fid / "sources.json").read_text()).get("public_id")
    except (OSError, ValueError):
        v = None
    return v.strip() if isinstance(v, str) and v.strip() else fid.split("--", 1)[-1]


def feed_brand(f):
    b = (f.get("brand") or "").lower()
    return b if b in OUR_BRANDS else "general"


def chain_public(fid, ids):
    """The research chain as the desk shows it, minus what is not public: the
    per-feed prompt-as-sent (it carries the whole internal avatar card), and
    the pull's raw error strings. Counts, searches, kept/thrown-out with the
    reason, and the creators followed all stay."""
    ch = D.chain(fid)
    st = ch["stages"]
    plan = st[0]["output"]
    if isinstance(plan, dict):
        plan = {k: v for k, v in plan.items() if not dirty(json.dumps(v, ensure_ascii=False), ids)}
    pull = st[1]["output"]
    if isinstance(pull, dict):
        pull = {"at": pull.get("at"), "observed": pull.get("observed"), "new": pull.get("new"),
                "by_source": {k: v for k, v in (pull.get("by_source") or {}).items() if not dirty(k, ids)},
                "trouble": len(pull.get("errors") or [])}
    sift = st[2]["output"]
    rows = lambda l: [{"author": clean(r.get("author"), ids), "kind": clean(r.get("kind"), ids),
                       "why": clean(r.get("why"), ids), "url": clean(r.get("url"), ids)} for r in l]
    sift = {"kinds": sift["kinds"], "kept": rows(sift["kept"]), "dropped": rows(sift["dropped"])}
    follow = [{"platform": d.get("platform") or "", "value": clean(d.get("value") or d.get("handle"), ids),
               "why": clean(d.get("receipt") or d.get("why"), ids)} for d in st[3]["output"]]
    entry = {k: v for k, v in (st[1].get("entry") or {}).items() if k != "note"}
    out = []
    for s, o in zip(st, (plan, pull, sift, follow, st[4]["output"])):
        out.append({"n": s["n"], "name": s["name"], "does": s["does"], "model": {"the daily run": "each Pull"}.get(s["model"], "the scrapers" if "pify" in s["model"] else s["model"]),
                    "prompt_file": s.get("prompt_file"), "output": o})
    out[1]["entry"] = entry
    out[4]["does"] = "Every Pull runs stages 2–4 again on the feed."
    return {"feed": public_id(fid), "stages": out}


def build(records, ws, stage, old, repix=False):
    D.FEEDS = records / "avatar-feeds"
    ids = own_account_ids(ws)
    for sub in ("cards", "chain", "sheets", "thumbs"):
        (stage / sub).mkdir(parents=True, exist_ok=True)
    tried = {}

    def thumb(name, make):
        """Reuse the last export's picture when there is one — same bytes, no churn."""
        if name in tried:                      # one try per picture per run
            return tried[name]
        dest = stage / "thumbs" / f"{name}.webp"
        prev = old / "thumbs" / f"{name}.webp"
        if prev.is_file() and not repix:
            shutil.copy2(prev, dest)
            tried[name] = True
            return True
        data = None
        for _ in range(2):
            try:
                data = make()
                break
            except Exception:
                data = None
        if not data and prev.is_file():
            # --repix asked for a fresh picture and there is no source to make
            # one from: most of the organic media lives on the Drive, not on
            # this disk, and only the published picture survives here. Keep it
            # rather than lose it — a re-pix must never empty the board.
            shutil.copy2(prev, dest)
            tried[name] = True
            return True
        if data:
            dest.write_bytes(data)
        tried[name] = bool(data)
        return tried[name]

    vids = records / "swipe-videos"
    feeds_out, n_cards, dropped = [], 0, 0
    for f in D.feeds():
        fid, pid_feed = f["id"], public_id(f["id"])
        items = json.loads((D.FEEDS / fid / "items.json").read_text())["items"] \
            if (D.FEEDS / fid / "items.json").exists() else {}
        rows = []
        for c in D.cards(fid):
            item = items.get(c["key"], {})
            item_id = c["key"].split(":", 1)[-1]
            pid = safe_id(c["platform"], item_id)
            row = {"key": c["key"], "id": pid, "feed": pid_feed, "platform": c["platform"], "url": c["url"],
                   "author": c["author"], "caption": c["caption"], "tags": c["tags"][:12],
                   "posted": iso_utc(item.get("posted")),
                   "seen": iso_utc(item.get("first_seen")),
                   "views": c["views"], "likes": c["likes"], "sent": c["sent"], "rise": c["rise"],
                   "punch": c["punch"], "kind": c["kind"], "lane": c["lane"], "source": c["source"],
                   "brand_fit": c["brand_fit"], "swipe_lane": c["swipe_lane"], "keep": c["keep"],
                   "what": c["what"], "format": c["format"], "why": c["why"],
                   "pic": item.get("kind") in ("image", "carousel")}
            row = {k: v for k, v in row.items() if v not in (None, "", [], False) or k == "keep" and v is False}
            if dirty(json.dumps(row, ensure_ascii=False), ids):
                dropped += 1
                continue
            cov = D.FEEDS / fid / "covers" / (re.sub(r"[^A-Za-z0-9_-]", "", str(item_id)) + ".jpg")
            if thumb(pid, lambda cov=cov: webp(cov.read_bytes(), ORGANIC_W) if cov.is_file() else None):
                row["thumb"] = 1
            hf = vids / item_id / "handoff.md"
            if hf.is_file():
                md = hf.read_text()
                if not dirty(md, ids):
                    if not (stage / "sheets" / f"{pid}.json").exists():
                        (stage / "sheets" / f"{pid}.json").write_text(json.dumps({"text": md}, ensure_ascii=False))
                    row["sheet"] = 1
            if (vids / item_id / "strip").is_dir() and \
                    thumb(f"{pid}-frames", lambda d=vids / item_id / "strip": frames_webp(d)):
                row["frames"] = 1
            rows.append(row)
        (stage / "cards" / f"{pid_feed}.json").write_text(
            json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
        n_cards += len(rows)
        (stage / "chain" / f"{pid_feed}.json").write_text(
            json.dumps(chain_public(fid, ids), ensure_ascii=False, separators=(",", ":")))
        brand = feed_brand(f)
        core = f.get("core")
        if core and brand == "general":
            core = pid_feed                    # an asked feed of his own: its own avatar
        sub = f.get("sub")
        whose = f.get("whose") if f.get("whose") and f.get("whose") != "damon" else None
        feeds_out.append({
            "id": pid_feed, "title": clean(f["title"], ids), "brand": brand,
            "core": core, "sub": sub,
            "whose": clean(whose, ids) or None,
            "line": clean(feed_line(fid), ids) or None,
            "sources": f["sources"], "probation": f["probation"], "sweeps": f["sweeps"],
            "source_list": [{"platform": s.get("platform") or "", "kind": s.get("kind") or "",
                             "value": clean(s.get("value"), ids), "status": s.get("status") or "",
                             "why": clean(s.get("receipt"), ids)}
                            for s in f["source_list"] if not dirty(str(s.get("value")), ids)],
            "cards": len(rows)})

    # ---- paid: competitors' ads, longest running first, per advertiser
    comps = competitors(ws)
    by_brand = brand_competitors(ws, comps)
    advertisers, ads = [], []
    pulled = {}
    want = [(f"ad-{r['mid']}", r["a"]["image_url"]) for comp in comps
            for r in paid_ads(ws, comp)[:ADS_PER_ADVERTISER]
            if repix or not (old / "thumbs" / f"ad-{r['mid']}.webp").is_file()]
    from concurrent.futures import ThreadPoolExecutor

    def grab(x):
        try:
            return x[0], webp(fetch(x[1]), PAID_W)
        except Exception:
            return x[0], None
    with ThreadPoolExecutor(max_workers=12) as pool:
        pulled.update(pool.map(grab, want))
    for comp, name in comps.items():
        rows = paid_ads(ws, comp)[:ADS_PER_ADVERTISER]
        if not rows:
            continue
        mine = [b for b, cs in by_brand.items() if comp in cs]
        advertisers.append({"id": comp, "name": NAMES.get(comp, name), "brands": mine or ["general"],
                            "ads": 0})
        for r in rows:
            a = r["a"]
            aid = f"ad-{r['mid']}"
            row = {"id": aid, "adv": comp,
                   "headline": (a.get("title") or "").strip()[:140],
                   "copy": re.sub(r"\d{12,}\s*$", "", re.sub(r"\s+", " ", a.get("description") or "").strip())[:240],
                   "days": r["days"] or None, "copies": r["copies"],
                   "first": (a.get("first_seen") or "")[:10] or None, "last": (a.get("last_seen") or "")[:10] or None,
                   "video": bool(a.get("video_url")),
                   # The creative itself, on AdPlexity, not the Facebook Ad
                   # Library (the owner, 2 Oct). The library page often shows a
                   # dead ad or nothing at all; the file is the ad. Video ads
                   # open the mp4, image ads the jpg. Both are public.
                   "url": a.get("video_url") or a.get("image_url")
                          or f"https://www.facebook.com/ads/library/?id={r['mid']}"}
            row = {k: v for k, v in row.items() if v not in (None, "")}
            if dirty(json.dumps(row, ensure_ascii=False), ids):
                dropped += 1
                continue
            if thumb(aid, lambda aid=aid, u=a["image_url"]: pulled.get(aid) or webp(fetch(u), PAID_W)):
                row["thumb"] = 1
            if a.get("video_url") and blank(stage / "thumbs" / f"{aid}.webp"):
                frame = video_frame(a["video_url"])      # the library's poster was a grey play box
                if frame:
                    (stage / "thumbs" / f"{aid}.webp").write_bytes(frame)
                    row["thumb"] = 1
            ads.append(row)
            advertisers[-1]["ads"] += 1
    ads.sort(key=lambda r: (-(r.get("days") or 0), -r["copies"]))
    (stage / "ads.json").write_text(json.dumps(ads, ensure_ascii=False, separators=(",", ":")))

    index = {"updated": f"Updated {date.today().strftime('%-d %b %Y')}",
             "built": date.today().isoformat(),
             "feeds": feeds_out, "brands": sorted({f["brand"] for f in feeds_out} - {"general"}), "advertisers": advertisers,
             "posts": n_cards, "ads": len(ads),
             "prompts": prompts(ws, ids), "formats": formats(ids), "sounds": sounds(records, ids, stage)}
    (stage / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    return index, dropped, ids


# ---------------------------------------------------------------- the drawers
def prompts(ws, ids):
    """The prompts the desk shows verbatim — templates only, never as-sent."""
    files = [*sorted(D.PROMPTS.glob("feed-*.md")),
             *sorted((ws / "tools/copywriter/prompts/video/stage-1b-audience").glob("*-v10-*.md")),
             *sorted((ws / "tools/copywriter/prompts/video/stage-4-loop/4b-hook").glob("*-v15-*.md"))]
    return {p.name: p.read_text() for p in files if not dirty(p.read_text(), ids)}


def formats(ids):
    lib = json.loads((HERE / "formats.json").read_text())
    keep = ("id", "name", "mechanic", "why_it_works", "beats", "text_behaviour", "camera",
            "status", "state", "family", "differs_by", "text_mechanic")
    out = []
    for f in lib["formats"]:
        row = {k: f.get(k) for k in keep if f.get(k)}
        ev = (f.get("evidence") or [{}])[0]
        if "code" in ev:
            row["proof"] = {"url": f"https://www.instagram.com/p/{ev['code']}/", "author": ev.get("author"),
                            "line": ev.get("line"), "views": ev.get("views")}
        else:
            row["proof"] = {"line": ev.get("note") or ev.get("clip") or "", "author": ev.get("creator") or "our own footage"}
        pr = f.get("proof") or {}
        row["posts"] = pr.get("posts", len(f.get("evidence") or []))
        row["best"] = pr.get("best_views") or 0
        if not dirty(json.dumps(row, ensure_ascii=False), ids):
            out.append(row)
    out.sort(key=lambda r: (-r["posts"], -r["best"]))
    return out


def sounds(records, ids, stage=None):
    """This week's trending sounds, as the /sounds page lists them — read
    only: no keep/skip, no pull button. The mp3 the desk plays is copied
    beside the data so the site plays it too."""
    try:
        rows = json.loads((records / "sounds" / "pool.json").read_text())["rows"].values()
    except Exception:
        return []
    out = []
    for r in rows:
        t = r.get("tags") or {}
        if t.get("classic_meme") or r.get("off_chart_since"):
            continue
        row = {k: r.get(k) for k in ("title", "artist", "seconds", "url", "rank", "bpm", "lanes", "first_seen")
               if r.get(k) not in (None, "")}
        row.update({k: t.get(k) for k in ("mood", "energy", "use", "why") if t.get(k)})
        mp3 = records / "sounds" / "audio" / f"{r.get('id')}.mp3"
        if stage is not None and r.get("id") and mp3.is_file():
            (stage / "sounds").mkdir(exist_ok=True)
            shutil.copy2(mp3, stage / "sounds" / mp3.name)
            row["audio"] = f"sounds/{mp3.name}"
        if row.get("url") and not dirty(json.dumps(row, ensure_ascii=False), ids):
            out.append(row)
    return sorted(out, key=lambda r: r.get("rank") or 999)


# ---------------------------------------------------------------- paid
def competitors(ws):
    root = ws / "components" / "swipe-paid"
    out = {}
    for d in sorted(root.iterdir()):
        if not (d / "blocks.json").is_file() or not (d / "_raw").is_dir():
            continue
        if packs.OURS.search(d.name):
            continue
        name = d.name
        bf = d / "_BRAND.md"
        if bf.is_file():
            head = bf.read_text().splitlines()[0].lstrip("# ").strip()
            name = head if head and head.lower() != d.name else name
        out[d.name] = name
    return out


# Competitor display names: each competitor folder's own _BRAND.md heading (see above), or
# PRIZM_COMPETITOR_NAMES="slug=Name,slug=Name" for a label the folder does not carry.
# Competitor names are brand data and never ship in code.
NAMES = dict(kv.split("=", 1) for kv in os.environ.get("PRIZM_COMPETITOR_NAMES", "").split(",") if "=" in kv)


def paid_ads(ws, comp):
    ads = {}
    for f in sorted((ws / "components" / "swipe-paid" / comp / "_raw").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        its = d.get("items") if isinstance(d, dict) and isinstance(d.get("items"), list) else \
            [d] if isinstance(d, dict) and "id" in d else []
        for it in its:
            if isinstance(it, dict) and it.get("id"):
                ads.setdefault(str(it["id"]), {}).update({k: v for k, v in it.items() if v not in (None, "")})
    rows = []
    for a in ads.values():
        mid = str(a.get("meta_ad_id") or "")
        if not mid.isdigit() or not a.get("image_url"):
            continue
        try:
            days = int(a.get("days_total") or 0)
        except ValueError:
            days = 0
        rows.append({"a": a, "mid": mid, "days": days,
                     "copies": int(a.get("meta_group_ads_count") or 1)})
    rows.sort(key=lambda r: (-r["days"], -r["copies"]))
    return rows


def brand_competitors(ws, comps):
    """Which competitors each of our product worlds names, read from the
    brand's own angles file — the matching the Paid lane's brand pills and
    avatar picker use."""
    out = {}
    for b in sorted((ws / "brands").iterdir()):
        f = b / "strategy" / "angles.json"
        if b.name.startswith("_") or not f.is_file():
            continue
        text = f.read_text().lower()
        out[b.name] = [c for c in comps if c in text or NAMES.get(c, "~").lower() in text]
    return out


def sizes(stage, old):
    thumbs = sum(p.stat().st_size for p in (stage / "thumbs").glob("*"))
    total = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file())
    changed = 0
    for p in stage.rglob("*"):
        if not p.is_file():
            continue
        q = old / p.relative_to(stage)
        if not q.is_file() or q.read_bytes() != p.read_bytes():
            changed += p.stat().st_size
    return thumbs, total, changed


# ---------------------------------------------------------------- the delete guard
def site_is_ours(site):
    """True only when replacing `site` replaces this export's own copy (O5b (export
    replace is deploy)): it does not exist, is an empty folder, or holds the
    index.json build() writes, carrying `feeds` and `posts`. Anything else is
    somebody else's folder, and deleting it is the delete wall (swipe-organic#32)."""
    site = Path(site)
    if not site.exists() and not site.is_symlink():
        return True
    if site.is_symlink() or not site.is_dir():
        return False
    if not any(site.iterdir()):
        return True
    try:
        index = json.loads((site / "index.json").read_text())
    except (OSError, ValueError):
        return False
    return isinstance(index, dict) and "feeds" in index and "posts" in index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(DEFAULT_SITE))
    ap.add_argument("--records", default=str(HERE / "records"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--first", action="store_true", help="full rebuild: skip the daily-change limit")
    ap.add_argument("--repix", action="store_true",
                    help="re-make every picture instead of reusing the last export's "
                         "(use after changing width or quality)")
    a = ap.parse_args()
    records = Path(a.records).expanduser()
    if not (records / "avatar-feeds").is_dir():
        sys.exit(f"no feed records at {records}")
    ws = packs._workspace()
    site = Path(a.site).expanduser()
    if not a.dry_run and not site.parent.is_dir():
        sys.exit(f"no site checkout at {site.parent} — nothing written")
    old = site if site.is_dir() else Path(tempfile.mkdtemp())
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "data"
        index, dropped, ids = build(records, ws, stage, old, a.repix)
        hits = scan(stage, ids)
        thumbs, total, changed = sizes(stage, old)
        print(f"feeds {len(index['feeds'])} · posts {index['posts']} · ads {index['ads']} · "
              f"rows held back {dropped}")
        print(f"pictures {thumbs/1e6:.1f} MB · all {total/1e6:.1f} MB · changed {changed/1e6:.2f} MB")
        if hits:
            print("REFUSED — the no-secrets scan found:")
            for h in hits[:20]:
                print("   ", h)
            sys.exit(1)
        print("no-secrets scan: clean")
        if thumbs > THUMBS_MAX:
            sys.exit(f"REFUSED — pictures are {thumbs/1e6:.1f} MB, the limit is {THUMBS_MAX/1e6:.0f} MB")
        first = a.first or not (site / "cards").is_dir()
        if changed > DAILY_MAX and not first:
            sys.exit(f"REFUSED — {changed/1e6:.1f} MB changed in one run, the limit is {DAILY_MAX/1e6:.0f} MB "
                     "(pass --first for a full rebuild)")
        print("size check: pass")
        if a.dry_run:
            return
        if not site_is_ours(site):
            sys.exit(f"REFUSED — {site} is not this export's own folder "
                     "(no index.json from feedsexport); nothing deleted")
        if site.exists():
            shutil.rmtree(site)
        shutil.copytree(stage, site)
        print(f"wrote {site}")


if __name__ == "__main__":
    main()
