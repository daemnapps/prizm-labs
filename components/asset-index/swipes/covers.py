"""covers.py: viral explore covers as indexed swipes. Pull what the platforms' discovery surfaces are pushing,
keep each post's numbers (views, likes, post date, URL), measure every cover locally, carry the by-eye breakdown,
and write one swipe row per cover beside the footage library, so a production can pull "a real cover like this"
next to its own footage. Brand-agnostic: swipes from the open internet serve any brand.

  python3 covers.py pull    <dir> [--key-name APIFY_TOKEN] [--only ig-explore tt-explore yt-trending yt-shorts]
  python3 covers.py pull    <dir> --avatar <avatar file> [--key-name APIFY_TOKEN] [--only av-ig-tags ...]
                                             one avatar's own feed: the hashtags, accounts and topics its file lists
  python3 covers.py rows    <dir>            raw/*.json -> rows.json (one shape for every platform), viral floor applied
  python3 covers.py fetch   <dir>            every row's cover -> covers/<id>.jpg
  python3 covers.py measure <dir>            local and free: text read (macOS Vision), faces/hands, colour -> measure.json
  python3 covers.py sheets  <dir>            numbered contact sheets for the by-eye breakdown -> sheets/<platform>-<n>.jpg
  python3 covers.py index   <dir> <out>      rows + measure + breakdown.json -> <out>/covers.json (the swipes) + patterns.json
                                             + avatars.json; rows from other pulls already in <out> are kept
  python3 covers.py import  <pull dir> <out> --avatar <avatar file or name> [--rows keep.json] [--pulled YYYY-MM-DD]
                                             a pull made outside this tool (a kept list + covers/) -> the index
  python3 covers.py moves   <out> [--set <id>=<move> ...] [--from moves.json] [--redo]
                                             the move each cover makes, read from its breakdown; no model call
  python3 covers.py find    <out> [--avatar NAME] [--move wrong-scale] [--rank likes|views] [--limit N] [--json]
                                  [--platform ig] [--frame hands-product] [--absurd 2] [--text none] [--min-views N]

Sources (Apify actors, chosen 2026-11-11; the platforms' own discovery surfaces, nothing searched by brand):
  ig-explore   agentx/instagram-trending-scraper     Instagram Explore, country locale United States
  tt-explore   khadinakbar/tiktok-trending-videos-scraper  TikTok Explore feed (All + categories), last 14 days, no ads
  yt-trending  sian.agency/youtube-trending-hype-pulse     YouTube Trending tab + Hype leaderboard, US
  yt-shorts    makework36/youtube-shorts-scraper    YouTube Shorts, most viewed since a date (YouTube has no public
                                                    Shorts explore feed; this is the nearest open surface)
Avatar sources (only what the avatar file lists is asked for; file shape in avatar.example.json):
  av-ig-tags      apify/instagram-hashtag-scraper   Reels under each hashtag
  av-ig-accounts  apify/instagram-scraper           each account's posts (videos kept)
  av-tt-tags / av-tt-accounts / av-tt-topics   clockworks/tiktok-scraper   hashtags, profiles, searches
  av-ys-topics    makework36/youtube-shorts-scraper Shorts, most viewed, per topic
Keys by name only (components/keys/loader.py). The breakdown fields a model or a person fills by eye are in BREAKDOWN.
The moves are in MOVES. Switches: switches.json beside this file (avatar, move, merge-keeps, avatar-slug,
avatar-scope, move-rules, merge-by-pull, move-picture); one machine: COVER_SWIPES_OFF.
"""
import json
import math
import re
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "components" / "keys"))
sys.path.insert(0, str(REPO / "components" / "video-edit" / "machine"))

SOURCES = {
    "ig-explore": ("agentx~instagram-trending-scraper", lambda since: {"max_results": 60, "country": "United States"}),
    "ig-explore-ca": ("agentx~instagram-trending-scraper", lambda since: {"max_results": 30, "country": "Canada"}),
    "ig-explore-uk": ("agentx~instagram-trending-scraper", lambda since: {"max_results": 30, "country": "United Kingdom"}),
    "tt-foryou": ("khadinakbar~tiktok-trending-videos-scraper", lambda since: {
        "feed": "foryou", "maxResults": 150, "region": "US", "postedWithinDays": 14, "minPlays": 500000, "excludeAds": True, "sortBy": "feed"}),
    "tt-explore": ("khadinakbar~tiktok-trending-videos-scraper", lambda since: {
        "feed": "explore", "categories": ["All", "Beauty Care", "Daily Life", "Fitness & Health", "Technology"],
        "maxResults": 80, "region": "", "postedWithinDays": 14, "excludeAds": True, "sortBy": "feed"}),
    "yt-trending": ("sian.agency~youtube-trending-hype-pulse", lambda since: {"operation": "trendingAndHype", "region": "US", "maxPages": 1, "lang": "en"}),
    "yt-shorts": ("makework36~youtube-shorts-scraper", lambda since: {
        "searchQueries": ["shorts", "skincare", "men grooming", "unboxing", "gadget"], "maxResultsPerQuery": 15,
        "sortBy": "view_count", "publishedAfter": since, "onlyShortsFilter": True}),
    "yt-shorts-2": ("makework36~youtube-shorts-scraper", lambda since: {
        "searchQueries": ["#shorts", "funny", "satisfying", "life hack", "prank", "transformation", "before and after",
                          "tiktok made me buy it", "product review", "morning routine"], "maxResultsPerQuery": 20,
        "sortBy": "view_count", "publishedAfter": since, "onlyShortsFilter": True}),
    "tt-explore-2": ("khadinakbar~tiktok-trending-videos-scraper", lambda since: {
        "feed": "explore", "categories": ["All", "Comedy", "Daily Life", "Beauty Care", "Outfit", "Fitness & Health",
                                          "Technology", "Food", "Family", "Relationship", "Cars", "Animals"],
        "maxResults": 200, "region": "", "postedWithinDays": 14, "minPlays": 500000, "excludeAds": True, "sortBy": "feed"}),
}
PLATFORM = {"ig-explore": "instagram", "ig-explore-ca": "instagram", "ig-explore-uk": "instagram", "tt-foryou": "tiktok", "tt-explore": "tiktok", "tt-explore-2": "tiktok", "yt-trending": "youtube", "yt-shorts": "youtube-shorts", "yt-shorts-2": "youtube-shorts"}
# The viral floor: a row below it is kept out of the swipes (numbers, not taste). Views where the platform gives them.
FLOOR = {"instagram": {"likes": 10000}, "tiktok": {"views": 500000}, "youtube": {"views": 100000}, "youtube-shorts": {"views": 250000}}
MAX_AGE_DAYS = 21

# Filled by eye per cover (breakdown.json: {id: {...}}). The vocabulary, so every cover is read the same way.
BREAKDOWN = {
    "frame": ["face", "face+product", "product", "hands-product", "pov", "body", "scene", "screen", "graphic", "text-only"],
    "people": ["none", "one", "two", "group"],
    "expression": ["none", "neutral", "smile", "shock", "intense", "talking", "looking-away"],
    "shot": ["extreme-close", "close", "medium", "wide"],
    "zoom": ["native", "punched-in", "split", "collage"],
    "text_style": ["none", "native-caption", "native-box", "outline", "designed-box", "designed-type", "burned-subtitle", "title-card"],
    "text_case": ["none", "lower", "sentence", "title", "upper", "mixed"],
    "text_place": ["none", "top", "upper-middle", "middle", "lower-middle", "bottom", "spread"],
    "grade": ["native", "warm", "cool", "high-contrast", "saturated", "muted", "dark", "flash"],
    "marks": ["circle", "arrow", "emoji", "sticker", "border", "split-line", "logo", "price", "number", "none"],
    "look": ["raw", "native", "lightly-edited", "designed", "studio"],
    "absurd": [0, 1, 2, 3],   # 0 as shot · 1 one odd thing · 2 impossible scale / absurd subject · 3 impossible scene
}

