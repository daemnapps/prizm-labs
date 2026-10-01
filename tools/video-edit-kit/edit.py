#!/usr/bin/env python3
"""THE EDIT KIT — the edit line as small commands an editor's agent runs on any
9:16 talking-head piece. Brand-free. Runs wherever there is Python 3.10+ and
ffmpeg: a laptop, or the Higgsfield sandbox (which has everything preinstalled).

Every number lives in settings.json beside this file. What each step does and
why: README.md.

    python3 edit.py doctor
        what this machine has, and which steps it can run
    python3 edit.py listen CLIP [CLIP ...]
        hears each clip: start/end silence, breaths (kept), mid-clip pauses
        (numbered P1, P2 ... for the editor to keep or cut), a line that stops
        short (cut off), and the clip's loudness
    python3 edit.py cut CUT.json --out rough.mp4 [--anyway]
        cut to the sound: start/end silence out, breaths kept, pauses cut
        unless the sheet keeps them, a 7% punch-in after each cut pause, the
        scenes in the sheet's order, hard cuts, every clip levelled to match.
        Stops if a talking clip is cut off (--anyway makes a review cut)
    python3 edit.py words VIDEO --out words.json [--script FILE | --sheet CUT.json]
        word timings off the sound; with the script, shown in the script's spelling
    python3 edit.py captions VIDEO WORDS.json --out captioned.mp4 [--report rough.report.json] [--look bold-highlight]
        burns the captions (2-4 words, the spoken word lit) and the sheet's
        hook/cards (from frame one) — type is always a layer on top
    python3 edit.py punch VIDEO --at 3.2-4.1 [--at ...] --out out.mp4 [--zoom 1.07]
        punch-ins on chosen moments, sound untouched
    python3 edit.py frame MOVE ...
        the frame fixes (clean, seams, bridge, loopclose ...) — runs
        ../video-edit/frame-control/framectl.py; needs numpy + opencv
    python3 edit.py safezone VIDEO [--boxes captioned.boxes.json] [--sheet-out sheet.png]
        9:16 check and the centred 4:5 band: faces (when opencv is here) and
        every text box must sit inside it; a contact sheet with the band drawn
    python3 edit.py loudness VIDEO
    python3 edit.py master VIDEO --out master.mp4
        -14 LUFS integrated, -1 dBTP peak; picture copied untouched
    python3 edit.py check VIDEO [--report rough.report.json]
        the final gate: 9:16, length, never black, mastered, no dead air
    python3 edit.py run CUT.json --out-dir OUT [--anyway] [--no-captions]
        all of it in order: cut, words, captions, master, safezone, check
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "settings.json").read_text())
FRAMECTL = HERE.parent / "video-edit" / "frame-control" / "framectl.py"


# ---------------------------------------------------------------- plumbing
def sh(cmd: list, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, check=check)


def ff(*args) -> None:
    r = sh(["ffmpeg", "-v", "error", "-y", *args])
    if r.returncode:
        raise SystemExit(f"ffmpeg failed: {r.stderr.strip()[-800:]}")


def probe(path: Path) -> dict:
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
            "-of", "json", path])
    if r.returncode:
        raise SystemExit(f"cannot read {path}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    fps = None
    if v.get("r_frame_rate") and v["r_frame_rate"] != "0/0":
        a, b = v["r_frame_rate"].split("/")
        fps = round(float(a) / float(b), 3) if float(b) else None
    return {"duration": float(d.get("format", {}).get("duration") or 0), "width": v.get("width"), "height": v.get("height"),
            "fps": fps, "audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


def write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def silences(path: Path, db: float | None = None, min_s: float | None = None) -> list[tuple[float, float]]:
    """Stretches quieter than `db` for `min_s` or longer, heard in the sound itself."""
    db = S["listen"]["silence_db"] if db is None else db
    min_s = S["listen"]["silence_min_s"] if min_s is None else min_s
    err = sh(["ffmpeg", "-nostats", "-v", "info", "-i", path, "-vn", "-af", f"silencedetect=noise={db}dB:d={min_s}", "-f", "null", "-"]).stderr
    out, start = [], None
    for line in err.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append((round(start, 3), round(float(m.group(1)), 3)))
            start = None
    if start is not None:  # silent to the end
        out.append((round(start, 3), round(probe(path)["duration"], 3)))
    return out


def loudness(path: Path) -> tuple[float | None, float | None]:
    """Integrated LUFS and true peak (dBTP), measured by ffmpeg's ebur128."""
    err = sh(["ffmpeg", "-nostats", "-v", "info", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    lufs = tp = None
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else err
    for line in summary.splitlines():
        t = line.strip()
        if t.startswith("I:") and "LUFS" in t:
            lufs = float(t.split("I:")[1].split("LUFS")[0])
        if t.startswith("Peak:") and "dBFS" in t:
            tp = float(t.split("Peak:")[1].split("dBFS")[0])
    return lufs, tp


def table(rows: list[list], head: list[str]) -> str:
    rows = [[str(c) for c in r] for r in rows]
    w = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(head)]
    line = lambda r: "  ".join(c.ljust(w[i]) for i, c in enumerate(r))  # noqa: E731
    return "\n".join([line(head), line(["-" * x for x in w])] + [line(r) for r in rows])


# ---------------------------------------------------------------- listen
def listen_clip(path: Path) -> dict:
    """What the sound says about one clip: where the talking starts and ends,
    every gap (breath or pause), and whether the line runs into the clip's end."""
    info = probe(path)
    dur = info["duration"]
    if not info["audio"]:
        return {"clip": str(path), "duration": dur, "silent": True, "why": "no sound track"}
    sil = silences(path)
    sounds, t = [], 0.0
    for a, b in sil:
        if a - t > 0.02:
            sounds.append((round(t, 3), a))
        t = b
    if dur - t > 0.02:
        sounds.append((round(t, 3), round(dur, 3)))
    if not sounds:
        return {"clip": str(path), "duration": dur, "silent": True, "why": "nothing above the silence line"}
    first, last = sounds[0][0], sounds[-1][1]
    breath = S["cut"]["breath_under_s"]
    gaps, n = [], 0
    for (a0, a1), (b0, _) in zip(sounds, sounds[1:]):
        g = round(b0 - a1, 3)
        if g >= breath:
            n += 1
            gaps.append({"id": f"P{n}", "kind": "pause", "from": a1, "to": b0, "length": g})
        else:
            gaps.append({"id": None, "kind": "breath", "from": a1, "to": b0, "length": g})
    tail = round(dur - last, 3)
    lufs, tp = loudness(path)
    return {"clip": str(path), "duration": round(dur, 3), "silent": False, "talk_from": first, "talk_to": last,
            "start_silence": first, "end_silence": tail, "sounds": sounds,
            "pauses": [g for g in gaps if g["kind"] == "pause"], "breaths": [g for g in gaps if g["kind"] == "breath"],
            "cut_off": tail < S["cut_off"]["end_window_s"], "lufs": lufs, "true_peak": tp}


def cmd_listen(a) -> int:
    rows, out = [], []
    for c in a.clips:
        r = listen_clip(Path(c))
        out.append(r)
        if r.get("silent"):
            rows.append([Path(c).name, f"{r['duration']:.2f}", "-", "-", "-", "-", "silent: " + r["why"]])
            continue
        ps = ", ".join(f"{p['id']} {p['length']:.2f}s@{p['from']:.2f}" for p in r["pauses"]) or "none"
        rows.append([Path(c).name, f"{r['duration']:.2f}", f"{r['start_silence']:.2f}", f"{r['end_silence']:.2f}",
                     len(r["breaths"]), ps, "CUT OFF - back to production" if r["cut_off"] else "whole line"])
    print(table(rows, ["clip", "secs", "start silence", "end silence", "breaths kept", "pauses (P#: length @ where)", "line"]))
    if a.out:
        write(Path(a.out), out)
    return 0


# ---------------------------------------------------------------- cut
def load_sheet(p: Path) -> dict:
    sheet = json.loads(p.read_text())
    base = p.resolve().parent
    for i, sc in enumerate(sheet.get("scenes") or []):
        sc.setdefault("id", f"s{i + 1:02d}")
        for k in ("clip", "still"):
            if sc.get(k) and not Path(sc[k]).is_absolute():
                sc[k] = str(base / sc[k])
    return sheet


def pieces_for(sc: dict, heard: dict, keep: set[str]) -> list[dict]:
    """Source spans to keep from one talking clip, each with its punch."""
    lead, tail = S["cut"]["lead_s"], S["cut"]["tail_s"]
    dur = heard["duration"]
    a = max(0.0, heard["talk_from"] - lead)
    out, n = [], 0
    for p in heard["pauses"]:
        if p["id"] in keep:
            continue
        out.append((a, min(dur, p["from"] + tail), p["id"]))
        a = max(0.0, p["to"] - lead)
    out.append((a, min(dur, heard["talk_to"] + tail), None))
    res = []
    for k, (s, e, cut_pause) in enumerate(out):
        z = S["punch"]["zoom"] if (k % 2 == 1 and sc.get("punch", True)) else 1.0
        res.append({"from": round(s, 3), "to": round(e, 3), "punch": z, "after_cut": out[k - 1][2] if k else None})
        n += 1
    return res


def render_piece(src: Path | None, still: Path | None, s: float, d: float, zoom: float, gain_db: float,
                 fps: float, has_audio: bool, out: Path) -> None:
    W, H = S["canvas"]["width"], S["canvas"]["height"]
    oy = S["punch"]["origin_y"]
    vf = (f"scale=w={W * zoom:.0f}:h={H * zoom:.0f}:force_original_aspect_ratio=increase:force_divisible_by=2,"
          f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{oy},fps={fps},setsar=1,format=yuv420p")
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart"]
    if still:
        ff("-loop", "1", "-framerate", fps, "-t", f"{d:.3f}", "-i", still, "-f", "lavfi", "-t", f"{d:.3f}",
           "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-map", "0:v", "-map", "1:a", *enc, "-shortest", out)
        return
    if has_audio:
        ff("-ss", f"{s:.3f}", "-t", f"{d:.3f}", "-i", src, "-vf", vf, "-af", f"volume={gain_db:.2f}dB,aresample=48000",
           "-map", "0:v", "-map", "0:a", *enc, out)
    else:
        ff("-ss", f"{s:.3f}", "-t", f"{d:.3f}", "-i", src, "-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
           "-vf", vf, "-map", "0:v", "-map", "1:a", *enc, out)


def do_cut(sheet_path: Path, out: Path, anyway: bool = False) -> dict:
    sheet = load_sheet(sheet_path)
    scenes = sheet.get("scenes") or []
    if not scenes:
        raise SystemExit("the cut sheet has no scenes")
    first_clip = next((sc["clip"] for sc in scenes if sc.get("clip")), None)
    fps = sheet.get("fps") or (probe(Path(first_clip))["fps"] if first_clip else None) or S["canvas"]["fps"]
    target = S["level"]["clip_lufs"]
    plan, cut_off, pauses = [], [], []
    for sc in scenes:
        if sc.get("still"):
            plan.append({"scene": sc["id"], "still": sc["still"], "from": 0, "to": float(sc.get("hold", 1.0)), "punch": 1.0})
            continue
        src = Path(sc["clip"])
        if not src.is_file():
            raise SystemExit(f"{sc['id']}: clip not found: {src}")
        info = probe(src)
        if sc.get("talks", True) is False or not info["audio"]:  # picture that carries no line: played as asked, sound as it is
            s = float(sc.get("from", 0)); e = float(sc.get("to", info["duration"]))
            plan.append({"scene": sc["id"], "src": str(src), "from": s, "to": e, "punch": 1.0, "gain": 0.0, "audio": info["audio"]})
            continue
        heard = listen_clip(src)
        if heard.get("silent"):
            plan.append({"scene": sc["id"], "src": str(src), "from": 0, "to": info["duration"], "punch": 1.0, "gain": 0.0, "audio": info["audio"]})
            continue
        if heard["cut_off"]:
            cut_off.append(f"{sc['id']} ({src.name}): the sound is still going at the clip's last frame - the line probably stops short")
        keep = set(sc.get("keep") or [])
        gain = round(target - heard["lufs"], 2) if heard.get("lufs") is not None else 0.0
        for p in heard["pauses"]:
            pauses.append({"scene": sc["id"], "pause": p["id"], "length": p["length"], "at_source": p["from"],
                           "action": "kept" if p["id"] in keep else "cut"})
        for pc in pieces_for(sc, heard, keep):
            plan.append({"scene": sc["id"], "src": str(src), **pc, "gain": gain, "audio": True})
    if cut_off and not anyway:
        raise SystemExit("STOP - a talking clip is cut off. It goes back to production, never edited around:\n  "
                         + "\n  ".join(cut_off) + "\n(--anyway makes a review cut with this marked)")
    out = Path(out)
    work = Path(tempfile.mkdtemp(prefix="cut-", dir=out.parent if out.parent.exists() else None)).resolve()
    t, segs = 0.0, []
    for k, p in enumerate(plan):
        d = round(p["to"] - p["from"], 3)
        seg = work / f"p{k:03d}.mp4"
        render_piece(Path(p["src"]) if p.get("src") else None, Path(p["still"]) if p.get("still") else None,
                     p["from"], d, p["punch"], p.get("gain", 0.0), fps, p.get("audio", False), seg)
        real = probe(seg)["duration"]
        p.update(start=round(t, 3), duration=round(real, 3))
        t += real
        segs.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs))
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out)
    shutil.rmtree(work, ignore_errors=True)
    overlays = []
    for o in sheet.get("overlays") or []:
        o = dict(o)
        if o.get("with"):
            parts = [p for p in plan if p["scene"] == o["with"]]
            if not parts:
                continue
            o["start"] = min(p["start"] for p in parts)
            o["end"] = round(max(p["start"] + p["duration"] for p in parts), 3)
        overlays.append(o)
    rep = {"video": str(out), "fps": fps, "length": round(probe(out)["duration"], 3), "pieces": plan, "pauses": pauses,
           "cut_off": cut_off, "overlays": overlays, "captions": sheet.get("captions") or {},
           "script": " ".join(sc.get("line", "") for sc in scenes if sc.get("line")).strip() or None}
    write(out.with_suffix(".report.json"), rep)
    return rep


