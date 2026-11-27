#!/usr/bin/env python3
"""analyze.py — "Analyze ads": every live ad in a brand's account, judged against its own offer's margin,
with the store's blended numbers beside it. Flags only; owner makes every call.

    python3 analyze.py brand_b                 # through yesterday (the warehouse's last full day)
    python3 analyze.py brand_b --asof 2026-10-03

Reads only the warehouse (Meta's synced copy + the store's order P&L) — no Meta API call.
Lines come from runs/media-buying/<brand>/desk.json; each ad is judged in multiples of its
break-even CPA = the store's real contribution per order on that ad's funnel (upsells in),
falling back to the offer's first-order break-even when the funnel has too few orders.

A desk whose desk.json carries `rule` (type meta_cpa_windows) is judged by that rule instead: Meta CPA over
3, 7 and 14 days against one line, with a prospecting keep (share of spend and daily frequency). See judge_windows.

Writes runs/media-buying/<brand>/<asof>/report.json + REPORT.md, numbered flags
(F1, F2 …) that decide.py records owner's calls against.
"""
import argparse, json, re, sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import warehouse as W

ROOT = HERE.parents[2]
ACTIONS = {"off": "Turn off", "pull_up": "Your call (kill rule hit, signs of life)", "double_down": "Double down",
           "keep": "Keep", "prospect": "Keep, prospecting", "watch": "Watch", "too_early": "Too early", "budget_up": "Budget up",
           "budget_down": "Budget down", "budget_hold": "Hold budget"}


def desk_dir(brand):
    return ROOT / "runs" / "media-buying" / brand


def load_desk(brand):
    return json.loads((desk_dir(brand) / "desk.json").read_text())


# ----------------------------------------------------------------- the reads --
def live_ads(acct):
    return W.rows("""
select ad_id, ad_name, adset_id, adset_name, campaign_id, campaign_name, landing_page_url,
       coalesce(campaign_daily_budget, 0) campaign_budget, coalesce(adset_daily_budget, 0) adset_budget, created_time::date created
from meta_ads where account_id = :'acct' and effective_status = 'ACTIVE';""", acct=acct)


def ad_days(acct, start, end):
    """Per ad, per window: spend, purchases, value, impressions, link clicks, checkouts."""
    return W.rows("""
with d as (
  select ad_id, campaign_id, date, spend, coalesce(purchases,0) purchases, coalesce(purchase_value,0) value,
         coalesce(impressions,0) impressions, coalesce(reach,0) reach, coalesce(link_clicks,0) link_clicks,
         coalesce((select sum((a->>'value')::numeric) from jsonb_array_elements(coalesce(actions,'[]'::jsonb)) a
                   where a->>'action_type' in ('offsite_conversion.fb_pixel_initiate_checkout')), 0) checkouts
  from meta_ad_insights where account_id = :'acct' and date <= :'end')
select ad_id, campaign_id,
  sum(spend) life_spend, sum(purchases) life_buys, sum(value) life_value, sum(impressions) life_impr, sum(link_clicks) life_clicks, sum(checkouts) life_checkouts,
  sum(spend) filter (where date > (:'end')::date - 7) spend7, sum(purchases) filter (where date > (:'end')::date - 7) buys7, sum(value) filter (where date > (:'end')::date - 7) value7,
  sum(spend) filter (where date > (:'end')::date - 3) spend3, sum(purchases) filter (where date > (:'end')::date - 3) buys3,
  sum(spend) filter (where date > (:'end')::date - 14) spend14, sum(purchases) filter (where date > (:'end')::date - 14) buys14,
  sum(impressions) filter (where date > (:'end')::date - 7) impr7, sum(reach) filter (where date > (:'end')::date - 7) reach7
from d group by 1, 2;""", acct=acct, end=end)


