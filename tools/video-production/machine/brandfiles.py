#!/usr/bin/env python3
"""
brandfiles.py — the two brand files the element kinds lean on, read the same
way every time (ELEMENTS.md §1, 2026-09-23):

  * the OFFER BANK — `brands/<brand>/products/offer-bank.md`. An endcard's
    words come from it and nowhere else;
  * the REAL PACKSHOT — `brands/<brand>/products/images.json` (`cutout`, then
    `hero`), else the photographs in `brands/<brand>/products/<product>/images`
    ranked packshot · cutout · -00 · hero. This is the same rule
    image-production's context builder uses (`image_production/context.py`
    `product_photo`), so a still and a video endcard reach the same file.

Nothing here names a brand. Where a brand lives is searched, in order:
`$VIDEO_MACHINE_BRANDS` (a folder of brand folders), the workspace's own
`brands/`, then `machine/fixtures/brands/` — so the test brand `_fixture`
resolves without a file of it ever entering the real brands tree.

A photograph a brand declares as a URL is fetched through image-production's
own cache (reading the brand's data, never generating a product); if that
cannot happen the caller is told exactly why and refuses.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PICTURE = (".png", ".jpg", ".jpeg", ".webp")
RANK = ("packshot", "cutout", "-00", "hero")


def _workspace() -> Path | None:
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return None


def roots() -> list[Path]:
    out = []
    env = os.environ.get("VIDEO_MACHINE_BRANDS")
    if env:
        out.append(Path(env))
    ws = _workspace()
    if ws:
        out.append(ws / "brands")
    out.append(HERE / "fixtures" / "brands")
    return out


def brand_root(brand: str | None) -> Path | None:
    if not brand:
        return None
    for r in roots():
        if (r / brand).is_dir():
            return r / brand
    return None


def offer_bank_path(brand: str | None) -> Path | None:
    b = brand_root(brand)
    f = b / "products" / "offer-bank.md" if b else None
    return f if f and f.is_file() else None


def _norm(s: str) -> str:
    s = str(s or "").lower().replace("’", "'").replace("—", " ").replace("–", " ")
    s = re.sub(r"[*_`|>#\[\]()]", " ", s)
    return " ".join(s.split())


def offer_line_found(brand: str | None, line: str) -> tuple[bool, str]:
    """Is this endcard line in the brand's offer bank? (found, why). The line,
    stripped of markdown and case, has to appear in the bank's text, and
    every price or number in it has to be one the bank prints."""
    f = offer_bank_path(brand)
    if f is None:
        return False, f"brand {brand!r} has no products/offer-bank.md"
    bank = _norm(f.read_text())
    want = _norm(line).rstrip(".!")
    if not want:
        return False, "the line is empty"
    if want in bank:
        return True, f"in {f.name}"
    nums = re.findall(r"\$?\d+(?:[.,]\d+)?%?", line)
    missing = [n for n in nums if _norm(n) not in bank]
    if nums and not missing:
        return False, (f"its figures are in {f.name} but the line itself is not — "
                       f"copy the bank's own words")
    return False, (f"not in {f.name}"
                   + (f" (and {', '.join(missing)} is not a figure it prints)" if missing else ""))


def _images_json(root: Path) -> dict:
    try:
        return json.loads((root / "products" / "images.json").read_text()).get("products", {})
    except (OSError, ValueError):
        return {}


def _fetched(brand: str, product: str, url: str):
    """A declared remote photograph, through image-production's own cache —
    the one place that already fetches a brand's own photo and caches it off
    the repo. (path, why) or (None, why not)."""
    ws = _workspace()
    if not ws:
        return None, "no workspace to find image-production in"
    try:
        import sys
        ip = ws / "tools" / "image-production"
        if str(ip) not in sys.path:
            sys.path.insert(0, str(ip))
        from image_production import context as ctx  # type: ignore
        got, why = ctx.fetched(brand, product, url)
        return got, why
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _drive_index():
    """components/brandpath/drive_index — product pictures on the Drive by id."""
    ws = _workspace()
    if not ws:
        return None
    try:
        import sys
        bp = ws / "components" / "brandpath"
        if str(bp) not in sys.path:
            sys.path.append(str(bp))
        import drive_index  # type: ignore
        return drive_index
    except Exception:
        return None


def packshot_of(brand: str | None, product: str | None, fetch: bool = False):
    """(path_or_url, why). A path is a real photograph on this machine; a url
    is a declared photograph that is not here yet (`fetch=True` fetches it
    through image-production's cache); None means the brand declares none."""
    if not product:
        return None, "no product named"
    root = brand_root(brand)
    if root is None:
        return None, f"no brand folder for {brand!r}"
    row = _images_json(root).get(product) or {}
    for field in ("cutout", "hero"):
        v = row.get(field)
        if not v:
            continue
        if not str(v).startswith(("http://", "https://")):
            p = root / v
            if p.is_file():
                return p, f"`{field}` in products/images.json"
            # not in this repo copy: the same picture on the Drive, by its Drive id
            # (the Drive was reorganized 2026-10-01 — products/DRIVE-INDEX.json)
            DI = _drive_index()
            got = DI.local(str(brand), v, root.parent) if DI else None
            if got:
                return got, f"`{field}` in products/images.json, found on the Drive by its id"
            return None, f"`{field}` in products/images.json names {v}, which is not on this machine"
        if fetch:
            got, why = _fetched(str(brand), product, v)
            if got:
                return Path(got), f"`{field}` in products/images.json, {why}"
            return v, f"`{field}` in products/images.json is a url that could not be fetched ({why})"
        return v, f"`{field}` in products/images.json (a url, fetched at make time)"
    folder = root / "products" / product / "images"
    cands = sorted(p for p in folder.glob("*") if p.suffix.lower() in PICTURE) if folder.is_dir() else []
    if not cands:
        DI = _drive_index()
        cands = [p for p in (DI.product_pictures(str(brand), product, root.parent) if DI else [])
                 if p.suffix.lower() in PICTURE]
    if cands:
        cands.sort(key=lambda p: next((i for i, r in enumerate(RANK) if r in p.name.lower()), 9))
        return cands[0], f"ranked first in products/{product}/images"
    return None, (f"brand {brand!r} declares no photograph for {product!r} — not in "
                  f"products/images.json and nothing in products/{product}/images")
