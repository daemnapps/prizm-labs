#!/usr/bin/env python3
"""THE SWIPES INDEX — one living row per swipe, so a tool reads one file instead of digging through nine pools.

The same front door as the product index (tools/video-production/machine/product_index.py), for swipes. The
audit that asked for it: components/naming/WHERE-EVERYTHING-GOES-damon.md ("swipes in about 9 places ... the Drive
swipe front door is stale ... no index for swipes").

Built from, read only:

  the swipe pools, read live through pools.py      every swipe saved for the brand, plus every `shared` one
  runs/intake/<brand>/<label>/swipes.jsonl          every earlier intake snapshot (a swipe a pool no longer holds stays)
  runs/video-teardown/VIDEO-INDEX.json              which source videos were torn down, by which run, into which briefs
  tools/image-teardown/briefs.json             the brief register: brief numbers, and the paid blocks image briefs came from

It writes:

  runs/intake/<brand>/SWIPES-INDEX.json            every swipe, one row per line, for machines
  runs/intake/<brand>/SWIPES.md                    the front page, for people: counts, every torn-down swipe, every pool
  Shared Assets/SWIPE LIBRARY.md                   the Drive front door, regenerated from both (only from the real
                                                   workspace with the Drive mounted; that one file, overwritten in place)

Every path is repo-relative or a "Shared Assets/..." label — never a machine path.

Read it, never re-scan:  import swipes_index as SI;  SI.find_swipe("<brand>", "<swipe id or post url>")

    python3 components/intake/tools/swipes_index.py --brand <brand> [--no-drive]    (every intake run rebuilds it too)
"""
import argparse
import collections
import datetime
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))                              # appended, never inserted at 0

import paths as P                                           # noqa: E402

INDEX = "SWIPES-INDEX.json"
FRONT = "SWIPES.md"
LIBRARY = "SWIPE LIBRARY.md"
MAX_BYTES = 9_500_000                                       # media and files over 10 MB never go in git


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


# ── the video key: the same rule as tools/video-teardown/machine/video_index.py key_of_url (copied, not
#    imported: importing that module opens the teardown's working folder) ─────────────────────────────────────
def key_of_url(u):
    u = (u or "").strip()
    if not u:
        return None
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", u)
    if m:
        return "ig:" + m.group(1)
    m = re.search(r"tiktok\.com/.*?/video/(\d+)", u) or re.search(r"tiktok\.com/.*?(\d{15,})", u)
    if m:
        return "tt:" + m.group(1)
    m = re.search(r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})", u)
    if m:
        return "yt:" + m.group(1)
    if "drive.google.com" in u:
        return None
    return "url:" + u.split("?")[0].rstrip("/")


def label(v):
    """A stored media location as a Drive label, a link, or a repo path — never a machine path."""
    v = (v or "").strip()
    if not v:
        return None
    if "Shared Assets/" in v:
        return "Shared Assets/" + v.split("Shared Assets/", 1)[1]
    if v.startswith(("http://", "https://")):
        return v
    if v.startswith("/"):
        ws = str(P.workspace()) + "/"
        return v[len(ws):] if v.startswith(ws) else None
    return v


# ── the sources ─────────────────────────────────────────────────────────────
def snapshots(brand):
    """Every intake snapshot for the brand, oldest first (by its run.json `when`)."""
    base = P.workspace() / "runs" / P.TOOL / brand
    out = []
    for f in base.glob("*/swipes.jsonl"):
        when = (_json(f.parent / "run.json") or {}).get("when") or ""
        out.append((when, f.parent.name, f))
    return sorted(out)


def live(brand):
    import pools
    try:
        return [r for r in pools.read_all() if pools.matches(r, brand)]
    except Exception as e:  # noqa: BLE001 — a pool that cannot be read leaves the snapshots standing
        print(f"  swipes index: the live pools could not be read ({type(e).__name__}: {e}); snapshots only")
        return []


