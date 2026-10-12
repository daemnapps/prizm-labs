#!/usr/bin/env python3
"""business — the ad account next to the store: each brand's spend and CPA over time, its storefront and funnel
sales, and (where orders carry the ad) store orders and sales per ad and per brief.

    business.py --brand brand-a        writes runs/media-buying/<brand>/business/<date>/business.json

the owner, 2 Oct 2026: "link back the ads to their briefs … per brand have a nice high level view of the spend and
CPAs … a separate tab for numbers from their storefronts and funnels so we have a unified look at the impact of
the ad on the overall business as well because meta just shows the platform metrics … gauge impact and
percentage of spend across the entire business". No profit numbers ("i don't need a profit table").

All from our warehouse — no Meta, Shopify or Next Commerce calls:
  meta_ad_insights        spend, Meta-reported purchases and value, per ad per day
  shopify_orders          Brand B store (brand-b.example); sales = total − tax − refunds, test and cancelled out.
                          Almost none of its orders carry the ad, so Brand B store numbers are whole-business only.
  nextcommerce_orders     Brand A funnels; sales = total excl. tax − refunds, test out. Orders carry the ad that
                          sold them (attribution.utm_content = Meta ad id), so store orders tie to ads and briefs.
Briefs: brief_for(brand, ad_name) reads the ad's name (the short name, a brief-NNNN, or an old pNNN code) and
finds the brief in the register (components/naming). Ads made before briefs existed say so.
"""
import argparse, json, re, sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WS / "tools/copywriter/library"))
sys.path.insert(0, str(WS / "components/naming"))
import names as N  # noqa: E402

DAYS = 90
TOK = [re.compile(r"(brief-\d{4})", re.I), re.compile(r"\bbrief[ _-]?p?(\d{3,4})\b", re.I),
       re.compile(r"(?:^|[_\-\s])p(\d{3})(?=[_\-\s]|$)", re.I), re.compile(r"\b(dxs-?\d{2})\b", re.I)]
# The store each brand sells through is the brand's own setting: brands/<brand>/meta/account.json ->
# "store": {"kind": "shopify" | "nextcommerce", "name": "<shown on the page>", "label": "<account_label>"}
# (shape: brands/_TEMPLATE/meta/account.json). The SQL per kind stays here.
STORE_KINDS = {
    "shopify": {"per_ad": False, "sql": """
        select created_at::date d, count(*) n, sum(total_price - total_tax - coalesce(total_refunded,0)) s, null::text ad
        from shopify_orders where created_at >= '{since}' and coalesce(is_test,false) = false and cancelled_at is null
        group by 1"""},
    "nextcommerce": {"per_ad": True, "sql": """
        select created_at::date d, count(*) n,
               sum(coalesce(report_total_excl_tax, total_excl_tax) - coalesce(refunds_total,0)) s,
               case when raw->'attribution'->>'utm_content' ~ '^[0-9]{{10,}}$' then raw->'attribution'->>'utm_content' end ad
        from nextcommerce_orders where created_at >= '{since}' and coalesce(is_test,false) = false
          and account_label = '{label}'
          and coalesce(lower(status),'') not in ('canceled','cancelled')
        group by 1, 4"""},
}


def store_of(brand):
    """{name, per_ad, sql} for this brand's store, from brands/<brand>/meta/account.json -> store."""
    acct = json.loads((WS / "brands" / brand / "meta" / "account.json").read_text())
    st = acct.get("store") or {}
    kind = STORE_KINDS[st.get("kind", "shopify")]
    return {"name": st.get("name", brand), "per_ad": kind["per_ad"],
            "sql": kind["sql"].replace("{label}", st.get("label", brand))}


class _Stores:
    def __getitem__(self, brand):
        return store_of(brand)


STORE = _Stores()


def q(sql):
    import meta_copy as MC
    return MC.db_query(f"select coalesce(json_agg(x),'[]') from ({sql}) x")


def brief_for(brand, ad_name):
    """{brief, title, product, angle, avatar} for an ad's name, or None (made before briefs, or not named to one)."""
    name = ad_name or ""
    first = re.split(r"\s+-\s+", name)[0]
    d = N.parse_any(first) or N.parse_any(first.split(" ")[0])
    prod = d.get("product") if d else None
    cands = []
    if d and d.get("brief_id") and d["brief_id"] != "none":
        cands.append(d["brief_id"])
    for rx in TOK:
        cands += [m.group(1) for m in rx.finditer(name)]
    for c in cands:
        try:
            hit = N.find_brief(brand, c, prod)
        except N.AmbiguousBrief:
            hit = None
        if hit:
            h = hit.get("header") or {}
            r = hit.get("register") or {}
            return {"brief": hit["brief"], "product": hit.get("product") or h.get("product"),
                    "title": h.get("title") or r.get("title") or r.get("concept") or "",
                    "angle": h.get("angle") or r.get("angle"), "avatar": h.get("avatar") or r.get("avatar"),
                    "format": h.get("format") or r.get("format"), "media": h.get("media") or h.get("type") or r.get("media"),
                    "concept": h.get("concept") or r.get("concept")}
    return None


