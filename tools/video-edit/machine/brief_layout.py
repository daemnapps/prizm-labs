#!/usr/bin/env python3
"""brief_layout.py — lay a brief onto a timeline: every scene a slot at its time, every word on screen at its time,
the music and the sound effects where the brief puts them. Every time says where it came from.

    python3 machine/brief_layout.py <brand> <brief folder> [--open]     # writes runs/video-edit/<brand>/<brief>/layout/

The clock, strongest first (a weaker source never moves a stronger one):
  1. a scene's own cut time in the brief      `lands_on: "the cut at 0:27"`
  2. the song's sections                      `song.sections[{scene, seconds}]` — a section starts at its scene
  3. the scene's share of the span it sits in  by its `beats` (one beat of the scene = one share; none = one share)
Every boundary is snapped to the song's beat when the brief gives a bpm. A scene with clips laid later keeps its slot.

Out: layout.json (each scene: start, end, source of its time), cutsheet.json (the slots, the words, the music and
sound as the cut sheet carries them), and with --open a HyperFrames project opened in Studio. A slot is a labelled
frame until its clip is laid; music and sound effects not made yet are stand-ins (a beat click, a noise sweep).
No brand is named in this file.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VP = REPO / "components" / "video-production" / "machine"
sys.path.insert(0, str(VP))
import scenes as SCN  # noqa: E402

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
AT = re.compile(r"\bat\s+(\d+):(\d{2}(?:\.\d+)?)")
SRC = re.compile(r"(\d+):(\d{2}(?:\.\d+)?)\s*-\s*(\d+):(\d{2}(?:\.\d+)?)")
SPLIT = re.compile(r"^(.*?)\s+for the first\s+([\d.]+)\s*s,\s*then\s+(.*)$", re.I | re.S)

# The caption presets (the owner, 2026-11-06: a few, mostly TikTok and Instagram style), each a text look in
# looks/edit-looks.json. One style runs through the whole piece: the one the swipe's caption read gives its first span
# (the hook). Later spans that name another style are noted in layout.json, not applied.
PRESETS = [
    ("headline-white-box", "Instagram text box: black words on a white box", r"white (?:box|background|card)|on (?:a )?white"),
    ("native-pop", "dark box: white words on a dark box", r"(?:black|dark) (?:box|plate|background)"),
    ("headline-plain", "TikTok text: white words, black outline, no box", r"outline|black edge|stroke|white text|white words"),
]
# The brief's lanes, in its own roll codes (roll_sheet: A, B-over/B-vo/B-silent, G, C, E), each its own row in Studio,
# always all of them, so every brief lines up the same way; an empty lane says so. (lane, row name, Studio track)
LANES = [("A", "A-roll", 1), ("B", "B-roll", 2), ("G", "Greenscreen", 3), ("C", "Cards", 4), ("E", "End card", 5)]
TRACK = {"captions": 6, "song": 7, "voice": 8}
BY_KIND = {"talking": "A", "aroll": "A", "broll": "B", "greenscreen": "G", "card": "C", "endcard": "E"}
KIND = {"broll": "B-roll", "card": "Card", "endcard": "End card", "greenscreen": "Greenscreen", "talking": "To camera", "aroll": "A-roll"}
PLACE = [(r"\blower\b|\bbottom\b", 62, "lower"), (r"\btop\b|upper", 12, "top"), (r"centr|center|middle", 42, "centre")]   # "lower centre" is lower


def caption_spans(doc: dict) -> list[dict]:
    """The brief's caption read (edit.captions), split into spans: which scenes, which preset, where on the frame."""
    ids = [s["id"] for s in doc["scenes"] if isinstance(s, dict)]
    kinds = {s["id"]: s.get("kind") for s in doc["scenes"] if isinstance(s, dict)}
    read = str((doc.get("edit") or {}).get("captions") or "")
    spans = []
    for part in [x.strip() for x in read.split(";") if x.strip()]:
        lo, hi = 0, len(ids) - 1
        m = re.search(r"through (S\w+)", part)
        if m and m.group(1) in ids:
            hi = ids.index(m.group(1))
        m = re.search(r"from (S\w+)", part)
        if m and m.group(1) in ids:
            lo = ids.index(m.group(1))
        if re.search(r"end ?card", part, re.I):
            scope = [i for i in ids if kinds[i] == "endcard"]
        else:
            scope = ids[lo:hi + 1]
        look = next(((i, n) for i, n, rx in PRESETS if re.search(rx, part, re.I)), None)
        where = next(((y, n) for rx, y, n in PLACE if re.search(rx, part, re.I)), (62, "lower"))
        if look:
            spans.append({"scenes": scope, "look": look[0], "name": look[1], "y_pct": where[0], "where": where[1], "read": part})
    return spans


