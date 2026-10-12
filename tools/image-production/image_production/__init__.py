"""image-production — one image engine every workflow uses.

    import image_production as IP
    IP.make({"brand": "...", "purpose": "email-hero", "direction": "...",
             "out": "..."})
    IP.dry_run({...})

One request shape, one context builder, one prompting structure, one model
route, one judge, the shared gates. Nothing here names a brand, a product, a
person or a model; every one of those is read at run time — brand content from
`brands/<brand>/`, elements from `components/elements/`, models from this
folder's `models.json`.

Stdlib only. Pillow is used if it is there (one measured check) and its
absence is not a failure.
"""
from . import (brand_facts, context, dryrun, engine, filing, gates, judge,  # noqa: F401
               paths, prompting, providers, route)
from .engine import BadRequest, finish, finish_entry, make, purposes, resolve  # noqa: F401

TOOL = paths.TOOL


def dry_run(req, **kw):
    """Resolve and print. Spends nothing, writes nothing. Returns
    (ok, resolved)."""
    report, resolved = dryrun.run(req, **kw)
    return report.missing == 0, resolved
