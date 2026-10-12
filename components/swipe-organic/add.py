#!/usr/bin/env python3
"""THE SAVE DOOR — a swipe you found by hand, filed so the system can see it.

    python3 add.py --pool tiktok-shop --brand brand-a ~/Downloads/*.mp4
    python3 add.py --pool competitor-pool --brand brand-a --url https://www.tiktok.com/@x/video/123
    python3 add.py --check                       what is filed but not on the Drive
    python3 add.py --pool tiktok-shop --list     what that pool holds

the owner, 2026-09-25, after thirteen swipes he handed over were stored but
invisible: "there will be multiple sources for me to pull swipes in and they
all need to be organized and indexed through proper lanes."

WHY A SWIPE GOES MISSING. Saving a swipe is three things, and doing two of
them looks exactly like doing all three:

    1. the media    lands in the library    records/swipe-videos/<id>/
    2. the Drive    the media is mirrored   Shared Assets/…/swipe-videos/<id>/
    3. the ROW      a line in a posts.json  <pool>/posts.json

`components/intake` builds the index from the ROWS — never by walking the
media. So a file dropped into the library is stored and unfindable: no brand
tool, no teardown and no board can see it. That is precisely what happened to
the thirteen. This door does all three, every time, or it does none of them.

WHAT A LANE IS. Not a folder — four fields the index already understands:

    source   organic · paid · own        where we found it
    owner    creator · competitor · own  whose it is
    kind     video · image · carousel …  read off the asset
    brand    the brand it was swiped for, or shared

A pool (`--pool`) is just a name for one batch from one place — `tiktok-shop`,
`competitor-pool`, `reddit-finds`. The lane is what routes it; the pool is what you
call it. Both are written into the row, so a swipe can always say where it
came from and which teardown it goes to.

NO SCRAPER NEEDED. A TikTok id resolves through the site's own oembed and
yt-dlp — author, caption, views — with no Apify allowance spent. That matters:
on 2026-09-24 the Apify cap was spent and a whole source was unreachable, while
the same facts sat one public request away.
"""
import argparse, json, re, shutil, subprocess, sys, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)
for _r in HERE.parents:                # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
LIB = HERE / "records" / "swipe-videos"
DRIVE = swipe_home.path("organic", "records", "swipe-videos")
MEDIA = {".mp4", ".mov", ".m4v", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
VIDEO = {".mp4", ".mov", ".m4v", ".webm"}


def say(m):
    print(m, flush=True)


def workspace():
    """The workspace root — run-kit's paths.repo(), never counted (SI-111 (organic one locator))."""
    return repo(HERE)


# ------------------------------------------------------------------ the id
def id_of(path_or_url):
    """A swipe's id: the TikTok/Instagram code when there is one, else the
    file's own stem. It is what the media folder is named and what every row
    points at, so it has to come out the same every time."""
    s = str(path_or_url)
    m = re.search(r"/(?:video|reel|reels|p)/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    return re.sub(r"[^A-Za-z0-9_-]+", "-", Path(s).stem).strip("-")


# -------------------------------------------------------------- the facts
def tiktok_facts(code):
    """Author, caption and views for a TikTok id — the site's own doors, no
    Apify. Either one can be down; a missing fact is left empty, never
    guessed."""
    out = {}
    try:
        u = ("https://www.tiktok.com/oembed?url="
             + urllib.parse.quote(f"https://www.tiktok.com/@x/video/{code}"))
        with urllib.request.urlopen(u, timeout=30) as f:
            o = json.load(f)
        out["caption"] = o.get("title", "")
        out["author"] = (o.get("author_url") or "").rstrip("/").split("@")[-1]
        out["url"] = f"{o.get('author_url','https://www.tiktok.com')}/video/{code}"
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["yt-dlp", "--skip-download", "--print",
             "%(uploader)s\t%(view_count)s\t%(like_count)s\t%(comment_count)s\t%(duration)s",
             f"https://m.tiktok.com/v/{code}.html"],
            capture_output=True, text=True, timeout=120)
        p = r.stdout.strip().split("\t")
        if len(p) >= 5:
            out.setdefault("author", p[0])
            for k, v in zip(("views", "likes", "comments", "duration"), p[1:5]):
                out[k] = int(v) if v.isdigit() else 0
    except Exception:
        pass
    return out


def probe(f):
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                            "format=duration", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True, timeout=60)
        return int(float(r.stdout.strip() or 0))
    except Exception:
        return 0