def caption_style(doc: dict) -> tuple[dict, list[str]]:
    """The one caption style for the whole piece, and a note for each later read that named another style."""
    spans = caption_spans(doc)
    if not spans:
        i, n, _ = next(x for x in PRESETS if x[0] == "headline-plain")
        return {"look": i, "name": n, "y_pct": 62, "where": "lower", "read": "(the brief names no caption style)"}, []
    one = {k: spans[0][k] for k in ("look", "name", "y_pct", "where", "read")}
    notes = [f"caption read \"{sp['read']}\" names {sp['name']}, {sp['where']}; the piece keeps one style: {one['name']}, {one['where']}"
             for sp in spans[1:] if (sp["look"], sp["where"]) != (one["look"], one["where"])]
    return one, notes


def clock(doc: dict) -> tuple[list[dict], float, list[str]]:
    """Every scene's start and end, and where each came from."""
    sc = [s for s in doc["scenes"] if isinstance(s, dict)]
    ids = [s["id"] for s in sc]
    bpm = float((doc.get("song") or {}).get("bpm") or (doc.get("music") or {}).get("tempo_bpm") or 0)
    beat = 60.0 / bpm if bpm else 0.0
    notes = []
    anchor: dict[int, tuple[float, str]] = {}
    t = 0.0
    secs = (doc.get("song") or {}).get("sections") or []
    for sec in secs:
        if sec.get("scene") in ids:
            anchor.setdefault(ids.index(sec["scene"]), (round(t, 3), f"song {sec.get('name')} starts here"))
        t += float(sec.get("seconds") or 0)
    end = t if secs else None
    for i, s in enumerate(sc):
        m = AT.search(str(s.get("lands_on") or ""))
        if m:
            at = int(m.group(1)) * 60 + float(m.group(2))
            if i in anchor and abs(anchor[i][0] - at) > 0.05:
                notes.append(f"{s['id']}: the brief's cut at {at:g}s wins over the song's {anchor[i][0]:g}s")
            anchor[i] = (at, f"brief: cut at {m.group(0)[3:]}")
    anchor.setdefault(0, (0.0, "the opening"))
    if end is None:
        end = max(a for a, _ in anchor.values()) + 3.0
        notes.append("no song length in the brief: the last span is 3 s a scene")
    last = len(sc) - 1                     # an end card the brief gives no cut time keeps the swipe's length, from the end
    m = SRC.search(str(sc[last].get("source") or ""))
    if sc[last].get("kind") == "endcard" and last not in anchor and m and last > 0:
        t0 = anchor[max(k for k in anchor if k < last)][0]
        want = float(m.group(3)) * 60 + float(m.group(4)) - float(m.group(1)) * 60 - float(m.group(2))
        at = end - want
        if beat:
            at = t0 + round((at - t0) / beat) * beat
        if t0 < at < end:
            anchor[last] = (round(at, 3), f"swipe: its end card runs {want:g}s, held to the end")
    keys = sorted(anchor) + [len(sc)]
    out = []
    for k0, k1 in zip(keys, keys[1:]):
        t0 = anchor[k0][0]
        t1 = anchor[k1][0] if k1 < len(sc) else end
        group = list(range(k0, k1))
        w = [max(1, len(sc[i].get("beats") or [])) for i in group]
        acc = t0
        for j, i in enumerate(group):
            a = acc
            b = t1 if j == len(group) - 1 else acc + (t1 - t0) * w[j] / sum(w)
            if beat and j < len(group) - 1:
                b = t0 + round((b - t0) / beat) * beat
            src = anchor[k0][1] if j == 0 else f"share of {sc[k0]['id']}–{sc[group[-1]]['id']} by beats ({w[j]} of {sum(w)})"
            out.append({"scene": sc[i]["id"], "start": round(a, 3), "end": round(b, 3), "from": src})
            acc = b
    return out, round(end, 3), notes