def teardowns():
    """VIDEO-INDEX.json: key -> {record, runs, finished, brand, briefs}."""
    vi = (_json(P.workspace() / "runs" / "video-teardown" / "VIDEO-INDEX.json") or {}).get("videos") or {}
    out = {}
    for k, v in vi.items():
        runs = v.get("runs") or []
        rec = next((r for r in runs if r.get("slug") == v.get("record")), runs[0] if runs else {})
        out[k] = {"record": v.get("record"), "brand": rec.get("brand"), "runs": len(runs),
                  "finished": any(r.get("finished") for r in runs), "briefs": [b.get("id") for b in v.get("briefs") or []]}
    return out


def register():
    """The brief register: id -> brief number, and (advertiser, block) -> image briefs made from that paid block."""
    reg = _json(P.workspace() / "tools" / "image-teardown" / "briefs.json") or {}
    number, blocks = {}, collections.defaultdict(list)
    for shelf in ("briefs", "retired"):
        for bid, b in (reg.get(shelf) or {}).items():
            m = re.search(r"(\d{3,4})", str(b.get("brief") or ""))
            number[bid] = m.group(1).zfill(4) if m else None
            sw = b.get("swipe") or {}
            if sw.get("block_file") and sw.get("brand"):
                blocks[(sw["brand"], Path(sw["block_file"]).stem)].append(bid)
    return number, blocks


def _run_path(slug, brand):
    ws = P.workspace() / "runs" / "video-teardown"
    for d in ([ws / brand / slug] if brand else []) + [ws / "_work" / slug]:
        if d.is_dir():
            return str(d.relative_to(P.workspace())) + "/"
    return None


# ── every other place a swipe is kept (2026-10-28, WHERE-EVERYTHING-GOES-damon.md item 6: "swipes in about 9") ──
# Each is read here as a SOURCE of the one index, read only, never moved. A swipe one of them shares with a pool (the
# same post) is one row with `also_in`; one only it holds is a row of its own.
PLACES = [
    ("pools", "components/swipe-paid/<advertiser>/blocks.json, pages.json; own/<account>/ads.json",
     "paid ads, their landing pages, our own ads (pools.py)"),
    ("pools", "components/swipe-organic/records/avatar-feeds/<feed>/items.json, records/swipe-videos/<code>/, <name>/posts.json",
     "organic posts: My Feeds, pulled videos, pulled sets (pools.py)"),
    ("snapshots", "runs/intake/<brand>/<label>/swipes.jsonl", "every earlier intake snapshot"),
    ("teardowns", "runs/video-teardown/VIDEO-INDEX.json", "which videos were torn down, into which briefs"),
    ("picture teardowns", "runs/image-teardown/<brand>/<run>/source.json", "the post each picture teardown read"),
    ("picks", "runs/creative-strategist/<brand>/<set>/picks.json", "the creative strategist's picked swipes"),
    ("research rounds", "runs/swipe-organic/<brand>/<round>/ranking.json, manifest.json", "ranked posts per avatar"),
    ("copy swipes", "runs/copywriter/<brand>/_swipe-sources*/<file>.md", "words the copywriter swiped"),
    ("lab registries", "lab/damon/swipes/<pool>/registry.md", "the hand-kept shared registries (competitor ads, "
                                                                  "landing pages, organic posts)"),
]


def _rec(lane, where, ref, source, kind, brand, pool, url=None, file=None, drive=None, title="", **extra):
    return dict({"id": f"swipe:{lane}:{where}:{ref}", "source": source, "kind": kind, "swiped_for": brand,
                 "pool": pool, "title": title, "asset": {"url": url, "file": file, "drive": drive}}, **extra)


