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

def key(n="APIFY_TOKEN"):
    if os.environ.get(n):
        return os.environ[n]
    r = subprocess.run(["security","find-generic-password","-a","damon","-s",f"daemn-{n}","-w"],
                       capture_output=True, text=True)
    if r.returncode: raise SystemExit(f"no keychain entry daemn-{n}")
    return r.stdout.strip()

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
