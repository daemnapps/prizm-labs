#!/usr/bin/env python3
"""The editor's working files for a maker pack, built every time it is packed (owner, 16 Nov 2026: "any hand off needs
this stuff ... i am literally taking a step off of the production side and handing off what i have to the editors").

    python3 maker_editfiles.py <hand-off folder>        (maker_pack.py calls it by itself)

Writes into the hand-off folder, from its clips.json:
  edit/placeholders/<clip id>.mp4   one slate per clip still to make: its swipe frame, "MAKE <clip id>", its length
  edit/<key>.premiere.xml           the ad as a Premiere sequence (Final Cut XML, File > Import): V1 the picture, made
                                    scenes in place and a slate wherever a clip goes; A1 the voice reads; a marker on
                                    every scene with its on-screen words. Media is found by file name inside the folder;
                                    when Premiere asks, point it at the folder once and it finds the rest. Swap each
                                    slate for its returned clip (Replace Footage) as they come in.
  hyperframes/                      the same timeline as a HyperFrames project (index.html, assets/), open with
                                    `hyperframes preview hyperframes`
Spends nothing; plain ffmpeg on this machine.
"""
import html
import os
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

FPS = 30
W, H = 1080, 1920
FONT = next((f for f in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if Path(f).exists()), None)


def _secs(src):
    m = re.match(r"\s*(\d+):(\d+(?:\.\d+)?)\s*-\s*(\d+):(\d+(?:\.\d+)?)", src or "")
    if not m:
        return None
    a, b = int(m[1]) * 60 + float(m[2]), int(m[3]) * 60 + float(m[4])
    return b - a if b > a else None


