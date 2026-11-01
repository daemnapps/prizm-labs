"""Comments — the comment section of any public post, filed row by row.

    python3 components/research-gatherer/gather.py comments --brand B --url <post> [--url <post>]
    python3 components/research-gatherer/gather.py comments --brand B --avatar A --sub S --url <post>
    python3 components/research-gatherer/gather.py comments --brand B --url <post> --dry-run

TikTok, Instagram and Facebook posts, through `components/apify`. Every row
carries the permalink to the exact comment and the post it sits under, its
likes and replies, and is read by `annotate.py` (lane by language,
awareness, sophistication, use, sub-avatar). No handle is stored — the
handle is looked up from the permalink when a card needs it.

Where rows go: with `--sub`, into that sub-avatar's own language folder
(`sub-avatars/<card>/language/comments-<date>.json`) and nowhere else; with
no sub, into the avatar's lane files. A dry run pulls nothing and spends
nothing.
"""
import argparse
import datetime as dt
import json
import re

from . import engine
from . import annotate as A
from . import ownvoice as OV


def say(m):
    print(m, flush=True)


def tiktok_rows(items, today):
    out = []
    for c in items or []:
        if c.get("error") or not c.get("text"):
            continue
        video = c.get("videoWebUrl") or ""
        vid = (re.search(r"/video/(\d+)", video) or [None, ""])[1]
        cid = c.get("cid") or c.get("id")
        # TikTok has no public URL per comment; the video URL with the
        # comment's id is the closest address to it (the app opens there).
        acct = A.slug((re.search(r"tiktok\.com/@([^/]+)/", video) or [None, "unknown-account"])[1])
        out.append(dict(kind="comment", text=A.clean(c["text"]), said=(c.get("createTimeISO") or "")[:10],
                        pulled=today, ref=f"{video}?comment_id={cid}" if video else f"tiktok comment {cid}",
                        source_id=f"post_tiktok_{acct}_{vid}" if vid else None, source_kind="post", property=acct,
                        post=vid or video, source_name="TikTok comment", source_type="comment",
                        likes=c.get("diggCount"), replies=c.get("replyCommentTotal"),
                        relationship="commenter, relationship unknown"))
    return out


def pull(urls, per_post, today):
    ap = engine.apify_layer()
    acts = engine._config().get("actors", {}).get("comments", {})
    rows, notes = [], []
    by = {}
    for u in urls:
        by.setdefault(engine.platform_of(u) or ("facebook" if "facebook.com" in u else None), []).append(u)
    for plat, us in by.items():
        try:
            if plat == "tiktok":
                items = ap.run(acts.get("tiktok", "clockworks~tiktok-comments-scraper"),
                               {"postURLs": us, "commentsPerPost": per_post, "maxRepliesPerComment": 0})
                rows += tiktok_rows(items, today)
            elif plat == "instagram":
                items = ap.run(acts.get("instagram", "apify~instagram-comment-scraper"),
                               {"directUrls": us, "resultsLimit": per_post})
                rows += [{k: v for k, v in r.items() if k != "_id"} for r in OV.ig_rows(items, today, "Instagram comment")]
            elif plat == "facebook":
                items = ap.run(acts.get("facebook", "apify~facebook-comments-scraper"),
                               {"startUrls": [{"url": x} for x in us], "resultsLimit": per_post,
                                "includeNestedComments": True, "viewOption": "RANKED_UNFILTERED"})
                for r in OV.fb_rows(items, {}, today):   # page = the page id in the url
                    r.pop("_id", None)
                    r["source_name"] = "Facebook comment"
                    rows.append(r)
            else:
                notes.append(f"{len(us)} url(s) on a platform with no comment scraper: {', '.join(us)[:200]}")
        except Exception as e:
            notes.append(f"{plat}: MISSING ({str(e)[:100]})")
    return rows, notes


def file_to_sub(brand, avatar, sub, entries, today):
    """The sub-avatar's own folder and nowhere else (the deep pull's rule).
    Ids are the standard ones, numbered across the whole avatar bank."""
    home = engine.sub_home(brand, avatar, sub) / "language"
    home.mkdir(parents=True, exist_ok=True)
    dest = home / f"comments-{today}.json"
    try:
        d = json.loads(dest.read_text())
    except Exception:
        d = {"schema": 1, "avatar": avatar, "sub": sub, "entries": []}
    filed = []
    for e in A.assign_ids(A.lang_dir(brand, avatar), [(lane, dict(e, sub=sub)) for lane, e in entries]):
        d["entries"].append(e)
        filed.append({**e, "_file": str(dest.relative_to(engine.WORKSPACE))})
    dest.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return filed


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gather.py comments")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--sub")
    ap.add_argument("--url", action="append", required=True)
    ap.add_argument("--per-post", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = OV._cfg()
    per = a.per_post or cfg["comments_per_post"]
    label = OV.brand_json(a.brand).get("label") or a.brand
    avatar = a.avatar or OV.only_avatar(a.brand)[0]
    if not avatar:
        say(f"name the avatar with --avatar (found: {', '.join(OV.only_avatar(a.brand)[1]) or 'none'})")
        return 2
    now = dt.datetime.now(dt.timezone.utc)
    today, run_label = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d-%H%M")
    say(f"comments · {a.brand} · {avatar}{' · ' + a.sub if a.sub else ''} · {len(a.url)} post(s){' · DRY RUN' if a.dry_run else ''}")
    if a.dry_run:
        for u in a.url:
            say(f"  would pull up to {per} comments from {engine.platform_of(u) or 'unknown platform'}: {u}")
        say("  dry run — nothing pulled, nothing spent, nothing filed")
        return 0
    rows, notes = pull(a.url, per, today)
    ldir = A.lang_dir(a.brand, avatar)
    have = A.bank_refs(ldir)
    fresh = [r for r in rows if r["ref"] not in have and len(r["text"]) >= 1]
    say(f"  {len(rows)} pulled · {len(rows) - len(fresh)} already in the bank · {len(fresh)} new")
    keep, dropped, held = A.read_and_sort(fresh, a.brand, avatar, label, "comments on a public post", cfg, run_label)
    if a.sub:
        filed = file_to_sub(a.brand, avatar, a.sub, keep, today)
    else:
        by_lane = {}
        for lane, e in keep:
            by_lane.setdefault(lane, []).append(e)
        filed = A.file_lanes(ldir, by_lane)
    rep = A.report(filed, dropped, held)
    out = engine._deep_runs_root() / a.brand / f"comments-{run_label}"
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in (("filed.json", filed), ("dropped.json", dropped), ("held.json", held)):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    (out / "report.md").write_text(A.report_md(rep, f"{label} comments · {run_label}"))
    (out / "run.json").write_text(json.dumps({"brand": a.brand, "avatar": avatar, "sub": a.sub, "urls": a.url,
                                              "run": run_label, "report": rep, "notes": notes}, indent=1))
    (out / "page.html").write_text(OV.render_page(label, run_label, "the posts named", filed, dropped, rep,
                                                  A.PROMPT.read_text(), notes))
    say(f"  filed {len(filed)} · dropped {len(dropped)} · held {len(held)} · thin levels: {', '.join(rep['thin_levels']) or 'none'}")
    say(f"  page: {out / 'page.html'}")
    return 0
