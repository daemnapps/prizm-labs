#!/usr/bin/env python3
"""signals — what good looks like, in numbers, per brand: the early signals every ad is judged on.

    signals.py --brand brand-b              writes runs/media-buying/<brand>/signals/<date>/signals.json + SIGNALS.md
    signals.py --brand brand-b --at 1000    the point every ad is measured at (default $__ of spend)

the owner, 2 Oct 2026: "establish what these signals actually are so that the machine knows what good
actually looks like, defined by specific KPIs … with the actual metrics that are coming back …
Our machine learns what good looks like, and all these learnings are retained in the system …
The media buyer and creative strategy agent are actually able to leverage this information."

The fair footing (the owner saw it on the Top 1% Plan page): every real asset is measured at the same
point, its first $AT of spend, so an ad Meta starved is judged on the same terms as one it scaled.
At that point, per asset: cost per sale, return on spend, link click rate, play rate, 25% hold,
days it took. Then three groups — the top 1% (tiers.py), the rest of the top 10%, everyone else —
and for every signal: GOOD — the line 3 of 4 winners clear; WATCH — the typical top-10% asset; BELOW — the
typical everyone-else, and how well it separates (share of winners at or better than GOOD vs share of everyone
else). A signal that does not separate is kept and marked so — knowing what does NOT predict a
winner is a learning too.

Read-only, from the warehouse (meta_ad_insights) — no Meta calls. The latest signals.json per brand
is the file the media buyer and the creative strategist read.
"""
import argparse, json, statistics as st, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WS / "tools/copywriter/library"))

# signal: (label, lower_is_better, what it says in plain words)
SIGNALS = {
    "cpa": ("Cost per sale", True, "what each sale cost by this point"),
    "roas": ("Return on spend", False, "sales value ÷ spend by this point"),
    "link_ctr": ("Link click rate", False, "link clicks ÷ impressions — the ad earned the click"),
    "hook_rate": ("Hook rate", False, "3-second video views ÷ impressions — the opening stopped the scroll"),
    "hold_25": ("25% hold", False, "3-second viewers who reached a quarter of the video (recorded from 2026 only)"),
    "days": ("Days to spend its first $__", True, "how fast Meta spent it — speed is Meta's own vote"),
}
SCALE = 5000          # an asset Meta took past this was scaled


def latest(brand, kind, name):
    runs = sorted((WS / "runs/media-buying" / brand / kind).glob(f"*/{name}"))
    return json.loads(runs[-1].read_text()) if runs else None


def daily(brand):
    import meta_copy as MC
    from brand import Brand
    acct = Brand(brand).account_id
    v = lambda c: f"coalesce((select sum((e->>'value')::numeric) from jsonb_array_elements({c}) e),0)"
    rows = MC.db_query(f"""select coalesce(json_agg(x),'[]') from (
        select ad_id, date, sum(spend) s, sum(purchases) p, sum(purchase_value) val, sum(impressions) i,
               sum(link_clicks) lc,
               sum((select sum((e->>'value')::numeric) from jsonb_array_elements(actions) e where e->>'action_type' = 'video_view')) v3,
               sum({v('video_p25_watched_actions')}) p25
        from meta_ad_insights where account_id = '{acct}' group by ad_id, date) x""")
    out = {}
    for r in rows:
        out.setdefault(r["ad_id"], []).append(r)
    return out


def at_point(asset, by_ad, at):
    """The asset's numbers summed over its ads, day by day, up to the day it passed $at."""
    days = {}
    for a in asset["ads"]:
        for r in by_ad.get(a["ad_id"], []):
            d = days.setdefault(r["date"], dict(s=0.0, p=0.0, val=0.0, i=0.0, lc=0.0, v3=0.0, p25=0.0))
            for k in d:
                d[k] += float(r.get(k) or 0)
    tot, n = dict(s=0.0, p=0.0, val=0.0, i=0.0, lc=0.0, v3=0.0, p25=0.0), 0
    for _, d in sorted(days.items()):
        n += 1
        for k in tot:
            tot[k] += d[k]
        if tot["s"] >= at:
            break
    if tot["s"] < at:
        return None
    div = lambda a, b, m=1: round(m * a / b, 2) if b else None
    return {"cpa": div(tot["s"], tot["p"]), "roas": div(tot["val"], tot["s"]), "link_ctr": div(tot["lc"], tot["i"], 100),
            "hook_rate": div(tot["v3"], tot["i"], 100) if tot["v3"] else None,
            "hold_25": div(tot["p25"], tot["v3"], 100) if tot["v3"] and tot["p25"] else None, "days": n,
            "spend": round(tot["s"]), "purchases": int(tot["p"])}


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 2) if xs else None


