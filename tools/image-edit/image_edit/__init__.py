"""image-edit — an edit is a delta off a reference, never a fresh shot.

    import image_edit as RE
    RE.edit({"brand": "…", "picture": "…", "change": "…"})          # one change
    RE.edit({"brand": "…", "picture": "…", "fix": "logo"})          # a named fix
    RE.vary({"brand": "…", "baseline": "…", "variations": [...]})   # the library, off a baseline

The discipline (keep/change split, delta only, one change, the band) is
`discipline.py`, lifted from the video machine's edit.py. The generation is
`tools/image-production`'s. The two-picture judge is `compare.py`.
Stdlib only. No brand, product, person or model is named anywhere here.
"""
from . import compare, discipline, engine, paths  # noqa: F401
from .engine import BadRequest, deltas_from, edit, fixes, resolve, sequence, variations, vary  # noqa: F401

TOOL = paths.TOOL
