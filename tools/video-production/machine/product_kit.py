"""THE PRODUCT TRUTH KIT — a product's own "casting sheet" (the owner, 2026-10-02:
"similar to how we have casting sheets for our avatars, you basically have to
build real models of products as well"). The standard: PRODUCT-KITS.md.

No spec sheets exist, so each product is built from its own real photos:
  measure   the outline and proportions from a clean packshot (its exact SAM
            cut-out); the real size from photos where a hand holds it
            (estimated, ± noted); the true colours; the label words
  model     a Blender model of the exact shape with the real label wrapped on,
            built by the builder for its KIND (blender/<builder>.py) — or, for
            soft or irregular goods no procedural model is honest for,
            "photo-only": measurements + the real cut-outs as references
  render    the model front, turned and back — checked against the packshot

The kit lives in the elements bank: runs/ai-elements/<brand>/products/<slug>/
  kit.json  measurements, sources, how each was taken, status
  model/    the .blend, label textures, reference renders, the real cut-out
Brand-agnostic: nothing here names a brand or a product.

    python3 product_kit.py build <brand> <slug>      # photos → measured kit → model → renders → check
    python3 product_kit.py list                      # every product on Drive vs its kit; missing = gate
    python3 product_kit.py publish <brand> <slug>    # the team copy → Drive <slug>/product-kit/
    python3 product_kit.py render <brand> <slug>     # re-render from kit.json (after a hand edit)
    python3 product_kit.py detect <image> "<what to find>"
"""
from __future__ import annotations

import importlib.util, itertools, json, math, os, re, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
BANK = Path(os.environ.get("PRODUCT_BANK") or WS / "runs" / "ai-elements")   # env: tests only
BLENDER = shutil.which("blender") or "/opt/homebrew/bin/blender"
sys.path.append(str(WS / "components" / "brandpath"))
import drive_index as DI                                # noqa: E402

