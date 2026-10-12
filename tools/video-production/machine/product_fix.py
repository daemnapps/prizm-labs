"""THE PRODUCT FIX — a picture whose product fails product_check.py keeps
everything else and gets the real product: one edit on the ruled edit door,
the picture first, then the product's kit render (its exact 3D model) and its
real packshot, worded by image-edit's own "Wrong product" fix (the whole object
at its real size — 2026-10-02). Measured again after each try; two tries at
most; the closest take is kept. Brand-agnostic.

    python3 product_fix.py <picture.png> --kit <kit.json> [--out <out.png>]
"""
from __future__ import annotations

import argparse, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
FIXES = WS / "tools" / "image-edit" / "library" / "fixes-v3-damon.json"


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py"); m = u.module_from_spec(sp); sp.loader.exec_module(m); return m


def words(kit, shaped=False) -> str:
    d = json.loads(FIXES.read_text())
    rows = d if isinstance(d, list) else (d.get("fixes") or d.get("rows"))
    row = next(r for r in rows if r.get("id") == "product")
    want = kit["outline"].get("axis_ratio") or kit["outline"]["height_over_width"]
    s = kit.get("size_cm") or {}
    size = (f", about {s['height']:.0f} cm tall and {s['width']:.0f} cm wide" if s.get("height") and s.get("width") else "")
    ref2 = "the real product, cut out" if kit.get("status") == "photo-only" else "the exact 3D model"
    return ("Image 1 is the picture. " + row["delta"][0].upper() + row["delta"][1:]
            + f". The product photo is image 2 ({ref2}) and image 3 (the real packshot): {want:.2f} times as tall "
            + f"as it is wide{size}. "
            + ("The product in image 1 already has its real outline and size: keep that outline exactly, and redraw "
               "its label, cap and colour from image 3 so it reads as the one real product held in the hand, its edges and the fingers "
               "on it blended naturally. " if shaped else "")
            + "Keep exactly as they are: " + ", ".join(row.get("keep") or []) + ", everything else in the picture. Change nothing else.")


def reshape(picture, mask, want, out):
    """Puts the product at its real proportions BEFORE the edit: its own pixels
    (same light, same angle) widened across its long axis to the kit's ratio and
    laid back over the picture. A model told "make it shorter" redraws the same
    tube; a model handed the right outline keeps it (2026-10-02, S26)."""
    import math
    from PIL import Image, ImageFilter
    im = Image.open(picture).convert("RGB"); m = mask.convert("L")
    pc = _load("product_check"); ratio = pc.axis_ratio(m)
    if not ratio or ratio <= want:
        im.save(out); return ratio
    k = ratio / want
    W, H = m.size; px = m.load(); step = max(1, int(max(W, H) / 400))
    pts = [(x, y) for y in range(0, H, step) for x in range(0, W, step) if px[x, y] > 127]
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    ang = math.degrees(0.5 * math.atan2(2 * sxy, sxx - syy))     # long axis angle from +x
    turn = ang - 90 if ang > 0 else ang + 90                      # turn that stands it upright
    rgba = im.copy(); rgba.putalpha(m)
    up = rgba.rotate(turn, resample=Image.BICUBIC, center=(mx, my))
    wide = up.resize((int(W * k), H), Image.LANCZOS)
    left = int(mx * k - mx); wide = wide.crop((left, 0, left + W, H))
    back = wide.rotate(-turn, resample=Image.BICUBIC, center=(mx, my))
    a = back.getchannel("A").filter(ImageFilter.GaussianBlur(1.5)); back.putalpha(a)
    im.paste(back, (0, 0), back); im.save(out)
    return ratio


def fix(picture, kit_path, out=None, tries=2, transport=None, key=None, verdict=None):
    picture = Path(picture); out = Path(out or picture); kit_path = Path(kit_path)
    kit = json.loads(kit_path.read_text()); want = kit["outline"].get("axis_ratio") or kit["outline"]["height_over_width"]
    pc = _load("product_check"); do = _load("direct_openai")
    v = verdict or pc.check(picture, kit_path, what=kit.get("what", "the product"))
    takes = [(abs((v["shape"].get("measured") or want) - want), picture.read_bytes(), v)]
    src = picture
    for n in range(tries):
        if v["ok"]:
            break
        keep = out.parent / "versions" / f"{out.stem}-product-miss-{n + 1}.png"
        keep.parent.mkdir(parents=True, exist_ok=True); keep.write_bytes(src.read_bytes())
        shaped = keep.with_name(keep.stem + "-shaped.png")
        was = v["shape"].get("measured") or want
        if was > want * (1 + pc.TOL):
            reshape(keep, pc.product_mask(keep, v["found"]["box"]), want, shaped)
        else:
            shaped.write_bytes(keep.read_bytes())
        do.generate(words(kit, shaped=was > want * (1 + pc.TOL)), [shaped, kit_path.parent / "model" / "reference-front.png",
                                 kit_path.parent / kit["sources"][0]], out, transport=transport, key=key)
        v = pc.check(out, kit_path, what=kit.get("what", "the product")); src = out
        takes.append((abs((v["shape"].get("measured") or want) - want), out.read_bytes(), v))
    best = min(takes, key=lambda t: t[0]); out.write_bytes(best[1])
    return best[2]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("picture"); ap.add_argument("--kit", required=True); ap.add_argument("--out")
    x = ap.parse_args(); r = fix(x.picture, x.kit, x.out)
    print(json.dumps({"ok": r["ok"], "shape": r["shape"], "why": r["why"]}, indent=1))
