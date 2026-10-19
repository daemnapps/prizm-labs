#!/usr/bin/env python3
"""GeeLark cloud phones: check, create, post, schedule — from one command.

    python3 geelark.py doctor                       # keys + account reachable?
    python3 geelark.py check-proxy --proxy-key PROXY_DE_1 --country DE
    python3 geelark.py new-phone --name de-brand-tt-1 --proxy-key PROXY_DE_1 --country DE
    python3 geelark.py phones
    python3 geelark.py post --phone de-brand-tt-1 --platform tiktok \\
        --video clip.mp4 --caption "..." [--at 2026-10-21T18:00]
    python3 geelark.py schedule plan.csv [--dry-run]
    python3 geelark.py status TASK_ID [TASK_ID ...]

Keys come from components/keys/loader.py (environment, then .env). A proxy is
never typed on the command line: put the proxy URL in .env under a name you
choose (e.g. PROXY_DE_1=socks5://user:pass@host:port) and pass that NAME.
No key, proxy password or token is ever printed.

API reference: https://github.com/GeeLark/geelark-openapi (docs/en).
Stdlib only, Python 3.9-clean.
"""
import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = "https://openapi.geelark.com/open/v1"
HERE = Path(__file__).resolve().parent

# GeeLark's RPA posting needs the app in English (task failure 20008), so the
# phone language stays English; the audience country comes from the proxy,
# which the phone's region, time zone and SIM follow.
PHONE_LANGUAGE = "default"
ANDROID = "Android 12"

TASK_STATUS = {1: "waiting", 2: "running", 3: "done", 4: "failed", 7: "cancelled"}
PHONE_STATUS = {0: "on", 1: "starting", 2: "off"}

# The failure codes people actually hit, in plain words (full list in the docs).
FAIL_HINTS = {
    20008: "TikTok's app language was changed — set it back to English and retry.",
    20100: "The phone has no internet — check its proxy.",
    20108: "The phone has no internet — check its proxy.",
    20110: "The proxy didn't answer — it may be expired or out of data.",
    20113: "The proxy isn't changing the phone's IP — check the proxy details.",
    20116: "This account isn't logged in on that phone — log in by hand first.",
    20129: "The phone is offline — start it and retry.",
    20136: "The account is blocked.",
    20137: "The account is blocked (an appeal is possible in the app).",
    20145: "The account has repeated community-guideline strikes.",
    20201: "The video upload failed — usually the proxy is too slow.",
    20204: "TikTok rejected the video upload.",
}


# ---------- keys ----------

def _loader():
    mod = sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in HERE.parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["shared_keys_loader"] = mod
        spec.loader.exec_module(mod)
    return mod


def _key(name, required=True):
    try:
        return _loader().key(name, required=required)
    except KeyError as e:
        sys.exit(str(e).strip("'\""))


def sign_headers(app_id, api_key, trace_id=None, ts=None):
    """GeeLark key verification: SHA256(appId+traceId+ts+nonce+apiKey), upper hex."""
    trace_id = trace_id or str(uuid.uuid4()).upper()
    ts = ts or str(int(time.time() * 1000))
    nonce = trace_id[:6]
    sign = hashlib.sha256((app_id + trace_id + ts + nonce + api_key).encode()).hexdigest().upper()
    return {"appId": app_id, "traceId": trace_id, "ts": ts, "nonce": nonce, "sign": sign}


def auth_headers():
    token = _key("GEELARK_API_TOKEN", required=False)
    if token:
        return {"traceId": str(uuid.uuid4()).upper(), "Authorization": "Bearer " + token}
    app_id = _key("GEELARK_APP_ID", required=False)
    api_key = _key("GEELARK_API_KEY", required=False)
    if not (app_id and api_key):
        sys.exit("This tool needs GEELARK_API_TOKEN (or GEELARK_APP_ID + GEELARK_API_KEY). "
                 "Add it to .env (see .env.example).")
    return sign_headers(app_id, api_key)


# ---------- the API ----------

class GeeLarkError(Exception):
    pass


