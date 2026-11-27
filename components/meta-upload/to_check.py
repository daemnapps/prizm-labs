#!/usr/bin/env python3
"""to_check — the one door every lane's last step goes through (CARD.md).

    to_check.py --brand brand_b --lane video --brief brief-0191 --batch batch-2026-10-01-a \\
        --media master.mp4 --links link_brand_b_cpk_quiz [--words words.json] --tool video-edit \\
        --run runs/video-edit/brand_b/brief-0191_2026-09-30 [--dry-run] [--root <fake meta root>]

Makes one ad folder at `meta/<brand>/1-check/<lane>/<ad name>/` on the Shared Assets
drive: the media COPIED in (`<ad name>_asset-NN.<ext>`, a carousel's slides as
`<ad name>_slide-NN.png` in order) and `card.json` in the meta-card/1 shape. The lane's
own run folder keeps its originals; nothing on the Drive is moved or deleted.

Words are never made here, and no copy is written at filing (owner, 2026-11-16, replacing the
2026-10-09 copywriter-at-filing rule). A card that arrives with none takes the brief's own written
copy if it has some, else the words of the newest live card for its product (card_words.from_live).
Still nothing → empty lists, and the card's check fails where owner sees it. Pages are catalog link ids
(lab/owner/catalog/data/catalog.json); an id the catalog doesn't know is refused.
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
import made_by_tool as MBT  # noqa: E402
import cover_rule as CR  # noqa: E402

SCHEMA = "meta-card/1"
LANES = ("video", "image", "carousel", "creator")
FORMATS = ("flexible", "carousel")
STATES = ("1-check", "2-approved", "3-live", "sent-back")
CATALOG = REPO / "lab/owner/catalog/data/catalog.json"
SHARED = SD.shared_assets()         # the mount's Shared Assets, else a named path that does not exist
PICTURE = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO = {".mp4", ".mov", ".m4v"}


class Refused(Exception):
    pass


# ---------------------------------------------------------------- quiz and offer
def with_offer_page(brand, product, links, ad_name=""):
    """A card whose pages are all quizzes gets the product's live offer page beside
    them (owner, 2026-10-23: anything tested on a quiz is also tested on the offer
    page). Pages are typed by components/naming page_pick, never by the id's
    spelling. Nothing to add (no quiz, an offer page already there, or none found)
    leaves the links as they came."""
    given = [x for x in links or [] if x]
    if not given or not product:
        return links
    recs = PP.records(brand)
    kinds = [PP.link_type(recs[x]) if x in recs else ("quiz" if "quiz" in x.lower() else None) for x in given]
    if not all(k == "quiz" for k in kinds):
        return links
    offers = PP.offer_pages(brand, product)
    if not offers:
        print(f"  NOTE {ad_name}: sends only to a quiz and no live offer page sells {product}; "
              "add one to --links so both are tested (owner, 2026-10-23)")
        return links
    print(f"  + {ad_name}: offer page {offers[0]} added beside the quiz (owner, 2026-10-23)")
    return given + [offers[0]]


# ---------------------------------------------------------------- where
def cards_root(root=None):
    """The meta/ folder: --root, $META_CARDS_ROOT, else the Drive's Shared Assets/meta."""
    if root:
        return Path(root)
    if os.environ.get("META_CARDS_ROOT"):
        return Path(os.environ["META_CARDS_ROOT"])
    if SD.api():
        return SD.meta()                       # the API copy (shared_drive.py)
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
    """product / avatar / angle off the brief record (components/naming names.brief_record:
    the brands/<brand>/briefs header over the brief register entry, where angle_pick.py keeps
    the angle it read off the brief — owner 2026-10-12, components/naming/ANGLE.md).
    `product` picks between briefs sharing a number (numbers count per brand
    AND product, owner 2026-10-01); a shared number with none is refused."""
    if not brief or brief == "none":
        return {}
    try:
        h = (N.brief_record(brand, N.brief_id(brief), product) if N.brief_number(brief) else None) \
            or N.brief_record(brand, brief, product) or {}
    except N.AmbiguousBrief as e:
        raise Refused(str(e))
    out = {k: h.get(k) for k in ("product", "avatar", "sub_avatar", "angle", "talent", "concept")}
    # the demographic is the brief's `face` move (creative-diversity), not part of the sub-avatar (8 Nov 2026)
    out["face"] = (h.get("moves") or {}).get("face")
    return out


