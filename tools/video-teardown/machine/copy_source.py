#!/usr/bin/env python3
"""What a copywriter needs about a post, in one file per selected video.

    python3 copy_source.py            every selected video
    python3 copy_source.py KZN-03     just one

The teardown answers "how was this made". This answers "how did she say it and
how did her audience answer" — the caption in her own voice, her hashtags, and
the comments the post actually drew. Ad copy has to sound like it came from the
same person who made the video, and this is where that voice lives.

Damon asked for this on 2026-08-27: when a creator delivers her video he needs
copy ready to run beside it, and that copy originates back at the post, not at
the finished cut. Nothing here touches the video pipeline.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library as L

SELECTED = "creators/SELECTED-2026-08-27.json"


def post_json(root, rel_video):
    f = root / Path(rel_video).parent / "post.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def one(vid, name, post, creator, handle):
    cap = (post.get("caption") or "").strip()
    tags = post.get("hashtags") or []
    mentions = post.get("mentions") or []
    comments = [c for c in (post.get("latestComments") or [])
                if (c.get("text") or "").strip()]
    views = post.get("videoPlayCount") or post.get("videoViewCount") or 0

    L_ = [f"# {vid} — copy source", "",
          f"**{creator}** (@{handle}) · [the original post]({post.get('url','')})  ",
          f"{views:,} views · {post.get('likesCount') or 0:,} likes · "
          f"{post.get('commentsCount') or 0:,} comments · "
          f"posted {(post.get('timestamp') or '')[:10]}", "",
          "> Written for the copy agent. Her caption is the voice to match; the",
          "> comments are her audience answering in their own words. Use both",
          "> before inventing a phrase neither of them used.", "",
          "## Her caption, verbatim", ""]
    L_ += ["> " + (cap.replace("\n", "\n> ") if cap else "_(no caption)_"), ""]
    if tags:
        L_ += ["## Hashtags she used", "", " ".join("#" + t for t in tags), ""]
    if mentions:
        L_ += ["## Accounts she tagged", "", " ".join("@" + m for m in mentions), ""]
    if comments:
        L_ += [f"## What her audience said ({len(comments)} captured)", ""]
        for c in comments:
            who = c.get("ownerUsername") or "someone"
            txt = " ".join((c.get("text") or "").split())
            likes = c.get("likesCount") or 0
            L_.append(f"- **@{who}**{f' ({likes} likes)' if likes else ''} — {txt}")
        L_.append("")
    else:
        L_ += ["## What her audience said", "", "_No comments captured on this post._", ""]
    return "\n".join(L_)


def build(only=None):
    root = L.root()
    sel = json.loads((root / SELECTED).read_text())
    made = 0
    for h, c in sel["creators"].items():
        for i in c["videos"]:
            if only and i["id"].upper() != only.upper():
                continue
            post = post_json(root, i["video"])
            if not post:
                print(f"  {i['id']}  no post.json — skipped")
                continue
            d = root / "creators" / h / "selected"
            d.mkdir(parents=True, exist_ok=True)
            nm = (i["name"] or "untitled").strip().replace("/", "-")[:48]
            (d / f"{i['id']}  {nm}.copy.md").write_text(
                one(i["id"], i["name"], post, c["creator"], h))
            made += 1
    return made


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    n = build(only)
    print(f"{n} copy source file(s) written beside the videos")
