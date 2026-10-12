#!/usr/bin/env python3
"""Pull a creator's TikTok slideshows into the My Feeds library (organic).

    python3 slideshows.py <handle> <handle> --top 8
    python3 slideshows.py male_aestheticcc --top 8 --group clipping-examples

One command per account, and the account comes out in exactly the shape the first account
was filed in on 2026-09-14 — `posts.json`, one `posts/NN_<handle>-<id>.md`
per slideshow, and the slides on Drive in the organic swipe home (found through
`swipe_home`) under `<handle>/posts/<stem>/photos/NN.jpg` —
because that shape is what the carousel lanes open a run from
(`teardown-lanes/carousel-creator/chain.py start --swipe <handle>`) and what
intake already counts as a carousel. the first account was built by hand in a session;
this is that session as a tool, so the next account costs one line.

**Slideshows only.** A creator's videos are the video machine's business and
never land here. Ranked by views; `--top N` keeps the N hottest.

**What it costs.** One profile read (~cents) + one post read for the picks
(needs `shouldDownloadSlideshowImages`, or the actor answers with empty
media) + one comments read. Roughly $__ an account at --top 8.

`--group` records which set an account belongs to (the designer's example list, a
competitor sweep) in posts.json; nothing else changes.
"""
import argparse, json, os, re, sys
from datetime import date
from pathlib import Path


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    This used to be `HERE.parents[2]`, which was the root only while this file
    sat in lab/. It moved to components/ on 2026-09-22 and every lookup
    silently pointed one level too high, at ~/Projects. A marker cannot go
    quietly wrong the next time something moves.

    The walk is run-kit's paths.repo() (SI-111 (organic one locator)).
    """
    return repo(start)


HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)
sys.path.insert(0, str(_workspace() / "components" / "apify"))
import apify as A  # noqa: E402

for _r in HERE.parents:                # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402

DRIVE = swipe_home.root("organic")


def profile_slideshows(handle, depth):
    items = A.run(A.POSTS_TT, {"profiles": [handle], "resultsPerPage": depth,
                               "shouldDownloadVideos": False})
    posts = [i for i in items if i.get("isSlideshow") and i.get("id")]
    posts.sort(key=lambda p: -(p.get("playCount") or 0))
    return posts, len(items)


def with_slides(urls):
    """The same posts again, this time with their slides — the profile read
    never carries them, whatever flags it is given (proved 2026-09-22)."""
    items = A.run(A.POSTS_TT, {"postURLs": urls, "shouldDownloadVideos": True,
                               "shouldDownloadSlideshowImages": True,
                               "shouldDownloadCovers": True})
    return {i.get("id"): i for i in items if i.get("id")}


def block_md(n, handle, p, slides, comments, drive_rel, rank_of):
    likes, com = p.get("diggCount") or 0, p.get("commentCount") or 0
    views, saves, shares = p.get("playCount") or 0, p.get("collectCount") or 0, p.get("shareCount") or 0
    eng = likes + com + saves + shares
    posted = (p.get("createTimeISO") or "")[:10]
    music = (p.get("musicMeta") or {})
    lines = [
        f"# {n} · {handle} — {p['id']}", "",
        f"**{likes:,} likes · {com:,} comments · {eng:,} engagement**  ",
        "_(heat signal: organic has no duplication — a creator posts once. Engagement is what the post earned.)_",
        f"**Rank:** {n} of {rank_of} of this creator's slideshows by views  ",
        f"**Views:** {views:,} · **saves:** {saves:,} · **shares:** {shares:,}  ",
        f"**Posted:** {posted}  ",
        f"**Post:** {p.get('webVideoUrl')}  ",
        f"**Type:** Slideshow — {len(slides)} stills, no motion  ",
        f"**Sound:** {music.get('musicName') or '?'} — {music.get('musicAuthor') or '?'}  ",
        f"**Format:** UNNAMED in `components/swipe-organic/formats.json`. the owner names it, not this pull.  ",
        f"**Drive:** `{drive_rel}` — mirrored {date.today()}, `photos/01.jpg … {len(slides):02d}.jpg` in posted order",
        "", "## Caption (verbatim, as posted)", "",
        "> " + (p.get("text") or "").replace("\n", "\n> "), "",
        "## Media", "",
        f"- `photos/` — {len(slides)} stills, exactly as posted (downloaded {date.today()})", "",
    ]
    if comments is None:
        lines += ["## Comments", "", "MISSING — the comments read failed; nothing guessed.", ""]
    else:
        cs = sorted(comments, key=lambda c: -(c.get("likes") or 0))[:60]
        lines += [f"## Comments ({len(cs)} pulled, most-liked first)", ""]
        for c in cs:
            lines += [f"- **@{c.get('owner')}** · {c.get('likes') or 0} likes  ",
                      f"  {(c.get('text') or '').strip()}"]
        lines.append("")
    return "\n".join(lines)


def pull(handle, top, depth, group):
    A.say(f"\n{handle}")
    posts, total = profile_slideshows(handle, depth)
    A.say(f"  {total} posts read · {len(posts)} slideshows · keeping top {min(top, len(posts))} by views")
    if not posts:
        return None
    picks = posts[:top]
    full = with_slides([p["webVideoUrl"] for p in picks])
    comments = A.comments_for([p["webVideoUrl"] for p in picks], "tiktok", per_post=100)

    out = HERE / handle
    (out / "posts").mkdir(parents=True, exist_ok=True)
    records = []
    for n, p in enumerate(picks, 1):
        f = full.get(p["id"], p)
        links = [s.get("downloadLink") or s.get("tiktokLink")
                 for s in (f.get("slideshowImageLinks") or []) if s]
        stem = f"{n:02d}_{handle}-{p['id']}"
        photos = DRIVE / handle / "posts" / stem / "photos"
        got = []
        for i, u in enumerate(links, 1):
            dest = photos / f"{i:02d}.jpg"
            if A.fetch(u, dest):
                got.append(dest.name)
        if links and not got:
            A.say(f"  ! {stem}: {len(links)} slides listed, none downloaded")
        drive_rel = swipe_home.label("organic", handle, "posts", stem) + "/"
        cm = None if comments is None else comments.get(p["webVideoUrl"], [])
        (out / "posts" / f"{stem}.md").write_text(
            block_md(n, handle, f, got, cm, drive_rel, len(picks)), encoding="utf-8")
        records.append({
            "file": f"{stem}.md", "id": p["id"],
            "views": p.get("playCount") or 0,
            "engagement": (p.get("diggCount") or 0) + (p.get("commentCount") or 0)
                          + (p.get("collectCount") or 0) + (p.get("shareCount") or 0),
            "slides": len(got), "url": p["webVideoUrl"],
            "posted": (p.get("createTimeISO") or "")[:10],
            "hashtags": " ".join("#" + h["name"] for h in (p.get("hashtags") or []) if h.get("name")),
            "sound": (f.get("musicMeta") or {}).get("musicName"),
        })
        A.say(f"  {stem}  {records[-1]['views']:,} views · {len(got)} slides")
    meta = (picks[0].get("authorMeta") or {})
    (out / "posts.json").write_text(json.dumps({
        "_what": f"{handle}'s slideshow posts — My Feeds library entry (organic). Built {date.today()} "
                 f"by slideshows.py from the Apify TikTok pull; every number is the post's own.",
        "creator": handle, "platform": "tiktok", "pulled": str(date.today()),
        "group": group, "followers": meta.get("fans"),
        "profile": f"https://www.tiktok.com/@{handle}",
        "slideshows_seen": len(posts), "posts_seen": total,
        "posts": records}, indent=1), encoding="utf-8")
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("handles", nargs="+", help="TikTok handles, without the @")
    ap.add_argument("--top", type=int, default=8, help="slideshows to keep per account, by views")
    ap.add_argument("--depth", type=int, default=40, help="posts to read off the profile before ranking")
    ap.add_argument("--group", default="", help="which set these accounts belong to")
    a = ap.parse_args()
    if not DRIVE.parent.parent.is_dir():
        sys.exit("Drive is not mounted — the slides have nowhere to go. Nothing pulled.")
    for h in a.handles:
        pull(h.lstrip("@"), a.top, a.depth, a.group)


if __name__ == "__main__":
    main()
