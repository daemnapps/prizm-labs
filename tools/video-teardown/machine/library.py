#!/usr/bin/env python3
"""The library — where everything we swipe lives, and how it's laid out.

One convention, in one file. Nothing else decides where a file goes.

    swipe/
      creators/<handle>/
        creator.md                 who she is, her link, what we've pulled
        profile.json               the raw profile scrape
        posts/01-<shortcode>/      one folder per post, ranked
          post.md                  this post: metrics, link, what's been done to it
          video.mp4 / image.jpg    the asset itself
          thumbnail.jpg
          teardown/
            1-teardown/v6.md       one folder per stage, one file per version
            2-spec/v2.md
      brands/<brand>/              swipe files work identically
        brand.md
        angles/<angle>/<asset-id>/ …same shape as a post folder

Media lives on the Drive, never in a repo. Text records live beside the media
so a folder explains itself without anything else open.
"""

import json, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C

# The mount is resolved in ONE place — chain.py. This file used to carry a
# byte-identical copy of the hardcoded path, and the two of them are how a
# second person's library silently became a folder on one laptop.
# Creator work moved out of `swipe/` on 2026-08-27 (Damon) — it was buried
# under four unrelated swipe projects. It stays inside the lab: everything of
# his does, and a top-level folder was the wrong read. Creators now sit at
# creators/<handle>, with the picking selections beside them. The
# old swipe folder keeps its other projects and is no longer reached from here.
ROOT_SUBPATH = ("lab", "damon")


def root():
    """The library on the team Drive.

    No mount is a LOUD error (2026-08-27). There used to be a LOCAL_FALLBACK to
    `~/devel/daemn/…` "so work never blocks" — on every machine but one that is
    a personal sandbox nobody else can see, so the work did not block, it just
    never arrived. Blocking with a sentence is the better failure."""
    return C.drive_root().joinpath(*ROOT_SUBPATH)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def slug(s, n=48):
    return (re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower() or "x")[:n]


# ------------------------------------------------------------- creators

def creator_dir(handle, make=True):
    d = root() / "creators" / slug(handle)
    if make:
        (d / "posts").mkdir(parents=True, exist_ok=True)
    return d


def keep_case(s, n=32):
    """Shortcodes are case-sensitive — the folder name has to match the real URL."""
    import re as _re
    return (_re.sub(r"[^A-Za-z0-9_-]+", "-", str(s)).strip("-") or "x")[:n]


def post_dir(handle, rank, shortcode, make=True):
    d = creator_dir(handle, make=False) / "posts" / f"{rank:02d}-{keep_case(shortcode)}"
    if make:
        d.mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------- brands / swipe files

def brand_dir(brand, make=True):
    d = root() / "brands" / slug(brand)
    if make:
        d.mkdir(parents=True, exist_ok=True)
    return d


def angle_asset_dir(brand, angle, asset_id, make=True):
    d = brand_dir(brand, make=False) / "angles" / slug(angle) / slug(asset_id, 40)
    if make:
        d.mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------- teardowns

def teardown_dir(asset_dir, stage_id, stage_name, make=True):
    d = asset_dir / "teardown" / f"{stage_id}-{slug(stage_name)}"
    if make:
        d.mkdir(parents=True, exist_ok=True)
    return d


def save_teardown(asset_dir, stage_id, stage_name, version, text, prompt_name=""):
    """One file per version. A new version never overwrites an old one — the
    whole point is being able to compare what a prompt change did."""
    d = teardown_dir(asset_dir, stage_id, stage_name)
    f = d / f"v{version}.md"
    header = (f"<!-- stage {stage_id} {stage_name} · {prompt_name} · {now()} -->\n\n")
    f.write_text(header + text)
    _touch_index(asset_dir, stage_id, stage_name, version, f)
    return f


def _touch_index(asset_dir, stage_id, stage_name, version, path):
    """Every asset folder keeps a record of what's been done to it, so the
    folder is readable on its own without opening anything else."""
    idx = asset_dir / "post.md"
    if not idx.exists():
        idx = asset_dir / "asset.md"
    if not idx.exists():
        return
    line = f"- stage {stage_id} {stage_name} — **v{version}** · {now()} · `{path.name}`\n"
    body = idx.read_text()
    marker = "\n## Teardowns\n\n"
    if marker not in body:
        body += marker
    head, _, tail = body.partition(marker)
    tail = "".join(l for l in tail.splitlines(keepends=True)
                   if f"stage {stage_id} {stage_name} " not in l)
    idx.write_text(head + marker + tail + line)


# ------------------------------------------------------------- records

def write_creator_md(handle, profile, url, posts=None):
    d = creator_dir(handle)
    p = profile or {}
    lines = [
        f"# {p.get('fullName') or handle}", "",
        f"**Handle** @{handle}  ",
        f"**Page** {url}  ",
        (f"**Followers** {p['followersCount']:,}  " if isinstance(
            p.get('followersCount'), int) else "**Followers** not available  "),
        f"**Posts on the page** {p.get('postsCount','—')}  ",
        f"**We indexed** {p.get('indexed','—')} of them  ",
        f"**Pulled** {now()}", "",
    ]
    if p.get("biography"):
        lines += ["## Bio", "", "> " + p["biography"].replace("\n", "\n> "), ""]
    if posts:
        lines += ["## Top posts we pulled", "",
                  "| # | Post | Score | Views | Likes | Comments |",
                  "|---|---|---|---|---|---|"]
        for i, x in enumerate(posts, 1):
            lines.append(
                f"| {i} | [{x.get('shortCode','')}]({x.get('url','')}) "
                f"| {x.get('_score',0):,} | {x.get('videoPlayCount') or x.get('videoViewCount') or 0:,} "
                f"| {x.get('likesCount') or 0:,} | {x.get('commentsCount') or 0:,} |")
        lines.append("")
    lines += ["## Notes", "",
              "_Anything learned about her — what she posts, how she talks, "
              "whether she's a fit — goes here and stays here._", ""]
    (d / "creator.md").write_text("\n".join(lines))
    return d / "creator.md"


def write_post_md(asset_dir, post, handle, rank):
    v = post.get("videoPlayCount") or post.get("videoViewCount") or 0
    lines = [
        f"# {handle} — post {rank:02d}", "",
        f"**Link** {post.get('url','')}  ",
        f"**Type** {post.get('type','')}  ",
        f"**Posted** {(post.get('timestamp') or '')[:10]}  ",
        f"**Score** {post.get('_score',0):,}  (views {v:,} + likes "
        f"{post.get('likesCount') or 0:,} + comments {post.get('commentsCount') or 0:,})  ",
        f"**Pulled** {now()}", "",
    ]
    if post.get("caption"):
        lines += ["## Caption", "", "> " + post["caption"].replace("\n", "\n> "), ""]
    (asset_dir / "post.md").write_text("\n".join(lines))
    (asset_dir / "post.json").write_text(json.dumps(post, indent=2, default=str))
    return asset_dir / "post.md"


if __name__ == "__main__":
    try:
        print("library root:", root())
    except C.MountError as e:
        print("library root: UNAVAILABLE —", e)