def judge_brief(b, std):
    """A brief, all its ads together, through the brand's standard (standard.json): the same lines as an ad."""
    g = {r["signal"]: r for r in std["judged"]}
    good_cpa, cut_cpa, good_roas, cut_roas = g["cpa"]["good"], g["cpa"]["cut"], g["roas"]["good"], g["roas"]["cut"]
    kill = next((r.get("cpa_over") for r in std["kill"]["rules"] if r.get("cpa_over")), None)
    x = b["spend"] / good_cpa
    cpa, roas = b["meta_cpa"], b["meta_roas"] or 0
    m = lambda v: f"${v:,.0f}"
    if x < 2:
        return "too early", f"{m(b['spend'])} spent across {b['ads']} ad{'s' if b['ads'] != 1 else ''} — judged from {m(2 * good_cpa)}"
    if not b["meta_buys"]:
        return "not working", f"no sale after {m(b['spend'])}"
    if x >= 5 and kill and cpa > kill:
        return "not working", f"CPA {m(cpa)}, over the kill line {m(kill)}"
    if cpa <= good_cpa and roas >= good_roas:
        return "working", f"CPA {m(cpa)}, return {roas:.2f}×"
    if x >= 5 and ((cut_cpa and cpa >= cut_cpa) or roas <= cut_roas):
        return "not working", f"CPA {m(cpa)}, return {roas:.2f}× — past the cut line"
    return "watch", f"CPA {m(cpa)}, return {roas:.2f}× — between good and cut"


def by_part(briefs, part):
    """Spend, CPA and verdict mix per angle / avatar / format, from the briefs that carry it."""
    out = {}
    for b in briefs:
        if b["brief"] == "made before briefs":
            continue
        k = b.get(part) or "not set"
        x = out.setdefault(k, dict(value=k, briefs=0, spend=0.0, meta_buys=0.0, meta_value=0.0, verdicts={}))
        x["briefs"] += 1; x["spend"] += b["spend"]; x["meta_buys"] += b["meta_buys"]; x["meta_value"] += b["meta_value"]
        x["verdicts"][b["verdict"]] = x["verdicts"].get(b["verdict"], 0) + 1
    for x in out.values():
        x["spend"] = round(x["spend"], 2)
        x["meta_cpa"] = round(x["spend"] / x["meta_buys"], 2) if x["meta_buys"] else None
        x["meta_roas"] = round(x["meta_value"] / x["spend"], 2) if x["spend"] else None
    return sorted(out.values(), key=lambda x: -x["spend"])