def other_places(brand):
    """Swipe records from every place outside the two pools (PLACES), for one brand; shared registries for every
    brand. Read only."""
    ws = P.workspace()
    out = []
    for f in sorted(ws.glob(f"runs/image-teardown/{brand}/*/source.json")):
        d = _json(f) or {}
        url = d.get("post_url") or d.get("url")
        if url or d.get("drive"):
            run = f.parent.relative_to(ws).as_posix() + "/"
            kind = "carousel" if (d.get("slide_count") or 0) > 1 else "image"
            out.append(_rec("teardown", "image", f.parent.name, "organic" if d.get("creator") else "paid", kind, brand,
                            run + "source.json", url=url, drive=label(d.get("drive")), _teardown=run))
    for f in sorted(ws.glob(f"runs/creative-strategist/{brand}/*/picks.json")):
        for it in (_json(f) or []) if isinstance(_json(f), list) else []:
            if isinstance(it, dict) and (it.get("url") or it.get("id")):
                out.append(_rec("pick", f.parent.name, it.get("id") or it["url"], "organic", it.get("kind") or "unknown",
                                brand, f.relative_to(ws).as_posix(), url=it.get("url"), file=it.get("file"),
                                title=it.get("caption") or ""))
    for f in sorted(ws.glob(f"runs/swipe-organic/{brand}/*/ranking.json")) + \
            sorted(ws.glob(f"runs/swipe-organic/{brand}/*/manifest.json")):
        d = _json(f) or {}
        items = next((v for v in (d.get("top"), d.get("posts"), d.get("ranked")) if isinstance(v, list)), []) \
            if isinstance(d, dict) else []
        for it in items:
            url = isinstance(it, dict) and (it.get("url") or it.get("webVideoUrl"))
            if url:
                out.append(_rec("research", f.parent.name, it.get("videoId") or it.get("id") or url, "organic", "video",
                                brand, f.relative_to(ws).as_posix(), url=url, title=it.get("caption") or ""))
    for f in sorted(ws.glob(f"runs/copywriter/{brand}/_swipe-sources*/*.md")):
        out.append(_rec("copy", f.parent.name.lstrip("_"), f.stem, "own" if f.parent.name.endswith("-own") else "paid",
                        "copy", brand, f.parent.relative_to(ws).as_posix() + "/", file=f.relative_to(ws).as_posix()))
    pool_kind = {"competitor-ads": ("paid", None), "landing-pages": ("paid", "page"), "organic-posts": ("organic", None)}
    for f in sorted(ws.glob("lab/damon/swipes/*/registry.md")):
        src, kind = pool_kind.get(f.parent.name, ("paid", None))
        for line in f.read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or not re.match(r"^[a-z]{2,4}-\d{3}$", cells[0]):
                continue
            url = re.search(r"https?://\S+", cells[2])
            k = kind or ("video" if "video" in cells[3].lower() else "image" if "static" in cells[3].lower() else "unknown")
            out.append(_rec("registry", f.parent.name, cells[0], src, k, "shared", f.relative_to(ws).as_posix(),
                            url=url.group(0).rstrip(")") if url else None, title=cells[7] if len(cells) > 7 else ""))
    return out


# ── one row ─────────────────────────────────────────────────────────────────
def _pool_name(r):
    parts = (r.get("pool") or "").split("/")
    if "avatar-feeds" in parts:
        return parts[parts.index("avatar-feeds") + 1]
    if len(parts) >= 3 and parts[1] == "swipe-paid":
        return parts[3] if parts[2] == "own" and len(parts) > 3 else parts[2]
    if len(parts) >= 3 and parts[1] == "swipe-organic":
        return parts[2]
    return r.get("pool") or None


def _owner(r, pool):
    url = (r.get("asset") or {}).get("url") or ""
    if r.get("source") == "organic":
        m = re.search(r"tiktok\.com/@([^/?]+)", url) or re.search(r"instagram\.com/([^/?]+)/(?:p|reel|reels)/", url)
        return "@" + m.group(1) if m else pool
    return pool                                             # paid: the advertiser · own: the ad account


