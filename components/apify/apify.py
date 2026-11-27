#!/usr/bin/env python3
"""The Apify layer — one place, four actors, every hard-won fix carried over.

Every non-obvious line here was paid for elsewhere in this workspace and is
kept with its reason:

- **403 means spent, not broken.** A used-up allowance answers 403 to
  everything, indistinguishable from a bad token until you read the account
  limits. A 403 retries once on APIFY_TOKEN_PERSONAL.
- **Apify media lives in a PRIVATE key-value store.** An unsigned request comes
  back 403 and reads exactly like a dead CDN link. Anything on api.apify.com
  gets the token appended.
- **TikTok needs `shouldDownloadVideos`.** Without it the actor returns empty
  mediaUrls and nothing is downloadable.

Keys come from the shared vault the video component already uses, so there is
one place to put a token, not two.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent


def _keys_loader():
    """components/keys/loader.py, loaded by path (never on sys.path), found from this file."""
    import importlib.util
    mod = sys.modules.get("upright_keys_loader")
    if mod is None:
        d = os.path.dirname(os.path.abspath(__file__))
        while not os.path.isfile(os.path.join(d, "components", "keys", "loader.py")):
            if os.path.dirname(d) == d:
                raise RuntimeError("components/keys/loader.py not found above " + __file__)
            d = os.path.dirname(d)
        spec = importlib.util.spec_from_file_location(
            "upright_keys_loader", os.path.join(d, "components", "keys", "loader.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["upright_keys_loader"] = mod
        spec.loader.exec_module(mod)
    return mod


def _vault(name):
    """The key, from wherever this machine keeps it.

    Order (the one key loader, components/keys/loader.py): the environment
    (cloud routines, a teammate's machine, CI), then ~/.upright-keys.env. This
    used to import the video teardown machine's own `keys.py`, which made the
    Apify layer depend on another tool's internals and broke wherever that
    tool was not checked out beside it.
    """
    v = os.environ.get(name)
    if v:
        return v
    try:
        return _keys_loader().key(name, required=False) or None
    except Exception:
        return None

API = "https://api.apify.com/v2"

# IG hashtag pages are gated on the main scraper ("no_items", found 2026-08-30)
# — the dedicated hashtag actor is the door that opens.
POSTS_IG_TAG = "apify~instagram-hashtag-scraper"
POSTS_IG = "apify~instagram-scraper"
POSTS_TT = "clockworks~tiktok-scraper"
PROFILE_IG = "apify~instagram-profile-scraper"
PROFILE_TT = "clockworks~tiktok-profile-scraper"
# The depth comment scrapers. The posts actors return a handful of
# `latestComments` — about 15 of 147 on a real post — which is a sample, not a
# comment section. These read the whole thing.
COMMENTS_IG = "apify~instagram-comment-scraper"
POSTS_YT = "streamers~youtube-scraper"
COMMENTS_TT = "clockworks~tiktok-comments-scraper"


def say(m):
    print(m, flush=True)


def token():
    # Host-agnostic: an env var wins (cloud routines, teammate machines),
    # the local keys file is the fallback (owner's Mac).
    t = _vault("APIFY_TOKEN")
    if not t:
        sys.exit("no APIFY_TOKEN — set the env var, or add APIFY_TOKEN=value to ~/.upright-keys.env")
    return t


def tokens():
    """Every Apify account on this machine, main first: APIFY_TOKEN, APIFY_TOKEN_PERSONAL, APIFY_TOKEN_2 to _9."""
    names = ["APIFY_TOKEN", "APIFY_TOKEN_PERSONAL"] + [f"APIFY_TOKEN_{n}" for n in range(2, 10)]
    return list(dict.fromkeys(t for t in (_vault(n) for n in names) if t)) or [token()]


def each_account(call):
    """call(token) on each account in turn, moving on when one is spent (402) or refused (403)."""
    accounts = tokens()
    for i, tok in enumerate(accounts):
        try:
            return call(tok)
        except urllib.error.HTTPError as e:
            if e.code not in (401, 402, 403) or i == len(accounts) - 1:       # 401: that account's key is dead
                raise
            say(f"  {e.code} — that Apify account is spent, trying the next one")


def _call(actor, payload, tok, timeout):
    url = (f"{API}/acts/{actor}/run-sync-get-dataset-items"
           f"?token={tok}&timeout={timeout}")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout + 60) as r:
        return json.loads(r.read() or b"[]")


def run(actor, payload, timeout=900):
    """Run an actor on the first account with room."""
    return each_account(lambda tok: _call(actor, payload, tok, timeout))


def run_async(actor, payload, run_id=None, poll=15, timeout=7200):
    """A long run (a comment section for 80 posts runs past the sync call's gateway window, which answers 502):
    start it, or pick up `run_id` already going, wait for it, then read its dataset. Never starts a second paid run
    for the same ask when a run id is given."""
    import time, urllib.request as U
    def call_as(t, url, body=None):
        req = U.Request(url, data=json.dumps(body).encode() if body is not None else None,
                        headers={"Authorization": f"Bearer {t}", "Content-Type": "application/json"})
        return json.loads(U.urlopen(req, timeout=120).read())
    if run_id:
        # A run belongs to the account that started it: find which one answers for it.
        tok, last = None, None
        for t in tokens():
            try:
                call_as(t, f"{API}/actor-runs/{run_id}")
                tok = t
                break
            except urllib.error.HTTPError as e:
                last = e
        if tok is None:
            raise last
    else:
        # Same rule as run(): a spent account moves on to the next one.
        tok, run_id = each_account(lambda t: (t, call_as(t, f"{API}/acts/{actor}/runs", payload)["data"]["id"]))
    def call(url, body=None):
        return call_as(tok, url, body)
    end = time.time() + timeout
    while True:
        r = call(f"{API}/actor-runs/{run_id}")["data"]
        if r["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        if time.time() > end:
            raise RuntimeError(f"run {run_id} still {r['status']} after {timeout}s")
        time.sleep(poll)
    if r["status"] != "SUCCEEDED":
        raise RuntimeError(f"run {run_id} ended {r['status']}")
    items, off = [], 0
    while True:
        page = call(f"{API}/datasets/{r['defaultDatasetId']}/items?clean=true&offset={off}&limit=1000")
        items += page
        if len(page) < 1000:
            return items
        off += 1000


def sign(url):
    if not url or "api.apify.com" not in url or "token=" in url:
        return url
    return f"{url}{'&' if '?' in url else '?'}token={token()}"


def fetch(url, dest, tries=3):
    url = sign(url)
    if not url:
        return False
    # Only a COMPLETE dest counts as done: the stream lands in dest.part and is
    # renamed onto dest when it finishes, so an interrupted download leaves no
    # dest and the next call fetches it again. A leftover .part is overwritten.
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
            os.replace(part, dest)
            return True
        except Exception as e:
            if n == tries - 1:
                say(f"    download failed: {str(e)[:90]}")
    return False


def as_post(it, platform):
    """One shape for every platform.

    swipe has no source abstraction and inlines each wire format in two places;
    that is the thing to not repeat. Everything downstream reads this shape and
    never an actor's own field names.
    """
    if platform == "tiktok":
        a = it.get("authorMeta") or {}
        st = it.get("stats") or it
        return dict(
            platform="tiktok", id=str(it.get("id") or ""),
            url=it.get("webVideoUrl") or "", author=a.get("name") or a.get("nickName") or "",
            author_followers=a.get("fans"),
            caption=it.get("text") or "", posted=it.get("createTimeISO"),
            views=st.get("playCount") or 0, likes=st.get("diggCount") or 0,
            comments=st.get("commentCount") or 0, shares=st.get("shareCount") or 0,
            saves=st.get("collectCount") or 0,
            media=(it.get("mediaUrls") or [None])[0],
            cover=it.get("videoMeta", {}).get("coverUrl") if it.get("videoMeta") else None,
            music=(it.get("musicMeta") or {}).get("musicName"),
            hashtags=[h.get("name") for h in (it.get("hashtags") or []) if h.get("name")],
            kind="video")
    if platform == "youtube":
        return dict(
            platform="youtube", id=str(it.get("id") or ""),
            url=it.get("url") or "", author=it.get("channelName") or "",
            author_followers=it.get("numberOfSubscribers"),
            caption=(it.get("title") or "") + ((" — " + (it.get("text") or "")[:150]) if it.get("text") else ""),
            posted=it.get("date"),
            views=it.get("viewCount") or 0, likes=it.get("likes") or 0,
            comments=it.get("commentsCount") or 0, shares=None, saves=None,
            media=None, cover=it.get("thumbnailUrl"),
            music=None,
            hashtags=[h.lstrip("#") for h in (it.get("hashtags") or [])],
            kind="short" if (it.get("url") or "").find("/shorts/") >= 0 else "video")
    return dict(
        platform="instagram", id=it.get("shortCode") or str(it.get("id") or ""),
        url=it.get("url") or "", author=it.get("ownerUsername") or "",
        author_followers=None,
        caption=it.get("caption") or "", posted=it.get("timestamp"),
        views=it.get("videoPlayCount") or it.get("videoViewCount") or 0,
        likes=it.get("likesCount") or 0, comments=it.get("commentsCount") or 0,
        shares=None, saves=None,
        media=it.get("videoUrl") or it.get("displayUrl"),
        cover=it.get("displayUrl"),
        music=(it.get("musicInfo") or {}).get("song_name") if it.get("musicInfo") else None,
        hashtags=it.get("hashtags") or [],
        kind="video" if it.get("videoUrl") else "image")


def score(p):
    """Views + likes + comments. The same rule the video component ranks on,
    kept identical so two libraries never disagree about what 'top' means."""
    return int(p.get("views") or 0) + int(p.get("likes") or 0) + int(p.get("comments") or 0)


def comments_for(urls, platform, per_post=100):
    """The whole comment section, not the sample the posts actor carries.

    Recipe ported from the retired ingest.py — the shapes differ per platform
    and both normalise to {text, likes, date, owner}. Never imported: the
    retired chain is history, not a reference (component CLAUDE.md rule 6).
    """
    if not urls:
        return {}
    try:
        if platform == "instagram":
            items = run(COMMENTS_IG, {"directUrls": urls,
                                      "resultsLimit": per_post * len(urls)})
            key = "postUrl"
        else:
            items = run(COMMENTS_TT, {"postURLs": urls, "commentsPerPost": per_post})
            key = "videoWebUrl"
    except Exception as e:
        say(f"  comments failed ({str(e)[:90]}) — recorded MISSING, not guessed")
        return None
    out = {}
    for c in items:
        out.setdefault(c.get(key), []).append(dict(
            text=c.get("text"),
            likes=c.get("likesCount") if c.get("likesCount") is not None else c.get("diggCount"),
            date=c.get("timestamp") or c.get("createTimeISO"),
            owner=c.get("ownerUsername") or c.get("uniqueId")))
    return out
