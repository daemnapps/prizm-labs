"""image-edit — an edit is a delta off a reference, never a fresh shot.

    import image_edit as RE
    RE.edit({"brand": "…", "picture": "…", "change": "…"})          # one change
    RE.edit({"brand": "…", "picture": "…", "fix": "logo"})          # a named fix
    RE.vary({"brand": "…", "baseline": "…", "variations": [...]})   # the library, off a baseline
    RE.ingest("<run folder>", {"<slug>": "<picture>"})              # the pictures back, judged

The discipline (keep/change split, delta only, one change, the band) is
`discipline.py`. The pictures are made on Higgsfield by the session; the
brand files and the judge's key are read through tools/image-production. The
two-picture judge is `compare.py`. Stdlib only (Pillow only for `region`).
No brand, product, person or model is named anywhere here.
"""
from . import compare, discipline, engine, paths  # noqa: F401
from .engine import (BadRequest, deltas_from, edit, fixes, ingest, ingest_one,  # noqa: F401
                     resolve, sequence, variations, vary)

TOOL = paths.TOOL
