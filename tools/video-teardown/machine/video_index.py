#!/usr/bin/env python3
"""The video index — one source video, one record, however many runs and briefs grew from it.

    python3 video_index.py              rebuild runs/video-teardown/VIDEO-INDEX.json + VIDEO-INDEX.md
    python3 video_index.py --find <video file or post url>   the record this video already has, if any
    import video_index as VI; VI.find(path_or_url)            what run.py asks before tearing a video down

the owner, 2026-10-13: "each individual video should just have one tear-down record. There's no reason to keep
re-entering the same video into the system over and over again. It's just one video, one tear-down record, one
index that can be used at any later point in time" — and: "using more references of what exists rather than just
assuming net new creation all the time". Creator-A's three-doctors post (KZN-03) had been entered five times under
five names (p191, p286, brief-0286, brief-0292, brief-0296), each a full teardown's worth of tokens.

A video's key, the first that exists:
  ig:<shortcode>     an Instagram post or reel (origin_url, or the library folder's name "03-<shortcode>")
  tt:<video id>      a TikTok video
  yt:<video id>      a YouTube video
  url:<link>         any other origin link, without its query string
  file:<size>-<sha1 of the first 2 MB>    the file itself, when nothing says where it came from
The record keeps every teardown run of that video (oldest finished one first: the record of reference), the
briefs grown from it (the briefs register, matched on the run's name), and where the video and its frames are.
Reads only; writes only the two index files.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C  # noqa: E402

WORK = C.runs_root()                      # runs/video-teardown/_work/
OUT = WORK.parent                         # runs/video-teardown/
WS = OUT.parents[1]
REGISTER = WS / "tools" / "image-teardown" / "briefs.json"


def key_of_url(u):
    u = (u or "").strip()
    if not u:
        return None
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", u)
    if m:
        return "ig:" + m.group(1)
    m = re.search(r"tiktok\.com/.*?/video/(\d+)", u) or re.search(r"tiktok\.com/.*?(\d{15,})", u)
    if m:
        return "tt:" + m.group(1)
    m = re.search(r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})", u)
    if m:
        return "yt:" + m.group(1)
    if "drive.google.com" in u:
        return None                       # a Drive copy says nothing about where the video came from
    return "url:" + u.split("?")[0].rstrip("/")


def key_of_folder(p):
    """A library post folder: .../posts/03-DbThHrJIapp/ → ig:DbThHrJIapp."""
    m = re.match(r"^\d+[-_]([A-Za-z0-9_-]{8,})$", Path(p).name) if p else None
    if m and not m.group(1).isdigit():
        return "ig:" + m.group(1)
    if m:
        return "tt:" + m.group(1)
    return None


def fingerprint(f):
    f = Path(f)
    if not f.is_file():
        return None
    h = hashlib.sha1()
    with f.open("rb") as fh:
        h.update(fh.read(2 * 1024 * 1024))
    return f"file:{f.stat().st_size}-{h.hexdigest()[:16]}"


def key_of_video(video=None, origin=None, library=None):
    v = Path(video) if video else None
    if v and not origin:
        for name in ("post.json", "meta.json"):
            p = v.parent / name
            if p.is_file():
                try:
                    origin = json.loads(p.read_text()).get("url") or origin
                except ValueError:
                    pass
    return (key_of_url(origin) or key_of_folder(library) or (key_of_folder(v.parent) if v else None)
            or (fingerprint(v) if v else None))


CACHE = OUT / "_video-keys.json"     # slug -> [run.json mtime, key]: a rebuild never re-reads a video it has keyed


def runs():
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    fresh = {}
    for f in sorted(WORK.glob("*/run.json")):
        try:
            st = C.read_record(f)            # stored repo-relative paths / labels read back (rule 4)
        except ValueError:
            continue
        mt = f.stat().st_mtime
        hit = cache.get(f.parent.name)
        if hit and hit[0] == mt:
            st["_key"] = hit[1]
        done = [k for k, v in (st.get("stages") or {}).items() if (v or {}).get("status") == "done"]
        vid = st.get("video") or ""
        k = st.get("_key") or key_of_url(st.get("origin_url")) or key_of_folder(st.get("library")) \
            or key_of_video(vid if vid and Path(vid).is_file() else None, st.get("origin_url"), st.get("library")) \
            or ("run:" + f.parent.name)
        fresh[f.parent.name] = [mt, k]
        yield k, {"slug": f.parent.name, "label": st.get("label"), "brand": st.get("brand"), "opened": st.get("opened"),
                  "finished": "stage7" in done, "stages_done": len(done), "creator": st.get("creator"),
                  "route": st.get("route") or st.get("production_route"), "origin_url": st.get("origin_url"),
                  "video": vid, "poster": str((f.parent / "poster.jpg").relative_to(WS)) if (f.parent / "poster.jpg").is_file() else None}
    try:
        CACHE.write_text(json.dumps(fresh))
    except OSError:
        pass


def build():
    idx = {}
    for k, r in runs():
        rec = idx.setdefault(k, {"key": k, "origin_url": None, "video": None, "poster": None, "runs": [], "briefs": []})
        rec["runs"].append(r)
        for f in ("origin_url", "video", "poster"):
            rec[f] = rec[f] or r.get(f)
    # a re-entry under a new name with no origin link (kzn03-face-scrub, kzn03-sections-proof) is the same video
    # as the record that has the link and the same post code (kzn-03-three-surgeons): fold it in
    real = {}
    for k, rec in idx.items():
        if not k.startswith(("run:", "file:")):
            for r in rec["runs"]:
                if code_of(r["slug"]):
                    real.setdefault(code_of(r["slug"]), k)
    for k in [k for k in idx if k.startswith(("run:", "file:"))]:
        codes = {code_of(r["slug"]) for r in idx[k]["runs"]}
        if len(codes) == 1 and None not in codes and real.get(next(iter(codes))):
            tgt = idx[real[next(iter(codes))]]
            tgt["runs"] += idx[k]["runs"]
            tgt.setdefault("merged", []).append(k)
            del idx[k]
    by_run, by_code = {}, {}
    for k, rec in idx.items():
        rec["runs"].sort(key=lambda r: (not r["finished"], r.get("opened") or "9999", r["slug"]))
        rec["record"] = rec["runs"][0]["slug"]           # the record of reference: the oldest finished run
        for r in rec["runs"]:
            by_run[r["slug"]] = k
            by_run[(r.get("label") or "").lower()] = k
            if code_of(r["slug"]):
                by_code.setdefault(code_of(r["slug"]), k)
    try:
        reg = json.loads(REGISTER.read_text())
        for shelf in ("briefs", "retired"):
            for bid, b in (reg.get(shelf) or {}).items():
                run = Path(str(b.get("run") or "")).name.lower()
                k = by_run.get(run) or by_code.get(code_of(b.get("run")) or "-")
                if k:
                    idx[k]["briefs"].append({"id": bid, "state": b.get("state"), "shelf": shelf, "type": b.get("type"),
                                             "title": b.get("title")})
    except (OSError, ValueError):
        pass
    return idx


def write():
    idx = build()
    (OUT / "VIDEO-INDEX.json").write_text(C._rk_paths.portable(        # stored paths portable (rule 4)
        json.dumps({"what": __doc__.split("\n")[0], "videos": idx}, indent=1)) + "\n")
    multi = sorted((r for r in idx.values() if len(r["runs"]) > 1), key=lambda r: -len(r["runs"]))
    L = ["# The video index", "", f"{len(idx)} source videos · {sum(len(r['runs']) for r in idx.values())} teardown runs · "
         f"{len(multi)} videos torn down more than once.", "",
         "One video, one record (the owner, 2026-10-13). The record of reference is the oldest finished run; a repeat "
         "teardown is refused by run.py unless `--again` is given.", "", "## Torn down more than once", "",
         "| Video | Runs | Record of reference | Briefs |", "|---|---|---|---|"]
    for r in multi:
        L.append(f"| {r['origin_url'] or r['key']} | {len(r['runs'])}: {', '.join(x['slug'] for x in r['runs'])} | {r['record']} | "
                 f"{', '.join(b['id'] for b in r['briefs']) or '—'} |")
    (OUT / "VIDEO-INDEX.md").write_text("\n".join(L) + "\n")
    return idx, multi


CODE = re.compile(r"^(?:runs/[^/]+/[^/]+/)?([a-z]{2,5})-?(\d{1,3})(?:\b|[-_])")


def code_of(s):
    """A creator post's short code: "kzn-03-three-surgeons", "kzn03-face-scrub", "runs/video-production/brand-b/kzn03" → kzn03."""
    m = CODE.match(str(s or "").lower())
    return f"{m.group(1)}{int(m.group(2)):02d}" if m else None


