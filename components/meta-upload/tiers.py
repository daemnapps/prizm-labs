#!/usr/bin/env python3
"""tiers — every real asset a brand ran, ranked: top 1% · top 5% · top 10% · under top 10%.

    tiers.py --brand brand-b                  rank from the warehouse, write runs/media-buying/<brand>/tiers/<date>/
    tiers.py --brand brand-b --by spend       rank by spend instead of purchases

the owner, 2 Oct 2026: "rank the top 10% of whatever it is that we have, and clearly filter for
that … the top 5% and the top 1%, we can just see those … Everything that is not top 10%
should still be documented as just being under top 10%." The goal: "create 1% top ads all
the time."

Read-only, from our warehouse's nightly copy of Meta (meta_ad_insights, meta_ads) — no Meta
calls. A real asset is one video or image: every ad that ran it is folded into one row and
its numbers added up. A flexible ad's set of videos/images is one asset (its sales can't be
split by video here). An ad with no media on file stands alone. Ranked by purchases driven (default) — scale and selling in one number —
with spend, CPA, ROAS, the ads, the texts it ran with and a link to the post beside it.
Ties at a cut line go to the higher tier.
"""
import argparse, json, math, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WS / "tools/copywriter/library"))

TIERS = (("top-1", 0.01), ("top-5", 0.05), ("top-10", 0.10))
LABEL = {"top-1": "Top 1%", "top-5": "Top 2–5%", "top-10": "Top 6–10%", "under-10": "Under top 10%"}


def out_dir(brand, day=None):
    return WS / "runs" / "media-buying" / brand / "tiers" / (day or date.today().isoformat())


def read(brand):
    """Every ad of the brand's account with its totals, words and media — one warehouse query."""
    import meta_copy as MC
    from brand import Brand
    acct = Brand(brand).account_id
    rows = MC.db_query(f"""select coalesce(json_agg(x), '[]') from (
        select i.ad_id, max(i.ad_name) ad_name, sum(i.spend) spend, sum(i.purchases) purchases,
               sum(i.purchase_value) purchase_value, sum(i.impressions) impressions, sum(i.link_clicks) link_clicks,
               min(i.date) first_day, max(i.date) last_day, max(i.campaign_name) campaign, max(i.adset_name) adset,
               (select a.raw->'creative' from meta_ads a where a.ad_id = i.ad_id) creative,
               (select a.instagram_permalink_url from meta_ads a where a.ad_id = i.ad_id) instagram,
               (select a.landing_page_url from meta_ads a where a.ad_id = i.ad_id) landing_page
        from meta_ad_insights i where i.account_id = '{acct}' group by i.ad_id) x""")
    ads = []
    for r in rows:
        w = MC.words_of(r.get("creative"))
        ads.append({"ad_id": r["ad_id"], "ad_name": r["ad_name"], "campaign": r["campaign"], "adset": r["adset"],
                    "spend": float(r["spend"] or 0), "purchases": float(r["purchases"] or 0),
                    "value": float(r["purchase_value"] or 0), "impressions": int(r["impressions"] or 0),
                    "link_clicks": int(r["link_clicks"] or 0), "first_day": r["first_day"], "last_day": r["last_day"],
                    "instagram": r["instagram"], "landing_page": r["landing_page"], **w})
    return ads