def last_day(acct):
    """The last day the warehouse holds for the account, or None."""
    r = W.rows("select max(date)::text d from meta_ad_insights where account_id = :'acct';", acct=acct)
    return (r[0]["d"] or None) if r else None


def campaign_spend(acct, end):
    return {r["campaign_id"]: r for r in W.rows("""
select campaign_id, max(campaign_name) name,
  sum(spend) filter (where date > (:'end')::date - 7) spend7, sum(purchases) filter (where date > (:'end')::date - 7) buys7,
  sum(spend) filter (where date > (:'end')::date - 3) spend3, sum(purchases) filter (where date > (:'end')::date - 3) buys3
from meta_ad_insights where account_id = :'acct' and date <= :'end' group by 1;""", acct=acct, end=end)}


def store_funnels(days, end, desk=None):
    """The store's real order value and contribution per order, by funnel (upsells in, refunds out).
    A store whose P&L carries no funnel tag (desk "store_source": "shopify_pnl") has none: every funnel
    then uses its own first-order line."""
    if (desk or {}).get("store_source") == "shopify_pnl":
        return {}
    return {r["funnel"]: r for r in W.rows("""
select coalesce(e.funnel,'(none)') funnel, count(*) orders, avg(p.revenue) aov,
  avg(p.revenue - coalesce(e.refunds_total,0) - coalesce(p.cogs,0) - coalesce(p.air_freight,0) - coalesce(p.fulfillment_us,0)
      - coalesce(p.fulfillment_china,0) - coalesce(p.payment_fee,0) - coalesce(p.platform_fee,0)) contribution
from pnl_orders p left join order_economics e on e.order_number = p.order_number
where p.revenue > 0 and p.date_placed::date > (:'end')::date - :days and p.date_placed::date <= :'end'
group by 1;""", days=days, end=end)}


SHOPIFY_BLEND = """
select count(*) orders, sum(p.revenue) revenue,
  sum(p.revenue - coalesce(p.tax,0) - coalesce(p.refunds_total,0) - coalesce(p.cogs,0)
      - coalesce(p.fulfillment, (select avg(q.fulfillment) from {table} q where q.placed_date > (:'end')::date - 30 and q.placed_date <= :'end'), 0)
      - coalesce(p.freight,0) - coalesce(p.payment_fee,0) - coalesce(p.platform_fee,0)) contribution,
  max(p.placed_date) last_order
from {table} p
where p.revenue > 0 and not p.cancelled and coalesce(p.seeded,0) = 0 and p.placed_date > (:'end')::date - :days and p.placed_date <= :'end';"""


def _table(desk):
    """The desk's own store P&L table name (a Shopify-style P&L view), refused unless it is a plain name."""
    t = desk.get("store_table", "")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", t):
        raise SystemExit("desk.json store_table must be a plain table name when store_source is shopify_pnl")
    return t


def store_blend(acct, end, days=7, desk=None):
    """The whole store against the whole ad account, same days."""
    shopify = (desk or {}).get("store_source") == "shopify_pnl"
    s = W.rows(SHOPIFY_BLEND.format(table=_table(desk)) if shopify else """
select count(*) orders, sum(p.revenue) revenue,
  sum(p.revenue - coalesce(e.refunds_total,0) - coalesce(p.cogs,0) - coalesce(p.air_freight,0) - coalesce(p.fulfillment_us,0)
      - coalesce(p.fulfillment_china,0) - coalesce(p.payment_fee,0) - coalesce(p.platform_fee,0)) contribution,
  max(p.date_placed)::date last_order
from pnl_orders p left join order_economics e on e.order_number = p.order_number
where p.revenue > 0 and coalesce(p.seeding_label,'') = '' and p.date_placed::date > (:'end')::date - :days and p.date_placed::date <= :'end';""",
                days=days, end=end)[0]
    m = W.rows("""select sum(spend) spend from meta_ad_insights where account_id = :'acct' and date > (:'end')::date - :days and date <= :'end';""",
               acct=acct, end=end, days=days)[0]
    spend, orders, contrib, rev = W.num(m["spend"]), W.num(s["orders"]), W.num(s["contribution"]), W.num(s["revenue"])
    return {"days": days, "meta_spend": round(spend, 2), "store_orders": int(orders), "store_revenue": round(rev, 2),
            "store_contribution": round(contrib, 2), "blended_cpa": round(spend / orders, 2) if orders else None,
            "contribution_per_order": round(contrib / orders, 2) if orders else None,
            "mer": round(rev / spend, 2) if spend else None, "after_ads": round(contrib - spend, 2),
            "last_order": s["last_order"]}