def sub_avatars_of(brand, avatar):
    """The sub-avatar ids filed under an avatar (brands/<brand>/core-avatars/avatars.json); [] when unknown."""
    p = Path(__file__).resolve().parents[2] / "brands" / brand / "core-avatars" / "avatars.json"
    try:
        rows = json.loads(p.read_text()).get("avatars") or []
    except (OSError, ValueError):
        return []
    return next((a.get("sub_avatars") or [] for a in rows if a.get("id") == avatar), [])


def brief_pages(brand, brief, product=None):
    """The brief's own landing page link ids ([] when none is recorded)."""
    try:
        return PP.landing_ids(brand, brief, product)
    except Exception:                       # noqa: BLE001 — no page is a failed check, not a crash
        return []


def waiting_for_brief(root, brand, lane, brief, ad_name):
    """Other cards for this brief still waiting in 1-check (the same lane), by folder name."""
    here = Path(root) / brand / "1-check" / lane
    if not here.is_dir():
        return []
    out = []
    for f in sorted(here.iterdir()):
        d = N.parse_short(f.name) if f.is_dir() else None
        if d and d.get("brief") == brief and f.name != ad_name:
            out.append(f.name)
    return out


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


def promo_ad_set(brand, card):
    """A promotional ad (its words carry a price) goes into its own ad set in the campaign: the avatar's ad set
    name with `promo` in the angle's place (owner, 24 Oct 2026). None for every other ad, or when no ad set name
    can be made."""
    import re, upload as U
    from brand import Brand
    text = " ".join(x for k in ("primary", "headlines", "descriptions") for x in (card.get("words") or {}).get(k) or [])
    if not re.search(r"[$£€]\s?\d", text):
        return None
    try:
        b = Brand(brand)
        name, _ = U.ad_set_for(b, U.card_fields(card))
        sep = U.build.naming.sep_for(b.naming, "ad_set") if hasattr(U, "build") else "_"
    except (SystemExit, Exception):
        return None
    return name.rsplit(sep, 1)[0] + sep + "promo" if name else None


