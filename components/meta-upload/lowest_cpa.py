#!/usr/bin/env python3
"""lowest_cpa — every approval card's default words and page, cheapest first, from records already kept. No Meta call.

    python3 lowest_cpa.py --brand <brand> [--promo]      print the picks with their numbers

Rule (owner, 2026-11-16): every card carries exactly 2 primary texts, 2 headlines and 2 descriptions, each the lowest
cost per purchase among proven lines (100+ purchases), and launches to ONE page: the brand's landing page with the
lowest cost per purchase over the last 30 days (10+ purchases).
  primary texts  the bank (runs/winners/<brand>/bank.json, best snapshot), ranked on their own, full bodies only
                 (250+ characters), a hard-coded link line dropped
  headlines      the bank, ranked on their own
  descriptions   the warehouse: ads whose creative carries one description, spend ÷ purchases summed per text
  page           the warehouse: spend ÷ purchases per landing page (query dropped), last 30 days
A line written for a past or seasonal offer (a sale, a price cut, a holiday, a clearance) is skipped, never reworded;
a promo card (`promo=True`) keeps them. Each pick carries its cpa and purchases. Brand-agnostic.
"""
import argparse, collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MIN_PURCH, MIN_PAGE_PURCH, MIN_BODY, PAGE_DAYS = 100, 10, 250, 30
OFFER = re.compile(r"\bsale\b|tariff|labor day|black friday|cyber|valentine|christmas|holiday|mother'?s day|father'?s day|"
                   r"new year|% ?off|\$\s?\d+\s?off|save \$|lowest price|final inventory|end of (an )?era|last chance|"
                   r"price(s)? (is|are) about|free \$|\$\d+ of\b|clearance|ends tonight|today only|\$\d+ (was|is) too much|"
                   r"we heard you|price drop|special offer|claim your|exclusive offer|limited time", re.I)


def _bank(brand):
    p = REPO / "runs" / "winners" / brand / "bank.json"
    d = json.loads(p.read_text()) if p.is_file() else {}
    return list(d.values()) if isinstance(d, dict) and "rows" not in d else d.get("rows", [])


def _best(r):
    s = [x for x in (r.get("snapshots") or []) if (x.get("purchases") or 0) >= MIN_PURCH and x.get("cpa")]
    return min(s, key=lambda x: x["cpa"]) if s else None


def _clean(body):
    return "\n".join(l for l in (body or "").split("\n") if not re.search(r"https?://|\.com\b", l)).strip()


def _rank(items, promo, n=2):
    seen, out = set(), []
    for cpa, purch, text, src in sorted(items):
        key = re.sub(r"\W+", " ", text.lower()).strip()[:160]
        if not text or key in seen or (not promo and OFFER.search(text)):
            continue
        seen.add(key)
        out.append({"text": text, "cpa": round(cpa, 2), "purchases": int(purch), "from": src})
        if len(out) == n:
            break
    return out


def _q():
    sys.path.insert(0, str(HERE))
    import directory as DIR
    return DIR._q()


def descriptions(brand, promo=False, q=None):
    q = q or _q()
    ads = q("select a.raw, sum(i.spend) spend, sum(i.purchases) p from meta_ads a join meta_ad_insights i on i.ad_id=a.ad_id "
            f"where i.account_name ilike '%{brand[:4]}%' group by a.ad_id, a.raw having sum(i.spend)>0")
    agg = collections.defaultdict(lambda: [0.0, 0.0])
    for a in ads:
        raw = json.loads(a["raw"]) if isinstance(a["raw"], str) else (a["raw"] or {})
        found = []

        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in ("description", "link_description") and isinstance(v, str) and v.strip():
                        found.append(v.strip())
                    elif k == "descriptions" and isinstance(v, list):
                        found.extend(t.get("text", "").strip() for t in v if isinstance(t, dict) and t.get("text"))
                    else:
                        walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(raw.get("creative") or raw)
        found = list(dict.fromkeys(found))
        if len(found) == 1:
            g = agg[found[0]]
            g[0] += float(a["spend"] or 0)
            g[1] += float(a["p"] or 0)
    got = _rank([(s / p, p, t, "warehouse") for t, (s, p) in agg.items() if p >= MIN_PURCH], promo)
    if len(got) < 2:          # too few proven descriptions: the next slot fills from 30+ purchases, cheapest first
        more = _rank([(s / p, p, t, "warehouse") for t, (s, p) in agg.items() if p >= 30], promo, n=4)
        got += [m for m in more if m["text"] not in {g["text"] for g in got}][:2 - len(got)]
    return got


def page(brand, q=None):
    q = q or _q()
    rows = q("select split_part(split_part(a.landing_page_url,'?',1),'#',1) page, sum(i.spend) spend, sum(i.purchases) p "
             "from meta_ad_insights i join meta_ads a on a.ad_id=i.ad_id "
             f"where i.date >= current_date - {PAGE_DAYS} and i.account_name ilike '%{brand[:4]}%' "
             "and coalesce(a.landing_page_url,'')<>'' group by 1")
    allp = [(float(r["spend"]) / float(r["p"]), float(r["p"]), r["page"]) for r in rows if r["p"] and float(r["p"]) >= 1]
    ok = [x for x in allp if x[1] >= MIN_PAGE_PURCH]
    if not ok:
        return None
    cpa, p, url = min(ok)
    best = {"url": url, "cpa": round(cpa, 2), "purchases": int(p), "days": PAGE_DAYS}
    # a cheaper page with too few sales to count launches beside it (owner, 16 Nov 2026: "in this case lets launch both")
    under = [x for x in allp if x[1] < MIN_PAGE_PURCH and x[0] < cpa and x[1] >= 3]
    if under:
        c2, p2, u2 = min(under)
        best["also"] = {"url": u2, "cpa": round(c2, 2), "purchases": int(p2)}
    return best


def link_id_for(brand, url):
    """The catalog id of a page url, or None."""
    cat = REPO / "lab" / "owner" / "catalog" / "data" / "catalog.json"
    try:
        c = json.loads(cat.read_text())
    except (OSError, ValueError):
        return None
    recs = ((c.get("brands") or {}).get(brand) or {}).get("records") or {}
    norm = lambda u: (u or "").split("?")[0].rstrip("/")
    for it in recs.values():
        if isinstance(it, dict) and it.get("type") == "link" and norm(it.get("url")) == norm(url):
            return it.get("id")
    return None


def picks(brand, promo=False):
    bank = _bank(brand)
    prim, heads = [], []
    for r in bank:
        b = _best(r)
        if not b:
            continue
        body = _clean(r.get("body"))
        if len(body) >= MIN_BODY:
            prim.append((b["cpa"], b["purchases"], body, r["id"]))
        if (r.get("headline") or "").strip():
            heads.append((b["cpa"], b["purchases"], r["headline"].strip(), r["id"]))
    q = _q()
    return {"primary": _rank(prim, promo), "headlines": _rank(heads, promo), "descriptions": descriptions(brand, promo, q),
            "page": page(brand, q)}


def words(brand, promo=False):
    """The card's words dict (2 + 2 + 2) and its page, from `picks`."""
    p = picks(brand, promo)
    return {k: [x["text"] for x in p[k]] for k in ("primary", "headlines", "descriptions")}, p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--promo", action="store_true")
    a = ap.parse_args()
    p = picks(a.brand, a.promo)
    for k in ("primary", "headlines", "descriptions"):
        print(k)
        for x in p[k]:
            print(f"  ${x['cpa']:.2f} x{x['purchases']}  {x['text'][:90]!r}")
    print("page", p["page"])