# ----------------------------------------------------------------- the rules --
def funnel_of(desk, url):
    url = url or ""
    return next((f for f in desk["funnels"] if f["match"] in url), None)


def break_even(desk, f, store):
    """Store contribution per order on the funnel when it has enough orders, else the offer's first-order line."""
    if not f:
        return None, "no funnel match"
    s = store.get(f["store_funnel"])
    if s and W.num(s["orders"]) >= desk["min_store_orders"]:
        return round(W.num(s["contribution"]), 2), f"store, {int(W.num(s['orders']))} orders / {desk['store_window_days']} days"
    return f["fallback_break_even"], "offer's first-order break-even (too few store orders)"


def judge_ad(a, be, L, life):
    """One ad -> (action, why). a: life_spend, life_buys, spend7, buys7, share, checkouts, link_rate."""
    spend, buys = a["life_spend"], a["life_buys"]
    cpa = spend / buys if buys else None
    cpa7 = a["spend7"] / a["buys7"] if a["buys7"] else None
    lived = [k for k, ok in (("share of spend", a["share"] >= life["share_of_spend_pct"]),
                             ("checkouts", a["checkouts"] >= life["checkouts"]),
                             ("link click rate", a["link_rate"] >= life["link_click_rate_pct"])) if ok]
    if spend < L["too_early_below"] * be:
        return "too_early", f"${spend:.0f} spent, under 1 break-even (${be:.0f})"
    kill = None
    if buys == 0 and spend >= L["kill_no_sale_at"] * be:
        kill = f"no sale after ${spend:.0f} ({spend / be:.1f}× break-even)"
    elif buys and spend >= L["decision_at"] * be and cpa > L["cut_cpa_over"] * be:
        kill = f"CPA ${cpa:.0f} is {cpa / be:.1f}× break-even after ${spend:.0f}"
    if kill:
        return ("pull_up", kill + "; but " + ", ".join(lived)) if lived else ("off", kill)
    # an ad with a real week behind it is judged on that week; a young one on its whole life
    recent = a["spend7"] >= be
    n, c, when = (a["buys7"], cpa7, "last 7 days") if recent else (buys, cpa, "so far")
    if recent and not a["buys7"]:
        return "watch", f"no sale in the last 7 days on ${a['spend7']:.0f} (lifetime CPA {('$%.0f' % cpa) if cpa else 'none'})"
    if n >= L["double_down_min_purchases"] and c <= L["double_down_cpa_up_to"] * be:
        return "double_down", f"{n:.0f} sales at ${c:.0f} CPA {when}, {c / be:.2f}× break-even"
    if c and c <= L["keep_cpa_up_to"] * be:
        return "keep", f"CPA ${c:.0f} {when}, {c / be:.2f}× break-even"
    return "watch", (f"CPA ${c:.0f} {when}, {c / be:.2f}× break-even" if c else f"no sale yet, ${spend:.0f} spent")


def rule_of(desk):
    """The desk's own keep / kill rule, or None. An unknown type is refused, never guessed at."""
    r = desk.get("rule")
    if r and r.get("type") != "meta_cpa_windows":
        raise SystemExit("desk.json rule type %r is not one this desk knows" % r.get("type"))
    return r