def words(doc: dict, times: list[dict]) -> list[dict]:
    """Every word on screen at its time: a scene's on_screen (split where the brief says 'for the first N s, then'),
    a card's lines for the card's whole slot."""
    at = {r["scene"]: r for r in times}
    one, _ = caption_style(doc)
    out = []
    for s in doc["scenes"]:
        r = at.get(s.get("id"))
        if not r:
            continue
        text = str(s.get("on_screen") or "").strip().replace(" / ", "\n")
        lines = [str(x) for x in s.get("lines") or [] if str(x).strip()]
        ec = s.get("endcard") if isinstance(s.get("endcard"), dict) else {}
        lines += [str(x) for x in [*(ec.get("offer_lines") or []), ec.get("cta")] if str(x or "").strip()]
        if text:
            m = SPLIT.match(text)
            if m:
                cut = min(r["end"], r["start"] + float(m.group(2)))
                out.append({"scene": s["id"], "text": m.group(1), "start": r["start"], "end": cut, "kind": "on_screen"})
                out.append({"scene": s["id"], "text": m.group(3), "start": cut, "end": r["end"], "kind": "on_screen"})
            else:
                out.append({"scene": s["id"], "text": text, "start": r["start"], "end": r["end"], "kind": "on_screen"})
        if lines:                          # a card's lines are one block, one line each, so they never overlap
            out.append({"scene": s["id"], "text": "\n".join(lines), "start": r["start"], "end": r["end"], "kind": "card"})
    for w in out:                          # one style all the way through, card lines included
        w.update(look=one["look"], look_name=one["name"], y_pct=one["y_pct"], where=one["where"])
    return out


def effects(doc: dict, times: list[dict]) -> list[dict]:
    at = {r["scene"]: r for r in times}
    out = []
    for e in (doc.get("edit") or {}).get("effects") or []:
        m = re.match(r"\s*(S[\w]+)", str(e.get("lands_on") or ""))
        r = at.get(m.group(1)) if m else None
        if r:
            last = "last frame" in str(e.get("lands_on"))
            out.append({"sound": e.get("sound"), "at": round(r["end"] - 0.6 if last else max(0.0, r["start"] - 2 / 30), 3),
                        "for": e.get("lands_on")})
    return out


def _ff(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, check=True)


def _esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def slot_frame(out: Path, s: dict, r: dict) -> Path:
    """A labelled frame for a slot with no clip yet: the scene, its kind and what it shows."""
    f = out / "slots" / f"{s['id']}.png"
    f.parent.mkdir(parents=True, exist_ok=True)
    what = str(s.get("happens") or s.get("plate") or s.get("kind") or "")
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        im = Image.new("RGB", (1080, 1920), (32, 37, 31))
        dr = ImageDraw.Draw(im)
        big, mid, small = (ImageFont.truetype(FONT, n) for n in (120, 44, 36))
        dr.text((64, 110), s["id"], font=big, fill=(125, 134, 123))
        dr.text((68, 260), f"{str(s.get('kind') or '').upper()} · {r['end'] - r['start']:.1f}s", font=mid, fill=(125, 134, 123))
        dr.multiline_text((68, 1560), "\n".join(textwrap.wrap(what, 44)[:4]), font=small, fill=(110, 118, 108), spacing=10)
        im.save(f)
    except (ImportError, OSError):   # no Pillow or font: a plain frame, the scene still named on the sheet
        _ff(["-f", "lavfi", "-i", "color=c=0x20251f:s=1080x1920", "-frames:v", "1", str(f)])
    return f