def strip_of(video, out_dir):
    """Six stills across the runtime — what makes a format readable without
    opening the file (videos.py's rule, kept)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if list(out_dir.glob("*.jpg")):
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
                    "-vf", "fps=1/8,scale=360:-1", "-frames:v", "6",
                    str(out_dir / "%02d.jpg")], capture_output=True, timeout=300)


# ------------------------------------------------------------------ Drive
def mirror(code):
    """The media, on the Drive at the mirrored path. Copies missing files
    only; never deletes on either side (the Drive mount rule)."""
    src, dst = LIB / code, DRIVE / code
    if not DRIVE.parent.parent.exists():
        return False
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.rglob("*"):
        if f.is_file():
            t = dst / f.relative_to(src)
            t.parent.mkdir(parents=True, exist_ok=True)
            if not t.exists():
                shutil.copy2(f, t)
    return True


def check():
    """What is filed here but not on the Drive. The mirror broke silently once
    — when this library graduated out of `lab/` and the mirror kept pointing at
    the old path — and 135 swipes sat on one laptop for days. This is the
    question that would have caught it."""
    if not DRIVE.parent.parent.exists():
        say("  the Drive is not mounted — cannot say what is mirrored")
        return 1
    local = {p.name for p in LIB.glob("*") if p.is_dir()}
    there = {p.name for p in DRIVE.glob("*") if p.is_dir()}
    missing = sorted(local - there)
    say(f"  {len(local)} filed here · {len(there)} on the Drive · {len(missing)} local-only")
    for c in missing[:20]:
        say(f"    not mirrored: {c}")
    if len(missing) > 20:
        say(f"    … and {len(missing)-20} more")
    if missing:
        say("  mirror them:  python3 add.py --mirror-all")
    return len(missing)


# ------------------------------------------------------------------- rows
def pool_file(pool):
    return HERE / pool / "posts.json"


def load_pool(pool, brand, source, owner):
    f = pool_file(pool)
    if f.is_file():
        return json.loads(f.read_text())
    return {"_what": f"{pool} — swipes added by hand through add.py. Media in the "
                     "library and on the Drive; this file is what the intake index reads.",
            "brand": brand, "platform": "", "pulled": str(date.today()),
            "group": pool, "source": source, "owner": owner,
            "drive_root": "", "posts_seen": 0, "posts": []}


def record_md(pool, row, facts):
    """The readable record behind the row — a pointer that does not open is
    not a receipt."""
    d = HERE / pool / "posts"
    d.mkdir(parents=True, exist_ok=True)
    stem = Path(row["file"]).stem
    v = row.get("views") or 0
    (d / f"{stem}.md").write_text(
        f"""# {('@' + row['creator']) if row.get('creator') else stem} — {pool}

> Added by hand through `add.py` on {date.today()}. Media in the library and
> on the Drive at the path below; this is the record.

| | |
|---|---|
| Post | {row.get('url') or '*(no link — a file, not a post)*'} |
| Views | {v:,} |
| Runtime | {row.get('seconds') or '?'}s |
| Video | `{row['drive']}` |
| Lane | {row.get('source','organic')} · {row.get('owner','creator')} · {row.get('kind','video')} |

## Caption, as posted

