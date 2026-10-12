#!/usr/bin/env python3
"""Follow the commenters out — what else is this room into.

    python3 affinity.py --sub brand-b/avatar-one/sub-one \
        [--people 40] [--depth 20] [--floor 3] [--dry-run]

The harvest reads what a room watches. This reads **who showed up and what
else they are into** — and that second hop is the whole point. What these
people care about OUTSIDE the category is the only route from "he likes
basketball" to a name you can put in a subject line.

Method: take the commenters who actually engaged, read their own public posts,
and count what recurs — hashtags, sounds, the accounts they name. A signal is
not a signal until enough separate people carry it, so everything is reported
with the number of people behind it and anything under the floor is labelled
thin rather than dropped.

**Aggregate only.** The output is clusters and named entities. This never
writes a file about a person, and the per-person pull is a means to a count.

Public data only. Reads only.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import apify as A

HERE = Path(__file__).resolve().parent
# Platform filler carries no information about a person. The first real pass
# had five of these in its top seven rows.
STOP = {"fyp", "foryou", "foryoupage", "fy", "viral", "trending", "tiktok",
        "explore", "reels", "instagram", "capcut", "duet", "parati",
        "viralvideo", "trend", "creatorsearchinsights", "edit", "tuff",
        "love", "funny", "sad", "follow", "like", "video", "new"}


def is_filler(tag):
    """fyp has a hundred spellings — fypシ, fyppppp, xyzbca, xybca, and on."""
    t = (tag or "").lower()
    return (t in STOP or t.startswith(("fyp", "fyf", "xyz", "xyb", "foryou"))
            or len(t) < 3)


def commenters(root, n):
    """Who to follow out — selected for SPECIFICITY, not reach (the ruling:
    a viral post's comment section is the whole internet, not a room).

    Members first: anyone who commented on 2+ different seeded posts —
    one appearance is the internet passing through, two is a member.
    Then the list fills from the most-liked commenters on NICHE posts
    (smallest-view posts first), never from the mega-viral ones.

    Returns (people, member_count, total_comments). Everyone followed
    feeds the opportunity lane; only members carry room claims."""
    per_post = {}          # who -> set(post_dir)
    liked = {}             # who -> best like count seen
    post_views = {}
    total = 0
    try:
        hj = json.loads((root / "harvest.json").read_text())
        for p in hj.get("posts", []):
            post_views[str(p.get("id"))] = p.get("views") or 0
    except Exception:
        pass
    for f in (root / "posts").glob("*/comments.md"):
        pdir = f.parent.name
        for line in f.read_text().splitlines():
            m = re.match(r"- \*\*(\d+)\*\* · @([^\s]+) — (.*)", line)
            if not m:
                continue
            total += 1
            likes, who = int(m.group(1)), m.group(2)
            if not who or who == "?":
                continue
            per_post.setdefault(who, set()).add(pdir)
            liked[who] = max(liked.get(who, 0), likes)
    members = sorted((w for w, ps in per_post.items() if len(ps) >= 2),
                     key=lambda w: (-len(per_post[w]), -liked[w]))
    def niche_rank(w):
        views = min((post_views.get(d.split("-")[-1], 0) or 0)
                    for d in per_post[w])
        return (views, -liked[w])   # smallest room first, then loudest voice
    rest = sorted((w for w in per_post if w not in set(members)), key=niche_rank)
    out = (members + rest)[:n]
    return out, set(members), total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", required=True)
    ap.add_argument("--people", type=int, default=40)
    ap.add_argument("--depth", type=int, default=20, help="posts read per person")
    ap.add_argument("--floor", type=int, default=3, help="separate people needed to call it a signal")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = HERE / "records/culture-digs" / args.sub
    people, members, total = commenters(root, args.people)
    print(f"{total} comments on file · {len(members)} members (2+ posts) · "
          f"following {len(people)} people out")
    if args.dry_run:
        print("  " + ", ".join("@" + p for p in people))
        return
    if not people:
        raise SystemExit("no commenters on file — run harvest.py first")

    tags, sounds, mentions, authors = (defaultdict(set) for _ in range(4))
    reached = 0
    for i in range(0, len(people), 10):
        chunk = people[i:i + 10]
        try:
            items = A.run(A.POSTS_TT, {"profiles": chunk, "resultsPerPage": args.depth,
                                       "shouldDownloadVideos": False}, timeout=600)
        except Exception as e:
            print(f"  batch failed ({str(e)[:80]}) — continuing")
            continue
        for it in items:
            p = A.as_post(it, "tiktok")
            who = (it.get("authorMeta") or {}).get("name") or ""
            if not who:
                continue
            authors[who].add(p["id"])
            for h in p["hashtags"]:
                if h and not is_filler(h):
                    tags[h.lower()].add(who)
            if p.get("music"):
                sounds[p["music"]].add(who)
            for m in re.findall(r"@([A-Za-z0-9._]{3,})", p["caption"] or ""):
                mentions[m.lower()].add(who)
        reached = len(authors)
        print(f"  read {reached} people's posts so far")

    def rank(d, only=None):
        if only is not None:
            d = {k: (v & only) for k, v in d.items()}
        return sorted(((k, len(v)) for k, v in d.items() if v), key=lambda x: -x[1])

    L = [f"# What else this room is into — {args.sub}", "",
         f"Followed **{reached}** of the {len(people)} most-engaged commenters out of the",
         f"posts they commented on, and read up to {args.depth} of their own posts each.", "",
         "**Aggregate only.** Every line carries the number of separate people behind",
         f"it. A signal needs **{args.floor}+** people; anything under that is listed as thin",
         "rather than dropped, because a thin signal is still a lead.", "",
         f"**Room claims come from MEMBERS only** ({len(members)} people on 2+ seeded",
         "posts). Everyone else still counts — in opportunity.md, the wide catch.", ""]
    for title, d, note in (
            ("Interests they carry", tags, "hashtags on their OWN posts, platform filler removed"),
            ("Sounds", sounds, "what they set their posts to"),
            ("Accounts they name", mentions, "@mentions in their own captions")):
        rows = rank(d, only=members)
        strong = [(k, n) for k, n in rows if n >= args.floor]
        thin = [(k, n) for k, n in rows if n < args.floor][:15]
        L += [f"## {title}", "", f"*{note}*", ""]
        if strong:
            L += [f"| Signal | People |", "|---|---|"]
            L += [f"| {k} | **{n}** |" for k, n in strong[:30]]
        else:
            L += ["> Nothing cleared the floor on this pass.", ""]
        if thin:
            L += ["", f"Thin — one or two people each, kept as leads: "
                  + ", ".join(f"`{k}`" for k, _ in thin), ""]
    (root / "affinity.md").write_text("\n".join(L) + "\n")

    # THE OPPORTUNITY LANE (the owner's ruling, 2026-08-29): nothing the net
    # catches is thrown away. The full unfiltered distribution — including
    # everything that is NOT this avatar — is first-class output, because
    # deviation is where novel concepts come from (a viral Minecraft world
    # can carry an acne story; the shape and the world both transfer).
    # affinity.md carries claims about THE ROOM; this carries raw material.
    O = [f"# The opportunity catch — {args.sub}", "",
         "Everything the wide net returned, unfiltered and receipted.",
         "**These are NOT claims about the avatar** — they are worlds, sounds",
         "and names that real engaged people carry, kept as transfer material.",
         "A world with reach can host our story; taste (the owner) picks.", ""]
    for title, d in (("Worlds & interests", tags), ("Sounds", sounds),
                     ("Names carried", mentions)):
        rows = rank(d)
        if not rows:
            continue
        O += [f"## {title}", "", "| Signal | People |", "|---|---|"]
        O += [f"| {k} | **{n}** |" for k, n in rows[:60]]
        O += [""]
    O += ["## How to use this", "",
          "Pick a world with receipts, keep its native shape, swap the story",
          "to ours. The test of the method is that rows here were never in",
          "any seed list — those are the ones a brief could not have named.", ""]
    (root / "opportunity.md").write_text("\n".join(O) + "\n")
    print(f"-> {(root/'opportunity.md').relative_to(HERE)}")


if __name__ == "__main__":
    main()
