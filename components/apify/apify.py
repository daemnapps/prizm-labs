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


def _vault(name):
    """The key, from wherever this machine keeps it.

    Order: the environment (cloud routines, a teammate's machine, CI), then
    the repo's .env, through components/keys/loader.py. This used to import
    the video teardown machine's own `keys.py`, which made the Apify layer
    depend on another tool's internals and broke wherever that tool was not
    checked out beside it.
    """
    try:
        return _shared_keys().lookup(name) or None
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
    # Host-agnostic: an env var wins, then the repo's .env.
    t = _vault("APIFY_TOKEN")
    if not t:
        sys.exit("This tool needs APIFY_TOKEN. Add it to .env (see .env.example).")
    return t


def _call(actor, payload, tok, timeout):
    url = (f"{API}/acts/{actor}/run-sync-get-dataset-items"
           f"?token={tok}&timeout={timeout}")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout + 60) as r:
        return json.loads(r.read() or b"[]")


def run(actor, payload, timeout=900):
    """Run an actor, falling back to the spare account when the first is spent."""
    tok = token()
    try:
        return _call(actor, payload, tok, timeout)
    except urllib.error.HTTPError as e:
        if e.code != 403:
            raise
        spare = _vault("APIFY_TOKEN_PERSONAL")
        if not spare or spare == tok:
            raise
        say("  403 — the main account looks spent, retrying on the spare")
        return _call(actor, payload, spare, timeout)


def sign(url):
    if not url or "api.apify.com" not in url or "token=" in url:
        return url
    return f"{url}{'&' if '?' in url else '?'}token={token()}"


def fetch(url, dest, tries=3):
    url = sign(url)
    if not url:
        return False
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
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
