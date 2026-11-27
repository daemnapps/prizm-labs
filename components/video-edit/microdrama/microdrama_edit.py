#!/usr/bin/env python3
"""microdrama_edit.py: the micro-drama edit station, end to end (rules: EDIT-GUIDE.md beside this file).

    python3 microdrama_edit.py build <edit.json> --out <run folder>   # trim, captions, hooks, HyperFrames project, renders
    python3 microdrama_edit.py build <edit.json> --out <run folder> --no-render

Takes the accepted scene clips named in edit.json and makes: a HyperFrames project per version (the regular cut and each
hook), every scene trimmed to its spoken words with dead pauses shortened, joins moved off shot changes, captions timed to
the words, the end card, then a render and a read-back of the sound. It never makes or remakes a clip.
Output goes only under --out (a run folder under runs/). Python 3.9 compatible.
"""
import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))

HF = "hyperframes@0.8.221"
LEAD, TAIL, GAP_MAX, GAP_KEEP = 0.33, 0.35, 0.8, 0.55
FIXES = {"flex": "FLEX", "Nevermind.": "Never mind.", "Nevermind": "Never mind"}


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe_fps(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
               "-of", "csv=p=0", str(path)]).stdout.strip()
    a, b = out.split("/")
    return float(a) / float(b)


def words_of(clip, cache):
    """Word timings from the scene's own sound (cached beside the output)."""
    f = cache / (clip["id"] + ".words.json")
    if f.exists():
        return json.loads(f.read_text())
    import listen  # video-edit's own transcriber
    wav = cache / (clip["id"] + ".wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", clip["file"], "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    got = listen.transcribe(wav)
    ws = [[w["text"], round(w["start"], 3), round(w["end"], 3)] for w in got]
    f.write_text(json.dumps(ws))
    wav.unlink()
    return ws


def shot_changes(clip, cache):
    """Times of hard shot changes: frame-to-frame difference spikes."""
    try:
        import numpy as np
    except ImportError:
        return []
    fps = probe_fps(clip["file"])
    raw = cache / (clip["id"] + ".gray")
    run(["ffmpeg", "-v", "error", "-y", "-i", clip["file"], "-vf", "scale=48:85,format=gray", "-f", "rawvideo", str(raw)])
    a = np.fromfile(str(raw), dtype=np.uint8).reshape(-1, 85, 48).astype(float)
    raw.unlink()
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    return [round((i + 1) / fps, 3) for i, x in enumerate(d) if x > 18]


def plan_clip(clip, words, cuts, fps):
    """Return the kept source ranges [(in, out)] for one scene, in seconds."""
    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                     clip["file"]]).stdout.strip())
    fr = 1.0 / fps
    if clip.get("ranges"):   # the person's own cut points (a repeated line, a bad frame): used as given
        return [(float(x), float(y)) for x, y in clip["ranges"]]
    first, last = (words[0][1], words[-1][2]) if words else (0.0, dur)
    a = clip.get("in", max(0.0, first - clip.get("lead", LEAD)))
    b = clip.get("out", clip.get("tail_to", min(dur, last + clip.get("tail", TAIL))))
    if "in" not in clip:      # a shot change just before the first word: start after it, so no stray frame shows
        for c in cuts:
            if a - fr < c <= first - 0.05 and c > a - 0.4:
                a = c + 2 * fr
    if "out" not in clip and "tail_to" not in clip:   # a shot change just after the last word: end before it
        for c in cuts:
            if last < c <= b + 0.15:
                b = max(last + 0.1, c - 2 * fr)
    a = round(a * fps) / fps
    b = round(b * fps) / fps
    segs = [(a, b)]
    if not clip.get("keep_pauses"):
        inner = [w for w in words if a - 0.06 <= w[1] < b]
        segs, cur = [], a
        for prev, nxt in zip(inner, inner[1:]):
            gap = nxt[1] - prev[2]
            if gap > GAP_MAX:
                cut_from = prev[2] + (GAP_KEEP - 0.3) / 1.0 + 0.0   # keep a breath after the word
                cut_to = nxt[1] - 0.3                               # and a lead into the next
                cut_from = round(cut_from * fps) / fps
                cut_to = round(cut_to * fps) / fps
                if cut_to - cut_from >= 0.2:
                    segs.append((cur, cut_from))
                    cur = cut_to
        segs.append((cur, b))
    return [(round(x, 4), round(y, 4)) for x, y in segs if y - x > 0.1]


