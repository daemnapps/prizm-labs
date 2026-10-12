"""Feed and dig comments — what the avatar's own rooms say under the posts
they watch, filed into the avatar's bank as prospect rows.

    python3 components/research-gatherer/gather.py feedcomments --feed <brand>--<x> [--top 15] [--max-comments 200] [--apply]
    python3 components/research-gatherer/gather.py feedcomments --all [--brand B] [--top 15] [--apply]
    python3 components/research-gatherer/gather.py digcomments  --dig <brand>/<avatar>/<sub> [--apply]
    python3 components/research-gatherer/gather.py digcomments  --all [--apply]
    (any of them: --dry-run pulls and counts, reads and files nothing)

the owner, 2026-10-06 (the bottom-up culture build): the culture map is built from
the real language only, so the comments under the posts each avatar's feed
already found, and the comments a culture dig already captured, go into the
bank as rows.

FREE ONLY — Apify is never called here. A feed post's comments come through
yt-dlp, by the video-teardown machine's own function
(`tools/video-teardown/machine/culture.py` › `pull`, imported, never
copied). This yt-dlp no longer reads TikTok comments at all (the extractor
returns the post with none), so a TikTok post that comes back empty is read
from TikTok's public web comment list instead — one plain GET per 50
comments, no key, no account. Instagram returns only the handful yt-dlp sees
on the page; a post nothing can read is named in the run and skipped.

Which posts (feedcomments): the feed's kept posts (`sift.keep`) in
`components/swipe-organic/records/avatar-feeds/<feed>/items.json`, ranked by
their latest views in `observations.jsonl`, growth between the last two
observations breaking ties, minus every post already pulled
(`runs/research/<brand>/feedcomments-state.json`) — top N of what is left.

Feed -> avatar: feed id `<brand>--<x>`; x is a core avatar id in
`brands/<brand>/core-avatars/avatars.json`, else the avatar whose
`sub_avatars` holds x (then the row's `sub` is x). Feeds whose id starts with
a skip prefix in research.json (`skip_feed_prefixes`) and feeds that map to
nothing are skipped. A dig's path is `<brand>/<avatar>/<sub>`.

Every row: source.type "comment", source.kind "feed-comment" | "dig-comment",
source.ref = the post URL, source.id = the comment id (a dig's comments.md
carries none, so a stable hash of the post, the commenter and the words),
source.property = the platform, source.item = the feed or dig id,
signal.likes, sub. Deduped on (source.ref, source.id) against the whole
avatar bank. Rows are read by the same two reads every gatherer row gets
(`annotate.read_and_sort`: the intake prompt, then the language layer's
labeller), then written as a PROPOSAL — `brands/` is written only by
`gather.py apply --proposal <run>/proposal.json` (or `--apply` here).
A row with no letters in it (an emoji, a sticker) is dropped before any
model reads it. Every run writes `runs/research/<brand>/<mode>-<run>/`.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import engine
from . import annotate as A

FEEDS = ("components", "swipe-organic", "records", "avatar-feeds")
DIGS = ("components", "swipe-organic", "records", "culture-digs")
PLAT_NAME = {"tiktok": "TikTok", "youtube": "YouTube", "instagram": "Instagram", "facebook": "Facebook"}
CHUNK = 120     # rows per worker — each worker runs the intake read + labeller on its chunk
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def say(m):
    print(m, flush=True)


def ws():
    return engine.WORKSPACE


def _cfg():
    c = dict(engine._config().get("ownvoice", {}))
    c.setdefault("model", "claude-sonnet-5")
    c.setdefault("batch", 30)
    return c


# ---------------------------------------------------------------- mapping

def avatars(brand, root=None):
    try:
        return json.loads(((Path(root) if root else ws()) / "brands" / brand / "core-avatars" / "avatars.json")
                          .read_text()).get("avatars") or []
    except Exception:
        return []


def map_feed(feed_id, root=None):
    """`<brand>--<x>` -> (brand, avatar, sub|None), or None when it maps to nothing."""
    skip = tuple(engine._config().get("skip_feed_prefixes") or [])
    if "--" not in (feed_id or "") or feed_id.startswith(skip):
        return None
    brand, x = feed_id.split("--", 1)
    avs = avatars(brand, root)
    for a in avs:
        if a.get("id") == x:
            return brand, x, None
    for a in avs:
        if x in (a.get("sub_avatars") or []):
            return brand, a["id"], x
    return None


def bank_file(brand, avatar, root=None):
    return (Path(root) if root else ws()) / "brands" / brand / "core-avatars" / avatar / "language" / "prospects.json"


# ---------------------------------------------------------------- dedupe

def bank_keys(brand, avatar, root=None):
    """{(source.ref, source.id)} across the whole avatar bank (sub folders included)."""
    base = (Path(root) if root else ws()) / "brands" / brand / "core-avatars" / avatar
    keys = set()
    for f in base.rglob("*.json") if base.is_dir() else []:
        if "/used/" in f.as_posix() or "/language/" not in f.as_posix():
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for e in d.get("entries", []) if isinstance(d, dict) else []:
            s = e.get("source") or {}
            if s.get("ref"):
                keys.add((s.get("ref"), s.get("id")))
    return keys


def dedupe(rows, have):
    """Rows whose (ref, source_id) is in `have` or seen earlier in `rows` are cut."""
    seen, out = set(have), []
    for r in rows:
        k = (r["ref"], r["source_id"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def has_words(t):
    return bool(re.search(r"[^\W\d_]", t or ""))


# ---------------------------------------------------------------- feed posts

def latest_views(obs_lines):
    """{item: (views at the last observation, growth since the one before)}."""
    hist = {}
    for line in obs_lines:
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("item"):
            hist.setdefault(o["item"], []).append((o.get("at") or "", o.get("views") or 0))
    out = {}
    for k, h in hist.items():
        h.sort()
        last = h[-1][1] or 0
        prev = h[-2][1] if len(h) > 1 else last
        out[k] = (last, (last or 0) - (prev or 0))
    return out


def rank_posts(items, obs, top, done=()):
    """The top `top` kept posts not yet pulled, loudest first."""
    done = set(done)
    ranked = []
    for key, it in items.items():
        if not (it.get("sift") or {}).get("keep") or not it.get("url") or it["url"] in done:
            continue
        v, g = obs.get(key, (0, 0))
        ranked.append((v, g, key, it))
    ranked.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return [dict(it, _views=v, _growth=g) for v, g, _, it in ranked[:top]]


def _culture():
    """The video-teardown machine's yt-dlp reader, imported in place."""
    p = ws() / "tools" / "video-teardown" / "machine"
    if str(p) not in sys.path:
        sys.path.append(str(p))
    import culture   # noqa: E402
    return culture


