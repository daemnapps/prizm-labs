#!/usr/bin/env python3
"""The post's own talk — its caption and its comments — for the culture read.

    python3 culture.py <run-folder>      pull (or re-read) and print it

the owner, 2026-10-05: two organic swipes went viral on pop culture the machine
never saw (a beloved film character dropped into a new situation), and the
teardown named them "AI player in a brown suit". The comments named them in
the first screen: viewers quote the character's lines back and say his name.
Comments are often where the culture is named, so stage 1k reads them.

FREE ONLY. The post is read with yt-dlp (`--skip-download --write-comments
--write-info-json`), never Apify. Where the post URL comes from, in order:
run.json `post_url` / `origin_url`, a post.json or meta.json beside the video
or in the run, then any *.info.json already in the run folder. No URL, no
info.json, or a platform that returns nothing: the text says so and the stage
carries on from the video and the record alone — never a stopped run.

What it keeps: `post/post.info.json` (yt-dlp's raw answer, working copy only)
and `post-talk.json` (caption, counts, comments — filed on the teardown shelf).
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

YTDLP_FALLBACK = "/opt/homebrew/bin/yt-dlp"
MAX_COMMENTS = 300            # the most a read is handed; most-liked first
TIMEOUT = 240
TALK_FILE = "post-talk.json"


def ytdlp():
    return shutil.which("yt-dlp") or (YTDLP_FALLBACK if Path(YTDLP_FALLBACK).exists() else None)


def _url_in(f):
    try:
        d = json.loads(Path(f).read_text())
    except Exception:
        return ""
    return str(d.get("url") or d.get("webpage_url") or d.get("post_url") or "").strip()


def post_url(d, st):
    """The post's own link, or ''. Never the Drive copy — that has no comments."""
    d = Path(d)
    for k in ("post_url", "origin_url", "source_post"):
        v = str((st or {}).get(k) or "").strip()
        if v.startswith("http"):
            return v
    homes = [d]
    if (st or {}).get("video"):
        homes.append(Path(st["video"]).parent)
    for h in homes:
        for name in ("post.json", "meta.json"):
            u = _url_in(h / name)
            if u.startswith("http"):
                return u
    # a swipe pulled with yt-dlp keeps <video>.info.json beside it, and the
    # run's own copy is source.mp4 — so look beside the original too
    for v in [(st or {}).get("video"), (st or {}).get("source_video")]:
        if v:
            u = _url_in(Path(v).with_suffix(".info.json"))
            if u.startswith("http"):
                return u
    return ""


def info_json_in(d):
    """An info.json already in the run folder (ours first, then any)."""
    d = Path(d)
    ours = d / "post" / "post.info.json"
    if ours.is_file():
        return ours
    found = sorted(p for p in d.glob("*.info.json") if p.is_file())
    return found[0] if found else None


def pull(d, url, runner=subprocess.run):
    """yt-dlp the post's metadata and comments into <run>/post/. -> (path|None, why)."""
    exe = ytdlp()
    if not exe:
        return None, "yt-dlp is not installed on this machine"
    out = Path(d) / "post"
    out.mkdir(parents=True, exist_ok=True)
    try:
        r = runner([exe, "--skip-download", "--write-comments", "--write-info-json",
                    "--no-warnings", "-o", str(out / "post.%(ext)s"), url],
                   capture_output=True, text=True, timeout=TIMEOUT)
    except Exception as e:
        return None, f"yt-dlp could not run ({type(e).__name__}: {str(e)[:120]})"
    f = out / "post.info.json"
    if f.is_file():
        return f, ""
    err = ((getattr(r, "stderr", "") or "") + (getattr(r, "stdout", "") or "")).strip()
    last = err.splitlines()[-1][:200] if err else "no output"
    return None, f"yt-dlp returned nothing for {url} ({last})"


