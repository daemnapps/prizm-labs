#!/usr/bin/env python3
"""kit_from_run.py — the join between MAKING and EDITING: reads a video machine
run record and writes the edit kit from it. Reads only; the production run is
never written to.

    build(vm_run) -> (kit, notes)      python3 machine/run.py from-run <video-production-run>

What it reads (tools/video-production's own record):
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

Every element in tools/video-production/ELEMENTS.md is carried (2026-09-23):
  scenes   kind talking · broll · card · screen · split · greenscreen · endcard, with
           their data, `opens`, `section` (the doctrine's id; `module` read only as a
           deprecated alias), `priority`, `claims`. A plate is found at the
           path the plan names or media/<scene>-PLATE.* (split: -L / -R, greenscreen: -BG);
           a card's or screen's words are copied as `plan_lines` so the gate can hold the
           set words to them exactly
  layers   hook · captions · lower_thirds · annotations · platform_ui · transitions · icons
  scenes   + subject_box per scene when production marks where the person is (text placement avoids it)
  sound    music / sfx / room_tone as bank rows {bank_id, file}; a file not on this
           machine goes to `unmade` by name (the gate reds it) — never a silent fallback
  versions hooks [{id, text, opener_scene}], plan.versions {cutdowns} — 9:16 only; `section` rides on each clip
  name     the naming fields (plan.name / run.name) for components/naming
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
        elif par.get("verdict") == "CUT_OFF":
            why.append("the line is cut off — sent back for a remake (remake-clip)")
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


def workspace() -> Path:
    """Found by walking up, never counted (the 2026-09-23 lesson)."""
    for d in Path(__file__).resolve().parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return Path(__file__).resolve().parent


KINDS = ("talking", "broll", "card", "screen", "split", "greenscreen", "endcard")
PLATE_EXT = (".png", ".jpg", ".jpeg", ".webp")
CLIP_EXT = (".mp4", ".mov", ".webm")


MODULE_ALIAS = {"mechanism": "unique-mechanism", "cta": "call-to-action"}  # the old six-value `module` tag, deprecated 2026-09-23


def section_ids() -> list[str]:
    """The doctrine's own section vocabulary (components/marketing-doctrine/frameworks.json),
    read, never restated here. [] when the doctrine is not on this machine."""
    f = workspace() / "components" / "marketing-doctrine" / "frameworks.json"
    d = _read(f, {}) or {}
    return [r["id"] for r in d.get("sections") or [] if isinstance(r, dict) and r.get("id")]


def section_of(s: dict, ids: list[str]) -> str | None:
    """A scene's section — the swap unit. `section` is what every scene already carries;
    `module` is read only as a deprecated alias. Never required: None when neither names one."""
    import re as _re
    for raw in (s.get("section"), s.get("module")):
        v = _re.sub(r"[^a-z0-9]+", "-", str(raw or "").strip().lower()).strip("-")
        v = MODULE_ALIAS.get(v, v)
        if v and (not ids or v in ids):
            return v
    return None


def kind_of(s: dict) -> str:
    """ELEMENTS.md §1. A scene written before `kind` existed is read off its type."""
    k = str(s.get("kind") or "").strip().lower()
    if k in KINDS:
        return k
    if s.get("type") == "C" or s.get("card"):
        return "card"
    return "talking" if (s.get("type") == "A" and s.get("to_camera")) else "broll"


def media(vm: Path, sid: str, given=None, roles=("PLATE",), exts=PLATE_EXT + CLIP_EXT) -> Path | None:
    """Where production put a picture: the path the plan names (absolute, or in the run),
    else media/<scene>-<ROLE>.<ext>. None when it is not there — never a guess."""
    if given:
        for p in (Path(str(given)), vm / str(given), vm / "media" / str(given)):
            if p.is_file():
                return p.resolve()
    for role in roles:
        for e in exts:
            p = vm / "media" / (f"{sid}-{role}{e}" if role else f"{sid}{e}")
            if p.is_file():
                return p
    return None


def bank_file(vm: Path, bank: str, row: dict | None) -> Path | None:
    """A music / SFX / room-tone file named by a bank row ({bank_id, file}). A missing
    file is an error the gate names, never a silent fallback (ELEMENTS.md §3)."""
    if not isinstance(row, dict) or not row.get("file"):
        return None
    f = str(row["file"])
    root = workspace()
    drives = sorted((Path.home() / "Library" / "CloudStorage").glob("GoogleDrive-*/Shared drives"))  # the row's `file` is a Drive path
    for p in (Path(f), vm / f, root / "tools" / "video-production" / "banks" / bank / f, *(d / f for d in drives)):
        if p.is_file():
            return p.resolve()
    return None


def bank_row(bank: str, bank_id: str | None) -> dict:
    """The bank's index row for an id (tags, tempo) — read-only, {} when the index is not built yet."""
    root = workspace()
    idx = _read(root / "tools" / "video-production" / "banks" / bank / "index.json", {}) or {}
    rows = idx.get("rows") if isinstance(idx, dict) else idx
    return next((r for r in rows or [] if isinstance(r, dict) and r.get("id") == bank_id), {})


