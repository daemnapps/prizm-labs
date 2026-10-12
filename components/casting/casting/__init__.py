"""casting — one engine that answers "who plays this role?"

    import casting
    casting.cast(brand="…", role="…")   -> the person already banked, or the gap
    casting.build({...})                -> the nine steps, for a gap
    casting.dry_run({...})              -> the same, spending nothing

Nothing here names a brand, a person or a product. Stdlib only; the picture
door and the judge are seams.
"""
from . import bank, filing, gates, generate, judge, paths, prompting  # noqa: F401
from . import registration, search                                     # noqa: F401
from . import dryrun as _dryrun
from . import engine as _engine

cast = _engine.cast
build = _engine.build
resolve = _engine.resolve
STEPS = _engine.STEPS
GENERATING = _engine.GENERATING
FIELDS = _engine.FIELDS
REQUIRED = _engine.REQUIRED
BUILD_REQUIRED = _engine.BUILD_REQUIRED
BadRequest = _engine.BadRequest

dry_run = _dryrun.run
dry_who = _dryrun.who

__all__ = ["cast", "build", "resolve", "dry_run", "dry_who", "STEPS",
           "GENERATING", "FIELDS", "REQUIRED", "BUILD_REQUIRED", "BadRequest", "bank", "search", "judge",
           "gates", "filing", "paths", "prompting", "registration", "generate"]
