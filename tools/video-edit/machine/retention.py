#!/usr/bin/env python3
"""retention.py — the retention checks: is this edit built to hold attention?

the owner, 2026-09-23: "we're going to get this machine ultra dialed in for attention
retention and customer acquisition … we are literally programming ads for social media."

    check(sheet, video=None, controls=None) -> report     every rule in looks/retention.json
    lines(report) -> [str]                                  what the run prints
    python3 machine/retention.py <run-folder | cutsheet.json> [--video <file>] [--json]

Every number is a dial in looks/retention.json (a run's controls.json overrides it:
{"retention": {"placement": "meta-feed", "dials": {"static-hold": {"max_s": 3}}}}).
NOTHING here blocks an export (the owner, 2026-09-23): the two evidence-backed rules
(hook in 3 s, length band) are INFO lines; every other rule is a WARN with a score and
flags at the seconds where it breaks — the live timeline's Retention lane draws them.

Measured from the cut sheet; the rendered file adds the loop score (ffmpeg SSIM,
first frame against last) and the loudest words (the emphasis fallback).
Standard library + ffmpeg only.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))

PLATES = ("card", "screen", "split", "endcard")
TEXT_PLATES = ("card", "screen", "endcard")
GRAPHIC_LAYERS = ("lower_thirds", "annotations", "platform_ui", "icons", "registry")
ZOOM_TRANSITIONS = ("zoom", "cinematic-zoom", "gl-zoom-blur", "gl-cube", "gl-doorway")


# ---------------------------------------------------------------- settings
def settings() -> dict:
    return json.loads((TOOL / "looks/retention.json").read_text())


def rules(controls: dict | None = None) -> tuple[list[dict], str, dict]:
    """The rows with the run's dial overrides applied, the placement id and its row."""
    S = settings()
    rc = (controls or {}).get("retention") or {}
    over = rc.get("dials") or {}
    rows = []
    for r in S["rules"]:
        r = json.loads(json.dumps(r))
        r["threshold"].update(over.get(r["id"]) or {})
        rows.append(r)
    pl = rc.get("placement") or S["placement"]["value"]
    return rows, pl, S["placement"]["options"].get(pl) or {"name": pl, "length_s": None}


# ---------------------------------------------------------------- what happens when
def _end(sheet: dict) -> float:
    return max((c["start"] + c["duration"] for c in sheet.get("picture") or []), default=0.0)


def _dedupe(ts: list[float], eps: float = 0.04) -> list[float]:
    out: list[float] = []
    for t in sorted(ts):
        if not out or t - out[-1] > eps:
            out.append(round(t, 3))
    return out


def caption_lines(sheet: dict) -> list[list[dict]]:
    caps = sheet.get("captions") or {}
    words = caps.get("words") or []
    if not words or ((sheet.get("controls") or {}).get("captions") or {}).get("value", "on") != "on":
        return []
    try:
        import compose as C
        mx = C.look_of(sheet).get("max_words", 3)
    except Exception:
        mx = 3
    lines, cur = [], []
    for w in words:  # the same grouping compose.py draws
        if cur and (len(cur) >= mx or w["start"] - cur[-1]["end"] > 0.35 or cur[-1]["text"].rstrip()[-1:] in ".!?"):
            lines.append(cur); cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    quiet = [(c["start"], c["start"] + c["duration"]) for c in sheet.get("picture") or [] if c.get("kind") in TEXT_PLATES]
    return [ln for ln in lines if not any(a <= (ln[0]["start"] + ln[-1]["end"]) / 2 < b for a, b in quiet)]


