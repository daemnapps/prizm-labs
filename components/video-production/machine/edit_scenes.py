#!/usr/bin/env python3
"""edit_scenes.py — the AI lane's scenes, ready to cut: each scene's picture, its voice and its words, from the chain's
own files (owner, 2026-11-20: video production is the piece holding the business back; the chain assembles the cut,
the Studio shows it, the editor builds on it).

For every scene the chain published (media/<scene>.mp4, written by clip_publish: a scene over two calls joined, a
split stacked render-over-people) it writes, under <run>/edit/:

    <scene>.mp4          the scene's picture with its voice: a talking scene keeps its own clip's sound (the read it
                         was lip-synced to); a silent scene gets the scene's locked read (vo/<scene>.mp3) as its
                         voice-over. A picture shorter than its voice holds its last frame to the end of the voice.
    <scene>.wav          that voice alone (what the Studio's cut lays as the scene's read)
    <scene>.words.json   {"words": [{w, start, end}]} on that voice's clock, from the read's own line times
                         (vo/timing.json), each line's words spread over its span by length — the captions' words
    EDIT.json            the scenes in the plan's order: file, seconds, where the voice came from, its text

Nothing is generated and nothing is spent; idempotent. No brand, product or person is named.

    python3 edit_scenes.py <run>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAIL = 0.2                      # the breath after a scene's last word


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def dur(p) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def has_sound(p) -> bool:
    """True when the file has an audio stream that is not silence."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of",
                        "csv=p=0", str(p)], capture_output=True, text=True)
    if not r.stdout.strip():
        return False
    v = subprocess.run(["ffmpeg", "-v", "info", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    try:
        mx = float(v.split("max_volume:")[1].split("dB")[0])
    except (IndexError, ValueError):
        return True
    return mx > -50


def words_of(scene_timing: dict, offset: float = 0.0, until: float | None = None) -> list:
    """[{w, start, end}] for one scene's read, each line's words spread over its own span by length. A last line the
    timing gave no length (start == end, 2026-11-21: brief-0380's "Tap below to buy.") runs to `until`, the end of the
    scene's own sound on the same clock as the lines, when that is later."""
    out = []
    lines = scene_timing.get("lines") or []
    for k, ln in enumerate(lines):
        toks = [t for t in str(ln.get("text") or ln.get("said") or "").split() if t]
        a, z = float(ln.get("start") or 0), float(ln.get("end") or 0)
        if z <= a and k == len(lines) - 1 and until is not None and until > a + 0.3:
            z = until
        if not toks or z <= a:
            continue
        total = sum(len(t) for t in toks)
        t0 = a
        for t in toks:
            t1 = t0 + (z - a) * len(t) / total
            out.append({"w": t, "start": round(t0 + offset, 3), "end": round(t1 + offset, 3)})
            t0 = t1
    return out


def _brief_doc(run: Path) -> dict:
    rj = _read(Path(run) / "run.json", {}) or {}
    bf = Path(rj.get("brief_from") or Path(run) / "brief.md")
    if not bf.is_absolute():
        bf = Path(__file__).resolve().parents[3] / bf
    try:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", bf.read_text(), re.S)
        return json.loads(blocks[-1]) if blocks else {}
    except (OSError, ValueError):
        return {}


def overlays_of(doc: dict, sid: str) -> tuple:
    """THE BRIEF'S ON-SCREEN TEXT AND ARROWS FOR ONE SCENE (2026-11-21, brief-0380: the close's "Tap below to buy." and
    its arrow never reached the cut): (placed, unplaced). Placed: each `Editor text "X": where; lands on "Y"` and each
    layers.annotations arrow with `at_words`, as {kind, text, where, at_words}; laid by the Studio as a card on the
    scene, timed to the words. Unplaced: editor text with no words to land on, listed for the editor, never guessed."""
    sc = next((x for x in doc.get("scenes") or [] if x.get("id") == sid), {}) or {}
    placed, unplaced = [], []
    for chunk in str(sc.get("on_screen") or "").split('Editor text "')[1:]:
        m = re.match(r'([^"]+)":\s*(.*)', chunk, re.S)
        if not m:
            continue
        body = m.group(2).split("\n")[0]
        lands = re.search(r'lands on "([^"]+)"', body)
        where = re.sub(r';?\s*lands on "[^"]+"\.?', "", body).strip(" ;.")
        (placed if lands else unplaced).append({"kind": "text", "text": m.group(1).strip(), "where": where,
                                                "at_words": lands.group(1).strip() if lands else ""})
    for a in ((doc.get("layers") or {}).get("annotations") or []):
        if a.get("scene") == sid and a.get("kind") == "arrow":
            (placed if a.get("at_words") else unplaced).append(
                {"kind": "arrow", "text": "", "where": str(a.get("target") or ""), "at_words": str(a.get("at_words") or "")})
    return placed, unplaced


def order_of(run: Path) -> list:
    """The run's scenes in play order (the plan's scenes, else the published files)."""
    plan = _read(run / "plan.json", {}) or {}
    ids = [s.get("id") for s in plan.get("scenes") or [] if s.get("id")]
    return ids or sorted(p.stem for p in (run / "media").glob("S*.mp4"))


def build(run: Path) -> dict:
    run = Path(run)
    timing = (_read(run / "vo" / "timing.json", {}) or {}).get("scenes") or {}
    out_dir = run / "edit"
    out_dir.mkdir(exist_ok=True)
    rows = []
    doc = _brief_doc(run)
    for sid in order_of(run):
        pic = run / "media" / f"{sid}.mp4"
        if not pic.is_file():
            continue
        t = timing.get(sid) or {}
        read = run / str(t.get("file") or f"vo/{sid}.mp3")
        talking = has_sound(pic)
        src = pic if talking else (read if read.is_file() else None)
        wav = out_dir / f"{sid}.wav"
        if src is not None:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "2", "-ar", "48000", str(wav)],
                           check=True)
        voice_s = dur(wav) if wav.is_file() else 0.0
        pic_s = dur(pic)
        seconds = round(max(pic_s, voice_s + TAIL if voice_s else 0.0), 3)
        dst = out_dir / f"{sid}.mp4"
        vf = f"tpad=stop_mode=clone:stop_duration={max(0.0, seconds - pic_s):.3f}"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(pic)]
        if wav.is_file():
            cmd += ["-i", str(wav), "-map", "0:v", "-map", "1:a", "-af", f"apad=whole_dur={seconds:.3f}"]
        else:
            cmd += ["-map", "0:v"]
        cmd += ["-vf", vf, "-t", f"{seconds:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt",
                "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(dst)]
        subprocess.run(cmd, check=True)
        # each scene's words on its OWN sound's clock (2026-11-21, brief-0380: the times were on the whole ad's voice
        # timeline, and the Studio added the scene's place on top, so every scene's captions started that late):
        # the scene's read starts at its timing `start`, which is second 0 of edit/<scene>.wav
        words = words_of(t, -float(t.get("start") or 0), float(t.get("start") or 0) + voice_s if voice_s else None)
        (out_dir / f"{sid}.words.json").write_text(json.dumps({"words": words}, ensure_ascii=False) + "\n")
        rows.append({"scene": sid, "file": f"edit/{sid}.mp4", "voice": f"edit/{sid}.wav" if wav.is_file() else None,
                     "words": f"edit/{sid}.words.json", "seconds": seconds,
                     "voice_from": "the clip's own lip-synced sound" if talking else
                     ("the scene's locked read, laid as voice-over" if src is not None else "none"),
                     "text": " ".join(str(ln.get("text") or "") for ln in t.get("lines") or []).strip(),
                     "overlays": overlays_of(doc, sid)[0], "overlays_unplaced": overlays_of(doc, sid)[1]})
    # the clip checklist's fix list rides with each scene into the cut: the small misses to adjust (owner, 2026-11-21)
    fx = _read(run / "clips" / "fixes.json", {}) or {}
    for r in rows:
        r["fixes"] = [f for v in fx.values() if r["scene"] in (v.get("scenes") or []) for f in v.get("fixes") or []]
    gaps = _read(run / "clips" / "gaps.json", {}) or {}
    res = {"scenes": rows, "seconds": round(sum(r["seconds"] for r in rows), 3),
           "gaps": [f"{k} ({', '.join(v.get('scenes') or [])}): refused by the model — hold a neighbouring shot or let "
                    f"the section's made clip cover it" for k, v in gaps.items()],
           "fixes": [f"{r['scene']} · {f['picture']}: {f['fix']}" for r in rows for f in r["fixes"]]}
    (out_dir / "EDIT.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    return res


def main(argv=None) -> int:
    run = Path((argv or sys.argv[1:])[0]).resolve()
    res = build(run)
    for r in res["scenes"]:
        print(f"{r['scene']:>4}  {r['seconds']:6.2f}s  {r['voice_from']}")
    print(f"{len(res['scenes'])} scene(s), {res['seconds']} s — {run / 'edit' / 'EDIT.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
