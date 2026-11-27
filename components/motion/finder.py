#!/usr/bin/env python3
"""The action finder: real footage of the same action, found in the house order (stage 2 of the chain).

    python3 finder.py find <scene dir> --action "she kisses his cheek, he ducks toward her" [--action ...]
                           --brand <brand> [--framemap <framemap.json>] [--source <the swipe's video>] [--web 6]
    python3 finder.py show <scene dir>                       the candidates, in order
    python3 finder.py yes <scene dir> <n> --by <name>        the owner's yes on candidate n (a web one is downloaded now)

Order (owner's ruling, 2026-11-12: what we already have first, because it costs nothing to reach):
  1. own     footage we own, searched by what it shows (components/asset-index `search`), rights checked there
  2. swipe   the swipe's own seconds: the frame-map shots whose moments describe the action
  3. web     a search list from YouTube (titles, lengths, links: a listing, nothing downloaded) and a TikTok search
             link, for when 1 and 2 do not show the action or show too little of it

Writes <scene dir>/motion/candidates.json: every candidate with where it is, its seconds, why it matched and a score,
and `pick` (the best one that needs no download) and, when the caller named the reference outright, `used`. A web candidate is never downloaded until `yes` names who said so;
`yes` on an own or swipe candidate only records the pick. No brand, product or person is named here; the brand comes
from the caller.
"""
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import home as ST  # noqa: E402

STOP = set("a an the and or of to in on at by for with from into up down out off is are his her their him she he they them "
           "it its then while as that this who whom one both each toward towards little bit slightly small".split())
SHORT = 1.2            # a reference shorter than this shows a pose, not a move: the finder keeps looking
WEB_MAX = 90           # seconds: the longest web clip worth listing as a reference
OWN_COVER = 0.4        # own footage counts as the action when its record holds at least this share of the action's words