def cut_file(src, a, b, out, fps):
    """One piece re-timed to the project's rate, so every join is frame exact."""
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.4f}", "-to", f"{b:.4f}", "-i", str(src), "-r", str(fps),
         "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-g", "12", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-b:a", "192k", str(out)])
    n = int(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                 "-of", "csv=p=0", str(out)]).stdout.strip() or 0)
    return n / fps


def caption_groups(words):
    """words: [text, start, end] on the timeline -> [(start, dur, text)]; 3 to 4 words, sentence breaks respected."""
    phrases, cur = [], []
    for w in words:
        if cur and (w[1] - cur[-1][2] > GAP_MAX or re.search(r"[.?!]$", cur[-1][0])):
            phrases.append(cur)
            cur = []
        cur.append(w)
    if cur:
        phrases.append(cur)
    groups = []
    for ph in phrases:
        n = len(ph)
        k = math.ceil(n / 4)
        size = math.ceil(n / k)
        groups += [ph[i:i + size] for i in range(0, n, size)]
    out = []
    for i, g in enumerate(groups):
        a, b = g[0][1], g[-1][2] + 0.12
        if i + 1 < len(groups):
            b = min(b, groups[i + 1][0][1])
        out.append((a, b - a, " ".join(x[0] for x in g)))
    return out


