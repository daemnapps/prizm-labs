#!/usr/bin/env python3
"""TrendTrack door: free checks, capped paid pulls, and sweeps the paid swipe pool can file.

Free:
  python3 components/trendtrack/trendtrack.py check
  python3 components/trendtrack/trendtrack.py lookup "<brand or domain>"
  python3 components/trendtrack/trendtrack.py pages "<brand or domain>"     # the brand's third-party pages

Spends credits (a live query cost 5 for 3 rows; every paid call names a ceiling and stays under it):
  python3 components/trendtrack/trendtrack.py sweep <domain> --slug <competitor> --max-credits 25
  python3 components/trendtrack/trendtrack.py pull /v1/ads/query --body '{"limit":10}' --max-credits 10 --label <label>
"""
import argparse
import datetime
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "components" / "run-kit"))
from run_kit import paths  # noqa: E402

API = "https://api.trendtrack.io"
PAGE_SIZE = 100  # the API's own row limit per call
FIRST_PAGE = 10  # small until the real cost per row is known
RESERVE = 2  # a query cost 2 credits above its row count when tested


class OverCeiling(Exception):
    """A paid call would cost more than the ceiling it was given."""


def _key():
    spec = importlib.util.spec_from_file_location(
        "upright_keys_loader", str(paths.repo() / "components" / "keys" / "loader.py"))
    mod = sys.modules.get("upright_keys_loader")
    if mod is None:
        mod = importlib.util.module_from_spec(spec)
        sys.modules["upright_keys_loader"] = mod
        spec.loader.exec_module(mod)
    k = mod.key("TRENDTRACK_API_KEY", required=False)
    if not k:
        sys.exit("no TRENDTRACK_API_KEY: add it to the keys file")
    return k


