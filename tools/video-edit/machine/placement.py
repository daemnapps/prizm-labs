#!/usr/bin/env python3
"""placement.py — where every text layer sits: a named zone (looks/placement.json)
inside the content 4:5 band and clear of the platforms' buttons, moved off the face
when production marks where the person is.

    zones() · rect(zone_id) · safe_box(controls) · zone_clear(zone, box)
    subject_box(clip)            the union of a clip's `subject_box` (one box, or one per frame)
    choose(asked, faces, taken)  -> (zone, why | None)   the nearest free zone when `asked` covers a face
                                 or another layer already holds that part of the frame then
    place(sheet)                 sets `zone` on every text layer, `captions.zones` per scene,
                                 records every move in sheet["placement"] and every
                                 face-blind scene in sheet["face_blind"]

A subject box is {x, y, w, h} in % of the frame (top-left origin), per scene in
plan.json (`subject_box`), or a list of them per frame ([{t, x, y, w, h}]) — the
edit takes their union, so text never crosses where the face goes at any moment.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
PLATE_KINDS = ("card", "screen", "endcard", "split")  # a plate or a split has no presenter's face to avoid


def settings() -> dict:
    return json.loads((TOOL / "looks/placement.json").read_text())


def zones() -> dict[str, dict]:
    return {z["id"]: z for z in settings()["zones"]}


def rect(z) -> tuple[float, float, float, float]:
    z = zones()[z] if isinstance(z, str) else z
    return z["x"], z["y"], z["x"] + z["w"], z["y"] + z["h"]


def centre(z) -> tuple[float, float]:
    x0, y0, x1, y1 = rect(z)
    return (x0 + x1) / 2, (y0 + y1) / 2


def safe_box(controls: dict | None = None) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) in % — the strictest of the surfaces this piece runs on,
    and never outside the content 4:5 band."""
    d = json.loads((TOOL / "machine/defaults.json").read_text())
    c = controls or {}
    sz = c.get("safe_zones") or d.get("safe_zones") or {}
    surf = sz.get("surfaces") or {}
    names = (c.get("platform_surfaces") or d.get("platform_surfaces") or {}).get("value") or list(surf)
    rows = [surf[n] for n in names if n in surf] or [{"top_pct": 12, "bottom_pct": 25, "left_pct": 6, "right_pct": 6}]
    c45 = sz.get("content_4x5") or {"top_pct": 14.84, "bottom_pct": 14.84}
    top = max([r["top_pct"] for r in rows] + [c45["top_pct"]])
    bottom = max([r["bottom_pct"] for r in rows] + [c45["bottom_pct"]])
    return max(r["left_pct"] for r in rows), top, 100 - max(r["right_pct"] for r in rows), 100 - bottom


def zone_clear(z, box) -> bool:
    x0, y0, x1, y1 = rect(z)
    L, T, R, B = box
    return x0 >= L - 0.01 and y0 >= T - 0.01 and x1 <= R + 0.01 and y1 <= B + 0.01


def subject_box(clip: dict) -> tuple[float, float, float, float] | None:
    sb = clip.get("subject_box")
    if not sb:
        return None
    boxes = sb if isinstance(sb, list) else [sb]
    boxes = [b for b in boxes if isinstance(b, dict) and {"x", "y", "w", "h"} <= set(b)]
    if not boxes:
        return None
    return (min(b["x"] for b in boxes), min(b["y"] for b in boxes),
            max(b["x"] + b["w"] for b in boxes), max(b["y"] + b["h"] for b in boxes))


def overlap(z, face) -> float:
    """How much of the zone the face covers (0..1)."""
    x0, y0, x1, y1 = rect(z)
    fx0, fy0, fx1, fy1 = face
    w, h = min(x1, fx1) - max(x0, fx0), min(y1, fy1) - max(y0, fy0)
    return 0.0 if w <= 0 or h <= 0 else (w * h) / ((x1 - x0) * (y1 - y0))


def crosses(a, b) -> bool:
    """Two zones clash when they share more than `crowd_overlap` of the smaller one."""
    x0, y0, x1, y1 = rect(a)
    u0, v0, u1, v1 = rect(b)
    w, h = min(x1, u1) - max(x0, u0), min(y1, v1) - max(y0, v0)
    if w <= 0.01 or h <= 0.01:
        return False
    small = min((x1 - x0) * (y1 - y0), (u1 - u0) * (v1 - v0))
    return w * h / small >= settings().get("crowd_overlap", 0.4)