def _yt_runner(max_comments):
    def run(cmd, **kw):
        n = int(max_comments)
        extra = ["--extractor-args", f"youtube:max_comments={n},all,{n},0;comment_sort=top"]
        return subprocess.run(cmd[:1] + extra + cmd[1:], **kw)
    return run


def tiktok_web_comments(video_id, max_comments, opener=None):
    """TikTok's public web comment list — one GET per 50, no key. [] on any failure."""
    opener = opener or urllib.request.urlopen
    out, cursor = [], 0
    while len(out) < max_comments:
        q = urllib.parse.urlencode({"aid": 1988, "aweme_id": video_id, "count": 50, "cursor": cursor})
        req = urllib.request.Request(f"https://www.tiktok.com/api/comment/list/?{q}",
                                     headers={"User-Agent": UA, "Referer": "https://www.tiktok.com/"})
        try:
            d = json.loads(opener(req, timeout=30).read().decode("utf-8", "replace") or "{}")
        except Exception:
            break
        for c in d.get("comments") or []:
            out.append(dict(id=str(c.get("cid") or ""), text=c.get("text") or "", likes=c.get("digg_count"),
                            replies=c.get("reply_comment_total"), author=(c.get("user") or {}).get("unique_id") or "",
                            timestamp=c.get("create_time")))
        if not d.get("has_more") or not d.get("comments"):
            break
        cursor = d.get("cursor") or cursor + 50
    return out[:max_comments]


