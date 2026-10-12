#!/usr/bin/env python3
"""standard — what good looks like, per brand: the one standard every new ad is judged by.

    standard.py --brand brand-b        writes runs/media-buying/<brand>/standard.json (the latest standard)

the owner, 2 Oct 2026: "we need to standardize … build a standard view of what good looks like … as a
criterion for all of these new ads that we put through our machine. And obviously, this is going
to differ per brand because each brand's metrics and avatars and assets are all different."

the owner, same day: days-to-spend and the $__ checkpoint are out — "how much it actually spent depends
on the budget itself … It's more about: Is this ad even scalable at this X budget?" So three signals,
each over the ad's life (ads with $__+ spent), from the warehouse (no Meta calls): cost per sale,
return on ad spend, and SHARE OF SPEND — the asset's spend over its campaign's whole spend on the
days it ran. For each:
  TOP 1% PACE  the typical top-1% ad at that point (median)
  GOOD         the line 3 of 4 top-1% ads cleared
  CUT          the typical ad outside the top 10% — at or past this, it's performing like the bottom
Signals that don't pick winners (clicks, hook, hold) are listed as WATCHED, NOT JUDGED.
The ad-parts rules (from the gap reads) sit beside the numbers with their status: approved,
waiting on the owner, or none yet.
"""
import argparse, json, statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())

MIN_SPEND = 100      # below this an ad never really ran
JUDGED = [("cpa", "Cost per acquisition (CPA)", True, "spend ÷ purchases"),
          ("roas", "Return on ad spend", False, "sales value ÷ spend"),
          ("share", "Share of spend", False, "of everything its campaign spent while the ad ran, how much Meta gave this ad — "
                                             "is it scalable at that budget")]
# WHEN to judge (the owner, 2 Oct: "At what point do we need to assess …?"). Measured in spend, as a
# multiple of the brand's GOOD CPA, so it holds at any budget. From replaying every ad launched in the
# data window: how often a read at that point matched where the ad ended (top 10% or not).
CHECKPOINTS = [
    {"name": "First read", "times_good_cpa": 3, "judge": ["cpa", "roas"],
     "what": "Early look. Over the cut line already: likely a loser. Not a final call."},
    {"name": "Decision", "times_good_cpa": 5, "judge": ["cpa", "roas"],
     "what": "Keep or cut on CPA and return."},
    {"name": "Scale check", "times_good_cpa": 10, "judge": ["share"],
     "what": "Is Meta giving it a real share of the campaign's spend? Share of spend is judged here, not earlier."},
]
# Per-brand lines live in the brand's own folder, not here: brands/<brand>/meta/standard-settings.json
# (shape: brands/_TEMPLATE/meta/standard-settings.json). Every brand's numbers come from replaying its
# own ads, so they are brand data. Keys: read_accuracy, kill, signs_of_life, avatars, parts, parts_note.
# WHAT BAD LOOKS LIKE — the kill lines (the owner, 2 Oct: "clear criteria for what bad looks like … so we
# can kill it so we don't waste any money"). Same two rules for every brand, the line set per brand from
# replaying every ad launched in the window: the most money saved while killing at most ~3% of ads that
# went on to the top 10%, and no top-1% ad. Brand B winners often look bad early and recover, so its
# decision line is looser.
# NO GOOD AD GETS KILLED (the owner, 2 Oct: "make sure that no good ones would actually be killed? If there's
# any question or confusion, then it should just be pulled up, and then we can train over time"). When a
# kill rule fires, the ad is killed only with NO sign of life; any sign of life pulls it up for the owner,
# with the reason, and his call is recorded so the lines can be retuned from it. Signs of life set from
# the past winners a kill rule would have hit — every one of them had at least one.


class _ByBrand:
    """One key of brands/<brand>/meta/standard-settings.json, read like the dict it replaced."""
    def __init__(self, key):
        self.key = key

    def get(self, brand, default=None):
        f = WS / "brands" / brand / "meta" / "standard-settings.json"
        try:
            v = json.loads(f.read_text()).get(self.key)
        except (OSError, ValueError):
            return default
        if v is None:
            return default
        if self.key == "read_accuracy":       # JSON keys are strings; the checkpoints ask with ints
            v = {(int(k) if str(k).isdigit() else k): ({int(a): b for a, b in x.items()} if isinstance(x, dict) else x)
                 for k, x in v.items()}
        return v


READ_ACCURACY = _ByBrand("read_accuracy")
KILL = _ByBrand("kill")
SIGNS_OF_LIFE = _ByBrand("signs_of_life")
WATCHED = ["Link click rate", "Hook rate (3-second views)", "25% hold"]
AVATARS = _ByBrand("avatars")
PARTS = _ByBrand("parts")
PARTS_NOTE = _ByBrand("parts_note")


def daily(brand):
    """Every ad's daily spend, sales and value, with its campaign — one warehouse query, no Meta calls."""
    import sys
    sys.path.insert(0, str(WS / "tools/copywriter/library"))
    sys.path.insert(0, str(HERE))
    import meta_copy as MC
    from brand import Brand
    acct = Brand(brand).account_id
    return MC.db_query(f"""select coalesce(json_agg(x),'[]') from (
        select ad_id, date, campaign_id, sum(spend) s, sum(purchases) p, sum(purchase_value) v
        from meta_ad_insights where account_id = '{acct}' group by ad_id, date, campaign_id) x""")


