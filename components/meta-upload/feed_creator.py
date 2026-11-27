#!/usr/bin/env python3
"""feed_creator — a matched creator / editor / designer delivery into 1-check, as one card.

    feed_creator.py --brand brand_b [--folder <watched folder>] [--links …] [--dry-run] [--root …]
    feed_creator.py --brand brand_b --trybe [<deliveries.json> …] [--links …] [--dry-run] [--root …]

--trybe files the creator machine's Trybe videos (runs/creator-machine/<brand>/<label>/deliveries.json),
one card per submission carrying its trybe_id (see feed_trybe below).

The delivery rule (components/naming/delivery_rule.py) matches each delivery folder
to its brief and names it `<brand>_<product>_<brief>_<batch>`; `delivery_rule.py
--apply --to-check` then hands every named folder here. Run alone, this walks the
brand's watched folders (brands/<brand>/briefs/delivery.json) and files every
delivery already in the short form.

Writes `meta/<brand>/1-check/<lane>/<ad name>/` (creator for a creator's footage, video or image for an editor's or designer's work) as `<ad name>_asset-NN.<ext>` (videos or
pictures, the delivery's own order) + card.json. The delivery folder is copied
from, never touched. One already filed (any state) is skipped.

creator: the handle the folder sits under (creators/<brand>/<handle>/DELIVERABLES),
else the brief's talent. made_by.who: who made it — the watched folder's name in
delivery.json's `who` map (creator, editor …), else that creator handle. Words: a words.json in the delivery folder, else the
brief's copywriter runs, else empty (the card's check fails).
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N  # noqa: E402
import card_words as W  # noqa: E402
import to_check as T  # noqa: E402
import delivery_rule as DR  # noqa: E402


def creator_of(folder, facts):
    m = re.search(r"/creators/[^/]+/([^/]+)/DELIVERABLES(/|$)", str(folder))
    if m and not m.group(1).lower().startswith("general"):
        return m.group(1)
    t = facts.get("talent")
    return t if t and t != "none" else None


def who_made(brand, folder, facts=None):
    """Who made this delivery, by the watched folder it was dropped in: the `who` map in
    brands/<brand>/briefs/delivery.json (an editor's or designer's name, 15 Oct 2026),
    else the creator handle the folder sits under, else the brief's talent, else None."""
    parent = Path(folder).resolve().parent
    try:
        _, cfg = DR.load(brand)
    except Exception:  # noqa: BLE001  a brand with no delivery.json still files
        cfg = {}
    for watched, name in (cfg.get("who") or {}).items():
        try:
            if DR.resolve(watched).resolve() == parent:
                return name
        except OSError:
            continue
    return creator_of(folder, facts or {})


def lane_of(folder, files):
    if re.search(r"/creators/[^/]+/[^/]+/DELIVERABLES(/|$)", str(folder)):
        return "creator"
    vids = sum(1 for f in files if f.suffix.lower() in (".mp4", ".mov", ".m4v"))
    return "video" if vids else "image"


def newest(folder):
    ts = [p.stat().st_mtime for p in Path(folder).iterdir() if p.is_file()]
    return max(ts) if ts else 0


def _order(p):
    n = (N.parse_any(p.stem) or {}).get("asset_n")
    return (n or 999, p.name)


def _rel(folder):
    f = str(folder)
    i = f.find("Shared drives/")
    return f[i + len("Shared drives/"):] if i >= 0 else f


def feed_one(brand, folder, *, links=(), root=None, dry_run=False, replace=False, repo=REPO):
    """One named delivery folder → (plan, words source)."""
    folder = Path(folder)
    d = N.parse_short(folder.name)
    if not d or d.get("asset") or d.get("funnel"):
        raise T.Refused(f"{folder.name}: not named yet (the delivery rule names it first)")
    brief = d["brief"]
    if brief == "none" and (folder / "naming.json").is_file():
        brief = json.loads((folder / "naming.json").read_text()).get("brief") or "none"
    files = sorted((p for p in folder.iterdir() if DR.is_work(p)), key=_order)
    facts = T.brief_facts(brand, brief, d["product"])
    if (folder / "words.json").is_file():
        words, src = W.from_file(folder / "words.json"), "words.json in the delivery"
    else:
        words, src = W.for_brief(brand, brief, repo, d["product"])
        src = src or "nothing found"
    who = creator_of(folder, facts)
    # a creator's own footage is the creator lane; an editor's or designer's
    # finished work is the video or image lane, by what the files are
    lane = lane_of(folder, files)
    # already filed (any state): only look, never file again — and never start the copywriter for it again
    # (16 Oct 2026: the runner reads every delivery every 10 minutes)
    if not replace and not dry_run and T.where_is(T.cards_root(root), N.slug(brand), lane, folder.name):
        dry_run = True
    p = T.to_check(brand, lane, "flexible", files, words, links,
                   {"tool": "delivery-rule", "run": _rel(folder), "creator": who if lane == "creator" else None,
                    "who": who_made(brand, folder, facts)},
                   ad_name=folder.name, brief=brief, root=root, dry_run=dry_run, replace=replace)
    return p, src


