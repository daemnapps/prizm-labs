#!/usr/bin/env python3
"""Derive the calendar's numbers straight from Klaviyo's REST API.

    python3 derive.py --brand brand-b [--months 24]

Why this exists rather than the MCP connector: the one call that returns
monthly order totals (`/api/metric-aggregates`) needs a structured request
body, and the connector only accepts flat text arguments — the call cannot be
made through it. Pulling the same data order-by-order works but takes roughly
a hundred separate requests for two years, which is not a sensible way to ask
a question. This is the fallback the developer wrote down on 2026-08-14 as option 2,
and its kill-condition has now fired.

Produces, per brand:

  the year   — orders and revenue by month, as far back as the data goes
  the week   — orders by day of week, 90 days
  the day    — orders by hour, 90 days, and the contiguous buy window
  the ledger — every campaign subject already sent, with its date

Reads only. Nothing here writes to Klaviyo.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.append(str(Path(__file__).resolve().parent.parent))
from paths import run_home, refuse_brand_write  # noqa: E402

API = "https://a.klaviyo.com/api"
REVISION = "2025-07-15"

# Accounts are DATA, in accounts.json — lab rule 7: no build hard-codes a
# brand. Adding a brand is adding a row there, not editing this file.
def _accounts():
    f = Path(__file__).resolve().parent / "accounts.json"
    if not f.is_file():
        sys.exit(f"no account map at {f}")
    raw = json.loads(f.read_text())["brands"]
    return {k: dict(account=v["account"], tz=v["timezone"],
                    placed_order=v["placed_order"]) for k, v in raw.items()}


BRANDS = _accounts()


def key_for(brand):
    """The private key, from the ENVIRONMENT only — `KLAVIYO_<BRAND>_KEY`.
    A key read off a file path is a wall (the-org, 2026-09-21), so the old
    ~/.config/daemn/klaviyo-<brand>.key fallback is gone (FOLD Y4c, 2026-09-23)."""
    name = f"KLAVIYO_{brand.upper()}_KEY"
    env = os.environ.get(name)
    if env and env.strip():
        return env.strip()
    sys.exit(
        f"no Klaviyo key for {brand}: set {name} in your environment.\n"
        f"  (Klaviyo → Settings → API keys → Create private key → read-only)")


def get(path, key, **params):
    q = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v)
    url = f"{API}/{path}/" + (f"?{q}" if q else "")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Klaviyo-API-Key {key}",
        "revision": REVISION, "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def post(path, key, body):
    req = urllib.request.Request(
        f"{API}/{path}/", method="POST",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Klaviyo-API-Key {key}",
                 "revision": REVISION, "accept": "application/json",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def aggregate(key, metric, interval, since, until, tz):
    """The call the connector cannot make.

    Klaviyo refuses any range over a year, so a longer ask is split into
    year-long windows and stitched. Discovered on the first real run — the
    two-year request came back 400, not truncated, which is the better
    failure of the two.
    """
    out = {}
    lo = since.replace(day=1)
    while lo < until:
        # Align every window to a month start. A window that ends mid-month
        # splits that month across two calls, and the second call's partial
        # figure then overwrites the first — which showed up as a month of
        # near-zero orders that moved when the range changed. Caught
        # 2026-08-27, before it reached a page.
        hi = lo.replace(year=lo.year + 1)
        hi = min(until, hi)
        for d, v in _aggregate_one(key, metric, interval, lo, hi, tz).items():
            cur = out.setdefault(d, {"orders": 0, "revenue": 0})
            cur["orders"] += v["orders"]
            cur["revenue"] += v["revenue"]
        lo = hi
    return out


def _aggregate_one(key, metric, interval, since, until, tz):
    body = {"data": {"type": "metric-aggregate", "attributes": {
        "metric_id": metric,
        "measurements": ["count", "sum_value"],
        "interval": interval,
        "timezone": tz,
        "filter": [f"greater-or-equal(datetime,{since:%Y-%m-%dT00:00:00})",
                   f"less-than(datetime,{until:%Y-%m-%dT00:00:00})"],
    }}}
    r = post("metric-aggregates", key, body)
    a = r["data"]["attributes"]
    dates = a["dates"]
    out = {}
    for row in a["data"]:
        m = row["measurements"]
        for i, d in enumerate(dates):
            out.setdefault(d, {})
            out[d]["orders"] = out[d].get("orders", 0) + (m.get("count") or [0] * len(dates))[i]
            out[d]["revenue"] = out[d].get("revenue", 0) + (m.get("sum_value") or [0] * len(dates))[i]
    return out


def bar(v, mx, w=30):
    return "#" * (round(w * v / mx) if mx else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--months", type=int, default=24)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.brand not in BRANDS:
        sys.exit(f"unknown brand: {args.brand} (known: {', '.join(BRANDS)})")
    b = BRANDS[args.brand]
    key = key_for(args.brand)
    tz = ZoneInfo(b["tz"])
    now = datetime.now(tz)
    L = []

    def say(s=""):
        print(s)
        L.append(s)

    say(f"# {args.brand} — derived {now:%Y-%m-%d}")
    say(f"\nKlaviyo account `{b['account']}` · orders from metric `{b['placed_order']}`")
    say(f"· timezone {b['tz']} · reads only.\n")

    # --- the year ---------------------------------------------------------
    say("## The year")
    since = (now - timedelta(days=31 * args.months)).replace(day=1)
    try:
        months = aggregate(key, b["placed_order"], "month", since, now + timedelta(days=1), b["tz"])
    except urllib.error.HTTPError as e:
        say(f"\ncould not read the monthly curve: HTTP {e.code} {e.read()[:200]!r}")
        months = {}
    if months:
        mx = max(v["orders"] for v in months.values())
        say("\n```")
        for d in sorted(months):
            v = months[d]
            say(f"{d[:7]}  {v['orders']:6.0f} orders  ${v['revenue']:10,.0f}  {bar(v['orders'], mx)}")
        say("```")
        say(f"\n{len(months)} months of history. A season has to appear twice before")
        say("it is a season — with fewer than 24 months, say so rather than calling")
        say("a single peak a pattern.")

    # --- the week and the day --------------------------------------------
    say("\n## The week and the day")
    d90 = now - timedelta(days=90)
    try:
        daily = aggregate(key, b["placed_order"], "day", d90, now + timedelta(days=1), b["tz"])
        hourly = aggregate(key, b["placed_order"], "hour", d90, now + timedelta(days=1), b["tz"])
    except urllib.error.HTTPError as e:
        say(f"\ncould not read: HTTP {e.code}")
        daily = hourly = {}

    if daily:
        dow = Counter()
        for d, v in daily.items():
            dow[datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(tz).strftime("%a")] += v["orders"]
        mx = max(dow.values())
        say("\n```")
        for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            say(f"{d}  {dow[d]:6.0f}  {bar(dow[d], mx)}")
        say("```")
        rank = sorted(dow.items(), key=lambda x: -x[1])
        say(f"\nBest days: {', '.join(k for k, _ in rank[:4])}. "
            f"Slow: {', '.join(k for k, _ in rank[-2:])}.")

    if hourly:
        hr = Counter()
        for d, v in hourly.items():
            hr[datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(tz).hour] += v["orders"]
        mx = max(hr.values())
        say("\n```")
        for h in range(24):
            say(f"{h:02d}  {hr[h]:6.0f}  {bar(hr[h], mx)}")
        say("```")
        # the best contiguous 3-hour block, not the best single hour: one
        # freak hour should never decide a send time
        best = max(range(22), key=lambda h: hr[h] + hr[h + 1] + hr[h + 2])
        say(f"\nBuy window: {best:02d}:00–{best+3:02d}:00. "
            f"Send ~{max(0, best - 2):02d}:00–{max(0, best - 1):02d}:00 "
            "— an hour or two ahead of it.")

    # --- the ledger -------------------------------------------------------
    say("\n## Subject lines already sent")
    say("\nThe ledger stage 5 of the email lane asks for. Anything on this list")
    say("is ground already spent.\n")
    try:
        r = get("campaigns", key,
                **{"filter": "equals(messages.channel,'email')",
                   "sort": "-created_at"})
        rows = [(c["attributes"].get("send_time") or "", c["attributes"]["name"])
                for c in r.get("data", []) if c["attributes"]["status"] == "Sent"]
        say("```")
        for t, n in sorted(rows, reverse=True):
            say(f"{t[:10]}  {n}")
        say("```")
        say(f"\n{len(rows)} sent campaigns on this page. The campaign name is not")
        say("always the subject line — where they differ, the subject is on the")
        say("message and has to be pulled per campaign.")
    except urllib.error.HTTPError as e:
        say(f"could not read campaigns: HTTP {e.code}")

    # email-production#19: a derive is a run, filed beside the chain's runs
    out = refuse_brand_write(Path(args.out)) if args.out else run_home(args.brand, "derived-" + datetime.now(timezone.utc).strftime("%Y-%m-%d")) / f"{args.brand}-derived.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print(f"\nwritten -> {out}", file=sys.stderr)


if __name__ == "__main__":
    import urllib.parse
    main()