def pull_post(post, max_comments, cache_root):
    """-> (comments [{id, text, likes, replies, author, timestamp}], via, why)."""
    url, plat = post["url"], post.get("platform") or engine.platform_of(post["url"]) or ""
    home = Path(cache_root) / f"{plat}-{post.get('id') or hashlib.sha1(url.encode()).hexdigest()[:12]}"
    cul = _culture()
    info_f = home / "post" / "post.info.json"
    why = ""
    if not info_f.is_file():
        info_f, why = cul.pull(home, url, runner=_yt_runner(max_comments))
    comments = []
    if info_f:
        try:
            info = json.loads(Path(info_f).read_text())
            talk = cul.talk_from_info(info, url)
            raw = info.get("comments") or []
            for c in talk["comments"]:
                rc = raw[c["n"]] if c["n"] < len(raw) else {}
                comments.append(dict(id=str(rc.get("id") or ""), text=c["text"], likes=c.get("likes"),
                                     replies=None, author=c.get("author") or "", timestamp=c.get("timestamp")))
        except Exception as e:
            why = f"info.json unreadable ({str(e)[:80]})"
    if comments:
        comments.sort(key=lambda c: -(c.get("likes") or 0))
        return comments[:max_comments], "yt-dlp", ""
    if plat == "tiktok" and post.get("id"):
        got = tiktok_web_comments(post["id"], max_comments)
        if got:
            return got, "tiktok-web", ""
        return [], "", why or "yt-dlp returned no comments and TikTok's web list returned none"
    return [], "", why or f"yt-dlp returned no comments for this {plat or 'unknown'} post"


def feed_rows(post, comments, feed_id, sub, today):
    plat = post.get("platform") or engine.platform_of(post["url"]) or ""
    rows = []
    for c in comments:
        t = A.clean(c.get("text") or "")
        if not t or not c.get("id"):
            continue
        said = ""
        if isinstance(c.get("timestamp"), (int, float)):
            said = dt.datetime.fromtimestamp(c["timestamp"], dt.timezone.utc).strftime("%Y-%m-%d")
        rows.append(dict(kind="comment", text=t, said=said, pulled=today, ref=post["url"],
                         source_id=c["id"], source_kind="feed-comment", property=plat, post=post.get("id") or "",
                         source_name=f"{PLAT_NAME.get(plat, plat)} comment", source_type="comment",
                         likes=c.get("likes"), replies=c.get("replies"), item=feed_id, sub=sub,
                         relationship="commenter, relationship unknown"))
    return rows


# ---------------------------------------------------------------- dig posts

LINE = re.compile(r"^- \*\*(-?\d+)\*\* · @(\S*) — ?(.*)$")


def parse_comments_md(text):
    """comments.md -> [{likes, author, text}]; multi-line comments kept whole.
    A MISSING file or a header with no bullets -> []."""
    out, cur = [], None
    for line in (text or "").splitlines():
        m = LINE.match(line)
        if m:
            cur = {"likes": int(m.group(1)), "author": m.group(2), "text": m.group(3)}
            out.append(cur)
        elif cur is not None and line.strip():
            cur["text"] = (cur["text"] + "\n" + line).strip("\n")
    for c in out:
        c["text"] = c["text"].strip()
    return out


def parse_post_md(text):
    m = re.search(r"^- url:\s*(\S+)", text or "", re.M)
    return m.group(1) if m else ""


