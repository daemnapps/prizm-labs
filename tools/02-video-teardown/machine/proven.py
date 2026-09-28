#!/usr/bin/env python3
"""0p · THE PROVEN GATE — Variation video runs on proven assets only.

Damon, 2026-09-28: "we only run variation on proven assets." Before a
variation tree is laid out, the source ad has to have proof on file:

  organic   views / likes / saves / shares from a swipe-organic manifest row
            whose `teardown_run` or `id` is this ad
            (runs/swipe-organic/<brand>/*/manifest.json)
  paid      spend / purchases / revenue from our own ads, matched by ad id or
            ad name (components/swipe-paid/own/<account>/ads.json)

The BAR is Damon's call and lives in `proven-bar.json` beside this file. A bar
left null means "any proof on file passes"; set a number and anything under it
is refused. No model, no network.

    python3 proven.py <teardown run slug> --brand <brand>
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C  # noqa: E402

BAR_FILE = Path(__file__).resolve().parent / "proven-bar.json"
ORGANIC = ("views", "likes", "saves", "shares", "comments")
PAID = ("spend", "impressions", "clicks", "purchases", "revenue")


def bar():
    try:
        return json.loads(BAR_FILE.read_text())
    except Exception:
        return {}


def _ids(slug):
    """The post / ad id a teardown slug carries (…-<long digits>)."""
    tail = slug.rsplit("-", 1)[-1]
    return {slug, tail}


def organic(brand, slug):
    keys = _ids(slug)
    for mf in sorted((C.WS / "runs" / "swipe-organic" / brand).glob("*/manifest.json")):
        try:
            rows = json.loads(mf.read_text()).get("rows") or []
        except Exception:
            continue
        for r in rows:
            tr = str(r.get("teardown_run") or "")
            if str(r.get("id")) in keys or (tr and tr.rstrip("/").rsplit("/", 1)[-1] in keys):
                return dict(kind="organic", source=str(mf.relative_to(C.WS)),
                            url=r.get("url"), rank=r.get("rank"),
                            **{k: r.get(k) for k in ORGANIC if r.get(k) is not None})
    return None


def paid(brand, slug):
    keys = _ids(slug)
    own = C.WS / "components" / "swipe-paid" / "own"
    for f in sorted(own.glob("*/ads.json")):
        try:
            ads = json.loads(f.read_text()).get("ads") or []
        except Exception:
            continue
        for a in ads:
            if str(a.get("id")) in keys or str(a.get("name")) in keys:
                return dict(kind="paid", source=str(f.relative_to(C.WS)), name=a.get("name"),
                            **{k: a.get(k) for k in PAID if a.get(k) is not None})
    return None


def check(brand, slug):
    """-> (passed, proof, why). Proof is every record found; why names the
    bar that failed, or what was missing."""
    proof = [p for p in (organic(brand, slug), paid(brand, slug)) if p]
    if not proof:
        return False, [], ("no proof on file — not in any swipe-organic manifest "
                           "for this brand and not among our own paid ads")
    b = {k: v for k, v in bar().items() if not k.startswith("_") and v is not None}
    if not b:
        return True, proof, "proof on file (no bar set in proven-bar.json — any proof passes)"
    for p in proof:
        ok = all((p.get(k.replace("min_", "")) or 0) >= v for k, v in b.items()
                 if k.replace("min_", "") in p)
        relevant = [k for k in b if k.replace("min_", "") in p]
        if relevant and ok:
            return True, proof, f"clears the bar on {p['kind']}: " + ", ".join(
                f"{k.replace('min_', '')} {p.get(k.replace('min_', ''))} ≥ {b[k]}" for k in relevant)
    return False, proof, "under the bar in proven-bar.json: " + json.dumps(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    ok, proof, why = check(a.brand, a.slug)
    print(("PASSED — " if ok else "REFUSED — ") + why)
    for p in proof:
        print("  ", json.dumps(p, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