def call(path, params=None, body=None, tries=2):
    """One request. Returns (json, credits this call cost, credits left)."""
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={
        "Authorization": "Bearer " + _key(), "User-Agent": "upright-client",
        "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            h = r.headers
            return json.loads(r.read().decode()), float(h.get("X-Usage-Cost") or 0), h.get("X-Credits-Remaining")
    except urllib.error.HTTPError as e:
        if e.code == 429 and tries > 1:
            time.sleep(min(int(e.headers.get("Retry-After") or 5), 60))
            return call(path, params, body, tries - 1)
        sys.exit("TrendTrack answered %s on %s: %s" % (e.code, path, e.read().decode()[:300]))


def rows_to_ask(spent, rows_so_far, ceiling):
    """The rows the next call may ask for without passing the ceiling.

    A live query cost 5 credits for 3 rows, more than 1 per row. So the first call stays
    small, and later calls are sized from the real cost measured so far.
    """
    room = ceiling - spent - RESERVE
    if rows_so_far:
        n = min(PAGE_SIZE, int(room / (spent / float(rows_so_far))))
    else:
        n = min(FIRST_PAGE, room)
    if n < 1:
        raise OverCeiling("stopped under the ceiling of %d credits" % ceiling)
    return n


def to_sweep_item(ad):
    """One TrendTrack ad in the item shape `swipe-paid/build.py cluster` reads."""
    media = ad.get("media") or {}
    content = ad.get("content") or {}
    metrics = ad.get("metrics") or {}
    adv = ad.get("advertiser") or {}
    is_video = media.get("type") == "video"
    return {
        "id": ad["id"],
        "source": "trendtrack",
        "title": content.get("title") or "",
        "description": content.get("body") or "",
        "video_url": (media.get("mediaUrl") or "") if is_video else "",
        "image_url": media.get("thumbnailUrl") or ("" if is_video else media.get("mediaUrl") or ""),
        "landing_page": content.get("landingPageUrl") or None,
        "meta_group_ads_count": metrics.get("duplicates") or 1,
        "meta_page_id": adv.get("facebookPageId") or adv.get("id"),
        "meta_page_name": adv.get("name"),
        "meta_status": ad.get("status"),
        "days_total": ad.get("daysRunning"),
        "first_seen": ad.get("firstSeenAt"),
        "last_seen": ad.get("lastSeenAt"),
        "reach": metrics.get("reach"),
        "reach_change_7d": metrics.get("reachDelta7d"),
        "estimated_spend": metrics.get("estimatedSpend"),
    }


def out_dir(group, label):
    d = paths.repo() / "runs" / "trendtrack" / group / label
    d.mkdir(parents=True, exist_ok=True)
    return d


def record(d, what, spent, left):
    (d / "run.json").write_text(json.dumps({
        "tool": "trendtrack", "what": what, "credits_spent": spent, "credits_left": left,
        "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}, indent=1) + "\n")


def find(q):
    data = call("/v1/lookup", {"q": q, "limit": 1})[0].get("data") or []
    if not data:
        sys.exit("TrendTrack found no match for %r" % q)
    return data[0]


def cmd_check(_):
    u = call("/v1/usage")[0]
    print("connected: %s | plan %s | credits left %s of %s" % (
        u["workspace"]["name"], u["billing"]["planCode"],
        u["credits"]["totalRemaining"], u["includedQuota"]["limit"]))
    print("data current to", call("/v1/system/freshness")[0]["data"]["latestReadyDate"])


def cmd_lookup(a):
    print(json.dumps(call("/v1/lookup", {"q": a.q, "limit": a.limit})[0].get("data"), indent=1))


def cmd_pages(a):
    hit = find(a.q)
    shop = (hit.get("shop") or {}).get("id")
    if not shop:
        sys.exit("%r has no linked shop" % a.q)
    data = call("/v1/lookup/facebook-shop", {"shopId": shop, "limit": a.limit})[0]["data"]
    pages = sorted(data.get("facebookPages") or [], key=lambda p: -(p.get("runningAds") or 0))
    for p in pages:
        print("%6s ads  %-11s %s  (page %s)" % (p.get("runningAds"), p.get("rank"), p.get("name"), p.get("facebookPageId")))
    if len(pages) >= a.limit:
        print("the list stopped at %d pages; there may be more" % a.limit)


def cmd_sweep(a):
    items, seen, spent, left, page = [], set(), 0, None, 1
    try:
        while True:
            limit = rows_to_ask(spent, len(items), a.max_credits)
            body = {"search": [a.domain], "searchType": "domain", "status": a.status, "platforms": ["facebook"],
                    "sortBy": a.sort, "order": "desc", "limit": limit, "page": page}
            res, cost, left = call("/v1/ads/query", body=body)
            spent += cost
            rows = res.get("data") or []
            fresh = [r for r in rows if r["id"] not in seen]
            seen.update(r["id"] for r in fresh)
            items += [to_sweep_item(r) for r in fresh]
            if len(rows) < limit or not fresh:
                break
            page += 1
    except OverCeiling as e:
        print(str(e))
    label = "%s-%s" % (a.slug, datetime.date.today().isoformat())
    d = out_dir("market", label)
    path = d / "ALL.json"
    path.write_text(json.dumps({"source": "trendtrack", "domain": a.domain, "items": items}, indent=1) + "\n")
    record(d, "sweep " + a.domain, spent, left)
    print("%d ads, %g credits spent, %s left" % (len(items), spent, left))
    print("file them: python3 components/swipe-paid/build.py cluster %s %s" % (path.relative_to(paths.repo()), a.slug))


def cmd_pull(a):
    params = dict(p.split("=", 1) for p in a.param)
    body = json.loads(a.body) if a.body else None
    asked = int((body or params).get("limit") or 0)
    if not asked:
        sys.exit("a paid pull names its limit, so the cost is known first")
    if asked + RESERVE > a.max_credits:
        sys.exit("limit %d plus %d credits of overhead is over the ceiling of %d" % (asked, RESERVE, a.max_credits))
    res, cost, left = call(a.path, params or None, body)
    d = out_dir("market", a.label)
    (d / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    record(d, "pull " + a.path, cost, left)
    print("%g credits spent, %s left -> %s" % (cost, left, (d / "result.json").relative_to(paths.repo())))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    p = sub.add_parser("lookup")
    p.add_argument("q")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(fn=cmd_lookup)
    p = sub.add_parser("pages")
    p.add_argument("q")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(fn=cmd_pages)
    p = sub.add_parser("sweep")
    p.add_argument("domain")
    p.add_argument("--slug", required=True)
    p.add_argument("--max-credits", type=int, required=True)
    p.add_argument("--status", default="active")
    p.add_argument("--sort", default="reach")
    p.set_defaults(fn=cmd_sweep)
    p = sub.add_parser("pull")
    p.add_argument("path")
    p.add_argument("--param", action="append", default=[])
    p.add_argument("--body")
    p.add_argument("--max-credits", type=int, required=True)
    p.add_argument("--label", required=True)
    p.set_defaults(fn=cmd_pull)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
