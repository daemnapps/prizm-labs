#!/usr/bin/env python3
"""performance — step 12: spend, purchases and revenue read back for every ad
the system put live, by the Prizm Labs key, once a day.

    performance.py                 # both brands, the last 7 days
    performance.py --days 30
    performance.py --dry-run       # list what it would read, call nothing

Reads the ad-level insights of each brand's ad account for ads named the
short way (`<unit>_<page>` — every ad the uploader makes), and writes:

    Shared Assets/meta/performance.jsonl        one line per ad per day
    meta/<brand>/3-live/<lane>/<unit>/card.json  card["performance"] = the totals

Nothing is written to Meta; this only reads. Purchases and revenue are the
`purchase` action and action value (Meta's default 7-day click / 1-day view).
"""
import argparse, json, sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "naming"))
import names as N
import cards as C
from brand import available, Brand

FIELDS = "ad_id,ad_name,date_start,spend,impressions,clicks,actions,action_values"


def ours(name):
    """An ad the system named: <unit>_<page>."""
    d = N.parse_short(name or "")
    return d if d and d.get("funnel") and not d.get("asset") else None


def action(rows, kind="purchase"):
    for r in rows or []:
        if r.get("action_type") == kind:
            return float(r.get("value") or 0)
    return 0.0


def read(brand, days, m=None):
    from meta import Meta
    m = m or Meta(brand)
    since = (date.today() - timedelta(days=days)).isoformat()
    until = date.today().isoformat()
    rows = m.paged(f"act_{m.ACCOUNT}/insights", level="ad", fields=FIELDS, time_increment=1,
                   time_range=json.dumps({"since": since, "until": until}),
                   filtering=json.dumps([{"field": "ad.name", "operator": "CONTAIN", "value": "_brief-"}]))
    out = []
    for r in rows:
        d = ours(r.get("ad_name"))
        if not d:
            continue
        out.append({"brand": brand, "date": r.get("date_start"), "ad_id": r.get("ad_id"),
                    "live_id": f"live_meta_{r.get('ad_id')}", "meta_ad_name": r.get("ad_name"),
                    "unit": d["ad_name"], "page": d["funnel"],
                    "spend": float(r.get("spend") or 0), "impressions": int(r.get("impressions") or 0),
                    "clicks": int(r.get("clicks") or 0),
                    "purchases": action(r.get("actions")), "revenue": action(r.get("action_values"))})
    return out


def write(rows, root=None):
    root = Path(root) if root else C.root()
    log = root / "performance.jsonl"
    seen = set()
    if log.is_file():
        for line in log.read_text().splitlines():
            try:
                x = json.loads(line); seen.add((x["ad_id"], x["date"]))
            except Exception:
                pass
    new = [r for r in rows if (r["ad_id"], r["date"]) not in seen]
    with log.open("a") as f:
        for r in new:
            f.write(json.dumps({**r, "read": datetime.now().isoformat(timespec="seconds")}) + "\n")
    # totals onto each live card
    tot = {}
    for r in rows:
        t = tot.setdefault(r["unit"], {"spend": 0, "purchases": 0, "revenue": 0, "impressions": 0, "clicks": 0})
        for k in t:
            t[k] += r[k]
    for unit, t in tot.items():
        for card in sorted(root.glob(f"*/3-live/*/{unit}/card.json")):
            c = json.loads(card.read_text())
            c["performance"] = {**{k: round(v, 2) for k, v in t.items()},
                                "cpa": round(t["spend"] / t["purchases"], 2) if t["purchases"] else None,
                                "roas": round(t["revenue"] / t["spend"], 2) if t["spend"] else None,
                                "as_of": date.today().isoformat()}
            card.write_text(json.dumps(c, indent=1, ensure_ascii=False))
    return len(new), len(tot)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--brand", action="append")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for b in a.brand or available():
        if a.dry_run:
            print(f"{b}: would read act_{Brand(b).account_id} ad insights, last {a.days} days, ads named *_brief-*")
            continue
        rows = read(b, a.days)
        n, units = write(rows)
        print(f"{b}: {len(rows)} ad-days read · {n} new · {units} ad(s) of ours")


if __name__ == "__main__":
    main()
