"""LYRIC CAPTIONS FOR A SUNG CUT: each scene's captions are the locked lyric lines sung over it, word by word, on the
song's measured word times (song/timing.json), shifted onto the scene's own clock (song-cut.json: the scene's slot).

Why: a Real-lane song ad lays the whole song under the picture (swipe_cut, 20 Nov), so its scenes have no read of
their own and their captions.json came out empty; the edit stage then held on "captions". The words shown are the
lyric's own spelling (apostrophes and case kept), timed by the measured words they match.

Run: python3 song_captions.py <production>        writes scenes/<s>/out/<pick>/<s>.captions.json for every scene
"""
import json
import re
import sys

from pathlib import Path

import settings as ST


def _key(t):
    return re.sub(r"[^a-z0-9]", "", str(t).lower())


def line_words(line):
    """The lyric line's own tokens, each timed by the measured words that spell it (sorry, don + t -> don't)."""
    meas = [w for w in line.get("words") or [] if _key(w.get("w"))]
    out, i = [], 0
    for tok in str(line.get("line") or "").split():
        k, got, start, end = _key(tok), "", None, None
        if not k:
            continue
        while i < len(meas) and len(got) < len(k):
            got += _key(meas[i]["w"])
            start = meas[i]["start"] if start is None else start
            end = meas[i]["end"]
            i += 1
        if start is None:                       # the take dropped this word: it shares the last word's time
            if not out:
                continue
            start, end = out[-1]["start"], out[-1]["end"]
        out.append({"text": tok, "start": float(start), "end": float(end)})
    return out


def captions(n):
    B = ST.BRIEFS / n
    brief = json.load(open(B / "brief.json"))
    cut = json.load(open(B / "song-cut.json"))
    import video_studio as VS
    _sb, srun = VS.song_of(n)
    timing = json.load(open(Path(srun) / "song" / "timing.json"))
    made = {}
    for sid in brief["order"]:
        slot = (cut.get("scenes") or {}).get(sid)
        if not slot:
            continue
        lines = []
        for ln in [x for x in timing.get("lines") or [] if x.get("start") is not None]:
            if not (slot["start"] - 0.05 <= float(ln["start"]) < slot["end"]):
                continue
            ws = [{"text": w["text"], "start": round(max(0.0, w["start"] - slot["start"]), 3),
                   "end": round(min(slot["end"], w["end"]) - slot["start"], 3)} for w in line_words(ln)]
            ws = [w for w in ws if w["end"] > w["start"]]
            if ws:
                lines.append({"text": " ".join(w["text"] for w in ws), "start": ws[0]["start"], "end": ws[-1]["end"],
                              "words": ws})
        pick = brief["picks"][sid]
        f = B / "scenes" / sid / "out" / pick / (sid + ".captions.json")
        if f.parent.is_dir():
            json.dump({"scene": sid, "layer": "captions", "style": "lyric", "lines": lines}, open(f, "w"), indent=1,
                      ensure_ascii=False)
            made[sid] = len(lines)
    return made


if __name__ == "__main__":
    print(captions(sys.argv[1]))
