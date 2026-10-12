#!/usr/bin/env python3
"""Harvest the rooms an avatar actually lives in.

    python3 harvest.py --seeds seeds/<brand>--<avatar>--<sub>.json \
        [--top 12] [--depth 60] [--comments 100] [--dry-run]

Everything that already exists here harvests by CREATOR HANDLE — you say whose
posts you want and it fetches them. This harvests by AVATAR: hashtags, searches
and phrases from the seed file, ranked on engagement, and the creators are an
OUTPUT rather than an input. That is the seam that was missing.

The comments are the payload. A post's caption is a creator broadcasting; the
comment section is the avatar talking to each other unprompted, with like
counts as weight. Scraped to depth, not the ~15 the posts actor carries.

Reads only from the platforms. Writes records here and media to Drive.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import apify as A
import locale_filter as LF

HERE = Path(__file__).resolve().parent
for _r in HERE.parents:                # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
DRIVE = swipe_home.root("organic")


def slug(s, n=60):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower())[:n].strip("-") or "untitled"


def discover(seed, depth):
    """One seed -> raw posts, in one shape."""
    k, p, v = seed["kind"], seed["platform"], seed["value"]
    out = []
    if p in ("tiktok", "any"):
        payload = {"resultsPerPage": depth, "shouldDownloadVideos": True}
        if k == "hashtag":
            payload["hashtags"] = [v]
        else:
            payload["searchQueries"] = [v]
            payload["searchSection"] = "/video"
        try:
            out += [A.as_post(i, "tiktok") for i in A.run(A.POSTS_TT, payload) if i.get("id")]
        except Exception as e:
            A.say(f"    tiktok failed: {str(e)[:90]}")
    if p in ("instagram", "any") and k == "hashtag":
        try:
            items = A.run(A.POSTS_IG, {"search": v, "searchType": "hashtag",
                                       "resultsType": "posts", "resultsLimit": depth,
                                       "addParentData": True})
            out += [A.as_post(i, "instagram") for i in items if i.get("shortCode")]
        except Exception as e:
            A.say(f"    instagram failed: {str(e)[:90]}")
    for o in out:
        o["_seed"] = v
        o["_seed_why"] = seed["why"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--top", type=int, default=12, help="posts kept per seed")
    ap.add_argument("--depth", type=int, default=60, help="posts indexed per seed before ranking")
    ap.add_argument("--comments", type=int, default=100)
    ap.add_argument("--only", default=None, help="run one seed value only")
    ap.add_argument("--locale", default=None,
                    help="keep posts that read as this market, e.g. US. The tags "
                         "are global — #freshcut returned a Berlin barber on the "
                         "first pass — and an avatar is not.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    S = json.loads(Path(args.seeds).read_text())
    key = f"{S['brand']}/{S['avatar']}/{S['sub_avatar']}"
    root = HERE / "records/culture-digs" / S["brand"] / S["avatar"] / S["sub_avatar"]
    media_root = DRIVE / S["brand"] / S["avatar"] / S["sub_avatar"]
    seeds = [s for s in S["seeds"] if not args.only or s["value"] == args.only]
    A.say(f"{key} · {len(seeds)} seed(s) · top {args.top} of {args.depth} each")

    if args.dry_run:
        for s in seeds:
            A.say(f"  would run [{s['kind']}/{s['platform']}] {s['value']}")
        return

    # One seed at a time, WRITTEN at a time. Discover, read the comments,
    # record — then the next seed. A failure on seed four leaves seeds one to
    # three on disk; the old shape wrote everything at the very end and a
    # failure anywhere lost the whole run.
    root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seen = set()          # (platform, id) already written this run
    all_posts, seeds_done, written = [], [], 0

    def record(p, cm):
        pid = f"{p['platform']}-{slug(p['author'])}-{p['id']}"
        d = root / "posts" / pid
        d.mkdir(parents=True, exist_ok=True)
        media_rel = f"{S['brand']}/{S['avatar']}/{S['sub_avatar']}/{pid}"
        if p.get("media"):
            ext = ".mp4" if p["kind"] == "video" else ".jpg"
            A.fetch(p["media"], media_root / pid / f"post{ext}")
        if p.get("cover"):
            A.fetch(p["cover"], media_root / pid / "cover.jpg")

        L = [f"# {p['author'] or '(unknown)'} — {p['platform']}", "",
             f"- url: {p['url']}", f"- posted: {p.get('posted') or 'unknown'}",
             f"- views: {p['views']:,} · likes: {p['likes']:,} · comments: {p['comments']:,}"
             + (f" · shares: {p['shares']:,}" if p.get("shares") else "")
             + (f" · saves: {p['saves']:,}" if p.get("saves") else ""),
             f"- found by: `{p['_seed']}` — {p['_seed_why']}",
             f"- sound: {p.get('music') or '—'}",
             f"- **Drive:** {swipe_home.label('organic', media_rel)}",
             f"- first seen: {now}", "",
             "## Caption", "", p["caption"] or "*(none)*", ""]
        if p["hashtags"]:
            L += ["## Hashtags", "", " ".join(f"#{h}" for h in p["hashtags"]), ""]
        L += ["## Format", "", "> UNREAD — set by formats.py", ""]
        (d / "post.md").write_text("\n".join(L))

        if cm is None:
            (d / "comments.md").write_text(
                "# Comments\n\n> MISSING — the scrape failed for this post. Not empty; unread.\n")
        else:
            rows = sorted(cm or [], key=lambda c: -(c.get("likes") or 0))
            C = [f"# Comments — {len(rows)} captured of {p['comments']:,} on the post", "",
                 "The room talking to each other, ranked by likes. **This is the payload** —",
                 "a caption is a creator broadcasting, this is the avatar unprompted.", ""]
            C += [f"- **{c.get('likes') or 0}** · @{c.get('owner') or '?'} — {c.get('text') or ''}"
                  for c in rows]
            (d / "comments.md").write_text("\n".join(C) + "\n")

    def checkpoint():
        # Rewritten after every seed, so the record on disk is always the
        # truth of what has actually been harvested so far — MERGED with
        # every earlier run, never replacing it. A later small run must not
        # shrink the bank (a 4-post freshcut re-run once clobbered a
        # 69-post record down to 4 in this file).
        prior = {"seeds_run": [], "posts": []}
        f = root / "harvest.json"
        if f.exists():
            try:
                prior = json.loads(f.read_text())
            except Exception:
                pass
        by_key = {(p.get("platform"), p.get("id")): p for p in prior.get("posts", [])}
        for p in all_posts:
            by_key[(p.get("platform"), p.get("id"))] = \
                {k: v for k, v in p.items() if not k.startswith("_")}
        merged_seeds = list(dict.fromkeys(prior.get("seeds_run", []) + seeds_done))
        f.write_text(json.dumps(
            {"harvested": now, "seeds_run": merged_seeds,
             "posts": list(by_key.values())},
            indent=1) + "\n")

    for s in seeds:
        A.say(f"\n[{s['kind']}/{s['platform']}] {s['value']}")
        raw = discover(s, args.depth)
        raw2, dropped = (LF.keep(raw, args.locale) if args.locale else (raw, []))
        kept = sorted(raw2, key=A.score, reverse=True)[:args.top]
        A.say(f"  {len(raw)} found"
              + (f" · {len(dropped)} dropped as off-market" if args.locale else "")
              + f" · keeping top {len(kept)} by engagement")
        for d, why in dropped[:3]:
            A.say(f"      dropped @{d.get('author')} — {why}")
        fresh = [p for p in kept if (p["platform"], p["id"]) not in seen]

        packs = {}
        for plat in ("tiktok", "instagram"):
            urls = [p["url"] for p in fresh if p["platform"] == plat and p["url"]]
            if not urls:
                continue
            A.say(f"  reading {plat} comment sections ({len(urls)} posts, "
                  f"up to {args.comments} each)")
            got = A.comments_for(urls, plat, args.comments)
            if got is not None:
                packs.update({u: c for u, c in got.items()})

        for p in fresh:
            record(p, packs.get(p["url"]))
            seen.add((p["platform"], p["id"]))
            all_posts.append(p)
            written += 1
        seeds_done.append(s["value"])
        checkpoint()
        A.say(f"  {len(fresh)} recorded — on disk now, whatever happens to the next seed")

    if not written:
        A.say("\nnothing harvested — the seeds returned no posts")
        return
    A.say(f"\n{written} posts recorded -> {root.relative_to(HERE)}")
    A.say(f"media -> {swipe_home.label('organic', S['brand'])}/…")


if __name__ == "__main__":
    main()
