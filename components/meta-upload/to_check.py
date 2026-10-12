#!/usr/bin/env python3
"""to_check — the one door every lane's last step goes through (CARD.md).

    to_check.py --brand brand-a --lane video --brief brief-0191 --batch batch-2026-10-01-a \\
        --media master.mp4 --links link_brand-a_cpk_quiz [--words words.json] --tool video-edit \\
        --run runs/video-edit/brand-a/brief-0191_2026-09-30 [--dry-run] [--root <fake meta root>]

Makes one ad folder at `meta/<brand>/1-check/<lane>/<ad name>/` on the Shared Assets
drive: the media COPIED in (`<ad name>_asset-NN.<ext>`, a carousel's slides as
`<ad name>_slide-NN.png` in order) and `card.json` in the meta-card/1 shape. The lane's
own run folder keeps its originals; nothing on the Drive is moved or deleted.

Words are never made here. When a card arrives with none, THE COPY MACHINE runs on its brief
first (tools/copywriter brief_words.py — the copywriter's own stages; the owner 2026-10-09:
"whenever … an ad set of creatives is ready for distribution, we need to run the copywriter on
those as well … so when I get to this Meta page to approve … we can just hit it") and the card
takes what it wrote. Still nothing → empty lists, and the card's check fails where the owner sees it. Pages are catalog link ids
(lab/catalog/data/catalog.json); an id the catalog doesn't know is refused.
No pages passed → the brief's own landing page (`landing_page`, chosen when the
brief was written — components/naming/page_pick.py); pages passed always win.

The root is `--root`, else $META_CARDS_ROOT, else `Shared Assets/meta` on the Drive
mount. Tests and proofs point it at a temp folder. Nothing here talks to Meta.

An ad already in 2-approved / 3-live / sent-back is never re-filed; one already in
1-check is left alone unless `replace` (and never once it carries an approval).
"""
import argparse, json, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "components/naming"))
sys.path.insert(0, str(HERE))
import names as N  # noqa: E402
import card_words as W  # noqa: E402
import page_pick as PP  # noqa: E402
import shared_drive as SD  # noqa: E402

SCHEMA = "meta-card/1"
LANES = ("video", "image", "carousel", "creator")
FORMATS = ("flexible", "carousel")
STATES = ("1-check", "2-approved", "3-live", "sent-back")
CATALOG = REPO / "lab/catalog/data/catalog.json"
SHARED = SD.shared_assets()         # the mount's Shared Assets, else a named path that does not exist
PICTURE = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO = {".mp4", ".mov", ".m4v"}


class Refused(Exception):
    pass


# ---------------------------------------------------------------- where
def cards_root(root=None):
    """The meta/ folder: --root, $META_CARDS_ROOT, else the Drive's Shared Assets/meta."""
    if root:
        return Path(root)
    if os.environ.get("META_CARDS_ROOT"):
        return Path(os.environ["META_CARDS_ROOT"])
    if not SHARED.is_dir():
        raise Refused(f"{SD.NOTE} (looked for {SHARED})")
    return SHARED / "meta"


def is_live_root(root):
    return Path(root).resolve() == (SHARED / "meta").resolve()


def where_is(root, brand, lane, ad):
    """Every state folder this ad already sits in."""
    return [s for s in STATES if (Path(root) / brand / s / lane / ad).is_dir()]


# ---------------------------------------------------------------- what
_CAT = None


def _catalog(path=None):
    global _CAT
    if path:
        return json.loads(Path(path).read_text())
    if _CAT is None:
        _CAT = json.loads(CATALOG.read_text())
    return _CAT


def pages_for(brand, link_ids, catalog=None):
    """[{"link_id", "url"}] for each catalog link id, in the order given."""
    recs = ((_catalog(catalog).get("brands") or {}).get(brand) or {}).get("records") or {}
    out, unknown = [], []
    for lid in dict.fromkeys(x for x in (link_ids or []) if x):
        r = recs.get(lid)
        if not r or r.get("type") != "link":
            unknown.append(lid)
            continue
        out.append({"link_id": lid, "url": r.get("url")})
    if unknown:
        raise Refused(f"not a {brand} link in the catalog: {', '.join(unknown)}")
    return out


