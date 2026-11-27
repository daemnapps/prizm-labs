#!/usr/bin/env python3
"""lane_check.py — check that every element of a brief's Studio edit sits on its own lane (lanes.json).

    python3 machine/lane_check.py <Studio project folder> [--sheet cutsheet.json] [--json]

Reads the project's index.html: every timed element with a data-track-index. Each element's kind comes from what it
is (picture, text, marker, sound); a picture's kind comes from the cut sheet the project was built from, which says
the lane its scene was laid on (found beside the project: ../cutsheet.json or ../studio-build/cutsheet.json, or
--sheet). The lane it sits on is its track. Prints every element on a lane it does not belong to, in plain words:
scene, what it is, the lane it sits on, the lane it belongs on. A clean project prints that it is clean.
Exit 0 when clean, 1 when anything is on the wrong lane or off the lanes. No brand is named in this file.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "lanes.json"
SCENE = re.compile(r"^(S\d+[a-z]?)\b")
SECTION = re.compile(r"^(intro|verse|pre-?chorus|chorus|bridge|hook|drop|outro|section|break)\b", re.I)
OVERLAY = {"lt", "ann", "ui", "disc", "icn", "lab"}
ROW_KIND = {"A-roll": "aroll_clip", "B-roll": "broll_clip", "Greenscreen": "greenscreen_clip",
            "Cards": "card_picture", "End card": "endcard_picture"}


class _Timed(HTMLParser):
    """Every element with a data-track-index, with its tag, attributes and the text inside it."""

    VOID = {"img", "source", "br", "hr", "input", "meta", "link"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found: list[dict] = []
        self.stack: list[tuple[str, dict | None]] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        el = None
        if "data-track-index" in a:
            el = {"tag": tag, "attrs": a, "text": ""}
            self.found.append(el)
        if tag not in self.VOID:
            self.stack.append((tag, el))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        for _, el in self.stack:
            if el is not None:
                el["text"] += data


def contract(path: Path = CONTRACT) -> dict:
    c = json.loads(path.read_text())
    c["row_names"] = {l["lane"] for l in c["lanes"]} | {"Picture", "Spoken captions", "Icons"}
    return c


def lane_of(track: int, c: dict) -> str | None:
    for l in c["lanes"]:
        if track in l.get("tracks", []) or (l.get("tracks_from") is not None and track >= l["tracks_from"]):
            return l["lane"]
    return None


def _strip_row(label: str, c: dict) -> str:
    """compose prefixes the first clip on a row with the row's name ("Cards · S9 · …"); drop it."""
    head, sep, rest = label.partition(" · ")
    return rest if sep and head in c["row_names"] else label


def find_sheet(project: Path) -> Path | None:
    for p in (project.parent / "cutsheet.json", project.parent / "studio-build" / "cutsheet.json"):
        if p.is_file():
            return p
    return None


def sheet_rows(sheet: Path | None) -> dict:
    """Each scene's lane as its cut sheet laid it (the brief's roll), e.g. {"S4": "Cards"}."""
    if not sheet:
        return {}
    doc = json.loads(sheet.read_text())
    return {p.get("scene") or p["id"]: p["row"] for p in doc.get("picture") or [] if p.get("row")}


def kind_of(el: dict, label: str, scene: str | None, rows: dict) -> str:
    tag, a = el["tag"], el["attrs"]
    cls = set(a.get("class", "").split())
    eid = a.get("id", "")
    low = f"{eid} {label} {Path(a.get('src', '')).name}".lower()
    if tag == "audio":
        if a.get("data-audio-group") == "sfx":
            return "sfx_audio"
        if "room" in low:
            return "room_tone"
        if eid == "music" or label.lower().startswith("music") or re.search(r"music|song", low):
            return "music_audio"
        if "voice" in low:
            return "voice_audio"
        return "unknown"
    if tag in ("video", "img"):
        if "gs" in cls:
            return "greenscreen_clip"
        return ROW_KIND.get(rows.get(scene or ""), "picture")
    if "mark" in cls:
        if "none in this brief" in label:
            return "empty_marker"
        if eid.startswith("song-") or SECTION.match(label):
            return "song_section"
        if eid.startswith("voice-") or SCENE.match(label):
            return "voice_line"
        return "unknown"
    if cls & {"card", "screen"}:
        return "card_text"
    if re.fullmatch(r"S\d+[a-z]?-layer-\d+", eid) or re.match(r"(S\d+[a-z]?\s+)?offer\s*·", label):
        return "card_text"                     # scene canvas to_studio: an offer card's own layer
    if "endcard" in cls:
        return "endcard_text"
    if cls & OVERLAY:
        return "overlay_graphic"
    if "cap" in cls or (cls <= {"clip"} and (label or el["text"].strip())):
        return "caption"
    return "unknown"


