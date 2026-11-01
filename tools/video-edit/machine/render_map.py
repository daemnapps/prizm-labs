#!/usr/bin/env python3
"""render_map.py — the finished video from an edit map: 9:16, 1080x1920, 30 fps, one file per version.
Local and free (ffmpeg + HyperFrames); nothing is sent anywhere.

    python3 render_map.py <video-production-run> [--out <edit run dir>] [--only control,<hook>] [--draft]

Reads <out>/edit-map.json (the control) and every <out>/edit-map-<hook>.json (one version per hook opening)
and writes <out>/renders/<version>.mp4 + <version>.json (what went in) and <version>.clean.mp4 (the same picture
and sound with no words on it — what the lips and the audit are measured on). What is on screen is exactly what
the timeline page plays and the sweep checked:
  picture  each piece of each clip from its in-point, slowed where the map says, the close-up crop applied; B-roll
           and same-room inserts on top for their windows; cards held; the item cut-outs and stickers laid on
           (ffmpeg here)
  words    NONE drawn here since 2026-10-21 (video system sync, C13: one edit path, compose.py the only renderer):
           map_sheet.py turns the map into a cut sheet and compose.py draws the captions (the look picked by
           format, looks/bank.json), the headline, the option pops, the badges and the end card's words, the
           transitions between shots and the realism finish
  sound    every line's own sound where the map lays it (the clip's span, an own track, a sound, a patch with
           the clip muted under it), the music bed ducked under the voices and up in the pauses — only when the
           ad has one — room tone only when the swipe has room sound (V14), then mastered to -14 LUFS integrated,
           -1 dBTP (Meta / Instagram feed loudness)
"""
from __future__ import annotations

import argparse
import json
import time
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FPS = 30
W, H = 1080, 1920
MIN_SHOT = 0.5          # seconds: nothing on screen shorter (no flashes)
STILL_SHARE = 0.4       # a shot with more still frames than this reads as too still (realism: digital-micro-shake)
PUSH = 0.06             # how far a push goes over a shot (6%) — only where the format turns pushes on (looks.moves)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listen as LI  # noqa: E402  (the same sound mix the clean pass checks)
import looks as LK  # noqa: E402  (one look registry, one loudness table — E6, E27)

LOOKS = json.loads((HERE.parent / "looks" / "edit-looks.json").read_text())   # the TEXT looks (thumbnails read them)
SOUND = LK.sound()
MIX = {"loudness_lufs": SOUND["lufs"], "true_peak_db": SOUND["true_peak_db"]}
ROOM_DB = SOUND["room_tone_db"]   # room air — only when the swipe or brief calls for room sound (V14)


# THUMBNAIL TYPE ONLY: font / _wrap / draw_block draw a thumbnail's words on a still (thumbs.py). No word of the
# video itself is drawn in this file since 2026-10-21 — compose.py draws them (C13).
def font(size: int, weight: str = "semibold"):
    for f in LOOKS["fonts"].get(weight) or LOOKS["fonts"]["semibold"]:
        try:
            ft = ImageFont.truetype(f, size)
            try:
                ft.set_variation_by_name({"semibold": "Semibold", "bold": "Bold", "heavy": "Heavy"}.get(weight, "Semibold"))
            except Exception:
                pass
            return ft
        except Exception:
            continue
    return ImageFont.load_default()


def look(kind: str, name: str | None = None) -> dict:
    """A text look by id (looks/edit-looks.json) — the ad names it, else the default for its kind."""
    lk = LOOKS["text"].get(name or "") or LOOKS["text"][LOOKS["defaults"][kind]]
    return lk


def caption_look(name: str | None = None) -> dict:
    """The caption look row (looks/bank.json — the one registry since 2026-10-21, E6), else the default look."""
    return LK.caption(name) or LK.caption(LK.pick_caption())


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def dur(f) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout or 0)


# ------------------------------------------------------------------ picture

def flatten(m: dict) -> list[dict]:
    """The one thing on screen at every moment: B-roll / inserts win over the picture for their windows."""
    tops = sorted(m.get("broll") or [], key=lambda r: r["a"])
    pieces = sorted(m["picture"], key=lambda p: p["a"])
    out = []
    for p in pieces:
        cuts = [(p["a"], p["b"])]
        for r in tops:
            nxt = []
            for a, b in cuts:
                if r["b"] <= a or r["a"] >= b:
                    nxt.append((a, b)); continue
                if r["a"] > a:
                    nxt.append((a, r["a"]))
                if r["b"] < b:
                    nxt.append((r["b"], b))
            cuts = nxt
        for a, b in cuts:
            if b - a > 1e-3:
                out.append({**p, "a": a, "b": b, "in": p.get("in", 0) + (a - p["a"]) * p.get("speed", 1)})
    for r in tops:
        out.append({"a": r["a"], "b": r["b"], "kind": "insert" if r.get("insert") else "broll", "clip": r.get("clip"),
                    "file": r.get("file"), "in": r.get("in", 0), "speed": r.get("speed", 1),
                    **({"clean": r["clean"]} if r.get("clean") else {})})
    out.sort(key=lambda s: (s["a"], s["b"]))
    return no_flash(no_overlap(out, m.get("total") or max(x["b"] for x in out)))


def _shift_in(s: dict, d: float) -> None:
    """Start segment `s` `d` seconds later on the timeline, its source moving with it (lips stay on their words)."""
    s["a"] += d
    s["in"] = s.get("in", 0) + d * float(s.get("speed") or 1)


def no_overlap(segs: list[dict], total: float) -> list[dict]:
    """One segment at a time, end to end. A piece that starts before the last one ends (a line's lead-in pad)
    starts where the last ends, its source moved on by the same amount — so every frame stays at its own time.
    (4 Oct 2026: overlapping pads were rendered twice and the picture slid ~0.4 s behind the voice by the pitch.)"""
    out, t = [], 0.0
    for s in segs:
        s = dict(s)
        if s["a"] < t:
            _shift_in(s, t - s["a"])
        s["b"] = min(s["b"], total)
        if s["b"] - s["a"] > 1e-3:
            out.append(s); t = s["b"]
    return out


def no_flash(segs: list[dict]) -> list[dict]:
    """No shot shorter than MIN_SHOT (the swipe's shortest is 0.6 s): a sliver's time goes to the B-roll beside it,
    else the shot before it carries on (its source simply plays on), else the shot after starts earlier."""
    segs = [dict(s) for s in segs]
    i = 0
    while i < len(segs):
        s = segs[i]
        if s["b"] - s["a"] >= MIN_SHOT or len(segs) == 1:
            i += 1; continue
        prev = segs[i - 1] if i else None
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        top = lambda x: x is not None and x["kind"] in ("broll", "insert")
        back_ok = nxt is not None and nxt.get("in", 0) >= (nxt["a"] - s["a"]) * float(nxt.get("speed") or 1)
        same = lambda x: x is not None and x.get("clip") and x.get("clip") == s.get("clip") and x["kind"] == s["kind"]
        # the same clip first (a punch-in step on the same take): her lips stay with her words. Giving a lip-synced
        # sliver to another angle put her voice on the wrong mouth (4 Oct, "That's scary").
        if same(nxt) and back_ok:
            _shift_in(nxt, s["a"] - nxt["a"])
        elif same(prev):
            prev["b"] = s["b"]
        elif prev is not None and (top(prev) or not (top(nxt) and back_ok)):
            prev["b"] = s["b"]
        elif nxt is not None and back_ok:
            _shift_in(nxt, s["a"] - nxt["a"])
        elif prev is not None:
            prev["b"] = s["b"]
        else:
            i += 1; continue
        del segs[i]
        i = max(0, i - 1)
    return segs


