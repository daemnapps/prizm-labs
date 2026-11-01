"""Product casting sheets: build every sheet to one layout from product-sheet-standard.json.

Six fixed views, three to a row, then the how-it-works row. No generation, only existing pictures.
The sheet it replaces is kept once in model/versions/. A view with no good picture stays an empty
tile, so every sheet shows the same places and the gap is plain. Writes runs/ai-elements/SHEET-AUDIT.json.

  python3 tools/video-production/machine/product_sheet.py [brand/product ...]
"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

WS = Path(__file__).resolve().parents[3]
BANK = WS / "runs/ai-elements"
STANDARD = WS / "tools/video-production/product-sheet-standard.json"
KEPT = "product-sheet-before-uniform-2026-10-30.png"

WIDTH, MARGIN, TOP = 1656, 24, 120
COL, ROW, TILE_W, TILE_H = 544, 574, 516, 500
FONT = "/System/Library/Fonts/Helvetica.ttc"


def layout(n_use: int) -> tuple[int, int]:
    """Rows and height: the six views always take two rows, the use row at least one."""
    rows = 2 + max(1, (n_use + 2) // 3)
    return rows, TOP + rows * ROW + 14


def title(name: str, size: dict | None) -> str:
    s = size or {}
    tall = s.get("height") or s.get("length")
    say = f"{tall:g} cm tall × {s['width']:g} cm wide" if tall and s.get("width") else "size not measured"
    return f"{name}  ·  product casting sheet  ·  {say}"


def source(kit: Path, spec, old: Path) -> Image.Image | None:
    if not spec:
        return None
    if isinstance(spec, dict) and "file" in spec:
        im = source(kit, spec["file"], old)
        box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
        return im.crop(box) if spec.get("trim") and box else im
    if isinstance(spec, dict):
        c, r = spec["old_sheet_cell"]
        x, y = MARGIN + c * COL, TOP + r * ROW
        return Image.open(old).convert("RGB").crop((x, y, x + 540, y + TILE_H))
    if spec.endswith("*"):
        files = sorted((kit / spec[:-1]).glob("*.jpg"))
        spec = files[-1]
    im = Image.open(kit / spec).convert("RGBA")
    flat = Image.new("RGBA", im.size, "white")
    flat.alpha_composite(im)
    return flat.convert("RGB")


def paste(sheet: Image.Image, im: Image.Image, x: int, y: int) -> None:
    k = min(TILE_W / im.width, TILE_H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    sheet.paste(im, (x + (TILE_W - im.width) // 2, y + (TILE_H - im.height) // 2))


def build(key: str, spec: dict, views: list, name: str, size: dict | None) -> dict:
    kit = BANK / key.split("/")[0] / "products" / key.split("/")[1]
    now, old = kit / "model/product-sheet.png", kit / "model/versions" / KEPT
    old.parent.mkdir(exist_ok=True)
    if not old.exists():
        shutil.copy2(now, old)
    tiles = [(label, spec["tiles"].get(v)) for v, label in views] + [tuple(u) for u in spec["use"]]
    _, height = layout(len(spec["use"]))
    sheet = Image.new("RGB", (WIDTH, height), "white")
    draw = ImageDraw.Draw(sheet)
    words, points = title(name, size), 44
    while draw.textlength(words, font=ImageFont.truetype(FONT, points)) > WIDTH - 2 * MARGIN:
        points -= 1
    draw.text((MARGIN, 24), words, font=ImageFont.truetype(FONT, points), fill="black")
    small = ImageFont.truetype(FONT, 30)
    missing = []
    for i, (label, s) in enumerate(tiles):
        x, y = MARGIN + (i % 3) * COL, TOP + (i // 3) * ROW
        im = source(kit, s, old)
        if im is None:
            missing.append(label)
            draw.rectangle((x, y, x + TILE_W, y + TILE_H), fill="#f4f4f4")
        else:
            paste(sheet, im, x, y)
        draw.text((x, y + TILE_H + 14), label, font=small, fill="black")
    sheet.save(now)
    return {"sheet": str(now.relative_to(WS)), "was": str(old.relative_to(WS)), "views_filled": 6 - len([v for v, _ in views if not spec["tiles"].get(v)]),
            "views_of": 6, "how_it_works": [u[0] for u in spec["use"]], "missing": missing}


def main(only: list[str]) -> None:
    doc = json.loads(STANDARD.read_text())
    index = json.loads((BANK / "PRODUCT-INDEX.json").read_text())["products"]
    audit_path = BANK / "SHEET-AUDIT.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    for key, spec in doc["products"].items():
        if only and key not in only:
            continue
        e = index[key]
        audit[key] = build(key, spec, doc["views"], e["name"], e.get("size_cm"))
        print(key, audit[key]["views_filled"], "of 6", audit[key]["missing"] or "")
    audit_path.write_text(json.dumps(audit, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