# The move a cover makes, in a few words: what a cover step copies (the move, not the picture). A person may write
# `move` into a cover's breakdown by eye; `derive_move` reads the rest of the breakdown where it already says it.
MOVES = {
    "impossible-object": "a thing that cannot exist",
    "impossible-scene": "a scene that cannot exist",
    "wrong-scale": "a thing at the wrong scale",
    "absurd-subject": "an absurd subject, shot straight",
    "face-at-limit": "a face pushed to its limit",
    "line-shown-literally": "the words name a thing the picture shows past real",
    "before-after": "before and after side by side",
    "pointed-at": "a circle or arrow on the target",
    "price-as-hook": "the price is the hook",
    "thing-to-lens": "a thing pushed at the lens",
    "one-odd-thing": "one odd thing in a normal frame",
    "as-shot": "no move: the frame as shot",
}
UNRATED = "unrated"       # no breakdown says it yet: waits for an eye read (`moves --set` or `move` in breakdown.json)
BREAKDOWN["move"] = list(MOVES)

# An avatar's feed is narrower and older than a discovery surface: its own floor, no age limit unless its file sets one.
AVATAR_FLOOR = {"instagram": {"likes": 5000}, "tiktok": {"views": 500000}, "youtube-shorts": {"views": 250000}}
AVATAR_ORDER = ["av-ig-tags", "av-ig-accounts", "av-tt-tags", "av-tt-accounts", "av-tt-topics", "av-ys-topics"]
SWITCHES = HERE / "switches.json"


def switch(name):
    """True when the named switch is on: `avatar` (avatar pulls, import, find --avatar) or `move` (the move field).
    switches.json {"<name>": {"on": true}}; one machine: COVER_SWIPES_OFF=all or a comma list of names."""
    off = {x.strip() for x in os.environ.get("COVER_SWIPES_OFF", "").split(",") if x.strip()}
    if "all" in off or name in off:
        return False
    try:
        return bool(json.loads(SWITCHES.read_text()).get(name, {}).get("on", True))
    except (OSError, ValueError):
        return True


def _need(name, what):
    if not switch(name):
        sys.exit(f"{what} is switched off (components/asset-index/swipes/switches.json `{name}.on`, or COVER_SWIPES_OFF "
                 f"on this machine). Row COVER-SWIPES in team/rollbacks.md.")


class AvatarError(ValueError):
    """A bad avatar name or a missing avatar file. The command line turns it into a stop with the same words."""


def avatar_slug(name):
    """Any spelling of an avatar's name -> the name every indexed cover carries: lower case, spaces and underscores
    to dashes, no leading or trailing dash. 'Home Baker', 'home_baker' and ' home-baker ' are one avatar."""
    return re.sub(r"-{2,}", "-", re.sub(r"[\s_]+", "-", str(name or "").strip().lower())).strip("-")


def read_avatar(ref):
    """An avatar file -> its record; a bare name -> {"avatar": name}. The name is what every indexed cover carries.
    A bad name or a missing file raises AvatarError (a ValueError), so a caller in Python is never stopped by it."""
    slug = switch("avatar-slug")
    stop = AvatarError if slug else (lambda words: SystemExit(words))
    p = Path(str(ref))
    if p.suffix == ".json" and not p.exists():
        raise stop(f"no avatar file at {p}")
    av = json.loads(p.read_text()) if p.suffix == ".json" else {"avatar": str(ref)}
    name = avatar_slug(av.get("avatar")) if slug else str(av.get("avatar") or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise stop(f"avatar name {name!r}: lower-case letters, digits and dashes (the `avatar` field of the avatar file)")
    av["avatar"] = name
    for k, lead in (("hashtags", "#"), ("accounts", "@"), ("topics", ""), ("on_topic", "")):
        av[k] = [str(x).strip().lstrip(lead) for x in av.get(k) or [] if str(x).strip()]
    av["platforms"] = av.get("platforms") or ["instagram"]
    return av


def avatar_jobs(av, since):
    """The avatar's feed as runs: {raw name: (actor, input)}. Only what its file lists, on the platforms it lists."""
    n = int(av.get("per_source") or 40)
    tags, accounts, topics, plats = av["hashtags"], av["accounts"], av["topics"], av["platforms"]
    jobs = {}
    if "instagram" in plats and tags:
        jobs["av-ig-tags"] = ("apify~instagram-hashtag-scraper", {"hashtags": tags, "resultsType": "reels", "resultsLimit": n})
    if "instagram" in plats and accounts:
        jobs["av-ig-accounts"] = ("apify~instagram-scraper", {
            "directUrls": [f"https://www.instagram.com/{h}/" for h in accounts], "resultsType": "posts",
            "resultsLimit": n, "addParentData": False})
    if "tiktok" in plats and tags:
        jobs["av-tt-tags"] = ("clockworks~tiktok-scraper", {"hashtags": tags, "resultsPerPage": n})
    if "tiktok" in plats and accounts:
        jobs["av-tt-accounts"] = ("clockworks~tiktok-scraper", {"profiles": accounts, "resultsPerPage": n})
    if "tiktok" in plats and topics:
        jobs["av-tt-topics"] = ("clockworks~tiktok-scraper", {"searchQueries": topics, "resultsPerPage": n})
    if "youtube-shorts" in plats and topics:
        jobs["av-ys-topics"] = ("makework36~youtube-shorts-scraper", {
            "searchQueries": topics, "maxResultsPerQuery": min(n, 20), "sortBy": "view_count",
            "publishedAfter": since, "onlyShortsFilter": True})
    return jobs


def _api(path, token, data=None):
    req = urllib.request.Request(f"https://api.apify.com/v2/{path}{'&' if '?' in path else '?'}token={token}",
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def pull(d, key_name="APIFY_TOKEN", only=None, wait_min=25, avatar=None):
    """Start every source's run, wait for each (a stalled run is stopped at wait_min and keeps what it has), save raw.
    With an avatar file the sources are that avatar's own feed (avatar_jobs), and the file is kept as <dir>/avatar.json
    so rows and index name the avatar on every cover."""
    if avatar:
        _need("avatar", "The avatar pull")
        av = read_avatar(avatar)
        since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - int(av.get("max_age_days") or 365) * 86400))
        jobs = avatar_jobs(av, since)
        if not jobs:
            sys.exit(f"avatar {av['avatar']}: its file lists no hashtags, accounts or topics for {av['platforms']}")
    else:
        since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 14 * 86400))
        jobs = {n: (SOURCES[n][0], SOURCES[n][1](since)) for n in SOURCES}
    if only:
        jobs = {n: jobs[n] for n in only}
    from loader import key
    token = key(key_name)
    (d / "raw").mkdir(parents=True, exist_ok=True)
    if avatar:
        (d / "avatar.json").write_text(json.dumps(av, indent=1))
    runs = {}
    for n, (actor, inp) in jobs.items():
        try:
            runs[n] = _api(f"acts/{actor}/runs", token, inp)["data"]
        except Exception as e:                      # a capped account says so in its body; never print the key
            print(n, "FAILED", str(getattr(e, "read", lambda: b"")()[:200] or e))
    end = time.time() + wait_min * 60
    while runs:
        for n, r in list(runs.items()):
            s = _api(f"actor-runs/{r['id']}", token)["data"]
            if s["status"] == "RUNNING" and time.time() < end:
                continue
            if s["status"] == "RUNNING":
                _api(f"actor-runs/{r['id']}/abort", token, {})
            items = _api(f"datasets/{r['defaultDatasetId']}/items?clean=true", token)
            (d / "raw" / f"{n}.json").write_text(json.dumps(items, indent=1))
            print(n, s["status"].lower(), len(items), "items, $%.3f" % (s.get("usageTotalUsd") or 0))
            runs.pop(n)
        time.sleep(15)