def crop_box(p: dict) -> tuple[float, float, float, float]:
    """The part of the source frame a shot shows (fractions x0, y0, x1, y1) — the one place this maths lives
    (crop_filter draws it; mouths.py and sweep read it)."""
    sc = float(p.get("scale") or 1.0)
    if sc <= 1.0:
        return 0.0, 0.0, 1.0, 1.0
    cx = 0.5 if p.get("x") is None else p["x"]
    cy = 0.4 if p.get("y") is None else p["y"]
    h = 0.5 / sc
    cx, cy = min(1 - h, max(h, cx)), min(1 - h, max(h, cy))
    return cx - h, cy - h, cx + h, cy + h


def crop_filter(p: dict, tilt: tuple | None = None) -> str:
    """The shot's crop. `tilt` (a0, a1 degrees, seconds): the crooked hold (realism), turned INSIDE the room the punch's
    crop leaves — the frame is rotated before the punched window is cut from it, so no corner shows and nothing is
    scaled twice (E38, verify 2026-10-21)."""
    sc = float(p.get("scale") or 1.0)
    base = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if sc <= 1.0:
        return base
    x0, y0, _, _ = crop_box(p)
    turn = ""
    if tilt:
        a0, a1, d = tilt
        turn = f",rotate=a='({a0}+({a1 - a0})*min(t/{max(d, 0.04):.3f}\\,1))*PI/180':c=black"
    return f"{base}{turn},crop=iw/{sc}:ih/{sc}:iw*{x0:.5f}:ih*{y0:.5f},scale={W}:{H}"


def tilt_for(p: dict, seconds: float) -> tuple | None:
    """The crooked hold for a punched shot, when the piece's realism picks it: by the shot (its clip and in-point, not
    its place), clamped to the angle its crop window leaves (compose.tilt_room). None for an unpunched shot."""
    sc = float(p.get("scale") or 1.0)
    if sc <= 1.0 or not TILT["on"]:
        return None
    import zlib
    import compose as C
    x0, y0, x1, y1 = crop_box(p)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    o = tuple(min(1.0, max(0.0, (c - 0.5 / sc) / (1 - 1 / sc))) for c in (cx, cy))   # the point the crop scales about
    room = C.tilt_room(sc, o)
    if room < 0.2:
        return None
    a0, a1 = (-0.9, 0.7) if zlib.crc32(f"{p.get('clip')}:{p.get('in')}".encode()) % 2 == 0 else (0.7, -0.6)
    return (round(max(-room, min(room, a0)), 3), round(max(-room, min(room, a1)), 3), seconds)


TILT = {"on": False}   # realism `crooked-hold` picked for this piece (render() sets it)


def clean_filter(p: dict) -> str:
    """An item baked into the clip from its start frame, painted over with the cloth just below it (edit_map
    clean_baked) — the right item's cut-out is laid on top in the words layer."""
    c = p.get("clean")
    if not c:
        return ""
    x0, y0, x1, y1 = c
    w, h = x1 - x0, y1 - y0
    # the cloth BELOW the patch only — never a band that reaches back into the patch itself (a taller patch near the
    # frame's foot used to copy the baked item it was hiding, 2026-10-20); a short clean band is stretched to fit
    hs = max(0.02, min(h, 1 - (y1 + 0.005)))
    stretch = f",scale=iw:ih*{h / hs:.4f}" if hs < h - 1e-4 else ""
    return (f"split[c0][c1];[c1]crop=iw*{w:.4f}:ih*{hs:.4f}:iw*{x0:.4f}:ih*{min(1 - hs, y1 + 0.005):.4f}{stretch},"
            f"boxblur=6:1,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*min(1,min(min(X,W-1-X),min(Y,H-1-Y))/18)'[c2];[c0][c2]overlay=W*{x0:.4f}:H*{y0:.4f},")


def still(src: Path, at: float, seconds: float) -> bool:
    """Does this stretch of the source sit still? (realism.still — one place for the measure)"""
    import realism as RL
    return RL.still(src, at, seconds)


