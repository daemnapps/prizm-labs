#!/usr/bin/env python3
"""winner_views: two read-only views of a brand's ad history, driven by winners.py (`yoy`, `store`). Facts only.

    yoy    the same months in both years, from an audit window's cells.json, with each creative's tags from tags.json
           under the audit's own merging rules. The widest window unless one is named; the last 3 full months by default.
           -> runs/winners/<brand>/views/yoy-<from>-<to>.md + .json
    store  whole-store revenue against ad spend by week (weeks start Monday, the newest can be part-way), read from the
           warehouse through funnel-tracking's daily history pull. -> runs/winners/<brand>/views/store-<date>.md + .json

Named apart from funnel-tracking's `views` module, which audit.py imports by that name.
"""
import collections, datetime as dt, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "funnel-tracking" / "machine"))
import audit as A  # noqa: E402
import bank as B  # noqa: E402

NOT_TAGGED = "Not tagged yet"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class BadInput(Exception):
    pass


def out_dir(root, brand):
    d = B.brand_dir(root, brand) / "views"
    d.mkdir(parents=True, exist_ok=True)
    return d


def money(x):
    return "-" if x is None else f"${x:,.0f}"


def cost(x):
    return "-" if x is None else f"${x:,.2f}"


def times(x):
    return "-" if x is None else f"{x:.2f}x"


def pct(x):
    return "-" if x is None else f"{x * 100:.1f}%"


def div(a, b, nd=2):
    return round(a / b, nd) if b else None


def clean(s):
    return str(s).replace("|", "/")


def write_pair(d, stem, text, doc):
    md, js = d / f"{stem}.md", d / f"{stem}.json"
    md.write_text(text)
    js.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return md, js


# ---------- yoy ----------

def widest_label(root, brand):
    d = B.brand_dir(root, brand) / "audit"
    wins = [(B.widest_key(json.loads(f.read_text())), f.parent.name) for f in (d.glob("*/window.json") if d.is_dir() else [])]
    if not wins:
        raise BadInput(f"{brand} has no audit yet")
    return max(wins)[1]


def default_months(until):
    """The last 3 full months at the window's end, as (from, to) month numbers."""
    end = dt.date.fromisoformat(until)
    full_to_end = (end + dt.timedelta(days=1)).day == 1
    n = end.year * 12 + end.month - 1 - (0 if full_to_end else 1)
    return (n - 2) % 12 + 1, n % 12 + 1


