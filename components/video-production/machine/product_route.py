"""THE PRODUCT ROUTE AT PRODUCTION (VIDEO-RULINGS V58, owner 2026-11-18).

The swipe's style decides how the product appears, and the style bank says it once:
`styles/bank.json` -> each style's `family` -> the bank's `product_route` map.

    in-scene photoreal styles (and a style not in the bank): a made shot holds the product in it, from its casting sheet,
             never an empty hand waiting for it (V59, owner 2026-11-25). Our footage stays footage; the end card keeps
             the real photo. Production's photoreal road already places it from its sheet, so it branches as `real` did
    real     the standing rule when the bank cannot be read
    in-look  handmade, drawn, 3d styles: the ad is 100% AI; the product is generated inside the picture
             and the clip, rendered in the ad's own look from its true-size 3D build (the product's kit)

Every production step that touches the product asks `route(...)` and branches on it. The writing side reads the same map (video-writing writing_v2.product_route).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE.parent / "styles" / "bank.json"

IN_LOOK = "in-look"
IN_SCENE = "in-scene"
REAL = "real"

# the words a picture or clip prompt carries for an in-look product
IN_LOOK_LINE = ("The product is in this picture, rendered in the picture's own look (the film's style), true to the "
                "product reference's shape, size, colour and label layout: the same object, made in this style. "
                "It is not a photograph pasted in and not redrawn from words.")
IN_LOOK_HELD = ("The product in the hand is the one in the product reference, rendered in the picture's own look "
                "(the film's style): same shape, size, colour and label layout, made in this style, held naturally.")


def _bank() -> dict:
    try:
        return json.loads(BANK.read_text())
    except (OSError, ValueError):
        return {}


def family_of(style_id: str | None) -> str | None:
    sid = str(style_id or "").strip()
    return next((s.get("family") for s in _bank().get("styles") or [] if isinstance(s, dict) and s.get("id") == sid), None)


def route_of_style(style_id: str | None) -> str:
    fam = family_of(style_id)
    pr = _bank().get("product_route") or {}
    return pr.get(fam) or pr.get("unknown") or REAL


def style_of(piece: dict | None = None, run=None) -> str:
    """The production's style id: VIDEO_LOOK (a look variation), the brief's piece, then the run record."""
    sid = str(os.environ.get("VIDEO_LOOK") or (piece or {}).get("style_id") or "").strip()
    if sid or run is None:
        return sid
    rd = Path(run)
    try:
        rec = json.loads((rd / "run.json").read_text())
    except (OSError, ValueError):
        rec = {}
    if rec.get("style_id"):
        return str(rec["style_id"])
    try:   # the brief the run was made from
        import importlib.util
        sp = importlib.util.spec_from_file_location("pr_storyboard_plan", HERE / "storyboard_plan.py")
        sb = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(sb)
        doc = sb.brief_doc(rec.get("brief_from") or rd / "brief.md") or {}
        return str((doc.get("piece") or {}).get("style_id") or "")
    except Exception:  # noqa: BLE001 — an unreadable brief means the standing rule
        return ""


def route(piece: dict | None = None, run=None) -> str:
    return route_of_style(style_of(piece, run))


def in_look(piece: dict | None = None, run=None) -> bool:
    return route(piece, run) == IN_LOOK


def endcard_ref(brand: str | None, product: str | None) -> tuple[Path | None, str]:
    """An in-look END CARD's product reference: the product's 3D build render from its kit (V58). (None, why) when
    the kit has none — the end card is then held, never made from a photo or from words."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("pr_element_paths", HERE / "element_paths.py")
    ep = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(ep)
    kit = ep.product_kit(brand or "", product or "") if product else None
    refs = kit_refs(kit)
    # one clean view for the card (the three-quarter render), the multi-view sheet only when nothing else exists
    one = next((r for r in refs if r.name in ("three-quarter.png", "front.png")), refs[0] if refs else None)
    if one:
        return one, f"the 3D build render of {product}"
    return None, (f"no 3D build render in {product}'s kit (model/product-sheet.png or model/reference-*.png)"
                  if kit else f"no product kit for {product!r}")


def kit_refs(kit: Path | str | None) -> list[Path]:
    """The product's 3D build renders from its kit — the reference an in-look product is made from (never the
    real packshot, which pulls the picture photoreal)."""
    if not kit:
        return []
    k = Path(kit)
    names = ("model/product-sheet.png", "model/sheet/current/front.png", "model/sheet/current/three-quarter.png",
             "model/sheet/current/back.png")
    return [k / n for n in names if (k / n).is_file()]
