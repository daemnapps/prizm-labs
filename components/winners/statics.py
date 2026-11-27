"""statics — the winning image ads: the static side of the winner loop (the video side is audit → bank → feed).

    winners.py statics --brand <b> [--days 30] [--min-spend 100] [--min-roas <break-even>]

Ruled 2026-11-23: the winner variation workflow existed for video only; a winning static had no way into variations,
so it went down the new-ad path and came back reinvented. This step lists the image ads that are proven on their own
numbers (the warehouse copy of Meta, read only), and ties each to what the chain already holds for it:

  the brief id      read off the ad's name (the naming convention puts it there)
  the chain run     the image-teardown run whose run.json names that brief
  the approved pic  the run's out/approved-picture.md (what was made and approved)
  the 3D set        the filed set whose set.json lists that run

The variation planner (ad-variations `machine/static_plan.py`) reads this list. Writes
runs/winners/<brand>/statics/<date>/statics.json + statics.md. Nothing in an ad account changes.
"""
import datetime as dt, json, re
from pathlib import Path

import audit as A

BRIEF = re.compile(r"(brief-(?:prizm-)?\d{3,4})")


def pull(brand, days):
    """Per image ad over the window: numbers, status and the picture link Meta keeps. Read only."""
    import views as V
    accts = A.accounts(brand)
    if not accts:
        return []
    rows = V._psql("""select i.ad_id, max(i.ad_name) ad_name, max(i.adset_name) adset, sum(i.spend) sp,
        sum(coalesce(i.purchases,0)) b, sum(coalesce(i.purchase_value,0)) v, min(i.date)::text f, max(i.date)::text l,
        max(a.effective_status) st, max(coalesce(a.image_url, a.thumbnail_url)) pic
        from meta_ad_insights i join meta_ads a on a.ad_id = i.ad_id
        where i.account_id in (%s) and a.video_id is null and i.date >= current_date - :'d'::int
        group by 1;""" % A._in_list(accts), d=str(days))
    out = []
    for r in rows:
        sp, b, v = float(r["sp"] or 0), float(r["b"] or 0), float(r["v"] or 0)
        out.append({"ad_id": r["ad_id"], "ad_name": r["ad_name"], "adset": r["adset"], "spend": round(sp, 2),
                    "purchases": b, "value": round(v, 2), "roas": round(v / sp, 2) if sp else None,
                    "cpa": round(sp / b, 2) if b else None, "first": r["f"], "last": r["l"], "status": r["st"],
                    "picture": r["pic"]})
    return out


def runs_by_brief(root, brand):
    out = {}
    for f in sorted((root / "runs" / "image-teardown" / brand).glob("*/run.json")):
        try:
            b = json.loads(f.read_text()).get("brief")
        except ValueError:
            continue
        if b:
            out.setdefault(b, []).append(f.parent.name)
    return out


def sets_by_run(root, brand):
    out = {}
    for f in (root / "runs" / "image-production" / brand / "sets").glob("*/set.json"):
        try:
            runs = json.loads(f.read_text()).get("runs") or []
        except ValueError:
            continue
        for r in runs if isinstance(runs, list) else [runs]:
            out.setdefault(str(r), []).append(f.parent.name)
    return out


def approved(root, brand, run):
    f = root / "runs" / "image-teardown" / brand / run / "out" / "approved-picture.md"
    if not f.is_file():
        return None
    m = re.search(r"THE APPROVED PICTURE:\s*(\S+)", f.read_text())
    return m.group(1) if m else None


def rank(rows, min_spend=100.0, min_roas=None):
    """Proven on its own numbers: spend at the floor, sales, then ROAS. One brief's ads stay separate rows (each ad is
    a placement of the same picture set); the planner groups by brief."""
    keep = [r for r in rows if r["spend"] >= min_spend and r["purchases"] > 0]
    if min_roas is not None:
        keep = [r for r in keep if (r["roas"] or 0) >= min_roas]
    return sorted(keep, key=lambda r: (-(r["roas"] or 0) * min(r["purchases"], 20), -r["purchases"]))


def link(root, brand, rows):
    rb, sr = runs_by_brief(root, brand), sets_by_run(root, brand)
    for r in rows:
        m = BRIEF.search(r["ad_name"] or "")
        r["brief"] = m.group(1) if m else None
        r["runs"] = rb.get(r["brief"], []) if r["brief"] else []
        r["approved_picture"] = next((approved(root, brand, x) for x in r["runs"] if approved(root, brand, x)), None)
        r["sets"] = sorted({s for x in r["runs"] for s in sr.get(x, [])})
        r["state"] = ("ready" if r["runs"] and r["approved_picture"] else
                      "no approved picture on its run" if r["runs"] else
                      "made outside the chain: open a run on its picture first")
    return rows


def write(root, brand, days=30, min_spend=100.0, min_roas=None, rows=None):
    rows = link(root, brand, rank(rows if rows is not None else pull(brand, days), min_spend, min_roas))
    d = root / "runs" / "winners" / brand / "statics" / dt.date.today().isoformat()
    d.mkdir(parents=True, exist_ok=True)
    doc = {"brand": brand, "days": days, "min_spend": min_spend, "min_roas": min_roas, "made": dt.datetime.now().isoformat(timespec="seconds"),
           "winners": rows}
    (d / "statics.json").write_text(json.dumps(doc, indent=1))
    lines = [f"# Winning image ads · {brand} · last {days} days · spend ≥ ${min_spend:,.0f}" +
             (f" · ROAS ≥ {min_roas}" if min_roas else ""), "",
             "| # | Ad | Spend | Sales | ROAS | Status | Brief | Run | 3D set | State |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['ad_name']} | ${r['spend']:,.0f} | {r['purchases']:g} | {r['roas']} | {r['status']} | "
                     f"{r['brief'] or '—'} | {', '.join(r['runs']) or '—'} | {', '.join(r['sets']) or '—'} | {r['state']} |")
    (d / "statics.md").write_text("\n".join(lines) + "\n")
    return d / "statics.json", doc