def call(path, body=None):
    headers = {"Content-Type": "application/json", **auth_headers()}
    req = urllib.request.Request(BASE + path, data=json.dumps(body or {}).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise GeeLarkError(f"GeeLark answered HTTP {e.code} on {path}")
    except urllib.error.URLError as e:
        raise GeeLarkError(f"Couldn't reach GeeLark ({e.reason})")
    if out.get("code") != 0:
        raise GeeLarkError(f"GeeLark said no on {path}: {out.get('code')} {out.get('msg')}"
                           + (f" — {out['data']}" if out.get("data") else ""))
    return out.get("data") or {}


def parse_proxy(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("socks5", "http", "https") or not u.hostname or not u.port:
        sys.exit("That proxy isn't in the form socks5://user:pass@host:port "
                 "(http:// and https:// work too). Fix it in .env.")
    return {"proxyType": u.scheme, "server": u.hostname, "port": u.port,
            "username": urllib.parse.unquote(u.username or ""),
            "password": urllib.parse.unquote(u.password or "")}


def check_proxy(proxy_url):
    p = parse_proxy(proxy_url)
    body = {"proxyQueryChannel": "IP2Location", **{k: v for k, v in p.items() if v}}
    return call("/proxy/check", body)


def phones(**query):
    return call("/phone/list", {"page": 1, "pageSize": 100, **query}).get("items", [])


def find_phone(name_or_id):
    for ph in phones():
        if name_or_id in (ph.get("id"), ph.get("serialName"), ph.get("serialNo")):
            return ph
    sys.exit(f"No cloud phone called '{name_or_id}'. `python3 geelark.py phones` lists them.")


def upload(path):
    """Push a local file to GeeLark's temporary storage; returns its URL."""
    p = Path(path)
    if not p.is_file():
        sys.exit(f"Can't find the file {path}")
    ext = p.suffix.lower().lstrip(".")
    data = call("/upload/getUrl", {"fileType": ext})
    req = urllib.request.Request(data["uploadUrl"], data=p.read_bytes(), method="PUT")
    with urllib.request.urlopen(req, timeout=600) as r:
        if r.status not in (200, 201):
            raise GeeLarkError(f"Upload of {p.name} failed (HTTP {r.status})")
    return data["resourceUrl"]


def media_url(v):
    return v if v.startswith(("http://", "https://")) else upload(v)


def when(at):
    """'' -> now; ISO local time ('2026-10-21T18:00') -> seconds timestamp."""
    if not at:
        return int(time.time())
    return int(datetime.datetime.fromisoformat(at).timestamp())


def post(phone_id, platform, video, caption="", title="", at=""):
    """Create one posting task. Returns the task id."""
    ts = when(at)
    platform = platform.lower()
    if platform == "tiktok":
        item = {"scheduleAt": ts, "envId": phone_id, "video": media_url(video),
                "videoDesc": caption, "needShareLink": True}
        return call("/task/add", {"taskType": 1, "list": [item]})["taskIds"][0]
    if platform == "tiktok-carousel":
        imgs = [media_url(x.strip()) for x in video.split("|") if x.strip()]
        item = {"scheduleAt": ts, "envId": phone_id, "images": imgs,
                "videoDesc": caption, "videoTitle": title[:90], "needShareLink": True}
        return call("/task/add", {"taskType": 3, "list": [item]})["taskIds"][0]
    if platform == "instagram":
        body = {"scheduleAt": ts, "id": phone_id, "description": caption,
                "video": [media_url(video)], "needShareLink": True}
        return call("/rpa/task/instagramPubReels", body)["taskId"]
    if platform == "youtube":
        body = {"scheduleAt": ts, "id": phone_id, "title": (title or caption)[:100],
                "video": media_url(video), "sameStyleVoice": 0, "originalVoice": 100}
        return call("/rpa/task/youtubePubShort", body)["taskId"]
    sys.exit(f"Unknown platform '{platform}' — use tiktok, tiktok-carousel, instagram or youtube.")


# ---------- commands ----------

def cmd_doctor(a):
    ok = True
    if _key("GEELARK_API_TOKEN", required=False):
        print("Keys: GEELARK_API_TOKEN set")
    elif _key("GEELARK_APP_ID", required=False) and _key("GEELARK_API_KEY", required=False):
        print("Keys: GEELARK_APP_ID + GEELARK_API_KEY set")
    else:
        print("Keys: MISSING — add GEELARK_API_TOKEN to .env (GeeLark app > Settings > API)")
        return 1
    try:
        found = phones()
        print(f"GeeLark: connected — {len(found)} cloud phone(s) on the account")
    except GeeLarkError as e:
        print(f"GeeLark: NOT connected — {e}")
        ok = False
    for name in a.proxy_key or []:
        try:
            r = check_proxy(_key(name))
            print(f"Proxy {name}: {'works' if r.get('detectStatus') else 'FAILED'} — "
                  f"{r.get('countryName')}, {r.get('city')} ({r.get('isp')})")
        except GeeLarkError as e:
            print(f"Proxy {name}: NOT working — {e}")
            ok = False
    return 0 if ok else 1


def _proxy_matches(name, country):
    r = check_proxy(_key(name))
    if not r.get("detectStatus"):
        print(f"Proxy {name} didn't connect: {r.get('message') or 'no answer'}")
        return False
    where = f"{r.get('countryName')} ({r.get('countryCode')}), {r.get('city')}, via {r.get('isp')}"
    if country and (r.get("countryCode") or "").upper() != country.upper():
        print(f"Proxy {name} comes out in {where} — not {country.upper()}. "
              "TikTok would see the wrong country; use a proxy from the right country.")
        return False
    print(f"Proxy {name} works: {where}, time zone {r.get('timezone')}")
    return True


def cmd_check_proxy(a):
    return 0 if _proxy_matches(a.proxy_key, a.country) else 1


def cmd_new_phone(a):
    if not _proxy_matches(a.proxy_key, a.country):
        return 1
    row = {"profileName": a.name, "proxyInformation": _key(a.proxy_key),
           "proxyQueryChannel": 2, "mobileLanguage": PHONE_LANGUAGE}
    if a.group:
        row["profileGroup"] = a.group
    if a.tags:
        row["profileTags"] = a.tags
    if a.note:
        row["profileNote"] = a.note
    out = call("/phone/addNew", {"mobileType": ANDROID, "chargeMode": 0, "data": [row]})
    d = (out.get("details") or [{}])[0]
    if d.get("code") not in (0, None):
        print(f"GeeLark didn't create it: {d.get('code')} {d.get('msg')}")
        return 1
    eq = d.get("equipmentInfo") or {}
    print(f"Created cloud phone '{d.get('profileName')}' (id {d.get('id')}): "
          f"{eq.get('deviceBrand', '')} {eq.get('deviceModel', '')}, "
          f"country {eq.get('countryName')}, time zone {eq.get('timeZone')}".replace("  ", " "))
    print("Next: open it in the GeeLark app, install/open the social app, and log in by hand once.")
    return 0


def cmd_phones(a):
    for ph in phones():
        eq = ph.get("equipmentInfo") or {}
        tags = ",".join(t.get("name", "") for t in ph.get("tags") or [])
        print(f"{ph.get('serialName'):<24} id {ph.get('id')}  "
              f"{PHONE_STATUS.get(ph.get('status'), '?'):<8} {eq.get('countryName', ''):<14} "
              f"{(ph.get('group') or {}).get('name', '')} {tags}")
    return 0


def cmd_post(a):
    ph = find_phone(a.phone)
    tid = post(ph["id"], a.platform, a.video, a.caption, a.title, a.at)
    print(f"Queued {a.platform} post on '{ph['serialName']}' — task {tid}. "
          f"Check it with: python3 geelark.py status {tid}")
    return 0


def cmd_schedule(a):
    """CSV columns: phone, platform, video, caption, title, at (title/at optional).
    For tiktok-carousel, put the images in `video` separated by |."""
    rows = list(csv.DictReader(open(a.csv, newline="", encoding="utf-8")))
    by_name = {}
    for ph in phones():
        for k in (ph.get("id"), ph.get("serialName"), ph.get("serialNo")):
            by_name[k] = ph
    bad = [r.get("phone") for r in rows if r.get("phone") not in by_name]
    if bad:
        sys.exit(f"These phones aren't on the GeeLark account: {', '.join(sorted(set(bad)))}")
    done = []
    for i, r in enumerate(rows, 1):
        ph = by_name[r["phone"]]
        label = f"{i}. {r['platform']} on {ph['serialName']} at {r.get('at') or 'now'}"
        if a.dry_run:
            print("would post", label)
            continue
        try:
            tid = post(ph["id"], r["platform"], r["video"], r.get("caption", ""),
                       r.get("title", ""), r.get("at", ""))
            done.append(tid)
            print(f"queued {label} — task {tid}")
        except (GeeLarkError, SystemExit) as e:
            print(f"SKIPPED {label} — {e}")
    if done:
        log = Path(a.csv).with_suffix(".tasks.txt")
        log.write_text("\n".join(done) + "\n")
        print(f"{len(done)} of {len(rows)} queued. Task ids saved to {log.name}; "
              f"check them with: python3 geelark.py status --file {log.name}")
    return 0


def cmd_status(a):
    ids = list(a.ids)
    if a.file:
        ids += [x.strip() for x in Path(a.file).read_text().split() if x.strip()]
    if not ids:
        sys.exit("Give one or more task ids, or --file with the saved ids.")
    for i in range(0, len(ids), 100):
        for t in call("/task/query", {"ids": ids[i:i + 100]}).get("items", []):
            line = f"{t.get('id')}  {TASK_STATUS.get(t.get('status'), '?'):<9} {t.get('serialName')}"
            if t.get("status") == 4:
                code = t.get("failCode")
                line += f"  — {FAIL_HINTS.get(code, t.get('failDesc'))} ({code})"
            if t.get("shareLink"):
                line += f"  {t['shareLink']}"
            print(line)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("doctor", help="are the keys in and is GeeLark reachable?")
    s.add_argument("--proxy-key", nargs="*", help=".env names of proxies to test too")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("check-proxy", help="where does this proxy come out?")
    s.add_argument("--proxy-key", required=True, help=".env name holding the proxy URL")
    s.add_argument("--country", help="2-letter country it must be in, e.g. DE")
    s.set_defaults(fn=cmd_check_proxy)

    s = sub.add_parser("new-phone", help="create one cloud phone behind a checked proxy")
    s.add_argument("--name", required=True)
    s.add_argument("--proxy-key", required=True, help=".env name holding the proxy URL")
    s.add_argument("--country", required=True, help="2-letter country the proxy must be in")
    s.add_argument("--group", help="e.g. the brand")
    s.add_argument("--tags", nargs="*", help="e.g. tiktok de")
    s.add_argument("--note")
    s.set_defaults(fn=cmd_new_phone)

    s = sub.add_parser("phones", help="list the cloud phones")
    s.set_defaults(fn=cmd_phones)

    s = sub.add_parser("post", help="queue one post")
    s.add_argument("--phone", required=True, help="cloud phone name or id")
    s.add_argument("--platform", required=True,
                   choices=["tiktok", "tiktok-carousel", "instagram", "youtube"])
    s.add_argument("--video", required=True, help="file or URL (carousel: images joined by |)")
    s.add_argument("--caption", default="")
    s.add_argument("--title", default="", help="YouTube title / carousel title")
    s.add_argument("--at", default="", help="local time, e.g. 2026-10-21T18:00 (default now)")
    s.set_defaults(fn=cmd_post)

    s = sub.add_parser("schedule", help="queue every row of a plan CSV")
    s.add_argument("csv")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_schedule)

    s = sub.add_parser("status", help="how did these posts go?")
    s.add_argument("ids", nargs="*")
    s.add_argument("--file")
    s.set_defaults(fn=cmd_status)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except GeeLarkError as e:
        print(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