def brief_facts(brand, brief, product=None):
    """product / avatar / angle off the brief header (brands/<brand>/briefs/briefs.json).
    `product` picks between briefs sharing a number (numbers count per brand
    AND product, the owner 2026-10-01); a shared number with none is refused."""
    if not brief or brief == "none":
        return {}
    try:
        h = N.brief_header(brand, N.brief_id(brief), product) or N.brief_header(brand, brief, product) or {}
    except N.AmbiguousBrief as e:
        raise Refused(str(e))
    return {k: h.get(k) for k in ("product", "avatar", "angle", "talent")}


def brief_pages(brand, brief, product=None):
    """The brief's own landing page link ids ([] when none is recorded)."""
    try:
        return PP.landing_ids(brand, brief, product)
    except Exception:                       # noqa: BLE001 — no page is a failed check, not a crash
        return []


def ad_name_for(brand, product, brief, batch):
    return N.short_unit(brand, product, brief or "none", batch)


def plain(text):
    """Ad text as Meta shows it: the writer's markdown (**bold**, *italic*,
    __under__) would arrive in the ad as literal asterisks."""
    import re
    t = str(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.S)
    t = re.sub(r"__(.+?)__", r"\1", t, flags=re.S)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", t)
    return t.strip()


def clean_words(words):
    words = words or {}
    return {k: list(dict.fromkeys(plain(x) for x in (words.get(k) or []) if plain(x)))[:W.CAP]
            for k in ("primary", "headlines", "descriptions")}


# ---------------------------------------------------------------- the card
def plan(brand, lane, fmt, media, words=None, links=(), made_by=None, *, ad_name=None,
         product=None, brief=None, batch=None, old_name=None, avatar=None, angle=None,
         root=None, catalog=None, dry_run=False, thumbs=None, copy_checked=None):
    """Everything to_check would write, written nowhere. Returns a dict with
    `card`, `target` (the ad folder) and `files` [(source, name in the folder)]."""
    brand = N.slug(brand)
    if lane not in LANES:
        raise Refused(f"lane must be one of {', '.join(LANES)} — got {lane!r}")
    if fmt not in FORMATS:
        raise Refused(f"format must be flexible or carousel — got {fmt!r}")
    if (fmt == "carousel") != (lane == "carousel"):
        raise Refused(f"the {lane} lane files {'carousel' if lane == 'carousel' else 'flexible'} ads")
    facts = brief_facts(brand, brief, product or (N.parse_short(ad_name) or {}).get("product") if ad_name else product)
    product = product or facts.get("product")
    if not ad_name:
        if not (product and batch):
            raise Refused("an ad name needs product and batch (or pass ad_name)")
        ad_name = ad_name_for(brand, product, brief, batch)
    d = N.parse_short(ad_name)
    if not d or d.get("asset") or d.get("funnel"):
        raise Refused(f"not a short ad name: {ad_name}")
    media = [Path(m) for m in media or []]
    if not media:
        raise Refused(f"{ad_name}: no media to file")
    gone = [str(m) for m in media if not m.is_file()]
    if gone and not dry_run:
        raise Refused(f"{ad_name}: media not found: {', '.join(gone[:3])}")
    files = []
    for i, m in enumerate(media, 1):
        if fmt == "carousel":
            files.append((m, f"{ad_name}_slide-{i:02d}.png"))
        else:
            ext = m.suffix.lower()
            if ext not in PICTURE | VIDEO:
                raise Refused(f"{m.name}: not a picture or a video")
            files.append((m, f"{N.short_file(ad_name, i)}{'.jpg' if ext == '.jpeg' else ext}"))
    # a designed thumbnail per video (4 Oct 2026, the owner: "unique thumbnails per creative … creative diversity …
    # what we need people to stop scrolling and watch"): thumbs[i] goes with media[i]; none = Meta's own frame
    thumb_of = {}
    for i, t in enumerate(thumbs or [], 1):
        if not t or i > len(files):
            continue
        t = Path(t)
        if t.suffix.lower() not in PICTURE:
            raise Refused(f"{t.name}: a thumbnail is a picture (.jpg/.png)")
        if not t.is_file() and not dry_run:
            raise Refused(f"{ad_name}: thumbnail not found: {t}")
        name = f"{N.short_file(ad_name, i)}_thumb{'.jpg' if t.suffix.lower() == '.jpeg' else t.suffix.lower()}"
        files.append((t, name))
        thumb_of[files[i - 1][1]] = name
    if not [x for x in links or [] if x]:
        links = brief_pages(brand, d["brief"], d["product"])
    root = cards_root(root)
    card = {
        "schema": SCHEMA,
        "brand": brand,
        "lane": lane,
        "format": fmt,
        "ad_name": ad_name,
        "old_name": old_name,
        "brief_id": d["brief"] if d["brief"] != "none" else None,
        "product": d["product"],
        "avatar": avatar or facts.get("avatar"),
        "angle": angle or facts.get("angle"),
        "media": [name for _, name in files if name not in thumb_of.values()],
        **({"thumbs": thumb_of} if thumb_of else {}),
        "words": clean_words(words),
        # the copy came from a copywriter run that passed the read-back copy check (stage 8c, 2026-10-09)
        "copy_checked": bool(copy_checked),
        "pages": pages_for(brand, links, catalog),
        "made_by": {"tool": None, "run": None, "creator": None, **(made_by or {})},
        "made_at": datetime.now().isoformat(timespec="seconds"),
        "checks": {},
        "approval": None,
        "meta": [],
    }
    return {"card": card, "root": root, "target": root / brand / "1-check" / lane / ad_name,
            "files": files, "already": where_is(root, brand, lane, ad_name), "media_missing": gone,
            "missing_words": W.missing(card["words"])}


