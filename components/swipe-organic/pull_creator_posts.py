#!/usr/bin/env python3
"""Pull the creators' own organic posts so their proven statics can be read.

Uses the STARTER token, not the personal one — the personal account is at its
monthly cap, which is what the Apify MCP was reaching for.
The token is asked by name through so_keys / components/keys/loader.py (environment first).
"""
import importlib.util, json, sys, time, urllib.request, urllib.error
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "so_keys", str(Path(__file__).resolve().parent / "so_keys.py"))
so_keys = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(so_keys)

HANDLES = ["ambrosial_jax","briluv50","danisidor","elenaglow50","glamwithpammie",
           "jodileabeauty","jojo.moran","just_janci","creator-a","lucianapatton",
           "selfcarebykerin","thekeziahaynes","tammysagelessbeauty"]
ACTOR = "shu8hvrXbJbY3Eb9W"          # apify/instagram-scraper

def key(n="APIFY_TOKEN"):
    v = so_keys.key(n)
    if not v: raise SystemExit(so_keys.missing(n))
    return v

def post(url, body, tok):
    req = urllib.request.Request(f"{url}?token={tok}", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def get(url, tok):
    with urllib.request.urlopen(f"{url}{'&' if '?' in url else '?'}token={tok}", timeout=120) as r:
        return json.load(r)

def main():
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

if __name__ == "__main__":
    main()
