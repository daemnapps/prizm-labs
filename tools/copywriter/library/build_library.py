#!/usr/bin/env python3
"""The copy library — every piece of copy we hold, as rows.

    python3 library/build_library.py --email-brand <brand> --pages-brand <brand> --pool <name>

All three are required: --email-brand names the brand whose shipped emails
are filed, --pages-brand the brand whose own pages are filed, --pool the
swipe-organic saves pool the creator captions come from. No brand or pool is
named here (workspace rule 7).

Walks the sources the channel map names and files every piece of copy as one
row: channel, format, origin, brand, the text itself where it can be lifted,
a path where it cannot. Same principle as the language layer and formats.json
— the copy library is DATA the machine queries, never prose someone maintains.

Re-runnable: it rebuilds runs/copywriter/_system/library/index.json from the
sources every time, so a new send, a new save or a new teardown shows up on
the next run with no edit here.

Origins:
    swiped   someone else wrote it and it ran in the wild — the study material
    ours     we shipped it to real readers — our own track record
    machine  a chain generated it — output, not evidence, kept out of counts
             used to judge what the market accepts
"""
import argparse, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../copywriter/library
AD   = HERE.parent                               # .../copywriter

# FOUND, never counted. This was AD.parent.parent.parent with a comment saying
# "(the team notes)" — the depth from the machine's OLD home. After the move to
# components/ on 2026-09-19 it resolved one level above the workspace, so the
# assert below fired and this script crashed on every run for three days.
WS = next((d for d in HERE.parents
           if (d / "components").is_dir() and (d / "brands").is_dir()), None)
if WS is None:
    sys.exit(f"workspace not found from {HERE}")
INDEX = WS / "runs/copywriter/_system/library/index.json"

# swipe-paid and swipe-organic moved out of the team notes into components/ on 2026-09-22.
SWIPE_PAID = WS / "components" / "swipe-paid"
SWIPE_ORGANIC = WS / "components" / "swipe-organic"


def _drive_root():
    """The shared drive, from whichever Google account this machine mounts.

    Was hardcoded to one person's address, so it resolved to nothing anywhere
    else. Set DRIVE_ACCOUNT to pin it; SHARED_DRIVE names the shared drive.
    """
    cs = Path.home() / "Library/CloudStorage"
    shared = os.environ.get("SHARED_DRIVE", "Shared drives/swipes")
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}" / shared
    m = sorted(cs.glob("GoogleDrive-*"))
    return (m[0] if m else cs / "GoogleDrive") / shared


DRIVE = _drive_root()

rows, notes = [], []

# The sourcing layer: who each source was written FOR, and which of our
# brand/avatar pairs may draw on it. `fits` is a ruling — empty means the
# source is quarantined from injection until the owner fills it.
SOURCES = json.loads((Path(__file__).parent / "sources.json").read_text())["sources"]


def audience_of(source_key, **per_row):
    src = SOURCES.get(source_key, {})
    a = dict(source=source_key, market=src.get("market"), fits=src.get("fits"))
    a.update({k: v for k, v in per_row.items() if v})
    return a


# Sources the owner removed from the library (sources.json `removed`): nothing from them,
# and nothing naming them, is filed.
REMOVED = [n for s in SOURCES.values() for n in (s.get("removed") or {}).get("names", [])]


def removed(*parts):
    hay = " ".join(str(p) for p in parts).lower()
    return any(n in hay for n in REMOVED)


def add(origin, brand, channel, fmt, title, text, path, **extra):
    if removed(path, title, text, extra.get("audience")):
        return
    rows.append(dict(
        id=f"c{len(rows)+1:04d}", origin=origin, brand=brand,
        channel=channel, format=fmt, title=(title or "").strip()[:200],
        text=(text or "").strip(), path=str(path), **extra))


def note(msg):
    notes.append(msg)
    print(f"  ! {msg}")