def push(n: int, amount: float | None = None) -> str:
    """A slow push-in across the shot (`amount`, else PUSH, over its length, eased): a still PICTURE (a plate, a photo)
    drifts by the format's image_drift so it is never frozen; a video shot is pushed only when the format asks."""
    a = PUSH if amount is None else amount
    if a <= 0:
        return ""
    z = f"(1+{a}*(1-cos(PI*min(n/{max(1, n - 1)},1)))/2)"
    return (f",scale=w='2*trunc({W}*{z}/2)':h='2*trunc({H}*{z}/2)':eval=frame:flags=bicubic,"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2")


PUSH_STILLS = {"on": False, "drift": 0.03}   # looks.moves(format): push_stills, image_drift − 1 — set per render


def render_picture(vm: Path, out: Path, m: dict, work: Path, crf: int) -> Path:
    segs = flatten(m)
    files = []
    for i, s in enumerate(segs):
        f0, f1 = round(s["a"] * FPS), round(s["b"] * FPS)
        n = f1 - f0
        if n <= 0:
            continue
        seg = work / f"seg{i:03d}.mp4"
        sp = float(s.get("speed") or 1.0)
        if s["kind"] == "plate" or (s["kind"] in ("broll", "insert") and Path(str(s.get("file") or "")).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")):
            # a still: a card plate, or a picture laid in as a cut-in on the timeline (2026-10-16)
            src = vm / s["src"] if s["kind"] == "plate" else out / s["file"]
            ff("-loop", "1", "-i", str(src), "-frames:v", str(n), "-vf", f"{crop_filter(s)},fps={FPS}{push(n, PUSH_STILLS['drift'])},format=yuv420p",
               "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-an", str(seg))
        else:
            src = (out / s["file"]) if s["kind"] == "broll" else (vm / "clips" / f"{s['clip']}.mp4")
            clen = dur(src)
            start = max(0.0, min(float(s.get("in") or 0), max(0.0, clen - 0.05)))
            slow = f"setpts=PTS/{sp}," if abs(sp - 1) > 1e-3 else ""
            move = push(n) if (PUSH_STILLS["on"] and still(src, start, n / FPS * sp)) else ""   # off unless the format asks (V15, E21)
            # tpad holds the last frame if a source runs a hair short (never black)
            ff("-ss", f"{start:.3f}", "-i", str(src), "-frames:v", str(n),
               "-vf", f"{slow}{clean_filter(s)}{crop_filter(s, tilt_for(s, n / FPS))},fps={FPS}{move},tpad=stop_mode=clone:stop_duration=2,format=yuv420p",
               "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-an", str(seg))
        files.append(seg)
    lst = work / "segs.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    pic = work / "picture.mp4"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(pic))
    return pic


# ------------------------------------------------------------------ words

def _box(draw, xy, r, fill):
    draw.rounded_rectangle(xy, radius=r, fill=fill)


def _wrap(text, ft, maxw, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=ft) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _rgba(c):
    return tuple(c) if c else None


def draw_block(d, lines: list[str], lk: dict, y0: float) -> dict:
    """Lines of words in a look, centred, from y0 (pixels). Returns where everything landed (for the checks).
    `per_line_box`: one card that hugs each line, as creators' text tools draw it — the line boxes are merged into a
    single shape (no seams, no overlaps), outer corners rounded, steps between lines filled smooth. Each line's text is
    measured (ink, outline included) and centred in its own band, so the padding is even on every side."""
    ft = font(lk["size"], lk["font"])
    lh = lk["line_h"]; px, py = lk["pad"]; sw = lk.get("stroke_w") or 0
    if not lk.get("per_line_box"):                            # the video's headline and pops: drawn as they were approved
        bw = max(d.textlength(l, font=ft) for l in lines) + 2 * px
        bh = lh * len(lines) + 2 * py
        x0 = (W - bw) / 2
        if lk.get("box"):
            _box(d, (x0, y0, x0 + bw, y0 + bh), lk["radius"], _rgba(lk["box"]))
        for k, l in enumerate(lines):
            tw = d.textlength(l, font=ft)
            d.text(((W - tw) / 2, y0 + py + k * lh), l, font=ft, fill=_rgba(lk["fill"]),
                   stroke_width=sw, stroke_fill=_rgba(lk.get("stroke")))
        return {"box": (x0, y0, x0 + bw, y0 + bh), "font_px": lk["size"], "lines": len(lines)}
    ink = [d.textbbox((0, 0), l, font=ft, stroke_width=sw) for l in lines]
    cap = max(b[3] - b[1] for b in ink)                       # tallest line's ink, outline included
    band = max(lh, cap + 2 * py)                              # each line's band: the ink plus even padding
    cx = W / 2
    bands = []
    for k, (l, b) in enumerate(zip(lines, ink)):
        tw = b[2] - b[0]
        top = y0 + k * band
        bands.append((cx - tw / 2 - px, top, cx + tw / 2 + px, top + band))
    if lk.get("box"):
        from PIL import ImageFilter
        r = int(lk.get("radius") or 0)
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        for (x0, t0, x1, t1) in bands:
            md.rectangle((x0, t0, x1, t1), fill=255)
        if r:                                                 # round outer corners and fill inner steps, one shape
            mask = mask.filter(ImageFilter.GaussianBlur(r / 2)).point(lambda v: 255 if v >= 128 else 0)
        d._image.paste(Image.new("RGBA", (W, H), _rgba(lk["box"])), (0, 0), mask)
    for l, (x0, t0, x1, t1) in zip(lines, bands):
        d.text((cx, (t0 + t1) / 2), l, font=ft, anchor="mm", fill=_rgba(lk["fill"]),
               stroke_width=sw, stroke_fill=_rgba(lk.get("stroke")))
    return {"bands": bands, "box": (min(b[0] for b in bands), bands[0][1], max(b[2] for b in bands), bands[-1][3]),
            "font_px": lk["size"], "lines": len(lines)}


def draw_items(state: dict) -> Image.Image:
    """The pictures laid on the frame at one moment — the item cut-outs (the real product photo, matted) and the
    stickers. No words: compose.py draws every word since 2026-10-21 (C13)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for cu in state.get("cutouts") or []:                  # the item's own picture, fitted in the brief's box
        sk = cutout_png(cu["file"])
        if sk is not None:
            x0, y0, x1, y1 = cu["box"]
            bw, bh = (x1 - x0) * W, (y1 - y0) * H
            k = min(bw / sk.width, bh / sk.height)
            sm = sk.resize((max(1, round(sk.width * k)), max(1, round(sk.height * k))), Image.LANCZOS)
            im.alpha_composite(sm, (round((x0 + x1) / 2 * W - sm.width / 2), round((y0 + y1) / 2 * H - sm.height / 2)))
    # STICKERS (2026-10-16, the owner on the timeline: "I can't add stickers and graphics") — rows of looks/icons.json
    # placed on the frame in % (x, y, w), drawn from the icon's own file
    for st in state.get("stickers") or []:
        png = sticker_png(st["id"], round(W * float(st.get("w", 18)) / 100))
        if png:
            sk = Image.open(png).convert("RGBA")
            im.alpha_composite(sk, (round(W * float(st.get("x", 41)) / 100), round(H * float(st.get("y", 40)) / 100)))
    return im


_CUTS = {}


def cutout_png(rel: str):
    """An item picture (repo path) as a clean RGBA cut-out (cutout.still: matted once, cached)."""
    if rel not in _CUTS:
        try:
            import cutout as CU
            _CUTS[rel] = Image.open(CU.still(HERE.parents[2] / rel)).convert("RGBA")
        except Exception as e:  # noqa: BLE001
            print(f"WARN cut-out {rel}: {e}")
            _CUTS[rel] = None
    return _CUTS[rel]


_ICONS = {}


def sticker_file(row: dict):
    """The icon's own picture on this Mac (looks/icons/<set>/<name>.svg), matched exactly, or None."""
    d = HERE.parent / "looks" / "icons" / str(row.get("set"))
    base = str(row.get("source") or "").split("/")[-1]
    for name in (base, base + "_default"):
        for ext in (".svg", ".png"):
            if base and (d / (name + ext)).is_file():
                return d / (name + ext)
    return None


def sticker_png(icon_id: str, px: int):
    """One looks/icons.json row as a transparent PNG at px wide (SVG drawn by ImageMagick), cached; None if unknown."""
    key = (icon_id, px)
    if key in _ICONS:
        return _ICONS[key]
    lib = json.loads((HERE.parent / "looks" / "icons.json").read_text())
    row = next((r for r in lib.get("icons") or [] if r.get("id") == icon_id), None)
    src = sticker_file(row) if row else None
    out = None
    if src:
        cache = HERE.parent / ".cache" / "stickers"
        cache.mkdir(parents=True, exist_ok=True)
        out = cache / f"{icon_id}-{px}.png"
        if not out.exists():
            import os as _os
            env = dict(_os.environ, PATH=_os.pathsep.join(["/opt/homebrew/bin", "/usr/local/bin", _os.environ.get("PATH", "/usr/bin:/bin")]))
            if src.suffix.lower() == ".svg" and shutil.which("rsvg-convert", path=env["PATH"]):     # draws every emoji's gradients
                subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px), "-a", "-o", str(out), str(src)],
                               check=True, capture_output=True, env=env)
            else:
                subprocess.run(["magick", "-background", "none", "-density", "300", str(src), "-resize", f"{px}x{px}", str(out)],
                               check=True, capture_output=True, env=env)
    _ICONS[key] = out
    return out


BREAK = (".", ",", "?", "!", "…", ":", ";", "—")


def _pieces(ws: list[str], per: int) -> list[tuple[int, int]]:
    """Script words -> caption pieces of up to `per` words, ending early where the line takes a breath (punctuation)."""
    out, i = [], 0
    while i < len(ws):
        j = i
        while j < len(ws) and j - i < per:
            j += 1
            if ws[j - 1].endswith(BREAK) and j - i >= 2:
                break
        out.append((i, j)); i = j
    return out