def judge_windows(a, R):
    """One ad -> (action, why), by the desk's rule. a: spend3/buys3, spend7/buys7, spend14/buys14, freq7 (daily
    frequency over 7 days), share7 (per cent of the account's 7-day spend). Binary once the ad is judged."""
    s14, b14, line = a["spend14"], a["buys14"], R["cpa"]
    if not b14 and s14 >= R["no_sale_off_at_14d_spend"]:
        return "off", "no sale in 14 days on $%.0f" % s14
    if s14 < R["judge_at_14d_spend"]:
        return "too_early", "$%.0f spent in 14 days, judged at $%.0f" % (s14, R["judge_at_14d_spend"])
    reads = [(n, a["spend%d" % n], a["buys%d" % n]) for n in (3, 7, 14) if a["spend%d" % n] > 0]
    said = ", ".join("%dd %s" % (n, ("$%.0f" % (s / b)) if b else "no sale") for n, s, b in reads)
    under = [n for n, s, b in reads if b and s / b <= line]
    if under:
        return "keep", "%s: at or under $%.0f in %s" % (said, line, " and ".join("%dd" % n for n in under))
    P = R["prospecting"]
    if s14 / b14 <= P["cpa14_up_to"] and a["freq7"] and a["freq7"] <= P["daily_frequency7_up_to"] and a["share7"] >= P["share7_from_pct"]:
        return "prospect", "%s: over $%.0f, but %.0f%% of spend at %.2f daily frequency" % (said, line, a["share7"], a["freq7"])
    return "off", "%s: over $%.0f in every window" % (said, line)


def judge_campaign(c, be, L, blend):
    cpa3 = c["spend3"] / c["buys3"] if c["buys3"] else None
    cpa7 = c["spend7"] / c["buys7"] if c["buys7"] else None
    healthy = blend["after_ads"] >= 0
    if cpa3 and cpa7 and cpa3 <= L["budget_up_cpa_up_to"] * be and cpa7 <= L["budget_up_cpa_up_to"] * be:
        if healthy:
            return "budget_up", f"CPA ${cpa3:.0f} (3 days) and ${cpa7:.0f} (7 days), both at or under break-even ${be:.0f}; store after ads ${blend['after_ads']:+,.0f}"
        return "budget_hold", f"campaign is at break-even, but the store is ${blend['after_ads']:+,.0f} after ads this week"
    over = lambda x: x is None or x > L["budget_down_cpa_over"] * be
    if c["spend7"] > be and over(cpa3) and over(cpa7):
        return "budget_down", f"CPA {('$%.0f' % cpa3) if cpa3 else 'none'} (3 days), {('$%.0f' % cpa7) if cpa7 else 'none'} (7 days) — over {L['budget_down_cpa_over']}× break-even ${be:.0f}"
    if not healthy:
        return "budget_hold", f"store is ${blend['after_ads']:+,.0f} after ads this week"
    return "budget_hold", f"CPA {('$%.0f' % cpa7) if cpa7 else 'none'} (7 days) against break-even ${be:.0f}"


