"""Where every generated element lives — ONE place says it (the owner, 2026-09-23:
"NOT put any of this generative work in the brands folder … the brands folder
is simply to store information about the brand … specifically this is the
casting and then we have ai-elements / sets, props and all that").

    runs/ai-elements/<brand>/casting/<person>/  a person: record, sheets, their voice/
    runs/ai-elements/<brand>/<kind>/<id>/          sets/, props/ (and any new kind)
    brands/<brand>/ai-cast/casting/              the cast LIST (who plays what) — brand info
    brands/<brand>/products/<product>/           the real product and packshots — brand info

Drive mirrors the runs paths under `Shared Assets/runs/…` (runs/README.md).
A person lives only under runs/ (2026-10-08): `casting_home` never reads the
old `brands/<brand>/ai-cast/<name>/` — a person still there is moved by a
person, never read. Brand-folder names resolve via brandpath.
"""
from __future__ import annotations
import sys
from pathlib import Path


def workspace(start: Path = Path(__file__).resolve()) -> Path:
    for p in [start, *start.parents]:
        if (p / "brands").is_dir() and (p / "components").is_dir():
            return p
    raise SystemExit("no workspace root above " + str(start))


WS = workspace()
sys.path.insert(0, str(WS / "components" / "brandpath"))
import brandpath as BP                                   # noqa: E402

CASTING = "casting"
ELEMENTS = "ai-elements"
DRIVE_RUNS = "Shared Assets/runs"


def casting_root(brand: str, ws: Path | None = None) -> Path:
    # people are one kind of element, beside sets and props (the owner, 2026-09-23:
    # "ai casting should go under elements structure as well like sets and props")
    return (ws or WS) / "runs" / ELEMENTS / brand / CASTING


def casting_home(brand: str, person: str, ws: Path | None = None) -> Path:
    return casting_root(brand, ws) / person


def elements_home(brand: str, kind: str, eid: str, ws: Path | None = None) -> Path:
    return (ws or WS) / "runs" / ELEMENTS / brand / kind / eid


def cast_list(brand: str, ws: Path | None = None) -> Path:
    return BP.brand_path(brand, "ai-elements/characters", CASTING, root=(ws or WS) / "brands")


def product_home(brand: str, product: str, ws: Path | None = None) -> Path:
    return BP.brand_path(brand, "products", product, root=(ws or WS) / "brands")


def product_kit(brand: str, product: str, ws: Path | None = None) -> Path | None:
    """The product's truth kit (runs/ai-elements/<brand>/products/): the folder named
    exactly by the brief's product id, else the one folder named `<id>-…`
    (Brand B's `brush` → `device-face-brush`). None when there is no kit or the match
    is ambiguous — a product is never guessed."""
    home = elements_home(brand, "products", product, ws).parent
    exact = home / product
    if exact.is_dir():
        return exact
    # a kit that is its OWN product in the brand's files (charging-case.md) is not this one
    others = {f.stem for f in (product_home(brand, "x", ws).parent).glob("*.md")} - {product}
    hits = [d for d in sorted(home.glob(product + "-*"))
            if d.is_dir() and (d / "kit.json").is_file() and d.name not in others]
    return hits[0] if len(hits) == 1 else None


def drive_path(p: Path, ws: Path | None = None) -> str:
    """The Drive twin of a runs path, as the team writes it."""
    rel = Path(p).resolve().relative_to((ws or WS).resolve())
    return "Shared Assets/" + str(rel) + "/"