def assets(ads):
    """One row per real asset (video or image); an ad with no media on file is its own row."""
    out = {}
    for a in ads:
        media = sorted(a.get("media") or [])
        # one video or image is the asset; a flexible ad's set of them is one asset (its sales
        # can't be split by video here, so counting them per video would count each sale twice)
        m = media[0] if len(media) == 1 else ("set:" + "+".join(media) if media else f"ad:{a['ad_id']}")
        for m in [m]:
            g = out.setdefault(m, {"asset": m, "kind": m.split(":")[0], "media": media, "ads": [], "spend": 0.0, "purchases": 0.0,
                                   "value": 0.0, "impressions": 0, "link_clicks": 0, "primary": {}, "headlines": {},
                                   "first_day": a["first_day"], "last_day": a["last_day"], "instagram": None})
            g["ads"].append({"ad_id": a["ad_id"], "ad_name": a["ad_name"], "spend": round(a["spend"], 2),
                             "purchases": a["purchases"], "campaign": a["campaign"], "adset": a["adset"]})
            for k in ("spend", "purchases", "value", "impressions", "link_clicks"):
                g[k] += a[k]
            for slot in ("primary", "headlines"):
                for t in a.get(slot) or []:
                    g[slot].setdefault(" ".join(t.lower().split()), t)
            g["first_day"] = min(g["first_day"], a["first_day"])
            g["last_day"] = max(g["last_day"], a["last_day"])
            g["instagram"] = g["instagram"] or a.get("instagram")
    rows = []
    for g in out.values():
        g["primary"], g["headlines"] = list(g["primary"].values()), list(g["headlines"].values())
        g["spend"], g["value"] = round(g["spend"], 2), round(g["value"], 2)
        g["cpa"] = round(g["spend"] / g["purchases"], 2) if g["purchases"] else None
        g["roas"] = round(g["value"] / g["spend"], 2) if g["spend"] else None
        g["ctr"] = round(100 * g["link_clicks"] / g["impressions"], 2) if g["impressions"] else None
        rows.append(g)
    return rows


def rank(rows, by="purchases"):
    """Rank and tier. Cut lines are counts (ceil), so a brand with few assets still has a top 1%."""
    rows = sorted(rows, key=lambda g: (-(g.get(by) or 0), -(g.get("spend") or 0)))
    n = len(rows)
    cuts = [(name, max(1, math.ceil(n * share))) for name, share in TIERS]
    for i, g in enumerate(rows):
        g["rank"] = i + 1
        g["tier"] = next((name for name, c in cuts if i < c), "under-10")
    # ties at a cut line go to the higher tier
    for name, c in cuts:
        if 0 < c < n:
            line = rows[c - 1].get(by) or 0
            for g in rows[c:]:
                if (g.get(by) or 0) == line and line > 0:
                    g["tier"] = rows[c - 1]["tier"]
    return rows, dict(cuts)


def summary(rows):
    s = {}
    for t in ("top-1", "top-5", "top-10", "under-10"):
        xs = [g for g in rows if g["tier"] == t]
        sp, pu = sum(g["spend"] for g in xs), sum(g["purchases"] for g in xs)
        s[t] = {"assets": len(xs), "spend": round(sp, 2), "purchases": pu, "cpa": round(sp / pu, 2) if pu else None}
    tot_sp, tot_pu = sum(g["spend"] for g in rows), sum(g["purchases"] for g in rows)
    for t in s:
        s[t]["share_of_spend"] = round(100 * s[t]["spend"] / tot_sp, 1) if tot_sp else None
        s[t]["share_of_purchases"] = round(100 * s[t]["purchases"] / tot_pu, 1) if tot_pu else None
    return s


def run(brand, by="purchases", say=print):
    ads = read(brand)
    rows, cuts = rank(assets(ads), by)
    d = out_dir(brand)
    d.mkdir(parents=True, exist_ok=True)
    window = (min(a["first_day"] for a in ads), max(a["last_day"] for a in ads)) if ads else (None, None)
    doc = {"brand": brand, "made": date.today().isoformat(), "ranked_by": by,
           "source": "warehouse (meta_ad_insights, meta_ads) — no Meta calls",
           "window": {"from": window[0], "to": window[1]}, "ads": len(ads), "assets": len(rows),
           "cut_counts": cuts, "summary": summary(rows), "rows": rows}
    (d / "tiers.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    s = doc["summary"]
    say(f"{brand}: {len(ads)} ads → {len(rows)} real assets, {window[0]}..{window[1]} · " + " · ".join(
        f"{LABEL[t]} {s[t]['assets']} ({s[t]['share_of_purchases']}% of purchases)" for t in s))
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--by", default="purchases", choices=["purchases", "spend", "value"])
    a = ap.parse_args()
    run(a.brand, a.by)


if __name__ == "__main__":
    main()