# ----------------------------------------------------------------- the run --
def run(brand, asof=None):
    desk = load_desk(brand)
    L, life, acct = desk["lines"], desk["signs_of_life"], desk["meta_account"]
    end = asof or str(date.today() - timedelta(days=1))
    if not asof and rule_of(desk):   # windows end on the last day the warehouse holds, never on a day not synced yet
        end = min(end, last_day(acct) or end)
    ads = live_ads(acct)
    perf = {r["ad_id"]: r for r in ad_days(acct, None, end)}
    camps = campaign_spend(acct, end)
    store = store_funnels(desk["store_window_days"], end, desk)
    blend = store_blend(acct, end, desk=desk)
    R = rule_of(desk)
    windows = {str(n): blend if n == 7 else store_blend(acct, end, days=n, desk=desk) for n in (3, 7, 14)} if R else None
    total7 = sum(W.num(c.get("spend7")) for c in camps.values())
    flags, by_campaign = [], {}
    for a in ads:
        p = perf.get(a["ad_id"], {})
        f = funnel_of(desk, a["landing_page_url"])
        be, be_from = break_even(desk, f, store)
        c = camps.get(a["campaign_id"], {})
        x = {"life_spend": W.num(p.get("life_spend")), "life_buys": W.num(p.get("life_buys")),
             "spend7": W.num(p.get("spend7")), "buys7": W.num(p.get("buys7")),
             "share": 100 * W.num(p.get("spend7")) / W.num(c.get("spend7"), 1) if W.num(c.get("spend7")) else 0,
             "checkouts": W.num(p.get("life_checkouts")),
             "link_rate": 100 * W.num(p.get("life_clicks")) / W.num(p.get("life_impr"), 1) if W.num(p.get("life_impr")) else 0}
        for n in (3, 14):
            x["spend%d" % n], x["buys%d" % n] = W.num(p.get("spend%d" % n)), W.num(p.get("buys%d" % n))
        x["freq7"] = round(W.num(p.get("impr7")) / W.num(p.get("reach7")), 2) if W.num(p.get("reach7")) else None
        x["share7"] = round(100 * x["spend7"] / total7, 1) if total7 else 0
        if R:
            be, be_from = R["cpa"], "the desk's rule"
            act, why = judge_windows(x, R)
        elif be is None:
            act, why = "watch", "landing page not mapped to a funnel in desk.json"
        else:
            act, why = judge_ad(x, be, L, life)
        by_campaign.setdefault(a["campaign_id"], []).append((be or 0, x["spend7"]))
        flags.append({"kind": "ad", "id": a["ad_id"], "name": a["ad_name"], "campaign": a["campaign_name"], "adset": a["adset_name"],
                      "offer": (f.get("offer_key") or f.get("offer")) if f else None, "break_even": be, "break_even_from": be_from,
                      "spend": round(x["life_spend"], 2), "purchases": int(x["life_buys"]),
                      "cpa": round(x["life_spend"] / x["life_buys"], 2) if x["life_buys"] else None,
                      "cpa7": round(x["spend7"] / x["buys7"], 2) if x["buys7"] else None,
                      "share7": round(x["share"], 1), "checkouts": int(x["checkouts"]), "link_rate": round(x["link_rate"], 2),
                      "action": act, "why": why})
        if R:
            flags[-1].update({"windows": {str(n): {"spend": round(x["spend%d" % n], 2), "sales": int(x["buys%d" % n]),
                                                   "cpa": round(x["spend%d" % n] / x["buys%d" % n], 2) if x["buys%d" % n] else None} for n in (3, 7, 14)},
                              "freq7": x["freq7"], "account_share7": x["share7"], "created": str(a.get("created") or "")})
    for cid, items in by_campaign.items():
        c = camps.get(cid)
        if not c:
            continue
        w = sum(s for _, s in items) or 1
        be = sum(b * s for b, s in items) / w if any(s for _, s in items) else sum(b for b, _ in items) / len(items)
        cc = {k: W.num(c[k]) for k in ("spend3", "buys3", "spend7", "buys7")}
        act, why = judge_campaign(cc, be, L, blend)
        if R:
            why = why.replace("break-even", "the line")
        ad = next((x for x in ads if x["campaign_id"] == cid), {})
        flags.append({"kind": "campaign", "id": cid, "name": c["name"], "break_even": round(be, 2),
                      "spend7": round(cc["spend7"], 2), "purchases7": int(cc["buys7"]),
                      "cpa3": round(cc["spend3"] / cc["buys3"], 2) if cc["buys3"] else None,
                      "cpa7": round(cc["spend7"] / cc["buys7"], 2) if cc["buys7"] else None,
                      "daily_budget": W.num(ad.get("campaign_budget")) / 100 or None,
                      "step_pct": L["budget_step_pct"], "action": act, "why": why})
    order = ["off", "pull_up", "budget_down", "budget_up", "double_down", "prospect", "watch", "keep", "budget_hold", "too_early"]
    flags.sort(key=lambda f: (order.index(f["action"]), -(f.get("spend") or f.get("spend7") or 0)))
    for i, f in enumerate(flags, 1):
        f["flag"] = f"F{i}"
    rep = {"brand": brand, "asof": end, "desk_status": desk["status"], "lines": L, "signs_of_life": life,
           "store": blend, "store_funnels": {k: {"orders": int(W.num(v["orders"])), "aov": round(W.num(v["aov"]), 2),
                                                  "contribution_per_order": round(W.num(v["contribution"]), 2)} for k, v in store.items()},
           "counts": {k: sum(1 for f in flags if f["action"] == k) for k in order}, "flags": flags}
    if R:
        meta = {n: {"spend": sum(f["windows"][n]["spend"] for f in flags if f["kind"] == "ad"), "sales": sum(f["windows"][n]["sales"] for f in flags if f["kind"] == "ad")} for n in windows}
        rep.update({"rule": R, "name": desk.get("name") or brand, "windows": {n: {"business": windows[n], "live_ads": {
            "spend": round(m["spend"], 2), "sales": m["sales"], "cpa": round(m["spend"] / m["sales"], 2) if m["sales"] else None}} for n, m in meta.items()}})
    out = desk_dir(brand) / end
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    (out / "REPORT.md").write_text(markdown(rep))
    return rep, out