def scene_ends(sheet: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in sheet.get("picture") or []:
        sc = c.get("scene") or c["id"]
        out[sc] = max(out.get(sc, 0.0), c["start"] + c["duration"])
    return out


def events(sheet: dict) -> dict[str, list[float]]:
    """Every moment something changes, by kind, on the final clock."""
    pics = sheet.get("picture") or []
    end = _end(sheet)
    cuts = _dedupe([t for c in pics for t in (c["start"], c["start"] + c["duration"]) if 0.02 < t < end - 0.02])
    zooms = []
    a = sorted((c for c in pics if c.get("roll") == "a"), key=lambda c: c["start"])
    for prev, c in zip(a, a[1:]):
        if (c.get("punch") or 1.0) != (prev.get("punch") or 1.0) and (c.get("scene") or c["id"]) == (prev.get("scene") or prev["id"]):
            zooms.append(c["start"])
    ends = scene_ends(sheet)
    trans = []
    for t in (sheet.get("layers") or {}).get("transitions") or []:
        if t.get("kind", "cut") != "cut" and t.get("after_scene") in ends:
            trans.append(ends[t["after_scene"]])
            if t["kind"] in ZOOM_TRANSITIONS:
                zooms.append(ends[t["after_scene"]])
    zooms += [z["at"] for z in sheet.get("zooms") or [] if isinstance(z, dict) and z.get("at") is not None]
    graphics = [o["start"] for o in sheet.get("overlays") or [] if o.get("start") is not None]
    L = sheet.get("layers") or {}
    for k in GRAPHIC_LAYERS:
        graphics += [r["start"] for r in L.get(k) or [] if r.get("start") is not None]
    for c in pics:  # a plate's own words land line by line
        if c.get("kind") in TEXT_PLATES:
            d = c.get(c["kind"]) or {}
            at = d.get("lands_at", c["start"] + 0.1)
            n = len(d.get("lines") or d.get("offer_lines") or [1])
            graphics += [at + j * 0.15 for j in range(n)]
    return {"cuts": cuts, "zooms": _dedupe(zooms), "transitions": _dedupe(trans), "graphics": _dedupe(graphics),
            "captions": _dedupe([ln[0]["start"] for ln in caption_lines(sheet)]),
            "sfx": _dedupe([s["at"] for s in sheet.get("sfx") or [] if s.get("at") is not None])}


def _gaps(ts: list[float], lo: float, hi: float, limit: float) -> list[tuple[float, float]]:
    pts = [lo] + [t for t in sorted(ts) if lo < t < hi] + [hi]
    return [(a, b) for a, b in zip(pts, pts[1:]) if b - a > limit + 1e-6]


def _merge(spans: list[tuple[float, float]], join: float = 0.05) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1] + join:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in out]


def _minus(spans, holes):
    out = []
    for a, b in spans:
        cur = [(a, b)]
        for h0, h1 in holes:
            nxt = []
            for x, y in cur:
                if h1 <= x or h0 >= y:
                    nxt.append((x, y))
                else:
                    if h0 > x: nxt.append((x, h0))
                    if h1 < y: nxt.append((h1, y))
            cur = nxt
        out += cur
    return [(a, b) for a, b in out if b - a > 0.05]


def _row(r: dict, status: str, score, value, detail: str, flags=None) -> dict:
    return {"id": r["id"], "name": r["name"], "severity": r["severity"], "evidence": r["evidence"], "threshold": r["threshold"],
            "status": status, "score": None if score is None else round(max(0.0, min(100.0, score))), "value": value,
            "detail": detail, "flags": flags or [], "source": r["source"]}


def _span_score(spans, limit, end) -> float:
    excess = sum((b - a) - limit for a, b in spans)
    return 100.0 * (1 - excess / end) if end else 100.0


# ---------------------------------------------------------------- the rules
def hook_3s(r, sheet, ev, video):
    th = r["threshold"]
    hooks = [o for o in sheet.get("overlays") or [] if o.get("kind") == "hook"]
    first = min((o["start"] for o in hooks), default=None)
    frame_one = first is not None and first <= th["frame_one_s"]
    words = (sheet.get("captions") or {}).get("words") or []
    spoken_end = None
    if words:
        for w in words:
            spoken_end = w["end"]
            if w["text"].rstrip()[-1:] in ".!?":
                break
    shown = sum(max(0.0, min(o["start"] + o["duration"], th["by_s"]) - o["start"]) for o in hooks if o["start"] < th["by_s"])
    lands = (spoken_end is not None and spoken_end <= th["by_s"]) or shown >= th["read_s"]
    met = frame_one and lands
    parts = [f"hook text {'on screen from frame one' if frame_one else ('first on at %.2fs' % first if first is not None else 'not on screen')}",
             f"hook line spoken by {spoken_end:.2f}s" if spoken_end is not None else "no spoken line",
             f"hook text up {shown:.1f}s of the first {th['by_s']:g}s"]
    return _row(r, "info", 100 if met else 0, "met" if met else "not met", " · ".join(parts),
                [] if met else [{"s": 0.0, "e": th["by_s"], "detail": "hook does not land in the first 3 s (info only)"}])


def length_band(r, sheet, ev, video, placement=None):
    pid, prow = placement
    end = _end(sheet)
    band = prow.get("length_s")
    if not band:
        return _row(r, "info", None, f"{end:.1f}s", f"{prow.get('name', pid)} — no length band; the piece runs {end:.1f}s")
    ok = band[0] <= end <= band[1]
    return _row(r, "info", 100 if ok else 0, f"{end:.1f}s", f"{prow.get('name', pid)}: {band[0]}–{band[1]}s band, the piece runs {end:.1f}s — {'inside' if ok else 'outside'} (info only)")