def feed_root(brand, watched, since=None, **kw):
    """Every named delivery under one watched folder → [(plan or None, why, words source)].
    `since` (a date): only deliveries whose newest file is from that day on — so
    work delivered before the approval road existed (much of it already live in
    Meta) never lands in 1-check by itself."""
    from datetime import datetime
    cut = datetime.fromisoformat(str(since)).timestamp() if since else None
    out = []
    for f in sorted(p for p in Path(watched).iterdir() if p.is_dir()):
        d = N.parse_short(f.name)
        if not d or d.get("asset") or d.get("funnel"):
            continue
        if cut and newest(f) < cut:
            continue
        try:
            p, src = feed_one(brand, f, **kw)
            out.append((p, None, src))
        except (T.Refused, ValueError) as e:
            out.append((None, f"{f.name}: {e}", None))
    return out


# ---------------------------------------------------------------- Trybe videos (2026-11-15)
# The creator machine saves every new Trybe submission and lists it in
# runs/creator-machine/<brand>/<label>/deliveries.json (the hand-off with "VIDEO · Creator videos back"):
# one record per submission with trybe_id, submission_id, creator, products, state, media_type and `media`,
# a builder-card-4 ref {drive_id, label, bytes} (a bare "Shared Assets/…" label is read too); `brief` and
# `product` (our ids) when known. EVERY record with a file becomes one card in 1-check/creator/ — no gate
# (2026-11-15) — carrying its trybe_id, so the uploader ends the Meta ad name with the id and puts
# trybe=<id> on the link (trybe_tag.py). One card per submission: the name must end with ITS id.
def deliveries_of(brand, label=None, repo=REPO):
    """Every deliveries.json the creator machine wrote for a brand (one label, or all), oldest first."""
    base = Path(repo) / "runs" / "creator-machine" / N.slug(brand)
    files = [base / label / "deliveries.json"] if label else sorted(base.glob("*/deliveries.json"))
    return [f for f in files if f.is_file()]


def _ref(media):
    if isinstance(media, dict):
        return media if media.get("label") else None
    if isinstance(media, str) and media.startswith("Shared Assets/"):
        return {"label": media}
    return None


def _fetch(ref):
    """A Drive ref -> a local file, through gdrive-creator's stored-reference surface (keys first)."""
    p = str(REPO / "components/gdrive-creator")
    if p not in sys.path:
        sys.path.append(p)
    from gdrive_creator import refs
    return Path(refs.local(ref))


ALIASES = HERE / "trybe_products.json"


def trybe_aliases(brand, path=None):
    """{Trybe product name: our product id} for a brand (trybe_products.json)."""
    try:
        d = json.loads(Path(path or ALIASES).read_text())
    except (OSError, ValueError):
        return {}
    return (d.get("brands") or {}).get(N.slug(brand)) or {}


def trybe_product(brand, rec, aliases=None):
    """Our product id for a Trybe record: its own `product`, else the first Trybe product name that the alias
    table (trybe_products.json) or naming resolves to a KNOWN product id (names.product_ids). An unknown name is
    never guessed: None."""
    known = set(N.product_ids(brand))
    table = trybe_aliases(brand) if aliases is None else aliases
    for name in ([rec["product"]] if rec.get("product") else []) + list(rec.get("products") or []):
        pid = table.get(name) or N.product_id(brand, name)
        if pid in known:
            return pid
    return None