def row(r, tear, number, blocks, seen_in, in_pools, brand):
    a = r.get("asset") or {}
    pool = _pool_name(r)
    lane = pool.split("--", 1)[1] if pool and "--" in pool else None
    drive = label(a.get("drive"))
    key = key_of_url(a.get("url"))
    if not key and drive:
        m = re.search(r"swipe-videos/([A-Za-z0-9_-]{6,})/", drive)
        key = "ig:" + m.group(1) if m and not m.group(1).isdigit() else ("tt:" + m.group(1) if m else None)
    t = tear.get(key) if key else None
    if not t and r.get("_teardown"):                       # read by a picture teardown (its source.json)
        t = {"record": r["_teardown"].rstrip("/").split("/")[-1], "run": r["_teardown"], "runs": 1, "finished": True,
             "briefs": [], "by": "image-teardown"}
    briefs = list(t["briefs"]) if t else []
    via = block = None
    if r.get("source") == "paid":
        m = (re.search(r"swipe/paid/([^/]+)/blocks/([^/]+)/", drive or "")
             or re.search(r"swipe-paid/([^/]+)/blocks/([^/]+)\.md$", a.get("file") or ""))
        made = blocks.get((m.group(1), m.group(2))) if m else None
        if made and r.get("kind") == "copy":                # the block itself: image briefs were made from it
            briefs += [b for b in made if b not in briefs]
            via = "image-teardown, from this paid block"
        elif made:
            block = len(made)                               # its block was briefed; which picture is not recorded
    out = {"id": r["id"], "source": r.get("source"), "lane": lane, "kind": r.get("kind"),
           "owner": _owner(r, pool), "whose": r.get("owner"), "swiped_for": r.get("swiped_for"),
           "title": (r.get("title") or "")[:100] or None, "url": a.get("url") or None, "drive": drive,
           "file": label(a.get("file")), "format": r.get("format") or None, "structure": r.get("structure") or None,
           "torn_down": bool(t) or bool(via),
           "teardown": ({"record": t["record"], "run": t.get("run") or _run_path(t["record"], t.get("brand") or brand),
                         "runs": t["runs"], "finished": t["finished"], "video": key, "by": t.get("by")} if t else
                        ({"by": "image-teardown", "via": via} if via else None)),
           "briefs": [{"id": b, "number": number.get(b)} for b in briefs],
           "block_briefs": block, "also_in": r.get("also_in")}
    if pool != out["owner"]:
        out["pool"] = pool
    if not in_pools:
        out["in_pools_now"], out["last_seen_in"] = False, seen_in
    return {k: v for k, v in out.items() if v not in (None, [], "")}


def collect(brand):
    tear = teardowns()
    number, blocks = register()
    rows = {}
    for when, lab, f in snapshots(brand):
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("id"):
                rows[r["id"]] = (r, f"runs/{P.TOOL}/{brand}/{lab}", False)
    for r in live(brand):
        rows[r["id"]] = (r, "the pools today", True)
    by_key = {}
    for rid, (r, _, _) in rows.items():
        k = key_of_url((r.get("asset") or {}).get("url"))
        if k:
            by_key.setdefault(k, rid)
    for r in other_places(brand):                          # every other place, one row per swipe
        k = key_of_url(r["asset"].get("url"))
        hit = rows.get(by_key.get(k)) if k else None
        if hit:
            hit[0].setdefault("also_in", [])
            if r["pool"] not in hit[0]["also_in"]:
                hit[0]["also_in"].append(r["pool"])
            if r.get("_teardown") and not hit[0].get("_teardown"):
                hit[0]["_teardown"] = r["_teardown"]
            continue
        rows.setdefault(r["id"], (r, r["pool"], True))
        if k:
            by_key.setdefault(k, r["id"])
    return [row(r, tear, number, blocks, seen, now, brand) for r, seen, now in rows.values()]


# ── the pages ───────────────────────────────────────────────────────────────
def _name(r):
    """What a person clicks: the post's link for media, the swipe id for a copy block or page (its url is the advertiser's page)."""
    u = r.get("url") if r.get("kind") in ("video", "image", "carousel") else None
    return (u or r["id"])[:100]


def _md_cell(s, n=80):
    return re.sub(r"\s+", " ", str(s or "—"))[:n].replace("|", "/")


