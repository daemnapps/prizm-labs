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


# FREE SPOT (the owner, 11 Oct 2026: "the scroll stopper and opening scenes … are covering up people's faces and
# stuff. You're not really thinking through how it needs to be designed like we did with the other ones.")
# The zones above are coarse: a headline knocked off a face went to the next band down, onto the chin, the
# hands and what she is holding. The hook and the captions now take the thumbnail's rule (thumbs.py, 4 Oct):
# read what is in the picture while the words are up — faces (with the jaw and neck under them), lips, hands,
# what draws the eye — and slide the layer to the height that covers the least of it, nearest its own zone.
COVER = {"lips": 30.0, "faces": 10.0, "hands": 4.0, "salient": 0.2}   # a face is never covered; a hand or the focus only when there is room
ITEMS = 6.0        # words or an item already on screen, under a caption (map_sheet keep_clear): below a face, above a hand
CROWD = 50.0       # another layer's words on screen at the same moment
DRIFT = 8.0        # per full frame-height moved away from the asked zone (keeps placement steady: words move for a face, not for a sleeve)
JAW = 0.5          # a face box runs on down this share of its height: chin, beard and neck
HEAD = 0.42        # a person whose face the reader missed (a small cartoon face): their head is the top of their body box


def heads(faces: list[dict], bodies: list[dict]) -> list[dict]:
    """Faces plus a head for every upper body with no face found inside it (boxes as shares or % — same units out)."""
    out = list(faces)
    for b in bodies or []:
        top = {"x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"] * HEAD}
        if not any(f["x"] < top["x"] + top["w"] and top["x"] < f["x"] + f["w"] and f["y"] < top["y"] + top["h"] and top["y"] < f["y"] + f["h"] for f in faces):
            out.append(top)
    return out
SPOT_PAD = 2.0     # % of the frame kept clear around a face, lips or hand


CAPTION_JAW = 0.0   # a caption may sit on the neck (edits-glow aims there, V13): the face box ends at the chin, SPOT_PAD keeps it clear