def measure(brand, min_spend=MIN_SPEND):
    """Per real asset: cost per sale, return on ad spend, and share of spend — the asset's spend over
    its campaign's whole spend on the days the asset ran (Meta's own vote, whatever the budget)."""
    tiers = json.loads(sorted((WS / "runs/media-buying" / brand / "tiers").glob("*/tiers.json"))[-1].read_text())
    rows = daily(brand)
    camp_day, by_ad = {}, {}
    for r in rows:
        k = (r["campaign_id"], r["date"])
        camp_day[k] = camp_day.get(k, 0.0) + float(r["s"] or 0)
        by_ad.setdefault(r["ad_id"], []).append(r)
    out = []
    for g in tiers["rows"]:
        if g["spend"] < min_spend:
            continue
        s = p = v = 0.0
        pairs = set()
        for a in g["ads"]:
            for r in by_ad.get(a["ad_id"], []):
                s += float(r["s"] or 0); p += float(r["p"] or 0); v += float(r["v"] or 0)
                if float(r["s"] or 0) > 0:
                    pairs.add((r["campaign_id"], r["date"]))
        camp = sum(camp_day[k] for k in pairs)
        out.append({"rank": g["rank"], "tier": g["tier"], "asset": g["asset"], "ad_name": g["ads"][0]["ad_name"],
                    "spend": round(s, 2), "purchases": p,
                    "cpa": round(s / p, 2) if p else None, "roas": round(v / s, 2) if s else None,
                    "share": round(100 * s / camp, 1) if camp else None})
    return tiers, out


def line(vals, low):
    """GOOD = the line 3 of 4 top-1% assets clear."""
    vals = sorted(v for v in vals if v is not None)
    if len(vals) < 4:
        return None
    q = st.quantiles(vals, n=4)
    return round(q[2] if low else q[0], 2)


def build(brand):
    tiers, rows = measure(brand)
    win = [r for r in rows if r["tier"] == "top-1"]
    rest = [r for r in rows if r["tier"] == "under-10"]
    others = [r for r in rows if r["tier"] != "top-1"]
    out = {"brand": brand, "measured": "over each ad's life, ads with at least $%d spent" % MIN_SPEND,
           "from": {"window": tiers["window"], "assets": len(rows), "winners": len(win), "rest": len(rest)},
           "approved": {"by": "the owner", "on": "2026-10-02", "said": "We have this, and this is good."},
           "avatars": AVATARS.get(brand, []), "judged": [], "watched": [],
           "parts": PARTS.get(brand, []), "parts_note": PARTS_NOTE.get(brand, "")}
    for k, label, low, means in JUDGED:
        good = line([r[k] for r in win], low)
        pace = round(st.median([r[k] for r in win if r[k] is not None]), 2)
        # CUT = the typical ad outside the top 10%; an ad that spent and sold nothing counts at the bad end
        bad = float("inf") if low else 0.0
        cut = st.median([r[k] if r[k] is not None else bad for r in rest])
        cut = round(cut, 2) if cut != float("inf") else None
        beats = lambda x: x is not None and (x <= good if low else x >= good)
        # an ad with spend and no sales has no cost per sale: it fails that line
        o = [r for r in others if k != "cpa" or r["purchases"] or r["spend"] >= MIN_SPEND]
        out["judged"].append({"signal": k, "label": label, "means": means, "lower_is_better": low,
                              "pace": pace, "good": good, "cut": cut,
                              "winners_at_good": round(100 * sum(beats(r[k]) for r in win) / len(win)),
                              "others_at_good": round(100 * sum(beats(r[k]) for r in o) / len(o))})
    out["watched"] = [{"label": l} for l in WATCHED]
    cpa_good = next(r["good"] for r in out["judged"] if r["signal"] == "cpa")
    acc = READ_ACCURACY.get(brand, {})
    out["checkpoints"] = [dict(c, spend=round(c["times_good_cpa"] * cpa_good), right_pct=acc.get(c["times_good_cpa"]),
                               winner_days=acc.get("winner_days", {}).get(c["times_good_cpa"])) for c in CHECKPOINTS]
    out["base_rate_pct"] = acc.get("base")
    k = KILL.get(brand)
    if k:
        out["kill"] = {"rules": [
            {"when": "by 2× good CPA", "spend": round(2 * cpa_good), "kill_if": "no sale yet"},
            {"when": "at 5× good CPA (the decision)", "spend": round(5 * cpa_good),
             "kill_if": f"CPA over {k['decision_cpa_x']}× good", "cpa_over": round(k["decision_cpa_x"] * cpa_good)}],
            "stats": k["stats"]}
        life = SIGNS_OF_LIFE.get(brand)
        if life:
            names = {"share": "Share of spend ≥ {n}%", "atc": "{n}+ add to carts", "ic": "{n}+ checkouts started",
                     "ctr": "Link click rate ≥ {n}%"}
            out["kill"]["signs_of_life"] = [names[s].format(n=n) for s, n, _ in life["rules"]]
            out["kill"]["history"] = life["history"]
            out["kill"]["your_calls"] = ("Every pulled-up ad gets your call (kill · keep · give it more) and a reason. "
                                         "The calls are kept and the lines are retuned from them, shown to you first.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    d = build(a.brand)
    p = WS / "runs/media-buying" / a.brand / "standard.json"
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print(f"{a.brand}: judged " + ", ".join(f"{r['label']} good {r['good']} (pace {r['pace']}, cut {r['cut']})" for r in d["judged"])
          + " · watched " + ", ".join(r["label"] for r in d["watched"]))


if __name__ == "__main__":
    main()
