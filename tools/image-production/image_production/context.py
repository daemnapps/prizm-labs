"""The ONE context builder. The brand's own facts, assembled the same way for
every caller — email, static ads, pages, video.

Nothing in this file names a brand, a product, a colour or a font. Every
value is read from `brands/<brand>/` at run time (workspace rule 7, and
components/CLAUDE.md rule-9 (brand home): brand CONTENT comes only from the
real brands tree).

Assembled from three places that each did half of it:
  - `tools/image-production/static/tools/paths.py` — `product_images`,
    `product_cutout` (the packshot for the product NAMED, not the one product
    a brand happens to have), and the identity folder
  - `tools/image-production/static/tools/dryrun.py` `_brand_rows` — palette read
    as every hex in `identity/*.md`, logo, fonts, and OK / MISSING per row
  - `components/email-production/simple_email.py` `product_photo` — the real
    product photo, ranked (packshot, cutout, -00, hero), which is the one that
    is passed BACK IN as a reference so the product is ours

A file that is declared but not on this machine is reported, never guessed:
media is not in git (workspace rule 3), so a fresh clone has the declaration
and not the bytes, and the caller is told exactly that.
"""
import json
import re
from pathlib import Path

from . import brand_facts as BF
import pathlib

from . import assets as AS
from . import paths as P

PICTURE = (".png", ".jpg", ".jpeg", ".webp")
HEX = re.compile(r"#[0-9A-Fa-f]{6}")
# The order a product photo is preferred in, lifted from simple_email.py.
RANK = ("packshot", "cutout", "-00", "hero")


class Missing:
    """One thing the picture wanted and did not get. Reported, never raised
    here — the gates decide what is fatal."""

    def __init__(self, what, detail, fatal=False):
        self.what, self.detail, self.fatal = what, detail, fatal

    def __repr__(self):
        return f"{self.what}: {self.detail}"

    def as_dict(self):
        return {"what": self.what, "detail": self.detail, "fatal": self.fatal}


def _local(v):
    return bool(v) and not str(v).startswith(("http://", "https://"))


def product_images(brand):
    """`brands/<brand>/products/images.json` → {key: {hero, cutout, all}}."""
    try:
        return json.loads(P.brand(brand)["product_images"].read_text()).get("products", {})
    except (OSError, ValueError):
        return {}


def product_known(brand, key):
    """Does the brand declare this product at all? A `.md` beside the others
    counts, because not every brand keeps an images.json row for everything."""
    if not key:
        return False
    if key in product_images(brand):
        return True
    products = P.brand(brand)["products"]
    return ((products / key / "product.md").is_file()
            or (products / f"{key}.md").is_file()
            or (products / key).is_dir())


# A brand may declare its product photo as the url of its own storefront image
# — a brand here declares every one of its products that way — and the model
# needs a FILE. Fetching the photo a brand itself declares is reading its data,
# never inventing a product. It is cached outside the repo and off the Drive:
# media never enters git (rule 3) and nothing is written into `brands/`.
CACHE = pathlib.Path.home() / ".cache" / "daemn" / "product-photos"


