"""Words set on top: the picture is made with no caption, headline or overlay text, and the brief's own type layer is
set over it afterwards (swaps rule 4, tools/image-teardown/tools/swaps.py).

    from image_production import words
    words.set_on_top("pic.png", type_layer)          # → {"ok", "plate", "elements", "notes"}

The model paints the photograph; the compositor (static/tools/compose.py: ImageMagick, no design tool) sets the words, so
they are character-exact and sit where the brief's layout puts them. The plate (the picture before the words) is kept
beside the result as `<name>.plate.<ext>`, so a change to the words never costs a new picture.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import paths as P

STROKE = {"color": "#000000", "pct": 0.6}
NATIVE_EDGE = re.compile(r"(?i)\b(stroke|outline|drop shadow)\b")


def compose_tool():
    return P.home() / "static" / "tools" / "compose.py"


def elements_of(layer):
    """The elements a layer carries, whether it is the brief's {"layout", "elements"} object or a bare list."""
    return list(layer.get("elements") or layer.get("type_layer") or []) if isinstance(layer, dict) else list(layer or [])


def prepare(layer):
    """The layer as the compositor reads it. An element whose letterform says it is outlined (the native caption look) gets
    the outline the compositor draws; every other key is the brief's own."""
    out = dict(layer) if isinstance(layer, dict) else {"elements": list(layer or [])}
    els = []
    for e in elements_of(layer):
        e = dict(e)
        lf = str(e.get("letterform") or "")
        # a drop shadow is drawn as a shadow when the layout records one (`shadow`, 2026-10-28); turning "drop shadow"
        # into a thick outline made the headline too wide at every size and it shrank to a speck
        edge = NATIVE_EDGE.search(re.sub(r"(?i)drop shadow", "", lf) if e.get("shadow") else lf)
        if not e.get("stroke") and edge:
            e["stroke"] = dict(STROKE)
        els.append(e)
    out["elements"] = els
    out.pop("type_layer", None)
    return out


def set_on_top(picture, layer, out=None, plate=None):
    """Set `layer` over `picture`. Writes the result to `out` (default: over `picture`), and keeps the plate at `plate`
    (default: beside the picture)."""
    picture = Path(picture)
    out = Path(out) if out else picture
    els = elements_of(layer)
    if not els:
        return {"ok": True, "plate": str(picture), "elements": 0, "notes": ["the layer has no words"]}
    plate = Path(plate) if plate else picture.with_name(picture.stem + ".plate" + picture.suffix)
    plate.parent.mkdir(parents=True, exist_ok=True)
    if picture.resolve() == out.resolve() or not plate.is_file():
        shutil.copy2(picture, plate)
    if isinstance(layer, dict) and layer.get("design"):      # a designed layout, in the brand's own fonts, replaces the stamped type
        from . import design_type
        return design_type.render(plate, layer, out)
    work = Path(tempfile.mkdtemp(prefix="words-"))
    try:
        lf = work / "layer.json"
        lf.write_text(json.dumps(prepare(layer), ensure_ascii=False))
        r = subprocess.run([sys.executable, str(compose_tool()), "--plate", str(plate), "--layer", str(lf), "--out", str(out)],
                           capture_output=True, text=True)
        if r.returncode or not out.is_file():
            return {"ok": False, "plate": str(plate), "elements": 0, "notes": [(r.stderr or r.stdout).strip()[-300:] or "the compositor failed"]}
        return {"ok": True, "plate": str(plate), "elements": len(els),
                "notes": [l.strip() for l in r.stdout.splitlines() if l.strip()][-4:]}
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(out.resolve().parent / ".compose-tmp", ignore_errors=True)
