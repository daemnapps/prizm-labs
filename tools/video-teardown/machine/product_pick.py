"""v2 product decision (18 Oct 2026, the owner): pick the product a run sells by
rule, write down why, and stop to ask only when the rules can't decide.

Brand-agnostic: every fact is read from brands/<brand>/, never typed here.
  1. lane is declared on the run (paid | organic) — never read off the swipe. It
     is recorded for the ASK only: organic and paid are the same video, so the
     lane never changes the product (the owner, 2026-10-20: "Our organic and paid
     content should be indistinguishable. The only core difference is really just
     the ask and the way that we gradualize that sales pitch." — VIDEO-RULINGS V1).
  2. candidates = the brand's sellable products (products/heroes.json `sellable`,
     else every product file), minus drafts named in `never`
  3. kept: the products with an IN-USE funnel (web/funnels/funnels.json); with no
     in-use funnel at all, the brand's heroes (products/heroes.json `heroes`)
  4. exactly one left -> pick it; several -> Settings `paid_product`, else the ad
     decides; none -> stop with the short list
  (Until 2026-10-21 organic took the brand's `organic_hero` instead — retired by V1.)
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _read(p):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def _setting(key):
    try:
        d = json.loads((REPO / "runs" / "settings" / "settings.json").read_text())
        for part in key.split("."):
            d = d[part]
        return d
    except Exception:  # noqa: BLE001
        return None


def _tiebreak(cands, run_dir, live_count):
    """Several products fit: pick the one the ad itself is about. Each product's
    own words (its name parts the others don't share, e.g. face vs body) are
    counted in what teardown read off the swipe and who it speaks to; a tie goes
    to the product with more live funnels. Brand-agnostic: words come from the
    product names."""
    import re
    parts = {c: set(c.split("-")) for c in cands}
    shared = set.intersection(*parts.values()) if parts else set()
    score = {c: 0 for c in cands}
    label = Path(run_dir).name.lower() if run_dir else ""            # the batch's own name says it most plainly
    for c in cands:                                                  # (e.g. grandma-house-face)
        score[c] += 10 * sum(1 for w in parts[c] - shared if re.search(r"(^|-)" + re.escape(w) + r"(-|$)", label))
    for n, weight in (("1b-audience.md", 3), ("2-spec.md", 1)):   # who it speaks to counts most; the shot-by-shot
        f = Path(run_dir) / "stages" / n if run_dir else None      # record is left out ("body language" isn't the body)
        if f and f.is_file():
            text = f.read_text(errors="ignore").lower()
            for c in cands:
                score[c] += weight * sum(len(re.findall(r"\b" + re.escape(w) + r"\b", text)) for w in parts[c] - shared)
    best = sorted(cands, key=lambda c: (score[c], live_count.get(c, 0)), reverse=True)
    return best[0], score


def lane_of(brand, lane):
    """(paid | organic | None, why): the run's declared lane, else the brand's Settings default.
    The writing reads it for the ASK (video-writing's {ask_lane})."""
    if lane in ("paid", "organic"):
        return lane, f"lane: {lane} (declared on the run)"
    d = _setting(f"brands.{brand}.default_lane")
    if d in ("paid", "organic"):
        return d, "lane: from Settings (no lane on the run)"
    return None, "lane not declared: say --lane paid or --lane organic"


def decide(brand, lane, run_dir=None):
    b = REPO / "brands" / brand
    lane, said = lane_of(brand, lane)
    if lane is None:
        return None, [said], []
    why = [said]
    heroes = _read(b / "products" / "heroes.json") or {}
    files = {p.stem for p in (b / "products").glob("*.md") if p.stem not in ("README", "offer-bank")} | \
            {p.name for p in (b / "products").iterdir() if p.is_dir() and (p / "product.md").is_file()}
    sell = [s.get("handle") for s in heroes.get("sellable") or [] if s.get("handle")]
    cands = [s for s in (sell or sorted(files)) if s in files]
    nv = heroes.get("never") or []
    never = set(nv.get("handles") or []) if isinstance(nv, dict) else set(nv)   # the brand file keeps them under "handles"
    cands = [c for c in cands if c not in never]
    why.append(f"sellable products on file: {len(cands)}")
    f = _read(b / "web" / "funnels" / "funnels.json") or {}
    live_count = {}
    for x in f.get("funnels", []):
        if x.get("product") and str(x.get("status", "")).startswith("in use"):
            live_count[x["product"]] = live_count.get(x["product"], 0) + 1
    live = [c for c in cands if c in live_count]
    if live:
        cands = live
        why.append("kept the ones with an in-use funnel in web/funnels/funnels.json → " + ", ".join(cands)
                   + f" (the same on both lanes: the {lane} lane changes only the ask)")
    else:
        heroes_list = [h for h in (heroes.get("heroes") or []) if h in cands]
        if not heroes_list:
            why.append("no product with an in-use funnel, and no heroes in products/heroes.json")
            return None, why, cands
        cands = heroes_list
        why.append("no product with an in-use funnel, so the brand's heroes (products/heroes.json) → " + ", ".join(cands))
    if len(cands) > 1:
        pref = _setting(f"brands.{brand}.paid_product")
        if pref and pref in cands:
            why.append(f"tie broken by Settings: {pref}")
            cands = [pref]
        else:
            pick, score = _tiebreak(cands, run_dir, live_count)
            why.append("several fit, so the ad decides: " + ", ".join(f"{c} {n} mention(s)" for c, n in score.items())
                       + f" (the run's name, who it speaks to, the spec) → {pick}")
            cands = [pick]
    if len(cands) == 1:
        why.append(f"picked: {cands[0]}")
        return cands[0], why, cands
    return None, why, cands