def run(brand, days=DAYS):
    from brand import Brand
    std = json.loads((WS / "runs/media-buying" / brand / "standard.json").read_text())
    acct = Brand(brand).account_id
    since = (date.today() - timedelta(days=days)).isoformat()
    meta = q(f"""select ad_id, max(ad_name) ad_name, date d, sum(spend) s, sum(purchases) p, sum(purchase_value) v
                 from meta_ad_insights where account_id = '{acct}' and date >= '{since}' group by ad_id, date""")
    store = q(STORE[brand]["sql"].format(since=since))
    daily = {}
    for r in meta:
        x = daily.setdefault(r["d"], dict(spend=0.0, meta_buys=0.0, meta_value=0.0, orders=0, sales=0.0, ad_orders=0, ad_sales=0.0))
        x["spend"] += float(r["s"] or 0); x["meta_buys"] += float(r["p"] or 0); x["meta_value"] += float(r["v"] or 0)
    per_ad_store = {}
    for r in store:
        x = daily.setdefault(r["d"], dict(spend=0.0, meta_buys=0.0, meta_value=0.0, orders=0, sales=0.0, ad_orders=0, ad_sales=0.0))
        x["orders"] += int(r["n"]); x["sales"] += float(r["s"] or 0)
        if r.get("ad"):
            x["ad_orders"] += int(r["n"]); x["ad_sales"] += float(r["s"] or 0)
            a = per_ad_store.setdefault(r["ad"], [0, 0.0]); a[0] += int(r["n"]); a[1] += float(r["s"] or 0)
    days_out = [dict(date=d, **{k: round(v, 2) for k, v in x.items()}) for d, x in sorted(daily.items())]

    ads = {}
    for r in meta:
        a = ads.setdefault(r["ad_id"], dict(ad_id=r["ad_id"], ad_name=r["ad_name"], spend=0.0, meta_buys=0.0, meta_value=0.0, first=r["d"]))
        a["spend"] += float(r["s"] or 0); a["meta_buys"] += float(r["p"] or 0); a["meta_value"] += float(r["v"] or 0)
        a["first"] = min(a["first"], r["d"])
    briefs = {}
    for a in ads.values():
        so = per_ad_store.get(a["ad_id"], [0, 0.0])
        a["store_orders"], a["store_sales"] = so[0], round(so[1], 2)
        a["brief"] = brief_for(brand, a["ad_name"])
        key = a["brief"]["brief"] if a["brief"] else "made before briefs"
        h = a["brief"] or {}
        b = briefs.setdefault(key, dict(brief=key, title=h.get("title", ""), product=h.get("product"), angle=h.get("angle"),
                                         avatar=h.get("avatar"), format=h.get("format"), media=h.get("media"), concept=h.get("concept"),
                                         ads=0, spend=0.0, meta_buys=0.0, meta_value=0.0, store_orders=0, store_sales=0.0))
        b["ads"] += 1; b["spend"] += a["spend"]; b["meta_buys"] += a["meta_buys"]; b["meta_value"] += a["meta_value"]
        b["store_orders"] += a["store_orders"]; b["store_sales"] += a["store_sales"]
    for b in briefs.values():
        b["spend"], b["store_sales"] = round(b["spend"], 2), round(b["store_sales"], 2)
        b["meta_cpa"] = round(b["spend"] / b["meta_buys"], 2) if b["meta_buys"] else None
        b["store_cpa"] = round(b["spend"] / b["store_orders"], 2) if b["store_orders"] else None
        b["store_roas"] = round(b["store_sales"] / b["spend"], 2) if b["spend"] else None
        b["meta_roas"] = round(b["meta_value"] / b["spend"], 2) if b["spend"] else None
        if b["brief"] != "made before briefs":
            b["verdict"], b["why"] = judge_brief(b, std)

    def window(n):
        cut = (date.today() - timedelta(days=n)).isoformat()
        xs = [x for x in days_out if x["date"] >= cut]
        s = {k: round(sum(x[k] for x in xs), 2) for k in ("spend", "meta_buys", "meta_value", "orders", "sales", "ad_orders", "ad_sales")}
        s["meta_cpa"] = round(s["spend"] / s["meta_buys"], 2) if s["meta_buys"] else None
        s["meta_roas"] = round(s["meta_value"] / s["spend"], 2) if s["spend"] else None
        s["store_cpa"] = round(s["spend"] / s["orders"], 2) if s["orders"] else None        # every store order, ad or not
        s["spend_pct_of_sales"] = round(100 * s["spend"] / s["sales"], 1) if s["sales"] else None
        s["mer"] = round(s["sales"] / s["spend"], 2) if s["spend"] else None                    # store revenue ÷ ad spend
        s["ad_share_of_orders"] = round(100 * s["ad_orders"] / s["orders"], 1) if s["orders"] else None
        return s

    good_cpa = next(r["good"] for r in std["judged"] if r["signal"] == "cpa")
    cut30 = (date.today() - timedelta(days=30)).isoformat()
    new = [a for a in ads.values() if a["first"] >= cut30]
    judged = [a for a in new if a["spend"] >= 2 * good_cpa]
    volume = {"launched_30d": len(new), "reached_a_verdict": len(judged),
              "spend_30d_new": round(sum(a["spend"] for a in new), 2),
              "spend_on_unjudged": round(sum(a["spend"] for a in new if a["spend"] < 2 * good_cpa), 2),
              "judged_from": round(2 * good_cpa)}
    bl = sorted(briefs.values(), key=lambda b: (b["brief"] == "made before briefs", -b["spend"]))
    doc = {"brand": brand, "made": date.today().isoformat(), "since": since, "store": STORE[brand]["name"],
           "volume": volume, "parts": {p_: by_part(bl, p_) for p_ in ("angle", "avatar", "format", "media")},
           "store_per_ad": STORE[brand]["per_ad"],
           "windows": {"7": window(7), "30": window(30), "90": window(days)}, "daily": days_out,
           "briefs": bl,
           "ads": {k: {"store_orders": v["store_orders"], "store_sales": v["store_sales"], "brief": v["brief"]}
                   for k, v in ads.items()}}
    out = WS / "runs/media-buying" / brand / "business" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    (out / "business.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    w = doc["windows"]["30"]
    linked = sum(1 for a in ads.values() if a["brief"])
    print(f"{brand}: last 30 days spend ${w['spend']:,.0f}, Meta CPA {w['meta_cpa']}, store orders {w['orders']}, "
          f"store sales ${w['sales']:,.0f}, spend = {w['spend_pct_of_sales']}% of sales, ad-tagged orders {w['ad_share_of_orders']}% · "
          f"{linked}/{len(ads)} ads linked to a brief · {len(briefs)} brief rows")
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--days", type=int, default=DAYS)
    a = ap.parse_args()
    run(a.brand, a.days)


if __name__ == "__main__":
    main()
