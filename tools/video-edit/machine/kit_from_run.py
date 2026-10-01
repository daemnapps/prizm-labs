#!/usr/bin/env python3
"""kit_from_run.py — the join between MAKING and EDITING: reads a video machine
run record and writes the edit kit from it. Reads only; the production run is
never written to.

    build(vm_run) -> (kit, notes)      python3 machine/run.py from-run <video-machine-run>

What it reads (ai-video-production's own record):
  run.json      brand, label, format            plan.json   scenes in order — type A (to camera) / B, the line, the section
  media/<id>.mp4  the chosen take per scene     vo/<id>.mp3  the scene's slice of the one voice read
  brief.md        the brief's `edit` block — headline, caption look, music, effects, cards (AI brief v11+)
  verdicts.json   motion · director · parity    media/<id>.parity.json  the line check written beside a take

A scene of type A that speaks to camera is TALKING A-ROLL: it keeps its own
sound (that is what keeps the lips right) and is cut at its pauses. A scene of
type B is B-ROLL OVER VOICE: its picture covers its slice of the voice read.
A clip is `approved` only when the record says so — motion and director
verdicts on file and not FLAG, and for a talking clip the words check PASS.
Nothing here approves anything.
"""
from __future__ import annotations
import json
from pathlib import Path


def _read(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def approved(vm: Path, sid: str, talking: bool, verdicts: dict) -> tuple[bool, str]:
    v = verdicts.get(sid) or {}
    why = []
    for layer in ("motion", "director"):
        row = v.get(layer)
        if not isinstance(row, dict):
            why.append(f"no {layer} verdict")
        elif row.get("verdict") == "FLAG":
            why.append(f"{layer} FLAG")
    if talking:
        par = v.get("parity") or _read(vm / "media" / f"{sid}.parity.json")
        if not isinstance(par, dict):
            why.append("words never checked")
        elif par.get("verdict") != "PASS":
            why.append("says other words")
    return (not why), ", ".join(why)


def edit_block(vm: Path) -> dict:
    """The brief's own `edit` block (AI brief v11+): headline, the source's caption
    look, music, effects, cards. The video machine ignores it; the edit reads it."""
    import re
    brief = vm / "brief.md"
    if not brief.exists():
        return {}
    for body in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", brief.read_text(), flags=re.S):
        try:
            d = json.loads(body)
        except Exception:
            continue
        if isinstance(d, dict) and "scenes" in d:
            return d.get("edit") or {}
    return {}


def build(vm: Path) -> tuple[dict, list[str]]:
    vm = vm.resolve()
    run, plan = _read(vm / "run.json", {}), _read(vm / "plan.json", {})
    verdicts = _read(vm / "verdicts.json", {}) or {}
    notes, clips = [], []
    for s in plan.get("scenes") or []:
        sid = s["id"]
        clip = vm / "media" / f"{sid}.mp4"
        if not clip.exists():
            notes.append(f"{sid} ({s.get('section')}): no clip made yet")
            continue
        talking = s.get("type") == "A" and bool(s.get("to_camera"))
        ok, why = approved(vm, sid, talking, verdicts)
        if not ok:
            notes.append(f"{sid}: not approved — {why}")
        row = {"id": sid, "src": str(clip), "scene": sid, "section": s.get("section"), "approved": ok,
               "why": f"{s.get('section')}: {s.get('outcome') or s.get('happens') or ''}".strip(": ")}
        if talking:
            row.update({"roll": "a", "talks": True, "words": None, "line": s.get("voice")})
        else:
            vo = vm / "vo" / f"{sid}.mp3"
            if not vo.exists():
                notes.append(f"{sid}: B-roll scene with no voice slice at vo/{sid}.mp3")
                continue
            row.update({"roll": "b", "talks": False, "voice": {"src": str(vo), "words": None}, "line": s.get("voice")})
        clips.append(row)
    for c in plan.get("cutaways") or []:
        notes.append(f"cutaway {c.get('id', '?')}: cutaways are not read yet — the plan's cutaway shape has no run to learn from")
    ed = edit_block(vm)
    overlays = []
    if ed.get("headline") and ed["headline"] != "none" and clips:
        overlays.append({"id": "hook", "kind": "hook", "text": ed["headline"], "with": clips[0]["id"], "y_pct": 16})
    for want, label in (("music", "music"), ("effects", "sound effects")):
        if ed.get(want) and ed[want] != "none":
            notes.append(f"the brief asks for {label} — no station makes them yet, so that layer is empty")
    if not ed:
        notes.append("the brief has no edit block (written before AI brief v11) — no headline, caption read, music or effects to carry")
    kit = {"from_run": str(vm), "brand": run.get("brand"), "label": run.get("label"), "format": run.get("format"),
           "style_id": (plan.get("piece") or {}).get("style_id"), "brief": run.get("source_brief"),
           "voice": None, "music": None, "sfx": [], "clips": clips, "overlays": overlays,
           "caption_read": ed.get("captions"), "wanted": {k: ed.get(k) for k in ("music", "effects", "cards") if ed.get(k)}}
    return kit, notes