def live_words(root, brand, product):
    """(words, source, copy_checked) from the newest LIVE card for this product with a body and a headline —
    a briefless creator ad reuses Meta text from a live card, no unique copy per ad (the owner's standing rule,
    ruled for creator ads by the main session 2026-11-15). (empty, None, False) when there is none."""
    best = None
    live = Path(root) / N.slug(brand) / "3-live"
    for c in sorted(live.glob("*/*/card.json")) if live.is_dir() else []:
        try:
            card = json.loads(c.read_text())
        except (OSError, ValueError):
            continue
        w = card.get("words") or {}
        if card.get("product") != product or not w.get("primary") or not w.get("headlines"):
            continue
        when = max([m.get("at") or "" for m in card.get("meta") or []] + [card.get("made_at") or ""])
        if not best or when > best[0]:
            best = (when, card)
    if not best:
        return W.empty(), None, False
    card = best[1]
    return card["words"], f"live card {card.get('ad_name')}", bool(card.get("copy_checked"))


def program_pages(brand, product, repo=REPO):
    """(catalog link ids, why) for a briefless creator ad: the brand's creator funnel (content-creators/program.json
    funnel.url). The catalog link at that url; else the live offer pages inside that funnel that sell this product
    (components/naming page_pick.offer_pages). ([], reason) when neither exists."""
    try:
        import brandpath as BP          # on sys.path through naming's names.py
        prog = json.loads((BP.brand_path(brand, "content-creators", root=Path(repo) / "brands") / "program.json").read_text())
    except (OSError, ValueError, KeyError) as e:
        return [], f"no creator program file ({e})"
    url = ((prog.get("funnel") or {}).get("url") or "").rstrip("/")
    if not url:
        return [], "the creator program names no funnel url"
    recs = ((T._catalog().get("brands") or {}).get(N.slug(brand)) or {}).get("records") or {}
    links = {k: (r.get("url") or "").rstrip("/") for k, r in recs.items() if r.get("type") == "link"}
    exact = [k for k, u in links.items() if u == url]
    if exact:
        return exact[:1], None
    import page_pick as PP
    inside = [k for k in PP.offer_pages(brand, product) if links.get(k, "").startswith(url + "/")]
    if inside:
        return inside[:1], None
    return [], f"no catalog page at the creator funnel {url}, and none inside it sells {product}"


def trybe_ads(brand, repo=REPO):
    """{trybe_id: ads Trybe already counts on it}, from the newest submissions.json the creator machine kept.
    A submission already made into an ad (by hand, or in Trybe) is not filed again."""
    base = Path(repo) / "runs" / "creator-machine" / N.slug(brand)
    out = {}
    for f in sorted(base.glob("*/submissions.json")):        # oldest label first, newest wins
        try:
            for x in json.loads(f.read_text()):
                if x.get("trybe_id"):
                    out[x["trybe_id"]] = int(((x.get("ads") or {}).get("count")) or 0)
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return out


def filed_trybe(root, brand):
    """{trybe_id: ad name} for every creator card already on the road (any state)."""
    out = {}
    for state in T.STATES:
        lane = Path(root) / N.slug(brand) / state / "creator"
        if not lane.is_dir():
            continue
        for f in lane.iterdir():
            c = f / "card.json"
            if not c.is_file():
                continue
            try:
                tid = json.loads(c.read_text()).get("trybe_id")
            except (OSError, ValueError):
                continue
            if tid:
                out.setdefault(tid, f.name)
    return out


def trybe_ad_name(root, brand, product, brief, day, taken):
    """<brand>_<product>_<brief>_batch-<day>-<letter>, the first letter no card (any state) and no name in
    `taken` holds — so two creators' videos on one brief and day are two ads."""
    for letter in "abcdefghijklmnopqrstuvwxyz":
        name = T.ad_name_for(brand, product, brief, f"batch-{day}-{letter}")
        if name not in taken and not T.where_is(root, N.slug(brand), "creator", name):
            taken.add(name)
            return name
    raise T.Refused(f"26 creator ads for {product} {brief} on {day} already")


