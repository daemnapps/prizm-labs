#!/usr/bin/env python3
"""assemble.py — lays every element the kit carries onto the cut. It ASSEMBLES
and decides nothing (the owner, 2026-09-23: "the teardown names every element, the
brief carries it, production makes it, the edit only assembles").

    assemble(sheet, kit, controls, brand) -> sheet      run after the cut (auto or model), before the gate
    sound(sheet)                                        music duck lane · beat · room tone — re-run after any re-time

The shapes are tools/video-production/ELEMENTS.md. What this adds to the sheet:

    picture[i]  kind, section, priority, opens, claims and the kind's own data
                (card · screen · split · greenscreen · endcard), `lands_at` resolved
                from `lands_on` onto the final clock
    layers      {lower_thirds, annotations, platform_ui, transitions, disclaimers, icons}, each
                row timed on the final clock (start, duration) and placed (a zone from
                looks/placement.json, moved off the face — placement.py — or an annotation target)
    music       + duck {under_db, gap_db, points} · tempo_bpm · source_start (the end lands on a bar)
    sfx         `at` resolved from at_words | scene
    room_tone   [{id, src, start, duration, volume_db}] under every trimmed join and silent scene
    hooks · versions · grade · mix · name · compliance · unmade · elements: true

No brand name lives in this file; a brand's disclaimers come from
brands/<brand>/brand-identity/compliance.json, read-only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import placement as P

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
KIND_KEYS = ("card", "screen", "split", "greenscreen", "endcard")
TEXT_KINDS = ("card", "screen", "endcard")


def section_map(sheet: dict) -> list[dict]:
    """The swap map (the owner, 2026-09-23: every part of the edit names the doctrine
    section it represents, so sections can be swapped in variations). The picture
    in play order, merged into runs of one section: {section, start, end, scenes,
    words}. B-roll over a talking run belongs to the section of the scene it came
    from; the map follows the main picture (A-roll and B-roll that stands alone)."""
    pics = sorted(sheet.get("picture") or [], key=lambda c: (c["start"], 0 if c.get("roll") == "a" else 1))
    words = (sheet.get("captions") or {}).get("words") or []
    runs: list[dict] = []
    for c in pics:
        sec = c.get("section") or "unlabelled"
        s0, e0 = c["start"], c["start"] + c["duration"]
        if runs and runs[-1]["section"] == sec and s0 <= runs[-1]["end"] + 0.05:
            r = runs[-1]
            r["end"] = max(r["end"], e0)
            sc = c.get("scene") or c["id"]
            if sc not in r["scenes"]:
                r["scenes"].append(sc)
        elif runs and s0 < runs[-1]["end"] - 0.05:
            continue  # a layer over a run that already has its section
        else:
            runs.append({"section": sec, "start": round(s0, 3), "end": round(e0, 3), "scenes": [c.get("scene") or c["id"]]})
    for r in runs:
        r["end"] = round(r["end"], 3)
        r["words"] = " ".join(w["text"] for w in words if r["start"] <= w["start"] < r["end"])
    return runs


def workspace() -> Path:
    for d in HERE.parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return TOOL


def layer_style() -> dict:
    return json.loads((TOOL / "looks/layers.json").read_text())


def ui_style(row: dict) -> dict | None:
    """A platform-UI row's style (looks/platform_ui.json): the one it names, else its kind's default."""
    d = json.loads((TOOL / "looks/platform_ui.json").read_text())
    want = row.get("style") or (d["kinds"].get(row.get("kind")) or {}).get("default")
    return next((s for s in d["styles"] if s["id"] == want), None)


def norm(t: str) -> list[str]:
    return re.sub(r"[^a-z0-9' ]", " ", str(t).lower()).split()


def find_words(phrase: str, words: list[dict], lo: float = 0.0, hi: float = 1e9) -> tuple[float, float] | None:
    """Where a phrase is SAID on the final clock, looked for inside [lo, hi) first,
    then anywhere. None when it is not said at all — the gate names it."""
    p = norm(phrase)
    if not p:
        return None
    toks, of = [], []  # a word shown in the script's spelling may be several tokens ("five-star", "$29") — each keeps its word
    for k, w in enumerate(words):
        for t in norm(w["text"]) or [""]:
            toks.append(t); of.append(k)
    for bounded in (True, False):
        for i in range(len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p and (not bounded or lo - 0.05 <= words[of[i]]["start"] < hi):
                return words[of[i]]["start"], words[of[i + len(p) - 1]]["end"]
    return None


def owner_of(pic_id: str, kit_clips: list[dict]) -> dict | None:
    """The kit clip a picture item came from: its own id, or a part of it (`<id>-2`)."""
    for c in kit_clips:
        if pic_id == c["id"] or pic_id.startswith(c["id"] + "-"):
            return c
    return None


def scene_spans(sheet: dict) -> dict[str, tuple[float, float]]:
    spans: dict[str, list[float]] = {}
    for c in sheet.get("picture") or []:
        sc = c.get("scene") or c["id"]
        a, b = c["start"], c["start"] + c["duration"]
        s = spans.setdefault(sc, [a, b])
        s[0], s[1] = min(s[0], a), max(s[1], b)
    return {k: (round(v[0], 3), round(v[1], 3)) for k, v in spans.items()}


def speech_spans(words: list[dict], join: float = 0.6) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for w in words:
        if out and w["start"] - out[-1][1] <= join:
            out[-1][1] = max(out[-1][1], w["end"])
        else:
            out.append([w["start"], w["end"]])
    return [(round(a, 3), round(b, 3)) for a, b in out]


def hold_for(clip: dict) -> float:
    """How long a silent plate stays up when the plan gives no seconds: long enough
    to read its words twice-ish (looks/layers.json → card), never a number per video."""
    if clip.get("hold"):
        return float(clip["hold"])
    st = layer_style()["card"]
    d = next((clip.get(k) for k in TEXT_KINDS if clip.get(k)), {}) or {}
    text = " ".join(list(d.get("lines") or []) + list(d.get("offer_lines") or []) + [d.get("cta") or "", d.get("guarantee") or ""])
    return round(max(st["hold_min_s"], len(text.split()) * st["hold_s_per_word"] + 0.6), 2)


def db(v: float) -> float:
    return round(10 ** (v / 20.0), 4)


def _end(sheet: dict) -> float:
    ends = [c["start"] + c["duration"] for c in sheet.get("picture") or []]
    return round(max(ends), 3) if ends else 0.0


# ------------------------------------------------------------------ sound
def sound(sheet: dict) -> dict:
    """Music ducked under the voice and cut to the beat, and room tone under every
    trimmed join and every silent span. Everything here is read off the sheet's own
    structure, so a re-timed version (a hook version, a cutdown) gets it right too."""
    snd = (sheet.get("controls") or {}).get("sound") or {}
    end = _end(sheet)
    words = (sheet.get("captions") or {}).get("words") or []
    speech = speech_spans(words)
    music = sheet.get("music")
    if music:
        voice_db = snd.get("voice_db", 0)
        under = voice_db + snd.get("music_db", -18)
        gap = voice_db + snd.get("music_gap_db", -10)
        att, rel = snd.get("duck_attack_s", 0.08), snd.get("duck_release_s", 0.35)
        ducked: list[list[float]] = []  # speech, widened by attack and release, joined across gaps too short to breathe
        for a, b in speech:
            a, b = max(0.0, a - att), min(end, b + rel)
            if ducked and a - ducked[-1][1] < 0.8:
                ducked[-1][1] = max(ducked[-1][1], b)
            else:
                ducked.append([a, b])
        pts = [{"t": 0, "v": db(under if ducked and ducked[0][0] <= 0.001 else gap)}]
        for a, b in ducked:
            if a > 0.001:
                pts += [{"t": round(a, 3), "v": db(gap)}, {"t": round(min(end, a + att), 3), "v": db(under)}]
            if b < end - 0.001:
                pts += [{"t": round(max(a, b - rel), 3), "v": db(under)}, {"t": round(b, 3), "v": db(gap)}]
        clean = []
        for p in sorted(pts, key=lambda p: p["t"]):
            if clean and abs(clean[-1]["t"] - p["t"]) < 1e-3:
                clean[-1] = p
            else:
                clean.append(p)
        bpm = music.get("tempo_bpm")
        music.update({"start": 0, "duration": end, "volume_db": under,
                      "duck": {"under_db": voice_db - under, "gap_db": gap, "points": clean[:512]}})
        if bpm:
            bar = 4 * 60.0 / float(bpm)
            music["source_start"] = round((bar - end % bar) % bar, 3)  # the last frame lands on a bar line of the track
            music["beat_s"] = round(60.0 / float(bpm), 4)
    tone = sheet.get("room_tone_src")
    joins: list[float] = []
    pics = sorted(sheet.get("picture") or [], key=lambda c: c["start"])
    for x, y in zip(pics, pics[1:]):
        if x.get("talks") and y.get("talks") and x.get("src") == y.get("src") and abs(x["start"] + x["duration"] - y["start"]) < 0.05:
            joins.append(y["start"])  # a pause was trimmed here
    for v, w in zip(sheet.get("voice_cuts") or [], (sheet.get("voice_cuts") or [])[1:]):
        if v["src"] == w["src"] and abs(v["start"] + v["duration"] - w["start"]) < 0.05:
            joins.append(w["start"])
    pad = snd.get("room_tone_pad_s", 0.2)
    spans = [(max(0, j - pad), min(end, j + pad)) for j in joins]
    cursor = 0.0
    for a, b in speech + [(end, end)]:
        if a - cursor > 0.3:
            spans.append((cursor, a))  # nobody speaks: a silent scene, or the air before a line
        cursor = max(cursor, b)
    merged: list[list[float]] = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1] + 0.05:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    sheet["room_tone_needed"] = {"joins": len(joins), "spans": len(merged)}
    sheet["room_tone"] = [{"id": f"tone{i + 1}", "src": tone["src"], "start": round(a, 3), "duration": round(b - a, 3),
                           "source_start": 0, "volume_db": snd.get("room_tone_db", -30)}
                          for i, (a, b) in enumerate(merged) if b - a > 0.05] if tone else []
    return sheet


# ------------------------------------------------------------------ disclaimers
def compliance(brand: str, claims: list[str], platform: str | None, root: Path | None = None) -> dict:
    """brands/<brand>/brand-identity/compliance.json, read-only. Accepts {"disclaimers": [{claim, text, platforms}]}
    or {"claims": {claim: {text, platforms}}} or {claim: text}. Never created here."""
    import os
    base = root or (Path(os.environ["VIDEO_EDIT_WORKSPACE"]) if os.environ.get("VIDEO_EDIT_WORKSPACE") else workspace())  # tests and proofs point elsewhere; brands/ is never written
    f = base / "brands" / str(brand) / "brand-identity" / "compliance.json"
    out = {"file": str(f) if f.is_file() else None, "claims": sorted(set(claims)), "rows": {}, "unfilled": []}
    if not f.is_file():
        out["unfilled"] = out["claims"]
        return out
    d = json.loads(f.read_text())
    rows = []
    if isinstance(d.get("disclaimers"), list):
        rows = d["disclaimers"]
    elif isinstance(d.get("claims"), dict):
        rows = [{"claim": k, **(v if isinstance(v, dict) else {"text": v})} for k, v in d["claims"].items()]
    else:
        rows = [{"claim": k, "text": v} for k, v in d.items() if isinstance(v, str) and not k.startswith("_")]
    for c in out["claims"]:
        hit = [r for r in rows if r.get("claim") == c and r.get("text")
               and (not r.get("platforms") or not platform or platform in r["platforms"])]
        if hit:
            out["rows"][c] = hit[0]["text"]
        else:
            out["unfilled"].append(c)
    return out


# ------------------------------------------------------------------ the whole assembly
def assemble(sheet: dict, kit: dict, controls: dict, brand: str, root: Path | None = None) -> dict:
    kit_clips = kit.get("clips") or []
    style = layer_style()
    words = (sheet.get("captions") or {}).get("words") or []
    sheet["elements"] = bool({"layers", "hooks", "unmade", "versions"} & set(kit))
    sheet["unmade"] = list(kit.get("unmade") or [])

    # 1. every picture item carries its scene's kind and data
    for c in sheet.get("picture") or []:
        k = owner_of(c["id"], kit_clips)
        if not k:
            continue
        for f in ("kind", "section", "priority", "opens", "claims", "subject_box"):
            if k.get(f) is not None and f not in c:
                c[f] = k[f]
        for f in KIND_KEYS:
            if k.get(f):
                c[f] = json.loads(json.dumps(k[f]))
        if k.get("hold") is not None:
            c["hold"] = k["hold"]
    sheet["framework"] = kit.get("framework")
    sheet["sections"] = section_map(sheet)
    spans = scene_spans(sheet)
    for c in sheet.get("picture") or []:
        for f in TEXT_KINDS:
            d = c.get(f)
            if d is None:
                continue
            lo, hi = spans.get(c.get("scene") or c["id"], (c["start"], c["start"] + c["duration"]))
            hit = find_words(d.get("lands_on"), words, lo, hi) if d.get("lands_on") else None
            d["lands_at"] = round(hit[0], 3) if hit else round(c["start"] + 0.1, 3)
            if d.get("lands_on") and not hit:
                d["lands_on_unheard"] = True

    # 2. layers, each timed on the final clock
    L = dict(kit.get("layers") or {})
    layers: dict = {"lower_thirds": [], "annotations": [], "platform_ui": [], "transitions": [], "disclaimers": [], "icons": []}
    for i, r in enumerate(L.get("lower_thirds") or []):
        lo, hi = spans.get(r.get("scene"), (None, None))
        row = {"id": f"lt{i + 1}", **r, "zone": r.get("zone") or style["lower_third"]["zone"]}
        if lo is not None:
            row.update(start=round(lo + 0.25, 3), duration=round(min(style["lower_third"]["hold_s"], hi - lo - 0.25), 3))
        layers["lower_thirds"].append(row)
    anchors = style["annotation"]["anchors"]
    for i, r in enumerate(L.get("annotations") or []):
        lo, hi = spans.get(r.get("scene"), (None, None))
        row = {"id": f"an{i + 1}", **r}
        t = r.get("target")
        if isinstance(t, str) and t in anchors:
            row["place"] = anchors[t]
        elif isinstance(t, dict) and {"x_pct", "y_pct"} <= set(t):
            row["place"] = {"w_pct": 30, "h_pct": 14, **t}
        if lo is not None:
            hit = find_words(r.get("at_words", ""), words, lo, hi) if r.get("at_words") else None
            if hit:  # drawn on the word, gone when its scene is
                row["start"] = round(hit[0], 3)
                row["duration"] = round(min(hi - hit[0], max(style["annotation"]["hold_s"], hit[1] - hit[0] + 0.6)), 3)
            elif not r.get("at_words"):
                row["start"], row["duration"] = round(lo + 0.2, 3), round(min(style["annotation"]["hold_s"], hi - lo - 0.2), 3)
        layers["annotations"].append(row)
    for i, r in enumerate(L.get("platform_ui") or []):
        lo, hi = spans.get(r.get("scene"), (None, None))
        row = {"id": f"ui{i + 1}", **r}
        ui = ui_style(r)  # the style row (looks/platform_ui.json): named, or the kind's default
        if ui:
            row["style"] = ui["id"]
            row.setdefault("zone", ui["zone"])
        if lo is not None:
            row.update(start=round(lo, 3), duration=round(hi - lo, 3))
        layers["platform_ui"].append(row)
    layers["transitions"] = [dict(r) for r in L.get("transitions") or []]
    ist = style["icons"]
    for i, r in enumerate(L.get("icons") or []):  # icons, emoji, stickers and drawn elements (looks/icons.json), on their words
        lo, hi = spans.get(r.get("scene"), (None, None))
        row = {"id": f"ic{i + 1}", **r, "zone": r.get("zone") or ist["zone"], "size": r.get("size") or ist["size"]}
        if lo is not None:
            hit = find_words(r.get("at_words", ""), words, lo, hi) if r.get("at_words") else None
            if hit:
                row["start"] = round(hit[0], 3)
                row["duration"] = round(min(hi - hit[0], max(ist["hold_s"], hit[1] - hit[0] + 0.6)), 3)
            elif not r.get("at_words"):
                row["start"], row["duration"] = round(lo + 0.2, 3), round(min(ist["hold_s"], hi - lo - 0.2), 3)
        layers["icons"].append(row)

    claims = list(kit.get("claims") or [])
    by_scene: dict[str, list[str]] = {}
    for k in kit_clips:
        for c in k.get("claims") or []:
            claims.append(c)
            by_scene.setdefault(k.get("scene") or k["id"], []).append(c)
    comp = compliance(brand, claims, kit.get("platform"), root)
    sheet["compliance"] = comp
    end = _end(sheet)
    dsty = style["disclaimer"]
    for c, text in comp["rows"].items():
        scenes = [s for s, cs in by_scene.items() if c in cs]
        if scenes and c not in (kit.get("claims") or []):
            for s in scenes:
                lo, hi = spans.get(s, (0.0, end))
                layers["disclaimers"].append({"id": f"dc{len(layers['disclaimers']) + 1}", "claim": c, "scene": s, "text": text,
                                              "start": lo, "duration": round(max(dsty["min_s"], hi - lo), 3), "zone": dsty["zone"]})
        else:  # a claim the whole piece makes: on for the whole piece
            layers["disclaimers"].append({"id": f"dc{len(layers['disclaimers']) + 1}", "claim": c, "text": text,
                                          "start": 0.0, "duration": end, "zone": dsty["zone"]})
    for d in layers["disclaimers"]:
        d["duration"] = round(min(d["duration"], end - d["start"]), 3)
    sheet["layers"] = layers
    import follow as FL  # an annotation on the face/person follows it (face track, else subject_box); none → fixed, with a WARN
    sheet["follow_notes"] = FL.apply(sheet)
    P.place(sheet)  # every text layer in a zone, moved off the face where production marked one

    # 3. sound: each cue lands where the plan says, on the final clock
    for x in sheet.get("sfx") or []:
        if x.get("at") is not None:
            continue
        if x.get("at_words"):
            hit = find_words(x["at_words"], words, *(spans.get(x.get("scene"), (0.0, 1e9))))
            if hit:
                x["at"] = round(hit[0], 3)
        elif x.get("scene") in spans:
            x["at"] = spans[x["scene"]][0]
    if kit.get("music") and sheet.get("music"):
        sheet["music"].update({k: kit["music"].get(k) for k in ("bank_id", "tempo_bpm", "energy", "mood") if kit["music"].get(k) is not None})
    tone = (kit.get("room_tone") or [None])[0]
    sheet["room_tone_src"] = tone
    sound(sheet)

    # 4. versions, the look over the piece, the mix, the name
    hooks = [dict(h) for h in kit.get("hooks") or []]
    control = next((o for o in sheet.get("overlays") or [] if o.get("kind") == "hook"), None)
    if control and not any(h.get("text") == control.get("text") for h in hooks):
        hooks.insert(0, {"id": "control", "text": control["text"]})
    sheet["hooks"] = hooks
    v = dict(kit.get("versions") or {})
    sheet["versions"] = {"hooks": bool(hooks),
                         "cutdowns": v.get("cutdowns", (controls.get("cutdowns") or {}).get("value", [15, 30, 60])),
                         "ratios": ["9x16"],  # 9:16 only (the owner, 2026-09-23); a plan asking for others is ignored, never rendered
                         "cover": True}
    sheet["grade"] = kit.get("grade") or (controls.get("grade") or {}).get("value", "none")
    sheet["mix"] = {"lufs": (controls.get("mix") or {}).get("lufs", -14), "true_peak_db": (controls.get("mix") or {}).get("true_peak_db", -1)}
    sheet["name"] = dict(kit.get("name") or {})
    return sheet