# --- 1 · <brand> emails — ours, shipped ----------------------------------
def emails(brand):
    # `the team notes` was merged into `brands/` and deleted on 2026-09-02,
    # so this read nothing and said "the email channel is empty this build"
    # every time — which reads like a fact about the brand, not a dead path.
    home = WS / "brands" / brand / "email-sms"
    cls = {}
    try:
        for r in json.loads((home / "classified.json").read_text()):
            cls[r["file"]] = r
    except Exception as e:
        note(f"email classification unreadable ({e}); sends filed untagged")
    sends = sorted((home / "sends").glob("*.md"))
    if not sends:
        note(f"no {brand} sends found at {home.relative_to(WS)} — email channel empty this build")
    for f in sends:
        s = f.read_text(encoding="utf-8", errors="replace")
        title = (re.match(r"# (.+)", s) or [None, f.stem]).group(1) if s.startswith("# ") else f.stem
        pv = re.search(r"^- preview: (.+)$", s, re.M)
        # The copy in an image-built DR email lives in the image alt text.
        alts = [a.strip() for a in re.findall(r"\[IMAGE alt=(.*?)\] \S*https?://", s)
                if len(a.strip()) > 25]
        c = cls.get(f.name, {})
        add("ours", brand, "email", "campaign-email", title,
            "\n\n".join(([pv.group(1)] if pv else []) + alts), f.relative_to(WS),
            tags=dict(category=c.get("category"), type=c.get("type"),
                      treatments=c.get("treatments"), sent=c.get("sent")),
            audience=audience_of(f"{brand}-email"))
    print(f"  emails: {len(sends)}")


# --- 2 · saved posts — swiped creator captions ---------------------------
def captions(pool):
    cat = SWIPE_ORGANIC / "records" / pool / "catalog.json"
    try:
        data = json.loads(cat.read_text())["rows"]
    except Exception as e:
        note(f"saves catalog unreadable ({e}); no creator captions this build")
        return
    n = 0
    for r in data:
        text = (r.get("caption") or "").strip()
        if not text:
            continue
        add("swiped", "-", "organic-social", "creator-caption",
            text.splitlines()[0][:80], text, cat.relative_to(WS),
            tags=dict(author=r.get("author"), category=r.get("category"),
                      grade=r.get("grade"), views=r.get("views"),
                      likes=r.get("likes"), url=r.get("url")),
            audience=audience_of(pool,
                                 avatar_fit=(r.get("avatar_fit") or "").strip("—- ") or None,
                                 bucket=r.get("bucket")))
        n += 1
    print(f"  creator captions: {n}")


# --- 3 · swiped ad angles — headline + primary text, verbatim ------------
def angles():
    n_h = n_p = 0
    for brand_dir in sorted((SWIPE_PAID).iterdir()):
        # blocks/ is the pool's one shape (the owner, 2026-10-08, I-196 (the owner
        # notice and asks)); angles/ is read only for a brand with no blocks/.
        adir = brand_dir / "blocks"
        if not adir.is_dir():
            adir = brand_dir / "angles"
        if not adir.is_dir():
            continue
        for f in sorted(adir.glob("*.md")):
            s = f.read_text(encoding="utf-8", errors="replace")
            h = re.search(r"## Headline\s*\n+> (.+)", s)
            p = re.search(r"## Primary text[^\n]*\n+> (.+?)(?=\n\n|\n##|\Z)", s, re.S)
            heat = re.search(r"\*\*(\d+) live creatives?\*\*", s)
            tags = dict(swipe_brand=brand_dir.name,
                        live_creatives=int(heat.group(1)) if heat else None)
            if h:
                # The angle file's "Headline" is the ANGLE STATEMENT — the
                # research's name for the copy block, not the ad's headline.
                # Real headlines are the per-ad `title` field AdPlexity
                # captured at swipe time; raw_ads() below files those.
                add("swiped", "-", "paid-social", "angle",
                    h.group(1), h.group(1), f.relative_to(WS), tags=tags,
                    audience=audience_of(brand_dir.name))
                n_h += 1
            if p:
                add("swiped", "-", "paid-social", "primary-text",
                    h.group(1) if h else f.stem,
                    re.sub(r"\n> ?", "\n", p.group(1)), f.relative_to(WS), tags=tags,
                    audience=audience_of(brand_dir.name))
                n_p += 1
    print(f"  swiped angles: {n_h} · primary texts: {n_p}")