def static_hold(r, sheet, ev, video):
    lim, end = r["threshold"]["max_s"], _end(sheet)
    allev = ev["cuts"] + ev["zooms"] + ev["transitions"] + ev["graphics"] + ev["captions"] + ev["sfx"]
    spans = _gaps(allev, 0.0, end, lim)
    longest = max((b - a for a, b in _gaps(allev, 0.0, end, 0)), default=0.0)
    flags = [{"s": a, "e": b, "detail": f"nothing changes for {b - a:.1f}s (dial {lim:g}s)"} for a, b in spans]
    return _row(r, "warn" if spans else "pass", _span_score(spans, lim, end), f"longest {longest:.1f}s",
                f"{len(spans)} hold(s) over {lim:g}s" if spans else f"something changes at least every {lim:g}s (longest gap {longest:.1f}s)", flags)


def change_cadence(r, sheet, ev, video):
    lim, end = r["threshold"]["every_s"], _end(sheet)
    vis = ev["cuts"] + ev["zooms"] + ev["transitions"] + ev["graphics"]
    spans = _gaps(vis, 0.0, end, lim)
    n = len(_dedupe(vis))
    flags = [{"s": a, "e": b, "detail": f"no cut, zoom or graphic for {b - a:.1f}s (dial {lim:g}s)"} for a, b in spans]
    return _row(r, "warn" if spans else "pass", _span_score(spans, lim, end), f"{n} visual changes, {n / end * 4:.1f} per 4s" if end else "0",
                f"{len(spans)} stretch(es) with no visual change for over {lim:g}s" if spans else f"a visual change at least every {lim:g}s", flags)


def voice_spans(sheet: dict) -> list[tuple[float, float]]:
    end = _end(sheet)
    sp = [(c["start"], c["start"] + c["duration"]) for c in sheet.get("picture") or [] if c.get("talks")]
    sp += [(v["start"], v["start"] + v["duration"]) for v in sheet.get("voice_cuts") or []]
    if sheet.get("voice"):
        v = sheet["voice"]
        sp.append((v.get("start", 0), v.get("start", 0) + (v.get("duration") or end)))
    return _merge(sp)


def dead_air(r, sheet, ev, video):
    lim = r["threshold"]["max_s"]
    words = sorted((sheet.get("captions") or {}).get("words") or [], key=lambda w: w["start"])
    vs = voice_spans(sheet)
    if not words or not vs:
        return _row(r, "pass", None, "no voice", "no spoken words to measure")
    flags, total, speech = [], 0.0, sum(b - a for a, b in vs)
    marks = []
    for a, b in vs:  # silence at the head and tail of each voiced run, and between words inside it
        inside = [w for w in words if a - 0.05 <= w["start"] < b]
        if not inside:
            continue
        marks.append((a, inside[0]["start"]))
        marks += [(x["end"], y["start"]) for x, y in zip(inside, inside[1:])]
        marks.append((inside[-1]["end"], b))
    for s, e in marks:
        if e - s > lim + 1e-6:
            total += e - s
            flags.append({"s": round(s, 3), "e": round(e, 3), "detail": f"{e - s:.2f}s of silence left in (dial {lim:g}s)"})
    return _row(r, "warn" if flags else "pass", 100.0 * (1 - total / speech) if speech else 100, f"{total:.2f}s dead air",
                f"{len(flags)} silence(s) over {lim:g}s, {total:.2f}s in all" if flags else f"no silence over {lim:g}s while the voice runs", flags)


def sfx_pairing(r, sheet, ev, video):
    th = r["threshold"]
    pops = ev["captions"]
    if not pops:
        return _row(r, "pass", None, "no caption pops", "captions are off or empty — nothing to pair")
    paired = [p for p in pops if any(abs(s - p) <= th["window_s"] for s in ev["sfx"])]
    ratio = len(paired) / len(pops)
    flags = [{"s": p, "e": p, "point": True, "detail": "caption pop with no sound effect"} for p in pops if p not in paired]
    return _row(r, "warn" if ratio < th["min_ratio"] else "pass", ratio * 100, f"{len(paired)}/{len(pops)} ({ratio:.0%})",
                f"{len(paired)} of {len(pops)} caption pops carry a sound effect (dial {th['min_ratio']:.0%})", flags)


