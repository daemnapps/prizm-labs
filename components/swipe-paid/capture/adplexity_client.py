#!/usr/bin/env python3
"""Thin AdPlexity Social API client — internal tool, stdlib only.

Auth: ADPLEXITY_API_KEY from the environment, else the macOS Keychain.
Base: https://app.adplexity.io/api/v2, header X-API-Key.
Docs: https://app.adplexity.io/docs/api/v2

CREDITS ARE PER AD RETURNED (verified live: meta.credits_cost = items+1),
NOT per request. `count` defaults to 100 server-side — ALWAYS pass a small
count. 5,000/mo, no rollover. Dictionary endpoints are free. Max date range
30 days. Every call logs to scan_runs.

Real params (from swagger.yml, saved alongside): search_query + search_mode
(keyword.ad | keyword.lp | keyword.ad_or_lp | keyword.lp_summary |
advertiser.lp_host | advertiser.lp_url_redirect_outbound | ...),
country=US,GB csv, vertical/affiliate_network/technology/tracking_tools =
dictionary IDs csv, days_running_from/to, order (newest | days_desc),
offset/count.

Usage:
  python3 adplexity_client.py smoke                 # dictionary call (free)
  python3 adplexity_client.py search "<query>" [--mode keyword.ad_or_lp]
          [--country US] [--count 10] [--days-from N] [--order days_desc]
  python3 adplexity_client.py lps "<query>" [...]   # search landing pages
  python3 adplexity_client.py ad <ad_id>            # full ad detail → ads table
  python3 adplexity_client.py lp <lp_id>            # LP detail → landing_pages table
"""
import json, os, re, sqlite3, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone


def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "market.db")
BASE = "https://app.adplexity.io/api/v2"

def _key():
    """The key by NAME, never by a path to somebody's file.

    It used to be read out of a .env beside the old research folder. That file
    is a tombstone now — every key moved to the macOS Keychain on 2026-09-11 —
    so the order is: the environment, then the Keychain.
    """
    k = os.environ.get("ADPLEXITY_API_KEY")
    if k:
        return k
    k = _shared_keys().lookup("ADPLEXITY_API_KEY", required=True)
    return k

def call(path, params=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-API-Key": _key(),
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return None, str(e)

def _db(path=None):
    """market.db is gitignored, so a fresh clone has no scan_runs until this
    makes it. Columns are the ones this folder's INSERTs and UPDATEs write."""
    con = sqlite3.connect(path or DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS scan_runs (run_id INTEGER PRIMARY KEY,"
        " ran_at TEXT, source TEXT, query_json TEXT, region TEXT,"
        " items_returned INTEGER, cost_usd REAL, apify_run_id TEXT,"
        " dataset_id TEXT, purpose TEXT, notes TEXT, completeness_ratio REAL)")
    return con

def log_run(source, query, items, notes, purpose="competitor"):
    con = _db()
    con.execute(
        "INSERT INTO scan_runs (ran_at, source, query_json, region, items_returned,"
        " purpose, notes) VALUES (?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), source, json.dumps(query),
         query.get("country") if isinstance(query, dict) else None,
         items, purpose, notes))
    con.commit()
    return con

def cmd_smoke():
    data, err = call("/dictionary/countries")
    if err:
        # some deployments name dictionary endpoints differently; try a sibling
        data, err = call("/dictionary/verticals")
    if err:
        sys.exit(f"SMOKE FAILED — {err}")
    n = len(data if isinstance(data, list) else data.get("data", data.get("items", [])))
    log_run("adplexity /dictionary", {"endpoint": "dictionary"}, n,
            "Smoke test: key valid, dictionary endpoint reachable.", "validation")
    print(f"SMOKE OK — key valid, {n} dictionary entries returned.")

def _search(endpoint, q, mode, country, count, days_from, order):
    from datetime import timedelta
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=29)  # max range is 30 days
    params = {"start_date": start.isoformat(), "end_date": end.isoformat(),
              "search_query": q, "search_mode": mode, "country": country,
              "count": count}
    if days_from:
        params["days_running_from"] = days_from
    if order:
        params["order"] = order
    data, err = call(endpoint, params)
    if err:
        sys.exit(f"SEARCH FAILED — {err}")
    items = data.get("data", []) if isinstance(data, dict) else data
    cost = (data.get("meta") or {}).get("credits_cost") if isinstance(data, dict) else None
    con = log_run(f"adplexity {endpoint}", params, len(items),
                  f"credits_cost={cost}")
    con.execute("UPDATE scan_runs SET cost_usd=? WHERE run_id=last_insert_rowid()",
                ((cost or 0) * 99.0 / 5000,))
    con.commit()
    print(json.dumps(items[:5], indent=2)[:3500])
    print(f"\n{len(items)} items · credits spent: {cost} · pull details with "
          f"`ad <id>` / `lp <id>` (1 credit each).")