def periods(until, first, last):
    """[(label, [YYYY-MM...])] for the earlier and the later year: the later run of those months that ends by `until`.
    A run across New Year (Nov to Feb) starts in the year before."""
    end = dt.date.fromisoformat(until)
    span = (last - first) % 12
    year = end.year if (end.year, last) <= (end.year, end.month) else end.year - 1
    def run(y):
        months = [((y * 12 + last - 1 - span + i) // 12, (y * 12 + last - 1 - span + i) % 12 + 1) for i in range(span + 1)]
        name = str(y) if months[0][0] == y else f"{months[0][0]}-{str(y)[2:]}"
        return name, [f"{a}-{b:02d}" for a, b in months]
    return [run(year - 1), run(year)]


def creative_tags(cells, merges, mem, ranked):
    """{creative key: (group, on screen, message)}, with the audit's merging rules and build()'s tag lookup."""
    def key(n):
        k = A.script_key(n)
        while k in merges:
            k = merges[k]
        return k
    names = collections.defaultdict(collections.Counter)
    for c in cells:
        names[key(c["name"])][c["name"]] += c["purchases"]
    formats = {r["name"]: r.get("format") for r in ranked.get("rows", [])}
    out = {}
    for k, variants in names.items():
        t = mem.get(k) or next((mem[v] for v, _ in variants.most_common() if v in mem), None)
        if not t:
            out[k] = (NOT_TAGGED, NOT_TAGGED, NOT_TAGGED)
            continue
        screen = t.get("on_screen") or NOT_TAGGED
        out[k] = (t.get("group") or A.group(t.get("format") or formats.get(k) or "", screen), screen, t.get("message") or NOT_TAGGED)
    return key, out


def totals(rows, year_total=None):
    sp = round(sum(r["spend"] for r in rows), 2)
    pu = sum(r["purchases"] for r in rows)
    va = sum(r["value"] for r in rows)
    out = {"ads": len({r["creative"] for r in rows}), "purchases": pu, "spend": sp, "cpa": div(sp, pu), "roas": div(va, sp)}
    if year_total is not None:
        out["share"] = div(pu, year_total, 4)
    return out


def yoy(root, brand, window=None, first=None, last=None):
    label = window or widest_label(root, brand)
    d = B.brand_dir(root, brand) / "audit" / label
    win, cells = A.load(d / "window.json"), A.load(d / "cells.json")
    if not win or not cells:
        raise BadInput(f"the {label} audit has no cells")
    if first is None:
        first, last = default_months(win["until"])
    merges, mem, ranked = A.load(d / "merges.json", {}), A.load(B.brand_dir(root, brand) / "tags.json", {}), A.load(d / "ranked.json", {})
    key, tags = creative_tags(cells, merges, mem, ranked)
    rows = {}
    for name, months in periods(win["until"], first, last):
        rows[name] = [{**c, "creative": key(c["name"]), "group": tags[key(c["name"])][0], "on_screen": tags[key(c["name"])][1],
                       "message": tags[key(c["name"])][2]} for c in cells if c["month"] in months]
    years = list(rows)
    doc = {"brand": brand, "window": label, "since": win["since"], "until": win["until"],
           "months": {y: ms for y, ms in periods(win["until"], first, last)}, "years": {}, "by_group": {}, "by_on_screen": {},
           "by_message": {}, "by_month": []}
    for y in years:
        doc["years"][y] = totals(rows[y])
    for field, slot in (("group", "by_group"), ("on_screen", "by_on_screen"), ("message", "by_message")):
        values = {r[field] for y in years for r in rows[y]}
        table = []
        for v in values:
            line = {"value": v}
            for y in years:
                line[y] = totals([r for r in rows[y] if r[field] == v], doc["years"][y]["purchases"])
            table.append(line)
        doc[slot] = sorted(table, key=lambda x: (-x[years[1]]["purchases"], -x[years[0]]["purchases"], x["value"]))
    for a, b in zip(doc["months"][years[0]], doc["months"][years[1]]):
        doc["by_month"].append({"month": MONTHS[int(b[5:]) - 1], years[0]: totals([r for r in rows[years[0]] if r["month"] == a]),
                                years[1]: totals([r for r in rows[years[1]] if r["month"] == b])})
    stem = f"yoy-{first:02d}-{last:02d}"
    md, js = write_pair(out_dir(root, brand), stem, yoy_md(doc, years), doc)
    return md, js, doc


def span_words(doc):
    y = list(doc["months"])
    ms = doc["months"][y[1]]
    return f"{MONTHS[int(ms[0][5:]) - 1]} to {MONTHS[int(ms[-1][5:]) - 1]}, {y[0]} vs {y[1]}"


def yoy_line(doc):
    y = list(doc["years"])
    def part(k):
        t = doc["years"][k]
        return f"{k}: {money(t['spend'])}, {t['purchases']:,} purchases, CPA {cost(t['cpa'])}, ROAS {times(t['roas'])}, {t['ads']} ads"
    return f"{doc['brand']} {span_words(doc)}. {part(y[0])}. {part(y[1])}."


def yoy_md(doc, years):
    a, b = years
    L = [f"# {doc['brand']} year over year: {span_words(doc)}", "", yoy_line(doc), "",
         f"From the audit window {doc['since']} to {doc['until']}, its cells and merges, and the tag memory. "
         "Ads are creatives, copies merged. Share is of that year's purchases in these months.", ""]
    for title, slot in (("By group", "by_group"), ("By what's on screen", "by_on_screen"), ("By message", "by_message")):
        L += [f"## {title}", "",
              f"| | {a} ads | {a} purchases | {a} share | {a} spend | {a} CPA | {a} ROAS | {b} ads | {b} purchases | {b} share | {b} spend | {b} CPA | {b} ROAS |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in doc[slot]:
            cols = []
            for y in years:
                t = r[y]
                cols += [str(t["ads"]), f"{t['purchases']:,}", pct(t["share"]), money(t["spend"]), cost(t["cpa"]), times(t["roas"])]
            L.append(f"| {clean(r['value'])} | " + " | ".join(cols) + " |")
        L.append("")
    L += ["## Month by month", "",
          f"| Month | {a} spend | {a} purchases | {a} CPA | {a} ROAS | {b} spend | {b} purchases | {b} CPA | {b} ROAS |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in doc["by_month"]:
        cols = []
        for y in years:
            t = r[y]
            cols += [money(t["spend"]), f"{t['purchases']:,}", cost(t["cpa"]), times(t["roas"])]
        L.append(f"| {r['month']} | " + " | ".join(cols) + " |")
    return "\n".join(L) + "\n"


# ---------- store ----------

def weeks_from(days, weeks):
    """Daily history rows -> the newest `weeks` Monday-start weeks, oldest first."""
    g = collections.OrderedDict()
    for k in sorted(days):
        x = days[k]
        day = dt.date.fromisoformat(k)
        wk = (day - dt.timedelta(days=day.weekday())).isoformat()
        w = g.setdefault(wk, collections.Counter())
        w["days"] += 1
        w["spend"] += x.get("spend") or 0
        w["ad_purchases"] += x.get("pixel_buys") or 0
        w["ad_value"] += x.get("pixel_value") or 0
        for ch in ("funnel", "store", "renewal"):
            w[ch + "_revenue"] += (x.get(ch) or {}).get("revenue") or 0
            w[ch + "_orders"] += (x.get(ch) or {}).get("orders") or 0
    out = []
    for wk, w in list(g.items())[-weeks:]:
        rev = w["funnel_revenue"] + w["store_revenue"] + w["renewal_revenue"]
        out.append({"week": wk, "days": w["days"], "orders": int(w["funnel_orders"] + w["store_orders"] + w["renewal_orders"]),
                    "funnel_revenue": round(w["funnel_revenue"], 2), "store_revenue": round(w["store_revenue"], 2),
                    "renewal_revenue": round(w["renewal_revenue"], 2), "revenue": round(rev, 2), "spend": round(w["spend"], 2),
                    "spend_share": div(w["spend"], rev, 4), "ad_purchases": round(w["ad_purchases"], 2)})
    return out


def store(root, brand, weeks=12, today=None, pull=None):
    today = today or dt.date.today()
    if pull is None:
        import history as H     # funnel-tracking: the warehouse read behind its daily charts
        pull = H.pull
    last = today - dt.timedelta(days=1)
    first = last - dt.timedelta(days=last.weekday() + 7 * (weeks - 1))     # the Monday `weeks` weeks back
    days = pull(brand, days=(today - first).days, today=today)
    rows = weeks_from(days, weeks)
    keys = ("orders", "funnel_revenue", "store_revenue", "renewal_revenue", "revenue", "spend", "ad_purchases")
    tot = {k: round(sum(r[k] for r in rows), 2) for k in keys}
    tot["spend_share"] = div(tot["spend"], tot["revenue"], 4)
    doc = {"brand": brand, "asof": today.isoformat(), "through": last.isoformat(), "source": "warehouse, through funnel-tracking history.pull",
           "weeks": rows, "total": tot}
    md, js = write_pair(out_dir(root, brand), f"store-{today.isoformat()}", store_md(doc), doc)
    return md, js, doc


def store_line(doc):
    t = doc["total"]
    return (f"{doc['brand']} store, {len(doc['weeks'])} weeks through {doc['through']}: {money(t['revenue'])} revenue on "
            f"{t['orders']:,.0f} orders, {money(t['spend'])} ad spend ({pct(t['spend_share'])} of revenue), "
            f"{t['ad_purchases']:,.0f} ad-attributed purchases.")


def store_md(doc):
    L = [f"# {doc['brand']} store revenue against ad spend, by week", "", store_line(doc), "",
         "Weeks start Monday; store days. Funnel, store and renewal as funnel-tracking splits them, sync copies out. "
         "Ad-attributed purchases are what the ad platform's pixel counted.", "",
         "| Week | Days | Orders | Funnel revenue | Store revenue | Renewal revenue | Total revenue | Ad spend | Spend share of revenue | Ad-attributed purchases |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in doc["weeks"]:
        L.append(f"| {r['week']} | {r['days']} | {r['orders']:,} | {money(r['funnel_revenue'])} | {money(r['store_revenue'])} | "
                 f"{money(r['renewal_revenue'])} | {money(r['revenue'])} | {money(r['spend'])} | {pct(r['spend_share'])} | {r['ad_purchases']:,.0f} |")
    t = doc["total"]
    L.append(f"| Total | | {t['orders']:,.0f} | {money(t['funnel_revenue'])} | {money(t['store_revenue'])} | {money(t['renewal_revenue'])} | "
             f"{money(t['revenue'])} | {money(t['spend'])} | {pct(t['spend_share'])} | {t['ad_purchases']:,.0f} |")
    return "\n".join(L) + "\n"
