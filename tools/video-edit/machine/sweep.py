#!/usr/bin/env python3
"""sweep.py — the frame-by-frame sweep of an edit map, before anyone is shown the cut (the owner, 3 Oct 2026:
"you need to do a frame by frame sweep at this stage of editing, this is how we ensure it's ultra smooth").

    python3 sweep.py <video-production-run> [--out <edit run dir>] [--fps 4]

Pulls the frame that is ON SCREEN at every step of the cut (B-roll on top, else the picture, punch-ins
applied) straight from the source clips — no render — and writes into <out>/sweep/:
  strip-NN.jpg   the whole cut, a contact sheet per 10 s, each frame stamped with its time
  cuts.jpg       every cut: the frame just before | just after, side by side (the smoothness check)
  sweep.json     black or empty frames, frozen stretches, the cut list
A person then LOOKS at every sheet; the machine only finds the frames worth looking at.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat


def on_screen(m: dict, t: float):
    for r in m.get("broll") or []:
        if r["a"] <= t < r["b"]:
            if r.get("insert"):
                return ("clip", r["clip"], r.get("in", 0) + (t - r["a"]) * r.get("speed", 1), 1.0, None, f"insert {r['clip']}")
            return ("broll", r["file"], (t - r["a"]) * r.get("speed", 1), 1.0, None, f"B-roll {r['name']}")
    for p in m["picture"]:
        if p["a"] <= t < p["b"]:
            if p["kind"] == "plate":
                return ("plate", p.get("src"), 0, 1.0, None, "card")
            return ("clip", p["clip"], p["in"] + (t - p["a"]) * p.get("speed", 1), p.get("scale", 1.0), (p.get("y"), p.get("x")), p["clip"] + (" close" if p.get("closeup") else ""))
    return None


def grab(vm: Path, out: Path, what, w=180) -> Image.Image:
    kind, src, at, scale, y, _ = what
    f = {"clip": vm / "clips" / f"{src}.mp4", "broll": out / str(src), "plate": vm / str(src)}[kind]
    tmp = out / "sweep" / "_f.jpg"
    if kind == "plate":
        im = Image.open(f).convert("RGB")
    else:
        try:
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                       capture_output=True, text=True).stdout or 0)
            at = min(at, dur - 0.06) if dur else at       # a hair past the last frame is the last frame, never black
        except ValueError:
            pass
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0.0, at):.3f}", "-i", str(f), "-frames:v", "1",
                        "-vf", "scale=360:-2", str(tmp)], check=False)
        if not tmp.exists():
            return Image.new("RGB", (w, int(w * 16 / 9)), "black")
        im = Image.open(tmp).convert("RGB"); tmp.unlink()
    if scale and scale > 1.0:
        yy, xx = y if isinstance(y, tuple) else (y, None)
        W, H = im.size; cw, ch = W / scale, H / scale
        cy = (yy if yy is not None else 0.4) * H
        cx = (xx if xx is not None else 0.5) * W
        left = min(max(0, cx - cw / 2), W - cw)
        top = min(max(0, cy - ch / 2), H - ch)
        im = im.crop((left, top, left + cw, top + ch)).resize((W, H))
    return im.resize((w, int(w * im.size[1] / im.size[0])))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--fps", type=float, default=4.0)
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else Path(__file__).resolve().parents[3] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    m = json.loads((out / "edit-map.json").read_text())
    sw = out / "sweep"; sw.mkdir(parents=True, exist_ok=True)
    for old in sw.glob("strip-*.jpg"):
        old.unlink()
    step = 1.0 / a.fps
    frames, issues, prev = [], [], None
    t = 0.0
    while t < m["total"]:
        w = on_screen(m, t)
        im = grab(vm, out, w) if w else Image.new("RGB", (180, 320), "black")
        lum = ImageStat.Stat(im.convert("L")).mean[0]
        if w is None or lum < 12:
            issues.append({"t": round(t, 2), "what": "black / empty frame", "on": w[5] if w else None})
        frames.append((round(t, 2), im, w[5] if w else "NOTHING"))
        t += step
    # frozen: identical consecutive frames from a clip (a hold past its last frame)
    for (t1, i1, n1), (t2, i2, n2) in zip(frames, frames[1:]):
        if n1 == n2 and n1 not in ("card",) and i1.resize((16, 28)).tobytes() == i2.resize((16, 28)).tobytes():
            issues.append({"t": t2, "what": "frozen frame", "on": n2})
    per = int(10 * a.fps)
    for k in range(0, len(frames), per):
        grp = frames[k:k + per]; cols = 10
        rows = (len(grp) + cols - 1) // cols; fw, fh = 180, 320 + 16
        sheet = Image.new("RGB", (cols * fw, rows * fh), "white"); d = ImageDraw.Draw(sheet)
        for i, (tt, im, name) in enumerate(grp):
            x, y = (i % cols) * fw, (i // cols) * fh
            sheet.paste(im.crop((0, 0, 180, 320)), (x, y + 16)); d.text((x + 2, y + 2), f"{tt:.2f} {name[:18]}", fill="black")
        sheet.save(sw / f"strip-{k // per:02d}.jpg", quality=72)
    # every cut, before | after
    cuts = []
    edges = sorted({round(p["a"], 3) for p in m["picture"]} | {round(r["a"], 3) for r in m.get("broll") or []} |
                   {round(r["b"], 3) for r in m.get("broll") or []})
    for e in edges:
        if 0.05 < e < m["total"] - 0.05:
            b4, af = on_screen(m, e - 0.04), on_screen(m, e + 0.04)
            if b4 and af and (b4[1], round(b4[2] + 0.08, 1)) != (af[1], round(af[2], 1)):
                cuts.append((e, b4, af))
    cw, chh = 150, 267 + 14
    sheet = Image.new("RGB", (6 * (2 * cw + 10), ((len(cuts) + 5) // 6) * chh), "white"); d = ImageDraw.Draw(sheet)
    for i, (e, b4, af) in enumerate(cuts):
        x, y = (i % 6) * (2 * cw + 10), (i // 6) * chh
        sheet.paste(grab(vm, out, b4, cw).crop((0, 0, cw, 267)), (x, y + 14))
        sheet.paste(grab(vm, out, af, cw).crop((0, 0, cw, 267)), (x + cw, y + 14))
        d.text((x + 2, y + 1), f"{e:.2f} {b4[5][:10]}>{af[5][:10]}", fill="black")
    sheet.save(sw / "cuts.jpg", quality=72)
    rep = {"frames": len(frames), "fps": a.fps, "cuts": [{"t": e, "from": b[5], "to": f[5]} for e, b, f in cuts], "issues": issues}
    (sw / "sweep.json").write_text(json.dumps(rep, indent=1))
    print(f"sweep: {len(frames)} frames · {len(cuts)} cuts · {len(issues)} issue(s) → {sw}")
    for x in issues[:30]:
        print(f"  {x['t']:7.2f}s  {x['what']}  ({x['on']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
