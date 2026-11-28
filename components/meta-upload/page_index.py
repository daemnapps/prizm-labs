#!/usr/bin/env python3
"""Which Facebook Page each live ad runs from, and the spend per Page. Never calls Meta.

The ad name says the brief, batch and funnel; it never says the Page (2026-11-28). A brand can run ads from more
than one Facebook Page (the account file's `fb_pages`), so the Page an ad runs from is recorded with its ad id when
it goes in, and read back here:

  1. the upload record   live.jsonl in the approval tree, and each live card's `meta` rows: ad id -> Page
                         (a copied ad runs from the Page of the ad it was copied from)
  2. an older name       ads uploaded 21-28 Nov carried `_p-<tag>` for a Page other than the brand's own;
                         the tag is read through the account file
  3. otherwise           the brand's own Page (the default in the account file); marked "by default"

    page_index.py <brand> [warehouse.json]     spend per Page, last 7 and 30 days, from the newest warehouse copy
"""
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

TAG = re.compile(r"_p-([a-z0-9-]+)$")


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def pages(brand):
    """The brand's Facebook Pages: [{"id", "name", "tag", "default"}] from brands/<brand>/meta/account.json."""
    d = _read(REPO / "brands" / brand / "meta" / "account.json") or {}
    rows = d.get("fb_pages") or ([{"id": str(d["page_id"]), "name": d.get("page_name"), "tag": "", "default": True}]
                                 if d.get("page_id") else [])
    return [{"id": str(r.get("id")), "name": r.get("name"), "tag": r.get("tag") or "",
             "default": bool(r.get("default")) or str(r.get("id")) == str(d.get("page_id"))} for r in rows]


def recorded(brand, live=None):
    """ad id -> {"fb_page", "fb_page_name"} from the upload records."""
    out, copied = {}, {}
    rows = []
    try:
        if live is None:
            import cards as C
            live = C.root() / "live.jsonl"
        for line in Path(live).read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        import cards as C
        for f in C.listing(state="3-live", brand=brand):
            rows += [dict(r, brand=brand) for r in (C.load(f) or {}).get("meta") or []]
    except (OSError, SystemExit, Exception):  # noqa: BLE001 — no approval tree here: fall through to the names
        pass
    for r in rows:
        if r.get("brand") not in (None, brand) or not r.get("ad_id"):
            continue
        if r.get("fb_page"):
            out[str(r["ad_id"])] = {"fb_page": str(r["fb_page"]), "fb_page_name": r.get("fb_page_name")}
        elif r.get("copied_from"):
            copied[str(r["ad_id"])] = str(r["copied_from"])
    for new, old in copied.items():
        if old in out and new not in out:
            out[new] = out[old]
    return out


def page_of(ad_id, ad_name, pg, rec):
    """{"fb_page", "fb_page_name", "by": "record" | "name" | "default"} for one ad."""
    hit = rec.get(str(ad_id))
    if hit:
        name = hit.get("fb_page_name") or next((p["name"] for p in pg if p["id"] == hit["fb_page"]), None)
        return {"fb_page": hit["fb_page"], "fb_page_name": name, "by": "record"}
    m = TAG.search((ad_name or "").strip())
    if m:
        p = next((p for p in pg if p["tag"] == m.group(1) or p["id"].endswith(m.group(1))), None)
        if p:
            return {"fb_page": p["id"], "fb_page_name": p["name"], "by": "name"}
    p = next((p for p in pg if p["default"]), pg[0] if pg else None)
    return {"fb_page": p and p["id"], "fb_page_name": p and p["name"], "by": "default"}


def index(brand, ads, live=None):
    """[warehouse ad rows] -> ad id -> Page."""
    pg, rec = pages(brand), recorded(brand, live)
    return {str(a.get("ad_id")): page_of(a.get("ad_id"), a.get("ad_name"), pg, rec) for a in ads}


def spend(brand, ads, live=None):
    """Spend and buys per Page: [{"fb_page", "fb_page_name", "ads", "spend7", "buys7", "spend30", "buys30", "by"}]."""
    ix = index(brand, ads, live)
    num = lambda v: float(v) if v not in (None, "") else 0.0  # noqa: E731
    out = {}
    for a in ads:
        p = ix[str(a.get("ad_id"))]
        g = out.setdefault(p["fb_page"], {"fb_page": p["fb_page"], "fb_page_name": p["fb_page_name"], "ads": 0,
                                          "spend7": 0.0, "buys7": 0.0, "spend30": 0.0, "buys30": 0.0, "by": {}})
        g["ads"] += 1
        g["by"][p["by"]] = g["by"].get(p["by"], 0) + 1
        for k in ("spend7", "buys7", "spend30", "buys30"):
            g[k] = round(g[k] + num(a.get(k)), 2)
    return sorted(out.values(), key=lambda g: -g["spend30"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    brand = sys.argv[1]
    wf = sys.argv[2] if len(sys.argv) > 2 else (sorted(glob.glob(str(REPO / "runs/funnel-tracking" / brand / "2*/warehouse.json"))) or [None])[-1]
    ads = (_read(wf) or {}).get("ads") or [] if wf else []
    for g in spend(brand, ads):
        print("%-22s %3d ads  $%9.2f 30d  %4d buys  $%8.2f 7d  (%s)" % (
            g["fb_page_name"], g["ads"], g["spend30"], g["buys30"], g["spend7"],
            ", ".join("%d by %s" % (n, k) for k, n in sorted(g["by"].items()))))