def _ts(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / (1000 if v > 1e12 else 1), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for fmt in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v), fmt).strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            pass
    return str(v)


def _g(x, *paths):
    for p in paths:
        cur = x
        for k in p.split("."):
            cur = cur.get(k) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur not in (None, "", []):
            return cur
    return None


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).replace(",", "").strip().upper()
    mult = 1
    for suf, m in (("K", 1e3), ("M", 1e6), ("B", 1e9)):
        if s.endswith(suf):
            s, mult = s[:-1], m
    try:
        return int(float(s) * mult)
    except ValueError:
        return None


def normalize(source, x):
    """One raw item -> the common row. Field names differ per actor; each list is tried in order."""
    p = PLATFORM[source]
    if source.startswith("ig-explore"):
        code = _g(x, "shortcode", "code", "post.shortcode")
        loc = {"ig-explore": "US", "ig-explore-ca": "Canada", "ig-explore-uk": "UK"}[source]
        return {"platform": p, "surface": f"Instagram Explore ({loc} locale)" + (" · " + x["explore_topic"] if x.get("explore_topic") else ""),
                "url": _g(x, "url", "post_url", "permalink") or (f"https://www.instagram.com/p/{code}/" if code else None),
                "cover_url": _g(x, "thumbnail_url", "display_url", "image_url", "cover_url", "media.0.url", "media_items.0.thumbnail_url", "media_items.0.url"),
                "views": _num(_g(x, "video_view_count", "play_count", "view_count", "views", "engagement.views", "engagement.play_count")),
                "likes": _num(_g(x, "like_count", "likes", "engagement.likes", "engagement.like_count")),
                "comments": _num(_g(x, "comment_count", "comments_count", "engagement.comments", "engagement.comment_count")),
                "posted": _ts(_g(x, "taken_at", "published_at", "timestamp", "created_at", "date")),
                "author": _g(x, "owner_username", "username", "owner.username", "creator.username", "author.username"),
                "followers": _num(_g(x, "owner.follower_count", "creator.follower_count", "author.followers")),
                "caption": (_g(x, "caption", "caption_text", "text") or "")[:300],
                "kind": _g(x, "post_type", "media_type", "product_type", "type", "format"),
                "duration": _g(x, "video_duration", "duration")}
    if source.startswith("tt-"):
        return {"platform": p, "surface": ("TikTok For You" if source == "tt-foryou" else "TikTok Explore") + (" · " + x["category"] if x.get("category") else ""),
                "url": _g(x, "videoUrl", "webVideoUrl", "url", "shareUrl"),
                "cover_url": _g(x, "coverUrl", "cover", "videoMeta.coverUrl", "covers.0", "video.cover", "originCover", "dynamicCover"),
                "views": _num(_g(x, "playCount", "plays", "views", "stats.playCount")),
                "likes": _num(_g(x, "diggCount", "likes", "stats.diggCount")),
                "comments": _num(_g(x, "commentCount", "comments", "stats.commentCount")),
                "shares": _num(_g(x, "shareCount", "shares", "stats.shareCount")),
                "posted": _ts(_g(x, "createTimeISO", "createTime", "postedAt", "publishedAt")),
                "saves": _num(_g(x, "saveCount")), "plays_per_hour": _num(_g(x, "playsPerHour")),
                "author": _g(x, "authorHandle", "authorMeta.name", "author.uniqueId", "authorUsername", "username"),
                "followers": _num(_g(x, "authorMeta.fans", "authorFollowers", "author.followerCount")),
                "caption": (_g(x, "text", "description", "desc", "caption") or "")[:300],
                "kind": "video", "duration": _g(x, "videoMeta.duration", "durationSec", "duration")}
    if source == "yt-trending":
        return {"platform": p, "surface": "YouTube " + {"trending": "Trending", "hype": "Hype"}.get(x.get("_sourceFeed"), str(x.get("_sourceFeed"))) + " (US)",
                "url": x.get("videoPageUrl"), "cover_url": f"https://i.ytimg.com/vi/{x['videoId']}/maxresdefault.jpg",
                "cover_fallback": x.get("thumbnailUrl"),
                "views": _num(x.get("viewCount")), "likes": _num(x.get("likeCount")), "comments": _num(x.get("commentCount")),
                "posted": x.get("publishedAt"), "author": x.get("channelTitle"), "caption": (x.get("videoTitle") or "")[:300],
                "rank": _num(x.get("hypeText")), "kind": "video", "duration": x.get("lengthText")}
    if source.startswith("yt-shorts"):
        vid = _g(x, "videoId", "id")
        return {"platform": p, "surface": "YouTube Shorts (most viewed, last 14 days)",
                "url": _g(x, "url", "videoUrl") or (f"https://www.youtube.com/shorts/{vid}" if vid else None),
                "cover_url": f"https://i.ytimg.com/vi/{vid}/oardefault.jpg" if vid else None,
                "cover_fallback": _g(x, "thumbnailUrl", "thumbnail", "thumbnails.0.url"),
                "views": _num(_g(x, "viewCount", "views")), "likes": _num(_g(x, "likeCount", "likes")),
                "comments": _num(_g(x, "commentCount", "comments", "commentsCount")),
                "posted": _ts(_g(x, "publishedAt", "uploadDate", "publishDate", "date")), "author": _g(x, "channelName", "channelTitle", "channel.name"),
                "caption": (_g(x, "title", "text") or "")[:300], "kind": "short", "duration": _g(x, "duration", "lengthSeconds")}


def normalize_avatar(source, x):
    """One raw item from an avatar source -> the common row, with `via`: the hashtag, account or topic that carried it."""
    if source.startswith("av-ig"):
        if x.get("type") and x.get("type") != "Video" and not x.get("videoPlayCount"):
            return None                                 # a photo post has no cover
        code = _g(x, "shortCode", "shortcode", "code")
        tag = x.get("tag") or (re.findall(r"/explore/tags/([^/?#]+)", x.get("inputUrl") or "") or [None])[0]
        owner = _g(x, "ownerUsername", "owner.username", "username")
        via = ("#" + tag) if tag else (("@" + owner) if owner and source == "av-ig-accounts" else None)
        likes = _num(_g(x, "likesCount", "likes"))
        return {"platform": "instagram", "surface": "Instagram, avatar feed" + (" · " + via if via else ""),
                "url": x.get("url") or (f"https://www.instagram.com/p/{code}/" if code else None),
                "cover_url": _g(x, "displayUrl", "thumbnailUrl", "images.0"),
                "views": _num(_g(x, "videoPlayCount", "igPlayCount", "videoViewCount", "views")),
                "likes": likes if likes is None or likes >= 0 else None,       # a hidden count comes back as -1
                "comments": _num(_g(x, "commentsCount", "comments")),
                "posted": _ts(_g(x, "timestamp", "takenAt")), "author": owner, "followers": None,
                "caption": (x.get("caption") or "")[:300], "kind": "reel", "duration": _g(x, "videoDuration", "duration"),
                "via": via}
    if source.startswith("av-tt"):
        r = normalize("tt-explore", x)
        got = _g(x, "searchHashtag.name", "input", "searchQuery")
        lead = {"av-tt-tags": "#", "av-tt-accounts": "@"}.get(source, "")
        r["via"] = (lead + str(got).lstrip("#@")) if got else None
        r["surface"] = "TikTok, avatar feed" + (" · " + r["via"] if r["via"] else "")
        return r
    if source.startswith("av-ys"):
        r = normalize("yt-shorts", x)
        got = _g(x, "searchQuery", "query", "input")
        r["via"] = str(got) if got else None
        r["surface"] = "YouTube Shorts, avatar feed" + (" · " + r["via"] if r["via"] else "")
        return r


