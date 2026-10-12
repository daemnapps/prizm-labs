#!/usr/bin/env python3
"""A product's true shape, measured — never described from memory.

    product_geometry.py --brand <brand> --product <slug>
    product_geometry.py --brand <brand> --product <slug> --json

the owner, 2026-09-24, on four rebuilds of one competitor sale ad: *"tube size is
still wrong"* and *"hands are awkwardly holding the tubes, use some context
here."* He was right both times, and the cause was the same each time: the
brand's product file described the container, the colour and the printing and
never the SHAPE. Asked for "a tube" with no proportion, an image model returns
a squat pot — and when the swipe being rebuilt holds small round jars, the
rebuild inherits the jar's geometry and the jar's fingertip pinch outright.

Nothing here is written by hand. The proportion is MEASURED off the brand's
own packshot, because the file is the fact; the grip is read out of the
brand's own product file if it records one. No brand, product or dimension is
named in this module (workspace rule 7) — everything comes from `--brand` and
`--product`.

**Why it matters more than it looks.** The draft standard generates the whole
picture, so every un-stated fact about the packaging is invented at generation
time, and an invented wordmark is worse than an absent one. `render.py`
already composites the real product from the brand's own photograph; this is
the other half — what the PLATE has to be told so the composite lands in a
frame that was built for the real object's proportions.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path


def _repo(start):
    p = start.resolve()
    for q in (p, *p.parents):
        if (q / "brands").is_dir() and (q / "components").is_dir():
            return q
    return p


REPO = _repo(Path(__file__).parent)

# The words a brand's product file uses when it records how the thing is held.
# Read, never assumed: a product nobody holds returns None and the prompt says
# nothing about a grip rather than inventing one.
GRIP_ROW = re.compile(r"^\|\s*\*\*How it is held\*\*\s*\|\s*(.+?)\s*\|\s*$", re.M | re.I)
SHAPE_ROW = re.compile(r"^\|\s*\*\*(?:Proportion|Shape)\*\*\s*\|\s*(.+?)\s*\|\s*$", re.M | re.I)
CONTAINER = re.compile(r"^\|\s*\*\*Container\*\*\s*\|\s*(.+?)\s*\|\s*$", re.M | re.I)


def _px(img):
    """A file's own pixel width and height. The file is the fact."""
    try:
        out = subprocess.run(["magick", "identify", "-format", "%w %h", str(img)],
                             capture_output=True, text=True, timeout=30)
        w, h = out.stdout.strip().split()[:2]
        return int(w), int(h)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None, None


def packshot(brand, product):
    """The brand's own picture of this product, alone, on a clean ground.

    Preference order is about what can be MEASURED, not about what looks
    best: a cut-out standing packshot gives a true silhouette, a hero shot
    styled in a scene does not, and a picture of someone holding it gives
    the hand rather than the object.
    """
    d = REPO / "brands" / brand / "products" / product / "images"
    if not d.is_dir():
        return None
    files = sorted(p for p in d.iterdir()
                   if p.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"))
    def rank(p):
        n = p.name.lower()
        if "hand" in n or "model" in n or "skin" in n:
            return 4                      # a person, not the object
        if "lockup" in n or "and-" in n:
            return 3                      # more than one object in frame
        if "hero" in n or "pdp" in n:
            return 2                      # styled in a scene
        if "packshot" in n:
            return 0                      # the object, alone
        return 1
    files.sort(key=lambda p: (rank(p), p.name))
    return files[0] if files else None


def words_for(ratio):
    """A ratio said the way a prompt can use it, without naming a product."""
    if ratio is None:
        return None
    if ratio >= 2.6:
        return "tall and slim"
    if ratio >= 1.7:
        return "upright, clearly taller than it is wide"
    if ratio >= 1.25:
        return "upright but stout"
    if ratio > 0.8:
        return "roughly square in silhouette"
    return "wider than it is tall"


def describe(brand, product):
    """Everything a plate prompt needs to know about this object's shape."""
    img = packshot(brand, product)
    w, h = _px(img) if img else (None, None)
    ratio = round(h / w, 2) if w and h else None
    pf = REPO / "brands" / brand / "products" / product / "product.md"
    text = pf.read_text(errors="replace") if pf.is_file() else ""
    grip = GRIP_ROW.search(text)
    shape = SHAPE_ROW.search(text)
    cont = CONTAINER.search(text)
    return {
        "brand": brand,
        "product": product,
        "image": str(img.relative_to(REPO)) if img else None,
        "pixels": [w, h] if w and h else None,
        "ratio": ratio,                       # height ÷ width
        "ratio_words": words_for(ratio),
        "declared_shape": _plain(shape.group(1)) if shape else None,
        "declared_grip": _plain(grip.group(1)) if grip else None,
        "container": _plain(cont.group(1)) if cont else None,
    }


def _plain(s):
    s = re.sub(r"[*`]", "", s)
    # A brand file cites its own evidence — "the way images/x.jpg shows it",
    # "(recorded 2026-08-20)". True in the file, noise in a prompt: a model
    # handed a file path tries to render one.
    s = re.sub(r",?\s*(?:the way|as|per|see)\s+\S*images/\S+\s*(?:shows? it)?", "", s, flags=re.I)
    s = re.sub(r"\(\s*(?:recorded|measured)[^)]*\)", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip().strip(",")


def sentence(g, grip=True):
    """The one line a plate prompt carries about the object's shape.

    Returns "" when nothing is known — a prompt that says nothing about the
    proportion is better than one that says a guessed number, because the
    guess is what put a squat pot in the frame in the first place.
    """
    if not g or not g.get("ratio"):
        return ""
    bits = [f"The product is {g['ratio_words']} — about 1 : {g['ratio']} width to "
            f"height, measured off the brand's own packshot, and that proportion "
            f"is exact rather than approximate"]
    if g.get("container"):
        bits.append("It is " + _lead_lower(_first(g["container"])))
    # `grip` is False for a frame with no hand in it: on a product-only
    # plate a sentence about how the object is held reads as an instruction
    # to put a hand in the picture, and the model obliges.
    if grip and g.get("declared_grip"):
        bits.append("It is held " + _lead_lower(_first(g["declared_grip"])))
    return " ".join(b.rstrip(".") + "." for b in bits)


def _first(s):
    """The first sentence only. A brand file argues its case over several
    sentences — right in the file, and in a prompt each extra clause is one
    more thing for a model to render literally."""
    return re.split(r"(?<=[.;:])\s+", s.strip(), maxsplit=1)[0].rstrip(".;:")


def _lead_lower(s):
    return s[0].lower() + s[1:] if s else s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--product", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    g = describe(a.brand, a.product)
    if a.json:
        print(json.dumps(g, indent=1))
        return
    if not g["image"]:
        sys.exit(f"no picture of {a.product} under brands/{a.brand}/products/"
                 f"{a.product}/images/ — nothing to measure, and nothing will "
                 f"be guessed")
    print(f"{a.brand} · {a.product}")
    print(f"  measured off  {g['image']}  ({g['pixels'][0]} x {g['pixels'][1]})")
    print(f"  proportion    1 : {g['ratio']}  — {g['ratio_words']}")
    print(f"  container     {g['container'] or '— not recorded'}")
    print(f"  held          {g['declared_grip'] or '— not recorded'}")
    print(f"\n  the line a prompt carries:\n  {sentence(g) or '— nothing known, so nothing said'}")


if __name__ == "__main__":
    main()