def markdown(r):
    s = r["store"]
    L = [f"# Analyze ads — {r['brand']}, through {r['asof']}", "",
         f"**Store, last {s['days']} days:** {s['store_orders']} orders · revenue ${s['store_revenue']:,.0f} · contribution ${s['store_contribution']:,.0f} · "
         f"Meta spend ${s['meta_spend']:,.0f} · blended CPA {('$%.2f' % s['blended_cpa']) if s['blended_cpa'] else '—'} · "
         f"contribution per order {('$%.2f' % s['contribution_per_order']) if s['contribution_per_order'] else '—'} · after ads **${s['after_ads']:+,.0f}** (last order in the warehouse {s['last_order']})", "",
         "| Flag | Call | What | Numbers | Why |", "|---|---|---|---|---|"]
    for f in r["flags"]:
        if f["action"] in ("too_early",):
            continue
        if f.get("windows"):
            nums = " / ".join("%sd %s ($%.0f, %d)" % (n, ("$%.0f" % w["cpa"]) if w["cpa"] else "—", w["spend"], w["sales"]) for n, w in f["windows"].items())
            nums += " · daily freq %s · %s%% of spend" % (f["freq7"] or "—", f["account_share7"])
        elif f["kind"] == "ad":
            nums = f"${f['spend']:,.0f} spent · {f['purchases']} sales · CPA {('$%.0f' % f['cpa']) if f['cpa'] else '—'} · break-even ${f['break_even'] or 0:.0f}"
        else:
            nums = f"7d ${f['spend7']:,.0f} · {f['purchases7']} sales · CPA 3d {f['cpa3'] or '—'} / 7d {f['cpa7'] or '—'} · break-even ${f['break_even']:.0f}"
        L.append(f"| {f['flag']} | {ACTIONS[f['action']]} | {f['kind']}: {f['name'][:70]} | {nums} | {f['why']} |")
    L += ["", f"Too early (not shown): {r['counts']['too_early']} ads.", "", f"Lines: {r['desk_status']}."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("brand"); ap.add_argument("--asof")
    a = ap.parse_args(argv)
    rep, out = run(a.brand, a.asof)
    print(json.dumps({"out": str(out), "counts": rep["counts"], "store": rep["store"]}, indent=1))


if __name__ == "__main__":
    main()
