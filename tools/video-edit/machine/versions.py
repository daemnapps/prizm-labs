#!/usr/bin/env python3
"""versions.py — every version from ONE cut sheet: parts swapped, never re-made
(ELEMENTS.md §4). Pure functions over the sheet; nothing here renders.

    plan(sheet)                  -> [{id, hook, order, length, dropped}]   what `render` makes
    variant(sheet, spec)         -> a new sheet: the hook swapped, the scenes re-timed
    carriers(sheet)              -> the scenes that carry the clock, in play order
    cutdown(sheet, seconds)      -> (order, dropped, total, fits)
    file_name(sheet, ratio, n, batch) -> (name, note)   via components/naming

What it makes (the owner, 2026-09-23): one video per hook on the same body, the 15/30/60
cutdowns by priority, a cover per hook — 9:16 ONLY ("I do not want 4:5 or 1:1 videos
at all"). Each scene's `section` (the doctrine's own id, marketing-doctrine/frameworks.json)
is carried and readable on the sheet; swapping sections is a separate build and is not
rendered here.

A version never cuts a line mid-scene: whole carrier scenes come out or move, and
everything laid over a scene (B-roll that covers it, a card's words, a lower
third, a sound cue) moves with it.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assemble as A  # noqa: E402

RATIO = "9x16"  # the only ratio made (the owner, 2026-09-23)
DEFAULT_PRIORITY = 5  # a scene the brief gave no priority comes out before any it ranked


def carriers(sheet: dict) -> list[dict]:
    """Scenes that carry the clock. A scene laid wholly inside another (B-roll that
    covers someone's words) rides with the one under it."""
    spans = A.scene_spans(sheet)
    meta = {}
    for c in sheet.get("picture") or []:
        m = meta.setdefault(c.get("scene") or c["id"], {})
        for f in ("priority", "section", "opens", "kind"):
            if c.get(f) is not None and f not in m:
                m[f] = c[f]
    items = sorted(spans.items(), key=lambda kv: (kv[1][0], -kv[1][1]))
    out: list[dict] = []
    for sc, (a, b) in items:
        host = next((o for o in out if o["start"] - 0.05 <= a and b <= o["end"] + 0.05 and not (abs(o["start"] - a) < 0.05 and abs(o["end"] - b) < 0.05)), None)
        if host:
            host["riders"].append(sc)
            continue
        out.append({"scene": sc, "start": a, "end": b, "riders": [], **meta.get(sc, {})})
    return out


def total(cs: list[dict]) -> float:
    return round(sum(c["end"] - c["start"] for c in cs), 3)


def cutdown(sheet: dict, seconds: float) -> tuple[list[str], list[str], float, bool]:
    """Take the lowest-priority whole scenes out first (latest first on a tie) until the
    piece fits. Priority 1 and the opener never come out."""
    cs = carriers(sheet)
    keep = list(cs)
    first = cs[0]["scene"] if cs else None
    cand = [c for c in cs if c.get("priority") != 1 and not c.get("opens") and c["scene"] != first]
    cand.sort(key=lambda c: (-(c.get("priority") or DEFAULT_PRIORITY), -c["start"]))
    dropped = []
    for c in cand:
        if total(keep) <= seconds + 0.01:
            break
        keep.remove(c)
        dropped.append(c["scene"])
    return [c["scene"] for c in keep], dropped, total(keep), total(keep) <= seconds + 0.01


def retime(sheet: dict, order: list[str]) -> dict:
    """A new sheet with the carrier scenes in `order`, each moved whole with
    everything that rides on it. Music, ducking and room tone are laid again."""
    cs = {c["scene"]: c for c in carriers(sheet)}
    s = copy.deepcopy(sheet)
    words = (sheet.get("captions") or {}).get("words") or []
    voice = sheet.get("voice")
    new = {k: [] for k in ("picture", "voice_cuts", "words", "sfx", "overlays", "room")}
    layers = {k: [] for k in ("lower_thirds", "annotations", "platform_ui", "transitions", "disclaimers", "icons")}
    t = 0.0
    for sc in order:
        c = cs[sc]
        a, b = c["start"], c["end"]
        members = {sc, *c["riders"]}
        shift = t - a

        def inside(x0: float) -> bool:
            return a - 0.01 <= x0 < b - 0.01

        for p in sheet.get("picture") or []:
            if (p.get("scene") or p["id"]) in members:
                q = copy.deepcopy(p); q["start"] = round(p["start"] + shift, 3)
                for k in A.TEXT_KINDS:
                    if q.get(k) and q[k].get("lands_at") is not None:
                        q[k]["lands_at"] = round(q[k]["lands_at"] + shift, 3)
                new["picture"].append(q)
        for v in sheet.get("voice_cuts") or []:
            if inside(v["start"]):
                q = dict(v); q["start"] = round(v["start"] + shift, 3); new["voice_cuts"].append(q)
        if voice:  # a voiceover piece: its one track becomes one cut per scene, so it moves with its pictures
            new["voice_cuts"].append({"id": f"vo-{sc}", "src": voice["src"], "start": round(t, 3), "duration": round(b - a, 3),
                                      "source_start": round(a - voice.get("start", 0), 3), "volume_db": voice.get("volume_db", 0)})
        new["words"] += [{**w, "start": round(w["start"] + shift, 3), "end": round(w["end"] + shift, 3)} for w in words if inside(w["start"])]
        new["sfx"] += [{**x, "at": round(x["at"] + shift, 3)} for x in sheet.get("sfx") or [] if x.get("at") is not None and inside(x["at"])]
        for k in ("lower_thirds", "annotations", "platform_ui", "disclaimers", "icons"):
            for r in (sheet.get("layers") or {}).get(k) or []:
                if r.get("start") is None:
                    continue
                if r.get("scene") in members or (not r.get("scene") and k != "disclaimers" and inside(r["start"])):
                    layers[k].append({**r, "start": round(r["start"] + shift, 3)})
        t += b - a
    end = round(t, 3)
    for r in (sheet.get("layers") or {}).get("disclaimers") or []:
        if not r.get("scene"):  # a claim the whole piece makes
            layers["disclaimers"].append({**r, "start": 0.0, "duration": end})
    kept = set(order)
    layers["transitions"] = [r for r in (sheet.get("layers") or {}).get("transitions") or [] if r.get("after_scene") in kept and r["after_scene"] != order[-1]]
    first = cs[order[0]]
    for o in sheet.get("overlays") or []:
        if o.get("kind") == "hook":  # the hook lives on whatever opens this version
            new["overlays"].append({**o, "start": 0, "duration": round(first["end"] - first["start"], 3)})
        elif o.get("start") is not None:
            for sc in order:
                c = cs[sc]
                if c["start"] - 0.01 <= o["start"] < c["end"] - 0.01:
                    off = sum(cs[x]["end"] - cs[x]["start"] for x in order[:order.index(sc)])
                    new["overlays"].append({**o, "start": round(o["start"] - c["start"] + off, 3)})
    s.update({"picture": new["picture"], "voice_cuts": new["voice_cuts"], "voice": None if voice else s.get("voice"),
              "sfx": new["sfx"], "overlays": new["overlays"], "layers": {**(sheet.get("layers") or {}), **layers}})
    s["captions"] = {**(sheet.get("captions") or {}), "words": new["words"]}
    A.sound(s)
    A.P.place(s)  # a new opener may put a face where the hook sat — placement runs again on the new order
    return s


def plan(sheet: dict) -> list[dict]:
    """What `render` makes: every hook on the full body, then each cutdown shorter
    than the piece on the control hook. 9:16 only; no section swaps (a separate build)."""
    v = sheet.get("versions") or {}
    hooks = sheet.get("hooks") or [None]
    cs = carriers(sheet)
    full = [c["scene"] for c in cs]
    out = []
    for h in hooks:
        hid = (h or {}).get("id") or "h1"
        order = list(full)
        op = (h or {}).get("opener_scene")
        if op and op in order and order[0] != op:
            order = [op] + [x for x in order if x != op]
        out.append({"id": f"{hid}-full", "hook": h, "order": order, "length": "full", "dropped": []})
    control = hooks[0]
    for n in v.get("cutdowns") or []:
        if total(cs) <= n + 0.01:
            continue  # already shorter than the cutdown — nothing to take out
        order, dropped, tot, fits = cutdown(sheet, n)
        out.append({"id": f"{(control or {}).get('id', 'h1')}-{n}s", "hook": control, "order": order, "length": f"{n}s",
                    "dropped": dropped, "seconds": tot, "fits": fits})
    return out


def variant(sheet: dict, spec: dict) -> dict:
    s = retime(sheet, spec["order"])
    h = spec.get("hook")
    if h:
        for o in s.get("overlays") or []:
            if o.get("kind") == "hook":
                o["text"] = h["text"]
    s["version"] = {k: spec.get(k) for k in ("id", "length", "dropped", "seconds", "fits")} | {"hook": (h or {}).get("id")}
    return s


def file_name(sheet: dict, ratio: str, n: int, batch: str | None = None) -> tuple[str, str | None]:
    """The naming convention's ad name + asset number (components/naming, read-only use).
    A field the plan did not give is never invented: the file gets a plain name and the
    note says which fields are missing."""
    meta = sheet.get("meta") or {}
    f = dict(sheet.get("name") or {})
    need = ["product", "talent", "avatar", "problem", "angle", "concept", "format", "brief"]
    f.setdefault("format", meta.get("format"))
    miss = [k for k in need if not f.get(k)]
    ver = (sheet.get("version") or {}).get("id") or "full"
    plain = f"{meta.get('label')}-{ver}-{ratio}"
    if miss:
        return plain, f"not named to the convention — the plan gives no {', '.join(miss)}"
    try:
        for d in HERE.parents:
            if (d / "components" / "naming" / "names.py").is_file():
                sys.path.insert(0, str(d / "components" / "naming"))
                break
        import names as N
        ad = N.ad_name(meta.get("brand"), f["product"], "video", f.get("source") or "ai", f["talent"], f["avatar"], f["problem"],
                       f["angle"], f["concept"], f["format"], f["brief"], ratio, batch or f.get("batch") or N.batch_id())
        return N.asset_name(ad, n), None
    except SystemExit as e:
        return plain, f"not named — {e}"
    except Exception as e:  # naming unreadable: say so, never guess
        return plain, f"not named — {type(e).__name__}: {e}"