def cmd_search(q, mode="keyword.ad_or_lp", country="US", count=10,
               days_from=None, order=None):
    _search("/search/ads", q, mode, country, count, days_from, order)

ECOM_VERTICALS = "54,57,58"  # E-commerce, Ecommerce, Retail (dictionary/verticals)

def cmd_momentum(q=None, country="US", count=10, days_from=14,
                 max_countries=1, vertical=ECOM_VERTICALS, offset=0):
    """Momentum ads: live >= days_from days, grouped by creative, sorted by
    how many ads run the same creative (variant replication = conviction).
    Impressions/spend/clicks do NOT exist in this API (Meta doesn't publish
    them for commerce ads) — days-running x variant-count is the proxy.

    US-ONLY BY DEFAULT (the owner, 2026-08-18): country=US AND
    countries_count_to=1 — the ad runs in the United States and nowhere
    else. International spray campaigns are noise; raise --max-countries
    deliberately if ever needed."""
    from datetime import timedelta
    end = datetime.now(timezone.utc).date()
    params = {"start_date": (end - timedelta(days=29)).isoformat(),
              "end_date": end.isoformat(), "country": country, "count": count,
              "days_running_from": days_from, "meta_grouping_id": 2,
              "countries_count_to": max_countries, "offset": offset,
              "order": "grouped_ads_desc"}
    if vertical:
        params["vertical"] = vertical
    # NOTE: do NOT default language=en — verified 2026-08-18 that it collapses
    # results to a small old big-brand subset (their language detection only
    # covers part of the index) and loses the real momentum ads. Eyeball the
    # occasional foreign-language row out instead.
    if q:
        params["search_query"] = q
        params["search_mode"] = os.environ.get("APX_MODE", "keyword.ad_or_lp")
    data, err = call("/search/ads", params)
    if err:
        sys.exit(f"MOMENTUM FAILED — {err}")
    items = data.get("data", [])
    cost = (data.get("meta") or {}).get("credits_cost")
    con = log_run("adplexity momentum /search/ads", params, len(items),
                  f"credits_cost={cost}", "competitor")
    con.execute("UPDATE scan_runs SET cost_usd=? WHERE run_id=last_insert_rowid()",
                ((cost or 0) * 99.0 / 5000,))
    con.commit()
    raw_dir = os.path.join(HERE, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    end_s = end.isoformat()
    import hashlib
    sig = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:6]
    raw_path = os.path.join(raw_dir, f"momentum_{end_s}_off{offset}_{sig}.json")
    json.dump({"params": params, "credits_cost": cost, "items": items},
              open(raw_path, "w"), indent=1)
    print(f"raw saved: {raw_path}")
    print(f"{'variants':>8}  {'id':>10}  title")
    for a in items:
        print(f"{a.get('meta_group_ads_count','?'):>8}  {a.get('id'):>10}  "
              f"{(a.get('title') or '')[:58]}")
    print(f"\n{len(items)} momentum ads (live ≥{days_from}d, most-replicated "
          f"creative first) · credits spent: {cost}")
    _credits_status(con)

