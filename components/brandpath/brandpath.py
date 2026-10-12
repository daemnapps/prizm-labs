"""One door into a brand's folders, so the folders can be renamed without
breaking a single tool.

    from brandpath import brand_path, brand_file

    brand_path(brand, "ai-elements/characters", "casting")   # today: brands/<brand>/ai-cast/casting
    brand_path(brand, "ai-elements", "index.json")           # today: brands/<brand>/elements/index.json
    brand_file(brand, "brand-identity", "identity-anchors.md")
    brand_path(brand, "intake", "ads", root=drive_brands)    # the same map, on the Drive mirror

Every key is the folder's NEW name (the folder plan, v6); a key may be a
sub-folder of the plan ("ai-elements/characters") when today's folder maps to
one level down. `brands/<brand>/FOLDERS.json` maps each new name to the
places that content sits TODAY, in order. A lookup tries the new name first, then each old place, and returns
the first that exists on disk — so the tools keep working the day the folder
moves, with no code change. When nothing exists yet (a file about to be
written, a folder a brand does not have) the path returned is the one a tool
would have built today: under the first of those places whose folder is on
disk, else under the new name.

Rules:
  * no brand, product or person is named in this file (workspace rule 7)
  * this module never creates, moves or deletes anything — it only says where
  * FOLDERS.json missing → the defaults below, which ARE the v6 plan, and one
    stderr note per brand per process when the brand folder itself exists
"""
import json
import os
import sys
from pathlib import Path

# The v6 folder plan (the brand folder map). new name -> today's places,
# first existing wins. An empty list means the folder is new: nothing maps to
# it yet.
DEFAULTS = {
    "brand-identity": ["identity", "identity-anchors.md", "story.md", "story.html", "position.md", "compliance.json"],
    "brand-identity/voice": ["voice"],
    "ai-elements": ["elements", "element-facts.json"],   # the element library: cards, index.json, element facts
    "ai-elements/characters": ["ai-cast", "elements/character"], # the AI cast: people, casting/ (the registry), and the character pictures
    "ai-elements/environments": ["elements/environment", "set"], # Drive moved to the plural names 2026-09-29; the repo's set/ joined 2026-09-30
    "ai-elements/props": ["elements/prop"],
    "intake": ["existing-content"],
    "intake/research": ["research"],
    "strategy": ["calendar", "strategy"],
    "content-creators": ["creators", "channels/creators"],
    "content-creators/clipping": ["channels/clipping"],
    "core-avatars": ["core-avatars"],
    "products": ["products"],
    "offers": ["offers"],
    "brand-assets": [],
    "competitors": ["competitive", "qc-dictionary.json"],
    "variables": ["variables"],
    "email-sms": ["email"],
    "ads": [],
    "ads/hooks": ["hook-ledger.md"],
    "ads/copy": ["copy"],
    "web": [],
    "web/funnels": ["funnels"],
    "customer-experience": ["customer-service-documentation", "customer"],
    "learnings": [],
    "briefs": ["briefs"],
    "archive": ["archive"],
    "archive/retired-2026-09-30": ["assets.json", "product-details.md"],       # retired in v6, kept (never deleted)
    "archive/retired-2026-09-30/dropbox-migration": ["dropbox-migration"],
    "operations": ["operations", "operations.md", "commerce"],
    "operations/data-notes": ["data-notes"],
    "operations/finance": ["finance"],
    "meta": ["meta"],
    "meta/persona-pages": ["persona-pages"],
    "context": ["context", "data-sources.md", "tracker.json", "market.md"],
}
FOLDERS_FILE = "FOLDERS.json"
_NOTED = set()   # brands already told about a missing FOLDERS.json, this process


def _note_missing(brand):
    """Say once per process per brand that its map is missing — a lookup
    runs `folders` many times, so a long run must not repeat the line."""
    if brand not in _NOTED:
        _NOTED.add(brand)
        print(f"brandpath: {brand} has no {FOLDERS_FILE} — the plan's defaults apply",
              file=sys.stderr)


class UnknownFolder(KeyError):
    """The key is not a folder in the plan, and not in the brand's FOLDERS.json."""


def repo(start=None):
    """The workspace root: the first folder upward holding components/ and
    brands/. `AI_WORKSPACE` wins when it names such a folder — a worktree
    would otherwise read the main checkout by accident."""
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir() and (Path(env) / "components").is_dir():
        return Path(env).resolve()
    here = Path(start or __file__).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError(f"no workspace (components/ + brands/) found upward of {here}")


def brands_dir(root=None):
    """The folder holding one folder per brand. `root` is a different such
    folder (the Drive mirror's `brands/`); the default is the repo's."""
    return Path(root) if root is not None else repo() / "brands"


def brand_root(brand, root=None):
    return brands_dir(root) / brand