def _copy(src, dst, carousel):
    if carousel and src.suffix.lower() != ".png":
        try:
            from PIL import Image
            Image.open(src).save(dst, "PNG")
            return
        except ImportError:
            r = subprocess.run(["sips", "-s", "format", "png", str(src), "--out", str(dst)], capture_output=True)
            if r.returncode == 0:
                return
            raise Refused(f"could not turn {src.name} into a png")
    shutil.copy2(src, dst)


def write(p, replace=False):
    """Write a plan. Returns (state, target): filed | replaced | skipped:<why>."""
    target, card = p["target"], p["card"]
    later = [s for s in p["already"] if s != "1-check"]
    if later:
        return f"skipped: already in {', '.join(later)}", target
    if "1-check" in p["already"]:
        old = target / "card.json"
        prior = json.loads(old.read_text()) if old.is_file() else {}
        if prior.get("approval"):
            return "skipped: already decided on in 1-check", target
        if not replace:
            return "skipped: already in 1-check", target
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.partial-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    for src, name in p["files"]:
        _copy(src, tmp / name, card["format"] == "carousel")
    (tmp / "card.json").write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    if not target.exists():
        tmp.rename(target)
        return "filed", target
    # replace IN PLACE, once the new set is whole: the folder itself stays, so its Drive link keeps working for
    # anyone it was shared with (4 Oct 2026: swapping the folder gave every refile a new link and trashed the one
    # the owner had shared). Each file is swapped on its own; files the new card no longer lists go.
    keep = {f.name for f in tmp.iterdir()}
    for f in tmp.iterdir():
        os.replace(f, target / f.name)
    for f in target.iterdir():
        if f.is_file() and f.name not in keep:
            f.unlink()
    tmp.rmdir()
    return "replaced", target


def copy_machine(brand, brief, product=None, run=None):
    """Run the copywriter on this brief (unless its copy is already written) and return the words it wrote,
    or None. Never raises: a card with no words still files, and its check says what is missing."""
    run = run or subprocess.run
    try:
        w, _ = W.for_brief(brand, brief, product=product)
        if not W.missing(w):
            return w                                        # already written by the copywriter
        cmd = [sys.executable, str(REPO / "tools" / "copywriter" / "machine" / "brief_words.py"),
               "--brand", brand, "--brief", brief] + (["--product", product] if product else [])
        print(f"  copy: no words on the card — running the copywriter on {brief}", flush=True)
        run(cmd, check=False)
        w, _ = W.for_brief(brand, brief, product=product)
        return None if W.missing(w) else w
    except Exception as e:                                  # the copywriter is its own machine; never block the card
        print(f"  copy: the copywriter did not finish for {brief}: {e}", file=sys.stderr)
        return None


