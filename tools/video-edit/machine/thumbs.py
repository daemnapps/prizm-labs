#!/usr/bin/env python3
"""thumbs.py — a designed thumbnail per version: the picture people see before the video plays (feed before autoplay,
autoplay off, the video tab, the end frame). the owner, 4 Oct 2026: "can we create unique thumbnails per creative … creative
diversity … what we need people to stop scrolling and watch."

    python3 thumbs.py <video-production-run> [--out <edit run dir>] [--only control,<hook>]

Per version (each edit-map*.json): a clean frame of that version — no captions, no headline — at the moment the ad's
decisions name (`thumbs.<version>.at`, seconds; default `thumbs.at`, else 1.0) — or any picture it names
(`thumbs.<version>.frame`: {clip | file, t, scale, x, y}) so each version can show something different, with that version's own thumbnail words
(`thumbs.<version>.text`, written by the copy step; none = a clean frame) set in a look from looks/edit-looks.json
(`thumbs.look`, default `thumb-bold`), inside the safe zone (clear of the feed's top and bottom bars), at the height the picture leaves free: the scene is
read (faces, lips, hands, what draws the eye) and the card goes where it covers none of them, nearest the look's spot. Writes
renders/<version>_thumb.jpg, 1080x1920, and checks it (9:16, under 10 MB). line.py files each one with its video;
Meta shows it as that video's thumbnail. Nothing about one ad lives here.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_map as RM  # noqa: E402  (the same shots, crop maths and looks the render uses)

MAX_BYTES = 10_000_000


def frame_at(vm: Path, out: Path, m: dict, t: float, dest: Path) -> None:
    """The clean picture on screen at second t of this version (the shot under the captions)."""
    s = next((x for x in RM.flatten(m) if x["a"] <= t < x["b"]), None) or RM.flatten(m)[0]
    src = (out / s["file"]) if s["kind"] == "broll" else (vm / "clips" / f"{s['clip']}.mp4")
    at = float(s.get("in") or 0) + (t - s["a"]) * float(s.get("speed") or 1)
    RM.ff("-ss", f"{max(0.0, at):.3f}", "-i", str(src), "-frames:v", "1", "-vf", RM.crop_filter(s), "-q:v", "2", str(dest))


SAFE = {"x0": 0.06, "x1": 0.94, "y0": 0.125, "y1": 0.875}   # clear of the sides; inside the 3:4 grid crop (top and bottom 12.5% cut)


# What the words may not cover, and how much each matters (the owner, 4 Oct 2026: "take the time to analyze the scene,
# then implement"). Lips worst, then the face, then hands (they carry the action: the doctor's touch, the product).
COVER_COST = {"lips": 25.0, "faces": 8.0, "hands": 4.0, "salient": 0.5}
GAP = 0.012          # keep this much clear around a face, lips or hand (share of the height)
DRIFT = 2.0          # cost per unit of height the card moves from the look's own spot (keeps covers consistent)


def scene(frame: Path) -> dict:
    """Faces (and their lips), hands and what draws the eye in this picture: macOS Vision, local and free."""
    tool = HERE / "vision" / ".build" / "scene"
    if not tool.exists() or tool.stat().st_mtime < (HERE / "vision" / "scene.swift").stat().st_mtime:
        tool.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(HERE / "vision" / "scene.swift"), "-o", str(tool)], check=True)
    r = subprocess.run([str(tool), str(frame)], capture_output=True, text=True)
    s = json.loads(r.stdout or "{}")
    return {"lips": [f["lips"] for f in s.get("faces", []) if f.get("lips")],
            "faces": [f["box"] for f in s.get("faces", [])],
            "hands": s.get("hands", []), "salient": s.get("salient", [])}


def place(sc: dict, card_w: float, card_h: float, prefer: float) -> tuple[float, dict]:
    """The card's top (share of the height): inside the safe area, covering the least of what matters, nearest the
    look's own spot. Returns it and what it still covers (shares of the card's area), for the record."""
    W, H = RM.W, RM.H
    x0, x1 = (W - card_w) / 2 / W, (W + card_w) / 2 / W
    h = card_h / H

    def over(y, b, gap):
        bx0, by0, bx1, by1 = b["x"], b["y"] - gap, b["x"] + b["w"], b["y"] + b["h"] + gap
        ix = max(0.0, min(x1, bx1) - max(x0, bx0)); iy = max(0.0, min(y + h, by1) - max(y, by0))
        return ix * iy / ((x1 - x0) * h)

    best = None
    y = SAFE["y0"]
    while y + h <= SAFE["y1"] + 1e-9:
        hits = {k: sum(over(y, b, 0 if k == "salient" else GAP) for b in sc.get(k, [])) for k in COVER_COST}
        cost = sum(COVER_COST[k] * v for k, v in hits.items()) + DRIFT * abs(y - prefer)
        if best is None or cost < best[0]:
            best = (cost, y, hits)
        y += 0.005
    return round(best[1], 3), {k: round(v, 3) for k, v in best[2].items() if v}


def design(frame: Path, text: str | None, look_id: str | None, dest: Path, y: float | None = None) -> dict:
    """The picture, with its words set in the look, and where the card landed. `y` (share of the height) places the
    card's top; default: read the scene and put it where it covers no lips, face or hands, nearest the look's own
    spot. Returns the card box and the placement record for the checks."""
    im = Image.open(frame).convert("RGB").resize((RM.W, RM.H))
    placed = {}
    if text:
        lk = RM.LOOKS["text"].get(look_id or "") or RM.LOOKS["text"][RM.LOOKS["defaults"].get("thumb", "thumb-bold")]
        d = ImageDraw.Draw(im, "RGBA")
        lk, lines = fit(text, lk, d)
        record = {"y_from": "decisions"}
        if y is None:
            trial = RM.draw_block(ImageDraw.Draw(Image.new("RGBA", (RM.W, RM.H)), "RGBA"), lines, lk, 0)
            bx0, by0, bx1, by1 = trial["box"]
            sc = scene(frame)
            y, covers = place(sc, bx1 - bx0, by1 - by0, float(lk["y"]))
            record = {"y_from": "scene", "scene": sc, "still_covers": covers}
        placed = RM.draw_block(d, lines, lk, RM.H * float(y))
        placed["placement"] = {**record, "y": y}
    im.save(dest, "JPEG", quality=90, optimize=True)
    if dest.stat().st_size > MAX_BYTES:
        im.save(dest, "JPEG", quality=78, optimize=True)
    return placed


MAX_LINES, MIN_SCALE = 3, 0.8   # a cover reads in three lines or fewer; shrink to 80% of the look before going to four


def balanced(text: str, ft, maxw: float, d) -> list[str]:
    """The fewest lines that fit, with the words split so the lines are as even as they can be (no one word left
    alone on a line when a better split exists). Sentence ends are preferred break points."""
    words = text.split()
    n = len(RM._wrap(text, ft, maxw, d))
    best, best_cost = None, None

    def splits(i, k):
        if k == 1:
            yield [words[i:]]
            return
        for j in range(i + 1, len(words) - k + 2):
            for rest in splits(j, k - 1):
                yield [words[i:j]] + rest

    for parts in splits(0, n):
        lines = [" ".join(p) for p in parts]
        widths = [d.textlength(l, font=ft) for l in lines]
        if max(widths) > maxw:
            continue
        cost = max(widths) - min(widths) - 120 * sum(l.endswith((".", "?", "!")) for l in lines[:-1])
        if best_cost is None or cost < best_cost:
            best, best_cost = lines, cost
    return best or RM._wrap(text, ft, maxw, d)


def fit(text: str, lk: dict, d) -> tuple[dict, list[str]]:
    """The look and the lines for this text: balanced breaks, and if it runs past MAX_LINES, the look scaled down
    (size, outline, line height, padding together) until it fits, no further than MIN_SCALE. Line breaks written into
    the text ("\\n") are kept as the lines, shrinking the look if a line would otherwise wrap."""
    scale, out = 1.0, None
    while True:
        k = dict(lk, size=round(lk["size"] * scale), line_h=round(lk["line_h"] * scale),
                 stroke_w=round((lk.get("stroke_w") or 0) * scale), pad=[round(v * scale) for v in lk["pad"]])
        ft = RM.font(k["size"], k["font"])
        lines = []
        for part in text.split("\n"):
            lines += balanced(part.upper() if k.get("upper") else part, ft, k["max_w"], d)
        out = (k, lines)
        kept = "\n" not in text or len(lines) == text.count("\n") + 1   # breaks written into the text are the lines
        if (len(lines) <= MAX_LINES and kept) or scale <= MIN_SCALE + 1e-9:
            return out
        scale = max(MIN_SCALE, scale - 0.05)


def contained(placed: dict) -> list[str]:
    """Is the card inside the frame's safe area? Every miss, named."""
    if not placed:
        return []
    x0, y0, x1, y1 = placed["box"]
    bad = []
    if x0 < SAFE["x0"] * RM.W or x1 > SAFE["x1"] * RM.W:
        bad.append(f"card runs to the edge ({x0 / RM.W:.0%}–{x1 / RM.W:.0%} across; keep inside {SAFE['x0']:.0%}–{SAFE['x1']:.0%})")
    if y0 < SAFE["y0"] * RM.H or y1 > SAFE["y1"] * RM.H:
        bad.append(f"card outside the grid crop ({y0 / RM.H:.0%}–{y1 / RM.H:.0%} down; keep inside {SAFE['y0']:.0%}–{SAFE['y1']:.0%})")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--only")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    dec = json.loads((out / "decisions.json").read_text()) if (out / "decisions.json").exists() else {}
    th = dec.get("thumbs") or {}
    versions = {"control": out / "edit-map.json", **{f.stem[len("edit-map-"):]: f for f in sorted(out.glob("edit-map-*.json"))}}
    want = set(a.only.split(",")) if a.only else set(versions)
    (out / "renders").mkdir(exist_ok=True)
    log = {}
    for v, f in versions.items():
        if v not in want:
            continue
        m = json.loads(f.read_text())
        mine = th.get(v) or {}
        t = float(mine.get("at", th.get("at", 1.0)))
        dest = out / "renders" / f"{v}_thumb.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            fr = Path(tmp) / "frame.jpg"
            if mine.get("frame"):                       # a named picture: any clip, any second, an optional punch-in
                f_ = mine["frame"]
                src = (out / f_["file"]) if f_.get("file") else (vm / "clips" / f"{f_['clip']}.mp4")
                RM.ff("-ss", f"{float(f_.get('t', 1.0)):.3f}", "-i", str(src), "-frames:v", "1", "-vf", RM.crop_filter(f_), "-q:v", "2", str(fr))
            else:
                frame_at(vm, out, m, t, fr)
            placed = design(fr, mine.get("text"), mine.get("look") or th.get("look"), dest, mine.get("y"))
        w, h = Image.open(dest).size
        misses = contained(placed)
        if placed.get("placement"):
            log[v] = placed["placement"]
            cov = placed["placement"].get("still_covers") or {}
            if cov.get("lips") or cov.get("faces", 0) > 0.05:
                misses.append(f"no clear spot — the card would cover {'her lips' if cov.get('lips') else 'the face'}; name a y or another frame in decisions")
        ok = abs(w / h - 9 / 16) < 0.01 and dest.stat().st_size <= MAX_BYTES and not misses
        print(f"  {v:<8} {dest.name}  {w}x{h}  {dest.stat().st_size / 1e3:.0f} KB  {'text: ' + mine['text'][:40] if mine.get('text') else 'clean frame'}"
              + ("" if ok else "  — " + ("; ".join(misses) or "not 9:16 / too big")))
        if not ok:
            raise SystemExit(f"thumbs: {dest.name} failed its check")
    if log:   # what each cover's picture held and where the words went: the record to check a placement against
        (out / "renders" / "thumbs-placement.json").write_text(json.dumps(log, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