def cmd_cut(a) -> int:
    rep = do_cut(Path(a.sheet), Path(a.out), a.anyway)
    rows = [[p["scene"], f"{p['start']:.2f}", f"{p['duration']:.2f}", f"{p['from']:.2f}-{p['to']:.2f}",
             "7% in" if p["punch"] != 1.0 else "", p.get("after_cut") or ""] for p in rep["pieces"]]
    print(table(rows, ["scene", "at", "secs", "source span", "punch", "after cut pause"]))
    if rep["pauses"]:
        print("\nPauses (keep any that land a beat: add its P# to that scene's \"keep\" in the cut sheet and cut again):")
        print(table([[x["scene"], x["pause"], f"{x['length']:.2f}s", f"{x['at_source']:.2f}", x["action"]] for x in rep["pauses"]],
                    ["scene", "pause", "length", "at (clip secs)", "now"]))
    for c in rep["cut_off"]:
        print("CUT OFF:", c)
    print(f"\n{rep['video']}  {rep['length']:.2f}s  ->  report: {Path(rep['video']).with_suffix('.report.json')}")
    return 0


# ---------------------------------------------------------------- words
def transcribe(video: Path, model: str = "base.en") -> list[dict]:
    try:
        from faster_whisper import WhisperModel  # Higgsfield's sandbox has it
        m = WhisperModel(model, device="cpu", compute_type="int8")
        segs, _ = m.transcribe(str(video), word_timestamps=True, language="en")
        return [{"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
                for s in segs for w in (s.words or []) if w.word.strip()]
    except ImportError:
        pass
    if shutil.which("hyperframes"):
        d = Path(tempfile.mkdtemp(prefix="words-"))
        r = sh(["hyperframes", "transcribe", video, "--dir", d])
        f = d / "transcript.json"
        if r.returncode or not f.is_file():
            raise SystemExit(f"transcribe failed: {r.stderr.strip()[-400:]}")
        ws = json.loads(f.read_text())
        ws = ws["words"] if isinstance(ws, dict) else ws
        return [{"text": (w.get("text") or w.get("word")).strip(), "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)}
                for w in ws if (w.get("text") or w.get("word", "")).strip()]
    raise SystemExit("no transcriber here: pip install faster-whisper (Higgsfield's sandbox already has it)")


def do_words(video: Path, out: Path, script: str | None = None, model: str = "base.en") -> dict:
    heard = transcribe(video, model)
    notes: list[str] = []
    words = heard
    if script:
        sys.path.insert(0, str(HERE))
        import spelling
        words, notes = spelling.align(heard, script)
    d = {"video": str(video), "words": words, "notes": notes, "spelling": "script" if script else "as heard"}
    write(out, d)
    return d


def cmd_words(a) -> int:
    script = None
    if a.script:
        script = Path(a.script).read_text()
    elif a.sheet:
        script = " ".join(sc.get("line", "") for sc in json.loads(Path(a.sheet).read_text()).get("scenes", []) if sc.get("line")).strip() or None
    d = do_words(Path(a.video), Path(a.out), script, a.model)
    print(f"{len(d['words'])} words -> {a.out} ({d['spelling']})")
    for n in d["notes"][:20]:
        print(" -", n)
    return 0


# ---------------------------------------------------------------- captions + cards
def font_path(want: str | None = None) -> str:
    for f in ([want] if want else []) + S["fonts"]:
        p = Path(f).expanduser()
        if p.is_file():
            return str(p)
    raise SystemExit("no heavy font found: pass --font /path/to/font.ttf")


def caption_lines(words: list[dict], max_words: int) -> list[list[dict]]:
    """Group timed words into on-screen lines: break on a pause, on sentence punctuation, or when full."""
    lines, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > S["caption_break_s"] or cur[-1]["text"].rstrip()[-1:] in ".!?"):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def _rgba(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + ((int(h[6:8], 16),) if len(h) == 8 else (255,))


def _case(t: str, case: str) -> str:
    return t.upper() if case == "upper" else t


def do_captions(video: Path, words_json: Path | None, out: Path, report: Path | None = None, look: str | None = None,
                font: str | None = None, captions: bool = True) -> dict:
    from PIL import Image, ImageDraw, ImageFont
    rep = json.loads(report.read_text()) if report and report.is_file() else {}
    look = look or (rep.get("captions") or {}).get("look") or "bold-highlight"
    L, C = S["looks"][look], S["looks"]["card"]
    info = probe(video)
    W, H, end = info["width"], info["height"], info["duration"]
    fp = font_path(font)
    words = (json.loads(words_json.read_text())["words"] if words_json else []) if captions else []
    lines = caption_lines(words, L["max_words"])

    # every moment something changes on screen
    states = []  # (start, end, line_idx, word_idx)
    for i, ln in enumerate(lines):
        stop = ln[-1]["end"] + 0.3
        if i + 1 < len(lines):
            stop = min(stop, lines[i + 1][0]["start"])
        for k, w in enumerate(ln):
            s = w["start"]
            e = ln[k + 1]["start"] if k + 1 < len(ln) else stop
            if e > s:
                states.append((s, e, i, k))
    overlays = [o for o in rep.get("overlays") or [] if o.get("text")]
    cuts = {0.0, end}
    for s, e, *_ in states:
        cuts |= {max(0.0, s), min(end, e)}
    for o in overlays:
        cuts |= {max(0.0, float(o["start"])), min(end, float(o["end"]))}
    cuts = sorted(c for c in cuts if 0 <= c <= end)

    work = Path(tempfile.mkdtemp(prefix="caps-")).resolve()
    cache: dict = {}
    boxes: list[dict] = []

    def zone_px(zid: str) -> tuple[int, int, int, int]:
        z = S["zones"][zid]
        return round(W * z["x"] / 100), round(H * z["y"] / 100), round(W * z["w"] / 100), round(H * z["h"] / 100)

    def fit(text: str, size: int, maxw: int, stroke: int):
        while size > 28:
            f = ImageFont.truetype(fp, size)
            if f.getlength(text) + 2 * stroke <= maxw:
                return f
            size -= 2
        return ImageFont.truetype(fp, size)

    def draw_card(d, o) -> list[tuple]:
        zx, zy, zw, _ = zone_px(o.get("zone") or C["zone"])
        rows = str(o["text"]).split("\n")
        k = W / 1080
        f = fit(max(rows, key=len), round(C["size_px"] * k), zw, 0)
        pad, y, out = round(16 * k), zy, []
        for r in rows:
            l, t, rr, b = f.getbbox(r)
            tw, th = rr - l, b - t
            x = zx + (zw - tw) // 2
            box = (x - pad, y, x + tw + pad, y + th + 2 * pad)
            d.rectangle(box, fill=_rgba(C["plate"]))
            d.text((x - l, y + pad - t), r, font=f, fill=_rgba(C["color"]))
            out.append(box)
            y = box[3]
        return out

    def draw_line(d, ln, k) -> tuple:
        zx, zy, zw, zh = zone_px(L["zone"])
        sc = W / 1080
        toks = [_case(w["text"], L["case"]) for w in ln]
        stroke = round(L["stroke_px"] * sc)
        f = fit(" ".join(toks), round(L["size_px"] * sc), zw, stroke)
        space = f.getlength(" ")
        widths = [f.getlength(t) for t in toks]
        total = sum(widths) + space * (len(toks) - 1)
        x = zx + (zw - total) / 2
        asc, desc = f.getmetrics()
        y = zy + (zh - (asc + desc)) / 2
        box = (int(x - stroke), int(y - stroke), int(x + total + stroke), int(y + asc + desc + stroke))
        if L.get("plate"):
            p = round(14 * sc)
            box = (box[0] - p, box[1] - p, box[2] + p, box[3] + p)
            d.rounded_rectangle(box, radius=round(12 * sc), fill=_rgba(L["plate"]))
        for i, (t, wdt) in enumerate(zip(toks, widths)):
            col = L["highlight"] if i == k else L["color"]
            d.text((x, y), t, font=f, fill=_rgba(col), stroke_width=stroke, stroke_fill=_rgba(L["stroke"]))
            x += wdt + space
        return box

    def frame_for(t0: float, t1: float) -> Path:
        mid = (t0 + t1) / 2
        st = next(((i, k) for s, e, i, k in states if s <= mid < e), None)
        ov = tuple(n for n, o in enumerate(overlays) if float(o["start"]) <= mid < float(o["end"]))
        key = (st, ov)
        if key not in cache:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            drawn = []
            for n in ov:
                drawn += [("card", b) for b in draw_card(d, overlays[n])]
            if st:
                drawn.append(("caption", draw_line(d, lines[st[0]], st[1])))
            p = work / f"f{len(cache):04d}.png"
            img.save(p)
            cache[key] = (p, drawn)
        p, drawn = cache[key]
        for kind, b in drawn:
            boxes.append({"kind": kind, "from": round(t0, 3), "to": round(t1, 3), "box": list(b)})
        return p

    lst = work / "list.txt"
    rows, last = [], None
    for t0, t1 in zip(cuts, cuts[1:]):
        if t1 - t0 < 1e-3:
            continue
        last = frame_for(t0, t1)
        rows.append(f"file '{last.as_posix()}'\nduration {t1 - t0:.4f}\n")
    if last:
        rows.append(f"file '{last.as_posix()}'\n")
    lst.write_text("".join(rows))
    ff("-i", video, "-f", "concat", "-safe", "0", "-i", lst, "-filter_complex",
       "[1:v]format=rgba[o];[0:v][o]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]",
       "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "copy",
       "-movflags", "+faststart", out)
    shutil.rmtree(work, ignore_errors=True)
    merged: list[dict] = []
    for b in boxes:  # one row per box per unbroken stretch
        if merged and merged[-1]["box"] == b["box"] and merged[-1]["kind"] == b["kind"] and abs(merged[-1]["to"] - b["from"]) < 1e-3:
            merged[-1]["to"] = b["to"]
        else:
            merged.append(dict(b))
    res = {"video": str(out), "look": look, "font": fp, "lines": len(lines), "cards": len(overlays), "boxes": merged, "frame": [W, H]}
    write(Path(out).with_suffix(".boxes.json"), res)
    return res


def cmd_captions(a) -> int:
    r = do_captions(Path(a.video), Path(a.words) if a.words else None, Path(a.out), Path(a.report) if a.report else None,
                    a.look, a.font, not a.no_captions)
    print(f"{r['lines']} caption lines, {r['cards']} cards, look {r['look']}, font {Path(r['font']).name} -> {a.out}")
    return 0


# ---------------------------------------------------------------- punch
def cmd_punch(a) -> int:
    info = probe(Path(a.video))
    W, H, dur = info["width"], info["height"], info["duration"]
    spans = sorted(tuple(float(x) for x in s.split("-")) for s in a.at)
    parts, t = [], 0.0
    for s, e in spans:
        if s > t:
            parts.append((t, s, 1.0))
        parts.append((s, min(e, dur), a.zoom))
        t = min(e, dur)
    if t < dur:
        parts.append((t, dur, 1.0))
    oy = S["punch"]["origin_y"]
    fc = [f"[0:v]split={len(parts)}" + "".join(f"[i{k}]" for k in range(len(parts)))]
    for k, (s, e, z) in enumerate(parts):
        zz = (f",scale={W * z:.0f}:{H * z:.0f}:force_divisible_by=2,crop={W}:{H}:(iw-{W})/2:(ih-{H})*{oy}" if z != 1.0 else "")
        fc.append(f"[i{k}]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS{zz},setsar=1[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0,format=yuv420p[v]")
    ff("-i", a.video, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "17", "-c:a", "copy", "-movflags", "+faststart", a.out)
    print(f"{len(spans)} punch-in(s) at {a.zoom:.2f}x -> {a.out}")
    return 0


# ---------------------------------------------------------------- frame fixes
def cmd_frame(a) -> int:
    if not FRAMECTL.is_file():
        raise SystemExit(f"framectl.py not found at {FRAMECTL} - clone the whole tools/ folder")
    return subprocess.call([sys.executable, str(FRAMECTL), *a.rest])


# ---------------------------------------------------------------- safe zone
def do_safezone(video: Path, boxes: Path | None = None, sheet_out: Path | None = None, step: float = 0.5) -> dict:
    info = probe(video)
    W, H = info["width"], info["height"]
    top, bot = S["safe"]["band_4x5_top_pct"] / 100, S["safe"]["band_4x5_bottom_pct"] / 100
    res = {"video": str(video), "size": [W, H], "checks": []}
    add = lambda name, ok, detail: res["checks"].append({"check": name, "pass": ok, "detail": detail})  # noqa: E731
    add("9:16 frame", bool(W and H and abs(W / H - 9 / 16) < 0.01), f"{W}x{H}")
    if boxes and boxes.is_file():
        bad = []
        uit, uib, uir = S["safe"]["ui_top_pct"] / 100, S["safe"]["ui_bottom_pct"] / 100, S["safe"]["ui_right_pct"] / 100
        for b in json.loads(boxes.read_text())["boxes"]:
            x0, y0, x1, y1 = b["box"]
            if y0 < H * top or y1 > H * bot:
                bad.append(f"{b['kind']} {b['from']:.2f}-{b['to']:.2f}s sits outside the 4:5 band (y {y0}-{y1} of {H})")
            elif y0 < H * uit or y1 > H * (1 - uib) or x1 > W * (1 - uir):
                bad.append(f"{b['kind']} {b['from']:.2f}-{b['to']:.2f}s sits under the app's buttons")
        add("every word on screen inside the 4:5 band", not bad, "; ".join(bad[:6]) or "all text boxes inside")
    try:
        import cv2
        cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        every, n, seen, out_of = max(1, round(fps * step)), 0, 0, []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            if n % every == 0:
                g = cv2.cvtColor(cv2.resize(fr, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY)
                for (x, y, w, h) in cas.detectMultiScale(g, 1.1, 6, minSize=(W // 12, W // 12)):
                    seen += 1
                    if y * 2 < H * top or (y + h) * 2 > H * bot:
                        out_of.append(f"{n / fps:.1f}s")
            n += 1
        add("faces inside the 4:5 band", not out_of,
            f"{seen} face sightings checked" + (f"; outside at {', '.join(sorted(set(out_of))[:10])}" if out_of else ""))
    except ImportError:
        res["checks"].append({"check": "faces inside the 4:5 band", "pass": None,
                              "detail": "opencv not installed - look at the contact sheet (pip install opencv-python-headless to automate)"})
    if sheet_out:
        n = max(1, int(info["duration"] // 2))
        cols = 6
        rows = max(1, -(-min(n, 24) // cols))
        sw, shh = 216, 384
        y0, y1 = round(shh * top), round(shh * bot)
        ff("-i", video, "-vf", f"fps=1/2,scale={sw}:{shh},drawbox=x=0:y={y0}:w={sw}:h=2:color=red@0.9:t=fill,"
           f"drawbox=x=0:y={y1}:w={sw}:h=2:color=red@0.9:t=fill,tile={cols}x{rows}", "-frames:v", "1", sheet_out)
        res["sheet"] = str(sheet_out)
    return res


def cmd_safezone(a) -> int:
    r = do_safezone(Path(a.video), Path(a.boxes) if a.boxes else None, Path(a.sheet_out) if a.sheet_out else None)
    print(table([["PASS" if c["pass"] else ("LOOK" if c["pass"] is None else "FAIL"), c["check"], c["detail"]] for c in r["checks"]],
                ["", "check", "detail"]))
    if r.get("sheet"):
        print("contact sheet (red lines = the 4:5 band):", r["sheet"])
    return 0 if all(c["pass"] is not False for c in r["checks"]) else 1


# ---------------------------------------------------------------- loudness + master
def cmd_loudness(a) -> int:
    i, tp = loudness(Path(a.video))
    print(f"{i} LUFS integrated, {tp} dBTP peak (master target {S['master']['lufs']} LUFS, peak at or under {S['master']['true_peak_db']} dBTP)")
    return 0


def do_master(video: Path, out: Path) -> dict:
    """Two passes of loudnorm on the sound only, then a limiter; picture copied untouched."""
    lufs, tp = S["master"]["lufs"], S["master"]["true_peak_db"]
    if not probe(video)["audio"]:
        shutil.copy(video, out)
        return {"mastered": False, "why": "no sound in the file"}
    af = f"loudnorm=I={lufs}:TP={tp - 0.5}:LRA=11"
    err = sh(["ffmpeg", "-nostats", "-v", "info", "-i", video, "-vn", "-af", af + ":print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(err[err.rindex("{"): err.rindex("}") + 1])
    af2 = (af + f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    ff("-i", video, "-c:v", "copy", "-af", af2 + f",alimiter=limit={10 ** ((tp - 0.3) / 20):.4f}:level=false",
       "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out)
    got = loudness(out)
    return {"mastered": True, "lufs": got[0], "true_peak_db": got[1]}


def cmd_master(a) -> int:
    r = do_master(Path(a.video), Path(a.out))
    print(f"mastered: {r.get('lufs')} LUFS, {r.get('true_peak_db')} dBTP -> {a.out}" if r["mastered"] else r["why"])
    return 0


# ---------------------------------------------------------------- final gate
def do_check(video: Path, report: Path | None = None) -> list[dict]:
    info = probe(video)
    res = []
    add = lambda name, ok, detail: res.append({"check": name, "pass": ok, "detail": detail})  # noqa: E731
    add("9:16, 1080x1920", (info["width"], info["height"]) == (S["canvas"]["width"], S["canvas"]["height"]), f"{info['width']}x{info['height']}")
    if report and report.is_file():
        want = json.loads(report.read_text())["length"]
        add("length matches the cut", abs(info["duration"] - want) <= S["checks"]["length_tolerance_s"], f"{info['duration']:.2f}s, cut was {want:.2f}s")
    black = sh(["ffmpeg", "-v", "info", "-i", video, "-vf", "blackdetect=d=0.2:pix_th=0.05", "-an", "-f", "null", "-"]).stderr
    add("picture never goes black", "black_start" not in black, "no black frames" if "black_start" not in black else "black frames found")
    lufs, tp = loudness(video)
    m = S["master"]
    add("mastered", lufs is not None and abs(lufs - m["lufs"]) <= m["tolerance_lu"] and tp is not None and tp <= m["true_peak_db"] + 0.1,
        f"{lufs} LUFS, {tp} dBTP (want {m['lufs']} +-{m['tolerance_lu']}, peak at or under {m['true_peak_db']})")
    dead = [(a, b) for a, b in silences(video, min_s=S["checks"]["dead_air_s"])]
    add("no dead air", not dead, "none" if not dead else "; ".join(f"{a:.2f}-{b:.2f}s" for a, b in dead[:8]))
    return res


def cmd_check(a) -> int:
    r = do_check(Path(a.video), Path(a.report) if a.report else None)
    print(table([["PASS" if c["pass"] else "FAIL", c["check"], c["detail"]] for c in r], ["", "check", "detail"]))
    return 0 if all(c["pass"] for c in r) else 1


# ---------------------------------------------------------------- the whole line
def cmd_run(a) -> int:
    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    name = a.name or Path(a.sheet).stem
    print("1/6 cut to the sound ...", flush=True)
    rep = do_cut(Path(a.sheet), od / f"{name}--rough.mp4", a.anyway)
    rough = Path(rep["video"])
    report = rough.with_suffix(".report.json")
    print(f"    {rep['length']:.2f}s, {len(rep['pieces'])} pieces, {sum(1 for p in rep['pauses'] if p['action'] == 'cut')} pauses cut"
          + (f", CUT OFF: {len(rep['cut_off'])}" if rep["cut_off"] else ""), flush=True)
    dressed = rough
    if not a.no_captions:
        print("2/6 words ...", flush=True)
        wj = od / f"{name}--words.json"
        w = do_words(rough, wj, rep.get("script"), a.model)
        print(f"    {len(w['words'])} words ({w['spelling']})", flush=True)
        print("3/6 captions + cards ...", flush=True)
        dressed = od / f"{name}--captioned.mp4"
        do_captions(rough, wj, dressed, report, a.look, a.font)
    else:
        print("2/6 3/6 captions skipped", flush=True)
    print("4/6 master ...", flush=True)
    final = od / f"{name}--master-9x16.mp4"
    mr = do_master(dressed, final)
    print(f"    {mr.get('lufs')} LUFS, {mr.get('true_peak_db')} dBTP", flush=True)
    print("5/6 safe zone ...", flush=True)
    boxes = dressed.with_suffix(".boxes.json") if dressed != rough else None
    sz = do_safezone(final, boxes, od / f"{name}--safezone.png")
    print("6/6 final checks ...", flush=True)
    ck = do_check(final, report)
    allc = sz["checks"] + ck
    print(table([["PASS" if c["pass"] else ("LOOK" if c["pass"] is None else "FAIL"), c["check"], c["detail"]] for c in allc], ["", "check", "detail"]))
    write(od / f"{name}--checks.json", {"master": str(final), "checks": allc, "cut": str(report)})
    print(f"\nmaster: {final}")
    return 0 if all(c["pass"] is not False for c in allc) else 1


def cmd_doctor(a) -> int:
    rows = []
    ffv = sh(["ffmpeg", "-version"]).stdout.splitlines()[:1] if shutil.which("ffmpeg") else []
    rows.append(["ffmpeg", "yes" if ffv else "NO", ffv[0] if ffv else "needed by every step"])
    filt = sh(["ffmpeg", "-hide_banner", "-filters"]).stdout if ffv else ""
    for f in ("silencedetect", "ebur128", "loudnorm", "overlay", "drawbox", "tile", "blackdetect"):
        rows.append([f"  filter {f}", "yes" if re.search(rf"\s{f}\s", filt) else "NO", ""])
    def has(mod):
        try:
            __import__(mod)
            return True
        except Exception:
            return False
    rows.append(["Pillow", "yes" if has("PIL") else "NO", "captions + cards"])
    rows.append(["faster-whisper", "yes" if has("faster_whisper") else "no", "words (or the hyperframes CLI: " + ("yes" if shutil.which("hyperframes") else "no") + ")"])
    rows.append(["opencv + numpy", "yes" if has("cv2") and has("numpy") else "no", "frame fixes and the automatic face check"])
    try:
        rows.append(["heavy font", "yes", font_path()])
    except SystemExit:
        rows.append(["heavy font", "NO", "pass --font"])
    rows.append(["framectl.py", "yes" if FRAMECTL.is_file() else "no", str(FRAMECTL)])
    print(table(rows, ["needs", "here", "for"]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("doctor").set_defaults(fn=cmd_doctor)
    p = sp.add_parser("listen"); p.add_argument("clips", nargs="+"); p.add_argument("--out"); p.set_defaults(fn=cmd_listen)
    p = sp.add_parser("cut"); p.add_argument("sheet"); p.add_argument("--out", required=True); p.add_argument("--anyway", action="store_true"); p.set_defaults(fn=cmd_cut)
    p = sp.add_parser("words"); p.add_argument("video"); p.add_argument("--out", required=True); p.add_argument("--script"); p.add_argument("--sheet")
    p.add_argument("--model", default="base.en"); p.set_defaults(fn=cmd_words)
    p = sp.add_parser("captions"); p.add_argument("video"); p.add_argument("words", nargs="?"); p.add_argument("--out", required=True)
    p.add_argument("--report"); p.add_argument("--look", choices=[k for k in S["looks"] if k not in ("card", "what")]); p.add_argument("--font")
    p.add_argument("--no-captions", action="store_true", help="cards only"); p.set_defaults(fn=cmd_captions)
    p = sp.add_parser("punch"); p.add_argument("video"); p.add_argument("--at", action="append", required=True); p.add_argument("--out", required=True)
    p.add_argument("--zoom", type=float, default=S["punch"]["zoom"]); p.set_defaults(fn=cmd_punch)
    p = sp.add_parser("frame"); p.add_argument("rest", nargs=argparse.REMAINDER); p.set_defaults(fn=cmd_frame)
    p = sp.add_parser("safezone"); p.add_argument("video"); p.add_argument("--boxes"); p.add_argument("--sheet-out"); p.set_defaults(fn=cmd_safezone)
    p = sp.add_parser("loudness"); p.add_argument("video"); p.set_defaults(fn=cmd_loudness)
    p = sp.add_parser("master"); p.add_argument("video"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_master)
    p = sp.add_parser("check"); p.add_argument("video"); p.add_argument("--report"); p.set_defaults(fn=cmd_check)
    p = sp.add_parser("run"); p.add_argument("sheet"); p.add_argument("--out-dir", required=True); p.add_argument("--name"); p.add_argument("--anyway", action="store_true")
    p.add_argument("--no-captions", action="store_true"); p.add_argument("--look", choices=[k for k in S["looks"] if k not in ("card", "what")]); p.add_argument("--font")
    p.add_argument("--model", default="base.en"); p.set_defaults(fn=cmd_run)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