def to_check(brand, lane, fmt, media, words=None, links=(), made_by=None, *, dry_run=False,
             replace=False, **kw):
    """Plan and (unless dry_run) write one card folder. Returns the plan with `state`."""
    # only a real filing runs the copywriter: tests and proofs file into their own --root / $META_CARDS_ROOT,
    # and NO_AD_WORDS=1 turns it off
    if (not dry_run and kw.get("brief") and not kw.get("root") and not os.environ.get("META_CARDS_ROOT")
            and os.environ.get("NO_AD_WORDS") != "1"
            and W.missing(clean_words(words))):
        words = copy_machine(brand, kw["brief"], kw.get("product")) or words
    if kw.get("copy_checked") is None and kw.get("brief") and kw["brief"] != "none":
        runs = W.runs_for_brief(brand, kw["brief"], product=kw.get("product"))
        kw["copy_checked"] = bool(runs) and all(W.checked(r) for r in runs)
    p = plan(brand, lane, fmt, media, words, links, made_by, dry_run=dry_run, **kw)
    if dry_run:
        p["state"] = ("would skip: already in " + ", ".join(p["already"])) if p["already"] and not replace \
            else "would file"
    else:
        p["state"], _ = write(p, replace)
    return p


def show(p, verbose=False):
    """The lines a person reads: what card, where, and what its words lack."""
    c = p["card"]
    w = c["words"]
    lines = [f"{p['state']:<10} {c['lane']}/{c['ad_name']}",
             f"           {len(c['media'])} {'slide' if c['format'] == 'carousel' else 'file'}(s) · "
             f"primary {len(w['primary'])} · headlines {len(w['headlines'])} · descriptions {len(w['descriptions'])} · "
             f"pages {len(c['pages'])}"
             + (f"  — MISSING: {', '.join(p['missing_words'])}" if p["missing_words"] else "")
             + (f"  — media not made yet: {len(p['media_missing'])}" if p.get("media_missing") else "")]
    if verbose:
        lines.append(f"           → {p['target']}")
        lines += [f"             {Path(s).name}  →  {n}" for s, n in p["files"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--lane", required=True, choices=LANES)
    ap.add_argument("--format", choices=FORMATS, help="default: carousel for the carousel lane, else flexible")
    ap.add_argument("--ad-name")
    ap.add_argument("--product")
    ap.add_argument("--brief")
    ap.add_argument("--batch")
    ap.add_argument("--old-name")
    ap.add_argument("--avatar", help="names the ad set (default: the brief header in brands/<brand>/briefs)")
    ap.add_argument("--angle", help="names the ad set (default: the brief header in brands/<brand>/briefs)")
    ap.add_argument("--media", nargs="+", required=True, help="the files, in order")
    ap.add_argument("--thumbs", nargs="*", default=[], help="a designed thumbnail per video, in the same order (optional)")
    ap.add_argument("--words", help="words.json, a copywriter stage8 render, or a copywriter run folder")
    ap.add_argument("--links", nargs="*", default=[], help="catalog link ids (default: the brief's landing page)")
    ap.add_argument("--tool")
    ap.add_argument("--run")
    ap.add_argument("--creator")
    ap.add_argument("--root", help="the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    checked = W.checked(a.words) if a.words and Path(a.words).is_dir() else None
    words = W.from_file(a.words) if a.words else (W.for_brief(a.brand, a.brief)[0] if a.brief else W.empty())
    try:
        p = to_check(a.brand, a.lane, a.format or ("carousel" if a.lane == "carousel" else "flexible"),
                     a.media, words, a.links, {"tool": a.tool, "run": a.run, "creator": a.creator},
                     ad_name=a.ad_name, product=a.product, brief=a.brief, batch=N.norm_batch(a.batch),
                     old_name=a.old_name, avatar=a.avatar, angle=a.angle, root=a.root, dry_run=a.dry_run, replace=a.replace, thumbs=a.thumbs,
                     copy_checked=checked)
    except (Refused, ValueError) as e:
        sys.exit(f"REFUSED  {e}")
    print(show(p, verbose=True))
    if a.dry_run:
        print(json.dumps(p["card"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