def still_ok(sid: str, verdicts: dict) -> tuple[bool, str]:
    """A plate is a still: no motion to judge, so only a FLAG on it holds it."""
    for key in (sid, f"{sid}-PLATE"):
        for layer, row in (verdicts.get(key) or {}).items():
            if isinstance(row, dict) and row.get("verdict") == "FLAG":
                return False, f"{layer} FLAG on {key}"
    return True, ""


def build(vm: Path) -> tuple[dict, list[str]]:
    vm = vm.resolve()
    run, plan = _read(vm / "run.json", {}), _read(vm / "plan.json", {})
    verdicts = _read(vm / "verdicts.json", {}) or {}
    notes, clips, unmade = [], [], []
    scene_ids = [s.get("id") for s in plan.get("scenes") or []]
    sections = section_ids()
    timing = (_read(vm / "vo" / "timing.json", {}) or {}).get("scenes") or {}
    for s in plan.get("scenes") or []:
        sid = s["id"]
        kind = kind_of(s)
        base = {"id": sid, "scene": sid, "section": section_of(s, sections), "kind": kind, "opens": bool(s.get("opens")),
                "priority": s.get("priority"), "claims": s.get("claims") or [],
                "subject_box": s.get("subject_box"),  # where the person is ({x,y,w,h} % or one per frame) — text moves off it
                "why": f"{s.get('section')}: {s.get('outcome') or s.get('happens') or kind}".strip(": "), "line": s.get("voice")}
        tm = timing.get(sid) or {}
        if tm.get("said_as") or tm.get("numbers"):  # what production swapped before the voice read it — the captions go back to the script's spelling
            base["said"] = {"said_as": tm.get("said_as") or [], "numbers": tm.get("numbers") or []}
        vo = vm / "vo" / f"{sid}.mp3"
        if kind in ("talking", "broll"):
            clip = vm / "media" / f"{sid}.mp4"
            if not clip.exists():
                notes.append(f"{sid} ({s.get('section')}): no clip made yet")
                continue
            talking = kind == "talking"
            ok, why = approved(vm, sid, talking, verdicts)
            if not ok:
                notes.append(f"{sid}: not approved — {why}")
            row = {**base, "src": str(clip), "approved": ok}
            if talking:
                row.update({"roll": "a", "talks": True, "words": None})
            else:
                if not vo.exists():
                    notes.append(f"{sid}: B-roll scene with no voice slice at vo/{sid}.mp3")
                    continue
                row.update({"roll": "b", "talks": False, "voice": {"src": str(vo), "words": None}})
            clips.append(row)
            continue
        # the made-once kinds: a plate (or two) the edit composes type on
        data = dict(s.get(kind) or {})
        if kind == "greenscreen":
            talker = data.get("talker_scene") or sid
            clip = media(vm, talker, data.get("clip"), roles=("",), exts=CLIP_EXT)
            bg = media(vm, sid, data.get("background"), roles=("BG", "PLATE"))
            if not clip or not bg:
                notes.append(f"{sid} (greenscreen): " + ", ".join(x for x, f in (("no presenter clip", clip), ("no background plate", bg)) if not f) + " made yet")
                unmade.append(f"{sid}: greenscreen parts not made")
                continue
            ok, why = approved(vm, talker, True, verdicts)
            if not ok:
                notes.append(f"{sid}: presenter clip {talker} not approved — {why}")
            data.update({"background": str(bg), "layout": data.get("layout") or "pip"})
            clips.append({**base, "src": str(clip), "roll": "a", "talks": True, "words": None, "approved": ok, "greenscreen": data})
            continue
        if kind == "split":
            left = media(vm, sid, data.get("left"), roles=("L", "LEFT"))
            right = media(vm, sid, data.get("right"), roles=("R", "RIGHT"))
            if not left or not right:
                notes.append(f"{sid} (split): a side is not made yet")
                unmade.append(f"{sid}: split side not made")
                continue
            ok, why = approved(vm, sid, False, verdicts) if any(str(x).endswith(CLIP_EXT) for x in (left, right)) else still_ok(sid, verdicts)
            data.update({"left": str(left), "right": str(right), "layout": data.get("layout") or "side", "labels": data.get("labels") or []})
            src = left
        else:  # card · screen · endcard: one text-free plate (an endcard's is an edit of the real packshot: <S>-PACKSHOT)
            roles = ("PACKSHOT", "PLATE") if kind == "endcard" else ("PLATE",)
            plate = media(vm, sid, data.get("plate") if str(data.get("plate", "")).lower().endswith(PLATE_EXT) else None, roles=roles)
            if not plate:
                notes.append(f"{sid} ({kind}): no plate made yet — media/{sid}-{roles[0]}.png")
                unmade.append(f"{sid}: {kind} plate not made")
                continue
            ok, why = still_ok(sid, verdicts)
            data["plate_brief"] = data.get("plate")
            data["plate"] = str(plate)
            if kind in ("card", "screen"):
                data["plan_lines"] = list(data.get("lines") or [])  # the gate holds the set words to these, exactly
            if kind == "endcard":
                data["plan_offer_lines"] = list(data.get("offer_lines") or [])
            src = plate
        if not ok:
            notes.append(f"{sid}: not approved — {why}")
        row = {**base, "src": str(src), "roll": "a", "talks": False, "still": str(src).lower().endswith(PLATE_EXT), "approved": ok, kind: data}
        if vo.exists():  # a plate over its slice of the one read: the voice is the clock, like B-roll
            row.update({"roll": "b", "voice": {"src": str(vo), "words": None}})
        else:
            row["hold"] = data.get("seconds") or s.get("seconds") or None
        clips.append(row)
    for c in plan.get("cutaways") or []:
        notes.append(f"cutaway {c.get('id', '?')}: cutaways are not read yet — the plan's cutaway shape has no run to learn from")

    # layers (ELEMENTS.md §2) — carried as they are; the edit sets them, it never writes their words
    ed = edit_block(vm)
    lay = dict(plan.get("layers") or {})
    overlays = []
    hook = lay.get("hook") or ({"text": ed["headline"]} if ed.get("headline") and ed["headline"] != "none" else None)
    opener = next((c for c in clips if c.get("opens")), clips[0] if clips else None)
    if hook and hook.get("text") and opener:
        overlays.append({"id": "hook", "kind": "hook", "text": hook["text"], "look": hook.get("look"), "with": opener["id"], "y_pct": 18})
    hooks = [dict(h) for h in plan.get("hooks") or [] if isinstance(h, dict) and h.get("text")]
    for h in hooks:
        if h.get("opener_scene") and h["opener_scene"] not in scene_ids:
            notes.append(f"hook {h.get('id')}: opener_scene {h['opener_scene']} is not a scene")

    # sound (ELEMENTS.md §3) — every file from a bank, by row
    music = None
    m = plan.get("music")
    if isinstance(m, dict) and (m.get("file") or m.get("bank_id")):
        f = bank_file(vm, "music", m)
        row = bank_row("music", m.get("bank_id"))
        if f:
            music = {"src": str(f), "bank_id": m.get("bank_id"), "tempo_bpm": m.get("tempo_bpm") or row.get("tempo_bpm"),
                     "energy": m.get("energy") or row.get("energy"), "mood": m.get("mood") or row.get("mood")}
        else:
            unmade.append(f"music {m.get('bank_id')}: the bank row's file is not on this machine ({m.get('file')})")
    elif ed.get("music") and ed["music"] != "none":
        notes.append("the brief asks for music but the plan names no music bank row yet — that layer is empty")
    sfx = []
    room_rows = [x for x in plan.get("sfx") or [] if isinstance(x, dict) and str(x.get("bank_id") or x.get("cue") or "").startswith("room-tone")]
    for i, x in enumerate(x for x in plan.get("sfx") or [] if x not in room_rows):
        f = bank_file(vm, "sfx", x)
        if not f:
            unmade.append(f"sfx {x.get('cue') or x.get('bank_id')}: the bank row's file is not on this machine ({x.get('file')})")
            continue
        sfx.append({"id": f"sfx{i + 1}", "src": str(f), "bank_id": x.get("bank_id"), "cue": x.get("cue"),
                    "at_words": x.get("at_words"), "scene": x.get("scene"), "for": x.get("at_words") or x.get("scene") or x.get("cue")})
    if not plan.get("sfx") and ed.get("effects") and ed["effects"] != "none":
        notes.append("the brief asks for sound effects but the plan names no SFX bank rows yet — that layer is empty")
    room = []
    rt = plan.get("room_tone")  # its own key, or the SFX bank's room-tone-<setting> rows named as cues
    for x in (rt if isinstance(rt, list) else [rt] if rt else []) + room_rows:
        f = bank_file(vm, "sfx", x)
        if f:
            room.append({"src": str(f), "bank_id": x.get("bank_id"), "setting": x.get("setting")})
        else:
            unmade.append(f"room tone {x.get('bank_id')}: the bank row's file is not on this machine")
    if not ed and not plan.get("layers"):
        notes.append("the brief has no edit block (written before AI brief v11) — no headline, caption read, music or effects to carry")

    versions = dict(plan.get("versions") or {})
    name = {k: v for k, v in {**(run.get("name") or {}), **(plan.get("name") or {})}.items() if v}
    for k in ("brief", "format"):
        if run.get(k) and k not in name:
            name[k] = run[k]
    kit = {"from_run": str(vm), "brand": run.get("brand"), "label": run.get("label"), "format": run.get("format"),
           "style_id": (plan.get("piece") or {}).get("style_id"), "brief": run.get("source_brief"),
           "voice": None, "music": music, "sfx": sfx, "room_tone": room, "clips": clips, "overlays": overlays,
           "layers": {k: lay.get(k) for k in ("lower_thirds", "annotations", "platform_ui", "transitions", "icons") if lay.get(k)},
           "caption_look": (lay.get("captions") or {}).get("look"), "grade": (plan.get("piece") or {}).get("grade"),
           "hooks": hooks, "versions": versions, "framework": plan.get("framework") or (plan.get("piece") or {}).get("framework"), "claims": plan.get("claims") or [], "platform": plan.get("platform") or run.get("platform"),
           "name": name, "unmade": unmade,
           "caption_read": ed.get("captions"), "wanted": {k: ed.get(k) for k in ("music", "effects", "cards") if ed.get(k)}}
    return kit, notes
