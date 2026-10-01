#!/usr/bin/env python3
"""cutsheet.py — the cut sheet: the one file that IS the edit, and the gate it
has to pass before anything renders.

The model (or the auto cut) decides; this file checks; compose.py executes.
Nothing else knows what is in the video.

    python3 machine/cutsheet.py check <cutsheet.json>

Shape (every time is seconds on the FINAL timeline unless it says source):

    meta      brand, label, format, style_id, width, height, fps
    controls  the dials this edit ran under (defaults.json + the run's overrides)
    voice     {src, start, volume_db} | null     a voiceover piece only. A TALKING clip carries its
                                                 own sound (talks: true, volume_db set) — never both
    voice_cuts [{id, src, start, duration, source_start, volume_db}]   a B-roll scene's slice of the voice read, cut at its pauses
    music     {src, start, volume_db} | null
    sfx       [{id, src, at, volume_db, for}]    `for` = the clip or word it belongs to
    picture   [{id, roll: "a"|"b", src, start, duration, source_start, scene, why,
                volume_db|null, still: bool}]    a-roll below, b-roll covers it
    captions  {look, words: [{text, start, end}], fixes: [{from, to}]}
    overlays  [{id, kind: "hook"|"label"|"end-card", text, start, duration, y_pct}]

No brand name lives in this file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent


def load(name: str) -> dict:
    return json.loads((TOOL / name).read_text())


def probe_seconds(path: Path) -> float | None:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception:
        return None


def end_of(sheet: dict) -> float:
    ends = [c["start"] + c["duration"] for c in sheet.get("picture", [])]
    return round(max(ends), 3) if ends else 0.0


def check(sheet: dict, root: Path, probe=probe_seconds) -> list[str]:
    """Every reason this sheet may not render. Empty list = green."""
    red: list[str] = []
    meta = sheet.get("meta") or {}
    for f in ("brand", "label", "width", "height", "fps"):
        if not meta.get(f):
            red.append(f"meta.{f} is missing")

    looks = {r["id"] for r in load("looks/bank.json")["looks"]}
    transitions = {r["id"] for r in load("looks/transitions.json")["transitions"]}
    controls = sheet.get("controls") or {}
    t = (controls.get("transition") or {}).get("value", "cut")
    if t not in transitions:
        red.append(f"controls.transition `{t}` is not a transition — known: {', '.join(sorted(transitions))}")

    picture = sheet.get("picture") or []
    if not picture:
        red.append("picture is empty — there is no video")
    ids = set()
    for i, c in enumerate(picture):
        at = f"picture[{i}] ({c.get('id', '?')})"
        if c.get("id") in ids:
            red.append(f"{at}: id used twice")
        ids.add(c.get("id"))
        if c.get("roll") not in ("a", "b"):
            red.append(f"{at}: roll must be 'a' or 'b'")
        if not c.get("why"):
            red.append(f"{at}: no `why` — every cut says what it is for")
        src = root / str(c.get("src", ""))
        if not src.is_file():
            red.append(f"{at}: file not found — {c.get('src')}")
            continue
        if c.get("duration", 0) <= 0:
            red.append(f"{at}: duration must be above zero")
        if not c.get("still"):
            have = probe(src)
            need = c.get("source_start", 0) + c.get("duration", 0)
            if have is not None and need > have + 0.05:
                red.append(f"{at}: trim runs past the source ({need:.2f}s asked, {have:.2f}s there)")

    # no hole in the picture: a-roll + b-roll together cover 0 → end
    end = end_of(sheet)
    spans = sorted((c["start"], c["start"] + c["duration"]) for c in picture if c.get("duration", 0) > 0)
    cursor = 0.0
    for s, e in spans:
        if s > cursor + 0.04:
            red.append(f"picture has a hole from {cursor:.2f}s to {s:.2f}s — nothing is on screen")
        cursor = max(cursor, e)
    a_spans = sorted((x["start"], x["start"] + x["duration"]) for x in picture if x.get("roll") == "a")
    for c in picture:
        if c.get("roll") == "b":
            at, stop = c["start"], c["start"] + c["duration"]
            under = a_spans + sorted((v["start"], v["start"] + v["duration"]) for v in sheet.get("voice_cuts") or [])
            for s0, e0 in sorted(under):  # a-roll (or the voice it covers) may be several cuts back to back
                if s0 <= at + 0.04 and e0 > at:
                    at = e0
            if at < stop - 0.04:
                red.append(f"picture ({c.get('id')}): b-roll has nothing under it from {at:.2f}s — if it carries the moment alone, label it 'a'")

    voice = sheet.get("voice")
    talking = [x for x in picture if x.get("talks")]
    for x in talking:
        if x.get("volume_db") is None:
            red.append(f"picture ({x.get('id')}): a talking clip is muted — it must carry its own sound, or the lips will not match")
    vcuts = sheet.get("voice_cuts") or []
    for i, v in enumerate(vcuts):
        if not (root / str(v.get("src", ""))).is_file():
            red.append(f"voice_cuts[{i}]: file not found — {v.get('src')}")
        for x in talking:
            if v["start"] < x["start"] + x["duration"] - 0.04 and x["start"] < v["start"] + v["duration"] - 0.04:
                red.append(f"two voices at {max(v['start'], x['start']):.2f}s: voice cut {v.get('id')} runs while {x.get('id')} is talking")
    if voice and talking:
        red.append("two voices: a separate voice track AND talking clips with their own sound — a talking clip's own sound is the voice")
    if not voice and not talking and not vcuts:
        red.append("no voice: neither a voice track nor a talking clip")
    if voice:
        if not (root / str(voice.get("src", ""))).is_file():
            red.append("voice: the approved voice track is missing")
        else:
            have = probe(root / voice["src"])
            if have is not None and voice.get("start", 0) + have > end + 0.5:
                red.append(f"voice runs {voice.get('start', 0) + have - end:.2f}s past the last picture")
    music = sheet.get("music")
    if music:
        if not (root / str(music.get("src", ""))).is_file():
            red.append(f"music: file not found — {music.get('src')}")
        if music.get("volume_db", -18) > (voice or {}).get("volume_db", 0) - 10:
            red.append("music is less than 10 dB under the voice — it will fight the words")
    for i, s in enumerate(sheet.get("sfx") or []):
        if not (root / str(s.get("src", ""))).is_file():
            red.append(f"sfx[{i}]: file not found — {s.get('src')}")
        if not s.get("for"):
            red.append(f"sfx[{i}]: no `for` — a sound belongs to a clip or a word")

    caps = sheet.get("captions") or {}
    if (controls.get("captions") or {}).get("value", "on") == "on":
        look = caps.get("look")
        if look not in looks and not (isinstance(look, dict) and look.get("id") == "match-swipe"):
            red.append(f"captions.look `{look}` is not a caption look — known: {', '.join(sorted(looks))}, or a match-swipe look")
        words = caps.get("words") or []
        if not words:
            red.append("captions are on but there are no timed words")
        last = -1.0
        for i, w in enumerate(words):
            if w["end"] <= w["start"]:
                red.append(f"captions.words[{i}] `{w['text']}`: ends before it starts")
            if w["start"] < last - 0.02:
                red.append(f"captions.words[{i}] `{w['text']}`: out of order")
            if w["end"] > end + 0.05:
                red.append(f"captions.words[{i}] `{w['text']}`: lands after the video ends")
            last = w["start"]

    safe = controls.get("safe_zone") or {}
    for i, o in enumerate(sheet.get("overlays") or []):
        if not o.get("text") and o.get("kind") != "end-card":
            red.append(f"overlays[{i}]: no text")
        y = o.get("y_pct")
        if y is not None and (y < safe.get("top_pct", 12) or y > 100 - safe.get("bottom_pct", 25)):
            red.append(f"overlays[{i}]: sits at {y}% — inside the part of the frame the app's buttons cover")
        if o.get("start", 0) + o.get("duration", 0) > end + 0.05:
            red.append(f"overlays[{i}]: runs past the end")
    return red


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2 or argv[0] != "check":
        print(__doc__)
        return 2
    p = Path(argv[1]).resolve()
    red = check(json.loads(p.read_text()), p.parent)
    for r in red:
        print("RED  ", r)
    print("GREEN — the sheet may render" if not red else f"{len(red)} to fix — nothing renders red")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