def talk_from_info(info, url=""):
    """yt-dlp's info dict -> the slim record the read is handed."""
    comments = []
    for i, c in enumerate(info.get("comments") or []):
        text = str(c.get("text") or "").strip()
        if not text:
            continue
        comments.append(dict(n=i, author=c.get("author") or "",
                             text=text, likes=c.get("like_count"),
                             reply=bool(c.get("parent") and c.get("parent") != "root"),
                             timestamp=c.get("timestamp")))
    return dict(url=info.get("webpage_url") or url, platform=info.get("extractor_key") or "",
                channel=info.get("channel") or info.get("uploader_id") or "",
                uploader=info.get("uploader") or "", posted=info.get("upload_date") or "",
                caption=(info.get("description") or "").strip(),
                likes=info.get("like_count"), views=info.get("view_count"),
                comment_count=info.get("comment_count"), comments=comments)


def _likes(v):
    return f"{v:,}" if isinstance(v, int) and v > 0 else None


def render(talk):
    """The talk as the prompt reads it — numbered so a receipt can cite C<n>."""
    cs = list(talk.get("comments") or [])
    have_likes = any(isinstance(c.get("likes"), int) and c["likes"] > 0 for c in cs)
    if have_likes:
        cs.sort(key=lambda c: (-(c.get("likes") or 0), c["n"]))
    cs = cs[:MAX_COMMENTS]
    posted = talk.get("posted") or ""
    if re.fullmatch(r"\d{8}", posted):
        posted = f"{posted[:4]}-{posted[4:6]}-{posted[6:]}"
    head = [f"POST: {talk.get('url') or 'unknown'}",
            f"PLATFORM: {talk.get('platform') or 'unknown'} · ACCOUNT: @{talk.get('channel') or 'unknown'}"
            + (f" ({talk['uploader']})" if talk.get("uploader") else "")
            + (f" · POSTED: {posted}" if posted else ""),
            "LIKES: " + (_likes(talk.get("likes")) or "not given")
            + " · VIEWS: " + (_likes(talk.get("views")) or "not given")
            + " · COMMENTS ON THE POST: " + (_likes(talk.get("comment_count")) or "not given"),
            "", "CAPTION (verbatim):", talk.get("caption") or "(no caption)", ""]
    total = talk.get("comment_count")
    note = (f"COMMENTS PULLED: {len(cs)}"
            + (f" of {total:,} on the post — the platform returned only these, so "
               "treat them as a sample, not the whole room" if isinstance(total, int) and total > len(cs) else "")
            + ("; ordered most-liked first" if have_likes else
               "; the platform gave no like counts, so they are in the order returned"))
    lines = head + [note, ""]
    if not cs:
        lines.append("(no comments came back)")
    for i, c in enumerate(cs, 1):
        lk = _likes(c.get("likes"))
        lines.append(f"C{i} · @{c.get('author') or 'unknown'}"
                     + (" · reply" if c.get("reply") else "")
                     + f" · likes: {lk or 'n/a'} · {c['text']}")
    return "\n".join(lines).strip() + "\n"


def none_text(why):
    return (f"NO POST TALK: {why}. The caption and comments could not be read, so "
            "this read works from the video and the record alone — say so at the top "
            "of the read, and hold every name to the receipts those two can give.\n")


def post_talk(d, st, runner=subprocess.run, refresh=False):
    """-> the text {post_talk} is filled with. Never raises."""
    d = Path(d)
    try:
        info_f = None if refresh else info_json_in(d)
        url = post_url(d, st)
        why = ""
        if info_f is None:
            if not url:
                return none_text("this run has no post URL (run.json post_url, a post.json "
                                 "beside the video) and no info.json in the run folder")
            info_f, why = pull(d, url, runner=runner)
        if info_f is None:
            return none_text(why)
        info = json.loads(Path(info_f).read_text())
        talk = talk_from_info(info, url)
        (d / TALK_FILE).write_text(json.dumps(talk, indent=1, ensure_ascii=False) + "\n")
        return render(talk)
    except Exception as e:
        return none_text(f"the post could not be read ({type(e).__name__}: {str(e)[:120]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = Path(sys.argv[1])
    st = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    print(post_talk(run, st, refresh="--refresh" in sys.argv))