def source_of(brief, idx):
    """The source video a brief grew from: its run is a teardown run, or shares that run's post code."""
    run = Path(str(brief.get("run") or "")).name.lower()
    for k, rec in idx.items():
        if any(r["slug"] == run or (r.get("label") or "").lower() == run for r in rec["runs"]):
            return k
    c = code_of(brief.get("run"))
    if c:
        for k, rec in idx.items():
            if any(code_of(r["slug"]) == c for r in rec["runs"]):
                return k
    return None


def saved():
    """The index as last written (fast); build it when there is none."""
    try:
        return json.loads((OUT / "VIDEO-INDEX.json").read_text())["videos"]
    except (OSError, ValueError, KeyError):
        return build()


_CACHE = {}


def find(video_or_url, label=None):
    """The finished record this video already has, or None. Asked by run.py before a teardown starts."""
    s = str(video_or_url)
    k = key_of_url(s) if s.startswith("http") else key_of_video(s)
    if not k:
        return None
    if "idx" not in _CACHE:
        _CACHE["idx"] = saved()
    rec = _CACHE["idx"].get(k)
    if not rec or not any(r["finished"] for r in rec["runs"]):
        return None
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--find")
    a = ap.parse_args()
    if a.find:
        r = find(a.find)
        print(json.dumps(r, indent=1) if r else "not in the index: a new video")
        return
    idx, multi = write()
    print(f"{len(idx)} videos · {len(multi)} torn down more than once -> {OUT / 'VIDEO-INDEX.md'}")


if __name__ == "__main__":
    main()
