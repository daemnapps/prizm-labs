#!/usr/bin/env python3
"""compose.py — turns a green cut sheet into a HyperFrames project: one web
page with timing marks that renders the same video every time.

    compose(sheet, root, project_dir, captions=True) -> Path to index.html

It executes the sheet and decides nothing. Picture order is the sheet's order;
b-roll paints over a-roll; text is a layer, never generated. Every move eases,
entrances move more than one property, exits are faster than entrances
(the editing rules in CLAUDE.md).

HyperFrames contract used here (read from its docs 2026-09-20):
  root  data-composition-id / data-start / data-width / data-height / data-duration
  clip  class="clip" id data-start data-duration data-track-index
  trim  data-media-start   (NOT data-playback-start — that one desyncs audio)
  vol   data-volume 0..3.98 (1 = 0 dB)
  one paused GSAP timeline registered in window.__timelines[<id>]
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"


def db_to_volume(db: float) -> float:
    return round(min(3.98, 10 ** (db / 20.0)), 3)


def look_of(sheet: dict) -> dict:
    look = (sheet.get("captions") or {}).get("look")
    if isinstance(look, dict):
        return look
    for r in json.loads((TOOL / "looks/bank.json").read_text())["looks"]:
        if r["id"] == look:
            return r
    raise SystemExit(f"caption look `{look}` is not in looks/bank.json")


def caption_lines(words: list[dict], max_words: int, max_gap: float = 0.35) -> list[list[dict]]:
    """Group timed words into on-screen lines: break on a pause, on sentence
    punctuation, or when the line is full."""
    lines, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap or cur[-1]["text"].rstrip()[-1:] in ".!?"):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def _asset(src: Path, assets: Path) -> str:
    assets.mkdir(parents=True, exist_ok=True)
    dest = assets / src.name
    if not dest.exists() or dest.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dest)
    return f"assets/{dest.name}"


def compose(sheet: dict, root: Path, project: Path, captions: bool = True) -> Path:
    meta = sheet["meta"]
    W, H, fps = meta["width"], meta["height"], meta["fps"]
    cid = "edit"
    end = max(c["start"] + c["duration"] for c in sheet["picture"])
    assets = project / "assets"
    body, tl, css = [], [], []

    # picture — a-roll first, b-roll above it
    for z, roll in ((1, "a"), (2, "b")):
        for c in (x for x in sheet["picture"] if x["roll"] == roll):
            src = _asset(root / c["src"], assets)
            common = f'id="{c["id"]}" class="clip pic" data-start="{c["start"]}" data-duration="{c["duration"]}" data-track-index="{z}" style="z-index:{z}"'
            if c.get("still"):
                body.append(f'<img {common} src="{src}" alt="">')
                drift = 1.06 if (len(tl) % 2 == 0) else 1.0
                tl.append(f'tl.fromTo("#{c["id"]}",{{scale:{2.06 - drift:.2f}}},{{scale:{drift},duration:{c["duration"]},ease:"sine.inOut"}},{c["start"]});')
            else:
                vol = c.get("volume_db")
                audio = f' data-has-audio="true" data-volume="{db_to_volume(vol)}"' if vol is not None else " muted"
                if c.get("punch", 1.0) != 1.0:
                    css.append(f'#{c["id"]}{{transform:scale({c["punch"]});transform-origin:50% 32%}}')
                body.append(f'<video {common} src="{src}" data-media-start="{c.get("source_start", 0)}" playsinline{audio}></video>')

    # sound
    track = 10
    for key in ("voice", "music"):
        a = sheet.get(key)
        if a:
            src = _asset(root / a["src"], assets)
            body.append(f'<audio id="{key}" data-start="{a.get("start", 0)}" data-track-index="{track}" data-volume="{db_to_volume(a.get("volume_db", 0))}" src="{src}"></audio>')
            track += 1
    for v in sheet.get("voice_cuts") or []:
        src = _asset(root / v["src"], assets)
        body.append(f'<audio id="{v["id"]}" data-start="{v["start"]}" data-duration="{v["duration"]}" data-media-start="{v["source_start"]}" data-track-index="{track}" data-volume="{db_to_volume(v.get("volume_db", 0))}" src="{src}"></audio>')
    track += 1
    lead = ((sheet.get("controls") or {}).get("sound") or {}).get("sfx_lead_frames", 2) / fps
    for s in sheet.get("sfx") or []:
        src = _asset(root / s["src"], assets)
        body.append(f'<audio id="{s["id"]}" data-start="{max(0, round(s["at"] - lead, 3))}" data-track-index="{track}" data-volume="{db_to_volume(s.get("volume_db", -8))}" src="{src}"></audio>')
        track += 1

    # captions — a setting, never a re-edit
    caps = sheet.get("captions") or {}
    if captions and caps.get("words"):
        L = look_of(sheet)
        fixes = {f["from"]: f["to"] for f in caps.get("fixes") or []}
        scale = W / 1080
        size = round(L["size_px"] * scale)
        stroke = round(L.get("stroke_px", 0) * scale)
        css.append(f""".cap{{position:absolute;left:6%;right:6%;top:{L['y_pct']}%;transform:translateY(-50%);z-index:20;text-align:center;
font-family:{L['font']};font-weight:{L['weight']};font-size:{size}px;line-height:1.08;color:{L['color']};
text-transform:{'uppercase' if L.get('case') == 'upper' else 'none'};text-shadow:{L.get('shadow', 'none')};
{f'-webkit-text-stroke:{stroke}px {L["stroke"]};paint-order:stroke fill;' if stroke else ''}}}
.cap span{{display:inline-block;margin:0 .22em}}
.cap .plate{{display:inline-block;padding:.18em .5em;border-radius:.2em;background:{L.get('plate', 'transparent')}}}""")
        lines = caption_lines(caps["words"], L["max_words"])
        for i, line in enumerate(lines):
            s, e = line[0]["start"], line[-1]["end"]
            nxt = e + 0.12
            if i + 1 < len(lines):  # never two lines on screen at once
                nxt = max(e, min(nxt, lines[i + 1][0]["start"] - 0.07))
            lid = f"cap{i}"
            spans = " ".join(f'<span id="{lid}w{j}">{html.escape(fixes.get(w["text"], w["text"]))}</span>' for j, w in enumerate(line))
            body.append(f'<div id="{lid}" class="clip cap" data-start="{round(max(0, s - 0.06), 3)}" data-duration="{round(nxt - max(0, s - 0.06), 3)}" data-track-index="20"><div class="plate">{spans}</div></div>')
            y = 26 if L.get("entrance") == "rise" else 0
            sc = 0.86 if L.get("entrance") == "pop" else 1
            tl.append(f'tl.fromTo("#{lid}",{{opacity:0,y:{y},scale:{sc}}},{{opacity:1,y:0,scale:1,duration:0.16,ease:"back.out(1.6)"}},{round(max(0, s - 0.06), 3)});')
            tl.append(f'tl.to("#{lid}",{{opacity:0,duration:0.08,ease:"power2.in"}},{round(nxt - 0.08, 3)});')
            if L["highlight"].lower() != L["color"].lower():
                for j, w in enumerate(line):
                    tl.append(f'tl.to("#{lid}w{j}",{{color:"{L["highlight"]}",scale:1.08,duration:0.08,ease:"power2.out"}},{w["start"]});')
                    off = min(w["end"], line[j + 1]["start"]) if j + 1 < len(line) else w["end"]
                    tl.append(f'tl.to("#{lid}w{j}",{{color:"{L["color"]}",scale:1,duration:0.08,ease:"power2.in"}},{round(off, 3)});')

    # overlays — hooks, labels, the end card
    for o in sheet.get("overlays") or []:
        oid = o["id"]
        css.append(f'#{oid}{{position:absolute;left:8%;right:8%;top:{o.get("y_pct", 20)}%;z-index:30;text-align:center;font:900 {round(64 * W / 1080)}px/1.1 "Arial Black","Helvetica Neue",Arial,sans-serif;color:#111;}}#{oid} b{{background:#fff;padding:.15em .4em;border-radius:.18em;box-decoration-break:clone;-webkit-box-decoration-break:clone}}')
        body.append(f'<div id="{oid}" class="clip" data-start="{o["start"]}" data-duration="{o["duration"]}" data-track-index="30"><b>{html.escape(o.get("text", ""))}</b></div>')
        if o["start"] > 0.05:  # a hook that opens the video is simply THERE on frame one — no fade, no slide
            tl.append(f'tl.fromTo("#{oid}",{{opacity:0,y:-30,scale:.94}},{{opacity:1,y:0,scale:1,duration:0.3,ease:"power3.out"}},{o["start"]});')
        tl.append(f'tl.to("#{oid}",{{opacity:0,y:-16,duration:0.15,ease:"power2.in"}},{round(o["start"] + o["duration"] - 0.15, 3)});')

    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><script src="{GSAP}"></script>
<style>html,body{{margin:0;background:#000}}#stage{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#000}}
.pic{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
{''.join(css)}</style></head><body>
<div id="stage" data-composition-id="{cid}" data-start="0" data-width="{W}" data-height="{H}" data-fps="{fps}" data-duration="{round(end, 3)}">
{chr(10).join(body)}
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
window.__timelines = window.__timelines || {{}};
window.__timelines["{cid}"] = tl;
</script>
</div></body></html>
"""
    project.mkdir(parents=True, exist_ok=True)
    (project / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}, indent=1))
    (project / "meta.json").write_text(json.dumps({"id": meta["label"], "name": meta["label"]}, indent=1))
    out = project / "index.html"
    out.write_text(page)
    return out