def front(brand, rows, built):
    c = collections.Counter
    torn = [r for r in rows if r.get("torn_down") or r.get("briefs")]
    L = [f"# Swipes — {brand}", "",
         "Every swipe saved for this brand (and every `shared` one), one row each across every pool. Machines read "
         f"`{INDEX}` (one row per line; `components/intake/tools/swipes_index.py find_swipe(brand, id_or_url)`). "
         "Rebuilt by every intake run; never edit by hand.", "",
         f"**{len(rows):,} swipes** · {len(torn):,} torn down or briefed · "
         f"{sum(1 for r in rows if r.get('in_pools_now', True)):,} in the pools today · built {built}", "",
         "## By source and kind", "", "| source | kind | swipes | torn down |", "|---|---|---:|---:|"]
    by = c((r.get("source"), r.get("kind")) for r in rows)
    td = c((r.get("source"), r.get("kind")) for r in torn)
    L += [f"| {s} | {k} | {n:,} | {td.get((s, k), 0):,} |" for (s, k), n in sorted(by.items(), key=lambda x: (str(x[0][0]), str(x[0][1])))]
    L += ["", f"## Torn down or briefed ({len(torn)})", "",
          "| Swipe | Kind | Owner | Teardown | Briefs | Media on the Drive |", "|---|---|---|---|---|---|"]
    for r in sorted(torn, key=lambda r: (-len(r.get("briefs") or []), r["id"])):
        t = r.get("teardown") or {}
        td_cell = (f"`{t['run']}`" if t.get("run") else t.get("record") or t.get("via") or "—") + \
                  (f" ({t['runs']} runs)" if (t.get("runs") or 0) > 1 else "")
        br = ", ".join(f"{b['number'] or b['id']}" for b in r.get("briefs") or []) or "—"
        L.append(f"| {_name(r)} | {r.get('kind')} | {_md_cell(r.get('owner'), 30)} | {td_cell} | {br} | "
                 f"{'`' + r['drive'] + '`' if r.get('drive') and not r['drive'].startswith('http') else '—'} |")
    pools = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (str(r.get("source")), str(r.get("pool") or r.get("owner")))):
        p = pools.setdefault((r.get("source"), r.get("pool") or r.get("owner")), {"n": 0, "kinds": c(), "torn": 0, "drive": None})
        p["n"] += 1
        p["kinds"][r.get("kind")] += 1
        p["torn"] += 1 if r.get("torn_down") else 0
        if not p["drive"] and r.get("drive") and r["drive"].startswith("Shared Assets/"):
            d = r["drive"]
            m = re.match(r"(Shared Assets/swipe/paid/[^/]+/|Shared Assets/swipe/organic/records/swipe-videos/|Shared Assets/[^/]+/[^/]+/[^/]+/)", d)
            p["drive"] = m.group(1) if m else d.rsplit("/", 1)[0] + "/"
    L += ["", f"## Every pool ({len(pools)})", "", "| Source | Pool | Swipes | Kinds | Torn down | Media home on the Drive |",
          "|---|---|---:|---|---:|---|"]
    for (s, p), v in pools.items():
        L.append(f"| {s} | {_md_cell(p, 50)} | {v['n']:,} | " + ", ".join(f"{k} {n}" for k, n in v["kinds"].most_common())
                 + f" | {v['torn']} | {'`' + v['drive'] + '`' if v['drive'] else '—'} |")
    return "\n".join(L) + "\n"


def drive_pools(m):
    """Today's pool folders on the Drive, by listing (only where the Drive is mounted): {"paid": [...], ...}."""
    out = {}
    for lane in ("paid", "organic", "picks"):
        d = Path(m) / "swipe" / lane
        try:
            out[lane] = sorted(x.name for x in d.iterdir() if x.is_dir() and not x.name.startswith("."))
        except OSError:
            out[lane] = []
    return out


