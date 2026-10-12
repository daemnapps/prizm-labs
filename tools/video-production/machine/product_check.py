"""THE PRODUCT CHECK — measures the product in a made picture against its kit
(product_kit.py) instead of guessing (the owner, 2026-10-02: "you should know what
it actually looks like … eliminate all product slop … at scale").

  shape   the product's height over width, against the kit's measured outline
          (front-facing; a turned product reads narrower, so only a TOO-TALL
          or TOO-WIDE front fails)
  label   the label's key words, read off the picture (macOS Vision text)
Returns {"ok", "shape": {...}, "label": {...}, "why": [...]}. Brand-agnostic.

    python3 product_check.py <picture.png> --kit <kit.json> [--what "the skincare tube"]
"""
from __future__ import annotations

import argparse, json, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOL = 0.12          # ±12% on height/width before it fails


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py"); m = u.module_from_spec(sp); sp.loader.exec_module(m); return m


def words_on(picture, box):
    """Text lines inside the box, via vision/readtext (macOS Vision)."""
    from PIL import Image
    import tempfile
    exe = HERE / "vision" / ".build" / "readtext"
    src = HERE / "vision" / "readtext.swift"
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], check=True, capture_output=True)
    im = Image.open(picture).convert("RGB"); W, H = im.size
    crop = im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))
    crop = crop.resize((crop.width * 2, crop.height * 2))
    with tempfile.NamedTemporaryFile(suffix=".png") as t:
        crop.save(t.name)
        out = subprocess.run([str(exe), t.name], capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


LS = HERE.parents[1].parent / "components" / "local-studio"


def product_mask(picture, box):
    """The product's own pixels (SAM 2.1, prompted by its box — the hand holding
    it is a separate object), as a PIL mask the size of the picture."""
    import subprocess, tempfile
    from PIL import Image
    im = Image.open(picture); W, H = im.size
    bx = f"{box[0] * W:.0f},{box[1] * H:.0f},{box[2] * W:.0f},{box[3] * H:.0f}"
    with tempfile.NamedTemporaryFile(suffix=".png") as t:
        subprocess.run([str(LS / ".venv" / "bin" / "python"), str(LS / "jobs" / "segment_image.py"), str(picture), t.name,
                        "--box", bx], check=True, capture_output=True)
        return Image.open(t.name).convert("L").copy()


def axis_ratio(mask):
    """Length over width of the mask along its own long axis — the same however it leans."""
    import math
    W, H = mask.size; step = max(1, int(max(W, H) / 400)); px = mask.load()
    pts = [(x, y) for y in range(0, H, step) for x in range(0, W, step) if px[x, y] > 127]
    if len(pts) < 50:
        return None
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy); ux, uy = math.cos(ang), math.sin(ang)
    a_ = sorted((p[0] - mx) * ux + (p[1] - my) * uy for p in pts)
    b_ = sorted(-(p[0] - mx) * uy + (p[1] - my) * ux for p in pts)
    q = lambda v, f: v[int(f * (len(v) - 1))]
    la, lb = q(a_, .995) - q(a_, .005), q(b_, .995) - q(b_, .005)
    return max(la, lb) / max(1e-6, min(la, lb))


def check(picture, kit_path, what="the product", caller=None):
    from PIL import Image
    kit = json.loads(Path(kit_path).read_text())
    im = Image.open(picture); W, H = im.size
    try:
        f = _load("product_kit").detect(picture, what, caller=caller)
    except AttributeError:                      # the reader found no product to box
        f = None
    if not f or not f.get("box"):
        return {"ok": True, "shape": {"measured": None, "note": "no product in this picture"}, "label": {}, "found": None, "why": []}
    mask = product_mask(picture, f["box"])
    ratio = axis_ratio(mask)
    want = kit["outline"].get("axis_ratio") or kit["outline"]["height_over_width"]
    why = []
    shape = {"measured": round(ratio, 2) if ratio else None, "kit": want, "facing": f.get("facing"), "lean": f.get("angle")}
    if ratio is None:
        shape["note"] = "leans too far to measure from its box"
    elif kit.get("shape_fixed") is False:
        shape["note"] = "soft goods — its shape is not fixed, so it is not measured"
    elif f.get("facing") in ("front", "back", None):
        if ratio > want * (1 + TOL):
            why.append(f"too tall and slim: {ratio:.2f}× as tall as wide, the real one is {want}×")
        elif ratio < want * (1 - TOL):
            why.append(f"too short and wide: {ratio:.2f}× as tall as wide, the real one is {want}×")
    lines = words_on(picture, f["box"])
    text = " ".join(lines).upper()
    key = [w.upper() for w in kit.get("label_words") or []]
    missing = [w for w in key if w not in text]
    if f.get("facing") in ("front", None) and missing:
        why.append("label words not found: " + ", ".join(missing))
    return {"ok": not why, "shape": shape, "label": {"read": lines, "missing": missing}, "found": f, "why": why}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("picture"); ap.add_argument("--kit", required=True); ap.add_argument("--what", default="the product")
    x = ap.parse_args(); print(json.dumps(check(x.picture, x.kit, x.what), indent=1))