def dig_comment_id(url, author, text):
    return "dig-" + hashlib.sha1(f"{url}\n{author}\n{text}".encode("utf-8")).hexdigest()[:16]


def dig_rows(post_dir, dig_id, sub, today):
    try:
        url = parse_post_md((post_dir / "post.md").read_text())
        cs = parse_comments_md((post_dir / "comments.md").read_text())
    except Exception:
        return []
    if not url.startswith("http"):
        return []
    plat = engine.platform_of(url) or post_dir.name.split("-", 1)[0]
    vid = (re.search(r"/(?:video|reel|p|shorts)/([\w-]+)", url) or [None, ""])[1]
    rows = []
    for c in cs:
        t = A.clean(c["text"])
        if not t:
            continue
        rows.append(dict(kind="comment", text=t, said="", pulled=today, ref=url,
                         source_id=dig_comment_id(url, c["author"], c["text"]), source_kind="dig-comment",
                         property=plat, post=vid, source_name=f"{PLAT_NAME.get(plat, plat)} comment",
                         source_type="comment", likes=c["likes"], item=dig_id, sub=sub,
                         relationship="commenter, relationship unknown"))
    return rows


def all_digs(root=None):
    base = (Path(root) if root else ws()).joinpath(*DIGS)
    return sorted("/".join(p.parent.relative_to(base).parts) for p in base.glob("*/*/*/posts"))


# ---------------------------------------------------------------- read, then propose

def read_parallel(rows, brand, avatar, label, source, cfg, run_label, jobs=4):
    """annotate.read_and_sort in chunks, `jobs` at a time. -> (lane_entries, dropped, held),
    each entry paired back to its row."""
    chunks = [rows[i:i + CHUNK] for i in range(0, len(rows), CHUNK)]

    def one(ch):
        return ch, A.read_and_sort(ch, brand, avatar, label, source, cfg, run_label)

    keep, dropped, held = [], [], []
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for n, (ch, (le, dr, he)) in enumerate(ex.map(one, chunks), 1):
            keep += le
            dropped += dr
            held += he
            say(f"  chunk {n}/{len(chunks)} read · {len(keep)} kept so far")
    return keep, dropped, held


def to_entry(lane_entry, row):
    """The annotated entry, made a prospect row with this build's source fields."""
    _, e = lane_entry
    e = dict(e)
    e.pop("attribution", None)
    e["funnel"], e["speaker"] = "prospect", "commenter"
    src = dict(e.get("source") or {})
    src.update(type="comment", kind=row["source_kind"], ref=row["ref"], id=row["source_id"],
               property=row["property"], item=row["item"])
    e["source"] = src
    e["sub"] = row.get("sub")
    sig = dict(e.get("signal") or {})
    if row.get("likes") is not None:
        sig["likes"] = row["likes"]
    e["signal"] = sig or None
    return e