def check(project: Path, sheet: Path | None = None, c: dict | None = None) -> dict:
    c = c or contract()
    project = Path(project)
    index = project / "index.html"
    sheet = sheet or find_sheet(project)
    rows = sheet_rows(sheet)
    p = _Timed()
    p.feed(index.read_text())
    holds = {l["lane"]: set(l["holds"]) for l in c["lanes"]}
    out = []
    for el in p.found:
        a = el["attrs"]
        if "data-start" not in a:
            continue
        try:
            track = int(a["data-track-index"])
        except ValueError:
            continue
        label = _strip_row(" ".join(html.unescape(a.get("data-timeline-label", "")).split()), c)
        what = label or " ".join(el["text"].split())
        eid = a.get("id", "")
        m = (SCENE.match(what) or SCENE.match(Path(a.get("src", "")).stem)
             or SCENE.match(eid.removeprefix("voice-")) or re.search(r"\b(S\d+[a-z]?)\b", what))   # last: "Whoosh · S4, the drop"
        scene = m.group(1) if m else None
        kind = kind_of(el, label, scene, rows)
        sits = lane_of(track, c)
        # a card scene's own text layers may sit on the card's lane (scene canvas puts them there)
        if kind == "caption" and sits in ("Cards", "End card") and rows.get(scene or "") == sits:
            kind = "card_text" if sits == "Cards" else "endcard_text"
        home = (c["kinds"].get(kind) or {}).get("home")
        if sits is None:
            verdict = "off"
        elif kind == "unknown":
            verdict = "unknown"
        elif kind in holds[sits]:
            verdict = "ok"
        else:
            verdict = "wrong"
        if kind == "picture" and verdict == "wrong":
            home = "a picture lane"
        out.append({"id": a.get("id", ""), "scene": scene, "kind": kind, "say": (c["kinds"].get(kind) or {}).get("say", "something unrecognised"),
                    "what": SCENE.sub("", what).strip(" ·") or what, "track": track, "sits_on": sits or f"row {track} (no lane)",
                    "belongs_on": home, "verdict": verdict, "start": float(a.get("data-start") or 0)})
    name = project.name
    meta = project / "meta.json"
    if meta.is_file():
        name = json.loads(meta.read_text()).get("name") or name
    bad = [e for e in out if e["verdict"] in ("wrong", "off")]
    return {"project": name, "folder": str(project), "sheet": str(sheet) if sheet else None,
            "elements": out, "wrong": bad, "unknown": [e for e in out if e["verdict"] == "unknown"],
            "clean": not bad, "lanes": [l["lane"] for l in c["lanes"]]}


def line(e: dict) -> str:
    who = e["scene"] or "no scene"
    what = e["what"][:60]
    where = f"belongs on {e['belongs_on']}" if e["belongs_on"] else "belongs on one of its own lanes"
    return f"  ✗ {who} · {e['say']} “{what}” sits on {e['sits_on']}, {where}"


def report(r: dict) -> str:
    n = len(r["elements"])
    used = len({e["sits_on"] for e in r["elements"]})
    head = f"{r['project']} · {n} elements on {used} rows" + ("" if r["sheet"] else " · no cut sheet found: pictures checked by what they are only")
    if r["clean"]:
        body = ["  ✓ clean: every element is on its own lane"]
    else:
        body = [f"  {len(r['wrong'])} on the wrong lane:"] + [line(e) for e in sorted(r["wrong"], key=lambda e: e["start"])]
    for e in r["unknown"]:
        body.append(f"  ? {e['scene'] or 'no scene'} · can't tell what “{e['what'][:60]}” is (row {e['track']}, {e['sits_on']})")
    return "\n".join([head] + body)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="+")
    ap.add_argument("--sheet")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    results = [check(Path(p), Path(a.sheet) if a.sheet else None) for p in a.project]
    if a.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=1, ensure_ascii=False))
    else:
        print("\n\n".join(report(r) for r in results))
    return 0 if all(r["clean"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
