#!/usr/bin/env python3
"""map_sheet.py — an edit map as a cut sheet, so ONE renderer draws every word (video system sync 2026-10-21, C13).

    sheet(vm, out, m, picture_mp4, sound_wav, heard) -> cut sheet      compose.py renders it; audit.py reads it

The edit map (edit_map.py) stays the cut — its clock, its mouths, its lips. render_map.py assembles its picture
(every piece from its in-point, the crops, the item cut-outs and stickers) and its sound with ffmpeg, as before; from
2026-10-21 it draws NO words. This file turns that picture + sound and the map's words into the cut sheet compose.py
already renders for the kit route, so captions, headlines, option cards, badges, the end card's words, the
transitions between shots and the realism finish come from one renderer, one look registry (looks/bank.json) and one
placement rule (placement.py: off every face and mouth — V13).

  picture   one sheet clip per piece on screen (render_map.flatten), all cut from the one assembled picture at its
            own second — so compose can draw a whip or a match where the brief's shot hands off that way (E28)
  sound     the assembled, mastered mix as the sheet's one voice track (the clips are muted here)
  captions  every line's words at the times production heard them (clips/calls/<clip>/transcript-words.json, E9 + E10),
            an own-track line's at the times the listen heard them; the script's spelling on those times; the line's
            `emphasis` words in the look's accent face (E11)
  overlays  the map's words on screen, each in its edit-looks.json `text` look, at the height the map set
  realism   the editing rows of the realism index for this piece (realism.py, E29)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent


def _call_dir(vm):
    """clips/calls/<call>/ — a run made before 2026-10-26 keeps clips/omni/<call>/ on disk."""
    c = Path(vm) / "clips"
    return c / "calls" if ((c / "calls").exists() or not (c / "omni").exists()) else c / "omni"


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def clip_words(vm: Path, clip: str) -> list[dict]:
    """Production's own word times for a take (clip seconds) — never transcribed again here (E9)."""
    w = _read(_call_dir(vm) / clip / "transcript-words.json", [])
    w = w.get("words", w) if isinstance(w, dict) else w
    return [x for x in w or [] if x.get("type", "word") == "word" and str(x.get("text", "")).strip()]


