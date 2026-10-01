#!/usr/bin/env python3
"""Creator sourcing — a page in, her ten best posts on the Drive.

    python3 sourcing.py --creator tammysagelessbeauty
    python3 sourcing.py --creator someone --platform TikTok
    python3 sourcing.py --all              every creator in creators.json
    python3 sourcing.py --list             who we know about

What it does, per creator: index her whole page, score every post
(views + likes + comments), keep the top ten, download them, and lay the
folder out so the folder explains itself — creator.md at the top, one
folder per post underneath, each with its metrics and its own teardown space.

The creator list comes from the brand's creator tracker sheet. A session
refreshes `creators.json` from the sheet; this only reads it.
"""

import argparse, json, shutil, sys, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import keys, library as L

ACTOR = "apify~instagram-scraper"
PROFILE_ACTOR = "apify~instagram-profile-scraper"
TIKTOK_ACTOR = "clockworks~tiktok-profile-scraper"
API = "https://api.apify.com/v2"
CREATORS = HERE / "creators.json"
INDEX_DEPTH = 200        # how deep to index a page before ranking
TOP_N = 10


def say(m): print(m, flush=True)


def handle_from(url):
    path = urllib.parse.urlparse(url).path.strip("/")
    return (path.split("/")[0] or "").lstrip("@")


# ------------------------------------------------------------------ apify

def _call(actor, payload, token, timeout):
    url = (f"{API}/acts/{actor}/run-sync-get-dataset-items"
           f"?token={token}&timeout={timeout}")
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout + 60) as r:
        return json.loads(r.read() or b"[]")


def apify(actor, payload, token, timeout=900):
    """Run an actor, falling back to a spare account when the first is spent.

    A used-up Apify allowance answers 403 to everything, which is
    indistinguishable from a bad token until you go and read the account's
    limits — it stopped a run dead on 2026-08-27 with nine videos left to
    fetch. If APIFY_TOKEN_PERSONAL is set, a 403 retries on it once and says
    so, rather than failing the whole pull."""
    try:
        return _call(actor, payload, token, timeout)
    except urllib.error.HTTPError as e:
        if e.code != 403:
            raise
        spare = keys.get("APIFY_TOKEN_PERSONAL", required=False)
        if not spare or spare == token:
            raise SystemExit(
                "Apify said 403 on every call, which means the account's monthly "
                "allowance is spent (check /users/me/limits). Add a second key as "
                "APIFY_TOKEN_PERSONAL to ~/.daemn/keys.env and re-run.")
        say("  first Apify account is spent — switching to the spare")
        return _call(actor, payload, spare, timeout)


def get_profile(handle, token):
    """Followers and bio come from the profile actor — the post scrape carries
    them only sometimes, which is how the first run recorded 'None'."""
    try:
        items = apify(PROFILE_ACTOR, {"usernames": [handle]}, token, timeout=180)
    except Exception as e:
        say(f"  (profile lookup failed: {str(e)[:80]})")
        return {}
    return items[0] if items else {}


def platform_of(url):
    return "tiktok" if "tiktok.com" in (url or "").lower() else "instagram"


def as_instagram(it):
    """One TikTok post, wearing Instagram's field names.

    Everything downstream — scoring, ranking, the folder layout, post.md —
    was written against the Instagram scraper's shape. Normalising here means
    TikTok is a source without a second copy of any of that. The names on the
    left are the contract; only this function knows they came from TikTok."""
    vm = it.get("videoMeta") or {}
    a = it.get("authorMeta") or {}
    media = it.get("mediaUrls") or []
    return {
        "shortCode": it.get("id"),
        "url": it.get("webVideoUrl"),
        "type": "Video",
        "timestamp": it.get("createTimeISO"),
        "caption": it.get("text"),
        "videoPlayCount": it.get("playCount"),
        "likesCount": it.get("diggCount"),
        "commentsCount": it.get("commentCount"),
        # shouldDownloadVideos gives an Apify-hosted copy; downloadAddr is the
        # fallback and expires, so prefer mediaUrls when both are present.
        "videoUrl": (media[0] if media else vm.get("downloadAddr")),
        "displayUrl": vm.get("coverUrl") or vm.get("originalCoverUrl"),
        "images": [],
        "ownerFullName": a.get("nickName"),
        "durationSeconds": vm.get("duration"),
        "_platform": "tiktok",
    }