def proposal(brand, tool, adds):
    return {"kind": "language-bank-proposal", "version": 1, "brand": brand, "tool": tool,
            "made_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "add": adds}


def file_run(brand, mode, run_label, prop, rep, dropped, held, extra, title, notes):
    out = engine._deep_runs_root() / brand / f"{mode}-{run_label}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "proposal.json").write_text(json.dumps(prop, indent=1, ensure_ascii=False) + "\n")
    for name, obj in (("dropped.json", dropped), ("held.json", held)):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    (out / "run.json").write_text(json.dumps(dict(extra, run=run_label, report=rep, notes=notes),
                                             indent=1, ensure_ascii=False))
    (out / "report.md").write_text(A.report_md(rep, title) + ("\n## Notes\n\n" + "\n".join(f"- {n}" for n in notes) + "\n"
                                                             if notes else ""))
    try:
        from . import ownvoice as OV
        filed = [a["entry"] for a in prop["add"]]
        (out / "page.html").write_text(OV.render_page(brand, run_label, title, filed, dropped, rep,
                                                      A.PROMPT.read_text(), notes))
    except Exception:
        pass
    return out


def process(brand, avatar, rows, mode, run_label, title, source_desc, extra, notes, jobs, apply_now, dry_run):
    """Dedupe -> pre-filter -> two reads -> proposal (+ apply). Returns (folder|None, rep, held_refs)."""
    cfg = _cfg()
    have = bank_keys(brand, avatar)
    fresh = dedupe(rows, have)
    words = [r for r in fresh if has_words(r["text"])]
    pre = [{"why": "no-words: emoji or sticker only (dropped before the read)", "ref": r["ref"], "text": r["text"]}
           for r in fresh if not has_words(r["text"])]
    say(f"  {len(rows)} comments · {len(rows) - len(fresh)} already in the bank · {len(pre)} with no words · "
        f"{len(words)} to read")
    if dry_run or not words:
        return None, {"filed": 0, "to_read": len(words)}, set()
    label = brand_label(brand)
    keep, dropped, held = read_parallel(words, brand, avatar, label, source_desc, cfg, run_label, jobs)
    by_key = {(r["ref"], r["source_id"]): r for r in words}
    adds = []
    for le in keep:
        src = le[1].get("source") or {}
        row = by_key.get((src.get("ref"), src.get("id")))
        if row is None:
            continue
        adds.append({"file": str(bank_file(brand, avatar).relative_to(ws())), "entry": to_entry(le, row)})
    rep = A.report([a["entry"] for a in adds], pre + dropped, held)
    prop = proposal(brand, f"research-gatherer {mode}", adds)
    out = file_run(brand, mode, run_label, prop, rep, pre + dropped, held, extra, title, notes)
    say(f"  proposed {len(adds)} · dropped {len(pre) + len(dropped)} · held {len(held)}")
    say(f"  proposal: {(out / 'proposal.json').relative_to(ws())}")
    if apply_now and adds:
        from . import bank_apply as BA
        try:
            r = BA.apply(out / "proposal.json")
            say(f"  applied {r['applied']} · skipped {r['skipped']}")
        except BA.Refused as e:
            say(f"  REFUSED — nothing written: {e}")
    return out, rep, {h["ref"] for h in held}


def brand_label(brand):
    try:
        from . import ownvoice as OV
        return OV.brand_json(brand).get("label") or brand
    except Exception:
        return brand


# ---------------------------------------------------------------- the two modes

def run_feed(feed_id, top, max_comments, jobs, apply_now, dry_run, run_label, today):
    m = map_feed(feed_id)
    if not m:
        say(f"feedcomments · {feed_id} · skipped (maps to no avatar)")
        return None
    brand, avatar, sub = m
    if not bank_file(brand, avatar).is_file():
        say(f"feedcomments · {feed_id} · skipped (no prospects bank for {brand}/{avatar})")
        return None
    fd = ws().joinpath(*FEEDS) / feed_id
    try:
        items = json.loads((fd / "items.json").read_text()).get("items") or {}
        obs = latest_views((fd / "observations.jsonl").read_text().splitlines())
    except Exception as e:
        say(f"feedcomments · {feed_id} · skipped (feed unreadable: {str(e)[:80]})")
        return None
    state_f = engine._deep_runs_root() / brand / "feedcomments-state.json"
    try:
        state = json.loads(state_f.read_text())
    except Exception:
        state = {"posts": {}}
    posts = rank_posts(items, obs, top, done=state["posts"].keys())
    say(f"feedcomments · {feed_id} -> {brand}/{avatar}{'/' + sub if sub else ''} · {len(posts)} post(s)"
        f"{' · DRY RUN' if dry_run else ''}")
    rows, notes, pulled = [], [], {}
    cache = engine.WORKSPACE / "runs" / "research-cache" / "_system" / "feedcomments"
    for p in posts:
        if dry_run:
            say(f"  would pull up to {max_comments} comments · {p['_views']:,} views · {p['url']}")
            continue
        cs, via, why = pull_post(p, max_comments, cache)
        say(f"  {len(cs):>4} comments via {via or '—'} · {p['_views']:,} views · {p['url']}")
        if not cs:
            notes.append(f"{p.get('platform')}: {p['url']} — {why}")
        pulled[p["url"]] = dict(at=today, comments=len(cs), via=via, why=why or None)
        rows += feed_rows(p, cs, feed_id, sub, today)
    if dry_run:
        return None
    out, rep, held_refs = process(brand, avatar, rows, "feedcomments", f"{run_label}-{feed_id}",
                                  f"{feed_id} feed comments · {run_label}", "comments under posts in the avatar's own feed",
                                  dict(brand=brand, avatar=avatar, sub=sub, feed=feed_id, posts=list(pulled)),
                                  notes, jobs, apply_now, False)
    for u, rec in pulled.items():
        if u not in held_refs:
            state["posts"][u] = dict(rec, feed=feed_id)
    state_f.parent.mkdir(parents=True, exist_ok=True)
    state_f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    return out


def run_dig(dig, jobs, apply_now, dry_run, run_label, today):
    parts = dig.strip("/").split("/")
    if len(parts) != 3:
        say(f"digcomments · {dig} · skipped (a dig is <brand>/<avatar>/<sub>)")
        return None
    brand, avatar, sub = parts
    if not bank_file(brand, avatar).is_file():
        say(f"digcomments · {dig} · skipped (no prospects bank for {brand}/{avatar})")
        return None
    base = ws().joinpath(*DIGS) / dig / "posts"
    dig_id = f"{brand}--{sub}"
    rows = []
    for pd in sorted(base.iterdir()) if base.is_dir() else []:
        if pd.is_dir():
            rows += dig_rows(pd, dig_id, sub, today)
    say(f"digcomments · {dig} · {len(rows)} comments with text{' · DRY RUN' if dry_run else ''}")
    out, rep, _ = process(brand, avatar, rows, "digcomments", f"{run_label}-{sub}",
                          f"{dig} dig comments · {run_label}", "comments under the posts a culture dig captured",
                          dict(brand=brand, avatar=avatar, sub=sub, dig=dig), [], jobs, apply_now, dry_run)
    return out


def feeds_for(brand=None, root=None):
    base = (Path(root) if root else ws()).joinpath(*FEEDS)
    out = []
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        if d.is_dir() and (d / "items.json").is_file() and map_feed(d.name, root):
            if brand is None or d.name.startswith(f"{brand}--"):
                out.append(d.name)
    return out


def main(argv=None, mode="feedcomments"):
    ap = argparse.ArgumentParser(prog=f"gather.py {mode}")
    if mode == "feedcomments":
        ap.add_argument("--feed")
        ap.add_argument("--top", type=int, default=15)
        ap.add_argument("--max-comments", type=int, default=200)
    else:
        ap.add_argument("--dig")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--brand", help="with --all: only this brand's feeds or digs")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--apply", action="store_true", help="hand the proposal to `gather.py apply` straight away")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    today, run_label = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d-%H%M")
    if mode == "feedcomments":
        targets = feeds_for(a.brand) if a.all else [a.feed] if a.feed else []
        if not targets:
            say("name a feed with --feed <brand>--<x>, or --all")
            return 2
        for f in targets:
            run_feed(f, a.top, a.max_comments, a.jobs, a.apply, a.dry_run, run_label, today)
    else:
        targets = [d for d in all_digs() if not a.brand or d.startswith(a.brand + "/")] if a.all else \
            [a.dig] if a.dig else []
        if not targets:
            say("name a dig with --dig <brand>/<avatar>/<sub>, or --all")
            return 2
        for d in targets:
            run_dig(d, a.jobs, a.apply, a.dry_run, run_label, today)
    return 0
