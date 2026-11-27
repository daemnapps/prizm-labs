#!/usr/bin/env python3
"""directory — where every ad goes, read from the data warehouse and the repo. No Meta call, no AI: a lookup.

    python3 directory.py --brand brand_b            build runs/meta-upload/<brand>/directory.json + DIRECTORY.md
    python3 directory.py --brand brand_b --show     print the table

Why: routing must come from what is actually spending and live, not from file guesses. Guessing sent one-time ads
into a renamed subscription campaign and split one product across two campaigns (Nov 2026). This table is the
one answer: the warehouse's live campaigns and ad sets lined up with the repo's pages, funnels and briefs.

Reads
  - warehouse (Supabase daily copy, read only, through funnel-tracking's psql door): meta_ads (every ad: campaign,
    ad set, status, landing page) and meta_ad_insights (spend per day) for the brand's ad accounts
  - brands/<brand>/web/funnels/funnels.json (funnel id, path, product), brands/<brand>/meta/account.json (naming,
    signed new ad sets), lab/owner/catalog/data/catalog.json (the brand's pages), brands/<brand>/briefs/briefs.json
Writes one table:
  campaigns  name, id, product, funnel, spend 7/30 days, last spend, ads ACTIVE, the pages its ads land on
  ad_sets    name, id, campaign, avatar, angle, spend 7 days, ads ACTIVE
  funnels    funnel id -> THE campaign: the live campaign named for it, else the one live campaign whose ads land on
             its pages; none (with the reason) when nothing live does — never a guess
  pages      every catalog page -> funnel -> campaign
  briefs     every brief -> avatar x angle -> ad set (open when it is live in the warehouse or signed new)
Live = spent in the last 7 days or has ACTIVE ads. Brand-agnostic.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MAX_AGE_H = 12


def _q():
    sys.path.insert(0, str(REPO / "components/funnel-tracking/machine"))
    import views as V
    return V._psql


def path_of(url):
    """host + folder of a page: two funnels on one path but different sites never match each other."""
    u = urlparse(url or "")
    p = u.path or "/"
    return u.netloc.lower().removeprefix("www.") + (p if p.endswith("/") else p.rsplit("/", 1)[0] + "/")


def build(brand, q=None):
    q = q or _q()
    sys.path.insert(0, str(HERE))
    import upload as U
    from brand import Brand
    b = Brand(brand)
    acct = [r["key_pattern"] for r in q("select key_pattern from brand_sources where source_table = 'meta_ad_insights' "
                                        "and key_column = 'account_id' and brand = :'b';", b=brand)]
    alist = ",".join("'%s'" % a.replace("'", "") for a in acct) or "''"
    spend = q("""select campaign_id, max(campaign_name) campaign, adset_id, max(adset_name) adset,
  round(coalesce(sum(spend) filter (where date > current_date - 7), 0)::numeric, 2) spend7,
  round(sum(spend)::numeric, 2) spend30, max(date) filter (where spend > 0) last_spend
from meta_ad_insights where account_id in (%s) and date > current_date - 30 group by 1, 3;""" % alist)
    ads = q("""select campaign_id, max(campaign_name) campaign, adset_id, max(adset_name) adset, landing_page_url url,
  count(*) filter (where effective_status = 'ACTIVE') active, count(*) ads