# --- 3b · real ad headlines — the per-ad `title` AdPlexity captured ------
def raw_ads():
    n, seen = 0, set()
    for brand_dir in sorted((SWIPE_PAID).iterdir()):
        rdir = brand_dir / "_raw"
        if not rdir.is_dir():
            continue
        for f in sorted(rdir.glob("ad_*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            t = (d.get("title") or "").strip()
            if not t or t.lower() in seen:
                continue
            seen.add(t.lower())
            add("swiped", "-", "paid-social", "headline", t, t,
                f.relative_to(WS),
                tags=dict(swipe_brand=brand_dir.name, ad_id=d.get("id")),
                audience=audience_of(brand_dir.name))
            n += 1
    print(f"  real ad headlines (deduped): {n}")
    # NOTE: the _BRAND cards count more distinct headlines than the repo's
    # _raw folders hold (the full sweeps live on the Drive) — this files what
    # is in the repo and picks the rest up whenever they land.


# --- 4 · swiped landing pages — full page text from the Drive ------------
def pages():
    n = missing = 0
    for brand_dir in sorted((SWIPE_PAID).iterdir()):
        pdir = brand_dir / "_pages"
        if not pdir.is_dir():
            continue
        for f in sorted(pdir.glob("*.md")):
            s = f.read_text(encoding="utf-8", errors="replace")
            url = re.search(r"\*\*URL:\*\* (\S+)", s)
            txt, src = "", f.relative_to(WS)
            cap = DRIVE / "components/swipe-paid" / brand_dir.name / "_pages" / f.stem / "page.txt"
            if cap.is_file():
                txt = cap.read_text(encoding="utf-8", errors="replace")[:20000]
            else:
                missing += 1
            add("swiped", "-", "owned-pages", "landing-page", f.stem, txt, src,
                tags=dict(swipe_brand=brand_dir.name,
                          url=url.group(1) if url else None,
                          text_on_drive=cap.is_file()),
                audience=audience_of(brand_dir.name))
            n += 1
    if missing:
        note(f"{missing} swiped pages have no page.txt on the Drive yet — "
             "filed by path, text to follow when captured")
    print(f"  swiped landing pages: {n}")


# --- 5 · teardown scripts — the source's own spoken words ----------------
# Finished teardowns are read off the filed shelves through run-kit's index
# (SI-56, 2026-10-08) — never from one Mac's working folder.
if str(WS / "components" / "run-kit") not in sys.path:
    sys.path.append(str(WS / "components" / "run-kit"))
from run_kit import index as RKI                 # noqa: E402


def teardowns(runs_root=None):
    """Every filed video-teardown run. `runs_root` lets a test point at its
    own runs/ tree; None is the workspace's."""
    filed = RKI.scan(runs_root)
    base = Path(runs_root).parent if runs_root else WS
    n = 0
    for r in filed:
        if r["machine"] != "video-teardown":
            continue
        run = base / r["path"]
        td = run / "stages" / "1-teardown.md"
        if not td.is_file():
            continue
        s = td.read_text(encoding="utf-8", errors="replace")
        # The teardown table is | time | visual | on-screen text | audio |.
        # Copy lives in TWO of those columns: the spoken words (audio, with a
        # speaker label) and the overlay text (some sources carry the whole
        # script on screen over music — those have no dialogue at all, and the
        # first extractor missed every one of them).
        lines, overlay, seen = [], [], set()
        for row in s.splitlines():
            cells = [c.strip() for c in row.split("|")]
            if len(cells) < 5 or not re.match(r"\d+:\d\d", cells[1] or ""):
                continue
            ov, au = cells[3], cells[4]
            if ov and ov.lower() not in ("", "-", "—", "none") and ov not in seen:
                seen.add(ov); overlay.append(ov)
            spoken = re.sub(r"^[A-Za-z .\[\]0-9-]{0,30}:\s*", "", au).strip()
            if spoken and not spoken.startswith("[") and spoken not in seen:
                seen.add(spoken); lines.append(spoken)
        lane = ""
        tri = run / "stages" / "0-triage.md"
        if tri.is_file():
            lane = "ORGANIC" if "ORGANIC" in tri.read_text(errors="replace") else "AD"
        channel = "organic-social" if lane == "ORGANIC" else "paid-social"
        # each run's audience stage already ruled who this source speaks to —
        # a WRITING stage, so it is filed on the writing shelf
        av = fn = None
        aud_f = base / "runs" / "video-writing" / r["brand"] / r["label"] / "stages" / "1b-audience.md"
        if not aud_f.is_file():
            aud_f = run / "stages" / "1b-audience.md"
        if aud_f.is_file():
            a_s = aud_f.read_text(errors="replace")
            m_av = re.search(r"^AVATAR:\s*([a-z0-9-]+)", a_s, re.M)
            m_fn = re.search(r"^FUNNEL:\s*([a-z]+)", a_s, re.M)
            av = m_av.group(1) if m_av else None
            fn = m_fn.group(1) if m_fn else None
        aud = audience_of("video-teardowns", avatar=av, funnel=fn)
        if lines:
            add("swiped", "-", channel, "video-script", r["label"],
                "\n".join(lines), td.relative_to(base),
                tags=dict(lane=lane or None, run=r["label"]), audience=aud)
            n += 1
        if overlay:
            add("swiped", "-", channel, "overlay-text", r["label"],
                "\n".join(overlay), td.relative_to(base),
                tags=dict(lane=lane or None, run=r["label"]), audience=aud)
    print(f"  teardown scripts: {n}")


# --- 6 · our own pages ---------------------------------------------------
def our_pages(brand):
    import sys as _sys
    _sys.path.append(str(WS / "components" / "brandpath"))
    import brandpath as BP                          # brand folders by their plan name
    base = BP.brand_path(brand, "intake", root=WS / "brands")   # today: existing-content/
    n = 0
    for sub, fmt in (("landing-pages", "landing-page"), ("quiz", "quiz")):
        d = base / sub
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.name.startswith("."):
                continue
            txt = ""
            if f.is_file() and f.suffix in (".md", ".txt", ".html"):
                txt = f.read_text(encoding="utf-8", errors="replace")[:20000]
            add("ours", brand, "owned-pages", fmt, f.stem, txt,
                f.relative_to(WS), audience=audience_of(f"{brand}-pages"))
            n += 1
    print(f"  our pages: {n}")


# --- 7 · machine output — tagged, never counted as evidence --------------
def machine():
    out = AD / "output"
    n = 0
    for d in sorted(out.iterdir()) if out.is_dir() else []:
        c = d / "copy.md"
        if c.is_file():
            add("machine", "-", "paid-social", "generated-set", d.name,
                "", c.relative_to(WS))
            n += 1
    print(f"  machine sets (tagged, not evidence): {n}")


def parse_args(argv=None):
    """The command line: all three flags required; one missing prints the
    usage line and exits 2 (argparse's own refusal)."""
    ap = argparse.ArgumentParser(
        prog="build_library.py",
        description="Rebuild the copy library index from its sources.")
    ap.add_argument("--email-brand", required=True, metavar="<brand>",
                    help="the brand whose shipped emails are filed (section 1)")
    ap.add_argument("--pages-brand", required=True, metavar="<brand>",
                    help="the brand whose own pages are filed (section 6)")
    ap.add_argument("--pool", required=True, metavar="<name>",
                    help="the swipe-organic saves pool the creator captions come from (section 2)")
    return ap.parse_args(argv)


def main(email_brand=None, pages_brand=None, pool=None):
    # The command line always passes all three (parse_args); a direct call
    # that leaves one out fails in that section's reader, never on a default.
    print("building the copy library…")
    emails(email_brand); captions(pool); angles(); raw_ads(); pages(); teardowns()
    our_pages(pages_brand); machine()

    out = dict(schema=1, note=__doc__.strip().splitlines()[0], rows=rows, notes=notes)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    # summary: channel × format, evidence only
    tally = {}
    for r in rows:
        if r["origin"] == "machine":
            continue
        k = (r["channel"], r["format"], r["origin"])
        tally[k] = tally.get(k, 0) + 1
    print(f"\n{len(rows)} rows -> runs/copywriter/_system/library/index.json")
    for (ch, fmt, o), c in sorted(tally.items()):
        print(f"  {ch:16} {fmt:16} {o:7} {c:5}")


if __name__ == "__main__":
    a = parse_args()
    main(a.email_brand, a.pages_brand, a.pool)
