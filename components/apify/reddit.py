#!/usr/bin/env python3
"""Read Reddit for the forum-research agent.

    python3 tools/reddit.py --out <dir> --queries "brown spots on legs" "sun damage hands" [--limit 150]

Reddit answers 403 to plain fetching, which is why the research agent could not
read it on its own (found 2026-09-12, first forum run). Apify's Reddit actor is
the door that opens, and the token and its spent-account fallback already live
in the swipe-organic Apify layer — this reuses both rather than minting a second.

**This spends money.** Pay-per-result, about $0.004 an item, so the default cap
of 150 is roughly $0.60 a run. The cap is real and printed on every run.

Writes one `reddit.md` the agent reads, plus `reddit.json` for anything later.
Posts and their comments come back together, sorted by relevance, and every row
keeps its permalink, score and date so a claim can carry a receipt.
"""
import argparse, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify  # noqa: E402  the shared layer: token, spare-account fallback, 403 handling

ACTOR = "trudax~reddit-scraper-lite"


def score(row):
    """The actor spells this differently per row kind, and comments often carry
    none at all — so an absent score prints as a dash, never as a zero."""
    for k in ("upVotes", "score", "upvotes", "ups", "numberOfUpvotes"):
        v = row.get(k)
        if isinstance(v, (int, float)):
            return int(v)
    return None


def _s(row):
    v = score(row)
    return "—" if v is None else str(v)


def when(row):
    for k in ("createdAt", "created_at", "created"):
        v = row.get(k)
        if not v:
            continue
        try:
            if isinstance(v, (int, float)):
                return datetime.fromtimestamp(v, timezone.utc).strftime("%Y-%m-%d")
            return str(v)[:10]
        except Exception:
            pass
    return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="where reddit.md and reddit.json land")
    ap.add_argument("--queries", nargs="+", required=True, help="search the way she types, not the way a marketer does")
    ap.add_argument("--limit", type=int, default=150, help="hard cap on results; ~$0.004 each")
    ap.add_argument("--sort", default="relevance", choices=["relevance", "new", "top", "comments"])
    ap.add_argument("--time", default="year", choices=["hour", "day", "week", "month", "year", "all"])
    ap.add_argument("--subreddits", nargs="*", default=[],
                    help="target her actual rooms, e.g. 45PlusSkincare 30PlusSkinCare. "
                         "A plain search wanders; naming the room is what keeps it on target.")
    ap.add_argument("--no-comments", action="store_true")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    print(f"reddit: {len(a.queries)} queries, cap {a.limit} results (~${a.limit*0.004:.2f})", flush=True)

    # searchComments=True makes the actor return loose comments and NO posts
    # (measured 2026-09-12: 60-cap run came back 0 posts / 10 comments). What we
    # want is posts, each with its own comment thread — that is searchPosts with
    # skipComments off, which is a different switch.
    # Three settings that are not optional, each found the hard way (2026-09-12):
    #  · ignoreStartUrls — the actor ships a PREFILLED startUrl (a pasta recipe).
    #    Leave it and the search is ignored: a run for "brown spots on my legs"
    #    came back ten posts from a video-game subreddit.
    #  · includeMediaLinks — without it there are no upVotes and no comment
    #    counts at all, so every row prints a dash and nothing can be ranked.
    #  · searchComments stays FALSE. True returns loose comments and NO posts.
    #    Comments come from skipComments=False, which walks each post's thread.
    payload = {
        "searches": a.queries,
        "ignoreStartUrls": True,
        "searchPosts": True,
        "searchComments": False,
        "searchCommunities": False,
        "searchUsers": False,
        "searchMedia": False,
        "includeMediaLinks": True,
        "sort": a.sort,
        "time": a.time,
        "maxItems": a.limit,
        "maxPostCount": max(5, a.limit // max(1, len(a.queries))),
        "maxComments": 0 if a.no_comments else 25,
        "skipComments": a.no_comments,
        "skipUserPosts": True,
        "skipCommunity": True,
        "includeNSFW": False,
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
    }
    # A bare search wanders (measured: "brown spots on my legs" returned a
    # Filipino beauty board and an acne-scar routine). Naming her rooms and
    # searching inside them is what keeps a pull on target.
    if a.subreddits:
        payload["startUrls"] = [
            {"url": f"https://www.reddit.com/r/{sr.lstrip('r/')}/search/?q={quote_plus(q)}"
                    f"&restrict_sr=1&sort={a.sort}&t={a.time}"}
            for sr in a.subreddits for q in a.queries]
        payload["ignoreStartUrls"] = False
        print(f"  targeted at r/{', r/'.join(s.lstrip('r/') for s in a.subreddits)}", flush=True)

    t0 = time.time()
    try:
        rows = apify.run(ACTOR, payload, timeout=900)
    except SystemExit:
        raise
    except Exception as e:
        (out / "reddit.md").write_text(f"# Reddit\n\n[UNFILLED: the Reddit read failed — {e}]\n")
        sys.exit(f"reddit: FAILED — {e}")

    rows = [r for r in rows if isinstance(r, dict)]
    (out / "reddit.json").write_text(json.dumps(rows, indent=1)[:8_000_000])

    posts = [r for r in rows if (r.get("dataType") or r.get("type")) == "post" or r.get("title")]
    ids = {id(r) for r in posts}
    comments = [r for r in rows if id(r) not in ids]

    L = [f"# Reddit — what came back",
         "",
         f"Read {datetime.now().strftime('%Y-%m-%d %H:%M')} · actor `{ACTOR}` · "
         f"sort {a.sort}, window {a.time} · cap {a.limit}",
         f"Queries: " + " · ".join(f"`{q}`" for q in a.queries),
         "",
         f"**{len(posts)} posts and {len(comments)} comments in {time.time()-t0:.0f}s.** "
         "Every row below keeps its permalink, score and date — quote verbatim and cite the link.",
         ""]
    if not rows:
        L.append("[UNFILLED: the actor returned nothing. Try different phrasing, a wider window, or sort=top.]")

    subs = {}
    for p in posts:
        subs.setdefault(p.get("communityName") or p.get("subreddit") or "?", []).append(p)

    L += ["## The rooms these came from", ""]
    for s, ps in sorted(subs.items(), key=lambda kv: -len(kv[1])):
        L.append(f"- **{s}** — {len(ps)} posts in this pull")
    L += ["", "## Posts", ""]
    for p in sorted(posts, key=lambda r: -(score(r) or 0)):
        L += [f"### {p.get('title','(no title)')}",
              f"- {p.get('communityName') or p.get('subreddit') or '?'} · "
              f"score {_s(p)} · "
              f"{p.get('numberOfComments') or p.get('numComments') or 0} comments · {when(p)}",
              f"- {p.get('url') or p.get('link') or ''}"]
        body = (p.get("body") or p.get("selftext") or "").strip()
        if body:
            L.append(f"\n{body[:1500]}\n")
        L.append("")
    if comments:
        L += ["## Comments", ""]
        for c in sorted(comments, key=lambda r: -(score(r) or 0))[:400]:
            body = (c.get("body") or "").strip().replace("\n", " ")
            if not body:
                continue
            L.append(f"- **{_s(c)}** · {when(c)} · "
                     f"{c.get('communityName') or '?'} · {c.get('url') or ''}\n  > {body[:700]}")
    (out / "reddit.md").write_text("\n".join(L))
    print(f"reddit: {len(posts)} posts, {len(comments)} comments -> {out/'reddit.md'}")


if __name__ == "__main__":
    main()