def choose(asked: str, faces: list[tuple], taken: list[tuple] = ()) -> tuple[str, str | None]:
    """Keep `asked` unless a face covers it or another layer already holds that part of the
    frame at that moment; then the nearest zone in its `moves_to` list that is free of both.
    `taken` is [(zone, what)] for layers on screen at the same time. The reason says what happened."""
    Z = zones()
    lim = settings().get("face_overlap", 0.15)
    hit = [f for f in faces if overlap(asked, f) >= lim]
    busy = [w for z, w in taken if crosses(asked, z)]
    if not hit and not busy:
        return asked, None
    cx, cy = centre(asked)
    free = lambda z: all(overlap(z, f) < lim for f in faces) and not any(crosses(z, t) for t, _ in taken)  # noqa: E731
    options = [z for z in Z[asked].get("moves_to") or [] if z in Z and free(z)]
    because = (f"would cover the face ({round(overlap(asked, hit[0]) * 100)}% of the zone)" if hit else f"is already holding {busy[0]}")
    if not options:
        return asked, f"`{asked}` {because} and no free zone is listed for it — left in place, check the frame"
    best = min(options, key=lambda z: ((centre(z)[0] - cx) ** 2 + (centre(z)[1] - cy) ** 2, (Z[asked]["moves_to"]).index(z)))
    return best, f"`{asked}` {because} — moved to `{best}`, the nearest free zone"


def presenter_rect(layout: str, src_aspect: float | None = None, W: int = 1080, H: int = 1920) -> dict:
    """Where a greenscreen presenter is DRAWN on the frame (the same numbers compose.py's CSS
    uses, looks/layers.json → greenscreen): the element's box and the source picture inside
    it, in px. `cutout` = full width, `cutout_height_pct` tall, sitting `cutout_bottom_pct` up,
    contained and bottom-centred; `pip` = a 9:13 card `pip_width_pct` wide, cover-cropped."""
    g = json.loads((TOOL / "looks/layers.json").read_text())["greenscreen"]
    sa = src_aspect or W / H
    if layout == "cutout":
        bw, bh = W, H * g["cutout_height_pct"] / 100
        bx, by = 0.0, H - H * g["cutout_bottom_pct"] / 100 - bh
        s = min(bw / sa, bh)  # contain: the displayed height
        dw, dh = s * sa, s
        ox, oy = bx + (bw - dw) / 2, by + bh - dh  # object-position 50% 100%
    else:
        bw = W * g["pip_width_pct"] / 100
        bh = bw * 13 / 9
        bx, by = W - W * g["pip_right_pct"] / 100 - bw, H - H * g["pip_bottom_pct"] / 100 - bh
        s = max(bw / sa, bh)  # cover
        dw, dh = s * sa, s
        ox, oy = bx + (bw - dw) / 2, by + (bh - dh) / 2
    return {"box": (bx, by, bx + bw, by + bh), "drawn": (ox, oy, dw, dh), "W": W, "H": H}


def to_frame(box: dict, rect: dict) -> dict | None:
    """A box in % of the SOURCE picture → % of the finished frame, clipped to where the
    presenter is drawn. None when it falls outside (cropped away)."""
    ox, oy, dw, dh = rect["drawn"]
    bx0, by0, bx1, by1 = rect["box"]
    W, H = rect["W"], rect["H"]
    x0 = max(bx0, ox + box["x"] / 100 * dw)
    y0 = max(by0, oy + box["y"] / 100 * dh)
    x1 = min(bx1, ox + (box["x"] + box["w"]) / 100 * dw)
    y1 = min(by1, oy + (box["y"] + box["h"]) / 100 * dh)
    if x1 <= x0 or y1 <= y0:
        return None
    return {**box, "x": round(100 * x0 / W, 2), "y": round(100 * y0 / H, 2), "w": round(100 * (x1 - x0) / W, 2), "h": round(100 * (y1 - y0) / H, 2)}


def ui_zone(row: dict) -> str | None:
    """A platform-UI row's zone when it names none: its style's (looks/platform_ui.json)."""
    d = json.loads((TOOL / "looks/platform_ui.json").read_text())
    want = row.get("style") or (d["kinds"].get(row.get("kind")) or {}).get("default")
    return next((x["zone"] for x in d["styles"] if x["id"] == want), None)


def _scene_of(c: dict) -> str:
    return c.get("scene") or c["id"]