def _age_days(posted, now):
    try:
        t = datetime.fromisoformat(str(posted).replace("Z", "+00:00"))
        return (now - t).total_seconds() / 86400
    except Exception:
        return None


def _post_key(url):
    """The post's own id out of its link: one video under two links is one row."""
    return (re.findall(r"(?:/video/|/reel/|/p/|/shorts/|[?&]v=)([\w-]+)", url or "") or [None])[0] or url


def _row_id(platform, key):
    return "%s-%s" % ({"instagram": "ig", "tiktok": "tt", "youtube": "yt", "youtube-shorts": "ys"}[platform],
                      re.sub(r"[^A-Za-z0-9]", "", key)[-8:])


def _on_topic(av, r):
    """True when the avatar file sets no `on_topic` words, or the caption or the carrying hashtag has one of them."""
    words = [w.lower() for w in (av or {}).get("on_topic") or []]
    text = ((r.get("caption") or "") + " " + (r.get("via") or "")).lower()
    return not words or any(w in text for w in words)


def rows(d):
    now = datetime.now(timezone.utc)
    out, seen, dropped = [], set(), Counter()
    order = ["ig-explore", "ig-explore-ca", "ig-explore-uk", "tt-explore", "tt-explore-2", "tt-foryou",
             "yt-trending", "yt-shorts", "yt-shorts-2"] + AVATAR_ORDER   # pull order, fixed, so a later pull never renumbers earlier rows
    av = read_avatar(d / "avatar.json") if (d / "avatar.json").exists() else None
    for f in sorted((d / "raw").glob("*.json"), key=lambda f: order.index(f.stem) if f.stem in order else 99):
        src = f.stem
        mine = src.startswith("av-")                # an avatar source: the avatar's floor, its age limit, its topic words
        if mine and not av:
            sys.exit(f"{f.name} is an avatar source but {d} has no avatar.json (pull it with --avatar)")
        for x in json.loads(f.read_text()):
            r = normalize_avatar(src, x) if mine else normalize(src, x)
            key = _post_key((r or {}).get("url"))     # the post's own id: one video under two links is one row
            if not r or not r.get("url") or not r.get("cover_url") or key in seen:
                dropped["no url/cover or duplicate"] += 1
                continue
            age = _age_days(r.get("posted"), now)
            r["age_days"] = round(age, 1) if age is not None else None
            fl = {**AVATAR_FLOOR, **(av.get("floor") or {})}[r["platform"]] if mine else FLOOR[r["platform"]]
            metric = "views" if "views" in fl else "likes"
            if (r.get(metric) or 0) < fl[metric]:
                dropped[f"{r['platform']} under {fl[metric]:,} {metric}"] += 1
                continue
            max_age = av.get("max_age_days") if mine else MAX_AGE_DAYS
            if max_age and age is not None and age > max_age:
                dropped[f"{r['platform']} older than {max_age} days"] += 1
                continue
            if mine and not _on_topic(av, r):
                dropped[f"{r['platform']} off the avatar's topic words"] += 1
                continue
            seen.add(key)
            r["source"] = src
            r["avatar"] = av["avatar"] if mine else None
            r["_key"] = key
            out.append(r)
    for r in out:                                   # the id carries the post's own id, so it never changes between pulls
        r["id"] = _row_id(r["platform"], r.pop("_key"))
    (d / "rows.json").write_text(json.dumps(out, indent=1))
    print(len(out), "rows", dict(Counter(r["platform"] for r in out)), "dropped", dict(dropped))


def fetch(d):
    rs = json.loads((d / "rows.json").read_text())
    (d / "covers").mkdir(exist_ok=True)

    def one(r):
        f = d / "covers" / f"{r['id']}.jpg"
        if f.exists() and f.stat().st_size > 2000:
            return None
        for u in (r.get("cover_url"), r.get("cover_fallback")):
            if not u:
                continue
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=30).read()
                if len(data) > 2000:
                    tmp = f.with_suffix(".src")
                    tmp.write_bytes(data)
                    subprocess.run(["sips", "-s", "format", "jpeg", str(tmp), "--out", str(f)], capture_output=True)
                    tmp.unlink()
                    if f.exists():
                        return None
            except Exception:
                continue
        return r["id"]
    with ThreadPoolExecutor(8) as ex:
        miss = [m for m in ex.map(one, rs) if m]
    print("covers", len(rs) - len(miss), "missing", miss)


def _colour(path):
    from PIL import Image, ImageStat
    im = Image.open(path).convert("RGB")
    im.thumbnail((256, 256))
    hsv = im.convert("HSV")
    h, s, v = (ImageStat.Stat(hsv.getchannel(c)) for c in "HSV")
    g = ImageStat.Stat(im.convert("L"))
    px = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    rg = [abs(r - g_) for r, g_, b in px]
    yb = [abs(0.5 * (r + g_) - b) for r, g_, b in px]
    mean = lambda a: sum(a) / len(a)
    def sd(a):
        m = mean(a)
        return math.sqrt(mean([(x - m) ** 2 for x in a]))
    colourful = math.sqrt(sd(rg) ** 2 + sd(yb) ** 2) + 0.3 * math.sqrt(mean(rg) ** 2 + mean(yb) ** 2)   # Hasler-Suesstrunk
    q = im.quantize(5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]
    counts = sorted(q.getcolors(), reverse=True)
    dom = ["#%02x%02x%02x" % tuple(pal[i * 3:i * 3 + 3]) for _, i in counts[:3]]
    return {"brightness": round(g.mean[0] / 255, 3), "contrast": round(g.stddev[0] / 255, 3),
            "saturation": round(s.mean[0] / 255, 3), "colourfulness": round(colourful, 1), "dominant": dom,
            "width": Image.open(path).size[0], "height": Image.open(path).size[1]}


def ocr_tool():
    """The text reader (macOS Vision, local and free), built from ocr.swift on first use."""
    tool = HERE / ".build" / "ocr"
    if not tool.exists() or tool.stat().st_mtime < (HERE / "ocr.swift").stat().st_mtime:
        tool.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(HERE / "ocr.swift"), "-o", str(tool)], check=True)
    return tool


def measure(d, ocr_tool):
    import thumbs as TH
    rs = json.loads((d / "rows.json").read_text())
    files = [d / "covers" / f"{r['id']}.jpg" for r in rs]
    have = [f for f in files if f.exists()]
    texts = subprocess.run([str(ocr_tool), *map(str, have)], capture_output=True, text=True).stdout.splitlines()
    scs = TH.scenes(have)
    out = {}
    for f, t, sc in zip(have, texts, scs):
        words = [w for w in json.loads(t or "[]") if w.get("conf", 0) >= 0.5]
        heights = [w["h"] for w in words]
        area = sum(w["w"] * w["h"] for w in words)
        cy = [w["y"] + w["h"] / 2 for w in words]
        out[f.stem] = {
            "text": " / ".join(w["t"] for w in words)[:300], "text_lines": len(words),
            "text_words": sum(len(w["t"].split()) for w in words),
            "text_area": round(area, 3), "text_line_height": round(max(heights), 3) if heights else 0,
            "text_centre_y": round(sum(cy) / len(cy), 2) if cy else None,
            "faces": len(sc["faces"]), "face_area": round(sum(b["w"] * b["h"] for b in sc["faces"]), 3),
            "hands": len(sc["hands"]), **_colour(f)}
    (d / "measure.json").write_text(json.dumps(out, indent=1))
    print("measured", len(out))