def stand_ins(out: Path, end: float, bpm: float, drop: float | None) -> tuple[Path, Path]:
    """A beat click for the song (a louder click on each bar, a burst on the drop) and a noise sweep for a whoosh."""
    beat = 60.0 / (bpm or 120)
    click = out / "audio" / "song-stand-in.wav"
    click.parent.mkdir(parents=True, exist_ok=True)
    expr = (f"0.25*sin(2*PI*880*t)*lt(mod(t,{beat:.5f}),0.03)"
            f"+0.35*sin(2*PI*1320*t)*lt(mod(t,{4 * beat:.5f}),0.05)")
    if drop is not None:
        expr += f"+0.5*sin(2*PI*220*t)*between(t,{drop:.3f},{drop + 0.4:.3f})"
    _ff(["-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={end:.3f}", "-ac", "2", str(click)])
    whoosh = out / "audio" / "whoosh-stand-in.wav"
    _ff(["-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink:a=0.5", "-af", "afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.3",
         "-ac", "2", "-ar", "48000", str(whoosh)])
    return click, whoosh


def shows(s: dict) -> str:
    """What a slot shows, in the brief's words: the action, else a card's words, else the end card's plate."""
    ec = s.get("endcard") if isinstance(s.get("endcard"), dict) else {}
    return str(s.get("happens") or " / ".join(str(x) for x in s.get("lines") or []) or ec.get("plate") or s.get("section") or "")


def lanes(doc: dict) -> dict:
    """Each scene's lane: the brief's roll sheet first (A, B-*, G, C, E), then the scene's kind."""
    rs = {r.get("scene"): str(r.get("roll") or "") for r in doc.get("roll_sheet") or [] if isinstance(r, dict) and r.get("scene")}
    for r in doc.get("roll_sheet") or []:           # "re-made as moving B-roll S10": that scene moves, so it is B-roll
        m = re.search(r"re-?made as moving B-roll (S\w+)", str(r.get("dropped") or "") if isinstance(r, dict) else "")
        if m:
            rs[m.group(1)] = "B"
    out = {}
    for s in doc["scenes"]:
        if not isinstance(s, dict):
            continue
        code = rs.get(s["id"], "")[:1].upper()
        out[s["id"]] = code if code in {c for c, _, _ in LANES} else BY_KIND.get(s.get("kind"), "A" if s.get("voice") else "B")
    return out


