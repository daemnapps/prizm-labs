#!/usr/bin/env python3
"""
library_check.py — preflight asks the element library "is this a real one?".

    python3 library_check.py <run-dir> [--library <dir>]

The run's FORMAT was always checked against this tool's own list
(formats/bank.json, preflight rule 9). The element library
(components/elements, list `format/video`) is BUILT FROM that same file plus
the rows the owner has named and nobody has written yet — so it knows one
thing the local list cannot: a format that has a name and no definition. A run
on one of those is a run on a word, and it is refused here, before anything is
paid for (rule 13).

What is asked, and of which list:

    run.json "format"                          format/video
    run.json / the brief's piece "style_id"    style/video
    each scene's delivery dials, in the brief's json block:
        humor                                  delivery/humor
        style  (or delivery_style)             delivery/delivery_style
        register                               delivery/register
        pacing                                 delivery/pacing

A dial left empty or written `unfilled` is a dial nobody set — not a wrong
value — and is passed over. The piece's `style` is a grade SENTENCE, never an
id, and is not asked about; a look that is an id goes in `style_id`.

Nothing here spends anything, edits the library, or knows a brand.

THE IMPORT. The library's module is called `elements`, and so is this
folder's own elements.py (the mirror of the cast's source images). So it is
found by walking up to `components/elements/machine` and loaded BY PATH under
another name — `import elements` from in here would get the wrong one.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBRARY_MODULE = "components/elements/machine/elements.py"
TO_DEFINE = "[TO DEFINE"
UNSET = ("", "unfilled")

# the brief's dial → the library list that holds its values
DIALS = {
    "humor": "humor",
    "style": "delivery_style",
    "delivery_style": "delivery_style",
    "register": "register",
    "pacing": "pacing",
}


class NoLibrary(Exception):
    """components/elements cannot be found or read from here."""


def _module_file() -> Path:
    for d in HERE.parents:
        f = d / LIBRARY_MODULE
        if f.is_file():
            return f
    raise NoLibrary(f"no {LIBRARY_MODULE} above {HERE}")


def load(library_dir: Path | None = None):
    """The library module, loaded by path. `library_dir` points it at another
    folder of lists (the tests' fixture library); the real one is the default.
    Each call gets its own copy, so a fixture library never leaks into a real
    check made later in the same process."""
    f = _module_file()
    if str(f.parent) not in sys.path:
        sys.path.append(str(f.parent))            # append, never first: names collide
    try:
        spec = importlib.util.spec_from_file_location("vm_element_library", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:                        # StopIteration from its REPO walk, etc.
        raise NoLibrary(f"{LIBRARY_MODULE} would not load ({type(e).__name__}: {e})")
    if library_dir is not None:
        mod.LIBRARY = Path(library_dir)
        mod._cache = {}
    if not mod.LIBRARY.is_dir():
        raise NoLibrary(f"no library folder at {mod.LIBRARY}")
    return mod


def _defined(row: dict) -> bool:
    return not str(row.get("what") or "").lstrip().startswith(TO_DEFINE)


def real_ids(lib, element: str, asset: str) -> list[str]:
    """The ids a run may actually name: on the list, defined, not deprecated."""
    return [r["id"] for r in lib.rows(element, asset)
            if _defined(r) and r.get("status") != "deprecated"]


def ask(lib, element: str, asset: str, value: str, where: str) -> tuple[str, str] | None:
    """None when `value` is a real, defined row; else (what is wrong, what to do)."""
    try:
        row = lib.get(element, asset, value)
    except lib.Unknown:
        try:
            known = ", ".join(real_ids(lib, element, asset)) or "none yet"
        except lib.Unknown as e:
            return (f"{where} {value!r}: {e.args[0]}", "rebuild the element library")
        return (f"{where} {value!r} is not a {element}/{asset} row",
                f"use one of: {known}")
    if not _defined(row):
        known = ", ".join(real_ids(lib, element, asset)) or "none yet"
        return (f"{where} {value!r} is named but not defined yet",
                f"define it at its source first, or use one of: {known}")
    return None


def _scenes(doc) -> list[dict]:
    if not isinstance(doc, dict):
        return []
    return [s for s in (doc.get("scenes") or []) if isinstance(s, dict)]


REBUILD = "python3 components/elements/machine/elements.py build"


def problems(run_json: dict | None, brief_doc=None, library_dir: Path | None = None,
             lib=None, local_formats: list | None = None) -> list[tuple[str, str, str]]:
    """Every (item, what, todo) the library refuses. Raises NoLibrary when the
    library cannot be read — the caller decides what that means.
    `local_formats` is what this tool's own bank holds: a format that is there
    and not in the library is a library that has not been rebuilt since the
    bank changed, and the refusal says that instead of calling it unknown."""
    lib = lib or load(library_dir)
    out: list[tuple[str, str, str]] = []

    def put(item, res):
        if res:
            out.append((item, res[0], res[1]))

    rj = run_json or {}
    if rj.get("format"):
        res = ask(lib, "format", "video", str(rj["format"]), "format")
        if res and "is not a" in res[0] and rj["format"] in (local_formats or []):
            res = (f"format {rj['format']!r} is in formats/bank.json but not in the "
                   "element library — the library is older than the bank",
                   f"rebuild it: {REBUILD}")
        put("run", res)

    piece = brief_doc.get("piece") if isinstance(brief_doc, dict) else None
    piece = piece if isinstance(piece, dict) else {}
    style_id = rj.get("style_id") or piece.get("style_id")
    if isinstance(style_id, str) and style_id.strip() not in UNSET:
        put("run", ask(lib, "style", "video", style_id.strip(), "style_id"))

    for i, sc in enumerate(_scenes(brief_doc), 1):
        sid = str(sc.get("id") or f"scene {i}")
        d = sc.get("delivery")
        if not isinstance(d, dict):
            continue
        for dial, asset in DIALS.items():
            v = d.get(dial)
            if not isinstance(v, str) or v.strip().lower() in UNSET:
                continue
            put(f"brief {sid}", ask(lib, "delivery", asset, v.strip(), f"delivery.{dial}"))
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    library_dir = None
    if "--library" in argv:
        i = argv.index("--library")
        library_dir = Path(argv[i + 1])
        del argv[i:i + 2]
    run = Path(argv[0]).expanduser().resolve()
    rj = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    doc = None
    if (run / "brief.md").is_file():
        sys.path.insert(0, str(HERE))
        import model_inputs                        # noqa: E402
        doc, _ = model_inputs.json_block((run / "brief.md").read_text())
    try:
        bad = problems(rj, doc, library_dir)
    except NoLibrary as e:
        print(f"element library not readable: {e}", file=sys.stderr)
        return 3
    for item, what, todo in bad:
        print(f"[rule 13] {item}: {what} → {todo}")
    if bad:
        return 2
    print("every named element is a real, defined row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
