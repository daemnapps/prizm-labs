"""PICTURE STANDARD — a brand's product picture rules, read by the 3D set's print words and checked on the finished picture
(2026-11-07).

The owner, on the brand_b designer's Face Scrub and Body Scrub galleries: the principles in that work are established as
the design system for every product picture of the brand from now on. The rules live with the brand, as
`brands/<brand>/brand-identity/product-pictures.json` (readable copy `product-pictures.md` beside it); this file only reads
them, so a brand without one is simply not checked.

    python3 picture_standard.py show <brand>                     the rules, as JSON
    python3 picture_standard.py lines <brand> <kind>             the lines a print's words carry for that kind
    python3 picture_standard.py check <brand> <kind> <picture>   square, ground, fill and label space, measured off the pixels

Kinds are the file's `kinds` (brand_b: shop-card, gallery, offer-icon). `lines` is what `picture_sets.first_print` adds to a
print's words when the brand has a standard; `check` reads pixels only and never calls a model.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from image_production import paths as P  # noqa: E402


def standard(brand):
    """The brand's rules, or {} when it has none."""
    try:
        d = P.brand(brand)["identity"]
    except Exception:
        return {}
    f = Path(d) / "product-pictures.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def lines(brand, kind, bundle=False):
    """The print words' lines for one kind: the always rules, the kind's ground, fill and props, the bundle rules when the
    picture is a bundle, and the never list. Empty when the brand has no standard."""
    s = standard(brand)
    if not s:
        return []
    k = (s.get("kinds") or {}).get(kind)
    if k is None:
        raise SystemExit(f"{brand} has no picture kind `{kind}`; its kinds: {', '.join(s.get('kinds') or {})}")
    out = list(s.get("always") or [])
    for field, label in (("ground", "The background"), ("fill", "The framing"), ("props", "Props")):
        if k.get(field):
            out.append(f"{label}: {k[field]}.")
    if bundle:
        out += s.get("bundles") or []
    if s.get("never"):
        out.append("Never: " + "; ".join(s["never"]) + ".")
    return out


def _ground(im):
    """The ground's colour: the mean of the four corner patches (3% of the side)."""
    w, h = im.size
    n = max(4, int(min(w, h) * 0.03))
    px = []
    for x0, y0 in ((0, 0), (w - n, 0), (0, h - n), (w - n, h - n)):
        patch = im.crop((x0, y0, x0 + n, y0 + n))
        px += list(patch.get_flattened_data() if hasattr(patch, "get_flattened_data") else patch.getdata())
    return tuple(round(sum(c[i] for c in px) / len(px)) for i in range(3))


def check(brand, kind, picture):
    """Measure a finished picture against the kind's checks. Returns {ok, fails, measured}."""
    from PIL import Image
    s = standard(brand)
    k = ((s.get("kinds") or {}).get(kind) or {})
    c = k.get("checks") or {}
    im = Image.open(picture)
    w, h = im.size
    fails, m = [], {"size": [w, h]}
    if abs(w - h) > 2:
        fails.append(f"not square: {w} x {h}")
    if not c.get("transparent") and min(w, h) < 1080:
        fails.append(f"too small: {min(w, h)} px on the short side, the standard asks 1220 or more")
    if c.get("transparent"):
        alpha = im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 10
        m["transparent"] = bool(alpha)
        if not alpha:
            fails.append("no transparent ground: an offer icon shows the panel colour through it")
        return {"ok": not fails, "fails": fails, "measured": m}
    rgb = im.convert("RGB")
    g = _ground(rgb)
    m["ground_rgb"] = g
    if c.get("ground_rgb_min") is not None and min(g) < c["ground_rgb_min"]:
        fails.append(f"ground is {g}, the kind asks every channel at {c['ground_rgb_min']} or more")
    if c.get("ground_warm") and not (g[0] >= g[1] >= g[2] and g[0] - g[2] >= 12):
        fails.append(f"ground {g} is not warm (red over green over blue)")
    # fill: the box of pixels that differ from the ground by more than a soft shadow does
    small = rgb.resize((256, 256))
    pts = [(x, y) for y in range(256) for x in range(256)
           if sum(abs(a - b) for a, b in zip(small.getpixel((x, y)), g)) > 60]
    if pts:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        fill = max(max(xs) - min(xs), max(ys) - min(ys)) / 256
        m["fill"] = round(fill, 2)
        m["box_pct"] = [round(100 * min(xs) / 256), round(100 * min(ys) / 256), round(100 * max(xs) / 256), round(100 * max(ys) / 256)]
        if c.get("fill_min") is not None and fill < c["fill_min"]:
            fails.append(f"product fills {fill:.0%} of the frame, the kind asks {c['fill_min']:.0%} or more")
        if c.get("fill_max") is not None and fill > c["fill_max"]:
            fails.append(f"product fills {fill:.0%} of the frame, the kind asks {c['fill_max']:.0%} or less")
    else:
        fails.append("no product found off the ground")
    return {"ok": not fails, "fails": fails, "measured": m}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("brand")
    l = sub.add_parser("lines"); l.add_argument("brand"); l.add_argument("kind"); l.add_argument("--bundle", action="store_true")
    c = sub.add_parser("check"); c.add_argument("brand"); c.add_argument("kind"); c.add_argument("picture")
    a = ap.parse_args(argv)
    if a.cmd == "show":
        print(json.dumps(standard(a.brand), indent=1, ensure_ascii=False))
    elif a.cmd == "lines":
        print("\n".join(lines(a.brand, a.kind, a.bundle)) or f"{a.brand} has no picture standard")
    else:
        r = check(a.brand, a.kind, a.picture)
        print(json.dumps(r, indent=1))
        return 0 if r["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