{facts.get('caption') or '*(none)*'}
""")


def add(paths, urls, pool, brand, source, owner, note=""):
    LIB.mkdir(parents=True, exist_ok=True)
    doc = load_pool(pool, brand, source, owner)
    have = {p.get("id") for p in doc["posts"]}
    added, seen = [], []

    for u in urls:
        code = id_of(u)
        seen.append((code, None, u))
    for p in paths:
        f = Path(p).expanduser()
        if f.is_dir():
            seen += [(id_of(x), x, "") for x in sorted(f.iterdir())
                     if x.suffix.lower() in MEDIA]
        elif f.suffix.lower() in MEDIA:
            seen.append((id_of(f), f, ""))
        else:
            say(f"  skipped (not media): {f.name}")

    for code, src, url in seen:
        d = LIB / code
        d.mkdir(parents=True, exist_ok=True)
        # the kind is the SOURCE's (SI-159 (organic pool honest)): a video is
        # stored as video.mp4, the name its readers open; an image keeps its suffix
        if src:
            ext = Path(src).suffix.lower()
            media = d / ("video.mp4" if ext in VIDEO else f"image{ext}")
            if not media.exists():
                shutil.copy2(src, media)
        else:
            media = d / "video.mp4"
            if not media.exists():
                media = next(iter(sorted(d.glob("image.*"))), media)
        if not media.exists():
            say(f"  {code}: no media — a link alone is not a swipe; download it first")
            continue
        kind = "video" if media.name == "video.mp4" else "image"
        facts = tiktok_facts(code) if re.fullmatch(r"\d{15,}", code) else {}
        if url and not facts.get("url"):
            facts["url"] = url
        if kind == "video":
            strip_of(media, d / "strip")
            secs = facts.get("duration") or probe(media)
        else:
            secs = 0
        meta = {"code": code, "url": facts.get("url", url), "author": facts.get("author", ""),
                "views": facts.get("views", 0), "likes": facts.get("likes", 0),
                "comments": facts.get("comments", 0), "duration": secs,
                "caption": facts.get("caption", ""), "pool": pool, "source": source,
                "owner": owner, "brand": brand, "added": str(date.today()),
                "added_by": note or "added by hand through add.py"}
        (d / "meta.json").write_text(json.dumps(meta, indent=1))
        mirrored = mirror(code)
        if code in have:
            say(f"  {code}: already in {pool} — media refreshed, "
                + ("Drive refreshed" if mirrored else "Drive pending (not mounted)"))
            continue
        n = len(doc["posts"]) + 1
        who = re.sub(r"[^a-z0-9]+", "-", (facts.get("author") or "swipe").lower()).strip("-")
        row = {"file": f"{n:02d}_{who}-{code}.md", "id": code, "creator": facts.get("author", ""),
               "views": facts.get("views", 0), "engagement": facts.get("likes", 0) + facts.get("comments", 0),
               "url": facts.get("url", url), "caption": facts.get("caption", ""),
               "seconds": secs, "source": source, "owner": owner, "kind": kind}
        if mirrored:
            row["drive"] = swipe_home.label("organic", "records", "swipe-videos", code, media.name)
        else:
            row["mirror"] = "pending"     # never claim a Drive copy that is not there
        doc["posts"].append(row)
        record_md(pool, row if mirrored else
                  dict(row, drive="not on the Drive yet — python3 add.py --mirror-all"), facts)
        added.append(row)
        say(f"  + {code}  @{row['creator'] or '?'}  {row['views']:,} views")

    doc["posts_seen"] = len(doc["posts"])
    doc["brand"] = brand
    pool_file(pool).parent.mkdir(parents=True, exist_ok=True)
    pool_file(pool).write_text(json.dumps(doc, indent=1))
    say(f"\n  {len(added)} added · {doc['posts_seen']} in the {pool} pool")
    say(f"  lane: {source} · {owner} · swiped for {brand}")
    say(f"  index it:  python3 components/intake/tools/run.py --brand {brand}")
    return added


def main():
    ap = argparse.ArgumentParser(description="File a swipe you found by hand.")
    ap.add_argument("files", nargs="*", help="media files or a folder of them")
    ap.add_argument("--url", action="append", default=[], help="a post link (needs its media too)")
    ap.add_argument("--pool", help="what to call this batch — tiktok-shop, competitor-pool, reddit-finds")
    ap.add_argument("--brand", help="the brand it was swiped for")
    ap.add_argument("--source", default="organic", choices=["organic", "paid", "own"])
    ap.add_argument("--owner", default="creator", choices=["creator", "competitor", "own"])
    ap.add_argument("--note", default="", help="where it came from, in your words")
    ap.add_argument("--check", action="store_true", help="what is filed but not on the Drive")
    ap.add_argument("--mirror-all", action="store_true", help="mirror everything local-only")
    ap.add_argument("--list", action="store_true", help="what a pool holds")
    a = ap.parse_args()

    if a.check:
        return 0 if check() == 0 else 1
    if a.mirror_all:
        local = {p.name for p in LIB.glob("*") if p.is_dir()}
        there = {p.name for p in DRIVE.glob("*") if p.is_dir()} if DRIVE.parent.parent.exists() else set()
        todo = sorted(local - there)
        for i, c in enumerate(todo, 1):
            mirror(c)
            if i % 25 == 0:
                say(f"  {i}/{len(todo)}")
        say(f"  mirrored {len(todo)}")
        return 0
    if a.list:
        if not a.pool:
            ap.error("--list needs --pool")
        f = pool_file(a.pool)
        if not f.is_file():
            say(f"  no pool called {a.pool}")
            return 1
        doc = json.loads(f.read_text())
        say(f"  {a.pool} · brand {doc.get('brand')} · {doc.get('posts_seen')} swipes")
        for p in sorted(doc["posts"], key=lambda r: -(r.get("views") or 0)):
            say(f"    {(p.get('views') or 0):>11,}  @{p.get('creator','?'):<24}{(p.get('caption') or '')[:50]}")
        return 0
    if not (a.files or a.url):
        ap.error("give it files (or --url), or ask --check")
    if not (a.pool and a.brand):
        ap.error("--pool and --brand are required: a swipe with no lane is what went missing")
    add(a.files, a.url, a.pool, a.brand, a.source, a.owner, a.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
