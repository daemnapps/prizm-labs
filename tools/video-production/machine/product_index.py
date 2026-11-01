"""THE PRODUCT INDEX: one fast lookup for every product's assets, so a tool reads one small file instead of digging.

2026-10-28: core assets get one fast index every tool reads.

Built from each product's kit (runs/ai-elements/<brand>/products/<slug>/kit.json) and the Shared Assets Drive folder:

  runs/ai-elements/PRODUCT-INDEX.json            every product, for machines: facts + a path to every asset
  runs/ai-elements/PRODUCTS.md                   the wiki's front page, for people: one line per product
  runs/ai-elements/<brand>/products/<slug>/PRODUCT.md   the product's card: the summary, then every asset by name

Read it, never re-scan:  import product_index as PI;  PI.find("brand-a", "war-face-wash", "label_art")

    python3 product_index.py            rebuild everything (product_kit.py sheet and score rebuild it too)
"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import product_kit as PK  # noqa: E402

BANK = PK.BANK
INDEX = BANK / "PRODUCT-INDEX.json"
FRONT = BANK / "PRODUCTS.md"
DRIVE_LABEL = "Shared Assets/brands"
# ONE MASTER (2026-10-28, components/naming/WHERE-EVERYTHING-GOES-damon.md item 5): the kit at
# runs/ai-elements/<brand>/products/<slug>/ is the product's one master. The Drive folder
# brands/<brand>/products/<slug>/product-kit/ is where the label art and the source files live (and the team copy
# `product_kit.py publish` puts there): a SOURCE, never a second master. Every entry and card says so.
SOURCE_ROLE = "label art and source files"
DRIVE_PARTS = {   # Drive folder -> what it holds, in the order a tool usually wants them
    "product-kit/3d-model": "the 3D models (.blend, .glb) and their renders",
    "product-kit/label-art": "the real label print files (bottle wrap and box)",
    "product-kit/source-files": "factory and source files (CAD and the like)",
    "cgi/360-rotate": "the brand's own CGI turntable video",
    "cgi": "the brand's own CGI stills",
    "packshot": "studio packshots",
    "lifestyle": "lifestyle photo shoots",
    "shopify-2026-10-08": "the store's own photos and videos",
    "video": "the store's product videos",
}


def _rel(p: Path | None) -> str | None:
    try:
        return str(p.relative_to(PK.WS)) if p else None
    except ValueError:
        return str(p)


def _drive(brand: str, slug: str) -> dict:
    """Each Drive folder that exists for the product: its label (a Shared Assets path) and how many files it holds."""
    root = PK.drive_brands()
    out = {}
    if not root:
        return out
    base = root / brand / "products" / slug
    for sub, what in DRIVE_PARTS.items():
        d = base / sub
        if d.is_dir():
            files = [f.name for f in d.iterdir() if f.is_file() and not f.name.startswith(".")]
            out[sub] = {"label": f"{DRIVE_LABEL}/{brand}/products/{slug}/{sub}", "holds": what, "files": len(files),
                        "examples": sorted(files)[:4]}
    return out


def entry(kit_path: Path) -> dict:
    kit = json.loads(kit_path.read_text()); d = kit_path.parent
    brand, slug = d.parent.parent.name, d.name
    std = json.loads((d / "model" / "standard.json").read_text()) if (d / "model" / "standard.json").is_file() else {}
    sheet = d / str((kit.get("sheet") or {}).get("file") or "model/product-sheet.png")
    angles = next((d / "model" / "sheet" / v / "angles.json" for v in ("master-v4", "master-v3", "jutsu-v2", "jutsu")
                   if (d / "model" / "sheet" / v / "angles.json").is_file()), None)
    he = kit.get("higgsfield_element") or {}
    models = sorted(_rel(p) for p in d.rglob("*") if p.suffix in (".blend", ".glb") and not {"versions", "work"} & set(p.parts))
    mech = kit.get("mechanics") or {}
    return {
        "brand": brand, "product": slug, "name": str((kit.get("aliases") or [slug])[0]).upper(),
        "what": kit.get("what") or kit.get("kind"),
        "size_cm": kit.get("size_cm"), "size_source": kit.get("size_cm_source") or ("hand-measured" if "size_cm" in (kit.get("hand_set") or []) else "estimated"),
        "closure": mech.get("closure"), "how_it_opens": mech.get("how_it_opens"),
        "held": (kit.get("behaviour") or {}).get("held"), "never_show": (kit.get("behaviour") or {}).get("never_show") or [],
        "formula": kit.get("formula_words"), "materials": kit.get("materials"),
        "physics": [{"action": a.get("action"), "how": a.get("how"), "timing": a.get("timing"), "prompt_line": a.get("prompt_line"),
                     "clip": a.get("clip"), "frames": a.get("frames")} for a in (kit.get("physics") or {}).get("actions") or []],
        "version": kit.get("version"), "standard": {"complete": std.get("complete"), "of": std.get("of"),
                                                    "open": [k for k, v in (std.get("rows") or {}).items() if v.get("state") in ("missing", "partial")]},
        "assets": {
            "kit": _rel(kit_path),
            "casting_sheet": _rel(sheet) if sheet.is_file() else None,
            "angles": _rel(angles),
            "models": models,
            "master_model": kit.get("master_model_v4") or kit.get("master_model"),
            "in_use_photos": [_rel(d / r) for r in (kit.get("in_use") or {}).get("refs") or []],
            "formula_photos": [_rel(d / x["picture"]) for x in kit.get("formula") or [] if x.get("picture")],
            "mechanics_review": _rel(d / "model" / "mechanics-review.jpg") if (d / "model" / "mechanics-review.jpg").is_file() else None,
            "label_art": (kit.get("label_art") or {}).get("files") or [],
            "higgsfield_element": {"id": he.get("id"), "name": he.get("name"),
                                   "use": f"<<<{he['id']}>>> in a Higgsfield prompt" if he.get("id") else None},
            "drive": _drive(brand, slug),
            "label_art_and_source_files": {
                "label": f"{DRIVE_LABEL}/{brand}/products/{slug}/product-kit",
                "role": SOURCE_ROLE,
                "note": "a source, not a second master: the master is this kit (runs/ai-elements/<brand>/products/<slug>/)"},
        },
    }


def card(e: dict) -> str:
    a = e["assets"]; sz = e.get("size_cm") or {}
    size = " × ".join(f"{sz[k]:g}" for k in ("height", "width", "depth") if isinstance(sz.get(k), (int, float)))
    L = [f"# {e['name']} · {e['brand']}", "",
         f"_Built by `tools/video-production/machine/product_index.py` from the kit. Do not edit by hand._", "",
         "## In one look", "",
         f"- **What:** {e.get('what') or '—'}",
         f"- **True size:** {size + ' cm' if size else '—'} ({e.get('size_source')})",
         f"- **Opens:** {e.get('closure') or '—'}{' — ' + e['how_it_opens'] if e.get('how_it_opens') else ''}",
         f"- **Held:** {e.get('held') or '—'}",
         f"- **Formula:** {e.get('formula') or '—'}",
         f"- **Physics:** " + ("; ".join(f"{p['action']}: {p.get('how') or ''}" for p in e.get("physics") or []) or "—"),
         f"- **Standard:** {e['standard'].get('complete')} of {e['standard'].get('of')}; open: {', '.join(e['standard']['open']) or 'none'}",
         f"- **Version signed off:** {'yes' if (e.get('version') or {}).get('approved_by') else 'no'}", "",
         "## Where everything is", "",
         f"- Casting sheet (send this with every picture of it): `{a['casting_sheet']}`",
         f"- Every angle and state, with verdicts: `{a['angles']}`",
         f"- Higgsfield element: `{a['higgsfield_element']['name']}` → {a['higgsfield_element']['use'] or '—'}",
         f"- The kit (all facts): `{a['kit']}` — the one master for this product",
         f"- Label art and source files: `{a['label_art_and_source_files']['label']}/` on the Drive — a source, "
         "not a second master",
         f"- 3D models: " + (", ".join(f"`{m}`" for m in a["models"]) or "—"),
         f"- Real label print files: " + (", ".join(f"`{x}`" for x in a["label_art"]) or "— none yet"),
         f"- In-use photos: {len(a['in_use_photos'])} · formula photos: {len(a['formula_photos'])}"
         + (f" · mechanics review: `{a['mechanics_review']}`" if a["mechanics_review"] else ""), "",
         "## On the Drive", ""]
    L += [f"- **{k}** ({v['files']} files): {v['holds']} → `{v['label']}`" for k, v in a["drive"].items()] or ["- not reachable from this machine"]
    if e.get("never_show"):
        L += ["", "## Never show it", ""] + [f"- {x}" for x in e["never_show"]]
    return "\n".join(L) + "\n"


def build(log=print) -> dict:
    entries = [entry(kp) for kp in sorted(BANK.glob("*/products/*/kit.json"))]
    INDEX.write_text(json.dumps({"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "read_with": "product_index.find(brand, product, key)",
                                 "products": {f"{e['brand']}/{e['product']}": e for e in entries}}, indent=1, ensure_ascii=False) + "\n")
    for e in entries:
        (BANK / e["brand"] / "products" / e["product"] / "PRODUCT.md").write_text(card(e))
    rows = ["# Products — the index", "", "Every product's card: the summary, then a link to every asset. Machines read "
            "`PRODUCT-INDEX.json` (same facts). Rebuilt from the kits; never edit by hand.", "",
            "| Product | Brand | Size (cm) | Standard | Card |", "|---|---|---|---|---|"]
    for e in entries:
        sz = e.get("size_cm") or {}
        size = " × ".join(f"{sz[k]:g}" for k in ("height", "width") if isinstance(sz.get(k), (int, float)))
        rows.append(f"| {e['name']} | {e['brand']} | {size or '—'} | {e['standard'].get('complete')}/{e['standard'].get('of')} | "
                    f"[{e['product']}]({e['brand']}/products/{e['product']}/PRODUCT.md) |")
    FRONT.write_text("\n".join(rows) + "\n")
    log(f"  index: {len(entries)} products → {_rel(INDEX)}, {_rel(FRONT)}, one PRODUCT.md each")
    return {"products": len(entries)}


def find(brand: str, product: str, key: str | None = None):
    """The product's index entry (or one key of it, or of its assets). Reads the index; builds it once if missing."""
    if not INDEX.is_file():
        build(log=lambda *_: None)
    e = json.loads(INDEX.read_text())["products"].get(f"{brand}/{product}")
    if e is None or key is None:
        return e
    return e.get(key, (e.get("assets") or {}).get(key))


if __name__ == "__main__":
    build()
