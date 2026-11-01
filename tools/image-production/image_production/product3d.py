"""THE PRODUCT FROM ITS 3D MODEL — the image model never draws the product.

the owner, 2026-10-14: "you need to use the 3d models moving forward for product
because its the foundation of everything now." The picture model kept drawing
the product wrong (stood up on a round bottom it cannot stand on, the wrong
shape, invented details). So when a request names a product whose kit carries a
3D model, the scene is made WITHOUT the product, and the product is RENDERED
from its kit's model at the pose and camera the scene needs, then composited in.

    render_product(kit, pose, camera, out_png, size_px)   the product, posed, on transparent
    place_product(scene, render, out_png, box= | anchor= + px_per_cm=)
                                                          composited: contact shadow,
                                                          light and colour matched, grain matched
    silhouette_iou(kit, angles)                           render vs the real turntable cut-out
    find_kit(brand, product) / declaration(kit)           which kit, and what it declares

The kit says how its product may be shown in `model/render3d.json` (the model
file, its poses — each pose one of the kit's `behaviour.rests` — and any holder
the pose rests it in). Nothing here names a brand, a product or a model; every
number is the kit's or the caller's. Blender runs as a sub-process
(`bpy_scripts/render_product_bpy.py`). Stdlib + Pillow only, Python 3.9.
"""
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import paths as P

HERE = Path(__file__).resolve().parent
BPY = HERE / "bpy_scripts" / "render_product_bpy.py"
DECLARATION = "model/render3d.json"


def blender():
    return os.environ.get("BLENDER") or shutil.which("blender") or "/opt/homebrew/bin/blender"


# ── which kit, and what it declares ──────────────────────────────────────────
def bank():
    return P.repo() / "runs" / "ai-elements"


def find_kit(brand, product, root=None):
    """The kit folder for a product the brand names (folder name or a kit alias)."""
    if not product:
        return None
    base = Path(root or bank()) / brand / "products"
    if not base.is_dir():
        return None
    key = str(product).lower()
    for kit in sorted(p for p in base.iterdir() if p.is_dir()):
        kj = kit / "kit.json"
        if not kj.is_file():
            continue
        try:
            k = json.loads(kj.read_text())
        except ValueError:
            continue
        names = {kit.name.lower()} | {str(a).lower() for a in (k.get("aliases") or [])}
        if key in names:
            return kit
    return None


def declaration(kit):
    """The kit's 3D declaration, or None when it has none (or its model file is missing)."""
    if kit is None:
        return None
    f = Path(kit) / DECLARATION
    if not f.is_file():
        return None
    d = json.loads(f.read_text())
    if d.get("status") == "deprecated":
        return None
    blend = (Path(kit) / d["model"]["blend"]).resolve()
    if not blend.is_file():
        return None
    return d


def has_model(kit):
    return declaration(kit) is not None


def kit_facts(kit):
    try:
        return json.loads((Path(kit) / "kit.json").read_text())
    except (OSError, ValueError):
        return {}


# ── render ───────────────────────────────────────────────────────────────────
def _alpha_bbox(im, threshold=8):
    a = im.getchannel("A").point(lambda v: 255 if v > threshold else 0)
    return a.getbbox()