def folders(brand, root=None):
    """The brand's alias map: DEFAULTS, overlaid with `brands/<brand>/
    FOLDERS.json` when it exists and parses. Always read from the REPO copy
    of the brand — the map is a fact about the plan, not about the mirror.
    A broken or half-written file falls back to the defaults for the keys it
    does not carry."""
    out = {k: list(v) for k, v in DEFAULTS.items()}
    f = brand_root(brand) / FOLDERS_FILE
    if root is not None and not f.is_file():
        f = brands_dir(root) / brand / FOLDERS_FILE
    if not f.is_file() and (brand_root(brand).is_dir() or f.parent.is_dir()):
        _note_missing(brand)
    try:
        data = json.loads(f.read_text())
    except (OSError, ValueError):
        return out
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                v = [v]
            if isinstance(v, list) and all(isinstance(x, str) for x in v):
                out[str(k)] = list(v)
    return out


def candidates(brand, key, *rest, root=None):
    """Every place `key/rest...` could be, new name first, in the order the
    map gives. Old places that are themselves a FILE only count when the
    lookup is for a file of that same name."""
    fmap = folders(brand, root)
    if key not in fmap:
        raise UnknownFolder(f"{key!r} is not a brand folder — the plan has: "
                            + ", ".join(sorted(fmap)))
    b = brand_root(brand, root)
    places = [key] + [p for p in fmap[key] if p != key]
    out = []
    for place in places:
        base = b.joinpath(*Path(place).parts)
        if Path(place).suffix and rest:
            # a file standing in for the folder — a match only when asked for
            # that file by name
            if len(rest) == 1 and Path(place).name == rest[0]:
                out.append(base)
            continue
        out.append(base.joinpath(*rest))
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def brand_path(brand, key, *rest, root=None):
    """The first existing path among the candidates. When none exists, the
    path a tool would have built TODAY, in this order: a file standing in
    for the folder when that exact file is asked for; the candidate under the
    first place whose FOLDER is on disk; the first of today's folder places
    even when the brand has it nowhere yet; and only for a folder the plan
    adds (nothing maps to it), the new-name path. So during the alias phase
    a write lands exactly where it lands today, and moves with the folder."""
    cands = candidates(brand, key, *rest, root=root)
    for p in cands:
        if p.exists():
            return p
    b = brand_root(brand, root)
    fmap = folders(brand, root)
    places = [key] + [p for p in fmap[key] if p != key]
    if len(rest) == 1:
        for place in places:
            if Path(place).suffix and Path(place).name == rest[0]:
                return b.joinpath(*Path(place).parts)
    for place in places:
        if Path(place).suffix:
            continue
        if b.joinpath(*Path(place).parts).is_dir():
            return b.joinpath(*Path(place).parts, *rest)
    for place in places[1:]:
        if not Path(place).suffix:
            return b.joinpath(*Path(place).parts, *rest)
    return cands[0]


def brand_file(brand, key, filename, root=None):
    """`brand_path` for one file inside the folder."""
    return brand_path(brand, key, filename, root=root)


def brand_paths(key, *rest, root=None, brands=None):
    """`brand_path` across every brand under `root` (or the given brands) —
    only the paths that exist. Replaces `brands/*/<old-name>/...` globs."""
    base = brands_dir(root)
    if brands is None:
        if not base.is_dir():
            return []
        brands = sorted(p.name for p in base.iterdir()
                        if p.is_dir() and not p.name.startswith(("_", ".")))
    out = []
    for b in brands:
        try:
            p = brand_path(b, key, *rest, root=root)
        except UnknownFolder:
            raise
        if p.exists():
            out.append(p)
    return out


def old_places(brand, root=None):
    """The reverse map: each of today's places (and each new name) -> its
    key. Built from `folders`, so a brand's FOLDERS.json is honoured."""
    out = {}
    for key, places in folders(brand, root).items():
        out.setdefault(key, key)
        for place in places:
            out.setdefault(place, key)
    return out


def resolve_rel(brand, rel, root=None):
    """`brand_path` for a TODAY-style relative path ("calendar/moments.json").

    For tools whose file lists are data — a checklist, a needs table, a
    variable map. When the first segment (or the first two, for a place like
    "channels/creators") is a place the map knows, the join goes through
    `brand_path`; anything else (email/…, market.md, a run folder) comes back
    as `brands/<brand>/rel`, exactly as the tool built it before."""
    parts = list(Path(rel).parts)
    if not parts:
        return brand_root(brand, root)
    rev = old_places(brand, root)
    for n in (2, 1):
        head = "/".join(parts[:n])
        if len(parts) >= n and head in rev:
            place, rest = head, parts[n:]
            if Path(place).suffix and rest:
                # a file standing in for a folder cannot have children
                break
            if Path(place).suffix:
                return brand_path(brand, rev[place], Path(place).name, root=root)
            return brand_path(brand, rev[place], *rest, root=root)
    return brand_root(brand, root).joinpath(*parts)


def rel(brand, key, *rest, root=None):
    """`brand_path` as words for a message, relative to the brands folder."""
    p = brand_path(brand, key, *rest, root=root)
    try:
        return str(p.relative_to(brands_dir(root)))
    except ValueError:
        return str(p)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        sys.exit("usage: brandpath.py <brand> <key> [parts...]")
    print(brand_path(sys.argv[1], sys.argv[2], *sys.argv[3:]))