def _loudness(video: Path, words: list[dict]) -> list[float] | None:
    """RMS of the rendered sound under each word (stdlib: ffmpeg → 8 kHz mono PCM)."""
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
    except Exception:
        return None
    pcm = array.array("h"); pcm.frombytes(raw[: len(raw) // 2 * 2])
    if not pcm:
        return None
    out = []
    for w in words:
        a, b = int(w["start"] * 8000), max(int(w["start"] * 8000) + 1, int(w["end"] * 8000))
        seg = pcm[a:b]
        out.append(math.sqrt(sum(x * x for x in seg) / len(seg)) if seg else 0.0)
    return out


def emphasis_words(sheet: dict, video: Path | None, share: float) -> tuple[list[dict], str]:
    words = (sheet.get("captions") or {}).get("words") or []
    marked = [w for w in words if w.get("emphasis")]
    if marked:
        return marked, "marked on the sheet"
    if video and Path(video).is_file() and words:
        loud = _loudness(Path(video), words)
        if loud and max(loud) > 0:
            n = max(1, round(len(words) * share))
            top = sorted(range(len(words)), key=lambda i: -loud[i])[:n]
            return [words[i] for i in sorted(top)], f"the loudest {share:.0%} of words in the rendered sound"
    pick = [w for w in words if re.search(r"\d", w["text"]) or w["text"].rstrip("!?.,").isupper() and len(w["text"].strip("!?.,")) > 1 or w["text"].endswith("!")]
    return pick, "numbers, ALL CAPS and '!' words"


def zoom_emphasis(r, sheet, ev, video):
    th = r["threshold"]
    emph, how = emphasis_words(sheet, video, th["loudest_share"])
    if not emph:
        return _row(r, "pass", None, "no emphasis words", f"no emphasis words found ({how})")
    hit = [w for w in emph if any(w["start"] - th["window_s"] <= z <= w["end"] + th["window_s"] for z in ev["zooms"])]
    ratio = len(hit) / len(emph)
    flags = [{"s": w["start"], "e": w["end"], "point": True, "detail": f"emphasis word “{w['text']}” with no zoom"} for w in emph if w not in hit]
    return _row(r, "warn" if ratio < th["min_ratio"] else "pass", ratio * 100, f"{len(hit)}/{len(emph)} ({ratio:.0%})",
                f"{len(hit)} of {len(emph)} emphasis words get a zoom — emphasis = {how} (dial {th['min_ratio']:.0%})", flags)


def broll_cadence(r, sheet, ev, video):
    lim = r["threshold"]["max_talking_s"]
    pics = sheet.get("picture") or []
    talk = _merge([(c["start"], c["start"] + c["duration"]) for c in pics if c.get("roll") == "a" and c.get("talks")])
    covered = [(c["start"], c["start"] + c["duration"]) for c in pics if c.get("roll") == "b"]
    runs = _minus(talk, covered)
    if not runs:
        return _row(r, "pass", None, "no talking runs", "no presenter-on-screen stretch without cover")
    L = sheet.get("layers") or {}
    marks = [r_["start"] for k in GRAPHIC_LAYERS for r_ in L.get(k) or [] if r_.get("start") is not None]
    spans = [g for a, b in runs for g in _gaps(marks, a, b, lim)]
    total = sum(b - a for a, b in runs)
    every = [g for a, b in runs for g in _gaps(marks, a, b, 0)]
    longest = max((y - x for x, y in every), default=0.0)
    flags = [{"s": a, "e": b, "detail": f"{b - a:.1f}s of talking with no B-roll or graphic (dial {lim:g}s)"} for a, b in spans]
    return _row(r, "warn" if spans else "pass", _span_score(spans, lim, total), f"longest {longest:.1f}s",
                f"{len(spans)} talking stretch(es) over {lim:g}s with nothing cut in" if spans else f"a cutaway at least every {lim:g}s of talking", flags)


def text_hook_1s(r, sheet, ev, video):
    by = r["threshold"]["by_s"]
    ts = [o["start"] for o in sheet.get("overlays") or [] if o.get("start") is not None and (o.get("text") or o.get("kind") == "end-card")]
    lines = caption_lines(sheet)
    if lines:
        ts.append(max(0.0, lines[0][0]["start"] - 0.06))
    for c in sheet.get("picture") or []:
        if c.get("kind") in TEXT_PLATES:
            ts.append((c.get(c["kind"]) or {}).get("lands_at", c["start"] + 0.1))
    ts += [x["start"] for x in (sheet.get("layers") or {}).get("platform_ui") or [] if x.get("start") is not None and x.get("text")]
    first = min(ts, default=None)
    if first is None:
        return _row(r, "warn", 0, "no text", "no words on screen at all", [{"s": 0.0, "e": by, "detail": "no text on screen"}])
    ok = first <= by + 1e-6
    return _row(r, "pass" if ok else "warn", 100 if ok else 100 - 50 * (first - by), f"{first:.2f}s",
                f"first words on screen at {first:.2f}s (dial {by:g}s)", [] if ok else [{"s": 0.0, "e": first, "detail": f"no words on screen until {first:.2f}s"}])


def ssim_first_last(video: Path) -> float | None:
    """SSIM (0–1) between the first and the last frame, both scaled to 270×480 grey."""
    import tempfile
    d = Path(tempfile.mkdtemp())
    try:
        vf = "scale=270:480,format=gray"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0", "-i", str(video), "-frames:v", "1", "-vf", vf, str(d / "a.png")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.12", "-i", str(video), "-frames:v", "1", "-update", "1", "-vf", vf, str(d / "b.png")], check=True)
        err = subprocess.run(["ffmpeg", "-v", "info", "-i", str(d / "a.png"), "-i", str(d / "b.png"), "-lavfi", "ssim", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = re.search(r"All:([0-9.]+)", err)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def loop_ending(r, sheet, ev, video):
    th = r["threshold"]
    if not video or not Path(video).is_file():
        return _row(r, "not measured", None, "—", "measured on the rendered file — not rendered yet")
    s = ssim_first_last(Path(video))
    if s is None:
        return _row(r, "not measured", None, "—", "could not read the first and last frames")
    end = _end(sheet)
    return _row(r, "pass" if s >= th["min_ssim"] else "warn", s * 100, f"SSIM {s:.2f}",
                f"last frame against the first: SSIM {s:.2f} (dial {th['min_ssim']:g}; 1.0 = identical)",
                [] if s >= th["min_ssim"] else [{"s": max(0.0, end - 0.5), "e": end, "detail": f"the ending does not loop back to the first frame (SSIM {s:.2f})"}])


RULES = {"hook-3s": hook_3s, "length-band": length_band, "static-hold": static_hold, "change-cadence": change_cadence,
         "dead-air": dead_air, "sfx-pairing": sfx_pairing, "zoom-emphasis": zoom_emphasis, "broll-cadence": broll_cadence,
         "text-hook-1s": text_hook_1s, "loop-ending": loop_ending}


def check(sheet: dict, video: Path | str | None = None, controls: dict | None = None) -> dict:
    """Every retention rule on this sheet (+ the rendered file when given). Never blocks."""
    rows, pid, prow = rules(controls if controls is not None else sheet.get("controls"))
    ev = events(sheet)
    video = Path(video) if video else None
    out = []
    for r in rows:
        fn = RULES.get(r["id"])
        if not fn:
            continue
        out.append(fn(r, sheet, ev, video, placement=(pid, prow)) if r["id"] == "length-band" else fn(r, sheet, ev, video))
    scored = [x["score"] for x in out if x["severity"] == "warn" and x["score"] is not None]
    return {"score": round(sum(scored) / len(scored)) if scored else None,
            "warnings": sum(1 for x in out if x["status"] == "warn"),
            "blocks_export": False, "placement": pid, "length_s": round(_end(sheet), 3),
            "measured_on": "cut sheet + rendered file" if video else "cut sheet",
            "rules": out, "events": {k: len(v) for k, v in ev.items()}}


def lines(report: dict) -> list[str]:
    out = [f"RETENTION  score {report['score'] if report['score'] is not None else '—'}/100 · {report['warnings']} warning(s) · "
           f"placement {report['placement']} · measured on the {report['measured_on']} · never blocks the export"]
    for x in report["rules"]:
        tag = {"pass": "OK   ", "warn": "WARN ", "info": "INFO ", "not measured": "---  "}.get(x["status"], "     ")
        out.append(f"  {tag}{x['name']}: {x['detail']}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a run folder or a cutsheet.json")
    ap.add_argument("--video"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    p = Path(a.target).resolve()
    video = Path(a.video) if a.video else None
    if p.is_dir():
        sp = p / "deliverable" / "cutsheet.json"
        if not sp.exists():
            sp = sorted(p.glob("cutsheet-v*.json"), key=lambda x: int(x.stem.split("-v")[1]))[-1]
        video = video or next((v for v in (p / "work" / "final.mp4", p / "work" / "captioned.mp4") if v.exists()), None)
        p = sp
    rep = check(json.loads(p.read_text()), video)
    print(json.dumps(rep, indent=1, ensure_ascii=False) if a.json else "\n".join(lines(rep)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