def library(per_brand, built, pools_now=None):
    """The Drive front door, regenerated from every brand's index (a shared swipe counted once)."""
    allrows = {}
    for b, rows in per_brand.items():
        for r in rows:
            allrows.setdefault(r["id"], dict(r, brands=[]))["brands"].append(b)
    rows = list(allrows.values())
    c = collections.Counter
    L = ["# SWIPE LIBRARY", "",
         f"Everything swiped, in one place. Built {built} from the swipes index in the team repo "
         "(`runs/intake/<brand>/SWIPES.md` and `SWIPES-INDEX.json`, rebuilt by every intake run). Read this in "
         "Higgsfield Supercomputer (\"open the swipe library for <brand>\") or by hand. Generated — never edit by hand.", "",
         "| Brand | Swipes | Video | Image / carousel | Copy / page | Torn down or briefed | Index in the repo |",
         "|---|---:|---:|---:|---:|---:|---|"]
    for b, rs in sorted(per_brand.items()):
        k = c(r.get("kind") for r in rs)
        L.append(f"| {b} | {len(rs):,} | {k.get('video', 0):,} | {k.get('image', 0) + k.get('carousel', 0):,} | "
                 f"{k.get('copy', 0) + k.get('page', 0):,} | {sum(1 for r in rs if r.get('torn_down') or r.get('briefs')):,} | "
                 f"`runs/intake/{b}/SWIPES.md` |")
    L += ["", "`shared` swipes (a competitor's ad library, a general feed) appear under every brand; below they are counted once.", "",
          "## Where the media is", "",
          "| What | Where on this drive |", "|---|---|",
          "| Paid — every competitor's ads, blocked by angle | `swipe/paid/<advertiser>/blocks/<block>/` — `video/`, `photos/`; landing pages in `_pages/` |",
          "| Organic — every pulled post | `swipe/organic/records/swipe-videos/<code>/video.mp4` |",
          "| Organic — My Feeds, one per sub-avatar | listed in the team repo, `components/swipe-organic/records/avatar-feeds/<feed>/` |",
          "| Teardowns | `runs/video-teardown/<brand>/<run>/` and `runs/image-teardown/<brand>/<run>/` |", ""]
    if pools_now:
        L += ["## Today's pool folders on this drive", "", "| Folder | Pools |", "|---|---|"]
        L += [f"| `swipe/{lane}/` | " + (", ".join(f"`{n}`" for n in names) or "—") + " |"
              for lane, names in pools_now.items()]
        L += ["", "Older homes on this drive (kept, not where new swipes go): `components/swipe-paid/`, "
                  "`components/swipe-organic/`. New swipes are saved into `swipe/` above.", ""]
    L += ["## Every place a swipe is kept — all of them feed the index", "", "| Place | Where (team repo) | What |",
          "|---|---|---|"]
    L += [f"| {a} | `{b}` | {c} |" for a, b, c in PLACES]
    L += ["", "A swipe held in two places is one row; the second place is in its `also_in`.", "",
          "## Pools", "", "| Source | Pool | Swipes | Torn down | Brands |", "|---|---|---:|---:|---|"]
    pools = collections.defaultdict(lambda: {"n": 0, "torn": 0, "brands": set()})
    for r in rows:
        p = pools[(r.get("source"), r.get("pool") or r.get("owner"))]
        p["n"] += 1
        p["torn"] += 1 if r.get("torn_down") else 0
        p["brands"].update(r["brands"] if r.get("swiped_for") != "shared" else ["shared"])
    for (s, p), v in sorted(pools.items(), key=lambda x: (str(x[0][0]), -x[1]["n"])):
        L.append(f"| {s} | {_md_cell(p, 50)} | {v['n']:,} | {v['torn']} | {', '.join(sorted(v['brands']))} |")
    torn = [r for r in rows if r.get("torn_down") or r.get("briefs")]
    L += ["", f"## Torn down or briefed ({len(torn)})", "", "| Swipe | Kind | Owner | Teardown run | Briefs |", "|---|---|---|---|---|"]
    for r in sorted(torn, key=lambda r: (-len(r.get("briefs") or []), r["id"])):
        t = r.get("teardown") or {}
        L.append(f"| {_name(r)} | {r.get('kind')} | {_md_cell(r.get('owner'), 30)} | "
                 f"{t.get('run') or t.get('record') or t.get('via') or '—'} | "
                 f"{', '.join(b['number'] or b['id'] for b in r.get('briefs') or []) or '—'} |")
    return "\n".join(L) + "\n"


