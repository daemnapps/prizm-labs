#!/usr/bin/env python3
"""feed_creator — a matched creator / editor / designer delivery into 1-check, as one card.

    feed_creator.py --brand brand-a [--folder <watched folder>] [--links …] [--dry-run] [--root …]

The delivery rule (components/naming/delivery_rule.py) matches each delivery folder
to its brief and names it `<brand>_<product>_<brief>_<batch>`; `delivery_rule.py
--apply --to-check` then hands every named folder here. Run alone, this walks the
brand's watched folders (brands/<brand>/briefs/delivery.json) and files every
delivery already in the short form.

Writes `meta/<brand>/1-check/<lane>/<ad name>/` (creator for a creator's footage, video or image for an editor's or designer's work) as `<ad name>_asset-NN.<ext>` (videos or
pictures, the delivery's own order) + card.json. The delivery folder is copied
from, never touched. One already filed (any state) is skipped.

creator: the handle the folder sits under (creators/<brand>/<handle>/DELIVERABLES),
else the brief's talent. Words: a words.json in the delivery folder, else the
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
    p = T.to_check(brand, lane, "flexible", files, words, links,
                   {"tool": "delivery-rule", "run": _rel(folder), "creator": who if lane == "creator" else None},
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


def report(res, verbose=False):
    for p, why, src in res:
        if p:
            print(T.show(p, verbose))
            print(f"           words from: {src} · creator: {p['card']['made_by']['creator']}")
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
    a = ap.parse_args()
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