# ── the kinds ────────────────────────────────────────────────────────────────
# A kind picks the builder. Round-section goods (bottle, pump bottle, jar, tub)
# are one honest shape — the measured outline turned on a lathe — so they share
# a builder. Soft or irregular goods get no invented model: photo-only.
KINDS = {
    "tube":        "tube.py",
    "bottle":      "bottle.py",
    "pump-bottle": "bottle.py",
    "jar":         "bottle.py",
    "box":         "box.py",
    "device":      None,        # brush, case, tool: no honest procedural model → photo-only
    "soft":        None,        # towel, pouch, bag, cloth → photo-only (and its shape is not fixed)
}
_KIND_WORDS = [  # first match wins — order matters (a "pump bottle" is not a plain "bottle")
    ("pump-bottle", ("pump", "airless", "dispenser")),
    ("tube",        ("tube", "squeeze")),
    ("jar",         ("jar", "tub", "pot", "tin", "supplement", "capsule", "pill")),
    ("bottle",      ("bottle", "vial", "dropper", "flask", "spray")),
    ("box",         ("box", "carton", "packet", "sachet")),
    ("soft",        ("towel", "cloth", "pouch", "bag", "fabric", "textile", "soft", "wash cloth", "washcloth", "glove", "case bag")),
    ("device",      ("brush", "device", "tool", "case", "roller", "razor", "trimmer", "gadget", "electronic", "charger")),
]
SKIP_FOLDERS = {"bundles", "_shared", "archive"}          # not single products
PHOTO_DIRS = ("packshot", "lifestyle", "ugc")             # real photographs, in this order
NOT_PHOTOS = {"ai", "cgi", "video", "cards", "texture", "product-kit", "versions"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_SOURCES = 10
RATIO_TOL = 0.03                                          # the model's outline vs the real one
# Real size is read off the hands and faces in real photos (macOS Vision, on this
# Mac). The bases are adult averages — an estimate, never a ruler:
PALM_CM = 10.0        # wrist joint to the middle finger's knuckle
KNUCKLE_CM = 6.5      # index knuckle to little-finger knuckle
FACE_BOX_CM = 16.0    # the face box Vision draws (brow to chin), not hairline to chin


def kind_of(words: str | None) -> str | None:
    """A free-text description of the product → one of KINDS (None = unknown)."""
    w = (words or "").lower().replace("_", " ")
    if w.strip() in KINDS:
        return w.strip()
    for kind, keys in _KIND_WORDS:
        if any(re.search(r"\b" + re.escape(k), w) for k in keys):
            return kind
    return None


def builder_of(kind: str | None) -> str | None:
    return KINDS.get(kind or "")


# ── where things are ─────────────────────────────────────────────────────────
def home(brand: str, slug: str) -> Path:
    return BANK / brand / "products" / slug


def drive_brands() -> Path | None:
    """`Shared Assets/brands` on the mounted Drive — discovered, never typed."""
    if os.environ.get("PRODUCT_DRIVE"):
        return Path(os.environ["PRODUCT_DRIVE"])
    m = DI.mount()
    if m and (m / "brands").is_dir():
        return m / "brands"
    return None


def drive_products(root: Path | None = None) -> list[tuple[str, str]]:
    """Every single product on Drive: (brand, slug). Bundles, shared and archive are not products."""
    root = root or drive_brands()
    out = []
    if not root or not root.is_dir():
        return out
    for b in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        pr = b / "products"
        if not pr.is_dir():
            continue
        for s in sorted(p for p in pr.iterdir() if p.is_dir()):
            if s.name in SKIP_FOLDERS or s.name.startswith((".", "_")):
                continue
            out.append((b.name, s.name))
    return out


def kit_status(brand: str, slug: str, bank: Path | None = None) -> dict | None:
    p = (bank or BANK) / brand / "products" / slug / "kit.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except ValueError:
        return {"status": "unreadable kit.json"}


USABLE = ("model", "photo-only")


def gate(brand: str, slug: str, bank: Path | None = None) -> str | None:
    """None when the product has a usable kit; otherwise one plain line saying why not."""
    k = kit_status(brand, slug, bank)
    if k is None:
        return (f"PRODUCT HAS NO TRUTH KIT: {brand}/{slug} — build it first: "
                f"python3 product_kit.py build {brand} {slug}")
    st = str(k.get("status") or "")
    if not st.startswith(USABLE):
        return f"PRODUCT KIT NOT READY: {brand}/{slug} — its kit says {st!r}"
    return None


def listing(root: Path | None = None, bank: Path | None = None) -> list[dict]:
    rows = []
    for brand, slug in drive_products(root):
        k = kit_status(brand, slug, bank)
        rows.append({"brand": brand, "slug": slug, "kit": k is not None,
                     "status": (k or {}).get("status", "MISSING — no kit"),
                     "kind": (k or {}).get("kind"),
                     "ratio": ((k or {}).get("outline") or {}).get("axis_ratio"),
                     "gate": gate(brand, slug, bank)})
    return rows


def _words(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def aliases(brand: str, slug: str) -> list[str]:
    """Other names the brand's own files use for this product (brands/<brand>/products/images.json):
    a key whose title holds every word of the slug, or the slug itself."""
    try:
        d = json.loads((WS / "brands" / brand / "products" / "images.json").read_text()).get("products", {})
    except (OSError, ValueError):
        return []
    sw = _words(slug.replace("-", " "))
    return sorted(k for k, v in d.items() if k != slug and isinstance(v, dict)
                  and (sw <= _words(str(v.get("title", ""))) ))


def slug_for(brand: str, name: str, bank: Path | None = None, root: Path | None = None) -> str | None:
    """A product key or folder name → its Drive slug (exact, else a kit's alias, else the one slug it starts)."""
    if not name:
        return None
    bank = bank or BANK
    slugs = {s for b, s in drive_products(root) if b == brand} | {p.name for p in (bank / brand / "products").glob("*") if p.is_dir()}
    if name in slugs:
        return name
    for s in sorted(slugs):
        k = kit_status(brand, s, bank) or {}
        if name in (k.get("aliases") or []):
            return s
    pre = [s for s in slugs if s.startswith(name + "-")]
    return pre[0] if len(pre) == 1 else None


def product_of_path(path, bank: Path | None = None, root: Path | None = None) -> tuple[str, str] | None:
    """A picture's path → (brand, slug) when it is a photo of ONE product
    (Drive, the bank, or the brand folder); None for anything else (bundles,
    shared shots, a frame this run made)."""
    parts = Path(str(path)).parts
    try:
        i = len(parts) - 1 - list(reversed(parts)).index("products")
    except ValueError:
        return None
    if i < 1 or i + 1 >= len(parts):
        return None
    brand = parts[i - 1]
    x = parts[i + 1]
    if x in SKIP_FOLDERS or x.startswith(("_", ".")):
        return None
    if i + 2 == len(parts) or x in ("images", "reference"):   # a flat folder: the file name carries the key
        stem = Path(parts[-1]).stem.lower()
        cands = [stem] + [stem.rsplit("-", n)[0] for n in range(1, stem.count("-") + 1)]
        for c in cands:
            s = slug_for(brand, c, bank, root)
            if s:
                return brand, s
        return None
    return brand, (slug_for(brand, x, bank, root) or x)


# ── the vision model (box, angle, facing, held, kind) ────────────────────────
def _review():
    for name in ("marketing-chain-checks/marketing_chain_checks", "quality-checks/quality_checks"):
        p = WS / "components" / name / "review.py"
        if p.exists():
            sp = importlib.util.spec_from_file_location("kit_review", p)
            m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
            return m
    raise SystemExit("no review module")


def detect(image, what: str, caller=None) -> dict:
    """{"box": [x0, y0, x1, y1] in 0–1, "angle": degrees the product leans
    (0 upright, + clockwise), "facing": "front|back|side|three-quarter",
    "held", "hand_box", "kind": what sort of object it is, "looks": a short name}."""
    rv = _review()
    q = (f"Find {what} in this picture. If there are several, describe only the largest one. "
         "Return ONE JSON object only (never a list): "
         '{"box_2d": [ymin, xmin, ymax, xmax] on a 0-1000 scale covering the whole object including its cap, '
         '"angle": degrees it leans from upright (positive = clockwise), '
         '"facing": "front" | "back" | "side" | "three-quarter", '
         '"held": true|false, "hand_box_2d": [ymin, xmin, ymax, xmax] of the hand holding it (wrist to fingertips) or null, '
         '"kind": "tube" | "pump bottle" | "bottle" | "jar" | "box" | "device" | "towel or soft goods" | "other", '
         '"looks": "a short plain name for it, e.g. the black pump bottle", '
         '"cap_end": "top" | "bottom" | "none" (where its cap or pump is in this picture)}')
    try:
        a = rv.ask([{"text": q}, rv._part(image)], caller=caller)
    except ValueError:                       # it answered with several objects anyway — ask once more
        a = rv.ask([{"text": q + " ONE object."}, rv._part(image)], caller=caller)
    y0, x0, y1, x1 = [v / 1000 for v in a.get("box_2d") or [0, 0, 1000, 1000]]
    hb = a.get("hand_box_2d")
    return {"box": [x0, y0, x1, y1], "angle": float(a.get("angle") or 0), "facing": a.get("facing"),
            "held": bool(a.get("held")), "hand_box": ([hb[1] / 1000, hb[0] / 1000, hb[3] / 1000, hb[2] / 1000] if hb else None),
            "kind": a.get("kind"), "looks": a.get("looks"), "cap_end": a.get("cap_end")}


def segment(image, what: str, caller=None):
    """The product's own pixels, cut out by the vision model: returns (box 0–1,
    a white-on-black mask image the size of the box) — fingers holding it are
    NOT part of it."""
    import base64, io
    from PIL import Image
    rv = _review()
    q = (f"Give the segmentation mask of {what} in this picture — the object only: not the hand or "
         "fingers holding it, not its shadow. Return JSON only: "
         '[{"box_2d": [ymin, xmin, ymax, xmax] on a 0-1000 scale, "mask": "data:image/png;base64,...", "label": "..."}]')
    a = rv.ask([{"text": q}, rv._part(image)], caller=caller)
    items = a if isinstance(a, list) else (a.get("items") or [a])
    it = items[0]
    y0, x0, y1, x1 = [v / 1000 for v in it["box_2d"]]
    m = it["mask"].split(",", 1)[-1]
    mask = Image.open(io.BytesIO(base64.b64decode(m))).convert("L")
    return [x0, y0, x1, y1], mask


def _pc():
    sp = importlib.util.spec_from_file_location("product_check", HERE / "product_check.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


# ── 1. the real photos ───────────────────────────────────────────────────────
def pick_sources(folder: Path, cap: int = MAX_SOURCES) -> list[Path]:
    """Real photographs of the product, packshots first. Top-level shots in
    packshot/ lifestyle/ ugc/ come first; dated sub-shoots only fill in when
    there are fewer than 3 (an older shoot may show an older pack). Never AI,
    CGI, video, designed cards or texture close-ups."""
    def photos(d: Path, deep: bool):
        if not d.is_dir():
            return []
        it = d.rglob("*") if deep else d.glob("*")
        return sorted(p for p in it if p.is_file() and p.suffix.lower() in PHOTO_EXT
                      and not (set(p.relative_to(folder).parts[:-1]) & NOT_PHOTOS))
    def rank(p: Path):
        n = p.name.lower()
        try:
            plain = _plain_background(p) if p.suffix.lower() != ".heic" else 0
        except Exception:
            plain = 0
        return (-(2 * plain + 2 * ("white" in n) + 1.5 * ("front" in n) + ("packshot" in n) + ("hero" in n) * 0.5
                  + 1.5 * ("hand" in n))                                  # a hand in shot is the size evidence
                + 2 * ("back" in n) + 2 * bool(re.search(r"\b(box|carton|packaging)\b", n.replace("-", " ").replace("_", " "))), n)
    top = []
    for d in PHOTO_DIRS:
        top += sorted(photos(folder / d, False), key=rank)
    top = [p for p in top if p.suffix.lower() != ".heic" or not p.with_suffix(".jpeg").exists()]
    if len(top) < 3:
        seen = set(top)
        for d in PHOTO_DIRS:
            top += [p for p in sorted(photos(folder / d, True), key=rank) if p not in seen]
    # a packshot-only product still gets its lifestyle shots in (they show size in a hand)
    pack = [p for p in top if "packshot" in p.relative_to(folder).parts]
    back = [p for p in pack if "back" in p.name.lower() and p not in pack[:5]
            and not re.search(r"\b(box|carton|packaging)\b", p.name.lower().replace("-", " ").replace("_", " "))][:1]
    by_dir = [[p for p in top if p not in pack and p.relative_to(folder).parts[0] == d] for d in PHOTO_DIRS]
    rest = [p for grp in itertools.zip_longest(*by_dir) for p in grp if p]   # lifestyle and ugc take turns
    keep = pack[:max(5, cap - len(rest) - len(back))] + back + rest
    return keep[:cap]


def safe_name(p: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", p.name).strip("-") + ".jpg"


def copy_sources(files: list[Path], dest: Path) -> list[Path]:
    """Copies (Drive is read-only here) as JPEG, named <original name>.jpg."""
    from PIL import Image
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for f in files:
        t = dest / safe_name(f)
        if not t.exists():
            if f.suffix.lower() == ".heic":
                subprocess.run(["sips", "-s", "format", "jpeg", str(f), "--out", str(t)], capture_output=True)
            else:
                im = Image.open(f)
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel("A")); im = bg
                im.convert("RGB").save(t, "JPEG", quality=95)
        if t.exists():
            out.append(t)
    return out


# ── 2. measuring a cut-out ───────────────────────────────────────────────────
def largest_part(mask):
    """Keeps the biggest connected piece of a mask (SAM sometimes adds a speck)."""
    from PIL import Image
    W, H = mask.size; s = max(1, int(max(W, H) / 500))
    sm = mask.resize((W // s, H // s)); w, h = sm.size; px = sm.load()
    seen = bytearray(w * h); best = []
    for y in range(h):
        for x in range(w):
            if px[x, y] > 127 and not seen[y * w + x]:
                comp = []; st = [(x, y)]; seen[y * w + x] = 1
                while st:
                    cx, cy = st.pop(); comp.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and px[nx, ny] > 127:
                            seen[ny * w + nx] = 1; st.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    keep = Image.new("L", (w, h), 0); kp = keep.load()
    for x, y in best:
        kp[x, y] = 255
    # fill its holes: anything the outside cannot reach is part of it (a label
    # patch or a print the cut-out skipped is still the product)
    out = bytearray(w * h); st = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    st = [(x, y) for x, y in st if kp[x, y] == 0]
    for x, y in st:
        out[y * w + x] = 1
    while st:
        cx, cy = st.pop()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h and not out[ny * w + nx] and kp[nx, ny] == 0:
                out[ny * w + nx] = 1; st.append((nx, ny))
    filled = Image.new("L", (w, h), 0); fp = filled.load()
    for y in range(h):
        for x in range(w):
            if not out[y * w + x] and kp[x, y] == 0:
                fp[x, y] = 255
    keep = keep.resize((W, H), Image.NEAREST)
    from PIL import ImageChops
    holes = filled.resize((W, H), Image.NEAREST)
    return ImageChops.lighter(ImageChops.multiply(mask.convert("L"), keep), holes)


def lean_of(mask) -> float:
    """Degrees the mask's long axis leans from vertical (+ = top leans right)."""
    W, H = mask.size; step = max(1, int(max(W, H) / 300)); px = mask.load()
    pts = [(x, y) for y in range(0, H, step) for x in range(0, W, step) if px[x, y] > 127]
    if len(pts) < 50:
        return 0.0
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    ang = math.degrees(0.5 * math.atan2(2 * sxy, sxx - syy))   # long axis from +x, y down
    lean = ang - 90 if ang > 0 else ang + 90                      # from vertical
    return -lean


def upright(image, mask, lean: float):
    """Turns photo and mask so the product stands straight (only small leans)."""
    from PIL import Image
    if abs(lean) < 1.0 or abs(lean) > 30:
        return image, mask
    return (image.rotate(-lean, resample=Image.BICUBIC, fillcolor=(255, 255, 255)),
            mask.rotate(-lean, resample=Image.NEAREST))


def cut_off(mask, edge: int = 3) -> bool:
    """True when the cut-out touches the photo's edge — the product is cropped."""
    bb = bbox(mask)
    if not bb:
        return True
    W, H = mask.size
    return bb[0] <= edge or bb[1] <= edge or bb[2] >= W - edge or bb[3] >= H - edge


def bbox(mask):
    return mask.point(lambda v: 255 if v > 127 else 0).getbbox()


def widths(mask, bb) -> list[tuple[float, float, int, int]]:
    """Per row of the cut-out: (t 0–1 down the product, width px, left, right)."""
    x0, y0, x1, y1 = bb; px = mask.load(); rows = []
    for y in range(y0, y1):
        xs = [x for x in range(x0, x1) if px[x, y] > 127]
        if xs:
            rows.append(((y - y0) / max(1, y1 - y0 - 1), xs[-1] - xs[0] + 1, xs[0], xs[-1]))
    return rows


def profile_of(rows, step: float = 0.02) -> tuple[list, float]:
    """The width profile, [t, width / max width] every `step` of the height, and the max width px."""
    if not rows:
        return [], 0
    mw = max(r[1] for r in rows)
    out = []
    t = 0.0
    while t <= 1.0 + 1e-9:
        near = [r[1] for r in rows if abs(r[0] - t) <= step / 2] or [min(rows, key=lambda r: abs(r[0] - t))[1]]
        out.append([round(t, 3), round(statistics.median(near) / mw, 3)])
        t += step
    return out, mw


def row_colours(image, mask, bb):
    """Per row: the median colour of the product across its middle half (print and glare left out)."""
    x0, y0, x1, y1 = bb; im = image.convert("RGB"); px = im.load(); mp = mask.load(); out = []
    for y in range(y0, y1):
        xs = [x for x in range(x0, x1) if mp[x, y] > 127]
        if not xs:
            out.append(None); continue
        a, b = xs[0], xs[-1]; q = (b - a) // 4
        cs = [px[x, y] for x in range(a + q, b - q + 1, max(1, (b - a) // 60))]
        cs = sorted(cs, key=lambda c: sum(c))
        cs = cs[len(cs) // 5: max(len(cs) // 5 + 1, len(cs) * 9 // 10)]
        out.append(tuple(int(statistics.median(c[i] for c in cs)) for i in range(3)))
    return out


def full_width_lines(image, mask, bb, lo=0.5, hi=0.95, gap=3, thresh=10, cover=0.9) -> list[float]:
    """Rows where a line runs right ACROSS the product (a cap meeting a body, a
    collar): most of the row's width changes brightness there. Printed words
    change only part of a row, so they are not mistaken for a part line.
    Returns t (0–1 down the product), top first, one per line."""
    x0, y0, x1, y1 = bb; L = image.convert("L"); px = L.load(); mp = mask.load(); h = max(1, y1 - y0 - 1)
    hits = []
    for y in range(y0 + gap, y1 - gap):
        t = (y - y0) / h
        if not (lo <= t <= hi):
            continue
        xs = [x for x in range(x0, x1) if mp[x, y] > 127]
        if len(xs) < 10:
            continue
        a, b = xs[0], xs[-1]; m = max(2, (b - a) // 25)
        xs = [x for x in xs if a + m <= x <= b - m and mp[x, y - gap] > 127 and mp[x, y + gap] > 127]
        if not xs:
            continue
        on = sum(1 for x in xs if max(abs(px[x, y + k] - px[x, y - k]) for k in (1, 2, gap)) > thresh)
        if on / len(xs) >= cover:
            hits.append(t)
    out = []
    for t in hits:
        if not out or t - out[-1][-1] > 0.015:
            out.append([t])
        else:
            out[-1].append(t)
    return [round(statistics.median(g), 3) for g in out]


def rgb01(c) -> list:
    return [round(v / 255, 4) for v in c]


def hexof(c01) -> str:
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in c01[:3])


def median_colour(cols, t0, t1, rows):
    sel = [c for c, r in zip(cols, rows) if c is not None and t0 <= r[0] <= t1]
    if not sel:
        sel = [c for c in cols if c is not None]
    return tuple(int(statistics.median(c[i] for c in sel)) for i in range(3))


def read_lines(picture, min_conf: float = 0.5) -> list[tuple[float, str]]:
    """(text height 0–1, line) for every line of text Vision reads with some
    confidence (a script it cannot read comes back as low-confidence junk)."""
    exe = HERE / "vision" / ".build" / "readtext"; src = HERE / "vision" / "readtext.swift"
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], check=True, capture_output=True)
    out = subprocess.run([str(exe), str(picture), "--boxes"], capture_output=True, text=True).stdout
    lines = []
    for l in out.splitlines():
        f = l.split("\t", 2)
        if len(f) == 3:
            try:
                if float(f[1]) >= min_conf:
                    lines.append((float(f[0]), f[2].strip(), float(f[1])))
            except ValueError:
                pass
    return lines


_DICT = None


def _real_word(w: str, names: set) -> bool:
    """A word a reader can trust: in the system dictionary, or one of the brand's
    or product's own names. A misread ("serun" for "serum") is neither."""
    global _DICT
    if _DICT is None:
        try:
            _DICT = {l.strip().lower() for l in open("/usr/share/dict/words")}
        except OSError:
            _DICT = set()
    w = w.lower()
    return not _DICT or w in _DICT or w in names or (w.endswith("s") and w[:-1] in _DICT)


def key_words(lines, n=3, names: set | None = None) -> list[str]:
    """The label's biggest words: the n tallest lines with real words (no sizes or
    numbers; a line read with full confidence, or every word of it a real word)."""
    names = {x.lower() for x in (names or set())}
    good = []
    for ln in lines:
        h, t = ln[0], ln[1]; conf = ln[2] if len(ln) > 2 else 1.0
        t = re.sub(r"[™®©]", "", t).strip()
        if len(re.findall(r"[A-Za-z]", t)) < 3 or re.search(r"\d", t):
            continue
        toks = re.findall(r"[A-Za-z]+", t)
        if conf < 0.99 and not all(_real_word(w, names) for w in toks):
            continue
        good.append((h, t))
    good.sort(key=lambda x: -x[0]); out = []
    for h, t in good:
        if t.upper() not in (o.upper() for o in out):
            out.append(t)
        if len(out) == n:
            break
    return out


def _vision(tool, picture) -> str:
    exe = HERE / "vision" / ".build" / tool; src = HERE / "vision" / f"{tool}.swift"
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], check=True, capture_output=True)
    return subprocess.run([str(exe), str(picture)], capture_output=True, text=True).stdout


def long_px(mask) -> float | None:
    """The product's length in pixels along its own long axis."""
    W, H = mask.size; step = max(1, int(max(W, H) / 500)); px = mask.load()
    pts = [(x, y) for y in range(0, H, step) for x in range(0, W, step) if px[x, y] > 127]
    if len(pts) < 50:
        return None
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts); sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    a = 0.5 * math.atan2(2 * sxy, sxx - syy); ux, uy = math.cos(a), math.sin(a)
    pr = sorted((p[0] - mx) * ux + (p[1] - my) * uy for p in pts)
    return pr[int(0.995 * (len(pr) - 1))] - pr[int(0.005 * (len(pr) - 1))]


def size_read(picture, box, L) -> tuple[float | None, str]:
    """One photo's read of the product's real length (cm): against the hand
    touching it (palm length and knuckle span — the smaller read, since a hand
    turned away from the camera only ever looks smaller), else against a face."""
    from PIL import Image
    W, H = Image.open(picture).size
    x0, y0, x1, y1 = box[0] * W, box[1] * H, box[2] * W, box[3] * H
    gx, gy = (x1 - x0) * 0.5, (y1 - y0) * 0.5
    hands = {}
    for l in _vision("hands", picture).splitlines():
        f = l.split()
        if len(f) == 6 and f[0] == "hand":
            hands.setdefault(f[1], {})[f[2]] = (float(f[3]) * W, float(f[4]) * H)
    reads = []
    for h in hands.values():
        if not any(x0 - gx <= x <= x1 + gx and y0 - gy <= y <= y1 + gy for x, y in h.values()):
            continue                                       # not the hand holding it
        r = []
        if "wrist" in h and "middleMCP" in h:
            r.append(L * PALM_CM / max(1, math.dist(h["wrist"], h["middleMCP"])))
        if "indexMCP" in h and "littleMCP" in h and math.dist(h["indexMCP"], h["littleMCP"]) > 0.25 * math.dist(h.get("wrist", h["indexMCP"]), h["indexMCP"]):
            r.append(L * KNUCKLE_CM / max(1, math.dist(h["indexMCP"], h["littleMCP"])))
        if r:
            reads.append(min(r))
    if reads:
        return round(min(reads), 1), "hand"
    faces = [l.split() for l in _vision("faces", picture).splitlines() if l.startswith("face")]
    if faces:
        fh = max(float(f[4]) for f in faces) * H
        return round(L * FACE_BOX_CM / fh, 1), "face"
    return None, ""


def size_from_reads(reads: list[tuple[float, str, str]], hw: float) -> dict | None:
    """[(cm, photo, against)] → height, width, ±. Every way these reads go
    wrong makes the product look BIGGER (it is held nearer the camera than the
    hand; a hand turned away looks smaller), so the lower quarter of the reads
    is taken, after dropping any under 0.6× the median (the wrong hand). Fewer
    than 3 reads is not a measure — the size is left unmeasured."""
    if len(reads) < 3:
        return None
    vals = sorted(r[0] for r in reads); m = statistics.median(vals)
    kept = [v for v in vals if v >= 0.6 * m]
    if len(kept) < 3:
        return None
    L = kept[(len(kept) - 1) // 4]
    pm = round(max(L * 0.25, statistics.median(kept) - L), 1)
    h, w = (L, L / hw) if hw >= 1 else (L * hw, L)
    return {"height": round(h, 1), "width": round(w, 1), "plus_minus": pm,
            "photos": [f"{p}: {v} cm against the {a}" for v, p, a in reads]}


# ── 3. the label textures ────────────────────────────────────────────────────
def label_from(image, mask, bb, fill, min_h=1600):
    """The product's own front as a texture: its bounding box from the photo,
    everything outside its cut-out filled with its own colour."""
    from PIL import Image
    crop = image.convert("RGB").crop(bb); m = mask.crop(bb).point(lambda v: 255 if v > 127 else 0)
    bg = Image.new("RGB", crop.size, tuple(fill)); bg.paste(crop, mask=m)
    if bg.height < min_h:
        k = min_h / bg.height; bg = bg.resize((int(bg.width * k), min_h), Image.LANCZOS)
    return bg


def bands_texture(cols, size):
    """A texture with no words: each height's own colour from the packshot (for a side we have no photo of)."""
    from PIL import Image
    c = [x for x in cols if x is not None] or [(128, 128, 128)]
    im = Image.new("RGB", (8, len(c)))
    for y, col in enumerate(c):
        for x in range(8):
            im.putpixel((x, y), col)
    return im.resize(size, Image.BILINEAR)


def cutout_png(image, mask, bb, pad=0.04):
    from PIL import Image
    rgba = image.convert("RGBA"); rgba.putalpha(mask.point(lambda v: 255 if v > 127 else 0))
    x0, y0, x1, y1 = bb; p = int(max(x1 - x0, y1 - y0) * pad)
    return rgba.crop((max(0, x0 - p), max(0, y0 - p), min(image.width, x1 + p), min(image.height, y1 + p)))


def on_white(rgba, size=(1000, 1250), fill=0.78):
    from PIL import Image
    W, H = size; k = min(W * fill / rgba.width, H * fill / rgba.height)
    r = rgba.resize((max(1, int(rgba.width * k)), max(1, int(rgba.height * k))), Image.LANCZOS)
    bg = Image.new("RGB", size, (255, 255, 255)); bg.paste(r, ((W - r.width) // 2, (H - r.height) // 2), r)
    return bg


# ── 4. render and check ──────────────────────────────────────────────────────
VIEWS = {"front": 0, "34": 35, "back": 180}


def _versions(p: Path, keep_dir: Path):
    if p.exists():
        keep_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(p.stat().st_mtime))
        shutil.copy2(p, keep_dir / f"{p.stem}-{stamp}{p.suffix}")


def render(kit_path: Path, log=print) -> dict:
    """reference-front / -34 / -back, on white and transparent, from the kit's builder; saves the .blend."""
    kit_path = Path(kit_path); kit = json.loads(kit_path.read_text()); d = kit_path.parent; md = d / "model"
    b = builder_of(kit.get("kind"))
    if kit.get("model_parts"):            # a refined kit (PRODUCT-KITS.md, the refinement pass): built part by part
        b = "parts.py"
    if not b:
        return {}
    md.mkdir(parents=True, exist_ok=True)
    out = {}
    blend = md / f"{Path(b).stem if kit.get('kind') != 'tube' else 'tube'}.blend"
    from PIL import Image
    for view, yaw in VIEWS.items():
        tr = md / f"reference-{view}-transparent.png"; wh = md / f"reference-{view}.png"
        for f in (tr, wh):
            _versions(f, md / "versions")
        args = [BLENDER, "-b", "-P", str(HERE / "blender" / b), "--", str(kit_path), str(tr), str(yaw), "0", "1000", "1250", "1"]
        if view == "front":
            _versions(blend, md / "versions"); args.append(str(blend))
        r = subprocess.run(args, capture_output=True, text=True, cwd=str(d))
        (md / "blender.log").write_text(r.stdout[-6000:] + r.stderr[-4000:])
        if not tr.exists():
            raise RuntimeError(f"blender did not render {tr.name}: see {md / 'blender.log'}")
        rgba = Image.open(tr).convert("RGBA")                 # the same render on pure white
        bg = Image.new("RGB", rgba.size, (255, 255, 255)); bg.paste(rgba, mask=rgba.getchannel("A")); bg.save(wh)
        out[tr.name] = tr; out[wh.name] = wh
    for junk in md.glob("*.blend1"):
        junk.unlink()
    log(f"  rendered {len(out)} references → {md}")
    return out


def check_render(kit_path: Path) -> dict:
    """The model's front render against the real packshot: its outline's length
    over width (SAM cut-out of the render, same measure as every picture) within
    ±3% of the kit's, and the label's key words read off it."""
    from PIL import Image
    kit_path = Path(kit_path); kit = json.loads(kit_path.read_text()); md = kit_path.parent / "model"
    pc = _pc()
    tr = md / "reference-front-transparent.png"; wh = md / "reference-front.png"
    if not (tr.exists() and wh.exists()):
        return {"ok": False, "why": ["no render"]}
    a = Image.open(tr).getchannel("A"); bb = a.point(lambda v: 255 if v > 20 else 0).getbbox()
    W, H = a.size
    box = [bb[0] / W, bb[1] / H, bb[2] / W, bb[3] / H]
    mask = pc.product_mask(wh, box)
    r = pc.axis_ratio(mask); want = kit["outline"]["axis_ratio"]
    words = " ".join(pc.words_on(wh, box)).upper()           # the same reader every picture's check uses
    missing = [w for w in kit.get("label_words") or [] if w.upper() not in words]
    why = []
    if r is None or abs(r - want) / want > RATIO_TOL:
        why.append(f"outline {r and round(r, 3)} vs real {want} (more than ±{int(RATIO_TOL * 100)}%)")
    if missing:
        why.append("label words not read on the render: " + ", ".join(missing))
    return {"ok": not why, "render_ratio": r and round(r, 3), "real_ratio": want,
            "off_pct": r and round((r - want) / want * 100, 2), "label_missing": missing, "why": why}


# ── 5. the one command ───────────────────────────────────────────────────────
KEEP_WHEN_HAND_SET = ("size_cm", "cap", "labels", "label_lock", "what", "kind", "tube_rgb", "cap_rgb", "outline", "body", "label_words")


def build(brand: str, slug: str, root: Path | None = None, cap: int = MAX_SOURCES, log=print) -> dict:
    """Real photos → measured kit.json → model → renders → check. Anything a
    person set by hand and listed in the kit's "hand_set" is kept; the machine's
    own fresh measures of those land in "remeasured" beside them."""
    from PIL import Image
    root = root or drive_brands()
    folder = (root / brand / "products" / slug) if root else None
    d = home(brand, slug); d.mkdir(parents=True, exist_ok=True); kp = d / "kit.json"
    old = json.loads(kp.read_text()) if kp.exists() else {}
    hand = set(old.get("hand_set") or [])
    kit = {"product": f"{brand}/{slug}", "built": time.strftime("%Y-%m-%d"), "standard": "tools/video-production/PRODUCT-KITS.md"}
    al = aliases(brand, slug)
    if al:
        kit["aliases"] = al

    # 1. photos
    files = pick_sources(folder, cap) if folder and folder.is_dir() else []
    srcs = copy_sources(files, d / "sources") if files else []
    if not srcs:
        kit.update({"status": "no real photos", "why": f"nothing usable in Drive {brand}/products/{slug}/ (packshot, lifestyle, ugc)"})
        kp.write_text(json.dumps({**old, **kit}, indent=1, ensure_ascii=False)); log(f"  {brand}/{slug}: no real photos"); return kit
    log(f"  {len(srcs)} real photos → {d / 'sources'}")

    # 2. look at each: where it is, which way it faces, held or not, what kind
    what = old.get("what") or f"the {slug.replace('-', ' ')} product itself (not its box, not any other product)"
    found = []
    for s in srcs:
        try:
            det = detect(s, what)
        except Exception as e:                       # the reader could not box it
            det = {"error": str(e)[:120]}
        found.append({"file": s, "name": s.name, "det": det, "size": Image.open(s).size})
    kinds = [kind_of(f["det"].get("kind")) for f in found if f["det"].get("kind")]
    kinds = [k for k in kinds if k]
    kind = old.get("kind") if "kind" in hand else (statistics.mode(kinds) if kinds else None)
    looks = [f["det"].get("looks") for f in found if f["det"].get("looks")]

    # 3. the clean packshot: front-facing, not held, standing straight, plain background
    def score(f):
        dt = f["det"]; n = f["name"].lower()
        if dt.get("error") or not dt.get("box"):
            return -99
        s = 0.0
        s += 3 if dt.get("facing") == "front" else (-2 if dt.get("facing") == "back" else 0)
        s -= 3 if dt.get("held") else 0
        s -= min(3, abs(dt.get("angle") or 0) / 5)
        s += 2 * ("white" in n) + 1.5 * ("front" in n) + 1 * ("packshot" in n) - 2 * ("back" in n)
        if kind == "tube" and dt.get("cap_end") == "top":
            s -= 4                                      # the builder stands a tube on its cap
        s += 2 * _plain_background(f["file"])
        return s
    found.sort(key=score, reverse=True)
    pc = _pc()
    pack = None
    for cand in [f for f in found if score(f) > -99][:4]:
        bx = cand["det"]["box"]; pad = 0.01
        box = [max(0, bx[0] - pad), max(0, bx[1] - pad), min(1, bx[2] + pad), min(1, bx[3] + pad)]
        m = largest_part(pc.product_mask(cand["file"], box))
        if not cut_off(m):                            # a packshot that crops the product measures only part of it
            pack, mask = cand, m
            break
        log(f"  {cand['name']}: the product runs off the edge of the photo — not measured from it")
    if pack is None:
        kit.update({"status": "no real photos", "why": "no photo shows the whole product uncropped and boxable"})
        kp.write_text(json.dumps({**old, **kit}, indent=1, ensure_ascii=False)); log(f"  {brand}/{slug}: no whole-product photo"); return kit
    det = pack["det"]
    if "kind" not in hand and kind_of(det.get("kind")):
        kind = kind_of(det.get("kind"))                     # the clean packshot's own read wins
    img = Image.open(pack["file"]).convert("RGB"); W, H = img.size
    ratio = pc.axis_ratio(mask)
    lean = lean_of(mask) if ratio and ratio > 1.25 else 0.0
    img_u, mask_u = upright(img, mask, lean)
    if kind == "tube" and det.get("cap_end") == "top":      # a tube's label sits the way it does on the tube: stand it on its cap
        img_u, mask_u = img_u.rotate(180), mask_u.rotate(180)
        log("  packshot shows the cap at the top — turned over so the tube stands on its cap")
    bb = bbox(mask_u)
    rows = widths(mask_u, bb)
    prof, mw = profile_of(rows)
    hw = round((bb[3] - bb[1]) / max(1, mw), 3)
    cols = row_colours(img_u, mask_u, bb)
    log(f"  packshot: {pack['name']} (facing {det.get('facing')}, lean {lean:.1f}°) — {ratio:.3f}× long over wide")

    outline = {"from": f"sources/{pack['name']} (front, measured)", "height_over_width": hw,
               "axis_ratio": round(ratio, 3),
               "axis_ratio_how": "length over width along the product's own long axis, from its exact cut-out (SAM 2.1) of the packshot",
               "profile": prof}
    # cross-check the ratio on the other front/back photos that stand fairly straight
    cross = []
    for f in found[1:]:
        dt = f["det"]
        if dt.get("box") and dt.get("facing") in ("front", "back") and abs(dt.get("angle") or 0) < 40:
            try:
                b2 = dt["box"]; r2 = pc.axis_ratio(largest_part(pc.product_mask(f["file"], b2)))
                if r2:
                    cross.append((f["name"], round(r2, 2)))
            except Exception:
                pass
        if len(cross) >= 3:
            break
    if cross:
        outline["cross_check"] = [f"{n}: {r}" for n, r in cross]

    # parts: where the cap / pump / collar meet the body
    body_rgb = median_colour(cols, 0.15, 0.6, rows)
    extra = {}
    if kind == "tube":
        lines_across = full_width_lines(img_u, mask_u, bb, lo=0.6, hi=0.93)
        cap_from = lines_across[0] if lines_across else 0.8      # the first line right across, from the top = the cap's top
        cap_rows = [r[1] for r in rows if cap_from + 0.03 <= r[0] <= 0.97]
        outline["cap_from"] = cap_from
        outline["cap_width"] = round(statistics.median(cap_rows) / mw, 3) if cap_rows else prof[-1][1]
        outline["profile"] = [p for p in prof if p[0] < cap_from]
        outline["cap_how"] = ("the cap's top is the first line that runs right across the cut-out in its lower half (where the cap meets the body); "
                              "its width the median below that" + ("" if lines_across else " — NO such line found, 0.8 assumed: check by eye"))
        outline["lines_across"] = lines_across
        body_rgb = median_colour(cols, 0.1, cap_from - 0.05, rows)
        extra["cap_rgb"] = rgb01(median_colour(cols, cap_from + 0.03, 0.97, rows))
        extra["tube_rgb"] = rgb01(body_rgb)
        extra["body"] = {"meet_width": 1.02, "meet_depth": 1.05, "meet_band": 0.06, "depth_curve": 0.6,
                         "how": "front outline measured; the body narrows onto the cap over its last 6% (bottom width = cap width × 1.02, "
                                "bottom depth = cap depth × 1.05) — on the real tube the body meets the cap nearly flush. "
                                "Depth grows from the flat crimp (0) to that, never past the cap."}
        extra["cap"] = {"kind": "plain", "depth_ratio": 1.0,
                        "how": "plain cap, round in section (no side photo read for an oval or a notch yet — set by hand in kit.json if the photos show one)"}
    else:
        parts = full_width_lines(img_u, mask_u, bb, lo=0.03, hi=0.97)
        bands = []
        edges = [0.0] + parts + [1.0]
        for a, b in zip(edges, edges[1:]):
            if b - a >= 0.03:
                bands.append({"from": round(a, 3), "to": round(b, 3), "rgb": rgb01(median_colour(cols, a + 0.01, b - 0.01, rows))})
        extra["parts"] = bands
        extra["parts_how"] = "bands between the lines that run right across the cut-out (cap, collar, body, base), each its own median colour"
        extra["body_rgb"] = rgb01(body_rgb)

    # size — from photos where a hand holds it
    reads = []
    for f in found:
        dt = f["det"]
        if not dt.get("box") or f is pack:
            continue
        try:
            fm = largest_part(pc.product_mask(f["file"], dt["box"])); L = long_px(fm)
            v, against = size_read(f["file"], dt["box"], L) if L else (None, "")
        except Exception:
            v = None
        if v:
            reads.append((v, f["name"], against))
    # Size: the reads are kept as evidence, never written as the real size. Tested
    # 2 Oct on every product: against hands they run 1.5–2× too big (the product
    # is held nearer the camera than the hand; a 50 mL pump bottle read 22 cm),
    # so a size goes in kit.json only when a person measures it with a ruler
    # (or sets it by hand, listed in "hand_set").
    size = size_from_reads(reads, hw)
    size_cm = {"height": None, "width": None, "plus_minus": None,
               "how": "not measured — needs one ruler measurement (height and width in cm) written here by hand and "
                      "\"size_cm\" added to \"hand_set\". The model is built to a nominal 10 units tall; its shape is exact."}
    size_reads = {"reads": [f"{p}: {v} cm against the {a}" for v, p, a in reads],
                  "lower_quarter": size and {"height": size["height"], "width": size["width"]},
                  "how": (f"the product's length in real photos against the hand holding it (adult palm ≈ {PALM_CM} cm wrist to "
                          f"middle knuckle, knuckles ≈ {KNUCKLE_CM} cm across) or a face (Vision's face box ≈ {FACE_BOX_CM} cm) — "
                          "EVIDENCE ONLY: these reads run 1.5–2× too big, so they are not the size")}

    # label: front texture from the packshot, back from a real back photo when there is one
    md = d / "model"; md.mkdir(exist_ok=True)
    labels = {}
    tag = "-auto" if "labels" in hand else ""          # hand-made label textures are never overwritten
    front = label_from(img_u, mask_u, bb, body_rgb)
    front.save(md / f"front{tag}.png"); labels["front"] = f"model/front{tag}.png"
    labels["front_how"] = f"lifted from the packshot ({pack['name']}), outside the cut-out filled with the product's own colour"
    back = next((f for f in found if f["det"].get("facing") == "back" and f["det"].get("box")), None)
    if back:
        bi = Image.open(back["file"]).convert("RGB"); bm = largest_part(pc.product_mask(back["file"], back["det"]["box"]))
        bl = lean_of(bm) if (pc.axis_ratio(bm) or 1) > 1.25 else 0
        bi, bm = upright(bi, bm, bl)
        if kind == "tube" and back["det"].get("cap_end") == "top":
            bi, bm = bi.rotate(180), bm.rotate(180)
        bt = label_from(bi, bm, bbox(bm), body_rgb).resize(front.size)
        bt.save(md / f"back{tag}.png"); labels["back"] = f"model/back{tag}.png"
        labels["back_how"] = f"lifted from the real back photo ({back['name']})"
    else:
        bands_texture(cols, front.size).save(md / f"back{tag}.png"); labels["back"] = f"model/back{tag}.png"
        labels["back_how"] = "no back photo: each height's own colour from the packshot, no words (nothing invented)"
    cutout_png(img_u, mask_u, bb).save(md / "packshot-cutout.png")

    lines = read_lines(md / f"front{tag}.png")
    names = _words(f"{brand} {slug} " + " ".join(al))
    try:
        d_ = json.loads((WS / "brands" / brand / "products" / "images.json").read_text()).get("products", {})
        names |= _words(" ".join(str(v.get("title", "")) for k_, v in d_.items() if isinstance(v, dict) and (k_ == slug or k_ in al)))
    except (OSError, ValueError):
        pass
    lw = key_words(lines, names=names)

    kit.update({"kind": kind, "kind_how": f"read off the photos ({', '.join(sorted(set(k for k in kinds if k)))})",
                "what": (looks[0] if looks else what), "outline": outline, "size_cm": size_cm, "size_reads": size_reads, "labels": labels,
                "label_words": lw, "label_read": [ln[1] for ln in lines], **extra,
                "sources": [f"sources/{f['name']}" for f in [pack] + [f for f in found if f is not pack]],
                "photos": {f["name"]: {k: f["det"].get(k) for k in ("facing", "held", "angle", "cap_end", "error") if f["det"].get(k) is not None} for f in found}})
    if hand:
        kit["remeasured"] = {k: kit.get(k) for k in hand if k in kit}
        for k in hand:
            if k in old:
                kit[k] = old[k]
        kit["hand_set"] = sorted(hand)
    for k in ("label_lock", "model_note"):
        if k in old and k not in kit:
            kit[k] = old[k]

    # 4. model + renders + check (or photo-only)
    b = builder_of(kit["kind"])
    if b:
        if not kit["size_cm"].get("height"):
            kit["size_cm"]["scale"] = "nominal"
        kit["status"] = "building"
        kp.write_text(json.dumps(kit, indent=1, ensure_ascii=False))
        render(kp, log=log)
        v = check_render(kp)
        kit["check"] = v
        kit["status"] = "model" if v["ok"] else f"model — check failed: {'; '.join(v['why'])}"
        log(f"  model check: render {v.get('render_ratio')} vs real {v.get('real_ratio')} ({v.get('off_pct')}%), "
            f"label missing {v.get('label_missing')} → {'PASS' if v['ok'] else 'FAIL'}")
    else:
        _photo_refs(found, pack, img_u, mask_u, bb, md, pc)
        kit["status"] = "photo-only"
        kit["photo_only_why"] = (f"a {kit['kind'] or 'product of unknown kind'} has no honest procedural model — the real cut-outs "
                                 "are its references (model/reference-*.png); the fix uses them")
        if kit["kind"] == "soft":
            kit["shape_fixed"] = False
        log(f"  photo-only ({kit['kind']}) — real cut-outs as references")
    if kp.exists() and "behaviour" not in kit:   # a rebuild keeps what the last one learned
        try:
            prev = json.loads(kp.read_text()).get("behaviour")
            if prev:
                kit["behaviour"] = prev
        except ValueError:
            pass
    kp.write_text(json.dumps(kit, indent=1, ensure_ascii=False))
    # HOW IT BEHAVES (the owner, 2026-10-07): every kit also reads the brand's own files
    # for what the product physically does — product_behaviour.py
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import product_behaviour
        product_behaviour.build(brand, slug, log=log)
        kit = json.loads(kp.read_text())
    except Exception as e:   # the measured kit stands; the behaviour is named as missing
        log(f"  behaviour not read ({type(e).__name__}: {e}) — run product_behaviour.py {brand} {slug}")
    return kit


def _plain_background(path) -> float:
    """1 for a plain studio background, 0 for a busy one (the border's spread)."""
    from PIL import Image, ImageStat
    im = Image.open(path).convert("L"); im.thumbnail((200, 200)); W, H = im.size
    strips = [im.crop((0, 0, W, 6)), im.crop((0, H - 6, W, H)), im.crop((0, 0, 6, H)), im.crop((W - 6, 0, W, H))]
    sd = statistics.mean(ImageStat.Stat(s).stddev[0] for s in strips)
    return max(0.0, 1 - sd / 30)


def _photo_refs(found, pack, img_u, mask_u, bb, md, pc):
    """Photo-only kits: the real cut-outs ARE the references — front from the
    packshot, turned and back from real photos that show those sides."""
    from PIL import Image
    on_white(cutout_png(img_u, mask_u, bb)).save(md / "reference-front.png")
    cutout_png(img_u, mask_u, bb).save(md / "reference-front-transparent.png")
    for view, faces in (("34", ("three-quarter", "side")), ("back", ("back",))):
        f = next((f for f in found if f is not pack and f["det"].get("facing") in faces and f["det"].get("box")
                  and not f["det"].get("held")), None)          # fingers over it leave holes in the cut-out
        for old_ref in (md / f"reference-{view}.png", md / f"reference-{view}-transparent.png"):
            if old_ref.exists():
                _versions(old_ref, md / "versions"); old_ref.unlink()
        if not f:
            continue
        im = Image.open(f["file"]).convert("RGB"); m = largest_part(pc.product_mask(f["file"], f["det"]["box"]))
        if cut_off(m):
            continue
        c = cutout_png(im, m, bbox(m))
        on_white(c).save(md / f"reference-{view}.png"); c.save(md / f"reference-{view}-transparent.png")


# ── 6. the team copy on Drive ────────────────────────────────────────────────
def readme(kit: dict, files: list[str]) -> str:
    s = kit.get("size_cm") or {}; o = kit.get("outline") or {}
    size = (f"about {s['height']} cm tall × {s['width']} cm wide (± {s.get('plus_minus')} cm — {s.get('how', '')[:140]})"
            if s.get("height") else "not measured yet — it needs one ruler measurement (the shape below is exact)")
    cols = []
    for k, label in (("tube_rgb", "body"), ("body_rgb", "body"), ("cap_rgb", "cap")):
        if kit.get(k):
            cols.append(f"{label} {hexof(kit[k])}")
    for p in kit.get("parts") or []:
        cols.append(f"{int(p['from'] * 100)}–{int(p['to'] * 100)}% down: {hexof(p['rgb'])}")
    say = {
        "kit.json": "every measurement and how it was taken (for the machine; you can ignore it)",
        "README.md": "this page",
        "packshot-cutout.png": "the REAL packshot, cut out on a transparent background — drop it into Photoshop / Figma / Canva",
        "front.png": "the front label as a flat picture (the texture wrapped on the 3D model)",
        "back.png": "the back label as a flat picture (plain colour if there is no back photo yet)",
    }
    for v in ("front", "34", "back"):
        nice = {"front": "straight on", "34": "turned a little", "back": "from behind"}[v]
        say[f"reference-{v}.png"] = f"the product {nice}, on white — attach it (with the packshot) to an AI image tool so it draws the right shape"
        say[f"reference-{v}-transparent.png"] = f"the product {nice}, transparent background — for Photoshop / Figma / video overlays"
    lines = [f"# {kit.get('product', '')} — product kit", "",
             f"**What it is:** {kit.get('what', '')} ({kit.get('kind') or 'kind not known'}).",
             f"**Status:** {kit.get('status')}", "",
             "## The real product, measured from its own photos", "",
             f"- **Real size:** {size}",
             f"- **Shape:** {o.get('axis_ratio')}× as long as it is wide. Any picture where it looks taller-and-thinner or shorter-and-wider than that is wrong.",
             f"- **Colours:** {', '.join(cols) or '—'}",
             f"- **Words on the front label (biggest):** {' · '.join(kit.get('label_words') or []) or '—'}",
             "", "## What each file is for", ""]
    for f in files:
        if f.endswith(".blend"):
            lines.append(f"- `{f}` — the 3D model. Open it in Blender (free) to pose the real product at any angle or light; the labels are packed inside.")
        else:
            lines.append(f"- `{f}` — {say.get(f, 'part of the kit')}")
    lines += ["", "## Rules", "",
              "- Use these instead of drawing the product. Never redraw the label from memory.",
              "- Older copies of every file are in `versions/`.",
              "- Something looks wrong? Tell the owner — the kit is rebuilt from the real photos, not edited by hand here.", ""]
    if kit.get("status") == "photo-only":
        lines.insert(6, "*This product has no 3D model on purpose (soft or irregular — a made-up model would be less true than the photos). Use the real cut-outs.*\n")
    return "\n".join(lines)


def publish(brand: str, slug: str, root: Path | None = None, log=print) -> Path:
    """Copies the team-usable kit to Drive: brands/<brand>/products/<slug>/product-kit/.
    Only that one folder is ever written; older copies go to product-kit/versions/."""
    root = root or drive_brands()
    if not root:
        raise SystemExit("the shared Drive is not mounted on this machine")
    pf = root / brand / "products" / slug
    if not pf.is_dir():
        raise SystemExit(f"no Drive folder for {brand}/{slug}")
    d = home(brand, slug); kp = d / "kit.json"
    kit = json.loads(kp.read_text()) if kp.exists() else {"product": f"{brand}/{slug}", "status": "no kit yet"}
    md = d / "model"
    want = [kp] if kp.exists() else []
    for n in ("packshot-cutout.png", "front.png", "back.png"):
        want.append(md / n)
    for v in VIEWS:
        want += [md / f"reference-{v}.png", md / f"reference-{v}-transparent.png"]
    want += sorted(md.glob("*.blend"))
    want = [p for p in want if p.exists()]
    out = pf / "product-kit"; out.mkdir(exist_ok=True)
    names = [p.name for p in want]
    rd = d / "README.md"; rd.write_text(readme(kit, ["README.md"] + names))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    n = 0
    for p in [rd] + want:
        t = out / p.name
        if t.exists():
            if t.read_bytes() == p.read_bytes():
                continue
            (out / "versions").mkdir(exist_ok=True)
            shutil.copy2(t, out / "versions" / f"{t.stem}-{stamp}{t.suffix}")
        shutil.copy2(p, t); n += 1
    log(f"  published {n} file(s) → {out}")
    return out


def _hand_list():
    rows = listing()
    w = max([len(f"{r['brand']}/{r['slug']}") for r in rows] + [10])
    for r in rows:
        name = f"{r['brand']}/{r['slug']}"
        print(f"{name:<{w}}  {str(r['kind'] or '-'):<12} {str(r['ratio'] or '-'):<7} {r['status']}")
    miss = [r for r in rows if r["gate"]]
    print(f"\n{len(rows)} products · {len(rows) - len(miss)} with a usable kit · {len(miss)} not ready")
    for r in miss:
        print("  " + r["gate"])
    return 1 if miss else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    if a[0] == "detect":
        print(json.dumps(detect(a[1], a[2]), indent=1))
    elif a[0] == "build":
        k = build(a[1], a[2])
        print(json.dumps({x: k.get(x) for x in ("status", "kind", "size_cm", "label_words")}, indent=1, ensure_ascii=False))
    elif a[0] == "render":
        kp = home(a[1], a[2]) / "kit.json"; render(kp); v = check_render(kp)
        k = json.loads(kp.read_text()); k["check"] = v
        k["status"] = "model" if v["ok"] else f"model — check failed: {'; '.join(v['why'])}"
        kp.write_text(json.dumps(k, indent=1, ensure_ascii=False)); print(json.dumps(v, indent=1))
    elif a[0] == "check":
        print(json.dumps(check_render(home(a[1], a[2]) / "kit.json"), indent=1))
    elif a[0] == "publish":
        publish(a[1], a[2])
    elif a[0] == "list":
        sys.exit(_hand_list())
    else:
        print(__doc__); sys.exit(2)
