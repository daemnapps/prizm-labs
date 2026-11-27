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
import argparse, json, re, sys, time
from datetime import datetime, timezone
import os
from pathlib import Path


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    The count here was right only while this file sat in lab/owner/. The move
    to components/ on 2026-09-22 made it resolve to ~/Projects, one level too
    high — outside the repo entirely. A marker cannot go quietly wrong the next
    time something moves. AI_WORKSPACE still wins when it names a workspace.
    """
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError(f"no workspace found upward of {here}")


from urllib.parse import quote_plus

HERE = Path(__file__).resolve().parent
REPO = _workspace()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify  # noqa: E402  the shared layer: token, spare-account fallback, 403 handling

ACTOR = "harshmaur~reddit-scraper"      # 2026-11-25: trudax~reddit-scraper-lite refuses every search without a session token
# reddit.json's ceiling. Rows are dropped from the END (least relevant) until
# the dump fits, so the file is always valid JSON — cutting the serialized
# text instead left a file no reader could parse.
JSON_CAP = 8_000_000


def _sub(x):
    """'r/name' → 'name'. Not lstrip('r/'), which strips a CHARACTER SET and
    turned 'running' into 'unning'."""
    return x[2:] if x.startswith("r/") else x


def _run(payload, dollars):
    """One capped run: the platform stops it at `dollars`."""
    import urllib.request

    def call(tok):
        url = f"{apify.API}/acts/{ACTOR}/run-sync-get-dataset-items?token={tok}&timeout=600&maxTotalChargeUsd={dollars}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=660) as r:
            return json.loads(r.read() or b"[]")
    return apify.each_account(call)


def as_row(r):
    """The shape every reader of this door already knows, whatever the actor calls things: a comment keeps its own link,
    its room, its score and its date."""
    r = dict(r)
    if r.get("dataType") == "comment":
        r.update({"communityName": "r/%s" % (r.get("subredditName") or r.get("parsedCommunityName") or "?"), "upVotes": r.get("commentUpVotes", r.get("score")), "createdAt": r.get("commentCreatedAt") or r.get("createdAt")})
        if r.get("id") and str(r.get("url") or "").endswith("/%s/" % r.get("parsedPostId")):
            r["url"] = r["url"] + "comment/%s/" % str(r["id"]).replace("t1_", "")
        r.pop("title", None)
    else:
        r["url"] = r.get("postUrl") or r.get("url") or r.get("contentUrl")
    r["parsedCommunityName"] = re.sub(r"^r/", "", str(r.get("communityName") or r.get("parsedCommunityName") or ""))
    return r


def _fit(rows, cap):
    """The longest prefix of rows whose dump fits under cap, and how many were dropped."""
    text = json.dumps(rows, indent=1)
    if len(text) <= cap:
        return text, 0
    lo, hi = 0, len(rows)          # lo always fits (an empty list does)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if len(json.dumps(rows[:mid], indent=1)) <= cap:
            lo = mid
        else:
            hi = mid
    return json.dumps(rows[:lo], indent=1), len(rows) - lo


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
    rooms = [_sub(r) for r in a.subreddits] or [""]
    sort = {"relevance": "relevance", "new": "new", "top": "top", "comments": "comments"}[a.sort]
    if a.subreddits:
        print(f"  targeted at r/{', r/'.join(x for x in rooms)}", flush=True)
    per = max(1, a.limit // (len(rooms) * len(a.queries)))         # items one search in one room may bring
    posts_each = per if a.no_comments else max(1, per // 4)
    payloads = [{"searchTerms": a.queries, **({"withinCommunity": r} if r else {}), "searchPosts": True, "searchComments": not a.no_comments, "searchCommunities": False,
                 "searchSort": sort, "searchTime": a.time, "crawlCommentsPerPost": not a.no_comments, "maxPostsCount": posts_each,
                 "maxCommentsCount": 0 if a.no_comments else max(1, per // 2), "maxCommentsPerPost": 0 if a.no_comments else 5, "includeNSFW": False} for r in rooms]

    t0 = time.time()
    # Every failure — a missing token (apify.token() raises SystemExit) included —
    # leaves the same two files: a reddit.md carrying the reason and an empty
    # reddit.json, so an older pull's json is never read as this one's. Exit 1.
    try:
        rows = []
        for p_ in payloads:
            if len(rows) >= a.limit:
                break
            rows += [as_row(r) for r in _run(p_, max(.25, round(a.limit * .004 / len(payloads), 2))) if isinstance(r, dict)]
        rows = rows[:a.limit]
    except (SystemExit, Exception) as e:
        (out / "reddit.md").write_text(f"# Reddit\n\n[UNFILLED: the Reddit read failed — {e}]\n")
        (out / "reddit.json").write_text("[]")
        print(f"reddit: FAILED — {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    rows = [r for r in rows if isinstance(r, dict)]
    text, truncated = _fit(rows, JSON_CAP)
    (out / "reddit.json").write_text(text)

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
    if truncated:
        L[5:5] = [f"truncated: {truncated} — rows dropped from the end of reddit.json to keep it "
                  f"under {JSON_CAP:,} chars; this page reads all {len(rows)}.", ""]
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