def tiktok_profile(items, handle, url):
    """TikTok carries the author on every post, so the profile is already in
    the payload — no second call, unlike Instagram."""
    for it in items:
        a = it.get("authorMeta") or {}
        if a:
            return {"fullName": a.get("nickName"),
                    "followersCount": a.get("fans"),
                    "followsCount": a.get("following"),
                    "postsCount": a.get("video"),
                    "biography": a.get("signature") or "",
                    "verified": a.get("verified"),
                    "externalUrl": ""}
    return {}


def index_page(url, token, depth=INDEX_DEPTH):
    """-> (posts in Instagram shape, profile or None).

    Instagram needs a second call for the profile; TikTok does not."""
    if platform_of(url) == "tiktok":
        handle = handle_from(url)
        say(f"  indexing the page (up to {depth} posts) …")
        # shouldDownloadVideos is REQUIRED — without it the actor returns empty
        # mediaUrls and no download address, so nothing is downloadable.
        items = apify(TIKTOK_ACTOR, {"profiles": [handle],
                                     "resultsPerPage": depth,
                                     "shouldDownloadVideos": True}, token)
        posts = [as_instagram(i) for i in items if i.get("id")]
        return posts, tiktok_profile(items, handle, url)

    say(f"  indexing the page (up to {depth} posts) …")
    items = apify(ACTOR, {
        "directUrls": [url],
        "resultsType": "posts",
        "resultsLimit": depth,
        "addParentData": True,
    }, token)
    return [i for i in items if i.get("shortCode")], None


# ------------------------------------------------------------------ ranking

def score(p):
    """Views + likes + comments, added up. That is the whole rule."""
    views = p.get("videoPlayCount") or p.get("videoViewCount") or 0
    return int(views) + int(p.get("likesCount") or 0) + int(p.get("commentsCount") or 0)


def rank(posts, n=TOP_N):
    for p in posts:
        p["_score"] = score(p)
    return sorted(posts, key=lambda p: p["_score"], reverse=True)[:n]


# ------------------------------------------------------------------ download

def sign(url):
    """Apify-hosted media lives in a PRIVATE key-value store, so an unsigned
    request comes back 403 — which reads exactly like a dead CDN link and cost
    an afternoon on 2026-08-27. Anything on api.apify.com gets the token."""
    if not url or "api.apify.com" not in url or "token=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={keys.get('APIFY_TOKEN')}"


def fetch(url, dest, tries=3):
    url = sign(url)
    if not url or dest.exists():
        return dest.exists()
    for n in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
            return True
        except Exception as e:
            dest.unlink(missing_ok=True)
            if n == tries:
                say(f"      couldn't download {dest.name} after {tries} tries: "
                    f"{str(e)[:80]}")
                return False
            time.sleep(4 * n)
    return False


def save_post(handle, p, i):
    d = L.post_dir(handle, i, p.get("shortCode"))
    L.write_post_md(d, p, handle, i)
    got = []
    if p.get("videoUrl"):
        if fetch(p["videoUrl"], d / "video.mp4"):
            got.append("video")
    if p.get("displayUrl"):
        if fetch(p["displayUrl"], d / ("thumbnail.jpg" if got else "image.jpg")):
            got.append("thumbnail" if got else "image")
    for n, extra in enumerate(p.get("images") or [], 1):
        if n > 1 and fetch(extra, d / f"image-{n:02d}.jpg"):
            got.append(f"image{n}")
    return d, got