from meta_ads where account_id in (%s) group by 1, 3, 5;""" % alist)
    camps, sets = {}, {}
    for r in spend + ads:
        c = camps.setdefault(r["campaign_id"], {"name": r["campaign"], "id": r["campaign_id"], "spend7": 0.0, "spend30": 0.0,
                                                "last_spend": None, "active_ads": 0, "pages": set()})
        s = sets.setdefault(r["adset_id"], {"name": r["adset"], "id": r["adset_id"], "campaign": r["campaign"], "spend7": 0.0,
                                            "active_ads": 0})
        if "spend7" in r:
            c["spend7"] += float(r["spend7"] or 0); c["spend30"] += float(r["spend30"] or 0)
            s["spend7"] += float(r["spend7"] or 0)
            if r["last_spend"] and (not c["last_spend"] or r["last_spend"] > c["last_spend"]):
                c["last_spend"] = r["last_spend"]
        else:
            c["active_ads"] += int(r["active"] or 0); s["active_ads"] += int(r["active"] or 0)
            if r["url"] and int(r["active"] or 0):
                c["pages"].add(path_of(r["url"]))
    live = lambda x: x["spend7"] > 0 or x["active_ads"] > 0
    nm = b.naming
    for c in camps.values():
        parts = (c["name"] or "").split(nm.get("campaign_sep", "_"))
        c["product"], c["funnel"] = (parts[3], parts[4]) if len(parts) >= 7 and parts[0] == "campaign" else (None, None)
        c["live"] = live(c); c["pages"] = sorted(c["pages"])
        c["spend7"], c["spend30"] = round(c["spend7"], 2), round(c["spend30"], 2)
    for s in sets.values():
        parts = (s["name"] or "").split(nm.get("ad_set_sep", "_"))
        s["avatar"], s["angle"] = (parts[2], "_".join(parts[3:])) if len(parts) >= 4 and parts[0] == "adset" else (None, None)
        s["live"] = live(s); s["spend7"] = round(s["spend7"], 2)
    funnels = {}
    for f in U.funnels(brand):
        want = U.campaign_name(b, f["id"], f.get("product"))
        fpath = path_of(f.get("url"))
        named = [c for c in camps.values() if c["name"] == want and c["live"]]
        landing = [c for c in camps.values() if c["live"] and any(p.startswith(fpath) for p in c["pages"])]
        if named:
            pick, why = named[0]["name"], "the live campaign named for this funnel"
        elif len({c["name"] for c in landing}) == 1:
            pick, why = landing[0]["name"], "the one live campaign whose ads land on this funnel's pages"
        else:
            pick = None
            why = ("no live campaign for this funnel (%s would be new)" % want if not landing else
                   "two live campaigns land on this funnel's pages (%s): pick one on the approval page"
                   % ", ".join(sorted({c["name"] for c in landing})))
        funnels[f["id"]] = {"funnel": f["id"], "url": f.get("url"), "product": f.get("product"), "campaign": pick, "why": why}
    pages = []
    cat = json.loads((REPO / "lab/owner/catalog/data/catalog.json").read_text())
    for lid, rec in sorted(((cat.get("brands") or {}).get(brand) or {}).get("records", {}).items()):
        if rec.get("type") != "link" or not rec.get("url"):
            continue
        url, fid, note = U.page_for(rec, brand)
        fu = funnels.get(fid) or {}
        pages.append({"link_id": lid, "url": url, "status": rec.get("status"), "funnel": fid,
                      "campaign": fu.get("campaign"), "why": fu.get("why") or note or "no funnel for this page"})
    signed = set(b.d.get("new_ad_sets") or [])
    live_sets = {s["name"] for s in sets.values() if s["live"]} | {s["name"] for s in sets.values()}
    briefs = []
    bf = REPO / "brands" / brand / "briefs/briefs.json"
    for r in (json.loads(bf.read_text()).get("briefs") if bf.is_file() else []):
        if not (r.get("avatar") and r.get("angle")):
            continue
        name = U.ad_set_for(b, {"avatar": r["avatar"], "angle": r["angle"]})[0] if hasattr(U, "ad_set_for") else None
        briefs.append({"brief": r.get("brief"), "product": r.get("product"), "avatar": r["avatar"], "angle": r["angle"],
                       "ad_set": name, "open": bool(name and (name in live_sets or name in signed))})
    return {"brand": brand, "made": datetime.now().isoformat(timespec="seconds"),
            "source": "warehouse (Supabase daily copy: meta_ads, meta_ad_insights) + repo; no Meta call",
            "campaigns": sorted(camps.values(), key=lambda c: (-c["spend7"], c["name"] or "")),
            "ad_sets": sorted(sets.values(), key=lambda s: (-s["spend7"], s["name"] or "")),
            "funnels": funnels, "pages": pages, "briefs": briefs}


def where(brand):
    return REPO / "runs" / "meta-upload" / brand / "directory.json"


def write(d):
    f = where(d["brand"])
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    (f.parent / "DIRECTORY.md").write_text(markdown(d))
    return f


def load(brand, max_age_h=MAX_AGE_H):
    """The directory, rebuilt from the warehouse when older than max_age_h (a stale copy is used, flagged, when the
    warehouse can't be reached). None when there is none at all."""
    f = where(brand)
    d = json.loads(f.read_text()) if f.is_file() else None
    old = not d or datetime.fromisoformat(d["made"]) < datetime.now() - timedelta(hours=max_age_h)
    if old:
        try:
            d = build(brand)
            write(d)
        except Exception as e:  # noqa: BLE001 — no warehouse: the last directory, marked stale
            if d:
                d["stale"] = str(e)[:200]
    return d


def campaign_for_funnel(brand, funnel):
    """(campaign, why) for a funnel id from the directory, or (None, None) when there is no directory."""
    d = load(brand)
    if not d or funnel not in (d.get("funnels") or {}):
        return None, None
    x = d["funnels"][funnel]
    return x["campaign"], (None if x["campaign"] else "no campaign: " + x["why"])


def markdown(d):
    out = ["# Ad directory · %s" % d["brand"], "", "Made %s from %s." % (d["made"], d["source"]), "",
           "## Funnel → campaign", "", "| Funnel | Campaign | Why |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % (k, v["campaign"] or "—", v["why"]) for k, v in sorted(d["funnels"].items())]
    out += ["", "## Campaigns", "", "| Campaign | Live | Spend 7d | Spend 30d | Active ads | Pages |", "|---|---|---|---|---|---|"]
    out += ["| %s | %s | %s | %s | %s | %s |" % (c["name"], "yes" if c["live"] else "no", c["spend7"], c["spend30"], c["active_ads"],
                                              ", ".join(c["pages"])) for c in d["campaigns"] if c["live"] or c["spend30"] > 0]
    out += ["", "## Ad sets", "", "| Ad set | Campaign | Live | Spend 7d |", "|---|---|---|---|"]
    out += ["| %s | %s | %s | %s |" % (s["name"], s["campaign"], "yes" if s["live"] else "no", s["spend7"]) for s in d["ad_sets"] if s["live"]]
    out += ["", "## Pages", "", "| Page | Funnel | Campaign |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % (p["link_id"], p["funnel"] or "—", p["campaign"] or "— " + p["why"]) for p in d["pages"]]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    d = build(a.brand)
    f = write(d)
    print(markdown(d) if a.show else f)