def sheets(d, per=12, cols=6):
    from PIL import Image, ImageDraw, ImageFont
    rs = json.loads((d / "rows.json").read_text())
    (d / "sheets").mkdir(exist_ok=True)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    by = {}
    for r in rs:
        by.setdefault(r["platform"], []).append(r)
    for p, items in by.items():
        wide = p == "youtube"
        tw, th = (480, 270) if wide else (270, 480)
        for n in range(0, len(items), per):
            part = items[n:n + per]
            rows_ = math.ceil(len(part) / cols)
            sheet = Image.new("RGB", (cols * (tw + 10), rows_ * (th + 44)), "white")
            dr = ImageDraw.Draw(sheet)
            for i, r in enumerate(part):
                f = d / "covers" / f"{r['id']}.jpg"
                x, y = (i % cols) * (tw + 10), (i // cols) * (th + 44)
                if f.exists():
                    im = Image.open(f).convert("RGB")
                    im.thumbnail((tw, th))
                    sheet.paste(im, (x + (tw - im.size[0]) // 2, y + 40 + (th - im.size[1]) // 2))
                dr.text((x + 4, y + 4), r["id"], fill="black", font=font)
            sheet.save(d / "sheets" / f"{p}-{n // per + 1}.jpg", quality=85)
    print("sheets", sorted(x.name for x in (d / "sheets").iterdir()))


def _share(rows_, field, value=None):
    vals = [r.get(field) for r in rows_ if r.get(field) is not None]
    if not vals:
        return {}
    c = Counter()
    for v in vals:
        for x in (v if isinstance(v, list) else [v]):
            c[x] += 1
    return {k: {"n": n, "pct": round(100 * n / len(rows_))} for k, n in c.most_common()}


def _median(a):
    a = sorted(x for x in a if x is not None)
    return a[len(a) // 2] if a else None


def _fit(src, dest, side=720):
    """The index's copy of a cover: longest side 720 px, jpeg. sips where it exists, else Pillow, else the file as it is."""
    if dest.exists():
        return
    if shutil.which("sips"):
        subprocess.run(["sips", "-Z", str(side), "-s", "formatOptions", "72", str(src), "--out", str(dest)], capture_output=True)
    if not dest.exists():
        try:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im.thumbnail((side, side))
            im.save(dest, "JPEG", quality=72)
        except Exception:
            shutil.copyfile(src, dest)


# ---- the move: read from the breakdown where it already says it, no model call
_TYPE = re.compile(r'"|\b(title|headline|caption|captions|text|word|words|letters|script|serif|box|label|labels|logo|subtitle)\b', re.I)
_SCALE = re.compile(r"\b(giant|huge|oversized|enormous|massive|towering|tower of|pile of|piles of|stack of|overflowing|"
                    r"mountain of|wall of|miniature|tiny|shrunk|shrunken)\b", re.I)
_FACE = re.compile(r"\b(mouth (wide )?open|mouths open|scream\w*|eyes wide|shouting|grimac\w*|jaw dropped)\b", re.I)
_LENS = re.compile(r"\b(hold\w*|push\w*|thrust\w*|shov\w*|point\w*)\b[^,]*\b(to|at|toward|towards|into) (the )?(camera|lens)\b"
                   r"|\bclose to the lens\b", re.I)
# Switch `move-rules` on: an impossible object is read from the words, and a plain open mouth or a thing only held to
# the camera no longer counts (the face must fill the frame; the thing must be pushed at the lens or the shot that close)
_OBJECT = re.compile(r"\b(made (of|out of|from)|melting|melted|dripping off|floating in (the )?air|with (legs|wings|teeth|a face)|"
                     r"half[- ]\w+[, ]+half|shaped like|turned into|growing out of|sprouting|inside out)\b|\w-shaped\b", re.I)
_FACE_HARD = re.compile(r"\b(mouth (wide|gaping) open|mouths (wide )?open wide|scream\w*|eyes wide|wide[- ]eyed|shouting|grimac\w*|"
                        r"jaw dropped|jaw on the floor)\b", re.I)
_MOUTH = re.compile(r"\bmouths? open\b", re.I)
_PUSH = re.compile(r"\b(push\w*|thrust\w*|shov\w*|jab\w*)\b[^,]*\b(to|at|toward|towards|into) (the )?(camera|lens)\b"
                   r"|\b(close to|into|against|touching) the lens\b", re.I)
_BEFORE = re.compile(r"\bbefore\s*(/|and|&|vs\.?|,)\s*after\b", re.I)
_PRICE = re.compile(r"[$£€]\s?\d[\d,.]*")
_STOP = set("the a an and or of to in on at for with by from is are was this that these those it its his her their our "
            "your you me my we us he she they them what when who why how not all one two out up off about into over "
            "under just very more most real new now white black red yellow green blue pink gold purple small big tiny "
            "huge large caps text box word words line lines caption title headline plus".split())


def _stems(text):
    out = set()
    for w in re.findall(r"[a-z]+", text.lower().replace("'s", "")):
        w = w[:-1] if len(w) > 3 and w.endswith("s") else w
        if len(w) >= 3 and w not in _STOP:
            out.add(w)
    return out


def _quotes_whole(shows):
    """`shows` with curly quotes made straight and no comma or semicolon inside a quote, so splitting it into parts
    never cuts the cover's own words into a part read as picture."""
    shows = shows.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r'"[^"]*"', lambda m: re.sub(r"[,;]", " ", m.group(0)), shows)


def derive_move(b):
    """A cover's breakdown -> (move, the other moves it also makes, why), from its own fields. `unrated` when it says
    none. Order: the most specific move first; `one-odd-thing` (absurd 1) and `as-shot` (absurd 0 and no words on the
    cover) only when nothing else is said. A cover with words on it and nothing else said stays `unrated`: whether its
    line is shown literally needs an eye read. Switch `move-rules` adds impossible-object and tightens face-at-limit and
    thing-to-lens. Switch `move-picture`: face-at-limit and thing-to-lens read the picture only (never the cover's
    own words), and line-shown-literally needs a picture past real (absurd 2 or 3), not a caption naming what is
    held up (README, "The move")."""
    if not b:
        return UNRATED, [], ""
    tight, words_out = switch("move-rules"), switch("move-picture")
    shows, marks, absurd = b.get("shows") or "", b.get("marks") or [], b.get("absurd")
    pic = (", ".join(part for part in re.split(r"[,;]", _quotes_whole(shows)) if not _TYPE.search(part))
           if words_out else shows)
    frame, shot, expr = str(b.get("frame") or ""), b.get("shot"), b.get("expression")
    made = []                                           # (move, why), the order below is the order of precedence
    if _BEFORE.search(shows):
        made.append(("before-after", "shows: " + _BEFORE.search(shows).group(0)))
    if tight and absurd in (2, 3) and frame not in ("graphic", "text-only", "screen"):
        thing = [m.group(0) for part in re.split(r"[,;]", shows) if not _TYPE.search(part) for m in _OBJECT.finditer(part)]
        if thing:
            made.append(("impossible-object", f"absurd {absurd}, shows: {thing[0]}"))
    if absurd in (2, 3):
        scale = [m.group(0) for part in re.split(r"[,;]", shows) if not _TYPE.search(part) for m in _SCALE.finditer(part)]
        if scale:
            made.append(("wrong-scale", f"absurd {absurd}, shows: {scale[0]}"))
        made.append(("impossible-scene", "absurd 3") if absurd == 3 else ("absurd-subject", "absurd 2"))
    face_fills = frame == "face" and shot in ("close", "extreme-close")
    if not tight and _FACE.search(pic):
        made.append(("face-at-limit", "shows: " + _FACE.search(pic).group(0)))
    elif not tight and expr == "shock" and frame.startswith("face"):
        made.append(("face-at-limit", "expression shock, frame " + frame))
    elif tight and _FACE_HARD.search(pic):
        made.append(("face-at-limit", "shows: " + _FACE_HARD.search(pic).group(0)))
    elif tight and face_fills and expr in ("shock", "intense") and _MOUTH.search(pic):
        made.append(("face-at-limit", f"expression {expr}, frame face, shot {shot}, shows: " + _MOUTH.search(pic).group(0)))
    elif tight and face_fills and expr == "shock":
        made.append(("face-at-limit", f"expression shock, frame face, shot {shot}"))
    if set(marks) & {"circle", "arrow"}:
        made.append(("pointed-at", "marks: " + "+".join(sorted(set(marks) & {"circle", "arrow"}))))
    if "price" in marks or _PRICE.search(shows):
        made.append(("price-as-hook", "marks: price" if "price" in marks else "shows: " + _PRICE.search(shows).group(0)))
    quoted = re.findall(r'"([^"]+)"', shows)
    if quoted and (not words_out or absurd in (2, 3)):    # a caption naming what a real frame holds up is a label
        both = _stems(" ".join(quoted)) & _stems(re.sub(r'"[^"]+"', " ", shows))
        if both:
            made.append(("line-shown-literally", "words and picture both: " + ", ".join(sorted(both))))
    if not tight and _LENS.search(pic):
        made.append(("thing-to-lens", "shows: " + _LENS.search(pic).group(0)))
    elif tight and _PUSH.search(pic):
        made.append(("thing-to-lens", "shows: " + _PUSH.search(pic).group(0)))
    elif tight and shot == "extreme-close" and _LENS.search(pic):
        made.append(("thing-to-lens", "shot extreme-close, shows: " + _LENS.search(pic).group(0)))
    wordless = b.get("text_style") == "none" or b.get("text_words") == 0
    if not made and absurd == 1:
        made.append(("one-odd-thing", "absurd 1"))
    if not made and absurd == 0 and wordless:           # with words on it the line may be the move: left for an eye read
        made.append(("as-shot", "absurd 0, no words"))
    if not made:
        return UNRATED, [], ""
    return made[0][0], [m for m, _ in made[1:]], made[0][1]


def set_move(row, redo=False):
    """Put `move` on one index row. A move written by eye (breakdown `move`, or `moves --set`) is never overwritten;
    a rule-made one is re-read only with redo."""
    b = row.get("breakdown") or {}
    if b.get("move") in MOVES:
        row.update(move=b["move"], move_also=[m for m in b.get("move_also") or [] if m in MOVES], move_by="eye", move_why="")
    elif row.get("move_by") == "eye" and row.get("move") in MOVES:
        pass
    elif redo or row.get("move") in (None, "", UNRATED):
        move, also, why = derive_move(b)
        row.update(move=move, move_also=also, move_by="breakdown" if move != UNRATED else None, move_why=why)
    return row


# ---- the index: one covers.json for every pull, each row carrying its avatar (None = a discovery surface)
def _avatars_of(row):
    return [a for a in [row.get("avatar")] + list(row.get("avatar_also") or []) if a]


def _merge(existing, new):
    """The rows a pull brings, merged into the index. Switch `merge-keeps` on: _merge_keeps; off: _merge_groups."""
    return _merge_keeps(existing, new) if switch("merge-keeps") else _merge_groups(existing, new)


def _ran(new):
    """The discovery sources a pull brought: the ones its indexed rows carry. A source whose run kept no indexed row
    (an empty or capped run, covers that never downloaded, a raw/<source>.json left in a reused folder) replaces
    nothing, so its old rows and their eye reads stay. Avatar sources (av-…) are not discovery sources."""
    names = {r.get("source") for r in new if r.get("avatar") is None}
    return {n for n in names if n and not str(n).startswith("av-")}


def _dropped_by(r, groups, ran):
    """True when this discovery row is one the new pull replaces. Switch `merge-by-pull` on: only a row whose source
    the pull brought an indexed row from (a row with no source goes with any discovery pull); off: every discovery
    row, when the pull brings discovery rows."""
    if r.get("avatar") is not None:
        return False
    if not switch("merge-by-pull"):
        return None in groups
    if not ran:                                         # no source named anywhere in the pull: the whole group
        return None in groups
    return not r.get("source") or r["source"] in ran


def _keep_eye(row, old):
    """An eye read on the row being replaced is carried onto the new row, unless the pull's own breakdown names a move
    (a newer eye read)."""
    if not old or old.get("move_by") != "eye" or old.get("move") not in MOVES:
        return row
    if (row.get("breakdown") or {}).get("move") in MOVES:
        return row
    row.update(move=old["move"], move_also=list(old.get("move_also") or []), move_by="eye", move_why=old.get("move_why") or "")
    return row


def _merge_keeps(existing, new):
    """New rows replace the rows with their id. A discovery pull replaces the discovery rows of the sources it brought
    (switch `merge-by-pull`; off: every discovery row), so a narrower pull keeps the other sources' rows and their
    eye reads. An avatar's covers are only ever added to or updated, so a second, narrower pull for an avatar keeps the rest.
    A discovery row the new discovery pull drops stays when an avatar also sees it, as that avatar's row. An eye read
    on a replaced row is kept (_keep_eye). One post in two groups is one row: the discovery row is the main one, the
    avatar that also sees it goes in `avatar_also`."""
    groups = {r.get("avatar") for r in new}
    ran = _ran(new)
    new_ids = {r["id"] for r in new}
    before = {r["id"]: r for r in existing}
    kept, carried = [], {}
    for r in existing:
        r = dict(r)
        if r["id"] in new_ids and r.get("avatar") in groups:            # replaced by the new row with its id
            carried[r["id"]] = list(r.get("avatar_also") or [])
            continue
        if _dropped_by(r, groups, ran):                                  # a discovery row the new discovery pull drops
            also = list(r.get("avatar_also") or [])
            if not also:
                continue
            r["avatar"] = also[0]                                         # an avatar sees it: it stays, as that avatar's
            r.pop("avatar_also", None)
            if also[1:]:
                r["avatar_also"] = also[1:]
        kept.append(r)
    by_id = {r["id"]: r for r in kept}
    for r in new:
        r = _keep_eye(dict(r), before.get(r["id"]))
        old = by_id.get(r["id"])
        if old is None:
            r.pop("avatar_also", None)
            also = [a for a in carried.get(r["id"]) or [] if a != r.get("avatar")]
            if also:
                r["avatar_also"] = also
            kept.append(r)
            by_id[r["id"]] = r
            continue
        if r.get("avatar") is None and old.get("avatar") is not None:      # the discovery row becomes the main one
            r["avatar_also"] = _avatars_of(old)
            kept[kept.index(old)] = r
            by_id[r["id"]] = r
        else:
            also = _avatars_of(old)[1 if old.get("avatar") else 0:]
            if r.get("avatar") and r["avatar"] not in _avatars_of(old):
                also.append(r["avatar"])
            if also:
                old["avatar_also"] = also
    return kept


def _merge_groups(existing, new):
    """New rows replace the rows of their own pull group (the avatar they carry, None = the discovery surfaces); rows
    of every other group stay. One post in two groups is one row: the discovery row is the main one, the avatar that
    also sees it goes in `avatar_also`."""
    groups = {r.get("avatar") for r in new}
    kept = [dict(r) for r in existing if r.get("avatar") not in groups]
    carried = {r["id"]: [a for a in r.get("avatar_also") or [] if a not in groups]      # a replaced row's other avatars
               for r in existing if r.get("avatar") in groups}
    for r in kept:
        also = [a for a in r.get("avatar_also") or [] if a not in groups]
        r.pop("avatar_also", None)
        if also:
            r["avatar_also"] = also
    by_id = {r["id"]: r for r in kept}
    for r in new:
        old = by_id.get(r["id"])
        if old is None:
            r = dict(r)
            r.pop("avatar_also", None)
            if carried.get(r["id"]):
                r["avatar_also"] = carried[r["id"]]
            kept.append(r)
            by_id[r["id"]] = r
            continue
        if r.get("avatar") is None and old.get("avatar") is not None:      # the discovery row becomes the main one
            r = dict(r)
            r["avatar_also"] = _avatars_of(old)
            kept[kept.index(old)] = r
            by_id[r["id"]] = r
        else:
            also = [a for a in _avatars_of(old)[1 if old.get("avatar") else 0:]]
            if r.get("avatar") and r["avatar"] not in _avatars_of(old):
                also.append(r["avatar"])
            if also:
                old["avatar_also"] = also
    return kept


def _write_index(out, swipes, avatar=None):
    """covers.json, patterns.json (the discovery surfaces' sums, as before) and avatars.json (one record per avatar)."""
    (out / "covers.json").write_text(json.dumps(swipes, indent=1))
    general = [s for s in swipes if not s.get("avatar")]
    pats = {}
    for p in sorted({s["platform"] for s in general}):
        g = [s for s in general if s["platform"] == p]
        b = [s["breakdown"] for s in g if s["breakdown"]]
        m = [s["measure"] for s in g if s["measure"]]
        pats[p] = {"covers": len(g), "read_by_eye": len(b),
                   "median_views": _median([s.get("views") for s in g]), "median_likes": _median([s.get("likes") for s in g]),
                   "median_age_days": _median([s.get("age_days") for s in g]),
                   "measured": {"with_text_pct": round(100 * sum(1 for x in m if x["text_words"]) / max(1, len(m))),
                                "median_words_when_text": _median([x["text_words"] for x in m if x["text_words"]]),
                                "median_text_line_height_pct": _median([round(100 * x["text_line_height"], 1) for x in m if x["text_words"]]),
                                "with_face_pct": round(100 * sum(1 for x in m if x["faces"]) / max(1, len(m))),
                                "median_face_area_pct": _median([round(100 * x["face_area"], 1) for x in m if x["faces"]]),
                                "median_saturation": _median([x["saturation"] for x in m]),
                                "median_contrast": _median([x["contrast"] for x in m]),
                                "median_brightness": _median([x["brightness"] for x in m]),
                                "median_colourfulness": _median([x["colourfulness"] for x in m])},
                   "by_eye": {k: _share(b, k) for k in BREAKDOWN}}
        pats[p]["by_eye"]["text_words"] = {"median": _median([x.get("text_words") for x in b])}
    if general or not (out / "patterns.json").exists():
        (out / "patterns.json").write_text(json.dumps(pats, indent=1))
    f = out / "avatars.json"
    avs = json.loads(f.read_text()) if f.exists() else {}
    if avatar:
        keep = {k: avatar[k] for k in ("who", "platforms", "hashtags", "accounts", "topics", "on_topic", "floor", "max_age_days") if avatar.get(k)}
        avs[avatar["avatar"]] = {**avs.get(avatar["avatar"], {}), **keep}
    names = sorted({a for s in swipes for a in _avatars_of(s)})
    for a in names:
        g = [s for s in swipes if a in _avatars_of(s)]
        avs[a] = {**avs.get(a, {}), "covers": len(g), "platforms_seen": dict(Counter(s["platform"] for s in g)),
                  "median_likes": _median([s.get("likes") for s in g]), "median_views": _median([s.get("views") for s in g]),
                  "moves": dict(Counter(s.get("move") or UNRATED for s in g)),
                  "pulled": max((s.get("pulled") or "" for s in g), default="")}
    avs = {a: v for a, v in avs.items() if a in names}
    if avs or f.exists():
        f.write_text(json.dumps(avs, indent=1))
    return pats


def index(d, out):
    rs = json.loads((d / "rows.json").read_text())
    ms = json.loads((d / "measure.json").read_text())
    bd = json.loads((d / "breakdown.json").read_text()) if (d / "breakdown.json").exists() else {}
    av = read_avatar(d / "avatar.json") if (d / "avatar.json").exists() else None
    out.mkdir(parents=True, exist_ok=True)
    (out / "covers").mkdir(exist_ok=True)
    swipes = []
    for r in rs:
        f = d / "covers" / f"{r['id']}.jpg"
        if not f.exists():
            continue
        _fit(f, out / "covers" / f.name)
        s = {**r, "kind_of_swipe": "cover", "use": ["paid", "organic"], "frame_file": f"covers/{f.name}",
             "measure": ms.get(r["id"], {}), "breakdown": bd.get(r["id"], {}),
             "pulled": time.strftime("%Y-%m-%d")}
        s.setdefault("avatar", None)
        swipes.append(set_move(s) if switch("move") else s)
    had = json.loads((out / "covers.json").read_text()) if (out / "covers.json").exists() else []
    swipes = _merge(had, swipes)
    pats = _write_index(out, swipes, av)
    print("swipes", len(swipes), {p: v["covers"] for p, v in pats.items()},
          "avatars", dict(Counter(s["avatar"] for s in swipes if s.get("avatar"))))


def import_pull(pull, out, avatar, rows_file=None, pulled=None):
    """A pull made outside this tool -> the index, every cover carrying its avatar. The pull is a folder with a kept
    list (keep.json, else rows.json: the hashtag scraper's own rows or this tool's rows) and covers/<post code or id>.jpg;
    measure.json and breakdown.json beside them are carried when present. Nothing in the pull folder is changed.
    A row with no picture is left out and counted. Returns the counts."""
    _need("avatar", "The avatar import")
    av = read_avatar(avatar)
    src = Path(rows_file) if rows_file else next((pull / n for n in ("keep.json", "rows.json") if (pull / n).exists()), None)
    if src is None or not src.exists():
        sys.exit(f"{pull}: no keep.json or rows.json (name the list with --rows)")
    pulled = pulled or time.strftime("%Y-%m-%d", time.gmtime(src.stat().st_mtime))
    load = lambda n: json.loads((pull / n).read_text()) if (pull / n).exists() else {}
    ms, bd = load("measure.json"), load("breakdown.json")
    now = datetime.now(timezone.utc)
    out.mkdir(parents=True, exist_ok=True)
    (out / "covers").mkdir(exist_ok=True)
    swipes, seen, left = [], set(), Counter()
    for x in json.loads(src.read_text()):
        if x.get("id") and x.get("platform") and x.get("url"):          # already this tool's row
            r, names = dict(x), [x["id"]]
        else:
            r = normalize_avatar("av-ig-tags", x)
            if not r or not r.get("url"):
                left["no link"] += 1
                continue
            key = _post_key(r["url"])
            r["id"] = _row_id(r["platform"], key)
            r["source"] = "av-ig-tags"
            names = [x.get("shortCode"), key, r["id"]]
        pic = next((pull / "covers" / f"{n}.jpg" for n in names if n and (pull / "covers" / f"{n}.jpg").exists()), None)
        if r["id"] in seen:
            left["duplicate"] += 1
            continue
        if pic is None:
            left["no picture"] += 1
            continue
        seen.add(r["id"])
        age = _age_days(r.get("posted"), now)
        r["age_days"] = round(age, 1) if age is not None else None
        _fit(pic, out / "covers" / f"{r['id']}.jpg")
        got = lambda table: next((table[n] for n in [r["id"]] + names if n and n in table), {})
        s = {**r, "avatar": av["avatar"], "kind_of_swipe": "cover", "use": ["paid", "organic"],
             "frame_file": f"covers/{r['id']}.jpg", "measure": got(ms), "breakdown": got(bd), "pulled": pulled}
        swipes.append(set_move(s) if switch("move") else s)
    had = json.loads((out / "covers.json").read_text()) if (out / "covers.json").exists() else []
    merged = _merge(had, swipes)
    _write_index(out, merged, av)
    counts = {"avatar": av["avatar"], "imported": len(swipes), "left_out": dict(left), "index": len(merged)}
    print("imported", counts)
    return counts


def moves(out, sets=None, redo=False):
    """Fill `move` on every index row that lacks it, from its breakdown (derive_move). `sets` {id: move} are eye reads
    and win. Rows whose breakdown says no move stay `unrated`. Returns the count per move."""
    _need("move", "The move field")
    swipes = json.loads((out / "covers.json").read_text())
    sets = dict(sets or {})
    bad = {i: m for i, m in sets.items() if m not in MOVES}
    missing = set(sets) - {s["id"] for s in swipes}
    if bad or missing:
        sys.exit(f"moves: not a move {bad} (the moves: {', '.join(MOVES)}); not in the index {sorted(missing)}")
    for s in swipes:
        if s["id"] in sets:
            s.update(move=sets[s["id"]], move_also=[], move_by="eye", move_why="")
        else:
            set_move(s, redo)
    _write_index(out, swipes)
    counts = dict(Counter(s["move"] for s in swipes).most_common())
    print("moves", counts)
    print("unrated", [s["id"] for s in swipes if s["move"] == UNRATED])
    return counts


def find_covers(out, avatar=None, move=None, platform=None, rank=None, limit=None, min_views=None, text=None, **eye):
    """The covers a cover step may follow, best first.

    avatar  the avatar's name, in any spelling: only covers that avatar sees. When the avatar has no covers in the
            index at all, the discovery surfaces' covers are returned instead (`scope` general-fallback, `note` says
            so). When it has covers but none pass the other filters, `scope` stays avatar, `covers` is empty and
            `note` says so: a cover never follows a discovery cover just because a filter emptied the avatar's list.
    move    one of MOVES (or `unrated`); matches a cover's main move or one it also makes.
    rank    `likes` or `views`. Default: likes with an avatar, else views (likes where a platform gives no views).
    eye     breakdown fields: frame, text_style, look, grade, absurd.
    Returns {"scope": "avatar" | "general" | "general-fallback", "avatar", "note", "covers": [index rows]}."""
    swipes = json.loads((Path(out) / "covers.json").read_text())
    note = ""
    if avatar and not switch("avatar"):
        avatar, note = None, "the avatar switch is off: the discovery surfaces' covers only"
    if move and not switch("move"):
        move, note = None, (note + "; " if note else "") + "the move switch is off: --move ignored"
    plat = (platform or "").replace("ig", "instagram").replace("tt", "tiktok").replace("yt", "youtube")

    def ok(s):
        b = s.get("breakdown", {})
        if plat and not s["platform"].startswith(plat):
            return False
        for k, v in eye.items():
            if v not in (None, "") and str(b.get(k)) != str(v):
                return False
        if move and move != (s.get("move") or UNRATED) and move not in (s.get("move_also") or []):
            return False
        if text == "none" and s["measure"].get("text_words"):
            return False
        if min_views and (s.get("views") or 0) < int(min_views):
            return False
        return True

    general = [s for s in swipes if not s.get("avatar")]
    scope, pool = "general", general
    if avatar:
        avatar = read_avatar(avatar)["avatar"]
        theirs = [s for s in swipes if avatar in _avatars_of(s)]
        hits = [s for s in theirs if ok(s)]
        if hits:
            scope, pool = "avatar", theirs
        elif theirs and switch("avatar-scope"):
            scope, pool = "avatar", []
            note = f"avatar {avatar} has {len(theirs)} covers, none pass these filters: no discovery covers given instead"
        else:
            scope = "general-fallback"
            note = (f"avatar {avatar} has no covers in the index" if not theirs else
                    f"avatar {avatar} has {len(theirs)} covers, none pass these filters") + ": these are the discovery surfaces' covers"
    rank = rank or ("likes" if scope == "avatar" else None)
    key = (lambda s: -(s.get(rank) or 0)) if rank else (lambda s: -(s.get("views") or s.get("likes") or 0))
    covers = sorted(filter(ok, pool), key=key)
    return {"scope": scope, "avatar": avatar, "note": note, "covers": covers[:int(limit)] if limit else covers}


def find(out, a):
    flags = {x for x in a if x in ("--json",)}
    a = [x for x in a if x not in flags]
    opt = dict(zip(a[::2], a[1::2]))
    res = find_covers(out, avatar=opt.get("--avatar"), move=opt.get("--move"), platform=opt.get("--platform"),
                      rank=opt.get("--rank"), limit=opt.get("--limit"), min_views=opt.get("--min-views"),
                      text=opt.get("--text"), **{k: opt.get("--" + k) for k in ("frame", "text_style", "look", "grade", "absurd")})
    if "--json" in flags:
        print(json.dumps(res, indent=1))
        return res
    if res["note"]:
        print("NOTE:", res["note"], file=sys.stderr)
    for s in res["covers"]:
        line = [s["id"], s["platform"], s.get("views"), s.get("likes"), (s.get("posted") or "")[:10], s["url"],
                s.get("breakdown", {}).get("frame"), s["frame_file"]]
        if switch("move"):
            line.append(s.get("move") or UNRATED)
        if switch("avatar"):
            line.append("+".join(_avatars_of(s)) or "-")
        print(*line)
    return res


def main(a):
    try:
        _main(a)
    except AvatarError as e:                            # the command line stops with the words; Python callers get the error
        sys.exit(str(e))


def _main(a):
    cmd, d = a[0], Path(a[1])
    val = lambda flag: a[a.index(flag) + 1] if flag in a else None

    def after(flag):                                    # the words after a flag, up to the next option
        if flag not in a:
            return None
        rest = a[a.index(flag) + 1:]
        return rest[:next((i for i, x in enumerate(rest) if x.startswith("--")), len(rest))]
    if cmd == "pull":
        pull(d, val("--key-name") or "APIFY_TOKEN", after("--only"), avatar=val("--avatar"))
    elif cmd == "rows":
        rows(d)
    elif cmd == "fetch":
        fetch(d)
    elif cmd == "measure":
        measure(d, ocr_tool())
    elif cmd == "sheets":
        sheets(d)
    elif cmd == "index":
        index(d, Path(a[2]))
    elif cmd == "import":
        if not val("--avatar"):
            sys.exit("import: name the avatar (--avatar <avatar file or name>)")
        import_pull(d, Path(a[2]), val("--avatar"), rows_file=val("--rows"), pulled=val("--pulled"))
    elif cmd == "moves":
        sets = json.loads(Path(val("--from")).read_text()) if val("--from") else {}
        sets.update(x.split("=", 1) for x in after("--set") or [])
        moves(d, sets, redo="--redo" in a)
    elif cmd == "find":
        find(d, a[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