def tracked_box(clip: dict, start: float | None = None, end: float | None = None) -> tuple | None | bool:
    """The union of the face boxes MediaPipe saw in this clip (faces.py → `face_track`,
    t on the final clock) while [start, end] is on screen. False = no track on this clip
    (fall back to subject_box); None = tracked, and no face in that window."""
    ft = clip.get("face_track")
    if not ft:  # never tracked, or the tracker saw no face anywhere in the clip: production's subject_box (or face-blind) stands
        return False
    lo = clip["start"] if start is None else max(start, clip["start"])
    hi = clip["start"] + clip["duration"] if end is None else min(end, clip["start"] + clip["duration"])
    pad = 1.0 / max(1.0, float(clip.get("face_track_fps") or 5.0))  # a box stands for the frames either side of it
    boxes = [b for b in ft if lo - pad <= b["t"] <= hi + pad]
    if not boxes:
        return None
    return (min(b["x"] for b in boxes), min(b["y"] for b in boxes),
            max(b["x"] + b["w"] for b in boxes), max(b["y"] + b["h"] for b in boxes))


def faces_in(sheet: dict, scene: str | None = None, start: float | None = None, end: float | None = None) -> tuple[list[tuple], list[str]]:
    """The face boxes under a layer — by its scene, or by the time it is on screen —
    and the scenes under it that carry a presenter but no subject box (face-blind).
    Per-frame tracking (faces.py) wins over production's one subject_box: only the
    boxes seen while the layer is up count."""
    boxes, blind = [], []
    for c in sheet.get("picture") or []:
        on = (_scene_of(c) == scene) if scene else (start is not None and c["start"] < end - 0.01 and start < c["start"] + c["duration"] - 0.01)
        if not on or c.get("kind") in PLATE_KINDS or c.get("still"):
            continue
        tb = tracked_box(c, None if scene else start, None if scene else end)
        if tb is not False:
            if tb:
                boxes.append(tb)
            continue
        b = subject_box(c)
        if b:
            boxes.append(b)
        elif _scene_of(c) not in blind:
            blind.append(_scene_of(c))
    return boxes, blind


def place(sheet: dict, defaults: dict | None = None) -> dict:
    """Give every text layer a zone and move it off the face and off words already on
    screen. Placed in order of importance: hook, captions, platform UI, lower thirds,
    icons (disclaimers keep the fine-print strip). Records every move."""
    S = settings()
    dz = dict(S.get("defaults") or {}, **(defaults or {}))
    moves, blind = [], []
    held: list[tuple] = []  # (zone, start, end, what) — the parts of the frame already holding words

    def put(row: dict, layer: str, asked: str, scene=None, start=None, end=None):
        faces, bl = faces_in(sheet, scene, start, end)
        for b in bl:
            if b not in blind:
                blind.append(b)
        if scene is not None:
            t = [(c["start"], c["start"] + c["duration"]) for c in sheet.get("picture") or [] if _scene_of(c) == scene]
            start, end = (min(a for a, _ in t), max(b for _, b in t)) if t else (0.0, 0.0)
        taken = [(z, w) for z, a, b, w in held if a < end - 0.01 and start < b - 0.01]
        z, why = choose(asked, faces, taken)
        held.append((z, start, end, f"{layer} {row.get('id') or ''}".strip()))
        row["zone"] = z
        if why:
            row["zone_asked"] = asked
            moves.append({"layer": layer, "id": row.get("id"), "scene": scene, "asked": asked, "zone": z, "why": why})

    for o in sheet.get("overlays") or []:
        if o.get("kind") == "hook":
            put(o, "hook", o.get("zone_asked") or o.get("zone") or dz["hook"], start=o.get("start", 0), end=o.get("start", 0) + o.get("duration", 0))
    caps = sheet.get("captions") or {}
    if caps.get("words"):
        look = caps.get("look")
        if isinstance(look, str):
            look = next((r for r in json.loads((TOOL / "looks/bank.json").read_text())["looks"] if r["id"] == look), {})
        asked = caps.get("zone") or (look or {}).get("zone") or dz["captions"]
        zmap = {}
        for c in sheet.get("picture") or []:
            sc = _scene_of(c)
            if sc in zmap or any(x.get("kind") in ("card", "screen", "endcard") for x in sheet["picture"] if _scene_of(x) == sc):
                continue  # a plate's own words are on screen — no captions there, so they hold no zone
            row = {"id": f"captions:{sc}"}
            put(row, "captions", asked, scene=sc)
            zmap[sc] = {"zone": row["zone"], **({"why": moves[-1]["why"]} if row.get("zone_asked") else {})}
        caps["zones"] = zmap
    L = sheet.get("layers") or {}
    for k in ("lower_thirds", "platform_ui", "icons"):
        for r in L.get(k) or []:
            if r.get("start") is None:
                continue
            asked = r.get("zone_asked") or r.get("zone") or (ui_zone(r) if k == "platform_ui" else None) or dz.get(k, "center")
            put(r, k, asked, start=r["start"], end=r["start"] + r["duration"])
    for r in L.get("disclaimers") or []:
        r.setdefault("zone", dz["disclaimers"])
    sheet["placement"] = moves
    sheet["face_blind"] = blind
    return sheet