def _seen(sheet: dict, start: float, end: float, jaw: float = JAW) -> dict[str, list[tuple]]:
    """Everything the words must not cover while [start, end] is on screen, as (x0, y0, x1, y1) in %. `jaw`: how far
    below the chin a face box READ off the picture reaches — the full JAW (chin, beard, neck) for a headline,
    CAPTION_JAW for captions (Vision's box ends at the chin). Production's rough `subject_box` always keeps the full
    JAW: it is a guess at the person, not a measured face."""
    reach = jaw
    out: dict[str, list[tuple]] = {k: [] for k in COVER}
    for c in sheet.get("picture") or []:
        if c.get("kind") in PLATE_KINDS or not (c["start"] < end - 0.01 and start < c["start"] + c["duration"] - 0.01):
            continue
        for b in c.get("face_track") or []:
            if start - 0.25 <= b["t"] <= end + 0.25:
                out["faces"].append((b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"] * (1 + reach)))
        for r in c.get("scene_read") or []:
            if start - 0.6 <= r["t"] <= end + 0.6:
                for k in COVER:
                    for b in r.get(k) or []:
                        out[k].append((b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"] * (1 + reach if k == "faces" else 1)))
        if not c.get("face_track") and not c.get("scene_read") and subject_box(c):
            x0, y0, x1, y1 = subject_box(c)
            out["faces"].append((x0, y0, x1, y1 + (y1 - y0) * JAW))
    return out


def spot(asked: str, seen: dict[str, list[tuple]], taken: list[tuple] = (), floor: float | None = None,
         ceiling: float | None = None) -> tuple[dict, dict]:
    """The asked zone's box slid up or down to where it covers the least (between the top headline band and the
    bottom of the caption band — the frame the platforms leave free; with `floor`, no higher than that, so the
    captions always read under the headline; with `ceiling`, its bottom no lower than that, so the headline leaves
    the caption band to the captions). Returns the box and what it still covers."""
    Z = zones()[asked]
    y, hits = free_y(Z["x"], Z["x"] + Z["w"], Z["h"], Z["y"], seen, taken, rect("top-headline")[1], rect("caption-band")[3], floor, ceiling)
    return ({"x": Z["x"], "y": y, "w": Z["w"], "h": Z["h"], "align": Z.get("align", "center")}, hits)


def _look_row(sheet: dict) -> dict:
    look = (sheet.get("captions") or {}).get("look")
    if isinstance(look, dict):
        return look
    try:
        bank = json.loads((Path(__file__).resolve().parent.parent / "looks/bank.json").read_text())["looks"]
    except Exception:
        return {}
    return next((r for r in bank if r.get("id") == look), {})


def caption_h(look: dict, Z: dict) -> float:
    """How tall a caption line really is (% of the frame): one line of the look's type when its words fit across the
    zone, else two — never taller than the zone. A box the height of the whole zone pushed captions off items and
    faces they never touched."""
    size = float(look.get("size_px") or 60)
    fits = int(look.get("max_words") or 4) * 6 * size * 0.5 <= float(Z["w"]) * 10.8
    line = size * 1.08 / 19.2
    return round(min(float(Z["h"]), (1 if fits else 2) * line + size * 0.36 / 19.2 + 1.0), 2)


def _look_fixed(sheet: dict):
    """The caption look's `fixed_y_pct` (looks/bank.json), if it names one: the band's top, held the whole video."""
    return _look_row(sheet).get("fixed_y_pct")


def _look_ceiling(sheet: dict):
    """The caption look's `max_bottom_pct` (looks/bank.json), if it names one: the lowest its words' box may reach."""
    look = (sheet.get("captions") or {}).get("look")
    if isinstance(look, dict):
        return look.get("max_bottom_pct")
    try:
        bank = json.loads((Path(__file__).resolve().parent.parent / "looks/bank.json").read_text())["looks"]
    except Exception:
        return None
    return next((r.get("max_bottom_pct") for r in bank if r.get("id") == look), None)


def free_y(x0: float, x1: float, h: float, prefer: float, seen: dict[str, list[tuple]], taken: list[tuple] = (),
           lo: float = 19.0, hi: float = 72.0, floor: float | None = None, ceiling: float | None = None) -> tuple[float, dict]:
    """The top (% of the frame) for a box x0..x1 wide and h tall that covers the least of `seen`, nearest `prefer`.
    Shared by both renderers: compose (HyperFrames) through spot(), render_map (the cut-sheet lane) directly."""
    if ceiling is not None:
        hi = max(min(hi, ceiling), lo + h)
    if floor is not None:
        lo = min(max(lo, floor), hi - h)

    def cover(y, b, pad):
        w = min(x1, b[2]) - max(x0, b[0]); v = min(y + h, b[3] + pad) - max(y, b[1] - pad)
        return 0.0 if w <= 0 or v <= 0 else w * v / ((x1 - x0) * h)

    best = None
    y = lo
    while y + h <= hi + 1e-9:
        hits = {k: sum(cover(y, b, 0 if k in ("salient", "items") else SPOT_PAD) for b in bs) for k, bs in seen.items()}
        cost = sum(COVER.get(k, ITEMS) * v for k, v in hits.items()) + CROWD * sum(cover(y, t, 0.5) for t in taken) + DRIFT * abs(y - prefer) / 100
        if best is None or cost < best[0] - 1e-9:
            best = (cost, y, hits)
        y += 0.5
    _, y, hits = best
    return round(y, 1), {k: round(v, 3) for k, v in hits.items() if v > 0.001}


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
    held_boxes: list[tuple] = []  # ((x0, y0, x1, y1), start, end) — where a slid hook or caption actually sits

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
        row.pop("box", None)
        fixed = _look_fixed(sheet) if layer == "captions" else None
        # EVERY CAPTION LOOK HOLDS ITS OWN HEIGHT and moves only off a face or a mouth (V13; C1 settled 2026-10-21): the
        # look's `prefer_y_pct` (edits-glow: 38, the neck), else its zone's own top — the bottom band by default. No
        # dodging shot by shot when nothing is under it (the 10-12 rule), never on a face or a mouth when something is.
        prefer = (_look_row(sheet).get("prefer_y_pct", zones()[asked]["y"]) if fixed is None else None) if layer == "captions" else None
        if prefer is not None:   # aim for one height, but never on a face or a mouth (the owner 2026-10-20: "awareness of the subject")
            Z = dict(zones()[asked])
            Z["h"] = caption_h(_look_row(sheet), Z)
            seen = _seen(sheet, start, end, CAPTION_JAW)
            # words and items already on screen (the map's headline, badges, the product cut-outs): kept clear, but a
            # face or a mouth always outranks them (V13) — weighted between a hand and a face
            seen["items"] = [tuple(b["box"]) for b in sheet.get("keep_clear") or [] if b["start"] < end - 0.01 and start < b["end"] - 0.01]
            # the whole safe frame is open to a caption that must leave a face, words or an item (the strictest feed's
            # buttons below, the top bar above) — the look's own height is still where it aims (2026-10-21)
            # a paid placement's own feeds bound it too (Meta's Reels-ads zone keeps the bottom 35% clear — the CTA and
            # ad copy; verify 10-21 row 20): the sheet's platform_surfaces, never looser than the default floor
            floor_ = min(max(rect("caption-band")[3], safe_box()[3]), safe_box(sheet.get("controls"))[3])
            y, still = free_y(Z["x"], Z["x"] + Z["w"], Z["h"], prefer, seen, [],
                              rect("top-headline")[1], floor_, None, _look_ceiling(sheet))
            bx = {"x": Z["x"], "y": y, "w": Z["w"], "h": Z["h"], "align": Z.get("align", "center")}
            row["box"] = bx
            held_boxes.append(((bx["x"], bx["y"], bx["x"] + bx["w"], bx["y"] + bx["h"]), start, end))
            moved = abs(y - prefer) > 0.6
            z = min(zones(), key=lambda i: abs(centre(i)[1] - (y + Z["h"] / 2)) + (0 if zones()[i]["x"] == Z["x"] else 100)) if moved else asked
            held.append((z, start, end, f"{layer} {row.get('id') or ''}".strip()))
            row["zone"] = z
            if moved:
                worry = {k: v for k, v in still.items() if k != "salient"}
                row["zone_asked"] = asked
                moves.append({"layer": layer, "id": row.get("id"), "scene": scene, "asked": asked, "zone": z,
                              "why": f"`{asked}` slid to {y}% down (box {Z['h']}% tall) — aimed at {prefer}%, moved to stay off the "
                                     f"face and mouth" + (f"; still covers {worry}" if worry else "")})
            return
        if fixed is not None:   # a caption look that holds one band for the whole video (the owner 2026-10-20: "keep the captions in the same general range")
            Z = zones()[asked]
            bx = {"x": Z["x"], "y": fixed, "w": Z["w"], "h": Z["h"], "align": Z.get("align", "center")}
            row["box"] = bx
            held_boxes.append(((bx["x"], bx["y"], bx["x"] + bx["w"], bx["y"] + bx["h"]), start, end))
            held.append((z, start, end, f"{layer} {row.get('id') or ''}".strip()))
            row["zone"] = z
            return
        if layer in ("hook", "captions"):            # slid to the free spot, not just the next band (see FREE SPOT)
            boxes = [bx for bx, a, b in held_boxes if a < end - 0.01 and start < b - 0.01]
            hooks = [bx[3] for bx, a, b in held_boxes if a < end - 0.01 and start < b - 0.01] if layer == "captions" else []
            bx, still = spot(asked, _seen(sheet, start, end), boxes, floor=(max(hooks) + 0.5) if hooks else None,
                              # captions stay off while the hook is up (compose.py), so the hook may use the whole safe frame;
                              # a caption look may cap how low its words go (the owner 2026-10-20: words above what she holds, not on it)
                              ceiling=_look_ceiling(sheet) if layer == "captions" else None)
            near = min(zones(), key=lambda i: abs(centre(i)[1] - (bx["y"] + bx["h"] / 2)) + (0 if zones()[i]["x"] == bx["x"] else 100))
            z = near
            row["box"] = bx
            held_boxes.append(((bx["x"], bx["y"], bx["x"] + bx["w"], bx["y"] + bx["h"]), start, end))
            worry = {k: v for k, v in still.items() if k != "salient"}
            if abs(bx["y"] - zones()[asked]["y"]) > 0.6 or worry:
                why = (f"`{asked}` slid to {bx['y']}% down (box {bx['h']}% tall) — the spot that covers the least face, lips, hands and focus"
                       + (f"; still covers {worry}" if worry else ""))
            else:
                why = None
        held.append((z, start, end, f"{layer} {row.get('id') or ''}".strip()))
        row["zone"] = z
        if why:
            row["zone_asked"] = asked
            moves.append({"layer": layer, "id": row.get("id"), "scene": scene, "asked": asked, "zone": z, "why": why})

    for o in sheet.get("overlays") or []:
        if o.get("kind") == "hook" and not o.get("fixed"):   # a `fixed` row keeps the height its maker set (the edit map's)
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
            zmap[sc] = {"zone": row["zone"], **({"box": row["box"]} if row.get("box") else {}),
                        **({"why": moves[-1]["why"]} if row.get("zone_asked") else {})}
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
