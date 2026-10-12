#!/usr/bin/env python3
"""feed_carousel — a finished carousel into 1-check, as one card (format "carousel").

    feed_carousel.py <slides folder> --brand brand-b --product gadget-bump-eliminator \\
        [--brief brief-0201] [--batch …] [--links …] [--pick 3=<file>] [--words …] [--dry-run] [--root …]

The slides folder is either
  - a sequence run (tools/image-edit/sequence.py → runs/image-edit/<brand>/<label>/,
    with sequence.json): slide 1 is the plate it started from, slide N the delivered
    picture in slide-NN/ (the first one, unless --pick N=<file> names another), or
  - a folder of finished slides named slide-01.png, slide-02.png … (the clipper
    carousels, runs/image-edit/brand-b/clipper-carousels/<run>/), or a delivery folder:
    `<brief>--slide-NN--vN.png` (a designer's, deliver-brief naming) or
    `<unit>_asset-NN.png` (named by the hourly delivery rule; asset NN is slide NN).

Every position from 1 up must have its picture, or nothing is filed and the gap is
named. Writes `meta/<brand>/1-check/carousel/<ad name>/<ad name>_slide-NN.png` in order
+ card.json. The run folder keeps its originals.

The batch: --batch, else today's first letter not already used by another carousel of
the same brand/product/brief (the same run filed again finds its own card and reuses it).
Words: --words, else the brief's copywriter runs, else empty (the card's check fails).
"""
import argparse, json, os, re, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N  # noqa: E402
import card_words as W  # noqa: E402
import to_check as T  # noqa: E402

# A slide's position, read off its name: `slide-03.png` (a run folder),
# `<brief>--slide-03--v2.png` (a designer's delivery, deliver-brief naming) or
# `<unit>_asset-03.png` (a delivery the hourly rule has named — the files are
# renamed in order, so asset NN is slide NN). Several versions of one slide:
# the highest `--vN` wins.
_FLAT = re.compile(r"(?:^|--|_)(?:slide|asset)-(\d{2})(?:--v(\d+))?\.(png|jpe?g|webp)$", re.I)


def slides(folder, picks=None):
    """[(position, file)] in order, and the gaps (positions with no picture)."""
    folder = Path(folder)
    picks = {int(k): Path(v) for k, v in (picks or {}).items()}
    seq = folder / "sequence.json"
    got = {}
    if seq.is_file():
        s = json.loads(seq.read_text())
        got[1] = Path(s["slide_one"])
        for sl in s.get("slides") or []:
            d = [Path(x) for x in sl.get("delivered") or []]
            if d:
                got[int(sl["slide"])] = d[0]
            else:
                got.setdefault(int(sl["slide"]), None)
    else:
        best = {}
        for p in sorted(folder.iterdir()):
            m = _FLAT.search(p.name)
            if m and not any(w in p.name.lower() for w in ("swipe", "control", "reference", "candidate")):
                n, v = int(m.group(1)), int(m.group(2) or 0)
                if n not in best or v >= best[n][0]:
                    best[n] = (v, p)
        got.update({n: p for n, (v, p) in best.items()})
    got.update(picks)
    if not got:
        return [], []
    top = max(got)
    gaps = [n for n in range(1, top + 1) if not got.get(n) or not Path(got[n]).is_file()]
    return [(n, Path(got[n])) for n in range(1, top + 1) if n not in gaps], gaps


def batch_for(root, brand, product, brief, run, day=None):
    """This run's own batch if it was filed before; else the first free letter today."""
    day = day or date.today()
    for letter in "abcdefghijklmnopqrstuvwxyz":
        b = N.batch_id(day, letter)
        ad = N.short_unit(brand, product, brief or "none", b)
        homes = [Path(root) / brand / s / "carousel" / ad for s in T.STATES]
        here = [h for h in homes if h.is_dir()]
        if not here:
            return b
        card = json.loads((here[0] / "card.json").read_text()) if (here[0] / "card.json").is_file() else {}
        if (card.get("made_by") or {}).get("run") == run:
            return b
    raise T.Refused(f"26 carousels of {product} on {day} already")


def _rel(p):
    p = Path(p).resolve()
    for base in (REPO, Path(os.environ.get("AI_WORKSPACE") or REPO)):
        if p.is_relative_to(base):
            return str(p.relative_to(base))
    return str(p)


def feed(folder, brand, product=None, *, brief=None, batch=None, links=(), picks=None, words=None,
         root=None, dry_run=False, replace=False, repo=REPO):
    """Plan or write the carousel's card. Returns (plan, words source)."""
    order, gaps = slides(folder, picks)
    if gaps:
        raise T.Refused(f"{Path(folder).name}: no finished picture for slide(s) {', '.join(map(str, gaps))} "
                        f"— pick one with --pick N=<file>")
    if not order:
        raise T.Refused(f"{Path(folder).name}: no slides found (sequence.json or slide-NN.png)")
    facts = T.brief_facts(brand, brief, product)
    product = product or facts.get("product")
    if not product:
        raise T.Refused("which product? pass --product (or a brief whose header names it)")
    run = _rel(folder)
    if words is None:
        words, src = W.for_brief(brand, brief, repo, product)
        src = src or "nothing found"
    else:
        src = "given"
    rootp = T.cards_root(root)
    batch = N.norm_batch(batch) if batch else batch_for(rootp, N.slug(brand), N.slug(product), brief, run)
    p = T.to_check(brand, "carousel", "carousel", [f for _, f in order], words, links,
                   {"tool": "image-edit", "run": run, "creator": None},
                   product=product, brief=brief, batch=batch, root=rootp, dry_run=dry_run, replace=replace)
    return p, src


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", help="a sequence run folder, or a folder of slide-NN.png")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--product", help="product slug (default: the brief's)")
    ap.add_argument("--brief")
    ap.add_argument("--batch")
    ap.add_argument("--links", nargs="*", default=[])
    ap.add_argument("--pick", action="append", default=[], metavar="N=FILE", help="the chosen picture for slide N")
    ap.add_argument("--words", help="words.json, a copywriter stage8 render, or a copywriter run folder")
    ap.add_argument("--root", help="the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    picks = dict(x.split("=", 1) for x in a.pick)
    try:
        p, src = feed(a.folder, a.brand, a.product, brief=a.brief, batch=a.batch, links=a.links, picks=picks,
                      words=W.from_file(a.words) if a.words else None, root=a.root,
                      dry_run=a.dry_run, replace=a.replace)
    except (T.Refused, ValueError) as e:
        sys.exit(f"REFUSED  {e}")
    print(T.show(p, verbose=True))
    print(f"           words from: {src}")
    if a.dry_run:
        print(json.dumps(p["card"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