def render_product(kit, pose=None, camera=None, out_png=None, size_px=1024, light=None,
                   samples=64, shadow=True, timeout=600):
    """Render the product from its kit's 3D model on a transparent background.

    pose    a pose id the kit declares (default: the kit's `default_pose`)
    camera  {azimuth, elevation, focal_mm, ortho} — degrees; azimuth 0 = the
            product's face toward camera, + = camera moves to the product's left
    light   {azimuth, elevation, warmth -1..1, strength, ambient} — azimuth is
            relative to the camera, negative = light from screen-left

    Writes out_png (product + its contact shadow, cropped to content),
    `<stem>-mask.png` (product alone) and `<stem>.json` (the record). Returns the
    record. A pose whose holder cannot be built falls back to the pose's declared
    real cut-out, and the record says so."""
    from PIL import Image

    kit = Path(kit)
    d = declaration(kit)
    if d is None:
        raise FileNotFoundError(f"{kit} declares no 3D model ({DECLARATION})")
    pid = pose or d.get("default_pose")
    poses = d.get("poses") or {}
    if pid not in poses:
        raise KeyError(f"pose `{pid}` is not declared — have: {', '.join(sorted(poses))}")
    p = poses[pid]
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    model = dict(d["model"])
    if p.get("model"):
        model.update(p["model"])
    model["blend"] = str((kit / model["blend"]).resolve())
    work = Path(tempfile.mkdtemp(prefix="render3d-"))
    spec = {
        "model": model,
        "holder": p.get("holder"),
        "pose": {"tilt_back_deg": p.get("tilt_back_deg", 0.0), "yaw_deg": p.get("yaw_deg", 0.0)},
        "camera": dict({"azimuth": 0.0, "elevation": 8.0, "focal_mm": 50.0}, **(camera or {})),
        "light": dict(d.get("light") or {}, **(light or {})),
        "size_px": int(size_px), "samples": int(samples), "shadow": bool(shadow),
        "out": str(work / "full.png"), "mask_out": str(work / "mask.png"),
        "meta_out": str(work / "meta.json"),
    }
    (work / "spec.json").write_text(json.dumps(spec, indent=1))
    rec = {"kit": str(kit), "pose": pid, "rest": p.get("rest"), "spec": spec,
           "source": "3d-model", "fallback": None}
    try:
        r = subprocess.run([blender(), "-b", "--python", str(BPY), "--", str(work / "spec.json")],
                           capture_output=True, text=True, timeout=timeout)
        ok = "RENDER3D-OK" in r.stdout and (work / "mask.png").is_file()
        if not ok:
            raise RuntimeError((r.stdout[-1500:] + r.stderr[-1500:]).strip())
    except Exception as e:                                   # noqa: BLE001
        fb = p.get("fallback_cutout")
        if not fb or not (kit / fb).is_file():
            raise
        rec.update(source="fallback-cutout", fallback=str(kit / fb),
                   why=f"the 3D render did not run: {str(e)[:300]}")
        im = Image.open(kit / fb).convert("RGBA")
        im.save(out_png)
        im.save(out_png.with_name(out_png.stem + "-mask.png"))
        bb = _alpha_bbox(im)
        rec.update(file=str(out_png), mask=str(out_png.with_name(out_png.stem + "-mask.png")),
                   contact_px=[(bb[0] + bb[2]) / 2.0, bb[3]], px_per_cm=None,
                   real_height_cm=p.get("fallback_height_cm"))
        out_png.with_suffix(".json").write_text(json.dumps(rec, indent=1))
        return rec

    meta = json.loads((work / "meta.json").read_text())
    mask = Image.open(work / "mask.png").convert("RGBA")
    full = Image.open(work / "full.png").convert("RGBA") if shadow else mask
    bb = _alpha_bbox(full) or _alpha_bbox(mask)
    pad = 4
    bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(full.width, bb[2] + pad),
          min(full.height, bb[3] + pad))
    full.crop(bb).save(out_png)
    mask_png = out_png.with_name(out_png.stem + "-mask.png")
    mask.crop(bb).save(mask_png)
    cx, cy = meta["contact_px"]
    rec.update(file=str(out_png), mask=str(mask_png), crop=list(bb),
               contact_px=[cx - bb[0], cy - bb[1]],
               px_per_cm=meta["px_per_cm_at_contact"], assembly_cm=meta["assembly_cm"],
               camera=meta["camera"], light=meta["light"])
    out_png.with_suffix(".json").write_text(json.dumps(rec, indent=1))
    shutil.rmtree(work, ignore_errors=True)
    return rec


