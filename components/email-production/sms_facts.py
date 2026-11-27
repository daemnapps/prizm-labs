#!/usr/bin/env python3
"""What a brand's SMS list holds, read-only, from whichever platform the brand names (2026-11-04).

    python3 sms_facts.py --brand <brand> [--max-pages N]

The platform is the brand's own record: brands/<brand>/operations/brand.json `sms_platform`. The key is
read by NAME through components/keys (`KLAVIYO_<BRAND>_KEY`, `POSTSCRIPT_<BRAND>_KEY`), never a path.
Only GET requests; nothing is sent, scheduled or changed on any platform. Only COUNTS are kept — no phone
number, email or name is written anywhere.

- klaviyo: every list and segment whose name says SMS or text, with its profile count; the SMS campaigns
  on file (how many, sent, the latest send date).
- postscript: every subscriber record, paged through the API (25 a page), counted in all and by
  promotional `can_send`; the oldest record's date. Postscript's public API has no campaigns endpoint
  (404 on every path tried, 2026-11-04), so past campaign results are reported as not readable.

Writes runs/email-production/<brand>/sms-facts/sms-facts.json and sms-facts.md.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from paths import HERE, WORKSPACE

UA = "upright-sms-facts/1.0 (read-only)"      # the platform's edge refuses a request with no agent


def _key(name):
    keys = next((p / "components" / "keys" for p in HERE.parents if (p / "components" / "keys").is_dir()), None)
    if keys and str(keys) not in sys.path:
        sys.path.append(str(keys))
    import loader
    return loader.key(name, required=False)


def platform_of(brand):
    f = WORKSPACE / "brands" / brand / "operations" / "brand.json"
    return (json.loads(f.read_text()).get("sms_platform") if f.is_file() else None) or None


def _get(url, headers):
    req = urllib.request.Request(url, headers=dict(headers, **{"User-Agent": UA, "accept": "application/json"}))
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 * (attempt + 1)); continue
            raise


def postscript(key, get=None, max_pages=None, say=print):
    get = get or (lambda path: _get("https://api.postscript.io" + path, {"Authorization": f"Bearer {key}"}))
    total = can = 0
    oldest, cursor, pages = None, None, 0
    while True:
        page = get("/api/v2/subscribers" + (f"?cursor={urllib.parse.quote(cursor)}" if cursor else ""))
        rows = page.get("subscribers") or []
        total += len(rows)
        can += sum(1 for r in rows if ((r.get("subscriptions") or {}).get("promotional") or {}).get("can_send"))
        for r in rows:
            c = (r.get("created_at") or "")[:10]
            if c and (oldest is None or c < oldest):
                oldest = c
        pages += 1
        if pages % 250 == 0:
            say(f"  … {pages} pages, {total} records")
        cursor = page.get("next_cursor")
        if not cursor or not rows or (max_pages and pages >= max_pages):
            break
    return {"platform": "postscript", "records": total, "promotional_can_send": can,
            "complete": not cursor or not rows, "pages_read": pages, "oldest_record": oldest,
            "campaigns": "not readable: Postscript's public API has no campaigns endpoint (404, 2026-11-04)"}


def klaviyo(brand, key):
    pull = HERE / "pull"
    if str(pull) not in sys.path:
        sys.path.insert(0, str(pull))
    import derive as D
    hdr = {"Authorization": f"Klaviyo-API-Key {key}", "revision": D.REVISION}
    out = {"platform": "klaviyo", "lists": []}
    for kind in ("lists", "segments"):
        url = f"{D.API}/{kind}/?fields[{kind[:-1]}]=name"
        while url:
            page = _get(url, hdr)
            for g in page.get("data") or []:
                name = g["attributes"].get("name") or ""
                if "sms" in name.lower() or "text" in name.lower():
                    one = _get(f"{D.API}/{kind}/{g['id']}/?additional-fields[{kind[:-1]}]=profile_count", hdr)
                    out["lists"].append({"kind": kind[:-1], "name": name,
                                         "profiles": one["data"]["attributes"].get("profile_count")})
            url = (page.get("links") or {}).get("next")
    q = urllib.parse.quote("equals(messages.channel,'sms')")
    url, camps = f"{D.API}/campaigns/?filter={q}&fields[campaign]=status,send_time", []
    while url:
        page = _get(url, hdr)
        camps += page.get("data") or []
        url = (page.get("links") or {}).get("next")
    sent = [c for c in camps if (c["attributes"].get("status") or "").lower() == "sent"]
    out["campaigns"] = {"on_file": len(camps), "sent": len(sent),
                        "latest_send": max((c["attributes"].get("send_time") or "")[:10] for c in sent) if sent else None}
    return out


def read(brand, max_pages=None, say=print):
    plat = platform_of(brand)
    if not plat:
        return {"brand": brand, "platform": None, "state": "no sms_platform in brands/<brand>/operations/brand.json"}
    name = f"{plat.upper()}_{brand.upper().replace('-', '_')}_KEY"
    key = _key(name)
    if not key:
        return {"brand": brand, "platform": plat, "state": f"not readable yet: {name} is empty"}
    try:
        got = postscript(key, max_pages=max_pages, say=say) if plat == "postscript" else klaviyo(brand, key)
    except urllib.error.HTTPError as e:
        return {"brand": brand, "platform": plat, "state": f"not readable: the platform answered {e.code}"}
    return dict(got, brand=brand, state="read", read_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))


def write(brand, facts):
    d = WORKSPACE / "runs" / "email-production" / brand / "sms-facts"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sms-facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    lines = [f"# SMS facts — {brand}", "", f"Platform: {facts.get('platform')} · {facts.get('state')}"
             + (f" · read {facts['read_at'][:10]}" if facts.get("read_at") else ""), ""]
    if facts.get("platform") == "postscript" and facts.get("state") == "read":
        lines += [f"- Subscriber records: {facts['records']:,}" + ("" if facts["complete"] else " (partial read)"),
                  f"- Promotional texts allowed (can_send): {facts['promotional_can_send']:,}",
                  f"- Oldest record: {facts['oldest_record']}", f"- Past campaigns: {facts['campaigns']}"]
    elif facts.get("platform") == "klaviyo" and facts.get("state") == "read":
        lines += [f"- {x['kind']} “{x['name']}”: {x['profiles']} profiles" for x in facts["lists"]] or ["- no list or segment named SMS"]
        c = facts["campaigns"]
        lines += [f"- SMS campaigns on file: {c['on_file']} ({c['sent']} sent; latest {c['latest_send'] or 'none'})",
                  "- A list's size is its members; the platform checks each one's consent at send."]
    (d / "sms-facts.md").write_text("\n".join(lines) + "\n")
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read a brand's SMS list facts, read-only. Never sends.")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--max-pages", type=int, default=None, help="stop paging after N pages (a partial read says so)")
    a = ap.parse_args(argv)
    facts = read(a.brand, a.max_pages)
    d = write(a.brand, facts)
    print((d / "sms-facts.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