def _mount():
    if os.environ.get("DRIVE_MOUNT") == "off":
        return None
    sys.path.append(str(P.code_repo() / "components" / "brandpath"))
    try:
        import drive_index
        return drive_index.mount()
    except Exception:  # noqa: BLE001
        return None


def write_index(brand, rows, built):
    out = P.workspace() / "runs" / P.TOOL / brand
    out.mkdir(parents=True, exist_ok=True)
    head = {"built": built, "brand": brand, "read_with": "swipes_index.find_swipe(brand, id_or_url)",
            "swipes": len(rows), "torn_down": sum(1 for r in rows if r.get("torn_down"))}
    body = ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in sorted(rows, key=lambda r: r["id"]))
    text = json.dumps(head, ensure_ascii=False)[:-1] + ',"rows":[\n' + body + "\n]}\n"
    if len(text.encode()) > MAX_BYTES:
        print(f"  swipes index: {brand} is {len(text.encode()):,} bytes — over the git limit; titles dropped to fit")
        for r in rows:
            r.pop("title", None)
        body = ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in sorted(rows, key=lambda r: r["id"]))
        text = json.dumps(head, ensure_ascii=False)[:-1] + ',"rows":[\n' + body + "\n]}\n"
    (out / INDEX).write_text(text)
    (out / FRONT).write_text(front(brand, rows, built))
    return out


def build(brand=None, drive=True, log=print):
    """Rebuild the brand's index (or every brand's), then the Drive front door from every brand's index."""
    built = datetime.datetime.now().isoformat(timespec="seconds")
    brands = [brand] if brand else P.brands()
    counts = {}
    for b in brands:
        rows = collect(b)
        out = write_index(b, rows, built)
        counts[b] = {"swipes": len(rows), "torn_down": sum(1 for r in rows if r.get("torn_down")),
                     "briefed": sum(1 for r in rows if r.get("briefs"))}
        log(f"  swipes index: {b} — {len(rows):,} swipes, {counts[b]['torn_down']} torn down → "
            f"{out.relative_to(P.workspace())}/{INDEX}, {FRONT}")
    real = P.workspace().resolve() == P.code_repo().resolve()
    m = _mount() if (drive and real) else None
    if m:
        per = {}
        for b in P.brands():
            doc = _json(P.workspace() / "runs" / P.TOOL / b / INDEX)
            if doc:
                per[b] = doc["rows"]
        (Path(m) / LIBRARY).write_text(library(per, built, drive_pools(m)))   # that one generated file, in place
        log(f"  swipe library: Shared Assets/{LIBRARY} regenerated from {', '.join(sorted(per))}")
    elif drive and real:
        log(f"  swipe library: the Drive is not mounted here — Shared Assets/{LIBRARY} not regenerated")
    return counts


def find_swipe(brand, id_or_url):
    """The swipe's row — by its id, its post url, or its video key (ig:<code>, tt:<id>). Reads the index; builds it
    once if missing."""
    f = P.workspace() / "runs" / P.TOOL / brand / INDEX
    if not f.is_file():
        build(brand, drive=False, log=lambda *_: None)
    s = str(id_or_url)
    k = key_of_url(s) if s.startswith("http") else (s if re.match(r"^(ig|tt|yt|url):", s) else None)
    for r in json.loads(f.read_text())["rows"]:
        if r["id"] == s or r.get("url") == s or (k and key_of_url(r.get("url")) == k):
            return r
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", help="one brand (default: every brand)")
    ap.add_argument("--no-drive", action="store_true", help="do not regenerate the Drive's SWIPE LIBRARY.md")
    ap.add_argument("--find")
    a = ap.parse_args(argv)
    if a.find:
        print(json.dumps(find_swipe(a.brand, a.find), indent=1, ensure_ascii=False))
        return 0
    build(a.brand, drive=not a.no_drive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
