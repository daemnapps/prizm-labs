#!/usr/bin/env python3
"""gap_packet — the winners and the losers of one brand, side by side, for the gap read.

    gap_packet.py --brand brand-b      writes runs/media-buying/<brand>/gap/<date>/packet.json + packet.md

the owner, 2 Oct 2026: compare the top 1% "against the top 25 biggest spenders" that did not make
the top 10% — "clearly identify the gaps in the top 1% versus the bottom 90% … against our
marketing doctrines, our avatar details, our research, brand context", so the system has
pass/fail rules and stops repeating what the bottom 90% did.

Reads the latest tiers.json (tiers.py) and, from the warehouse (no Meta calls), each asset's
attention numbers summed over its ads: play rate (video plays ÷ impressions — Meta counts
any start), hold (25% / 50% / 100% watched ÷ plays), thruplay rate, link click rate, plus the landing pages
it sent people to and how long it ran.
"""
import argparse, json, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WS / "tools/copywriter/library"))

WINNERS, LOSERS = "top-1", 25


def tiers(brand):
    runs = sorted((WS / "runs/media-buying" / brand / "tiers").glob("*/tiers.json"))
    return json.loads(runs[-1].read_text())


def attention(brand, ad_ids):
    import meta_copy as MC
    from brand import Brand
    acct = Brand(brand).account_id
    ids = ",".join(f"'{i}'" for i in ad_ids) or "''"
    v = lambda col: f"coalesce(sum((select sum((e->>'value')::numeric) from jsonb_array_elements({col}) e)),0)"
    rows = MC.db_query(f"""select coalesce(json_agg(x),'[]') from (
        select ad_id, sum(impressions) impressions, sum(video_plays) plays, sum(video_thruplays) thruplays,
               {v('video_p25_watched_actions')} p25, {v('video_p50_watched_actions')} p50,
               {v('video_p100_watched_actions')} p100, sum(link_clicks) link_clicks,
               max(frequency) max_frequency, count(distinct date) days
        from meta_ad_insights where account_id='{acct}' and ad_id in ({ids}) group by ad_id) x""")
    pages = MC.db_query(f"""select coalesce(json_agg(x),'[]') from (
        select ad_id, landing_page_url from meta_ads where ad_id in ({ids})) x""")
    return {r["ad_id"]: r for r in rows}, {r["ad_id"]: r["landing_page_url"] for r in pages}


def pct(a, b):
    return round(100 * float(a) / float(b), 1) if b and float(b) else None


def packet(brand):
    d = tiers(brand)
    rows = d["rows"]
    win = [g for g in rows if g["tier"] == WINNERS]
    lose = sorted([g for g in rows if g["tier"] == "under-10"], key=lambda g: -g["spend"])[:LOSERS]
    ids = [a["ad_id"] for g in win + lose for a in g["ads"]]
    att, pages = attention(brand, ids)
    out = []
    for side, group in (("winner", win), ("loser", lose)):
        for g in group:
            s = {k: 0.0 for k in ("impressions", "plays", "thruplays", "p25", "p50", "p100", "link_clicks", "days")}
            for a in g["ads"]:
                for k in s:
                    s[k] += float((att.get(a["ad_id"]) or {}).get(k) or 0)
            out.append({
                "side": side, "rank": g["rank"], "asset": g["asset"], "kind": g["kind"],
                "ad_names": [a["ad_name"] for a in g["ads"]], "campaigns": sorted({a.get("campaign") or "" for a in g["ads"]}),
                "adsets": sorted({a.get("adset") or "" for a in g["ads"]}),
                "spend": g["spend"], "purchases": g["purchases"], "cpa": g["cpa"], "roas": g["roas"],
                "ran": f"{g['first_day']} → {g['last_day']}", "days_with_spend": int(s["days"]),
                "hook_rate": pct(s["plays"], s["impressions"]), "hold_25": pct(s["p25"], s["plays"]),
                "hold_50": pct(s["p50"], s["plays"]), "watched_100": pct(s["p100"], s["plays"]),
                "thruplay_rate": pct(s["thruplays"], s["impressions"]), "link_ctr": pct(s["link_clicks"], s["impressions"]),
                "landing_pages": sorted({pages.get(a["ad_id"]) or "" for a in g["ads"]} - {""}),
                "primary": g["primary"], "headlines": g["headlines"], "instagram": g.get("instagram")})
    return d, out


def md(brand, d, items):
    L = [f"# Gap packet — {brand}", "", f"Window {d['window']['from']} → {d['window']['to']} · ranked by purchases · "
         f"winners = top 1% ({sum(1 for i in items if i['side'] == 'winner')}) · losers = the {LOSERS} under-top-10% assets "
         "with the most spend.", "",
         "Attention numbers: play rate = video plays (any start) ÷ impressions; hold = % of plays reaching 25/50/100%; "
         "link CTR = link clicks ÷ impressions. Blank = not a video or not on file.", ""]
    for i in items:
        L += [f"## {i['side'].upper()} #{i['rank']} — {i['kind']} — {int(i['purchases'])} purchases, ${i['spend']:,.0f}, CPA "
              f"{'$%.2f' % i['cpa'] if i['cpa'] else '—'}",
              f"- Ads: {'; '.join(i['ad_names'][:6])}", f"- Ad sets: {'; '.join(i['adsets'][:4])}",
              f"- Ran: {i['ran']} ({i['days_with_spend']} ad-days) · landing: {', '.join(i['landing_pages'][:3]) or '—'}",
              f"- Play rate {i['hook_rate']}% · hold 25% {i['hold_25']}% · 50% {i['hold_50']}% · 100% {i['watched_100']}% · "
              f"link CTR {i['link_ctr']}%", f"- Headlines: {' | '.join(i['headlines'][:5]) or '—'}", "", "Primary text(s):", ""]
        L += [f"> " + t.replace("\n", "\n> ") + "\n" for t in i["primary"][:3]] or ["> (no words on file)", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    d, items = packet(a.brand)
    out = WS / "runs/media-buying" / a.brand / "gap" / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    (out / "packet.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    (out / "packet.md").write_text(md(a.brand, d, items))
    w = [i for i in items if i["side"] == "winner"]
    l = [i for i in items if i["side"] == "loser"]
    avg = lambda xs, k: round(sum(x[k] for x in xs if x[k] is not None) / max(1, sum(1 for x in xs if x[k] is not None)), 1)
    print(f"{a.brand}: {len(w)} winners, {len(l)} losers → {out.relative_to(WS)} · play rate {avg(w, 'hook_rate')}% vs "
          f"{avg(l, 'hook_rate')}% · hold 25% {avg(w, 'hold_25')} vs {avg(l, 'hold_25')} · link CTR {avg(w, 'link_ctr')} vs {avg(l, 'link_ctr')}")


if __name__ == "__main__":
    main()