def line_words(control: dict, heard: list[dict]) -> dict:
    """The heard words of each line, as seconds from the line's own start, keyed by (scene, text) — the same line
    sounds the same in every version, so one listen of the control times the captions of every hook version."""
    out = {}
    for l in control["voice"]:
        ws = [w for w in heard if l["a"] - 0.12 <= w["start"] < l["b"] + 0.05]
        if ws:
            out[(l.get("scene"), l["text"])] = [w["start"] - l["a"] for w in ws]
    return out


def caption_chunks(m: dict, per: int | None = None, timed: dict | None = None) -> list[dict]:
    """Captions, a few words at a time. With `timed` (line_words) each piece comes up on its first spoken word and
    stays until the next piece — the words on screen change when she says them; without, a line is split evenly."""
    per = per or int(caption_look((m.get("captions") or {}).get("look_id")).get("max_words", 4))
    out = []
    for l in m["voice"]:
        ws = l["text"].split()
        if not ws:
            continue
        starts = (timed or {}).get((l.get("scene"), l["text"]))
        pcs = _pieces(ws, per) if starts else [(k * per, min(len(ws), (k + 1) * per)) for k in range(-(-len(ws) // per))]
        if starts:
            at = [l["a"] + starts[min(len(starts) - 1, round(i * len(starts) / len(ws)))] for i, _ in pcs]
            at[0] = l["a"]
            ends = at[1:] + [l["b"]]
        else:
            step = (l["b"] - l["a"]) / len(pcs)
            at = [l["a"] + k * step for k in range(len(pcs))]
            ends = at[1:] + [l["b"]]
        for (i, j), a, b in zip(pcs, at, ends):
            if b - a > 1 / FPS:
                out.append({"a": a, "b": b, "text": " ".join(ws[i:j]), "y": l.get("cap_y", 0.74)})
    return out


def render_items(m: dict, work: Path) -> Path | None:
    """The item cut-outs and stickers on the cut's clock, as one transparent layer (None when the ad has neither)."""
    stickers = m.get("stickers") or []
    cuts = m.get("cutouts") or []
    if not stickers and not cuts:
        return None
    edges = sorted({0.0, m["total"]} | {round(x, 3) for s_ in stickers for x in (s_["a"], s_["b"])} |
                   {round(x, 3) for c_ in cuts for x in (c_["a"], c_["b"])})
    lst, cache = [], {}
    for a, b in zip(edges, edges[1:]):
        if b - a < 1 / FPS / 2:
            continue
        mid = (a + b) / 2
        st = {"stickers": [s_ for s_ in stickers if s_["a"] <= mid < s_["b"]],
              "cutouts": [c_ for c_ in cuts if c_["a"] <= mid < c_["b"]]}
        key = json.dumps(st, sort_keys=True)
        if key not in cache:
            f = work / f"i{len(cache):04d}.png"; draw_items(st).save(f); cache[key] = f
        lst.append((cache[key], b - a))
    txt = work / "items.txt"
    txt.write_text("".join(f"file '{f}'\nduration {d:.4f}\n" for f, d in lst) + f"file '{lst[-1][0]}'\n")
    items = work / "items.mov"
    ff("-f", "concat", "-safe", "0", "-i", str(txt), "-vf", f"fps={FPS},format=rgba", "-c:v", "png", "-t", f"{m['total']:.3f}",
       str(items))
    return items



# ------------------------------------------------------------------ sound

# a quiet room: soft brown noise, rumble and hiss cut, at ROOM_DB — ONLY when the swipe has room sound (V14, C10:
# the map's `room_tone`, the brief's cue). Without it the voices' own tails carry the joins (the clips are not dead
# silent; the swipe's quietest moment is -41 dB)
ROOM_CHAIN = ("[{i}:a]highpass=f=90,lowpass=f=2800,aformat=channel_layouts=mono,"
              f"volume={10 ** ((ROOM_DB + 28) / 20):.5f}[r]")      # the noise alone sits at about -28 dB RMS


def room_called(m: dict) -> bool:
    """Does this ad call for room sound? The map carries the brief's cue (edit_map.py `room_tone`)."""
    return bool(m.get("room_tone"))


def room_in(m: dict) -> list[str]:
    return ["-f", "lavfi", "-t", f"{m['total'] + 0.5:.3f}", "-i", "anoisesrc=color=brown:amplitude=0.25:sample_rate=44100:seed=7"]


def render_sound(vm: Path, out: Path, m: dict, work: Path) -> Path:
    voice = LI.mix(vm, out, m, work / "voices")              # the cut's voices, exactly as the clean pass hears them
                                                              # (in this render's own folder: versions render pooled, E35)
    mus = m.get("music") or {}
    final = work / "sound.wav"
    room = room_called(m)
    ins = ["-i", str(voice)]
    chains, mixed = [], ["[0:a]"]
    if mus.get("made") and (out / mus["file"]).exists():   # a bed only when the ad has one (V14: never assumed)
        talk = "+".join(f"between(t,{max(0, l['a'] - 0.1 - mus['a']):.3f},{l['b'] + 0.1 - mus['a']:.3f})"
                        for l in m["voice"] + m["sounds"]) or "0"
        under = 10 ** (mus.get("under_voice_db", SOUND["music_db"]) / 20)
        pause = 10 ** (mus.get("in_pauses_db", SOUND["music_gap_db"]) / 20)
        mlen = mus["b"] - mus["a"]
        # a bank bed shorter than the edit loops to the last frame (it never stops before the edit does)
        ins += (["-stream_loop", "-1"] if mus.get("loop") else []) + ["-i", str(out / mus["file"])]
        chains.append(f"[{len(mixed)}:a]atrim=0:{mlen:.3f},aresample=44100,aformat=channel_layouts=mono,"
                      f"volume='if(gt({talk},0),{under:.4f},{pause:.4f})':eval=frame,"
                      f"afade=t=out:st={max(0, mlen - 1.5):.3f}:d=1.5,adelay={int(mus['a'] * 1000)}:all=1[m]")
        mixed.append("[m]")
    if room:
        ins += room_in(m)
        chains.append(ROOM_CHAIN.format(i=len(mixed)))
        mixed.append("[r]")
    # the sound effects the swipe or the brief calls for (V14; verify 2026-10-21 row 5 — they were never mixed): each
    # bank file at its cue, landing two frames early, at the table's level, 15 ms fades so no edge clicks
    for n, c in enumerate(x for x in m.get("sfx") or [] if x.get("made") and x.get("file")):
        f = Path(c["file"]) if Path(c["file"]).is_absolute() else out / c["file"]
        if not f.exists():
            continue
        at = max(0.0, float(c["a"]) - float(c.get("lead_frames", SOUND["sfx_lead_frames"])) / FPS)
        if at >= m["total"] - 0.05:
            continue
        ins += ["-i", str(f)]
        g = 10 ** (float(c.get("db", SOUND["sfx_db"])) / 20)
        chains.append(f"[{len(mixed)}:a]aresample=44100,aformat=channel_layouts=mono,volume={g:.4f},"
                      f"afade=t=in:st=0:d=0.015,areverse,afade=t=in:st=0:d=0.015,areverse,adelay={int(at * 1000)}:all=1[x{n}]")
        mixed.append(f"[x{n}]")
    head = (";".join(chains) + ";") if chains else ""
    ff(*ins, "-filter_complex",
       f"{head}{''.join(mixed)}amix=inputs={len(mixed)}:normalize=0,atrim=0:{m['total']:.3f},"
       f"loudnorm=I={MIX['loudness_lufs']}:TP={MIX['true_peak_db']}:LRA=11[o]", "-map", "[o]", "-ar", "48000", str(final))
    return final


# ------------------------------------------------------------------ one version

def render(vm: Path, out: Path, m: dict, name: str, draft: bool = False) -> Path:
    dest = out / "renders"; dest.mkdir(parents=True, exist_ok=True)
    crf = 26 if draft else 18
    fmt = (json.loads((vm / "run.json").read_text()) if (vm / "run.json").exists() else {}).get("format")
    mv = LK.moves(fmt)
    PUSH_STILLS.update(on=bool(mv.get("push_stills")), drift=max(0.0, float(mv.get("image_drift") or 1.0) - 1.0))
    import realism as RL
    TILT["on"] = "crooked-hold" in (RL.pick(fmt, vm=vm) or {}).get("rows", [])
    clean = dest / f"{name}.clean.mp4"
    with tempfile.TemporaryDirectory() as t:
        work = Path(t)
        talking_only_when_talking(out, m, name)            # refuses if the lead's mouth shows talking with no voice of theirs
        timed, _ = hear(vm, out, m, name)                   # refuses before a frame is made if a word is cut off
        hf = out / "listen" / ("" if name == "control" else name) / "heard.json"
        heard = json.loads(hf.read_text()) if hf.exists() else None   # times an own-track line's captions (a check, never re-run)
        pic = render_picture(vm, out, m, work, crf)
        items = render_items(m, work)
        sound = render_sound(vm, out, m, work)
        keep = dest / f"{name}.sound.wav"
        shutil.copy2(sound, keep)
        vf = ["-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a"] if items \
            else ["-map", "0:v", "-map", "1:a"]
        ff("-i", str(pic), *(["-i", str(items)] if items else []), "-i", str(sound), *vf, "-c:v", "libx264", "-crf", str(crf),
           "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
           "-movflags", "+faststart", "-t", f"{m['total']:.3f}", str(clean))
    sync = lips(vm, m, clean)                               # measured on the picture with no words on it
    if sync["held"] and _lenient():   # a draft to watch on the timeline; the final still holds a slip
        print(f"WARN {name}: the picture slips {max(abs(r['frames']) for r in sync['shots']):.0f} frame(s) against the voice "
              "(draft kept: edit on Auto; the final holds it)")
    elif sync["held"]:
        clean.rename(clean.with_suffix(".held.mp4"))
        raise SystemExit(f"HELD {name}: the picture has slipped {max(abs(r['frames']) for r in sync['shots']):.0f} frame(s) against the voice — "
                         f"see renders/{name}.clean.held.mp4; nothing is delivered from a held render")
    mp4 = words_on(vm, out, m, name, clean, keep, heard, fmt, "draft" if draft else "delivery")
    (dest / f"{name}.json").write_text(json.dumps({"version": name, "hook": m.get("hook"), "seconds": m["total"],
                                                   "from": "edit-map" + (f"-{name}" if name != "control" else "") + ".json",
                                                   "words_by": "compose.py (map_sheet.py)", "sheet": f"{name}.sheet.json",
                                                   "quality": "draft" if draft else "delivery",
                                                   "size": [W, H], "fps": FPS, "loudness": "-14 LUFS / -1 dBTP",
                                                   "room_tone": room_called(m), "lips": sync}, indent=1))
    print(f"  lips: {sync['checked']} talking shots checked, worst {max((abs(r['frames']) for r in sync['shots']), default=0):.1f} clip frame(s) off"
          + ("  — HELD: the picture has slipped against the voice" if sync["held"] else ""))
    return mp4


def words_on(vm: Path, out: Path, m: dict, name: str, clean: Path, sound: Path, heard: list[dict] | None, fmt: str | None,
             quality: str) -> Path:
    """The words, the transitions and the finish, drawn by compose.py over the assembled picture (map_sheet.py): one
    renderer for every word in the system (C13). The sheet is kept beside the render — audit.py reads it."""
    import compose as C
    import faces as FC
    import map_sheet as MS
    import placement as P
    import realism as RL
    import run as R
    dest = out / "renders"
    sh = MS.sheet(vm, out, m, clean, sound, heard, fmt)
    try:
        notes = FC.read_scenes(sh, out)                     # faces, lips, hands on the picture under every word (Vision)
    except Exception as e:  # noqa: BLE001 — no Vision on this machine: placement is face-blind and says so
        notes = [f"scene read not run ({type(e).__name__}) — captions placed face-blind"]
    RL.mark(sh, out)                                        # too still → the hand's shake; off centre → the nudge
    P.place(sh)
    sh["helper_notes"] = notes
    (dest / f"{name}.sheet.json").write_text(json.dumps(sh, indent=1, ensure_ascii=False))
    mp4 = dest / f"{name}.mp4"
    project = out / "work" / f"compose-{name}"
    C.compose(sh, out, project, captions=True)
    for cmd in (["hyperframes", "lint", str(project)],
                ["hyperframes", "render", str(project), "--output", str(mp4), "--quality", quality, "--quiet"]):
        with HF_LOCK:
            r = subprocess.run(cmd, capture_output=True, text=True)
        (out / "work" / f"compose-{name}.{cmd[1]}.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            raise SystemExit(f"{cmd[1]} failed for {name} — see {out / 'work' / f'compose-{name}.{cmd[1]}.log'}")
    R.master(mp4, {"lufs": MIX["loudness_lufs"], "true_peak_db": MIX["true_peak_db"]})
    return mp4


def lips(vm: Path, m: dict, mp4: Path) -> dict:
    """Are the lips in time in the finished file? Every lip-synced shot with a clear second on screen (no B-roll over
    it) is found in its source clip frame by frame (syncheck.picture_lag). More than one frame of slip anywhere = HELD."""
    import syncheck as SC
    tops = m.get("broll") or []
    rows = []
    for s in flatten(m):
        if s["kind"] != "clip" or not s.get("lip") or s["b"] - s["a"] < 1.0:
            continue
        t = s["a"] + 0.2
        if any(r["a"] < t + 0.6 and r["b"] > t for r in tops):
            continue
        src = vm / "clips" / f"{s['clip']}.mp4"
        # A FRAME IS THE CLIP'S FRAME (2026-10-09, LeBron r3): a 24 fps clip in a 30 fps cut can't land on the 30 fps
        # grid, so measuring there read every shot ±1.6 frames off while the sound was dead in time. Measure and hold
        # in the clip's own frames.
        cf = src_fps(src)
        # THREE LOOKS, THE MIDDLE ONE (2026-10-09, LeBron r3): a locked wide shot barely moves, so one look can land
        # a frame and a half out while the sound is dead in time; the median of three spots in the shot is the reading.
        sp = float(s.get("speed") or 1)
        # SEVEN LOOKS, THEIR MEAN (2026-10-09): a reading only lands on whole clip frames (0.042 s at 24 fps), so a
        # true slip of ~0.046 s reads -0.025 on some looks and -0.067 on others; the middle of three flipped between
        # 1.0 and 1.6 frames as the same shot moved in time between versions. The mean of up to seven looks across
        # the shot is the slip itself; the 1.5-frame limit is unchanged.
        # A LOOK EVERY 0.15 s ACROSS THE WHOLE SHOT (2026-10-20): seven looks still flipped a shot between 1.1 and 1.6
        # frames on the 24-in-30 grid and held a cut that was in time, which led to a "nudge" that set the picture
        # off its own voice. Every look the shot has, their mean.
        n = max(1, int((s["b"] - t - 0.5) / 0.15) + 1)
        looks = [SC.picture_lag(mp4, t + d, src, s["in"] + (0.2 + d) * sp, crop_filter(s), fps=cf)
                 for d in (k * 0.15 for k in range(n))
                 if t + d + 0.5 <= s["b"] and not any(r["a"] < t + d + 0.5 and r["b"] > t + d for r in tops)]
        looks = sorted(x for x in looks if x is not None)
        lg = round(sum(looks) / len(looks), 4) if looks else None
        if lg is not None:
            rows.append({"at": round(s["a"], 2), "clip": s["clip"], "late_s": lg, "fps": cf,
                         "frames": round(lg * cf, 2)})
    worst = max((abs(r["late_s"]) for r in rows), default=0.0)
    held = any(abs(r["frames"]) > 1.5 for r in rows)
    return {"checked": len(rows), "worst_s": worst, "held": held, "shots": rows}


def src_fps(clip: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", str(clip)], capture_output=True, text=True).stdout.strip() or f"{FPS}/1"
    n, d = (r.split("/") + ["1"])[:2]
    return max(1, round(float(n) / float(d or 1)))


_DRAFT = {"on": False, "approved": False}


def _lenient() -> bool:
    """A finding is listed, never a stop: a draft on Auto, or a cut of APPROVED clips """
    return bool(_DRAFT.get("approved")) or (_DRAFT["on"] and _edit_auto())


def _edit_auto() -> bool:
    try:
        a = json.loads((Path(__file__).resolve().parents[3] / "runs" / "settings" / "settings.json").read_text())["automation"]
        return a.get("edit") == "auto" and not a.get("paused")
    except Exception:  # noqa: BLE001
        return False


def talking_only_when_talking(out: Path, m: dict, name: str) -> None:
    """mouths.py over what will be on screen: her mouth moving with no voice of hers, or her voice over a mouth that
    isn't saying it, refuses the render (the owner, 4 Oct: "you're showing her talking when she should not be talking")."""
    import mouths as MO
    tracks = {f.stem: json.loads(f.read_text()) for f in (out / "tracks").glob("*.json")}
    if not tracks:
        return
    found = MO.reviewed(MO.check(m, tracks, MO.lead_of(m)), out)
    if found and (_edit_auto() or _DRAFT.get("approved")):
        # edit on Auto (Outlier Settings): the draft renders so it can be SEEN; each mismatch is listed for the
        # timeline (cover it there with a close-up or B-roll) and logged to Calls — the final still needs it covered
        msg = "; ".join(f"{f['a']:.1f}s {f['kind'].lower()} ({f['line']})" for f in found)
        print(f"WARN {name}: the lead's mouth and the sound disagree — {msg} (rendered anyway: edit on Auto; cover on the timeline)")
        try:
            import fcntl
            q = Path(__file__).resolve().parents[3] / "runs" / "decisions" / "calls.jsonl"
            with q.open("a") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                fh.write(json.dumps({"id": f"{out.name}:mouths:{int(time.time())}", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                     "run": out.name, "gate": "mouths", "decision": "rendered the draft — cover these on the timeline",
                                     "item": {"what": msg[:400]}, "mode": "auto", "verdict": None, "look": True}) + "\n")
        except Exception:  # noqa: BLE001
            pass
        return
    if found:
        raise SystemExit(f"HELD {name}: the lead's mouth and the sound disagree — " + "; ".join(
            f"{f['a']:.1f}s {f['kind'].lower()} ({f['line']})" for f in found) + ". Cover it (close-up above the mouth, "
            "B-roll) — machine/mouths.py lists them.")


def accepted_cut(out: Path, script: str) -> bool:
    """Is every word of this missing phrase one a person accepted as cut (decisions.json `cut_words`, with their words)?"""
    dec_f = Path(out) / "decisions.json"
    allowed = {LI._norm(w) for c in ((json.loads(dec_f.read_text()).get("cut_words") or []) if dec_f.exists() else [])
               for w in str(c.get("words", "")).split()}
    return bool(str(script).split()) and all(LI._norm(w) in allowed for w in str(script).split())


def hear(vm: Path, out: Path, m: dict, name: str) -> tuple[dict, list[dict]]:
    """Every word the version's soundtrack says, held against the script BEFORE anything is rendered (listen.py).
    A scripted word that is not heard is a cut-off word: the render is refused, naming it — unless the run's
    decisions.json `cut_words` lists it as cut on the owner's word (4 Oct 2026: "We should never be cutting off words
    unless I'm discreetly describing to cut it out"; "Guaranteed" went out cut off while the check had flagged it)."""
    d = out / "listen" / ("" if name == "control" else name)
    wav = LI.mix(vm, out, m, d)
    heard = LI.transcribe(wav)
    found = LI.check(m, heard)
    (d / "heard.json").write_text(json.dumps(heard, indent=1))
    (d / "listen.json").write_text(json.dumps(found, indent=1))
    cut = [f for f in found if f["what"] == "missing / clipped" and not accepted_cut(out, f["script"])]
    if cut and _lenient():   # a DRAFT on Auto renders so it can be seen; the final still holds
        print(f"WARN {name}: word(s) maybe cut off — " + "; ".join(f"{f['t']:.1f}s {f['line']} \"{f['script']}\"" for f in cut)
              + " (draft rendered anyway: edit on Auto; the final holds it)")
        cut = []
    if cut:
        raise SystemExit(f"HELD {name}: word(s) cut off — " + "; ".join(
            f"{f['t']:.1f}s {f['line']} ({f['who']}) \"{f['script']}\"" for f in cut) +
            ". Fix the cut (word_fix.py + add_lines / trim_line) or list it in decisions.json cut_words on the owner's word.")
    return line_words(m, heard), found


def timed_words(out: Path) -> dict | None:
    """The clean pass's heard words (listen.py) against the control's lines, or None (captions split evenly)."""
    h, c = out / "listen" / "heard.json", out / "edit-map.json"
    if not (h.exists() and c.exists()):
        return None
    return line_words(json.loads(c.read_text()), json.loads(h.read_text()))


def versions(out: Path) -> dict:
    v = {"control": out / "edit-map.json"}
    for f in sorted(out.glob("edit-map-*.json")):
        v[f.stem.replace("edit-map-", "")] = f
    return v


# ------------------------------------------------------------------ a hook version = a new opening on the control (E35)
# V22 (the owner, 2026-10-21): "it would just rebuild the storyboard five times versus just switching out that hook or the
# thumbnail". A hook version swaps ONLY the opening: the same audio, the same body, the same captions after the hook.
# So it renders only its own opening (picture, words and checks for those seconds) and is joined onto the control's
# already-rendered body — the body's frames stream-copied from the control's own file, the sound joined at the same
# sample and mastered once — then proven frame by frame against the control (v2.same_after_opening). Anything that does
# not prove out is rendered in full, as before. Thumbnails are frames of the finished cut (thumbs.py), never a render.
HF_LOCK = threading.Lock()   # one HyperFrames render at a time on this Mac (v2's rule); the rest of a version runs pooled


def _sigs(m: dict, shift: float) -> list[tuple]:
    """What is on screen and heard, each with where it sits once shifted back onto the control's clock."""
    out = []
    for x in flatten(m):
        out.append((("pic", x.get("kind"), x.get("clip") or x.get("file") or x.get("src"), round(float(x.get("in") or 0), 2),
                     round(x["b"] - x["a"], 2), round(float(x.get("scale") or 1), 2)), round(x["a"] - shift, 2), x["b"]))
    for l in (m.get("voice") or []) + (m.get("sounds") or []):
        out.append((("line", l.get("kind"), l.get("clip") or l.get("file"), round(float(l.get("in") or 0), 2), round(float(l["len"]), 2),
                     l.get("text")), round(l["a"] - shift, 2), l["b"]))
    for t in m.get("text") or []:
        out.append((("text", t.get("kind"), " ".join(t.get("words") or [])), round(t["a"] - shift, 2), t["b"]))
    return out


def opening_of(hook: dict, control: dict, name: str) -> tuple[float, float] | None:
    """(shift, D) from the SECTIONS, not by comparing the re-planned body: the hook replaces its opening clip inside its
    section, so the version is the control from the end of that section on, moved by the difference in the section's
    end. None when the hook's clip or its section cannot be found in both."""
    sec = next((p.get("section") for p in hook.get("picture") or [] if p.get("clip") == name), None)
    hb = next((x["b"] for x in hook.get("sections") or [] if x.get("id") == sec), None)
    cb = next((x["b"] for x in control.get("sections") or [] if x.get("id") == sec), None)
    if sec is None or hb is None or cb is None:
        return None
    return round(float(hb) - float(cb), 3), round(float(hb), 3)


def same_frame(hook: dict, control: dict, t_ctrl: float, shift: float) -> bool:
    """At control second t_ctrl (hook second t_ctrl + shift), do both show the same clip at the same clip second?"""
    a = next((x for x in flatten(control) if x["a"] <= t_ctrl < x["b"]), None)
    b = next((x for x in flatten(hook) if x["a"] <= t_ctrl + shift < x["b"]), None)
    if not a or not b or a.get("clip") != b.get("clip") or a.get("file") != b.get("file"):
        return False
    ia = float(a.get("in") or 0) + (t_ctrl - a["a"]) * float(a.get("speed") or 1)
    ib = float(b.get("in") or 0) + (t_ctrl + shift - b["a"]) * float(b.get("speed") or 1)
    return abs(ia - ib) < 1.0 / FPS and abs(float(a.get("scale") or 1) - float(b.get("scale") or 1)) < 1e-3


def split_map(hook: dict, control: dict) -> tuple[float, float]:
    """(shift, D): from hook second D on, the hook is the control moved by `shift` seconds — D is where the last thing
    the control does not have ends. D == the hook's whole length means nothing can be reused."""
    shift = round(float(hook["total"]) - float(control["total"]), 3)
    have = {(k, a) for k, a, _ in _sigs(control, 0.0)}
    near = lambda k, a: any((k, round(a + d, 2)) in have for d in (-0.02, -0.01, 0.0, 0.01, 0.02))   # noqa: E731
    D = 0.0
    for k, a, b in _sigs(hook, shift):
        if not near(k, a):
            D = max(D, b)
    return shift, round(D, 3)


def _head_of(m: dict, head_s: float) -> dict:
    """The map cut at head_s: only what is on screen or heard before it."""
    h = json.loads(json.dumps(m))
    h["total"] = round(head_s, 3)
    for k in ("picture", "broll", "text", "cutouts", "stickers", "voice", "sounds", "patches"):
        if h.get(k):
            h[k] = [x for x in h[k] if float(x.get("a", x.get("mute_a", 0))) < head_s - 1e-3]
    for x in (h.get("text") or []) + (h.get("cutouts") or []) + (h.get("stickers") or []):
        x["b"] = min(float(x["b"]), head_s)
    return h


def joined_version(vm: Path, out: Path, m: dict, name: str, control: dict, draft: bool) -> Path | None:
    """The hook version as its own opening + the control's body, or None when it cannot be (no control render yet, a
    different body, no keyframe to join on, or the proof fails) — the caller then renders it in full."""
    import v2 as V2
    dest = out / "renders"
    ctrl, ctrl_snd, ctrl_rec = dest / "control.mp4", dest / "control.sound.wav", dest / "control.json"
    rec = json.loads(ctrl_rec.read_text()) if ctrl_rec.exists() else {}
    if not (ctrl.exists() and ctrl_snd.exists()) or rec.get("quality") != ("draft" if draft else "delivery"):
        return None
    op = opening_of(m, control, name)
    shift, D = op if op else split_map(m, control)
    if D >= float(m["total"]) - 1.0:
        return None
    # the join: the first keyframe of the control past the opening where both show the very same frame
    k_ctrl = next((k for k in V2.keyframes(ctrl) if k >= D - shift + 0.5 and same_frame(m, control, k, shift)
                   and same_frame(m, control, k - 0.5, shift)), None)
    if k_ctrl is None:
        return None
    head_s = round(k_ctrl + shift, 3)
    hm = _head_of(m, head_s)
    crf = 26 if draft else 18
    fmt = (json.loads((vm / "run.json").read_text()) if (vm / "run.json").exists() else {}).get("format")
    import realism as RL
    mv = LK.moves(fmt)                                   # the same moves and finish the control was made with
    PUSH_STILLS.update(on=bool(mv.get("push_stills")), drift=max(0.0, float(mv.get("image_drift") or 1.0) - 1.0))
    TILT["on"] = "crooked-hold" in (RL.pick(fmt, vm=vm) or {}).get("rows", [])
    talking_only_when_talking(out, m, name)            # the opening's mouths, before a frame is made
    hear(vm, out, m, name)                              # every scripted word of the version heard (a check)
    hf = out / "listen" / name / "heard.json"
    heard = json.loads(hf.read_text()) if hf.exists() else None
    clean = dest / f"{name}.clean.mp4"
    with tempfile.TemporaryDirectory() as t:
        work = Path(t)
        pic = render_picture(vm, out, hm, work, crf)
        items = render_items(hm, work)
        full_snd = render_sound(vm, out, m, work)       # the whole version's mix, so its level matches the control's
        head_snd = work / "head.wav"
        ff("-i", str(full_snd), "-t", f"{head_s:.6f}", "-c:a", "pcm_s16le", str(head_snd))
        vf = ["-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a"] if items \
            else ["-map", "0:v", "-map", "1:a"]
        ff("-i", str(pic), *(["-i", str(items)] if items else []), "-i", str(head_snd), *vf, "-c:v", "libx264", "-crf", str(crf),
           "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-t", f"{head_s:.3f}", str(clean))
        sync = lips(vm, hm, clean)
        if sync["held"] and not (_lenient()):
            clean.rename(clean.with_suffix(".held.mp4"))
            raise SystemExit(f"HELD {name}: the opening's picture has slipped {max(abs(r['frames']) for r in sync['shots']):.0f} frame(s) against the voice")
        head = words_on(vm, out, hm, f"{name}-head", clean, head_snd, [w for w in heard or [] if float(w.get("start", 0)) < head_s] or None,
                        fmt, "draft" if draft else "delivery")
        # the join: the opening's frames, then the control's own from k_ctrl (stream copy); the sound at the same sample
        body_snd = work / "body.wav"
        ff("-ss", f"{k_ctrl:.6f}", "-i", str(ctrl_snd), "-c:a", "pcm_s16le", str(body_snd))
        joined_snd = work / "joined.wav"
        ff("-i", str(head_snd), "-i", str(body_snd), "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-ar", "48000", "-c:a", "pcm_s16le", str(joined_snd))
        body = work / "body.mp4"
        ff("-ss", f"{k_ctrl:.6f}", "-i", str(ctrl), "-map", "0:v:0", "-c", "copy", "-avoid_negative_ts", "make_zero", str(body))
        lst = work / "list.txt"
        lst.write_text(f"file '{Path(head).resolve()}'\nfile '{body.resolve()}'\n")
        vid = work / "video.mp4"
        ff("-f", "concat", "-safe", "0", "-i", str(lst), "-map", "0:v:0", "-c", "copy", "-movflags", "+faststart", str(vid))
        mp4 = dest / f"{name}.mp4"
        V2.mux(vid, V2.master_audio(joined_snd, work / "sound.m4a", {"lufs": MIX["loudness_lufs"], "true_peak_db": MIX["true_peak_db"]}), mp4)
        shutil.copy2(joined_snd, dest / f"{name}.sound.wav")
    # the opening ends on a whole frame (HyperFrames rounds its length up), so the body's frames sit at the opening's
    # real length: the proof reads them there. The sound is joined at the exact sample — the body's picture is at most
    # half a frame off its sound, inside the lips' 1.5-frame hold
    head_n = round(dur(head) * FPS)
    proof = same_frames(mp4, head_n, ctrl, round(k_ctrl * FPS), round(dur(ctrl) * FPS) - round(k_ctrl * FPS))
    proof["picture_vs_sound_s"] = round(head_n / FPS - head_s, 4)
    if not proof["identical"]:
        print(f"  {name}: the joined body did not match the control frame for frame — rendering it in full")
        return None
    (dest / f"{name}.sheet.json").write_text(json.dumps({"joined": True, "head_sheet": f"{name}-head.sheet.json", "head_s": head_s,
                                                         "shift": shift, "body_from": "control.mp4", "k_ctrl": k_ctrl}, indent=1))
    (dest / f"{name}.json").write_text(json.dumps({"version": name, "hook": m.get("hook"), "seconds": m["total"],
                                                   "from": f"edit-map-{name}.json", "joined": {"opening_s": head_s, "body_from_control_s": k_ctrl,
                                                   "shift_s": shift, "proof": proof}, "quality": "draft" if draft else "delivery",
                                                   "size": [W, H], "fps": FPS, "room_tone": room_called(m), "lips": sync}, indent=1))
    print(f"  {name}: opening {head_s:.1f}s rendered, the rest joined on from the control (proved frame for frame)")
    return mp4


def _gray(f: Path, n: int) -> bytes:
    """Frame n of a file, small and grey. ffmpeg's -ss is already counted from the stream's own start, so frame n is
    found at n / FPS, a hair early (a concat moves the start by a few milliseconds; adding it again lands a frame late)."""
    return subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, n / FPS - 0.005):.4f}", "-i", str(f), "-frames:v", "1",
                           "-vf", "scale=270:480", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout


def same_frames(joined: Path, j0: int, control: Path, c0: int, count: int, n: int = 12) -> dict:
    """The proof, by FRAME, not by second: joined frame j0+i is control frame c0+i, for n frames spread over the body
    (a concat shifts start times by a few milliseconds, so a read by the second lands on the neighbouring frame)."""
    rows = []
    for i in [round(x * max(0, count - 2) / max(1, n - 1)) for x in range(n)]:
        a, b = _gray(joined, j0 + i), _gray(control, c0 + i)
        diff = sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a)) if a and len(a) == len(b) else None
        rows.append({"frame": c0 + i, "mean_diff": None if diff is None else round(diff, 3)})
    return {"identical": all(r["mean_diff"] is not None and r["mean_diff"] < 0.5 for r in rows), "samples": rows}


def render_one(vm: Path, out: Path, name: str, f: Path, control: dict | None, draft: bool) -> Path:
    m = json.loads(f.read_text())
    if name != "control" and control is not None:
        mp4 = joined_version(vm, out, m, name, control, draft)
        if mp4 is not None:
            return mp4
    return render(vm, out, m, name, draft)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--only"); ap.add_argument("--draft", action="store_true")
    ap.add_argument("--full", action="store_true", help="render every hook version in full (no join onto the control)")
    ap.add_argument("--approved", action="store_true",
                    help="the clips, voice and script are approved: list word, mouth and sync findings, never stop on them")
    ap.add_argument("--pool", type=int, default=3, help="hook versions worked on at once (HyperFrames still renders one at a time)")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    want = set(a.only.split(",")) if a.only else None
    _DRAFT["on"] = bool(a.draft)
    _DRAFT["approved"] = bool(getattr(a, "approved", False))
    vs = [(n, f) for n, f in versions(out).items() if not want or n in want]
    t0 = time.time()
    for name, f in [x for x in vs if x[0] == "control"]:   # the control first: every hook version joins onto it
        mp4 = render_one(vm, out, name, f, None, a.draft)
        print(f"rendered {name}: {mp4} · {dur(mp4):.2f}s")
    control = json.loads((out / "edit-map.json").read_text()) if (out / "edit-map.json").exists() and not a.full else None
    hooks = [x for x in vs if x[0] != "control"]
    if hooks:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max(1, min(a.pool, len(hooks)))) as pool:
            jobs = {pool.submit(render_one, vm, out, n, f, control, a.draft): n for n, f in hooks}
            failed = []
            for j, n in jobs.items():
                try:
                    mp4 = j.result()
                    print(f"rendered {n}: {mp4} · {dur(mp4):.2f}s")
                except BaseException as e:  # noqa: BLE001 — one version's stop never takes the others down; each is named
                    failed.append(f"{n}: {e}")
        if failed:
            print(f"render: {len(vs)} version(s) in {time.time() - t0:.0f}s — stopped: " + " · ".join(failed))
            raise SystemExit("\n".join(failed))
    print(f"render: {len(vs)} version(s) in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