def cmd_advertiser(domain, mode="advertiser.lp_url_redirect_outbound",
                   country=None, count=25, offset=0, order="first_seen",
                   grouping=2, days=30, pages=1, days_running=None):
    """Sweep one advertiser's whole live library by their domain.

    Mirrors the AdPlexity UI advertiser search:
      sm=ad & qs=advertiser.lp_url_redirect_outbound & q=<domain>
      & order=first_seen & mg=2 & from=-30d

    NO country filter by default — an advertiser sweep wants their entire
    footprint, unlike momentum scans which are deliberately US-only.
    mg=2 groups by creative, so each row is a distinct creative and
    meta_group_ads_count = how many ad variants run it (conviction signal).
    order=first_seen ascending shows the creative genealogy: what they
    launched first, what they layered on.
    """
    from datetime import timedelta
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=min(days, 29))
    slug = re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-")
    raw_dir = os.path.join(HERE, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    all_items, total_cost = [], 0
    for page in range(pages):
        off = offset + page * count
        params = {"start_date": start.isoformat(), "end_date": end.isoformat(),
                  "search_query": domain, "search_mode": mode,
                  "count": count, "offset": off, "order": order}
        if grouping:
            params["meta_grouping_id"] = grouping
        if country:
            params["country"] = country
        if days_running:  # the UI's "days=N" filter: live at least N days
            params["days_running_from"] = days_running
        data, err = call("/search/ads", params)
        if err:
            print(f"ADVERTISER FAILED at offset {off} — {err}")
            break
        items = data.get("data", []) if isinstance(data, dict) else (data or [])
        cost = ((data.get("meta") or {}).get("credits_cost") or 0) if isinstance(data, dict) else 0
        total_cost += cost
        con = log_run("adplexity advertiser /search/ads", params, len(items),
                      f"credits_cost={cost} domain={domain}", "competitor")
        con.execute("UPDATE scan_runs SET cost_usd=? WHERE run_id=last_insert_rowid()",
                    (cost * 99.0 / 5000,))
        con.commit()
        json.dump({"params": params, "credits_cost": cost, "items": items},
                  open(os.path.join(raw_dir,
                       f"advertiser_{slug}_{end.isoformat()}_off{off}.json"), "w"),
                  indent=1)
        all_items.extend(items)
        if len(items) < count:
            break
    combined = os.path.join(raw_dir, f"advertiser_{slug}_{end.isoformat()}_ALL.json")
    json.dump({"domain": domain, "mode": mode, "order": order,
               "grouping": grouping, "window": [start.isoformat(), end.isoformat()],
               "credits_cost": total_cost, "count": len(all_items),
               "items": all_items}, open(combined, "w"), indent=1)
    print(f"raw saved: {combined}")
    print(f"{'vars':>5}  {'type':>4}  {'id':>10}  title")
    for a in all_items:
        print(f"{a.get('meta_group_ads_count','-'):>5}  "
              f"{a.get('meta_ad_type','-'):>4}  {a.get('id'):>10}  "
              f"{((a.get('title') or a.get('description') or '') or '')[:60]}")
    print(f"\n{len(all_items)} creatives for {domain} · credits spent: {total_cost}")
    _credits_status()


def _credits_status(con=None):
    con = con or _db()
    usd = con.execute("SELECT COALESCE(sum(cost_usd),0) FROM scan_runs WHERE"
                      " source LIKE 'adplexity%'").fetchone()[0]
    logged = round(usd * 5000 / 99.0)
    print(f"credit ledger (logged by this client): ~{logged} used. NOTE: "
          f"~700–800 discovery-probe credits from 2026-08-18 predate logging —"
          f" true remaining ≈ {5000 - logged - 750} of 5,000. Dashboard is the"
          f" source of truth.")

def cmd_credits():
    _credits_status()

def cmd_lps(q, mode="keyword.lp", country="US", count=10,
            days_from=None, order=None):
    _search("/search/lps", q, mode, country, count, days_from, order)

def cmd_ad(ad_id):
    data, err = call(f"/ads/{ad_id}")
    if err:
        sys.exit(f"AD FAILED — {err}")
    a = data.get("data", data) if isinstance(data, dict) else data
    raw_dir = os.path.join(HERE, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json.dump(a, open(os.path.join(raw_dir, f"ad_{ad_id}.json"), "w"), indent=1)
    lps = a.get("landing_pages") or []
    lp_url = (lps[0].get("url") if lps else None) or a.get("link_url")
    con = log_run(f"adplexity /ads/{ad_id}", {"ad_id": ad_id}, 1, "Full ad detail.")
    con.execute(
        """INSERT OR REPLACE INTO ads (ad_archive_id, page_id, primary_text,
           headline, outbound_url, snapshot_url, is_active, first_seen, last_seen,
           media_urls_json)
           VALUES (?,?,?,?,?,?,?,COALESCE((SELECT first_seen FROM ads WHERE
           ad_archive_id=?), datetime('now')), datetime('now'), ?)""",
        (f"apx:{ad_id}", str(a.get("brand_id") or a.get("page_id") or ""),
         a.get("description") or a.get("body"), a.get("title") or a.get("headline"),
         lp_url,
         a.get("video_url") or a.get("image_url"),
         1 if a.get("live", a.get("status")) in (1, True, "active") else 0,
         f"apx:{ad_id}", json.dumps(a.get("media") or a.get("images") or [])))
    con.commit()
    print(json.dumps(a, indent=2)[:3000])
    print("\nSaved to ads table.")

def cmd_lp(lp_id):
    data, err = call(f"/lps/{lp_id}")
    if err:
        sys.exit(f"LP FAILED — {err}")
    lp = data.get("data", data) if isinstance(data, dict) else data
    con = log_run(f"adplexity /lps/{lp_id}", {"lp_id": lp_id}, 1, "LP detail.")
    con.execute(
        """INSERT INTO landing_pages (url, captured_at, viewport, screenshot_path,
           html_path, stack_json, capture_session)
           VALUES (?, datetime('now'), 'mobile', ?, ?, ?, 1)""",
        (lp.get("url"), lp.get("screenshot_url"), lp.get("archive_url"),
         json.dumps({"redirects": lp.get("redirects"),
                     "technologies": lp.get("technologies"),
                     "tracking_tools": lp.get("tracking_tools"),
                     "affiliate_networks": lp.get("affiliate_networks")})))
    con.commit()
    print(json.dumps(lp, indent=2)[:3000])
    print("\nSaved to landing_pages table (redirect chain + stack in stack_json).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "smoke":
        cmd_smoke()
    elif cmd in ("search", "lps"):
        kw = sys.argv[2]
        def opt(flag, default, cast=str):
            return cast(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
        fn = cmd_search if cmd == "search" else cmd_lps
        fn(kw,
           mode=opt("--mode", "keyword.ad_or_lp" if cmd == "search" else "keyword.lp"),
           country=opt("--country", "US"),
           count=opt("--count", 10, int),
           days_from=opt("--days-from", None, int),
           order=opt("--order", None))
    elif cmd == "momentum":
        def opt(flag, default, cast=str):
            return cast(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
        q = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        cmd_momentum(q, country=opt("--country", "US"),
                     count=opt("--count", 10, int),
                     days_from=opt("--days-from", 14, int),
                     max_countries=opt("--max-countries", 1, int),
                     vertical=opt("--vertical", ECOM_VERTICALS),
                     offset=opt("--offset", 0, int))
    elif cmd == "advertiser":
        def opt(flag, default, cast=str):
            return cast(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
        cmd_advertiser(sys.argv[2],
                       mode=opt("--mode", "advertiser.lp_url_redirect_outbound"),
                       country=opt("--country", None),
                       count=opt("--count", 25, int),
                       offset=opt("--offset", 0, int),
                       order=opt("--order", "first_seen"),
                       grouping=opt("--grouping", 2, int),
                       days=opt("--days", 30, int),
                       pages=opt("--pages", 1, int),
                       days_running=opt("--days-running", None, int))
    elif cmd == "credits":
        cmd_credits()
    elif cmd == "ad":
        cmd_ad(sys.argv[2])
    elif cmd == "lp":
        cmd_lp(sys.argv[2])
    else:
        sys.exit(__doc__)