def line_words(vm: Path, l: dict, heard: list[dict] | None) -> tuple[list[dict], str]:
    """One line's words on the cut's clock, in the script's spelling, and where their times came from."""
    import spelling as SP
    got, by = [], "even"
    if l.get("kind") == "in clip" and l.get("clip"):
        lo, hi, sp = float(l["in"]), float(l["in"]) + float(l["len"]), float(l.get("speed") or 1)
        for w in clip_words(vm, l["clip"]):
            if w["end"] <= lo + 0.02 or w["start"] >= hi - 0.02:
                continue
            got.append({"text": w["text"], "start": round(l["a"] + (max(lo, w["start"]) - lo) / sp, 3),
                        "end": round(l["a"] + (min(hi, w["end"]) - lo) / sp, 3)})
        by = "production" if got else by
    if not got and heard:
        got = [{"text": w["text"], "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)}
               for w in heard if l["a"] - 0.12 <= float(w["start"]) < l["b"] + 0.05 and str(w.get("text", "")).strip()]
        by = "heard" if got else by
    if got:
        words, _ = SP.align(got, l.get("text"), None)
        return [w for w in words if str(w.get("text", "")).strip()], by
    ws = str(l.get("text") or "").split()          # nothing timed it: spread across the line, said so on the sheet
    step = (l["b"] - l["a"]) / max(1, len(ws))
    return [{"text": t, "start": round(l["a"] + k * step, 3), "end": round(l["a"] + (k + 1) * step, 3)} for k, t in enumerate(ws)], by


def hand_offs(vm: Path) -> dict:
    """{scene: hands_off} — how each scene hands off to the next (the shot contract: continuous · action · match · whip
    · cut): the scene's own, else its last shot's (brief v3), else the plan's `layers.transitions`, else the
    storyboard's sections. {} when the brief predates it."""
    import kit_from_run as K
    out = {}
    plan = _read(vm / "plan.json", {}) or {}
    for s in plan.get("scenes") or []:
        k = K.scene_hands_off(s)
        if s.get("id") and k:
            out[s["id"]] = k
    for t in (plan.get("layers") or {}).get("transitions") or []:
        if isinstance(t, dict) and t.get("after_scene") and t.get("kind") and t["after_scene"] not in out:
            out[t["after_scene"]] = str(t["kind"]).strip().lower()
    for g in (_read(vm / "storyboard.json", {}) or {}).get("sections") or []:
        for sc in g.get("scenes") or []:
            if g.get("hands_off") and sc not in out:
                out[sc] = str(g["hands_off"]).strip().lower()
    return out


DRAWN = {"whip": "whip", "match": "match"}          # continuous / action / cut are hard cuts: the pictures make them


def sheet(vm: Path, out: Path, m: dict, picture_mp4: Path, sound_wav: Path, heard: list[dict] | None = None,
          fmt: str | None = None) -> dict:
    import looks as LK
    import render_map as RM
    import realism as RL
    vm, out = Path(vm), Path(out)
    run = _read(vm / "run.json", {}) or {}
    fmt = fmt or run.get("format")
    plan = _read(vm / "clips" / "plan.json", {}) or {}
    first_scene = {c["id"]: (c.get("lines") or [{}])[0].get("scene") for c in plan.get("calls") or []}
    segs = RM.flatten(m)
    picture = []
    for i, s in enumerate(segs):
        sid = f"s{i:03d}"
        scene = s.get("scene") or first_scene.get(s.get("clip"))
        picture.append({"id": sid, "roll": "a", "src": str(picture_mp4), "start": round(s["a"], 3),
                        "duration": round(s["b"] - s["a"], 3), "source_start": round(s["a"], 3), "scene": sid,
                        "shot": scene, "section": s.get("section"), "clip": s.get("clip"), "still": False,
                        "talks": bool(s.get("lip")), "volume_db": None, "kind": None,
                        # the punch is ALREADY in the assembled picture (render_map.crop_filter): recorded, never a
                        # second scale in compose (verify 2026-10-21 row 1 — a 1.07 punch landed near 1.19)
                        **({"punched": float(s["scale"])} if s.get("scale") and float(s["scale"]) > 1 else {}),
                        "why": s.get("closeup") or s.get("fix") or ("the line, lip-synced" if s.get("lip") else s.get("kind") or "the plan's picture")})
    # captions: every spoken line's words, production's times first
    look_id = (m.get("captions") or {}).get("look_id")
    app = m.get("app") or LK.app_for(vm, run)               # the app the piece pretends to be made in (V13, verify 10-21
    if not LK.caption(look_id):                            # row 9): its own fields, the brief, else the swipe's link
        # the swipe's own caption look first (the scene breakdown's `captions`), then the format's
        look_id = LK.from_swipe(LK.swipe_captions(vm)) or LK.pick_caption(fmt, app)
    words, accent, timed_by = [], [], {}
    for l in sorted(m.get("voice") or [], key=lambda x: x["a"]):
        ws, by = line_words(vm, l, heard)
        words += ws
        timed_by[by] = timed_by.get(by, 0) + 1
        accent += [str(e) for e in (l.get("emphasis") or [])]
    words = sorted((w for w in words if w["start"] < float(m["total"]) - 0.05), key=lambda w: w["start"])   # an opening: its own words
    # the words on screen, each in its own look (edit-looks.json `text`), at the height the map set
    overlays, keep_clear = [], []
    for n, t in enumerate(m.get("text") or []):
        if t["kind"] not in ("hook headline", "option card", "endcard text", "badge", "card"):   # a card's words (2026-10-28)
            continue
        lk = LK.text_look(t["kind"], t.get("look_id")) if t["kind"] != "badge" else None
        # single words are one phrase, read as a line that wraps (an opening came out one word per line, 2026-10-28);
        # a list of phrases (a card's lines) keeps one per line. Repeats are kept: "this one is" repeats words
        ws = [str(w) for w in t["words"]]
        text = " ".join(ws) if all(" " not in w for w in ws) else "\n".join(dict.fromkeys(ws))
        y = t.get("pin_y") if t.get("pin_y") is not None else (t.get("y") if t.get("y") is not None else (lk or {}).get("y", 0.6))
        if t["kind"] == "badge":
            on = next((c for c in m.get("cutouts") or [] if c["a"] <= (t["a"] + t["b"]) / 2 < c["b"]), None)
            y = (on["box"][1] - 0.075) if on else 0.56
        ov = {"id": f"t{n}-{re.sub(r'[^a-z]+', '-', t['kind'])}", "kind": "hook" if (t["kind"] == "hook headline" and t.get("pin_y") is None) else "text",
              "what": t["kind"], "text": text, "start": round(t["a"], 3), "duration": round(t["b"] - t["a"], 3),
              "y_pct": round(float(y) * 100, 2), "fixed": True}
        if lk:
            ov["text_look"] = lk
        else:
            ov["badge"] = t.get("colour") or "red"
        overlays.append(ov)
    for ov in overlays:                            # the words already set on screen are taken: no caption over them
        lk = ov.get("text_look") or {}
        n = max(1, len(ov["text"].split("\n")))
        h = (n * float(lk.get("line_h", 72)) + 2 * float((lk.get("pad") or [0, 20])[1])) / 19.2 if lk else 7.0
        w = (float(lk.get("max_w", 860)) / 10.8) if lk else 40.0
        keep_clear.append({"box": [50 - w / 2, ov["y_pct"] - 1.0, 50 + w / 2, ov["y_pct"] + h + 1.0],
                           "start": ov["start"], "end": ov["start"] + ov["duration"], "what": ov["what"]})
    for cu in m.get("cutouts") or []:              # the item's cut-out and its badge are taken: no caption over them
        x0, y0, x1, y1 = cu["box"]
        keep_clear.append({"box": [x0 * 100, (y0 - 0.08) * 100, x1 * 100, y1 * 100], "start": cu["a"], "end": cu["b"], "what": "item"})
    tr = []
    ho = hand_offs(vm)
    for x, y in zip(picture, picture[1:]):
        k = DRAWN.get(ho.get(x.get("shot") or ""))
        if k and x.get("shot") != y.get("shot"):
            tr.append({"after_scene": x["scene"], "kind": k, "why": f"the brief's shot {x['shot']} hands off on a {k}"})
    cv = {"width": RM.W, "height": RM.H, "fps": RM.FPS}
    import run as R
    controls = R.controls_for(None)
    # the feeds whose safe box every word keeps inside: a paid placement adds Meta's Reels-ads zone (top 14%, bottom
    # 35% — the sponsored label, CTA and ad copy; V1/V16, verify 10-21 row 20)
    placement = m.get("placement") or LK.placement_of(vm, run)
    controls["platform_surfaces"] = {**(controls.get("platform_surfaces") or {}), "value": LK.surfaces(placement)}
    sh = {"meta": {"brand": run.get("brand"), "label": run.get("label") or out.name, "format": fmt, "app": app,
                   "placement": placement, **cv},
          "controls": controls, "cut_by": "edit_map.py (the clock, the mouths) — rendered by compose.py",
          "picture": picture, "voice": {"src": str(sound_wav), "start": 0, "volume_db": 0}, "voice_cuts": [],
          "music": None, "sfx": [],
          "captions": {"look": look_id, "words": words, "fixes": [], "accent": sorted(set(accent)), "timed_by": timed_by,
                       "spelling": []},
          "overlays": overlays, "layers": {"transitions": tr}, "keep_clear": keep_clear,
          "from_map": True, "total": m["total"]}
    sh["realism"] = RL.pick(fmt, vm=vm, run=run)
    return sh
