#!/usr/bin/env python3
"""ad_filter — every live ad through the brand's standard: scale · good · watch · too early · pulled up · cut · kill.

    ad_filter.py --brand brand-b               writes runs/media-buying/<brand>/filter/<date>/verdicts.json + FILTER.md
    ad_filter.py --brand brand-b --live-days 3 an ad is live when it spent in the last N days of the data (default 3)

the owner, 2 Oct 2026: "build the filter" — so that "every time we do a pull on our ad metrics, we can run through
this filter and be very clear about what is going on", and "if there's any question or confusion, then it
should just be pulled up".

Reads the brand's approved standard (standard.py → runs/media-buying/<brand>/standard.json) and our warehouse's
copy of Meta (meta_ad_insights) — no Meta calls, and it changes nothing in Meta. Per live ad, over its life so
far: spend, purchases, CPA, return on ad spend, share of spend (its spend ÷ its campaign's spend on the days it
ran), add to carts, checkouts started, link click rate. Where it stands is spend as a multiple of the brand's
GOOD CPA:

  under 2×        TOO EARLY      not enough spend to judge
  kill rule fires KILL           no sale by 2×, or CPA over the brand's kill line at 5× — and no sign of life
                  PULLED UP      the same, but with a sign of life (share, carts/checkouts, click rate) — the owner's call
  3× to 5×        GOOD / WATCH   first read on CPA and return
  5× and over     GOOD / CUT     the decision: past the cut line on CPA or return → CUT, or PULLED UP if it shows life
  10× and over    SCALE          good on CPA and return AND Meta gives it a good share of spend
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WS / "tools/copywriter/library"))

ORDER = ["pull up", "kill", "cut", "scale", "good", "watch", "too early"]
LABEL = {"pull up": "Pulled up for you", "kill": "Kill", "cut": "Cut", "scale": "Scale", "good": "Good",
         "watch": "Watch", "too early": "Too early"}


def standard(brand):
    return json.loads((WS / "runs/media-buying" / brand / "standard.json").read_text())


def rows(brand):
    import meta_copy as MC
    from brand import Brand
    acct = Brand(brand).account_id
    act = lambda t: (f"coalesce((select sum((e->>'value')::numeric) from jsonb_array_elements(actions) e "
                     f"where e->>'action_type'='{t}'),0)")
    return MC.db_query(f"""select coalesce(json_agg(x),'[]') from (
        select ad_id, max(ad_name) ad_name, date, campaign_id, max(campaign_name) campaign, max(adset_name) adset,
               sum(spend) s, sum(purchases) p, sum(purchase_value) v, sum(impressions) i, sum(link_clicks) lc,
               sum({act('add_to_cart')}) atc, sum({act('initiate_checkout')}) ic
        from meta_ad_insights where account_id = '{acct}' group by ad_id, date, campaign_id) x""")


def life_signs(brand, a):
    """The signs of life this ad shows, in plain words (standard.py SIGNS_OF_LIFE)."""
    import standard as STD
    rules = STD.SIGNS_OF_LIFE.get(brand, {}).get("rules", [])
    out = []
    for k, n, words in rules:
        v = a.get(k) or 0
        if v >= n:
            out.append(words.format(v=round(v, 1) if isinstance(v, float) and v % 1 else int(v)))
    return out


def judge(brand, a, std):
    g = {r["signal"]: r for r in std["judged"]}
    good_cpa, cut_cpa = g["cpa"]["good"], g["cpa"]["cut"]
    good_roas, cut_roas = g["roas"]["good"], g["roas"]["cut"]
    good_share = g["share"]["good"]
    kill_x = next((r for r in std["kill"]["rules"] if r.get("cpa_over")), {}).get("cpa_over")
    x = a["spend"] / good_cpa
    a["times_good_cpa"] = round(x, 1)
    cpa, roas, share = a["cpa"], a["roas"], a["share"]
    life = life_signs(brand, a)
    a["signs_of_life"] = life
    money = lambda v: f"${v:,.0f}"

    def pull_or(kind, why):
        if life:
            return "pull up", f"{why} — but {', '.join(life)}"
        return kind, why

    if x >= 2 and not a["purchases"]:
        return pull_or("kill", f"no sale after {money(a['spend'])} ({x:.1f}× good CPA)")
    if x >= 5 and cpa and kill_x and cpa > kill_x:
        return pull_or("kill", f"CPA {money(cpa)}, over the kill line {money(kill_x)}")
    if x < 2:
        return "too early", f"{money(a['spend'])} spent — judged from {money(2 * good_cpa)}"
    ok = cpa is not None and cpa <= good_cpa and (roas or 0) >= good_roas
    bad = (cpa is None or (cut_cpa and cpa >= cut_cpa)) or (roas or 0) <= cut_roas
    if x >= 10 and ok:
        if share is not None and share >= good_share:
            return "scale", f"CPA {money(cpa)}, return {roas:.2f}×, {share:.1f}% of its campaign's spend"
        return "good", f"CPA {money(cpa)}, return {roas:.2f}× — but only {share or 0:.1f}% of its campaign's spend"
    if ok:
        return "good", f"CPA {money(cpa)}, return {roas:.2f}×"
    if x >= 5 and bad:
        return pull_or("cut", f"CPA {money(cpa) if cpa else '—'}, return {(roas or 0):.2f}× — past the cut line at the decision")
    return "watch", f"CPA {money(cpa) if cpa else '—'}, return {(roas or 0):.2f}× — {'first read' if x < 5 else 'between good and cut'}"


def leaning(a, std):
    """The first read (from 2× good CPA, before the 5× decision): already past the cut line on CPA or return —
    'likely a loser', per the standard. Not a kill; it shows where the final call happens."""
    g = {r["signal"]: r for r in std["judged"]}
    good_cpa, cut_cpa, cut_roas = g["cpa"]["good"], g["cpa"]["cut"], g["roas"]["cut"]
    for span, s, p, cpa, roas in (("", a["spend"], a["purchases"], a["cpa"], a["roas"]),
                                  ("this week: ", (a.get("week") or {}).get("spend", 0), (a.get("week") or {}).get("purchases", 0),
                                   (a.get("week") or {}).get("cpa"), (a.get("week") or {}).get("roas"))):
        x = (s or 0) / good_cpa
        if 2 <= x < 5 and p and ((cut_cpa and cpa and cpa >= cut_cpa) or (roas or 0) <= cut_roas):
            return (f"{span}CPA ${cpa:,.0f}, return {(roas or 0):.2f}× on ${s:,.0f} — past the cut line already, "
                    f"likely a loser; the call is at ${5 * good_cpa:,.0f}")
    return None


def week_verdict(brand, a, std):
    """The last 7 days on their own: no sale from 2× good CPA, or CPA past the kill line from 5×, or past the cut
    line from 5× → kill / cut, unless a sign of life pulls it up. None when the week says nothing new."""
    g = {r["signal"]: r for r in std["judged"]}
    good_cpa, cut_cpa, cut_roas = g["cpa"]["good"], g["cpa"]["cut"], g["roas"]["cut"]
    kill_x = next((r for r in std["kill"]["rules"] if r.get("cpa_over")), {}).get("cpa_over")
    w = a["week"]
    x = w["spend"] / good_cpa
    life = a.get("signs_of_life") or []
    m = lambda v: f"${v:,.0f}"
    tail = f" — but {', '.join(life)}" if life else ""
    if x >= 2 and not w["purchases"]:
        return ("pull up" if life else "kill"), f"this week: no sale on {m(w['spend'])}" + tail
    if x >= 5 and w["cpa"] and kill_x and w["cpa"] > kill_x:
        return ("pull up" if life else "kill"), f"this week: CPA {m(w['cpa'])} on {m(w['spend'])}, over the kill line {m(kill_x)}" + tail
    if x >= 5 and ((cut_cpa and w["cpa"] and w["cpa"] >= cut_cpa) or (w["roas"] or 0) <= cut_roas):
        return ("pull up" if life else "cut"), f"this week: CPA {m(w['cpa']) if w['cpa'] else '—'}, return {(w['roas'] or 0):.2f}× on {m(w['spend'])}, past the cut line" + tail
    return None


def run(brand, live_days=3):
    std = standard(brand)
    R = rows(brand)
    camp, by_ad = {}, {}
    for r in R:
        k = (r["campaign_id"], r["date"])
        camp[k] = camp.get(k, 0.0) + float(r["s"] or 0)
        by_ad.setdefault(r["ad_id"], []).append(r)
    last = max(r["date"] for r in R)
    spent_days = [r["date"] for r in R if float(r["s"] or 0) >= 1]
    last_spend = max(spent_days) if spent_days else None
    since = (date.fromisoformat(last) - timedelta(days=live_days - 1)).isoformat()
    ads = []
    for aid, rs in by_ad.items():
        if not any(r["date"] >= since and float(r["s"] or 0) > 0 for r in rs):
            continue
        t = {k: sum(float(r[k] or 0) for r in rs) for k in ("s", "p", "v", "i", "lc", "atc", "ic")}
        pairs = {(r["campaign_id"], r["date"]) for r in rs if float(r["s"] or 0) > 0}
        c = sum(camp[k] for k in pairs)
        a = {"ad_id": aid, "ad_name": rs[0]["ad_name"], "campaign": rs[0]["campaign"], "adset": rs[0]["adset"],
             "first_day": min(r["date"] for r in rs), "spend": round(t["s"], 2), "purchases": t["p"],
             "cpa": round(t["s"] / t["p"], 2) if t["p"] else None, "roas": round(t["v"] / t["s"], 2) if t["s"] else None,
             "share": round(100 * t["s"] / c, 1) if c else None, "atc": t["atc"], "ic": t["ic"],
             "ctr": round(100 * t["lc"] / t["i"], 2) if t["i"] else None,
             "last_3_days_spend": round(sum(float(r["s"] or 0) for r in rs if r["date"] >= since), 2)}
        # THIS WEEK (the owner, 2 Oct: "ads that have gotten significant spend through a new test that likely need to get
        # killed" — and efficiency "way down" in the last 7 days). Judged on the last 7 days of the data alone, from
        # 2× good CPA spent this week; it can only make a verdict harsher, never kinder, and signs of life still pull up.
        wk = (date.fromisoformat(last) - timedelta(days=6)).isoformat()
        w = {k: sum(float(r[k] or 0) for r in rs if r["date"] >= wk) for k in ("s", "p", "v")}
        a["week"] = {"spend": round(w["s"], 2), "purchases": w["p"], "cpa": round(w["s"] / w["p"], 2) if w["p"] else None,
                     "roas": round(w["v"] / w["s"], 2) if w["s"] else None}
        a["verdict"], a["why"] = judge(brand, a, std)
        lean = leaning(a, std)
        if lean and a["verdict"] == "watch":
            a["leaning"], a["why"] = "cut", lean
        wv = week_verdict(brand, a, std)
        if wv and ORDER.index(wv[0]) < ORDER.index(a["verdict"]) and a["verdict"] in ("scale", "good", "watch", "too early"):
            a["lifetime_verdict"], a["lifetime_why"] = a["verdict"], a["why"]
            a["verdict"], a["why"] = wv
        ads.append(a)
    ads.sort(key=lambda a: (ORDER.index(a["verdict"]), -a["spend"]))
    counts = {v: sum(1 for a in ads if a["verdict"] == v) for v in ORDER}
    doc = {"brand": brand, "data_through": last, "last_spend_day": last_spend, "live": f"spent in the last {live_days} days of the data (since {since})",
           "standard": str((WS / "runs/media-buying" / brand / "standard.json").relative_to(WS)),
           "counts": counts, "ads": ads, "made": date.today().isoformat(),
           "note": "Nothing here changes Meta. Kill and cut are a list for the owner; pulled-up ads need his call."}
    out = WS / "runs/media-buying" / brand / "filter" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    (out / "verdicts.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    L = [f"# The filter — {brand}, data through {last}", "", " · ".join(f"{LABEL[v]} {n}" for v, n in counts.items()), ""]
    for v in ORDER:
        xs = [a for a in ads if a["verdict"] == v]
        if xs:
            L += [f"## {LABEL[v]} ({len(xs)})", ""] + [f"- {a['ad_name']} — {a['why']} (spent ${a['spend']:,.0f})" for a in xs] + [""]
    (out / "FILTER.md").write_text("\n".join(L))
    print(f"{brand} (data through {last}): " + " · ".join(f"{LABEL[v]} {n}" for v, n in counts.items() if n))
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--live-days", type=int, default=3)
    a = ap.parse_args()
    run(a.brand, a.live_days)


if __name__ == "__main__":
    main()
