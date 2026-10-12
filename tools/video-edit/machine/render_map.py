#!/usr/bin/env python3
"""render_map.py — the finished video from an edit map: 9:16, 1080x1920, 30 fps, one file per version.
Local and free (ffmpeg + Pillow); nothing is sent anywhere.

    python3 render_map.py <video-production-run> [--out <edit run dir>] [--only control,<hook>] [--draft]

Reads <out>/edit-map.json (the control) and every <out>/edit-map-<hook>.json (one version per hook opening)
and writes <out>/renders/<version>.mp4 + <version>.json (what went in). What is on screen is exactly what the
timeline page plays and the sweep checked:
  picture  each piece of each clip from its in-point, slowed where the map says, the punch-in / close-up crop
           applied; B-roll and same-room inserts on top for their windows; cards held
  words    the opening headline (the swipe's look), the option pops, captions in the platform look the edit
           names (Instagram/Facebook native: sentence case, white on a soft dark box, above the feed buttons)
  sound    every line's own sound where the map lays it (the clip's span, an own track, a sound, a patch with
           the clip muted under it), the music bed ducked under the voices and up in the pauses, then
           mastered to -14 LUFS integrated, -1 dBTP (Meta / Instagram feed loudness)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FPS = 30
W, H = 1080, 1920
MIN_SHOT = 0.5          # seconds: nothing on screen shorter (no flashes)
STILL_SHARE = 0.4       # a shot with more still frames than this gets a slow push
PUSH = 0.06             # how far the push goes over the shot (6%)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listen as LI  # noqa: E402  (the same sound mix the clean pass checks)

LOOKS = json.loads((HERE.parent / "looks" / "edit-looks.json").read_text())
MIX = LOOKS["mix"]
ROOM_DB = MIX["room_db"]   # room air under everything: the clips are dead silent between words, a phone never is


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
    return LOOKS["captions"].get(name or "") or LOOKS["captions"][LOOKS["defaults"]["captions"]]


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
                    "file": r.get("file"), "in": r.get("in", 0), "speed": r.get("speed", 1)})
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


def crop_filter(p: dict) -> str:
    sc = float(p.get("scale") or 1.0)
    base = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if sc <= 1.0:
        return base
    x0, y0, _, _ = crop_box(p)
    return f"{base},crop=iw/{sc}:ih/{sc}:iw*{x0:.5f}:ih*{y0:.5f},scale={W}:{H}"


def still(src: Path, at: float, seconds: float) -> bool:
    """Does this stretch of the source sit still? (more than STILL_SHARE of its frames barely change) — the swipe is
    a handheld phone: 11% of its frames are still, ours were 18% before shots like these got a push."""
    txt = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{at:.3f}", "-t", f"{seconds:.3f}", "-i", str(src), "-vf",
                          "scale=135:240,signalstats,metadata=print:key=lavfi.signalstats.YDIF", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    yd = [float(x) for x in re.findall(r"YDIF=([\d.]+)", txt)]
    return bool(yd) and sum(y < 0.6 for y in yd) / len(yd) > STILL_SHARE


def push(n: int) -> str:
    """A slow push-in across the shot (PUSH over its length, eased), so a still shot keeps moving like a hand-held phone."""
    z = f"(1+{PUSH}*(1-cos(PI*min(n/{max(1, n - 1)},1)))/2)"
    return (f",scale=w='2*trunc({W}*{z}/2)':h='2*trunc({H}*{z}/2)':eval=frame:flags=bicubic,"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2")


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
        if s["kind"] == "plate":
            src = vm / s["src"]
            ff("-loop", "1", "-i", str(src), "-frames:v", str(n), "-vf", f"{crop_filter(s)},fps={FPS}{push(n)},format=yuv420p",
               "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-an", str(seg))
        else:
            src = (out / s["file"]) if s["kind"] == "broll" else (vm / "clips" / f"{s['clip']}.mp4")
            clen = dur(src)
            start = max(0.0, min(float(s.get("in") or 0), max(0.0, clen - 0.05)))
            slow = f"setpts=PTS/{sp}," if abs(sp - 1) > 1e-3 else ""
            move = push(n) if still(src, start, n / FPS * sp) else ""
            # tpad holds the last frame if a source runs a hair short (never black)
            ff("-ss", f"{start:.3f}", "-i", str(src), "-frames:v", str(n),
               "-vf", f"{slow}{crop_filter(s)},fps={FPS}{move},tpad=stop_mode=clone:stop_duration=2,format=yuv420p",
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


def draw_state(state: dict) -> Image.Image:
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for t in state.get("texts") or []:
        if t["kind"] not in ("hook headline", "option card"):
            continue
        lk = look(t["kind"], t.get("look_id"))
        ft = font(lk["size"], lk["font"])
        lines = []
        for w in t["words"]:
            lines += _wrap(w.upper() if lk.get("upper") else w, ft, lk["max_w"], d)
        draw_block(d, lines, lk, H * float(t.get("y") or lk["y"]))
    c = state.get("caption")
    if c:                                                     # the caption look the ad names (default: IG/FB native)
        lk = caption_look(state.get("caption_look"))
        ft = font(lk["size"], lk["font"])
        lines = _wrap(c["text"], ft, lk["max_w"], d)
        cy_ = float(c.get("y") or lk["y"])
        y = H * (lk["y_closeup"] if cy_ > 0.8 else min(cy_, lk["y"]))   # over a close-up: low, just above the feed buttons
        for k, l in enumerate(lines):
            tw = d.textlength(l, font=ft); x0 = (W - tw) / 2; yk = y + k * lk["line_h"]
            _box(d, (x0 - 22, yk - 8, x0 + tw + 22, yk + lk["size"] + 10), lk["radius"], _rgba(lk["box"]))
            d.text((x0, yk), l, font=ft, fill=_rgba(lk["fill"]))
    return im


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
    per = per or caption_look((m.get("captions") or {}).get("look_id"))["words"]
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


def render_words(m: dict, work: Path, timed: dict | None = None) -> Path:
    caps = caption_chunks(m, timed=timed)
    texts = m.get("text") or []
    edges = sorted({0.0, m["total"]} | {round(x, 3) for c in caps for x in (c["a"], c["b"])} |
                   {round(x, 3) for t in texts for x in (t["a"], t["b"])})
    lst, cache = [], {}
    for a, b in zip(edges, edges[1:]):
        if b - a < 1 / FPS / 2:
            continue
        mid = (a + b) / 2
        st = {"texts": [t for t in texts if t["a"] <= mid < t["b"]],
              "caption": next((c for c in caps if c["a"] <= mid < c["b"]), None),
              "caption_look": (m.get("captions") or {}).get("look_id")}
        key = json.dumps(st, sort_keys=True)
        if key not in cache:
            f = work / f"w{len(cache):04d}.png"; draw_state(st).save(f); cache[key] = f
        lst.append((cache[key], b - a))
    txt = work / "words.txt"
    txt.write_text("".join(f"file '{f}'\nduration {d:.4f}\n" for f, d in lst) + f"file '{lst[-1][0]}'\n")
    words = work / "words.mov"
    ff("-f", "concat", "-safe", "0", "-i", str(txt), "-vf", f"fps={FPS},format=rgba", "-c:v", "png", "-t", f"{m['total']:.3f}",
       str(words))
    return words


# ------------------------------------------------------------------ sound

# a quiet room: soft brown noise, rumble and hiss cut, at ROOM_DB — so no pause is ever digital silence (the swipe's
# quietest moment is -41 dB; ours had 79 blocks at -127 dB)
ROOM_CHAIN = ("[{i}:a]highpass=f=90,lowpass=f=2800,aformat=channel_layouts=mono,"
              f"volume={10 ** ((ROOM_DB + 28) / 20):.5f}[r]")      # the noise alone sits at about -28 dB RMS


def room_in(m: dict) -> list[str]:
    return ["-f", "lavfi", "-t", f"{m['total'] + 0.5:.3f}", "-i", "anoisesrc=color=brown:amplitude=0.25:sample_rate=44100:seed=7"]


def render_sound(vm: Path, out: Path, m: dict, work: Path) -> Path:
    voice = LI.mix(vm, out, m)                                # the cut's voices, exactly as the clean pass hears them
    mus = m.get("music") or {}
    final = work / "sound.wav"
    if mus.get("made") and (out / mus["file"]).exists():
        talk = "+".join(f"between(t,{max(0, l['a'] - 0.1 - mus['a']):.3f},{l['b'] + 0.1 - mus['a']:.3f})"
                        for l in m["voice"] + m["sounds"]) or "0"
        under, pause = 10 ** (mus["under_voice_db"] / 20), 10 ** (mus["in_pauses_db"] / 20)
        mlen = mus["b"] - mus["a"]
        mchain = (f"[1:a]atrim=0:{mlen:.3f},aresample=44100,aformat=channel_layouts=mono,"
                  f"volume='if(gt({talk},0),{under:.4f},{pause:.4f})':eval=frame,"
                  f"afade=t=out:st={max(0, mlen - 1.5):.3f}:d=1.5,adelay={int(mus['a'] * 1000)}:all=1[m]")
        ff("-i", str(voice), "-i", str(out / mus["file"]), *room_in(m), "-filter_complex",
           f"{mchain};{ROOM_CHAIN.format(i=2)};[0:a][m][r]amix=inputs=3:normalize=0,atrim=0:{m['total']:.3f},"
           f"loudnorm=I={MIX['loudness_lufs']}:TP={MIX['true_peak_db']}:LRA=11[o]", "-map", "[o]", "-ar", "48000", str(final))
    else:
        ff("-i", str(voice), *room_in(m), "-filter_complex",
           f"{ROOM_CHAIN.format(i=1)};[0:a][r]amix=inputs=2:normalize=0,atrim=0:{m['total']:.3f},loudnorm=I={MIX['loudness_lufs']}:TP={MIX['true_peak_db']}:LRA=11[o]",
           "-map", "[o]", "-ar", "48000", str(final))
    return final


# ------------------------------------------------------------------ one version

def render(vm: Path, out: Path, m: dict, name: str, draft: bool = False) -> Path:
    dest = out / "renders"; dest.mkdir(parents=True, exist_ok=True)
    crf = 26 if draft else 18
    with tempfile.TemporaryDirectory() as t:
        work = Path(t)
        talking_only_when_talking(out, m, name)            # refuses if the lead's mouth shows talking with no voice of theirs
        timed, _ = hear(vm, out, m, name)                   # refuses before a frame is made if a word is cut off
        pic = render_picture(vm, out, m, work, crf)
        words = render_words(m, work, timed)
        sound = render_sound(vm, out, m, work)
        mp4 = dest / f"{name}.mp4"
        ff("-i", str(pic), "-i", str(words), "-i", str(sound), "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
           "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{m['total']:.3f}", str(mp4))
    sync = lips(vm, m, mp4)
    if sync["held"]:
        mp4.rename(mp4.with_suffix(".held.mp4"))
        raise SystemExit(f"HELD {name}: the picture has slipped {sync['worst_s'] * FPS:.0f} frame(s) against the voice — "
                         f"see renders/{name}.held.mp4; nothing is delivered from a held render")
    (dest / f"{name}.json").write_text(json.dumps({"version": name, "hook": m.get("hook"), "seconds": m["total"],
                                                   "from": "edit-map" + (f"-{name}" if name != "control" else "") + ".json",
                                                   "size": [W, H], "fps": FPS, "loudness": "-14 LUFS / -1 dBTP",
                                                   "lips": sync}, indent=1))
    print(f"  lips: {sync['checked']} talking shots checked, worst {sync['worst_s'] * FPS:.0f} frame(s) off"
          + ("  — HELD: the picture has slipped against the voice" if sync["held"] else ""))
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
        lg = SC.picture_lag(mp4, t, vm / "clips" / f"{s['clip']}.mp4", s["in"] + 0.2 * float(s.get("speed") or 1),
                            crop_filter(s))
        if lg is not None:
            rows.append({"at": round(s["a"], 2), "clip": s["clip"], "late_s": lg})
    worst = max((abs(r["late_s"]) for r in rows), default=0.0)
    return {"checked": len(rows), "worst_s": worst, "held": worst > 1.5 / FPS, "shots": rows}


def talking_only_when_talking(out: Path, m: dict, name: str) -> None:
    """mouths.py over what will be on screen: her mouth moving with no voice of hers, or her voice over a mouth that
    isn't saying it, refuses the render (the owner, 4 Oct: "you're showing her talking when she should not be talking")."""
    import mouths as MO
    tracks = {f.stem: json.loads(f.read_text()) for f in (out / "tracks").glob("*.json")}
    if not tracks:
        return
    found = MO.reviewed(MO.check(m, tracks, MO.lead_of(m)), out)
    if found:
        raise SystemExit(f"HELD {name}: the lead's mouth and the sound disagree — " + "; ".join(
            f"{f['a']:.1f}s {f['kind'].lower()} ({f['line']})" for f in found) + ". Cover it (close-up above the mouth, "
            "B-roll) — machine/mouths.py lists them.")


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
    dec_f = out / "decisions.json"
    allowed = {LI._norm(w) for c in ((json.loads(dec_f.read_text()).get("cut_words") or []) if dec_f.exists() else [])
               for w in str(c.get("words", "")).split()}
    cut = [f for f in found if f["what"] == "missing / clipped"
           and not all(LI._norm(w) in allowed for w in f["script"].split())]
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--only"); ap.add_argument("--draft", action="store_true")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    want = set(a.only.split(",")) if a.only else None
    for name, f in versions(out).items():
        if want and name not in want:
            continue
        m = json.loads(f.read_text())
        mp4 = render(vm, out, m, name, a.draft)
        print(f"rendered {name}: {mp4} · {dur(mp4):.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