def words(text):
    out = []
    for w in re.findall(r"[a-z']+", str(text).lower()):
        if w in STOP or len(w) < 3:
            continue
        for suf in ("ing", "es", "ed", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def own(action, brand, per=4):
    """Footage we own that shows the action (asset-index's own search, its declared library surface)."""
    part = ST.part("asset-index", ST.DATA_REPO)
    if not brand or not (part / "machine" / "search.py").is_file():
        return [], "no asset index in this workspace" if brand else "no brand given"
    code = ("import json,sys;sys.path.insert(0,sys.argv[1]);import search as S;"
            "print(json.dumps([{k:h.get(k) for k in ('score','clip_id','in','out','shows','shared_path','kind','rights')} "
            "for h in S.search(sys.argv[2],'',sys.argv[3],per=int(sys.argv[4]))],default=str))")
    r = subprocess.run([sys.executable, "-c", code, str(part / "machine"), action, brand, str(per)], capture_output=True, text=True)
    if r.returncode:
        return [], "the asset index could not be searched: " + (r.stderr or "")[-200:]
    hits = json.loads(r.stdout.strip().splitlines()[-1] or "[]")
    q = set(words(action))
    out = []
    for h in hits:
        if h.get("in") is None:
            continue
        cover = len(q & set(words(h.get("shows", "")))) / max(1, len(q))
        if cover < OWN_COVER:                         # shares a word or two with the action: not footage of it
            continue
        out.append({"from_where": "own", "clip_id": h["clip_id"], "label": h.get("shared_path"), "from": h["in"], "to": h["out"],
                    "seconds": round(float(h["out"]) - float(h["in"]), 2), "shows": h.get("shows"), "score": round(float(h["score"]), 2),
                    "covers": round(cover, 2), "rights": h.get("rights"), "needs_download": False})
    return out, None


def swipe(action, framemap, source=None):
    """The swipe's own shots whose moments describe the action."""
    fm = json.loads(Path(framemap).read_text())
    q = set(words(action))
    out = []
    for s in fm.get("shots") or []:
        m = s.get("map") or {}
        does = "; ".join(str(x.get("does", "")) for x in m.get("moments") or [])
        text = " ".join([does, str(m.get("start_frame", "")), str(m.get("end_frame", ""))])
        have = set(words(text))
        cover = len(q & have) / max(1, len(q))
        if cover < 0.3:
            continue
        secs = round(float(s["end"]) - float(s["start"]), 2)
        out.append({"from_where": "swipe", "shot": s.get("id"), "label": "the swipe, shot %s" % s.get("id"),
                    "source": str(source or Path(framemap).parent.parent / "source.mp4"), "from": s["start"], "to": s["end"],
                    "seconds": secs, "shows": does[:240], "score": round(cover, 2), "covers": round(cover, 2),
                    "short": secs < SHORT, "needs_download": False})
    return sorted(out, key=lambda c: (-c["score"], c["from"]))


def web(action, n=6):
    """A search list, nothing downloaded: YouTube results (yt-dlp's listing) and a TikTok search link."""
    phrase = " ".join(action.split()[:12])
    out, note = [], None
    try:
        # short clips only: a reference is seconds of one action, never a long video to dig through
        r = subprocess.run(["yt-dlp", "ytsearch%d:%s shorts" % (n * 4, phrase), "--flat-playlist", "--dump-json", "--no-warnings"],
                           capture_output=True, text=True, timeout=120)
        for line in r.stdout.splitlines():
            try:
                v = json.loads(line)
            except ValueError:
                continue
            if not v.get("duration") or float(v["duration"]) > WEB_MAX or len(out) >= n:
                continue
            out.append({"from_where": "web", "site": "youtube", "label": v.get("title"), "url": v.get("url") or v.get("webpage_url"),
                        "seconds": v.get("duration"), "views": v.get("view_count"), "channel": v.get("channel") or v.get("uploader"),
                        "needs_download": True})
        if r.returncode and not out:
            note = "YouTube could not be listed: " + (r.stderr or "")[-160:]
    except (OSError, subprocess.SubprocessError) as e:
        note = "YouTube could not be listed: %s" % str(e)[:120]
    out.append({"from_where": "web", "site": "tiktok", "label": "TikTok search: " + phrase,
                "url": "https://www.tiktok.com/search/video?q=" + urllib.parse.quote(phrase), "needs_download": True, "search_link": True})
    return out, note


def find(scene_dir, actions, brand=None, framemap=None, source=None, n_web=6, also_web=None, used=None):
    """Every candidate for the scene's actions, in the house order, written to <scene>/motion/candidates.json."""
    d = Path(scene_dir) / "motion"
    d.mkdir(parents=True, exist_ok=True)
    rows, notes = [], []
    for action in actions:
        got, note = own(action, brand)
        if note:
            notes.append(note)
        for c in got:
            rows.append(dict(c, action=action))
        if framemap and Path(framemap).exists():
            for c in swipe(action, framemap, source):
                rows.append(dict(c, action=action))
    # the same clip found for two actions is one candidate
    seen, uniq = {}, []
    for c in rows:
        k = (c["from_where"], c.get("label") or c.get("shot"), c.get("from"))      # one file may sit in the index under two ids
        if k in seen:
            seen[k]["action"] = seen[k]["action"] + " / " + c["action"] if c["action"] not in seen[k]["action"] else seen[k]["action"]
            seen[k]["score"] = max(seen[k]["score"], c["score"])
            continue
        seen[k] = c
        uniq.append(c)
    strong = [c for c in uniq if c["covers"] >= 0.5 and not c.get("short")]
    need_web = not strong
    webs = []
    for action in (also_web or []) + (actions if need_web else []):
        got, note = web(action, n_web)
        if note:
            notes.append(note)
        webs += [dict(c, action=action) for c in got]
    order = {"own": 0, "swipe": 1, "web": 2}
    cands = sorted(uniq, key=lambda c: (order[c["from_where"]], -c["score"])) + webs
    for i, c in enumerate(cands, 1):
        c["n"] = i
        # the reference the caller named outright (a span of the swipe): marked, so a board shows what was used
        c["used"] = bool(used and c["from_where"] == "swipe" and any(float(a) - 0.05 <= float(c["from"]) and float(c["to"]) <= float(b) + 0.05 for a, b in used))
    usable = [c for c in cands if not c["needs_download"] and c["covers"] >= 0.3]
    strong.sort(key=lambda c: (-c["covers"], order[c["from_where"]]))
    pick = (strong[0] if strong else (max(usable, key=lambda c: (c["covers"], not c.get("short"))) if usable else None))
    rec = {"actions": actions, "brand": brand, "order": ["own", "swipe", "web"], "candidates": cands,
           "pick": pick["n"] if pick else None,
           "why_web": ("nothing we have shows the whole move (a match under half the action's words, or shorter than %.1f s)" % SHORT) if need_web
           else ("the motion read asked for more footage" if also_web else None),
           "used": used, "waiting_for_yes": [c["n"] for c in cands if c["needs_download"]], "notes": notes,
           "found_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    old = d / "candidates.json"
    if old.exists():                                  # a yes already given is kept
        try:
            rec["approved"] = json.loads(old.read_text()).get("approved") or []
        except ValueError:
            pass
    old.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def yes(scene_dir, n, by):
    """The owner's yes on one candidate. A web candidate is downloaded now, into <scene>/motion/found/; nothing is
    downloaded without `by`."""
    if not by:
        raise SystemExit("a download needs the name of who said yes (--by)")
    f = Path(scene_dir) / "motion" / "candidates.json"
    rec = json.loads(f.read_text())
    c = next((x for x in rec["candidates"] if x["n"] == int(n)), None)
    if c is None:
        raise SystemExit("no candidate %s" % n)
    row = {"n": c["n"], "by": by, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if c["needs_download"]:
        if c.get("search_link"):
            raise SystemExit("candidate %s is a search link, not a video: pick a video from it and give its link" % n)
        out = Path(scene_dir) / "motion" / "found"
        out.mkdir(parents=True, exist_ok=True)
        dest = out / ("ref-%d.mp4" % c["n"])
        r = subprocess.run(["yt-dlp", "-f", "mp4[height<=720]/best[height<=720]/best", "-o", str(dest), "--no-warnings", c["url"]],
                           capture_output=True, text=True)
        if r.returncode or not dest.exists():
            raise SystemExit("could not download it: " + (r.stderr or r.stdout)[-300:])
        row["file"] = str(dest)
        c["file"] = str(dest)
    rec.setdefault("approved", []).append(row)
    rec["pick"] = c["n"]
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return row


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)

    def opts(k):
        return [a[i + 1] for i, x in enumerate(a) if x == k and i + 1 < len(a)]

    def opt(k, d=None):
        return (opts(k) or [d])[0]
    if a[0] == "find":
        rec = find(a[1], opts("--action"), opt("--brand"), opt("--framemap"), opt("--source"), int(opt("--web", 6)))
    elif a[0] == "yes":
        print(json.dumps(yes(a[1], a[2], opt("--by")), indent=1))
        sys.exit(0)
    else:
        rec = json.loads((Path(a[1]) / "motion" / "candidates.json").read_text())
    for c in rec["candidates"]:
        print("%2d %s %-6s %5s s  %s  %s" % (c["n"], "*" if c["n"] == rec.get("pick") else " ", c["from_where"],
                                            c.get("seconds") if c.get("seconds") is not None else "?", c.get("score", ""), (c.get("label") or "")[:80]))
    if rec.get("why_web"):
        print("web list because: " + rec["why_web"])
