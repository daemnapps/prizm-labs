#!/usr/bin/env python3
"""USED EVERYTHING — the edit proves it put together exactly what production made (owner, 2026-11-21: "video editing
is simply piece the above together … the edit should just make what we made come to life in the detail").

    python3 used_everything.py <production>          the findings, one line each; exit 1 when any holds

A Studio production's edit project (briefs/<n>/studio/) is checked against what production handed it:

| check | holds when |
|---|---|
| every scene in | a scene in the brief's order has no clip in the edit |
| the scene as made | a scene's clip in the edit is not the file production cut for it (swapped, or an old cut) |
| nothing invented | the edit plays a picture or sound production never made (not a scene's cut, the song, the bed or a read) |
| every line on screen | a caption line production timed for a scene is not drawn in the edit |
| the song and the bed | a song or a music bed production made is not in the edit |
| every version | the control or a hook/footage version the brief names has no finished render, or one older than the cut |
| the level | a finished version is more than 0.5 LU off -14 LUFS |

Checks, not taste: nothing here judges a picture, only that what was made is what plays. Run by `deliver` before any
card is filed; a hold names the scene and what is wrong.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))

MEDIA = (".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".aac")


def _md5(p, cap=None):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _words(s):
    """The words of a text or of the edit's page, as drawn: tags out, entities read, case and punctuation off."""
    import html as H
    t = H.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).lower().replace("\u2019", "'")
    return re.findall(r"[a-z0-9$%]+(?:'[a-z0-9]+)*", t)


def loudness(f):
    """Integrated loudness of a file's sound alone (the picture is not decoded)."""
    import subprocess
    m = subprocess.run(["ffmpeg", "-nostdin", "-vn", "-i", str(f), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(json.loads(m[m.rindex("{"):m.rindex("}") + 1])["input_i"])


def check(n, B=None, level=True, measure=None):
    """[(ok, check, what)] for production n; ok False holds the delivery."""
    import video_studio as VS
    B = Path(B or VS.bdir(n))
    brief = _load(B / "brief.json", {}) or {}
    proj = B / "studio"
    html = (proj / "index.html").read_text() if (proj / "index.html").is_file() else ""
    out = []
    if not html:
        return [(False, "every scene in", "no edit project yet (studio/index.html): the render has not run")]
    used = set(re.findall(r'src="([^"]+)"', html))
    used_media = {u for u in used if u.lower().endswith(MEDIA) and not u.startswith("http")}
    made = {}
    from collections import Counter
    body = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    body = re.sub(r'data-timeline-label="[^"]*"', " ", body)          # a track's label is not a word on screen
    drawn = Counter(_words(body))
    for s in brief.get("order") or []:
        pick = (brief.get("picks") or {}).get(s, "take-1")
        cut = B / "scenes" / s / "out" / pick / (s + ".mp4")
        # the project names a scene's clip by the scene, or by its take and scene when the pick is not the first take
        rel = next((u for u in used_media if Path(u).stem in (s, "%s-%s" % (pick, s))), None)
        if not rel:
            out.append((False, "every scene in", "%s is not in the edit" % s))
            continue
        made[rel] = s
        if not cut.is_file():
            out.append((False, "the scene as made", "%s: production's cut (%s) is missing" % (s, cut.relative_to(B))))
        elif not (proj / rel).is_file() or os.path.getsize(proj / rel) != os.path.getsize(cut) or _md5(proj / rel) != _md5(cut):
            out.append((False, "the scene as made", "%s: the clip in the edit is not production's current cut" % s))
        caps = _load(cut.with_name(s + ".captions.json"), {}) or {}
        missing = []
        for ln in caps.get("lines") or []:
            gone = [w for w in _words(ln.get("text")) if not drawn.get(w)]
            for w in _words(ln.get("text")):
                if drawn.get(w):
                    drawn[w] -= 1
            if gone:
                missing.append((ln.get("text") or "", gone))
        if missing and (brief.get("captions") or {}).get("off") is not True:
            out.append((False, "every line on screen", "%s: %d caption line(s) with words not drawn, first: %r (missing %s)"
                        % (s, len(missing), missing[0][0][:50], ", ".join(missing[0][1][:4]))))
    extra = sorted(u for u in used_media if u not in made and not re.search(r"(song|bed|music|voice|read|sfx|room)", Path(u).stem, re.I))
    if extra:
        out.append((False, "nothing invented", "the edit plays media production never made: %s" % ", ".join(extra[:5])))
    music = B / "music"
    if (music / "bed.json").is_file() and not any(re.search(r"(bed|music|song)", Path(u).stem, re.I) for u in used_media):
        out.append((False, "the song and the bed", "production laid a music bed (music/bed.json) and the edit has no music"))
    if brief.get("song") and not any("song" in Path(u).stem.lower() for u in used_media):
        out.append((False, "the song and the bed", "the brief is sung and the edit has no song"))
    vers = {v["id"]: Path(VS.BRIEFS) / v["file"] for v in VS.versions(n)}
    want = ["control"] + [vid for vid, _, _ in VS._version_ids(brief)]
    cut_t = vers["control"].stat().st_mtime if "control" in vers and vers["control"].is_file() else None
    for vid in want:
        f = vers.get(vid)
        if not f or not f.is_file():
            out.append((False, "every version", "%s has no finished render" % vid))
        elif cut_t and vid != "control" and f.stat().st_mtime < cut_t - 1:
            out.append((False, "every version", "%s was rendered before the latest cut" % vid))
        elif level:
            lufs = (measure or loudness)(f)
            if abs(lufs + 14) > 0.5:
                out.append((False, "the level", "%s sits at %.1f LUFS, not -14" % (vid, lufs)))
    if not any(not ok for ok, _, _ in out):
        out.append((True, "used everything", "%d scenes as made, %d versions, every line on screen" %
                    (len(brief.get("order") or []), len(want))))
    return out


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the production, e.g. used_everything.py idea-36")
    res = check(n)
    for ok, name, what in res:
        print("%s %-22s %s" % ("✓" if ok else "✗", name, what))
    return 1 if any(not ok for ok, _, _ in res) else 0


if __name__ == "__main__":
    sys.exit(main())