# ── measured against the real thing ──────────────────────────────────────────
def _mask_of(im, size=256):
    """Alpha mask, cropped to content, fitted into a size×size square by height."""
    from PIL import Image
    a = im.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 127 else 0)
    bb = a.getbbox()
    a = a.crop(bb)
    s = (size - 8) / float(max(a.width, a.height))
    a = a.resize((max(1, int(a.width * s)), max(1, int(a.height * s))))
    sq = Image.new("L", (size, size), 0)
    sq.paste(a, ((size - a.width) // 2, size - 4 - a.height))
    return sq


def iou(a, b):
    from PIL import ImageChops
    inter = ImageChops.multiply(a, b).point(lambda v: 255 if v > 127 else 0)
    union = ImageChops.lighter(a, b)
    ni = sum(1 for v in inter.getdata() if v)
    nu = sum(1 for v in union.getdata() if v)
    return ni / float(nu) if nu else 0.0


def silhouette_iou(kit, angles=(0, 45, 90, 180), out_dir=None, size_px=600):
    """Render the bare model at each turntable angle (orthographic, level) and
    score its silhouette against the kit's real cut-out at that angle. Both are
    cropped to content and scaled to the same height, so the score is SHAPE."""
    from PIL import Image
    kit = Path(kit)
    d = declaration(kit)
    tt = d.get("turntable") or {}
    pattern = tt.get("pattern", "sources/turntable-{:03d}.png")
    sign = float(tt.get("sign", 1.0))
    measure = tt.get("pose", "bare")
    # the real frame's TRUE angle when the kit indexed its turntable (frame 60 may sit at 64.5)
    true = {}
    if tt.get("index") and (kit / tt["index"]).is_file():
        true = {int(k): float(v.get("angle", k)) for k, v in json.loads((kit / tt["index"]).read_text()).items()}
    out_dir = Path(out_dir or tempfile.mkdtemp(prefix="iou-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for ang in angles:
        real = kit / pattern.format(int(ang))
        if not real.is_file():
            rows.append({"angle": ang, "iou": None, "why": f"no real cut-out {real.name}"})
            continue
        rec = render_product(kit, measure, {"azimuth": sign * true.get(int(ang), ang), "elevation": 0.0, "ortho": True},
                             out_dir / f"model-{int(ang):03d}.png", size_px=size_px, samples=8,
                             shadow=False)
        m = _mask_of(Image.open(rec["mask"]))
        r = _mask_of(Image.open(real))
        score = iou(m, r)
        side = Image.new("RGB", (512, 256), "white")
        side.paste(Image.merge("RGB", (r, m, m)), (0, 0))
        from PIL import ImageChops
        side.paste(Image.merge("RGB", (ImageChops.invert(r), ImageChops.invert(m),
                                       ImageChops.invert(ImageChops.lighter(r, m)))), (256, 0))
        side.save(out_dir / f"overlay-{int(ang):03d}.png")
        rows.append({"angle": ang, "true_angle": true.get(int(ang), ang), "iou": round(score, 4), "real": str(real),
                     "model": rec["mask"], "overlay": str(out_dir / f"overlay-{int(ang):03d}.png")})
    good = [r["iou"] for r in rows if r.get("iou") is not None]
    return {"angles": rows, "mean": round(sum(good) / len(good), 4) if good else None}


# ── place it in the scene ────────────────────────────────────────────────────
def _stats(img, box):
    from PIL import ImageStat
    reg = img.crop(box).convert("RGB")
    st = ImageStat.Stat(reg)
    lum = ImageStat.Stat(reg.convert("L"))
    return st.mean, lum.mean[0], lum.stddev[0]


def _noise_level(img, box):
    """How grainy the scene is around the spot: the spread of a pixel against its blurred self."""
    from PIL import ImageChops, ImageFilter, ImageStat
    reg = img.crop(box).convert("L")
    diff = ImageChops.difference(reg, reg.filter(ImageFilter.GaussianBlur(1.2)))
    return ImageStat.Stat(diff).mean[0]


def place_product(scene_png, render, out_png, box=None, anchor=None, px_per_cm=None,
                  height_px=None, shadow=0.75, contact=0.55, match=0.35, grain=True,
                  soften=0.6, seed=7):
    """Composite a rendered product into a scene.

    Where and how big — one of:
      box=(l, t, r, b)                fit the render inside the box, contact point on its bottom
      anchor=(x, y) + px_per_cm=k     the contact point lands on (x, y); size from the REAL
                                      size: the render's own px-per-cm at its contact point
                                      is rescaled to the scene's k
      anchor=(x, y) + height_px=h     the contact point on (x, y), the render h px tall
    render is the record from render_product (or a path to its png).

    Then: its contact shadow (from the render) plus a soft contact pool under it;
    its light and colour pulled toward the scene around the spot (`match` 0..1);
    the scene's grain laid over it; edges softened to the scene's sharpness."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    rec = render if isinstance(render, dict) else json.loads(Path(render).with_suffix(".json").read_text())
    scene = Image.open(scene_png).convert("RGBA")
    full = Image.open(rec["file"]).convert("RGBA")
    mask = Image.open(rec["mask"]).convert("RGBA")
    cx, cy = rec["contact_px"]

    mbb = _alpha_bbox(mask, 40) or (0, 0, mask.width, mask.height)
    if box is not None:
        # fitted by the PRODUCT's own outline (not its shadow), centred in the box
        l, t, r, b = box
        s = min((r - l) / float(mbb[2] - mbb[0]), (b - t) / float(mbb[3] - mbb[1]))
        ax, ay = (l + r) / 2.0, (t + b) / 2.0
    elif anchor is not None and px_per_cm and rec.get("px_per_cm"):
        s = float(px_per_cm) / float(rec["px_per_cm"])
        ax, ay = anchor
    elif anchor is not None and height_px:
        s = float(height_px) / float(mask.height)
        ax, ay = anchor
    else:
        raise ValueError("place_product needs box=, or anchor= with px_per_cm= or height_px=")

    w, h = max(1, int(round(full.width * s))), max(1, int(round(full.height * s)))
    full = full.resize((w, h), Image.LANCZOS)
    mask = mask.resize((w, h), Image.LANCZOS)
    if box is None:
        ox, oy = int(round(ax - cx * s)), int(round(ay - cy * s))
    else:
        ox = int(round(ax - (mbb[0] + mbb[2]) / 2.0 * s))
        oy = int(round(ay - (mbb[1] + mbb[3]) / 2.0 * s))

    # the spot's surroundings: a ring around where the product lands
    ring = (max(0, ox - w // 2), max(0, oy - h // 4), min(scene.width, ox + w + w // 2),
            min(scene.height, oy + h + h // 4))
    mean_rgb, lum, _ = _stats(scene, ring)

    prod_alpha = mask.getchannel("A")
    shadow_alpha = ImageChops.subtract(full.getchannel("A"), prod_alpha)

    # 1. the contact shadow: the render's cast shadow + a soft pool right under the contact
    layer = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    # the catcher leaves a faint veil over its whole frame; keep only real shadow,
    # and fade it out before the render's edge so no box ever shows
    floor = 14
    sh = shadow_alpha.point(lambda v: 0 if v <= floor else int((v - floor) * 255.0 / (255 - floor) * shadow))
    fade = Image.new("L", (w, h), 0)
    ix, iy = int(w * 0.08), int(h * 0.08)
    ImageDraw.Draw(fade).rectangle((ix, iy, w - ix, h - iy), fill=255)
    fade = fade.filter(ImageFilter.GaussianBlur(max(2, min(w, h) * 0.05)))
    sh = ImageChops.multiply(sh, fade)
    tone = tuple(int(c * 0.18) for c in mean_rgb[:3])
    layer.paste(Image.new("RGBA", (w, h), tone + (255,)), (ox, oy), sh)
    pool = Image.new("L", scene.size, 0)
    pw = w * 0.42
    ph = max(3.0, h * 0.035)
    pcx, pcy = ox + cx * s, oy + cy * s
    ImageDraw.Draw(pool).ellipse((pcx - pw, pcy - ph, pcx + pw, pcy + ph * 0.8),
                                 fill=int(255 * contact))
    pool = pool.filter(ImageFilter.GaussianBlur(max(2.0, ph * 1.2)))
    layer = Image.alpha_composite(layer, Image.merge("RGBA", (*Image.new("RGB", scene.size, tone).split(), pool)))
    out = Image.alpha_composite(scene, layer)

    # 2. the product's light and colour pulled toward the scene's
    prod = mask.convert("RGB")
    grey = sum(mean_rgb[:3]) / 3.0 or 1.0
    tint = [1.0 + match * ((c / grey) - 1.0) for c in mean_rgb[:3]]
    gain = 1.0 + match * 0.5 * ((lum / 128.0) - 1.0)
    gain = max(0.85, min(1.25, gain))      # never so dark the bristle face reads as a smooth shell
    chans = [ch.point(lambda v, k=tint[i] * gain: max(0, min(255, int(v * k))))
             for i, ch in enumerate(prod.split())]
    prod = Image.merge("RGB", chans)

    # 3. the scene's grain, and its sharpness
    if soften:
        prod = prod.filter(ImageFilter.GaussianBlur(soften))
    if grain:
        n = _noise_level(scene, ring)
        if n > 0.4:
            rnd = random.Random(seed)
            amp = n * 1.6
            noise = Image.new("L", (w, h))
            noise.putdata([max(0, min(255, int(128 + rnd.gauss(0, amp)))) for _ in range(w * h)])
            prod = Image.merge("RGB", [ImageChops.add(c, noise, 1.0, -128) for c in prod.split()])
    edge = prod_alpha.filter(ImageFilter.GaussianBlur(0.7))
    out.paste(prod, (ox, oy), edge)
    out = out.convert("RGB")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    out.save(out_png)
    return {"file": str(out_png), "box": [ox, oy, ox + w, oy + h], "scale": s,
            "contact": [pcx, pcy], "tint": [round(t, 3) for t in tint], "gain": round(gain, 3)}


# ── the request side: what the engine calls ──────────────────────────────────
def wanted(req, brand):
    """(kit, declaration) when this request's product is drawn from its 3D model,
    else (None, None). On by default for a product whose kit has a model;
    `product_3d: False` on the request turns it off."""
    if req.get("product_3d") is False or not req.get("product") or req.get("from_image"):
        return None, None
    kit = find_kit(brand, req["product"])
    d = declaration(kit)
    if d is None:
        if req.get("product_3d") is True:
            raise FileNotFoundError(f"product_3d asked for, but `{req['product']}` has no kit "
                                    f"with a 3D model under {bank()}/{brand}/products/")
        return None, None
    return kit, d


# ── which pose, and is this a frame the model covers at all ─────────────────
HANDS = r"\b(hands?|held|holding|holds|grip|gripping|palm|fingers?)\b"
NO_HANDS = r"\bno (?:hands?|person|people|figures?|body parts?)\b"


def shows_hands(text):
    """Does the frame's own description put a hand in it? A "no hands" clause is not a hand."""
    import re
    t = re.sub(NO_HANDS, " ", str(text or ""), flags=re.I)
    return bool(re.search(HANDS, t, re.I))


def pose_for(decl, hands=False):
    """The pose the kit's behaviour allows for this frame: (pose id | None, why).

    Unheld, the kit's default pose (a product that cannot stand rests in its
    holder). Held, only a pose the kit declares `held: true` — the product in a
    hand is rendered only when the kit carries that pose; otherwise None, and
    the caller says so rather than inventing a grip."""
    poses = decl.get("poses") or {}
    if hands:
        held = [k for k, v in poses.items() if v.get("held") and not v.get("measure_only")]
        if held:
            return held[0], f"the frame has a hand in it — the kit's held pose `{held[0]}`"
        return None, ("the frame has a hand in it and the kit declares no held pose — "
                      "the 3D path cannot render a hand, so it is not used for this frame")
    return decl.get("default_pose"), "unheld — the kit's resting pose"


def not_covered(decl, text):
    """A frame that shows the product as something the model is not (its retail
    box, its packaging) is outside the 3D path: the kit lists those words in
    `not_covers`. Returns the reason, or None."""
    t = str(text or "").lower()
    for w in decl.get("not_covers") or []:
        if str(w).lower() in t:
            return f"the frame shows the product as `{w}` — the 3D model is the product itself, not that"
    return None


def zone_from_text(text):
    """A brief that already reserves the product's spot says so as
    `product_zone A–B% width, C–D% height`. Returns (l, t, r, b) fractions or None."""
    import re
    m = re.search(r"product[_ ]zone\D{0,12}(\d+)\s*[–-]\s*(\d+)%\s*width,\s*(\d+)\s*[–-]\s*(\d+)%\s*height",
                  str(text or ""), re.I)
    if not m:
        return None
    l, r, t, b = (int(v) / 100.0 for v in m.groups())
    return (l, t, r, b)


def size_words(facts):
    sc = facts.get("size_cm") or {}
    if sc.get("height"):
        return f"{sc['height'] * 10:.1f} mm tall" + (f", {sc['width'] * 10:.1f} mm wide" if sc.get("width") else "")
    return "its real size"


# ── where it goes, and how big, read off the scene ──────────────────────────
def _box(b, w, h):
    """[ymin, xmin, ymax, xmax] in 0–1000 → (l, t, r, b) pixels."""
    y0, x0, y1, x1 = (float(v) for v in b)
    return (x0 / 1000.0 * w, y0 / 1000.0 * h, x1 / 1000.0 * w, y1 / 1000.0 * h)


def locate(scene_png, what, size, ask, count=1, where=""):
    """Ask the eyes where the empty spot is and for a reference of known size.
    Returns {kind, spots: [(l, t, r, b) px], px_per_cm | None, reference, raw}.
    px_per_cm is the REFERENCE's box over its real size — the scene's own scale."""
    from PIL import Image
    from . import prompting
    q = (prompting.body(prompting.latest("product-locate"))
         .replace("{what}", what).replace("{size}", size)
         .replace("{count}", str(count)).replace("{where}", where or ""))
    raw = ask(Path(scene_png), q) or {}
    if isinstance(raw, list):                         # the eyes sometimes answer [ {...} ]
        raw = raw[0] if raw and isinstance(raw[0], dict) else {}
    w, h = Image.open(scene_png).size
    spots = [_box(s["box_2d"], w, h) for s in (raw.get("spots") or []) if s.get("box_2d")]
    ref = raw.get("reference") or None
    k = None
    if ref and ref.get("box_2d") and ref.get("real_cm"):
        l, t, r, b = _box(ref["box_2d"], w, h)
        px = (b - t) if str(ref.get("measure", "height")).startswith("h") else (r - l)
        if px > 4 and float(ref["real_cm"]) > 0:
            k = px / float(ref["real_cm"])
    return {"kind": raw.get("kind"), "spots": spots, "px_per_cm": k, "reference": ref, "raw": raw}


def judge_ask(entry=None, caller=None):
    """An `ask(image, question) -> dict` over this component's own judge door."""
    from . import judge, route as R

    def ask(img, question):
        text = (caller or judge.google_caller)(question, img, entry or R.judge_entry())
        text = text.strip().strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        try:
            return json.loads(text)
        except ValueError:
            i, j = text.find("{"), text.rfind("}")
            return json.loads(text[i:j + 1]) if i >= 0 else {}
    return ask


def plan(req, decl):
    """The placement this request asks for, with the kit's defaults under it.
    `product_place` (optional): {pose, x, y (fractions of the frame, the contact
    point), height (fraction of the frame height), px_per_cm, camera{}, light{}}."""
    p = dict(decl.get("place") or {})
    asked = req.get("product_place") or {}
    p.update(asked)
    # a request that names the spot is obeyed; otherwise the scene is read for it
    p["fixed"] = any(k in asked for k in ("x", "y", "height", "px_per_cm"))
    p.setdefault("pose", decl.get("default_pose"))
    p.setdefault("x", 0.5)
    p.setdefault("y", 0.72)
    p.setdefault("height", 0.3)
    return p


def spot_words(pl):
    """Plain words for where the product will go, for the scene prompt."""
    x, y = pl["x"], pl["y"]
    col = "left" if x < 0.38 else ("right" if x > 0.62 else "centre")
    row = "lower" if y > 0.62 else ("upper" if y < 0.38 else "middle")
    top = max(0.0, y - pl["height"] * 1.1)
    half_w = pl["height"] * 0.6
    return (f"the {row} {col} of the frame (from {int(max(0, x - half_w) * 100)}% to "
            f"{int(min(1, x + half_w) * 100)}% across, {int(top * 100)}% to {int(y * 100)}% down)")


GRAPHIC_FILL = 0.75     # a product panel in a layout: the product is 75% of its height, centred
GRAPHIC_LIGHT = {"azimuth": -30.0, "elevation": 50.0, "warmth": 0.15, "strength": 1.7,
                 "ambient": 0.16, "rim": 1.4}        # the shelf proof's light, rim lifted for a dark ground


def fill_box(box, frac=GRAPHIC_FILL):
    """The box a product fills inside a layout panel: frac of its height, centred."""
    l, t, r, b = box
    cx, cy, hh = (l + r) / 2.0, (t + b) / 2.0, (b - t) * frac / 2.0
    hw = (r - l) * 0.92 / 2.0
    return (cx - hw, cy - hh, cx + hw, cy + hh)


def place_located(scene_png, rec, out_png, loc, i=0, zone=None, graphic=False):
    """Place one render where `locate` (or a declared zone) says.

    A photo with a reference: the contact point is the spot's bottom centre and
    the size is the product's REAL size at the scene's own px-per-cm. A graphic,
    or a declared zone: fitted inside the box. Returns place_product's record
    plus how the size was decided."""
    from PIL import Image
    w, h = Image.open(scene_png).size
    if zone is not None:
        # A ZONE IS A LAYOUT PANEL, NOT A ROOM (the owner, 2026-10-14): there is no
        # real object to measure against, so the product fills it — 75% of its
        # height, centred — with no colour match (a dark ground would sink it
        # into a black egg) and no grain.
        l, t, r, b = zone
        box = (l * w, t * h, r * w, b * h) if max(zone) <= 1.0 else tuple(zone)
        got = place_product(scene_png, rec, out_png, box=fill_box(box), match=0.0,
                            grain=False, soften=0.3)
        got["size_from"] = f"{int(GRAPHIC_FILL * 100)}% of the product panel's height, centred"
        return got
    spots = loc.get("spots") or []
    spot = spots[min(i, len(spots) - 1)] if spots else None
    if spot and loc.get("px_per_cm") and loc.get("kind") != "graphic" and rec.get("px_per_cm"):
        anchor = ((spot[0] + spot[2]) / 2.0, spot[3])
        got = place_product(scene_png, rec, out_png, anchor=anchor, px_per_cm=loc["px_per_cm"])
        ref = loc.get("reference") or {}
        got["size_from"] = (f"real size against `{ref.get('name')}` "
                            f"({ref.get('real_cm')} cm {ref.get('measure', 'height')}) → "
                            f"{loc['px_per_cm']:.1f} px/cm")
        return got
    if spot and (graphic or loc.get("kind") == "graphic"):
        got = place_product(scene_png, rec, out_png, box=fill_box(spot), match=0.0,
                            grain=False, soften=0.3)
        got["size_from"] = f"{int(GRAPHIC_FILL * 100)}% of the located panel's height, centred"
        return got
    if spot:
        got = place_product(scene_png, rec, out_png, box=spot)
        got["size_from"] = "fitted to the located spot (no reference of known size)"
        return got
    raise ValueError("the scene gave no spot for the product")


def composite_into(scene_png, out_png, kit, pl, work_dir, ask=None):
    """Render the product for this placement and put it into the scene. Returns the record.
    With `ask` and no spot named by the request, the scene is read for the spot
    and for its scale (real size against a reference); else the plan's x/y/height."""
    from PIL import Image
    sc = Image.open(scene_png)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    rec = render_product(kit, pl.get("pose"), pl.get("camera"), work_dir / "product.png",
                         size_px=int(pl.get("size_px", 1024)), light=pl.get("light"),
                         samples=int(pl.get("samples", 64)))
    if ask is not None and not pl.get("fixed"):
        facts = kit_facts(kit)
        try:
            loc = locate(scene_png, facts.get("what") or "the product", size_words(facts), ask,
                         where="It goes in " + spot_words(pl) + ".")
            placed = place_located(scene_png, rec, out_png, loc)
            (work_dir / "locate.json").write_text(json.dumps(loc, indent=1, default=str))
            return {"render": rec, "placed": placed, "located": loc}
        except Exception as e:                               # noqa: BLE001
            (work_dir / "locate-failed.txt").write_text(f"{type(e).__name__}: {e}\n")
    anchor = (pl["x"] * sc.width, pl["y"] * sc.height)
    if pl.get("px_per_cm") and rec.get("px_per_cm"):
        placed = place_product(scene_png, rec, out_png, anchor=anchor, px_per_cm=pl["px_per_cm"])
    else:
        placed = place_product(scene_png, rec, out_png, anchor=anchor,
                               height_px=pl["height"] * sc.height)
    return {"render": rec, "placed": placed}
