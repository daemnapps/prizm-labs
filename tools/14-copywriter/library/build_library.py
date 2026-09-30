#!/usr/bin/env python3
"""The copy library — every piece of copy we hold, as rows.

    python3 library/build_library.py

Walks the sources the channel map names and files every piece of copy as one
row: channel, format, origin, brand, the text itself where it can be lifted,
a path where it cannot. Same principle as the language layer and formats.json
— the copy library is DATA the machine queries, never prose someone maintains.

Re-runnable: it rebuilds index.json from the sources every time, so a new
send, a new save or a new teardown shows up on the next run with no edit here.

Origins:
    swiped   someone else wrote it and it ran in the wild — the study material
    ours     we shipped it to real readers — our own track record
    machine  a chain generated it — output, not evidence, kept out of counts
             used to judge what the market accepts
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../copy/library
AD   = HERE.parent                               # .../copy
WS   = AD.parent.parent.parent                   # ai-workspace  (copy)
assert (WS / "lab").is_dir(), f"workspace not found from {HERE}"

LAB   = WS / "lab" / "damon"
DRIVE = Path.home() / ("Library/CloudStorage/GoogleDrive-${DRIVE_ACCOUNT}/"
                       "Shared drives/Shared Assets")

rows, notes = [], []

# The sourcing layer: who each source was written FOR, and which of our
# brand/avatar pairs may draw on it. `fits` is a ruling — empty means the
# source is quarantined from injection until Damon fills it.
SOURCES = json.loads((Path(__file__).parent / "sources.json").read_text())["sources"]


def audience_of(source_key, **per_row):
    src = SOURCES.get(source_key, {})
    a = dict(source=source_key, market=src.get("market"), fits=src.get("fits"))
    a.update({k: v for k, v in per_row.items() if v})
    return a


def add(origin, brand, channel, fmt, title, text, path, **extra):
    rows.append(dict(
        id=f"c{len(rows)+1:04d}", origin=origin, brand=brand,
        channel=channel, format=fmt, title=(title or "").strip()[:200],
        text=(text or "").strip(), path=str(path), **extra))


def note(msg):
    notes.append(msg)
    print(f"  ! {msg}")


# --- 1 · <brand> emails — ours, shipped -----------------------------------
def emails():
    b = LAB / "brands" / "<brand>"
    # email-sms/ is the v6 name; email/ the old one, read while a brand moves
    home = next((b / n for n in ("email-sms", "email") if (b / n).is_dir()), b / "email-sms")
    cls = {}
    try:
        for r in json.loads((home / "classified.json").read_text()):
            cls[r["file"]] = r
    except Exception as e:
        note(f"email classification unreadable ({e}); sends filed untagged")
    sends = sorted((home / "sends").glob("*.md"))
    if not sends:
        note("no <brand> sends found — the email channel is empty this build")
    for f in sends:
        s = f.read_text(encoding="utf-8", errors="replace")
        title = (re.match(r"# (.+)", s) or [None, f.stem]).group(1) if s.startswith("# ") else f.stem
        pv = re.search(r"^- preview: (.+)$", s, re.M)
        # The copy in an image-built DR email lives in the image alt text.
        alts = [a.strip() for a in re.findall(r"\[IMAGE alt=(.*?)\] \S*https?://", s)
                if len(a.strip()) > 25]
        c = cls.get(f.name, {})
        add("ours", "<brand>", "email", "campaign-email", title,
            "\n\n".join(([pv.group(1)] if pv else []) + alts), f.relative_to(WS),
            tags=dict(category=c.get("category"), type=c.get("type"),
                      treatments=c.get("treatments"), sent=c.get("sent")),
            audience=audience_of("<brand>-email"))
    print(f"  emails: {len(sends)}")


# --- 2 · saved posts — swiped creator captions ---------------------------
def captions():
    cat = LAB / "swipe-organic" / "records" / "damon-saves" / "catalog.json"
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
            audience=audience_of("damon-saves",
                                 avatar_fit=(r.get("avatar_fit") or "").strip("—- ") or None,
                                 bucket=r.get("bucket")))
        n += 1
    print(f"  creator captions: {n}")


# --- 3 · swiped ad angles — headline + primary text, verbatim ------------
def angles():
    n_h = n_p = 0
    for brand_dir in sorted((LAB / "swipe-paid").iterdir()):
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
    for brand_dir in sorted((LAB / "swipe-paid").iterdir()):
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
    for brand_dir in sorted((LAB / "swipe-paid").iterdir()):
        pdir = brand_dir / "_pages"
        if not pdir.is_dir():
            continue
        for f in sorted(pdir.glob("*.md")):
            s = f.read_text(encoding="utf-8", errors="replace")
            url = re.search(r"\*\*URL:\*\* (\S+)", s)
            txt, src = "", f.relative_to(WS)
            cap = DRIVE / "swipe-paid" / brand_dir.name / "_pages" / f.stem / "page.txt"
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
def teardowns():
    runs = WS / "components" / "video-teardown" / "machine" / "runs"
    n = 0
    for run in sorted(runs.iterdir()):
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
        # each run's audience stage already ruled who this source speaks to
        av = fn = None
        aud_f = run / "stages" / "1b-audience.md"
        if aud_f.is_file():
            a_s = aud_f.read_text(errors="replace")
            m_av = re.search(r"^AVATAR:\s*([a-z0-9-]+)", a_s, re.M)
            m_fn = re.search(r"^FUNNEL:\s*([a-z]+)", a_s, re.M)
            av = m_av.group(1) if m_av else None
            fn = m_fn.group(1) if m_fn else None
        aud = audience_of("video-teardowns", avatar=av, funnel=fn)
        if lines:
            add("swiped", "-", channel, "video-script", run.name,
                "\n".join(lines), td.relative_to(WS),
                tags=dict(lane=lane or None, run=run.name), audience=aud)
            n += 1
        if overlay:
            add("swiped", "-", channel, "overlay-text", run.name,
                "\n".join(overlay), td.relative_to(WS),
                tags=dict(lane=lane or None, run=run.name), audience=aud)
    print(f"  teardown scripts: {n}")


# --- 6 · our own pages ---------------------------------------------------
def our_pages():
    b = LAB / "brands" / "<brand>"
    # intake/ is the v6 name; existing-content/ the old one
    base = next((b / n for n in ("intake", "existing-content") if (b / n).is_dir()), b / "intake")
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
            add("ours", "<brand>", "owned-pages", fmt, f.stem, txt,
                f.relative_to(WS), audience=audience_of("<brand>-pages"))
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


def main():
    print("building the copy library…")
    emails(); captions(); angles(); raw_ads(); pages(); teardowns(); our_pages(); machine()

    out = dict(schema=1, note=__doc__.strip().splitlines()[0], rows=rows, notes=notes)
    (HERE / "index.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    # summary: channel × format, evidence only
    tally = {}
    for r in rows:
        if r["origin"] == "machine":
            continue
        k = (r["channel"], r["format"], r["origin"])
        tally[k] = tally.get(k, 0) + 1
    print(f"\n{len(rows)} rows -> library/index.json")
    for (ch, fmt, o), c in sorted(tally.items()):
        print(f"  {ch:16} {fmt:16} {o:7} {c:5}")


if __name__ == "__main__":
    main()