def fetched(brand, key, url, timeout=20):
    """(local path, why) for a declared remote photo, or (None, why not)."""
    if not str(url).lower().startswith(("http://", "https://")):
        return None, "not a url"
    ext = pathlib.Path(str(url).split("?")[0]).suffix.lower() or ".jpg"
    if ext not in PICTURE:
        ext = ".jpg"
    out = CACHE / brand / f"{key}{ext}"
    if out.is_file() and out.stat().st_size > 1024:
        return out, f"cached at {out}"
    try:
        import urllib.request
        out.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(str(url), headers={"User-Agent": "image-production"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if len(data) < 1024:
            return None, "what came back was too small to be a photograph"
        out.write_bytes(data)
        return out, f"fetched once and cached at {out}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


_fetched = fetched  # old private name, kept for callers


def product_photo(brand, key):
    """The real product photograph for the product NAMED — the thing that is
    passed back into the model as a reference.

    Returns (path_or_url, note). The path is returned whether or not the file
    is on this machine; the caller reports it missing. `None` means the brand
    declares nothing usable for that product."""
    if not key:
        return None, "no product named"
    root = P.brand(brand)["root"]
    declared = (product_images(brand).get(key) or {})
    for field in ("cutout", "hero"):
        v = declared.get(field)
        if _local(v):
            if not (root / v).is_file():
                # not in this repo copy: the same picture on the Drive, by Drive id
                on_drive = P.drive_picture(brand, v)
                if on_drive:
                    return on_drive, f"declared as `{field}` in products/images.json, found on the Drive by its id"
            return root / v, f"declared as `{field}` in products/images.json"
        if v:
            got, why = fetched(brand, key, v)
            if got:
                return got, f"declared as `{field}` in products/images.json, {why}"
            return v, (f"declared as `{field}` in products/images.json — a remote url, "
                       f"and it could not be fetched ({why})")

    folder = root / "products" / key / "images"
    cands = sorted(p for p in folder.glob("*") if p.suffix.lower() in PICTURE) if folder.is_dir() else []
    cands += sorted(p for p in (root / "products" / "images").glob(f"{key}*")
                    if p.suffix.lower() in PICTURE) if (root / "products" / "images").is_dir() else []
    cands += [p for p in P.drive_product_pictures(brand, key) if p.suffix.lower() in PICTURE]
    if cands:
        cands.sort(key=lambda p: next((i for i, r in enumerate(RANK) if r in p.name.lower()), 9))
        return cands[0], f"found in {P.rel(cands[0].parent)}"
    return None, "the brand declares no photograph for this product"


def product_title(brand, key):
    return (product_images(brand).get(key) or {}).get("title") or key


def logo(brand):
    """The brand's logo, whatever it is called. A fixed filename was wrong:
    one brand keeps `logo-white.png`, another keeps three `*-logo*.svg`, and
    the tool that hardcoded the first reported the second as having no logo."""
    # It also looks on the DRIVE, and it looks DEEP. A real brand kit is a tree
    # — Logo/<name>-Logo/01 Primary Logo/01 Digital/02 White/…/02 PNG/ — and a
    # flat listing of one folder in the repo found nothing while the whole kit
    # sat on the mount (2026-09-21). Media is not in git, so the Drive is where
    # it lives.
    homes = [P.brand(brand)["identity"]]
    try:
        # Drive: Team Drive/brands/<brand>/brand-identity/logos/ (organized
        # 2026-10-01; the old Drive name `identity/` no longer exists). The
        # folder is found through brandpath, so a later rename follows.
        d = AS._drive_brand(brand)
        homes.append(P.brandpath().resolve_rel(brand, "brand-identity", root=d.parent) / "logos")
    except Exception:
        pass
    found = []
    for d in homes:
        if not d or not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if (f.is_file() and "logo" in f.name.lower()
                    and f.suffix.lower() in PICTURE + (".svg",)):
                found.append(f)
    if not found:
        return []
    # A picture model reads a raster. Vector is kept for people, not for models,
    # and the PRIMARY mark beats a secondary one.
    def rank(f):
        n = str(f).lower()
        return (0 if f.suffix.lower() in PICTURE else 1,
                0 if "primary" in n else 1,
                0 if "png" in f.suffix.lower() else 1,
                -f.stat().st_size)
    # Two is enough — the primary mark on light and on dark. A model handed
    # forty variants of one logo averages them.
    return sorted(found, key=rank)[:2]


def palette(brand):
    """Every colour the brand has written down — read out of its own identity
    files, so a picture is never given a colour nobody signed.

    A headline once shipped in a competitor's pink because nothing of ours was
    on file to replace it (brands/<brand>/identity/palette.md says so)."""
    d = P.brand(brand)["identity"]
    hexes, where = [], []
    for f in sorted(d.glob("*.md")) if d.is_dir() else []:
        found = HEX.findall(f.read_text(errors="replace"))
        if found:
            where.append(P.rel(f))
        for h in found:
            if h.upper() not in {x.upper() for x in hexes}:
                hexes.append(h)
    return hexes, where


def fonts(brand):
    f = P.brand(brand)["identity"] / "fonts.md"
    return f if f.is_file() else None


def element_rows(req, library):
    """The element library's own rows for the style, format and template this
    request names. `library` is the seam: `components/elements/machine/
    elements.py` in production, a stub in tests.

    (picked, rows, problems) — an unknown id is REFUSED naming the real ids,
    and a draft row that only reserves a name is refused as not defined yet."""
    picked, rows, problems = {}, {}, []
    for field, element in (("style", "style"), ("format", "format"), ("template", "template")):
        value = req.get(field)
        if not value or value == "prompted":
            continue
        picked[field] = value
        try:
            row = library.get(element, "image", value)
        except library.Unknown as e:
            problems.append(f"{field}: {e.args[0]}")
            continue
        if str(row.get("what") or "").lstrip().startswith("[TO DEFINE"):
            problems.append(
                f"{field}: `{value}` is named but not defined yet — the {element} "
                f"list holds the name and no definition, so nothing can be built to it")
            continue
        rows[field] = row
    return picked, rows, problems


def build(req, library=None):
    """The whole context for one request. Returns a plain dict — the shape the
    prompt, the route, the gates and the dry run all read."""
    brand = P.need_brand(req.get("brand"), "the packshot, the logo and the colours")
    purpose = req["_purpose"]          # already resolved and checked by engine.resolve
    product = req.get("product")
    missing = []

    photo, photo_note = product_photo(brand, product)
    need_photo = purpose.get("product_reference", "none")
    # Usable means USABLE AS A REFERENCE: a file on this machine, right now.
    # A remote url is not — nothing here downloads, so a url is a declaration
    # the model never sees, and a purpose that is made FROM the real product
    # photograph cannot be made from one.
    on_machine = bool(photo) and isinstance(photo, Path) and photo.is_file()

    if product and not product_known(brand, product):
        missing.append(Missing("product", f"brands/{brand} declares no product `{product}`",
                               fatal=True))
    elif need_photo == "required" and not product:
        missing.append(Missing("product", f"purpose `{purpose['id']}` is made FROM the real "
                                          f"product photograph — name a product", fatal=True))
    elif photo is None:
        if need_photo == "required":
            missing.append(Missing("product photo", f"{photo_note} — `{purpose['id']}` cannot be "
                                                    f"made without it", fatal=True))
    elif not on_machine:
        where = photo_note if not isinstance(photo, Path) else \
            f"{P.rel(photo)} is declared and is not on this machine (media is not in git)"
        detail = where
        if need_photo == "required":
            detail += (f" — `{purpose['id']}` is made FROM the real photograph, and nothing here "
                       f"downloads one. Put the file on this machine, or name a product the brand "
                       f"keeps a local photograph for")
        missing.append(Missing("product photo", detail, fatal=(need_photo == "required")))

    logos = logo(brand)
    if not logos:
        missing.append(Missing("logo", f"brands/{brand}/identity holds no logo file"))
    colours, colour_files = palette(brand)
    if not colours:
        missing.append(Missing("palette", f"no colour written down in brands/{brand}/identity/*.md"))
    font_file = fonts(brand)
    if font_file is None:
        missing.append(Missing("fonts", f"no brands/{brand}/identity/fonts.md"))

    picked, rows, element_problems = ({}, {}, [])
    if library is not None:
        picked, rows, element_problems = element_rows(req, library)

    facts = BF.facts_for_prompt(brand, product)
    tests, facts_note = BF.product_checks(brand, "", product)

    references = []
    if photo is not None and isinstance(photo, Path) and photo.is_file() and need_photo != "none":
        references.append(photo)

    # THE BRAND'S OWN ASSETS, matched to what this picture is about (2026-09-21).
    # Every hero picture before this went out with an empty reference list: the
    # model was handed words and nothing else, so it drew competent stock
    # instead of this brand. The assets were already on the Drive and nothing
    # read them. Matched on the direction's own words; a picture with nobody in
    # it is never handed the cast. Turn it off with `assets: False` on a request.
    # An EDIT takes no matched assets unless asked: the reference IS the
    # picture, and on the first live edit (2026-09-22) three matched packshots
    # rode along and the model painted hands and a towel into a headline swap.
    asset_note = []
    if req.get("assets", not req.get("from_image")) is not False:
        try:
            found, asset_note = AS.pick(brand, req.get("direction", ""), product,
                                        want_people=req.get("people"),
                                        limit=int(req.get("asset_limit", 3)))
        except Exception as e:                       # a slow or absent mount never stops a run
            found, asset_note = [], [f"the brand's assets could not be read ({type(e).__name__})"]
        for r in found:
            f = Path(r["path"])
            if f.is_file() and f not in references:
                references.append(f)
        if not found:
            missing.append(Missing("brand assets", asset_note[0] if asset_note else
                                   "nothing matched", fatal=False))
    for extra in req.get("references") or []:
        p = Path(extra)
        if p.is_file():
            references.append(p)
        else:
            missing.append(Missing("reference", f"{extra} is not a file on this machine", fatal=True))
    from_image = req.get("from_image")
    if from_image:
        p = Path(from_image)
        if p.is_file():
            references.insert(0, p)
        else:
            missing.append(Missing("from_image", f"{from_image} is not a file on this machine", fatal=True))

    return {
        "brand": brand,
        "brand_root": str(P.rel(P.brand(brand)["root"])),
        "purpose": purpose,
        "product": {
            "key": product,
            "title": product_title(brand, product) if product else None,
            "photo": str(photo) if photo else None,
            "photo_note": photo_note,
            "photo_on_machine": bool(photo and isinstance(photo, Path) and photo.is_file()),
            "facts": facts,
            "facts_note": facts_note,
            "judge_tests": tests,
        },
        "logo": [str(p) for p in logos],
        "palette": colours,
        "palette_from": colour_files,
        "fonts": str(font_file) if font_file else None,
        "elements": {"picked": picked, "rows": rows, "problems": element_problems},
        "references": [str(p) for p in references],
        "assets_why": asset_note,
        "missing": [m.as_dict() for m in missing],
        "_missing_objects": missing,
    }