def feed_trybe(brand, deliveries, *, links=(), root=None, dry_run=False, fetch=None, repo=REPO, since=None):
    """Every Trybe record in the deliveries.json files -> [(plan or None, why, words source)].
    A submission already filed (any state, found by its trybe_id) is skipped quietly; one Trybe already counts
    an ad on (built by hand before this road) is listed and not filed. `since` (YYYY-MM-DD): only submissions
    created that day or later."""
    fetch = fetch or _fetch
    cards = T.cards_root(root)
    have = filed_trybe(cards, brand)
    ads = trybe_ads(brand, repo)
    taken, out = set(), []
    for dfile in deliveries:
        dfile = Path(dfile)
        try:
            recs = json.loads(dfile.read_text())
        except (OSError, ValueError) as e:
            out.append((None, f"{dfile}: unreadable ({e})", None))
            continue
        try:
            run = str(dfile.resolve().relative_to(Path(repo).resolve()))
        except ValueError:
            run = dfile.name
        for rec in recs if isinstance(recs, list) else []:
            tid = rec.get("trybe_id")
            who = rec.get("creator")
            tag = f"{tid or '?'} ({who or 'unknown creator'})"
            try:
                import trybe_tag as TT
                tid = TT.clean(tid)
            except ValueError as e:
                out.append((None, f"{tag}: {e}", None))
                continue
            if not tid:
                out.append((None, f"{tag}: no trybe_id on the record", None))
                continue
            if tid in have:
                continue                                    # already on the road, in any state
            if since and str(rec.get("created_at") or "")[:10] < str(since):
                continue
            n_ads = int(((rec.get("ads") or {}).get("count") if isinstance(rec.get("ads"), dict) else 0) or 0) \
                or ads.get(tid, 0)
            if n_ads:
                out.append((None, f"{tag}: already an ad ({n_ads} counted by Trybe) — not filed again", None))
                continue
            ref = _ref(rec.get("media"))
            if not ref:
                out.append((None, f"{tag}: no saved video on the record (the creator machine kept no file)", None))
                continue
            product = trybe_product(brand, rec)
            if not product:
                out.append((None, f"{tag}: Trybe's product {rec.get('products')} is not one of our product ids — "
                                  "the record needs `product`, or naming needs the alias", None))
                continue
            brief = rec.get("brief") or "none"
            day = str(rec.get("created_at") or "")[:10] or None
            if not day:
                out.append((None, f"{tag}: no created_at", None))
                continue
            try:
                name = trybe_ad_name(cards, brand, product, brief, day, taken)
                media = Path(ref["label"]).name if dry_run else fetch(ref)
                pages, checked, brief_id = list(links or []), None, None
                if brief != "none":
                    words, src = W.for_brief(brand, brief, repo, product)
                else:
                    # briefless (main session, 2026-11-15): words from a live card for the product, the page from
                    # the creator program's funnel, brief id trybe-<id>
                    words, src, checked = live_words(cards, brand, product)
                    brief_id = f"trybe-{tid}"
                    if not pages:
                        pages, why = program_pages(brand, product, repo)
                        if why:
                            print(f"  NOTE {tag}: {why}")
                p = T.to_check(brand, "creator", "flexible", [media], words, pages,
                               {"tool": "creator-machine", "run": run, "creator": who, "who": who,
                                "trybe_submission": rec.get("submission_id"), "trybe_state": rec.get("state")},
                               ad_name=name, brief=brief, product=product, root=root, dry_run=dry_run,
                               trybe_id=tid, brief_id=brief_id, copy_checked=checked)
                have[tid] = name
                out.append((p, None, src or "nothing found (no live card for the product)"))
            except (T.Refused, ValueError, OSError) as e:
                out.append((None, f"{tag}: {e}", None))
    return out


def report(res, verbose=False):
    for p, why, src in res:
        if p:
            print(T.show(p, verbose))
            print(f"           words from: {src} · made by: {p['card']['made_by'].get('who') or p['card']['made_by']['creator']}")
        else:
            print(f"REFUSED    {why}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--folder", action="append", help="a watched folder (default: the brand's delivery.json)")
    ap.add_argument("--links", nargs="*", default=[])
    ap.add_argument("--root", help="the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--since", help="with --trybe: only submissions created on/after this date (YYYY-MM-DD)")
    ap.add_argument("--trybe", nargs="*", metavar="DELIVERIES_JSON",
                    help="file the creator machine's Trybe videos (default: every runs/creator-machine/<brand>/*/deliveries.json)")
    a = ap.parse_args()
    if a.trybe is not None:
        files = [Path(x) for x in a.trybe] or deliveries_of(a.brand)
        res = feed_trybe(a.brand, files, links=a.links, root=a.root, dry_run=a.dry_run, since=a.since)
        print(f"== Trybe: {sum(1 for p, _, _ in res if p)} card(s) from {len(files)} deliveries file(s)")
        report(res, a.verbose)
        return
    _, cfg = DR.load(a.brand)
    for w in [DR.resolve(x) for x in (a.folder or cfg.get("watch", []))]:
        if not w.is_dir():
            print(f"not reachable here: {w}")
            continue
        res = feed_root(a.brand, w, links=a.links, root=a.root, dry_run=a.dry_run, replace=a.replace)
        print(f"== {w.name}: {sum(1 for p, _, _ in res if p)} card(s)")
        report(res, a.verbose)


if __name__ == "__main__":
    main()
