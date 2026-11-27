#!/usr/bin/env python3
"""
assemble.py — the cut, as a file Premiere opens.

    python3 machine/assemble.py <run>

Reads the storyboard and writes a Final Cut Pro 7 XML (`xmeml`) that Premiere
imports as a real sequence: every clip on V1 in scene order, Nina's voice take
under each talking beat on A1, and a marker on every beat carrying its line.

Not `.prproj` — that is a compressed proprietary document with no published
schema, and a hand-written one opens empty. xmeml is documented and is Adobe's
own interchange path.

**Picture and voice are separate tracks on purpose.** The clips are generated
silent and the voice is laid under them, which is how an editor works and what
makes a headline swap free: the picture never has to be regenerated to change
what is said over it. Lip sync is a later pass on the shots that survive
review, not a tax paid on all thirty-three.
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
from pathlib import Path
from xml.sax.saxutils import escape

FPS = 30


def probe(p: Path) -> dict:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=width,height,r_frame_rate", "-show_entries",
             "format=duration", "-of", "json", str(p)],
            capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout)
        st = next((s for s in d.get("streams", []) if s.get("width")), {})
        num, _, den = (st.get("r_frame_rate") or "30/1").partition("/")
        return {"w": int(st.get("width") or 1080), "h": int(st.get("height") or 1920),
                "fps": float(num) / float(den or 1),
                "sec": float((d.get("format") or {}).get("duration") or 0)}
    except Exception:
        return {"w": 1080, "h": 1920, "fps": 30.0, "sec": 0.0}


def url(p: Path) -> str:
    return "file://localhost" + urllib.parse.quote(str(p.resolve()))


def rate(tb=FPS):
    return f"<rate><timebase>{tb}</timebase><ntsc>FALSE</ntsc></rate>"


def chars(w, h, tb=FPS):
    return (f"<samplecharacteristics>{rate(tb)}<width>{w}</width>"
            f"<height>{h}</height><anamorphic>FALSE</anamorphic>"
            f"<pixelaspectratio>square</pixelaspectratio>"
            f"<fielddominance>none</fielddominance></samplecharacteristics>")


def build(run: Path) -> Path:
    b = json.loads((run / "storyboard.json").read_text())
    vid, aud, markers = [], [], []
    at = 0

    for s in b["scenes"]:
        # Owned footage wins. It is real, it is free, and it cannot drift from
        # the product — so a scene the library could carry is cut, not
        # generated, and the generated take stays on the shelf underneath it.
        owned = run / "owned" / f"scene-{s['n']:02d}.mp4"
        gen = run / "clips" / f"scene-{s['n']:02d}.mp4"
        clip = owned if owned.exists() and owned.stat().st_size > 20000 else gen
        if not clip.exists():
            continue
        s["used"] = "owned" if clip is owned else "generated"
        info = probe(clip)
        n = max(1, round(info["sec"] * FPS))

        # A talking beat is only as long as the line in it. The clip was
        # generated to the brief's timing, the voice take came back shorter,
        # and the difference is Nina standing there saying nothing. Trim the
        # picture to the take plus a short handle so the cut lands on the end
        # of the sentence rather than after it.
        vo_path = run / "voice" / f"scene-{s['n']:02d}.mp3"
        if s["type"] == "A" and s.get("used") != "owned" and vo_path.exists():
            vsec = probe(vo_path)["sec"]
            if vsec > 0:
                want = max(1, round((vsec + 0.35) * FPS))
                n = min(n, want)
        cid, fid = f"v{s['n']}", f"f{s['n']}"
        vid.append(
            f'<clipitem id="{cid}"><name>{escape(clip.name)}</name>'
            f'<enabled>TRUE</enabled><duration>{n}</duration>{rate()}'
            f'<start>{at}</start><end>{at+n}</end><in>0</in><out>{n}</out>'
            f'<file id="{fid}"><name>{escape(clip.name)}</name>'
            f'<pathurl>{escape(url(clip))}</pathurl>{rate()}'
            f'<duration>{n}</duration><media><video>{chars(info["w"],info["h"])}'
            f'</video></media></file>'
            f'<sourcetrack><mediatype>video</mediatype><trackindex>1</trackindex>'
            f'</sourcetrack></clipitem>')

        # the voice take sits under its own beat, its own length
        vo = run / "voice" / f"scene-{s['n']:02d}.mp3"
        if vo.exists() and s.get("used") != "owned":
            vn = max(1, round(probe(vo)["sec"] * FPS))
            aid, afid = f"a{s['n']}", f"af{s['n']}"
            aud.append(
                f'<clipitem id="{aid}"><name>{escape(vo.name)}</name>'
                f'<enabled>TRUE</enabled><duration>{vn}</duration>{rate()}'
                f'<start>{at}</start><end>{at+vn}</end><in>0</in><out>{vn}</out>'
                f'<file id="{afid}"><name>{escape(vo.name)}</name>'
                f'<pathurl>{escape(url(vo))}</pathurl>{rate()}'
                f'<duration>{vn}</duration><media><audio>'
                f'<channelcount>1</channelcount></audio></media></file>'
                f'<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex>'
                f'</sourcetrack></clipitem>')

        label = f"{s['n']:02d} {s['type']} · " + (
            (s.get("say") or s.get("happens") or s.get("product") or "")[:70])
        markers.append(f'<marker><name>{escape(label)}</name>'
                       f'<comment>{escape((s.get("delivery") or "")[:120])}</comment>'
                       f'<in>{at}</in><out>-1</out></marker>')
        at += n

    name = escape(b.get("title") or run.name)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n'
           '<xmeml version="4">\n'
           f'<sequence id="{escape(run.name)}"><name>{name}</name>'
           f'<duration>{at}</duration>{rate()}'
           f'<timecode>{rate()}<string>00:00:00:00</string><frame>0</frame>'
           f'<displayformat>NDF</displayformat></timecode><media>'
           f'<video><format>{chars(1080,1920)}</format>'
           f'<track>{"".join(vid)}</track></video>'
           '<audio><format><samplecharacteristics><depth>16</depth>'
           '<samplerate>48000</samplerate></samplecharacteristics></format>'
           f'<track>{"".join(aud)}</track></audio></media>'
           f'{"".join(markers)}</sequence>\n</xmeml>\n')
    out = run / f"{run.name}.xml"
    out.write_text(xml)
    return out


if __name__ == "__main__":
    import sys
    r = Path(sys.argv[1]).expanduser().resolve()
    p = build(r)
    print(f"{p}  ({p.stat().st_size/1024:.0f} KB)")
