#!/usr/bin/env python3
"""Pull the creators' own organic posts so their proven statics can be read.

Uses the STARTER token, not the personal one — the personal account is at its
monthly cap, which is what the Apify MCP was reaching for.
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

# The creators are private: pass their handles on the command line, or as
# PRIZM_CREATOR_HANDLES="handle,handle".
HANDLES = sys.argv[1:] or [h for h in os.environ.get("PRIZM_CREATOR_HANDLES", "").split(",") if h]
ACTOR = "shu8hvrXbJbY3Eb9W"          # apify/instagram-scraper


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


def key(n="APIFY_TOKEN"):
    return _shared_keys().lookup(n, required=True).strip()

def post(url, body, tok):
    req = urllib.request.Request(f"{url}?token={tok}", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def get(url, tok):
    with urllib.request.urlopen(f"{url}{'&' if '?' in url else '?'}token={tok}", timeout=120) as r:
        return json.load(r)

tok = key()
run = post(f"https://api.apify.com/v2/acts/{ACTOR}/runs", {
    "resultsType":"posts", "resultsLimit":30, "addParentData":True,
    "directUrls":[f"https://www.instagram.com/{h}/" for h in HANDLES]}, tok)["data"]
rid, ds = run["id"], run["defaultDatasetId"]
print(f"run {rid} · dataset {ds}", flush=True)
while True:
    time.sleep(15)
    st = get(f"https://api.apify.com/v2/actor-runs/{rid}", tok)["data"]
    n = get(f"https://api.apify.com/v2/datasets/{ds}", tok)["data"]["itemCount"]
    print(f"  {st['status']} · {n} items", flush=True)
    if st["status"] in ("SUCCEEDED","FAILED","ABORTED","TIMED-OUT"):
        break
items = get(f"https://api.apify.com/v2/datasets/{ds}/items?clean=true&limit=1000", tok)
json.dump(items, open("ig_posts.json","w"))
print(f"DONE {st['status']} · {len(items)} items -> ig_posts.json")
print("usage:", get("https://api.apify.com/v2/users/me/limits", tok)["data"]["current"].get("monthlyUsageUsd"))
