#!/usr/bin/env python3
"""feed_image — an image-edit drop into 1-check, one card per ad.

    feed_image.py --brand brand-a --batch 260923a --links link_brand-a_cpk_quiz link_brand-a_cpk_landing
    feed_image.py … --dry-run          print every card it would write, write nothing
    feed_image.py … --root /tmp/meta   a fake meta/ folder (or $META_CARDS_ROOT)

Reads `runs/image-teardown/<brand>/<batch>/deliverable/<ad folder>/` (legacy
`runs/image-edit/` read in place) — variations.py's drop; the pictures sit on
the Drive copy when git holds only the manifest — and writes `meta/<brand>/1-check/image/<ad name>/` through to_check.py.

The words, per ad:
  primary       the drop's own copy.csv row (primary_text, alt_text) — the copy
                chosen for that ad
  headlines,    the copywriter run that wrote that primary text: its stage 8
  descriptions  render's HEADLINES and DESCRIPTIONS lists (found by the body
                text itself, card_words.run_for_body). copy.csv kept the body
                and dropped those lists — this is where they come back from.
  no copy row   the brief's own copywriter runs (card_words.for_brief), else empty
"""
import argparse, csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N  # noqa: E402
import card_words as W  # noqa: E402
import to_check as T  # noqa: E402

PICTURE = {".png", ".jpg", ".jpeg", ".webp"}


def deliverables(brand, batch, repo=REPO):
    """The drop's deliverable folder here, and its copy on the Drive (for this checkout only):
    the new home runs/image-teardown/ first, the legacy runs/image-edit/ second."""
    for machine in ("image-teardown", "image-edit"):
        rel = Path("runs") / machine / N.slug(brand) / batch / "deliverable"
        places = [Path(repo) / rel] + ([T.SHARED / rel] if Path(repo) == REPO else [])
        found = [p for p in places if p.is_dir()]
        if found:
            return found
    return []


def copy_rows(places):
    """copy.csv rows by old ad name, from the first place that has the file."""
    for d in places:
        f = d / "copy.csv"
        if f.is_file():
            with f.open(encoding="utf-8-sig") as fh:
                return {r["ad_name"]: r for r in csv.DictReader(fh)}
    return {}


def _asset_key(p):
    n = (N.parse_any(p.stem) or {}).get("asset_n")
    if n:
        return (n, p.name)
    m = re.search(r"(\d+)", p.stem)
    return (int(m.group(1)) if m else 999, p.name)


def pictures(places, folder):
    """The ad's pictures in asset order, from the first place that has any."""
    for d in places:
        f = d / folder
        if f.is_dir():
            pics = sorted((p for p in f.iterdir() if p.suffix.lower() in PICTURE and not p.name.startswith(".")),
                          key=_asset_key)
            if pics:
                return pics
    return []


def words_for(brand, row, brief, repo=REPO):
    """(words, where they came from) for one ad."""
    if not row:
        w, src = W.for_brief(brand, brief, repo)
        return w, src or "nothing found"
    bodies = [b for b in (W.body_of(row.get("primary_text")), W.body_of(row.get("alt_text"))) if b]
    both = (row.get("primary_text") or "") + "\n" + (row.get("alt_text") or "")
    col = lambda k: [x.strip() for x in re.split(r"\n| \| ", row.get(k) or "") if x.strip()]
    heads = col("headlines") or W.listed(both, "HEADLINES")
    descs = col("descriptions") or W.listed(both, "DESCRIPTIONS")
    src = "copy.csv"
    if not heads or not descs:
        run = next((r for r in (W.run_for_body(brand, b, repo) for b in bodies) if r), None)
        if run:
            r = W.parse_render(W.render_of(run))
            heads = heads or r["headlines"]
            descs = descs or r["descriptions"]
            src = f"copy.csv + {run.relative_to(repo)}"
    return {"primary": bodies, "headlines": heads, "descriptions": descs}, src


def ads(brand, batch, repo=REPO):
    """Every ad folder in the drop: (old name, its manifest, places)."""
    places = deliverables(brand, batch, repo)
    seen = {}
    for d in places:
        for mf in sorted(d.glob("*/manifest.json")):
            seen.setdefault(mf.parent.name, json.loads(mf.read_text()))
    return places, seen


def feed(brand, batch, links, *, root=None, dry_run=False, replace=False, repo=REPO, only=None):
    """Plan or write every card in the drop. Returns [(plan or None, why, words source)]."""
    places, found = ads(brand, batch, repo)
    if not places:
        raise T.Refused(f"no drop at runs/image-teardown/{brand}/{batch}/deliverable nor the legacy "
                        f"runs/image-edit/{brand}/{batch}/deliverable (here or on the Drive)")
    rows = copy_rows(places)
    machine = places[0].parent.parent.parent.name     # image-teardown, or image-edit for a legacy drop
    out = []
    for old, man in sorted(found.items()):
        d = N.parse_any(man.get("ad_name") or old) or {}
        product, brief = man.get("product") or d.get("product"), d.get("brief_id") or N.brief_id(man.get("brief"))
        if only and brief not in only and man.get("brief") not in only:
            continue
        words, src = words_for(brand, rows.get(old) or rows.get(man.get("ad_name")), brief, repo)
        try:
            p = T.to_check(brand, "image", "flexible", pictures(places, old), words, links,
                           {"tool": machine, "run": f"runs/{machine}/{brand}/{batch}", "creator": None},
                           product=product, brief=brief, batch=N.norm_batch(man.get("batch") or d.get("batch") or batch),
                           old_name=old, avatar=None, angle=None, root=root, dry_run=dry_run, replace=replace)
            out.append((p, None, src))
        except (T.Refused, ValueError) as e:
            out.append((None, f"{old}: {e}", src))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--batch", required=True, help="the drop folder name, e.g. 260923a")
    ap.add_argument("--links", nargs="*", default=[], help="catalog link ids — each becomes its own Meta ad (default: each brief's landing page)")
    ap.add_argument("--briefs", help="only these briefs (comma list, either spelling)")
    ap.add_argument("--root", help="the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--replace", action="store_true", help="re-file an ad still waiting in 1-check")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    a = ap.parse_args()
    only = {f for b in a.briefs.split(",") for f in N.brief_forms(b.strip())} if a.briefs else None
    try:
        res = feed(a.brand, a.batch, a.links, root=a.root, dry_run=a.dry_run, replace=a.replace, only=only)
    except T.Refused as e:
        sys.exit(f"REFUSED  {e}")
    short = 0
    for p, why, src in res:
        if p:
            print(T.show(p, a.verbose or a.dry_run))
            print(f"           words from: {src}")
            short += bool(p["missing_words"])
        else:
            print(f"REFUSED    {why}")
    ok = [p for p, _, _ in res if p]
    root = ok[0]["root"] if ok else None
    print(f"\n{len(ok)} card(s) {'planned' if a.dry_run else 'written'} · {short} missing words · "
          f"{sum(1 for p, _, _ in res if not p)} refused" + (f" · {root}/{a.brand}/1-check/image/" if root else ""))


if __name__ == "__main__":
    main()