def sheet(brand: str, brief: str, doc: dict, times, end, said, fx, out: Path) -> dict:
    by = {s["id"]: s for s in doc["scenes"] if isinstance(s, dict)}
    bpm = float((doc.get("song") or {}).get("bpm") or 0)
    drop = next((fx_["at"] + 2 / 30 for fx_ in fx if "drop" in str(fx_.get("for"))), None)
    click, whoosh = stand_ins(out, end, bpm, drop)
    lane = lanes(doc)
    row_of = {c: (n, t) for c, n, t in LANES}
    picture = [{"id": r["scene"], "roll": "a", "kind": None, "src": str(slot_frame(out, by[r["scene"]], r)),
                "start": r["start"], "duration": round(r["end"] - r["start"], 3), "source_start": 0,
                "scene": r["scene"], "still": True, "volume_db": None, "section": by[r["scene"]].get("section"),
                "why": f"{r['scene']}: slot, timed from {r['from']}", "drift": False,
                "track": row_of[lane[r["scene"]]][1], "row": row_of[lane[r["scene"]]][0],
                "label": f"{r['scene']} · {shows(by[r['scene']])}".strip(" ·")}
               for r in times]
    markers = []
    for code, name, t in LANES:                       # an empty lane is still on the timeline, saying it is empty
        if code not in lane.values():
            markers.append({"id": f"empty-{code}", "track": t, "row": name, "start": 0, "duration": end, "label": "none in this brief"})
    at = {r["scene"]: r for r in times}
    spoken = [(s_["id"], str(s_.get("voice")).strip()) for s_ in doc["scenes"] if isinstance(s_, dict) and str(s_.get("voice") or "").strip() and s_["id"] in at]
    for sc, v in spoken:
        markers.append({"id": f"voice-{sc}", "track": TRACK["voice"], "row": "Voice", "start": at[sc]["start"],
                        "duration": round(at[sc]["end"] - at[sc]["start"], 3), "label": f"{sc} {v}"})
    if not spoken:
        markers.append({"id": "voice-none", "track": TRACK["voice"], "row": "Voice", "start": 0, "duration": end,
                        "label": "none in this brief (nothing is spoken)"})
    secs = [x for x in (doc.get("song") or {}).get("sections") or [] if x.get("scene") in at]
    for i, x in enumerate(secs):
        s0 = at[x["scene"]]["start"]
        s1 = at[secs[i + 1]["scene"]]["start"] if i + 1 < len(secs) else end
        markers.append({"id": f"song-{i}", "track": TRACK["song"], "row": "Song", "start": s0, "duration": round(s1 - s0, 3),
                        "label": f"{x.get('name', 'section')} · {' / '.join(x.get('lines') or []) or 'no words'}"})
    sys.path.insert(0, str(HERE))
    import looks as LK
    overlays = []
    for i, w in enumerate(said):
        o = {"id": f"{w['scene']}-w{i}", "kind": "label", "text": w["text"], "label": f"{w['scene']} · {w['text']}", "start": w["start"],
             "track": TRACK["captions"], "row": "Captions",
             "duration": round(w["end"] - w["start"], 3), "entrance": "cut"}
        if w.get("look"):
            o.update(text_look=LK.text_look("headline", w["look"]), look_id=w["look"], y_pct=w["y_pct"])
        else:
            o["zone"] = "center-block"
        overlays.append(o)
    return {"meta": {"brand": brand, "label": brief, "format": "brief-layout", "style_id": None, "width": 1080,
                     "height": 1920, "fps": 30, "made_by": "brief layout",
                     "brief": f"runs/video-writing/{brand}/{brief}/deliverable/5-brief.md"},
            "controls": {"transition": {"value": "cut"}, "captions": {"value": "off"}},
            "voice": None, "voice_cuts": [],
            "music": {"src": str(click), "start": 0, "volume_db": -6, "stand_in": True, "label": "Music · beat stand-in", "why": "the song's slot: a beat click until the song is made"},
            "sfx": [{"id": f"fx{i}", "src": str(whoosh), "at": f["at"], "volume_db": -6, "for": f["for"], "label": f"Whoosh · {f['for']}"} for i, f in enumerate(fx)],
            "picture": picture, "captions": {"look": None, "words": []}, "overlays": overlays, "markers": markers}


def layout(brand: str, brief: str) -> tuple[dict, Path]:
    d = REPO / "runs" / "video-writing" / brand / brief / "deliverable"
    doc, why = SCN.json_block((d / "5-brief.md").read_text())
    if not isinstance(doc, dict) or not doc.get("scenes"):
        raise SystemExit(f"no scene block in the brief ({why})")
    times, end, notes = clock(doc)
    said, fx = words(doc, times), effects(doc, times)
    out = REPO / "runs" / "video-edit" / brand / brief / "layout"
    out.mkdir(parents=True, exist_ok=True)
    style, style_notes = caption_style(doc)
    lay = {"brief": brief, "length": end, "scenes": times, "caption_style": style, "words": said, "effects": fx,
           "notes": notes + style_notes}
    (out / "layout.json").write_text(json.dumps(lay, indent=1, ensure_ascii=False))
    sh = sheet(brand, brief, doc, times, end, said, fx, out)
    (out / "cutsheet.json").write_text(json.dumps(sh, indent=1, ensure_ascii=False))
    return lay, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("brand"); ap.add_argument("brief"); ap.add_argument("--open", action="store_true")
    a = ap.parse_args(argv)
    lay, out = layout(a.brand, a.brief)
    for r in lay["scenes"]:
        print(f"{r['scene']:5} {r['start']:6.2f}–{r['end']:6.2f}s  {r['from']}")
    st = lay["caption_style"]
    print(f"captions, whole piece: {st['look']} ({st['name']}), {st['where']}  ← \"{st['read']}\"")
    for n in lay["notes"]:
        print("note ", n)
    if a.open:
        sys.path.insert(0, str(HERE))
        import compose as C
        project = out / "studio"
        C.compose(json.loads((out / "cutsheet.json").read_text()), out, project, captions=False)
        print(f"project: {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