def _dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def _esc(t):
    return str(t).replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def _card(frame, title, sub, png):
    """The slate's one picture: the swipe frame darkened, a band with the clip id and what it is (Pillow, since an
    ffmpeg without drawtext is common)."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont
    if frame and Path(frame).exists():
        im = Image.open(frame).convert("RGB")
        s = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * s + 1), int(im.height * s + 1)))
        x, y = (im.width - W) // 2, (im.height - H) // 2
        im = ImageEnhance.Brightness(im.crop((x, y, x + W, y + H))).enhance(0.6)
    else:
        im = Image.new("RGB", (W, H), (43, 43, 43))
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, int(H * 0.40), W, int(H * 0.60)), fill=(0, 0, 0, 160))
    def font(n):
        try:
            return ImageFont.truetype(FONT, n) if FONT else ImageFont.load_default()
        except OSError:
            return ImageFont.load_default()
    for text, size, colour, top in ((title, 88, (255, 255, 255), 0.445), (sub, 44, (255, 178, 122), 0.525)):
        f = font(size)
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, H * top), text, font=f, fill=colour)
    im.save(png)


def _slate(out, frame, title, sub, secs):
    """A placeholder clip: the swipe frame darkened, the clip id and what it is, the exact length."""
    import tempfile
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        png = Path(t) / "slate.png"
        _card(frame, title, sub, png)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(png), "-t", "%.3f" % secs,
                        "-r", str(FPS), "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "30", "-an", str(out)],
                       check=True)


def _items(folder, doc):
    """The picture track in order: (name, file relative to the folder, seconds, scene row, clip or None)."""
    clips = {c["id"]: c for c in doc["clips"]}
    items = []
    for s in doc["scenes"]:
        span = s.get("secs") or _secs(s.get("swipe")) or 2.0
        if s.get("file"):
            d = _dur(folder / s["file"]) or span
            items.append({"name": Path(s["file"]).name, "file": s["file"], "secs": d, "scene": s, "clip": None})
            continue
        cl = [clips[c] for c in s.get("clips") or [] if c in clips and not clips[c].get("hold")]   # a held clip is left out
        for c in cl:
            each = c.get("secs") or max(round(span / max(len(cl), 1), 3), 0.5)
            mid = next((r for r in c.get("refs") or [] if r.endswith("-mid.jpg")), None) or next(iter(c.get("refs") or []), None)
            rel = "edit/placeholders/%s" % Path(c["return"]).name          # the clip's one name (its return name)
            _slate(folder / rel, folder / mid if mid else None, "MAKE " + c["id"], "%s · %.1f s · returns as %s" % (
                s.get("section") or s["scene"], each, Path(c["return"]).name), each)
            items.append({"name": Path(c["return"]).name, "file": rel, "secs": each, "scene": s, "clip": c})
    return items


def _fr(secs):
    return int(round(secs * FPS))


def premiere(folder, doc, items):
    """Final Cut Pro 7 XML (xmeml v4), which Premiere imports as a sequence."""
    t, v, a, marks, files = 0, [], [], [], {}

    def fileref(i, rel, dur_fr, audio=False):
        fid = "file-%d" % i
        if rel in files:
            return '<file id="%s"/>' % files[rel]
        files[rel] = fid
        media = ("<media><audio><samplecharacteristics><samplerate>48000</samplerate><depth>16</depth>"
                 "</samplecharacteristics></audio></media>" if audio else
                 "<media><video><samplecharacteristics><width>%d</width><height>%d</height></samplecharacteristics>"
                 "</video></media>" % (W, H))
        return ('<file id="%s"><name>%s</name><pathurl>%s</pathurl><rate><timebase>%d</timebase></rate>'
                "<duration>%d</duration>%s</file>" % (fid, html.escape(Path(rel).name), html.escape(quote(os.path.relpath(rel, "edit"))),
                                                       FPS, dur_fr, media))
    seen_scene = set()
    first = {}
    for i, it in enumerate(items, 1):
        d = _fr(it["secs"])
        at = (it["scene"].get("song_at") or [None])[0]
        if at is not None and it["scene"]["scene"] not in first:
            first[it["scene"]["scene"]] = True
            t = _fr(at)
        v.append('<clipitem id="v-%d"><name>%s</name><duration>%d</duration><rate><timebase>%d</timebase></rate>'
                 "<start>%d</start><end>%d</end><in>0</in><out>%d</out>%s</clipitem>"
                 % (i, html.escape(it["name"]), d, FPS, t, t + d, d, fileref(i, it["file"], d)))
        s = it["scene"]
        if s["scene"] not in seen_scene:
            seen_scene.add(s["scene"])
            note = " / ".join(x for x in [s.get("words"), (s.get("on_screen") or "").replace("\n", " / ")] if x)
            marks.append("<marker><name>%s</name><comment>%s</comment><in>%d</in><out>-1</out></marker>"
                         % (html.escape("%d · %s · %s" % (s["n"], s["scene"], s.get("section") or "")), html.escape(note), t))
            if s.get("voice"):
                vd = _fr(_dur(folder / s["voice"]) or it["secs"])
                a.append('<clipitem id="a-%d"><name>%s</name><duration>%d</duration><rate><timebase>%d</timebase></rate>'
                         "<start>%d</start><end>%d</end><in>0</in><out>%d</out>%s</clipitem>"
                         % (i, html.escape(Path(s["voice"]).name), vd, FPS, t, t + vd, vd,
                            fileref(1000 + i, s["voice"], vd, audio=True)))
        t += d
    song = folder / "song" / "song.mp3"
    if song.exists():                    # a sung ad: the whole song on its own track under the picture
        sd = _fr(_dur(song) or t / FPS)
        a.append('<clipitem id="a-song"><name>song.mp3</name><duration>%d</duration><rate><timebase>%d</timebase></rate>'
                 "<start>0</start><end>%d</end><in>0</in><out>%d</out>%s</clipitem>"
                 % (sd, FPS, sd, sd, fileref(9999, "song/song.mp3", sd, audio=True)))
        t = max(t, sd)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="seq-1">'
           "<name>%s</name><duration>%d</duration><rate><timebase>%d</timebase></rate>%s"
           "<media><video><format><samplecharacteristics><width>%d</width><height>%d</height>"
           "<rate><timebase>%d</timebase></rate></samplecharacteristics></format><track>%s</track></video>"
           "<audio><track>%s</track></audio></media></sequence></xmeml>\n"
           % (html.escape(doc["key"]), t, FPS, "".join(marks), W, H, FPS, "".join(v), "".join(a)))
    out = folder / "edit" / ("%s.premiere.xml" % doc["key"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml)
    return out


def hyperframes(folder, doc, items):
    """The same timeline as a HyperFrames project: picture on track 1, voice on track 2, on-screen words on track 3."""
    hf = folder / "hyperframes"
    (hf / "assets").mkdir(parents=True, exist_ok=True)
    els, t, seen = [], 0.0, set()
    first = {}
    song = folder / "song" / "song.mp3"
    if song.exists():
        shutil.copy2(song, hf / "assets" / "song.mp3")
        els.append('<audio id="song" class="clip" data-start="0" data-duration="%.3f" data-track-index="2" '
                   'data-timeline-label="song" src="assets/song.mp3" data-volume="1"></audio>' % (_dur(song) or 0))
    for i, it in enumerate(items, 1):
        at = (it["scene"].get("song_at") or [None])[0]
        if at is not None and it["scene"]["scene"] not in first:
            first[it["scene"]["scene"]] = True
            t = float(at)
        name = "%02d-%s" % (i, Path(it["file"]).name)
        shutil.copy2(folder / it["file"], hf / "assets" / name)
        s = it["scene"]
        label = ("MAKE " + it["clip"]["id"]) if it["clip"] else "%s · made" % s["scene"]
        els.append('<video id="v%d" class="clip pic" data-start="%.3f" data-duration="%.3f" data-track-index="1" '
                   'data-timeline-label="%s" src="assets/%s" data-media-start="0" muted playsinline></video>'
                   % (i, t, it["secs"], html.escape(label), name))
        if s["scene"] not in seen:
            seen.add(s["scene"])
            if s.get("voice"):
                vn = Path(s["voice"]).name
                shutil.copy2(folder / s["voice"], hf / "assets" / vn)
                els.append('<audio id="a%d" class="clip" data-start="%.3f" data-duration="%.3f" data-track-index="2" '
                           'data-timeline-label="voice · %s" src="assets/%s" data-volume="1"></audio>'
                           % (i, t, _dur(folder / s["voice"]) or it["secs"], s["scene"], vn))
            if s.get("on_screen"):
                span = sum(x["secs"] for x in items if x["scene"] is s)
                els.append('<div id="c%d" class="clip cap" data-start="%.3f" data-duration="%.3f" data-track-index="3" '
                           'data-timeline-label="on screen · %s"><span>%s</span></div>'
                           % (i, t, span, s["scene"], html.escape((s["on_screen"] or "").split("\n")[0])))
        t += it["secs"]
    page = ('<!doctype html>\n<html><head><meta charset="utf-8">'
            '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
            "<style>html,body{margin:0;background:#000}#stage{position:relative;width:%dpx;height:%dpx;overflow:hidden;background:#000}"
            ".pic{position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover}"
            ".cap{position:absolute;left:0;width:100%%;top:62%%;z-index:30;display:flex;justify-content:center}"
            ".cap span{max-width:860px;text-align:center;font:800 58px/72px -apple-system,Helvetica,Arial,sans-serif;color:#fff;"
            "-webkit-text-stroke:8px #000;paint-order:stroke fill}</style></head><body>\n"
            '<div id="stage" data-composition-id="edit" data-start="0" data-width="%d" data-height="%d" data-fps="%d" '
            'data-duration="%.3f">\n%s\n<script>\nconst tl = gsap.timeline({ paused: true });\n'
            'window.__timelines = window.__timelines || {};\nwindow.__timelines["edit"] = tl;\n</script>\n</div></body></html>\n'
            % (W, H, W, H, FPS, max(t, (_dur(song) or 0) if song.exists() else 0), "\n".join(els)))
    (hf / "index.html").write_text(page)
    (hf / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components",
                                                               "assets": "assets"}}, indent=1))
    (hf / "meta.json").write_text(json.dumps({"id": doc["key"], "name": doc["key"]}, indent=1))
    return hf


def build(folder):
    folder = Path(folder)
    doc = json.loads((folder / "clips.json").read_text())
    items = _items(folder, doc)
    return {"premiere": str(premiere(folder, doc, items)), "hyperframes": str(hyperframes(folder, doc, items)),
            "placeholders": sum(1 for it in items if it["clip"]), "seconds": round(sum(it["secs"] for it in items), 1)}


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1]), indent=1))