def write_project(pdir, items, caps, card, font_src):
    (pdir / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(str(HERE / "template" / "hyperframes.json"), str(pdir / "hyperframes.json"))
    (pdir / "meta.json").write_text(json.dumps({"id": pdir.name, "name": pdir.name}))
    t = sum(s["duration"] for s in items)
    rows = "\n".join(
        f'<video id="scene-{html.escape(s["id"])}" class="clip" data-start="{s["start"]:.9f}" data-duration="{s["duration"]:.9f}" '
        f'data-track-index="1" data-timeline-label="{html.escape(s["id"].upper())} · {html.escape(s["label"])}" src="assets/{s["asset"]}" '
        f'data-media-start="0" data-has-audio="true" data-volume="1" playsinline preload="auto"></video>' for s in items)
    crow = "\n".join(
        f'<div class="cap" id="cap{i}" data-start="{a:.9f}" data-duration="{d:.9f}" data-track-index="3" '
        f'data-timeline-label="Caption · {html.escape(tx)}">{html.escape(tx)}</div>' for i, (a, d, tx) in enumerate(caps))
    css = ("*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#000}"
           "#root{position:relative;width:100%;height:100%;overflow:hidden;background:#000}"
           ".clip{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}"
           "#cta{z-index:5;background:#000;display:flex;align-items:center;justify-content:center;padding:10%;"
           "font-family:Proxima,'Helvetica Neue',Arial,sans-serif;color:#fff;text-align:center}"
           "#cta .words{width:100%;display:flex;flex-direction:column;gap:40px}#cta p{font-size:58px;margin:0;line-height:1.15}"
           "#cta h1{font-size:82px;margin:0;line-height:1.1}")
    face = ""
    if font_src:
        shutil.copy(str(font_src), str(pdir / "assets" / "caption-font.woff2"))
        face = "@font-face{font-family:Proxima;src:url('assets/caption-font.woff2');font-weight:600}"
    css += face + (".cap{position:absolute;left:6%;right:6%;top:66%;text-align:center;font-family:Proxima,'Helvetica Neue',Arial,sans-serif;"
                   "font-weight:600;font-size:62px;line-height:1.15;color:#fff;-webkit-text-stroke:7px #000;paint-order:stroke fill;"
                   "text-shadow:0 2px 6px rgba(0,0,0,.45);z-index:8}")
    shutil.copy(str(HERE / "template" / "gsap.min.js"), str(pdir / "assets" / "gsap.min.js"))
    card_html = ""
    if card:
        card_html = (f'<section id="cta" class="clip" data-track-kind="graphics" data-track-index="2" data-start="{t:.9f}" '
                     f'data-duration="{card["secs"]:.9f}" data-timeline-label="End card"><div class="words"><p>{html.escape(card["lines"][0])}</p>'
                     f'<h1>{html.escape(card["lines"][1])}</h1></div></section>')
        t += card["secs"]
    (pdir / "index.html").write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(pdir.name)}</title>'
        f'<script src="assets/gsap.min.js"></script><style>{css}</style></head><body>'
        f'<div id="root" data-composition-id="edit" data-width="1080" data-height="1920" data-fps="24" data-duration="{t:.9f}">\n'
        f'{rows}\n{crow}\n{card_html}\n</div><script>const tl=gsap.timeline({{paused:true}});window.__timelines=window.__timelines||{{}};'
        f'window.__timelines["edit"]=tl;</script></body></html>')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("edit")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.edit).read_text())
    fps = spec.get("fps", 24)
    out = Path(a.out)
    cache = out / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    font = spec.get("caption_font")
    pieces, words_by = [], {}
    for clip in spec["clips"]:
        if clip.get("drop"):
            print(f"{clip['id']}: dropped")
            continue
        ws = words_of(clip, cache)
        words_by[clip["id"]] = ws
        segs = plan_clip(clip, ws, shot_changes(clip, cache), fps)
        print(f"{clip['id']}: keeps " + ", ".join(f"{x:.2f}-{y:.2f}" for x, y in segs))
        for n, (x, y) in enumerate(segs):
            pieces.append({"id": clip["id"] + "abcdefgh"[n] if len(segs) > 1 else clip["id"], "clip": clip["id"], "label": clip.get("label", ""),
                           "file": clip["file"], "in": x, "out": y})
    assets = out / "_pieces"
    assets.mkdir(exist_ok=True)
    for p in pieces:
        p["asset"] = p["id"] + ".mp4"
        p["duration"] = cut_file(p["file"], p["in"], p["out"], assets / p["asset"], fps)
    clipfile = {c["id"]: c["file"] for c in spec["clips"]}
    hook_pieces = {}
    for h in spec.get("hooks", []):
        x, y = h["from"], h["to"]
        item = {"id": "hook-" + h["clip"], "clip": h["clip"], "label": "HOOK", "file": clipfile[h["clip"]], "in": x, "out": y}
        item["asset"] = f'hook-{h["name"]}.mp4'
        item["duration"] = cut_file(item["file"], x, y, assets / item["asset"], fps)
        hook_pieces[h["name"]] = item
    versions = [("regular", [])] + [(n, [hp]) for n, hp in hook_pieces.items()]
    for name, hooks in versions:
        items = [dict(p) for p in hooks] + [dict(p) for p in pieces]
        t = 0.0
        words = []
        for s in items:
            s["start"] = t
            for w, ws, we in words_by[s["clip"]]:
                if s["in"] - 0.06 <= ws < s["out"] - 0.05:
                    words.append([FIXES.get(w, w), s["start"] + ws - s["in"], s["start"] + min(we, s["out"]) - s["in"]])
            t += s["duration"]
        pdir = out / name
        pdir.mkdir(exist_ok=True)
        for s in items:
            (pdir / "assets").mkdir(exist_ok=True)
            shutil.copy(str(assets / s["asset"]), str(pdir / "assets" / s["asset"]))
        write_project(pdir, items, caption_groups(words), spec.get("end_card"), font)
        (pdir / "sequence.json").write_text(json.dumps(items, indent=2))
        print(f"{name}: {t:.1f}s of scenes, {len(caption_groups(words))} captions")
        if not a.no_render:
            run(["npx", "--yes", HF, "check"], cwd=str(pdir))
            run(["npx", "--yes", HF, "render", "-o", f"renders/{name}.mp4"], cwd=str(pdir))
    print("done: open each project folder in HyperFrames (npx hyperframes preview) and look at every join and caption")


if __name__ == "__main__":
    main()