def opening_labels(brand, d, lane, fmt, files, thumb_of, given=None):
    """The card's `openings`: one row per video asset saying which opening it carries (openings.py). A video card
    only; [] for every other lane, and never a refusal: a label that can't be read is left empty on its row."""
    if lane != "video" or fmt != "flexible":
        return []
    try:
        import openings as OP
        import concept as CN
        media = [(src, name) for src, name in files if name not in thumb_of.values()]
        said = []
        if d.get("brief") and d["brief"] != "none":
            _, reg = CN.register()
            _, entry = CN.find_entry(reg, brand, d["brief"], d.get("product"))
            bf = CN.brief_file(entry) if entry else None
            said = CN.from_brief(bf)["openings"] if bf else []
        return OP.labels([src for src, _ in media], [name for _, name in media], given, said)
    except Exception as e:                       # noqa: BLE001 — a label never stops a filing
        print(f"  openings: not labelled ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr)
        return []


def _register_lock():
    """The brief register's own lock (image-teardown briefs.py holds it while it numbers a brief), so a write here
    never drops a brief numbered in between. None where it can't be taken."""
    try:
        import fcntl, tempfile
        f = open(os.path.join(tempfile.gettempdir(), "brief-register.lock"), "a")
        fcntl.flock(f, fcntl.LOCK_EX)
        return f
    except Exception:                            # noqa: BLE001
        return None


def read_concept(brand, brief, product=None):
    """Before a real filing plans its card: the brief's concept onto its record, so the first card carries it."""
    if not brief or brief == "none":
        return
    lock = _register_lock()
    try:
        import concept as CN
        CN.auto(brand, brief, product)
    except Exception as e:                       # noqa: BLE001 — the card is filed either way
        print(f"  concept: not read ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr)
    finally:
        if lock:
            lock.close()


def record_openings(brand, card):
    """After a real filing: the card's opening rows onto the brief's record, under the register's lock. Never raises."""
    if not card.get("brief_id") or not card.get("openings"):
        return
    lock = _register_lock()
    try:
        import concept as CN
        CN.file_assets(brand, card["brief_id"], card.get("product"), card["ad_name"], card["openings"])
    except Exception as e:                       # noqa: BLE001 — the card is filed either way
        print(f"  openings: not written to the brief's record ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr)
    finally:
        if lock:
            lock.close()


# ---------------------------------------------------------------- the card
def plan(brand, lane, fmt, media, words=None, links=(), made_by=None, *, ad_name=None,
         product=None, brief=None, batch=None, old_name=None, avatar=None, angle=None, openings=None,
         root=None, catalog=None, dry_run=False, thumbs=None, copy_checked=None, second_card=False,
         cover_records=None, trybe_id=None, brief_id=None):
    """Everything to_check would write, written nowhere. Returns a dict with
    `card`, `target` (the ad folder) and `files` [(source, name in the folder)].

    A brief is one flexible video ad: every version of it (the control and each hook) rides in the same
    card as asset-01, asset-02 … A second waiting video card for a brief is refused; pass all the versions
    as `media` in one filing (with replace=True to add to the waiting card). `second_card=True` only when a
    brief deliberately goes out as a second, separate ad.

    `trybe_id` (a Trybe creator's video, 8 hex): written on the card; the uploader then ends the Meta ad name
    with it and puts trybe=<trybe_id> on the link (trybe_tag.py). A malformed id is refused here.
    `brief_id`: the card's brief id when it is not the ad name's (a briefless Trybe video is `trybe-<id>`)."""
    brand = N.slug(brand)
    try:
        import trybe_tag as TT
        trybe_id = TT.clean(trybe_id)
    except ValueError as e:
        raise Refused(f"{ad_name or brief}: {e}")
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
    if lane == "video" and d["brief"] != "none" and not second_card:
        twins = waiting_for_brief(cards_root(root), brand, lane, d["brief"], ad_name)
        if twins:
            raise Refused(f"{ad_name}: brief {d['brief']} already has a waiting card ({', '.join(twins)}). One brief is one "
                          f"flexible ad: file every version together as that card's media (replace=True), not a card each")
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
    # a cover per video, each different (ruling 4 Oct 2026: creative diversity, a reason to stop scrolling):
    # thumbs[i] goes with media[i]; none = Meta's own frame
    thumb_of, cover_pairs, cover_given = {}, [], []
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
        cover_pairs.append((files[i - 1][0], files[i - 1][1], t, name))
        cover_given.append(cover_records[i - 1] if cover_records and i <= len(cover_records) else None)
    # each cover's record (the swipe it follows, the frame of its own video it starts from) rides on the card, read
    # from what the caller passes, the `.cover.json` beside the cover, or image production's own record of it
    # (cover_rule.py). Nothing is refused here: a cover with no record files, and the card's checks hold it
    cover_recs = CR.for_filing(cover_pairs, cover_given)
    # ONLY THE IMAGE PRODUCTION TOOL MAKES THE PICTURES (RULE GATE-5, 2026-11-11): every thumbnail and every picture
    # filed is a file image production delivered, by its sha256 in a run record; a frame grab, words typed on
    # afterwards, a hand composite or split, or an edit after delivery is refused here (made_by_tool.py)
    made, bad = MBT.refuse(lane, [src for src, _ in files])
    if bad:
        raise Refused(f"{ad_name}: " + " | ".join(bad))
    made_rec = {}
    for src, name in files:
        r = made.get(str(src))
        if r:
            made_rec[name] = {**r, **({"converted": True} if fmt == "carousel" and Path(src).suffix.lower() != ".png" else {})}
    if not [x for x in links or [] if x]:
        links = brief_pages(brand, d["brief"], d["product"])
    # QUIZ AND OFFER, BOTH (owner, 2026-10-23: "Anything that is tested with a quiz
    # should also get tested with the offer page too. Because sometimes the offer
    # page just works better."). A card is one ad per page, so a card that sends to
    # a quiz carries an offer page beside it. A quiz-only card is flagged on the
    # (not refused: the lanes that file quiz-only cards today keep running);
    # which offer page is the caller's choice, never guessed here.
    links = with_offer_page(brand, d["product"], links, ad_name)
    root = cards_root(root)
    # the angle is the brief's (components/naming/ANGLE.md): set once when the brief is
    # registered, read here. A hand-typed --angle is only for an ad with no brief angle.
    the_angle = facts.get("angle")
    if angle and the_angle and N.slug(angle) != N.slug(the_angle):
        raise Refused(f"{ad_name}: the angle is the brief's own ({the_angle}) — "
                      f"--angle {angle} disagrees; change the brief's angle, not the card")
    the_angle = the_angle or angle
    the_avatar = avatar or facts.get("avatar")
    if facts.get("sub_avatar") and the_avatar and facts["sub_avatar"] not in sub_avatars_of(brand, the_avatar):
        raise Refused(f"{ad_name}: sub-avatar {facts['sub_avatar']} is not filed under {the_avatar} "
                      f"(brands/{brand}/core-avatars/avatars.json) — file it there, or fix the brief record")
    opening_rows = opening_labels(brand, d, lane, fmt, files, thumb_of, openings)
    card = {
        "schema": SCHEMA,
        "brand": brand,
        "lane": lane,
        "format": fmt,
        "ad_name": ad_name,
        "old_name": old_name,
        "brief_id": brief_id or (d["brief"] if d["brief"] != "none" else None),
        "product": d["product"],
        "avatar": avatar or facts.get("avatar"),
        # the sub-avatar the brief declares (brief record `sub_avatar`), traced brief → card → index (8 Nov 2026)
        "sub_avatar": facts.get("sub_avatar"),
        # the demographic on screen, from the brief record `moves.face` (gender/age-band/ethnic-appearance)
        "face": facts.get("face"),
        "angle": the_angle,
        # the concept the brief names, and which opening each asset carries: the short name holds neither, so a
        # result is read back to them here and on the brief's record (openings.py, components/naming/concept.py)
        **({"concept": facts["concept"]} if facts.get("concept") else {}),
        **({"openings": opening_rows} if opening_rows else {}),
        "media": [name for _, name in files if name not in thumb_of.values()],
        **({"thumbs": thumb_of} if thumb_of else {}),
        **({"made_by_tool": made_rec} if made_rec else {}),
        **({"cover_records": cover_recs} if cover_recs else {}),
        "words": clean_words(words),
        # the copy came from a copywriter run that passed the read-back copy check (stage 8c, 2026-10-09)
        "copy_checked": bool(copy_checked),
        "pages": pages_for(brand, links, catalog),
        "made_by": {"tool": None, "run": None, "creator": None, **(made_by or {})},
        "made_at": datetime.now().isoformat(timespec="seconds"),
        "checks": {},
        "approval": None,
        "meta": [],
        # the Trybe rule (trybe_tag.py): present only on a Trybe creator's video
        **({"trybe_id": trybe_id} if trybe_id else {}),
    }
    import delivery_gate as DG
    delivery_result = DG.plan(card, media, thumbs)
    promo = promo_ad_set(brand, card)
    if promo:
        card["ad_set"] = promo
    return {"delivery_result": delivery_result, "delivery_media": media, "delivery_thumbs": thumbs, "card": card, "root": root, "target": root / brand / "1-check" / lane / ad_name,
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
    if src.suffix.lower() in (".mp4", ".mov", ".m4v"):
        import delivery                          # every ad video is filed at the one delivery size (delivery.SPEC)
        try:
            delivery.make(src, dst)
            return
        except (OSError, subprocess.SubprocessError) as e:   # never block a filing; the uploader sizes it again
            print(f"  delivery size: {src.name} filed as its master ({e})", file=sys.stderr)
    shutil.copy2(src, dst)


def write(p, replace=False):
    """Write a plan. Returns (state, target): filed | replaced | skipped:<why>."""
    target, card = p["target"], p["card"]
    import delivery_gate as DG
    delivery_result = DG.plan(card, p.get("delivery_media") or [src for src, name in p["files"] if name in card["media"]], p.get("delivery_thumbs"))
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
    DG.receipt(delivery_result, tmp, card)
    if delivery_result and card["lane"] == "video":
        failed = [k + ": " + v["why"] for k, v in CR.checks(tmp, card, lane="video", state="1-check").items() if not v["ok"]]
        if failed:
            raise Refused("Incomplete covers: " + " | ".join(failed))
    (tmp / "card.json").write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    if not target.exists():
        tmp.rename(target)
        SD.save_tree(target)                   # API copy: the new card goes up to the Drive
        DG.filed(delivery_result, card)
        return "filed", target
    # replace IN PLACE, once the new set is whole: the folder itself stays, so its Drive link keeps working for
    # anyone it was shared with (4 Oct 2026: swapping the folder gave every refile a new link and trashed the one
    # owner had shared). Each file is swapped on its own; a file the new card no longer lists STAYS, and the new
    # card names it under "superseded" (2026-10-18, LD-17 (Drive deletes out): no machine delete on Drive).
    keep = {f.name for f in tmp.iterdir()}
    was = target / "card.json"
    before = json.loads(was.read_text()) if was.is_file() else {}
    left = {f.name for f in target.iterdir() if f.is_file() and f.name not in keep and not f.name.startswith(".")}
    superseded = sorted((set(before.get("superseded") or []) | left) - keep)
    if superseded:
        card["superseded"] = superseded
        (tmp / "card.json").write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    for f in tmp.iterdir():
        os.replace(f, target / f.name)
    tmp.rmdir()
    SD.save_tree(target)
    DG.filed(delivery_result, card)
    return "replaced", target


def copy_machine(brand, brief, product=None, run=None):
    """Run the copywriter on this brief (unless its copy is already written) and return the words it wrote,
    or None. Never raises: a card with no words still files, and its check says what is missing."""
    run = run or subprocess.run
    try:
        w, _ = W.for_brief(brand, brief, product=product)
        if not W.missing(w):
            return w                                        # already written by the copywriter
        cmd = [sys.executable, str(REPO / "components" / "copywriter" / "machine" / "brief_words.py"),
               "--brand", brand, "--brief", brief] + (["--product", product] if product else [])
        print(f"  copy: no words on the card — running the copywriter on {brief}", flush=True)
        run(cmd, check=False)
        w, _ = W.for_brief(brand, brief, product=product)
        return None if W.missing(w) else w
    except Exception as e:                                  # the copywriter is its own machine; never block the card
        print(f"  copy: the copywriter did not finish for {brief}: {e}", file=sys.stderr)
        return None


def description_on(part):
    """The description switch (description.json beside this file): `check` (the words check needs one) or `fill` (the
    filer fills an empty one). Off for the file's `on` false, the part false, or META_DESCRIPTION_OFF=all/<part>."""
    off = {x.strip() for x in os.environ.get("META_DESCRIPTION_OFF", "").split(",") if x.strip()}
    if off & {"all", "1", part}:
        return False
    try:
        c = json.loads((HERE / "description.json").read_text())
    except (OSError, ValueError):
        c = {}
    return c.get("on") is not False and c.get(part) is not False


def live_description(brand, product=None, root=None):
    """The description on the most live briefs (3-live) of the brand, the same product's first (its short and old
    names count), never a price, offer or dated line; None when none qualifies. The winners bank holds headline and
    body only, so a description cannot be ranked by CPA yet: the live cards' own line is kept (copy rule, decisions
    2026-11-12: keep 1 from the brand's live cards)."""
    import re
    from collections import defaultdict
    live = cards_root(root) / N.slug(brand) / "3-live"
    stale = re.compile(r"[$%]|\d|\b(sale|off|save|friday|cyber|holiday|christmas|limited|today|now)\b", re.I)
    want = {x for x in (N.slug(product or ""), N.slug(product or "").split("-")[0]) if x}
    same, any_ = defaultdict(set), defaultdict(set)
    for f in live.glob("*/*/card.json") if live.is_dir() else []:
        try:
            c = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        brief = c.get("brief_id") or f.parent.name
        for d in (c.get("words") or {}).get("descriptions") or []:
            d = str(d).strip()
            if not d or stale.search(d):
                continue
            any_[d].add(brief)
            if want and N.slug(c.get("product") or "") in want:
                same[d].add(brief)
    pool = same or any_
    return max(pool, key=lambda d: (len(pool[d]), -len(d))) if pool else None


def _to_drive(files):
    """A filed ad is finished, whoever made it (owner, 2026-11-17: finished work lives on the Drive, not the
    Mac). Each source file under runs/ goes to the same path on the Drive and leaves a pointer here; the Mac's
    copy drops once Drive has it (run-kit drive_hand). A no-op off the mount; never stops a filing."""
    try:
        rk = str(Path(__file__).resolve().parents[1] / "run-kit")
        if rk not in sys.path:
            sys.path.append(rk)
        from run_kit import drive_hand
        drive_hand.hand_all([f for f in files if Path(f).suffix.lower() in drive_hand.FINISHED])
    except Exception as e:                       # filing never stops on the Drive copy
        print(f"  Drive: kept on this Mac ({type(e).__name__}: {e})", flush=True)


def read_back(p, brand, brief):
    """The finished ad read off its own picture and put beside its row on the creative matrix (creative-diversity). Written on
    the card as `matrix`; a miss is said, never a stop. QC_DIVERSITY=0 skips it."""
    if os.environ.get("QC_DIVERSITY", "1") == "0" or "unittest" in sys.modules or not brief:
        return
    try:
        sys.path.append(str(HERE.parent / "creative-diversity"))
        import importlib
        MX = importlib.import_module("creative_matrix")
        s = MX.PL._own("check").score_card(p["target"]) or {}
        got = MX.finished(brand, brief, s.get("moves") or {}) if s.get("moves") else None
        if got:
            import cards as C
            card = C.load(Path(p["target"]))
            card["matrix"] = got
            C.save(Path(p["target"]), card)
            print("  matrix: %d of 7 came out as planned%s" % (got["as_planned"], "; off: " + "; ".join("%s planned %s, made %s" % tuple(x) for x in got["off"]) if got["off"] else ""))
    except Exception as e:  # noqa: BLE001
        print(f"  matrix: the finished picture was not read ({type(e).__name__}: {str(e)[:100]})", file=sys.stderr)


def taken(brand, brief):
    """The ad is filed: the plan every chain reads says so (creative-diversity creative_plan.py). Never stops a filing."""
    try:
        sys.path.append(str(HERE.parent / "creative-diversity"))
        import importlib
        importlib.import_module("creative_plan").mark(brand, brief, "filed")
    except Exception as e:  # noqa: BLE001
        print(f"plan not marked ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)


def to_check(brand, lane, fmt, media, words=None, links=(), made_by=None, *, dry_run=False,
             replace=False, **kw):
    """Plan and (unless dry_run) write one card folder. Returns the plan with `state`."""
    # every card's words and page are the lowest-CPA ones (owner, 2026-11-16; lowest_cpa.py): 2 primary texts, 2
    # headlines, 2 descriptions and one page. `keep_words=True` (or LOWEST_CPA_OFF=1) files the words given as they are.
    keep = kw.pop("keep_words", False)
    if not keep and os.environ.get("LOWEST_CPA_OFF") != "1" and not kw.get("root") and not os.environ.get("META_CARDS_ROOT"):
        try:
            import lowest_cpa as LC
            lw, pk = LC.words(brand, promo=(kw.get("angle") == "promo"))
            words = dict(words or {}, **{k: v for k, v in lw.items() if v})
            if not links and pk.get("page"):
                ids = [LC.link_id_for(brand, x["url"]) for x in (pk["page"], pk["page"].get("also")) if x]
                links = [i for i in ids if i] or links
            if len(words.get("descriptions") or []) < 2:
                d = live_description(brand, kw.get("product"), kw.get("root"))
                if d and d not in (words.get("descriptions") or []):
                    words["descriptions"] = list(words.get("descriptions") or []) + [d]
            kw["copy_checked"] = True if kw.get("copy_checked") is None else kw["copy_checked"]
        except Exception as e:  # noqa: BLE001 — the picker failing never stops a filing; the card's own checks still run
            print(f"lowest_cpa: not applied ({str(e)[:120]})", file=sys.stderr)
    # only a real filing runs the copywriter: tests and proofs file into their own --root / $META_CARDS_ROOT,
    # and NO_AD_WORDS=1 turns it off
    if (not dry_run and kw.get("brief") and not kw.get("root") and not os.environ.get("META_CARDS_ROOT")
            and os.environ.get("NO_AD_WORDS") != "1"
            and W.missing(clean_words(words))):
        words = copy_machine(brand, kw["brief"], kw.get("product")) or words
    words = dict(words or {})
    if not words.get("descriptions") and description_on("fill"):   # none: 1 from the brand's live cards
        d = live_description(brand, kw.get("product"), kw.get("root"))
        if d:
            words["descriptions"] = [d]
    if kw.get("copy_checked") is None and kw.get("brief") and kw["brief"] != "none":
        runs = W.runs_for_brief(brand, kw["brief"], product=kw.get("product"))
        kw["copy_checked"] = bool(runs) and all(W.checked(r) for r in runs)
    if not dry_run and not kw.get("root") and not os.environ.get("META_CARDS_ROOT"):
        read_concept(brand, kw.get("brief"), kw.get("product"))   # a trial root never writes the brief register
    p = plan(brand, lane, fmt, media, words, links, made_by, dry_run=dry_run, **kw)
    if dry_run:
        p["state"] = ("would skip: already in " + ", ".join(p["already"])) if p["already"] and not replace \
            else "would file"
    else:
        p["state"], _ = write(p, replace)
        if p["state"] in ("filed", "replaced"):          # what the cover rule holds this card on, said at filing
            p["cover_checks"] = CR.checks(p["target"], p["card"], lane, "1-check")
        if p["state"] in ("filed", "replaced") and not kw.get("root"):
            import ads_index; ads_index.rebuild_quietly(brand)       # the finished-ads index follows every new card
        if p["state"] in ("filed", "replaced") and not kw.get("root") and not os.environ.get("META_CARDS_ROOT"):
            record_openings(brand, p["card"])                        # a trial root never writes the brief register
            if kw.get("brief"):
                taken(brand, kw["brief"])
                if lane in ("image", "carousel"):
                    read_back(p, brand, kw["brief"])
        if p["state"] in ("filed", "replaced"):
            _to_drive([src for src, _ in p["files"]])
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
    lines += [f"           NOT READY — {CR.LABELS[k]}: {v['why']}"
              for k, v in (p.get("cover_checks") or {}).items() if not v["ok"]]
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
    ap.add_argument("--angle", help="only for an ad whose brief has no angle; the brief's own angle always wins and a different one is refused (components/naming/ANGLE.md)")
    ap.add_argument("--media", nargs="+", required=True, help="the files, in order")
    ap.add_argument("--thumbs", nargs="*", default=[], help="a designed thumbnail per video, in the same order (optional)")
    ap.add_argument("--cover-records", nargs="*", default=[],
                    help="a cover record per thumbnail, in the same order (JSON files: swipe, frame, version, headline); "
                         "default: <cover>.cover.json beside each cover, else image production's record of it")
    ap.add_argument("--openings", nargs="*", default=[],
                    help="the opening each video carries, in the same order (default: read from the edit's own "
                         "record beside each render, openings.py)")
    ap.add_argument("--words", help="words.json, a copywriter stage8 render, or a copywriter run folder")
    ap.add_argument("--links", nargs="*", default=[], help="catalog link ids (default: the brief's landing page)")
    ap.add_argument("--tool")
    ap.add_argument("--run")
    ap.add_argument("--creator")
    ap.add_argument("--root", help="the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    import importlib.util as _u, pathlib as _pl
    _s = _u.spec_from_file_location("profile_arg", next(q for q in _pl.Path(__file__).resolve().parents if q.name == "components") / "naming" / "profile_arg.py")
    _PA = _u.module_from_spec(_s); _s.loader.exec_module(_PA)   # --profile <avatar>[_<sub>][_<demographic>] (naming/PEOPLE.md)
    a = ap.parse_args(_PA.expand(None, has=('avatar',)))
    checked = W.checked(a.words) if a.words and (Path(a.words).is_dir() or Path(a.words).suffix == ".json") else None
    words = W.from_file(a.words) if a.words else (W.for_brief(a.brand, a.brief)[0] if a.brief else W.empty())
    try:
        p = to_check(a.brand, a.lane, a.format or ("carousel" if a.lane == "carousel" else "flexible"),
                     a.media, words, a.links, {"tool": a.tool, "run": a.run, "creator": a.creator},
                     ad_name=a.ad_name, product=a.product, brief=a.brief, batch=N.norm_batch(a.batch),
                     old_name=a.old_name, avatar=a.avatar, angle=a.angle, root=a.root, dry_run=a.dry_run, replace=a.replace, thumbs=a.thumbs,
                     copy_checked=checked, cover_records=a.cover_records or None, openings=a.openings or None)
    except (Refused, ValueError) as e:
        sys.exit(f"REFUSED  {e}")
    print(show(p, verbose=True))
    if a.dry_run:
        print(json.dumps(p["card"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