def reconcile(handle, top):
    """A re-pull replaces the previous top ten rather than piling a second set
    on top of it. Anything already torn down is left alone and reported — that
    work is never thrown away to tidy a folder."""
    posts = L.creator_dir(handle, make=False) / "posts"
    if not posts.exists():
        return
    keep = {L.post_dir(handle, i, p.get("shortCode"), make=False).name.lower()
            for i, p in enumerate(top, 1)}
    for d in sorted(posts.iterdir()):
        if not d.is_dir() or d.name.lower() in keep:
            continue
        if (d / "teardown").exists():
            say(f"  keeping {d.name} — it has teardown work in it")
            continue
        # A post chosen off the picking board is usually NOT in the top ten —
        # that is the whole point of the deeper pass — so without this the next
        # pull would quietly delete the videos someone picked (2026-08-27).
        if (d / "SELECTED").exists():
            say(f"  keeping {d.name} — it is a selected post")
            continue
        shutil.rmtree(d, ignore_errors=True)


# ------------------------------------------------------------------ per creator

def pull(name, url, token, depth=INDEX_DEPTH, n=TOP_N):
    handle = handle_from(url)
    if not handle:
        say(f"  skipping {name}: can't read a handle out of {url}")
        return None
    say(f"\n▶ {name}  @{handle}")

    posts, prof_raw = index_page(url, token, depth)
    if not posts:
        say("  nothing came back — page may be private, or the handle is wrong")
        return None
    say(f"  indexed {len(posts)} posts")

    top = rank(posts, n)
    raw = prof_raw if prof_raw is not None else get_profile(handle, token)
    profile = {
        "fullName": raw.get("fullName") or top[0].get("ownerFullName") or name,
        "followersCount": raw.get("followersCount"),
        "followsCount": raw.get("followsCount"),
        "postsCount": raw.get("postsCount") or len(posts),
        "indexed": len(posts),
        "biography": raw.get("biography") or "",
        "verified": raw.get("verified"),
        "externalUrl": raw.get("externalUrl") or "",
    }

    d = L.creator_dir(handle)
    (d / "profile.json").write_text(json.dumps(
        {"name": name, "url": url, "indexed": len(posts),
         "pulled": L.now(), "profile": profile}, indent=2))

    reconcile(handle, top)

    saved = []
    for i, p in enumerate(top, 1):
        pd, got = save_post(handle, p, i)
        saved.append(pd)
        say(f"  {i:2d}. {p['shortCode']:<14} {p['_score']:>9,}  "
            f"{'+'.join(got) or 'no media'}")

    L.write_creator_md(handle, profile, url, top)
    say(f"  → {d}")
    return d


# ------------------------------------------------------------------ cli

def load_creators():
    if not CREATORS.exists():
        sys.exit(f"No creator list yet at {CREATORS}.\n"
                 "Ask a session to refresh it from the brand's creator tracker.")
    return json.loads(CREATORS.read_text())


def main():
    ap = argparse.ArgumentParser(description="Pull a creator's top posts.")
    ap.add_argument("--creator", help="one handle or profile URL")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--platform", default="Instagram")
    ap.add_argument("--top", type=int, default=TOP_N)
    ap.add_argument("--depth", type=int, default=INDEX_DEPTH)
    ap.add_argument("--limit", type=int, help="only the first N creators")
    a = ap.parse_args()

    people = load_creators() if (a.all or a.list) else []
    people = [c for c in people
              if c.get("platform", "").lower() == a.platform.lower()]

    if a.list:
        say(f"{len(people)} {a.platform} creators on the tracker:")
        for c in people:
            say(f"  {c['name']:<22} {c.get('url','')}")
        return

    token = keys.get("APIFY_TOKEN")
    say(f"Library: {L.root()}")

    if a.creator:
        if a.creator.startswith("http"):
            u = a.creator
        elif a.platform.lower() == "tiktok":
            u = f"https://www.tiktok.com/@{a.creator.lstrip('@')}/"
        else:
            u = f"https://www.instagram.com/{a.creator.lstrip('@')}/"
        pull(a.creator, u, token, a.depth, a.top)
        return

    if not a.all:
        sys.exit("give me --creator <handle>, or --all")

    if a.limit:
        people = people[:a.limit]
    say(f"{len(people)} creators to pull.")
    for c in people:
        try:
            pull(c["name"], c["url"], token, a.depth, a.top)
        except Exception as e:
            say(f"  stopped on {c['name']}: {str(e)[:160]}")


if __name__ == "__main__":
    main()