def build(brand, at=1000.0):
    tiers = latest(brand, "tiers", "tiers.json")
    by_ad = daily(brand)
    groups = {"winners": [], "top10": [], "rest": []}
    for g in tiers["rows"]:
        m = at_point(g, by_ad, at)
        if not m:
            continue
        row = {"rank": g["rank"], "asset": g["asset"], "tier": g["tier"], "ad_name": g["ads"][0]["ad_name"],
               "total_spend": g["spend"], "scaled": g["spend"] >= SCALE, **m}
        groups["winners" if g["tier"] == "top-1" else "top10" if g["tier"] in ("top-5", "top-10") else "rest"].append(row)
    sig = {}
    for k, (label, low, plain) in SIGNALS.items():
        wv = sorted(r[k] for r in groups["winners"] if r[k] is not None)
        if len(wv) < 4:
            continue
        # GOOD = the line 3 of 4 winners clear (their 75th percentile on the worse side)
        q = st.quantiles(wv, n=4)
        good = round(q[2] if low else q[0], 2)
        watch, below = (med([r[k] for r in groups[x]]) for x in ("top10", "rest"))
        beats = (lambda v: v is not None and (v <= good if low else v >= good))
        w = [r for r in groups["winners"] if r[k] is not None]
        o = [r for r in groups["top10"] + groups["rest"] if r[k] is not None]
        sw = round(100 * sum(beats(r[k]) for r in w) / len(w)) if w else None
        so = round(100 * sum(beats(r[k]) for r in o) / len(o)) if o else None
        gap = (sw - so) if sw is not None and so is not None else None
        sig[k] = {"label": label, "lower_is_better": low, "means": plain, "good": good, "watch": watch, "below": below,
                  "winners_hitting_good_pct": sw, "others_hitting_good_pct": so,
                  "separates": "strongly" if gap is not None and gap >= 35 else "somewhat" if gap is not None and gap >= 15
                  else "no"}
    wc = med([r["cpa"] for r in groups["winners"]])
    early_good = [r for r in groups["top10"] + groups["rest"] if r["cpa"] and wc and r["cpa"] <= wc and not r["scaled"]]
    return {"brand": brand, "made": date.today().isoformat(), "measured_at_spend": at,
            "source": "warehouse (meta_ad_insights) — no Meta calls", "window": tiers["window"],
            "assets_measured": {k: len(v) for k, v in groups.items()},
            "scaled_share": {k: round(100 * sum(r["scaled"] for r in v) / len(v)) if v else None for k, v in groups.items()},
            "signals": sig,
            "cut_too_early": sorted(early_good, key=lambda r: r["cpa"]),
            "assets": groups}


def md(d):
    at = f"${d['measured_at_spend']:,.0f}"
    L = [f"# What good looks like — {d['brand']}", "",
         f"Every real asset measured at its first {at} of spend (warehouse, {d['window']['from']} → {d['window']['to']}). "
         f"Winners = the top 1% ({d['assets_measured']['winners']} reached {at}); top 10% = the next tiers "
         f"({d['assets_measured']['top10']}); rest = everyone else that reached {at} ({d['assets_measured']['rest']}).", "",
         "| Signal | Good (3 of 4 winners clear it) | Watch (typical top 10%) | Below (typical rest) | Winners at Good | Others at Good | Separates |",
         "|---|---|---|---|---|---|---|"]
    for s in d["signals"].values():
        L.append(f"| {s['label']} | {s['good']} | {s['watch']} | {s['below']} | {s['winners_hitting_good_pct']}% | "
                 f"{s['others_hitting_good_pct']}% | {s['separates']} |")
    L += ["", f"Scaled past ${SCALE:,}: winners {d['scaled_share']['winners']}% · top 10% {d['scaled_share']['top10']}% · "
          f"rest {d['scaled_share']['rest']}%.", "",
          f"Cut too early? {len(d['cut_too_early'])} assets matched the typical winner's cost per sale at {at} and were never scaled:", ""]
    L += [f"- {r['ad_name']} — ${r['cpa']} per sale at {at} ({r['purchases']} sales), stopped at ${r['total_spend']:,.0f}"
          for r in d["cut_too_early"]]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--at", type=float, default=1000.0)
    a = ap.parse_args()
    d = build(a.brand, a.at)
    out = WS / "runs/media-buying" / a.brand / "signals" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    (out / "signals.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    (out / "SIGNALS.md").write_text(md(d))
    print(f"{a.brand}: " + " · ".join(f"{s['label']} good {s['good']} ({s['separates']})" for s in d["signals"].values())
          + f" · cut too early {len(d['cut_too_early'])}")


if __name__ == "__main__":
    main()
