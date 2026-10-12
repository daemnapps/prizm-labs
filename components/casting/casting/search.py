"""Step 2 — the owned footage, searched for an archetype, and the frames back.

**This writes no search of its own.**
`tools/image-production/image_production/assets.py` already reads the
footage index (`tools/asset-index/work/<collection>/<id>/breakdown.json`)
and the brand's Drive shelves, and it already matches on WHAT IS IN an asset
rather than what it is called. That is exactly the search this step needs, so
it is imported. `the team notes/avatar-builder/find.py` reads the same records with
its own scan; this component calls the shared reader instead, and the one
thing it adds is the part find.py has that assets.py does not — the FRAMES
beside each record, which is what a baseline is.

The known gap is upstream and unchanged: stage 4 of the footage chain
(`promote`) has never run, so there is no
`creators/<slug>/delivered/index.jsonl` to query and the raw work folder is
read. Running it is free and turns this step from a scan into a lookup; the
interface does not change either way (find.py's own note, carried).

Brand-agnostic: the brand and the words are always passed in.
"""
import sys

from . import bank as B
from . import paths as P

FRAME = "frame_*.jpg"


def assets():
    """image-production's asset reader. APPENDED to sys.path, never inserted
    at 0: a folder at position 0 shadows the stdlib."""
    d = str(P.sibling("..", "tools", "image-production"))
    if d not in sys.path:
        sys.path.append(d)
    from image_production import assets as A
    return A


def _frames(record_dir):
    from pathlib import Path
    d = Path(record_dir) if record_dir else None
    if not d or not d.is_dir():
        return []
    return [str(p) for p in sorted(d.glob(FRAME))]


def baselines(brand, like, collection=None, limit=8, need_frames=True,
              reader=None, start=None):
    """Baseline candidates for a role — (rows, why).

    A row is `{clip, collection, said, frames, baseline, points, words,
    source}`. `baseline` is the first frame of the record: a real shot of a
    real room, which is what step 3 picks from.
    """
    A = reader if reader is not None else assets()
    want = B.words(like)
    why, rows = [], []

    described = []
    try:
        described = A.described(brand)
    except Exception as e:                       # noqa: BLE001 — a missing index is a finding, not a crash
        why.append("the footage index could not be read: %s: %s" % (type(e).__name__, e))
    if not described:
        why.append("no footage records for `%s` — the index reads owned footage into "
                   "tools/asset-index/work/<collection>/; stage 4 (promote) has "
                   "never run, so there is nothing faster to read either" % brand)

    for r in described:
        if collection and collection.lower() not in str(r.get("collection", "")).lower():
            continue
        hits = sorted(B.words(r.get("said")) & want)
        if not hits:
            continue
        frames = r.get("frames") or _frames(r.get("record"))
        if need_frames and not frames:
            continue
        rows.append({"clip": r.get("name"), "collection": r.get("collection"),
                     "kind": r.get("kind"), "said": r.get("said"),
                     "frames": frames, "baseline": frames[0] if frames else None,
                     "points": len(hits) * 5 + min(len(frames), 3),
                     "words": hits, "record": r.get("record"),
                     "source": "footage index",
                     "why": "%s — the record says %s, and it has %d frame(s)"
                            % (r.get("name"), ", ".join(hits), len(frames))})

    # The brand's own reference shelves on the Drive, matched the same way.
    # A still of a person the brand already shot is as real a room as a frame
    # pulled out of a clip.
    try:
        shelf, shelf_why = A.pick(brand, like, limit=limit)
    except Exception as e:                       # noqa: BLE001
        shelf, shelf_why = [], ["the brand's Drive shelves could not be read: "
                                "%s: %s" % (type(e).__name__, e)]
    for r in shelf:
        path = r.get("path")
        if not path or any(row.get("baseline") == path for row in rows):
            continue
        rows.append({"clip": r.get("name"), "collection": r.get("kind"),
                     "kind": r.get("kind"), "said": r.get("said") or r.get("name"),
                     "frames": [path], "baseline": path,
                     "points": 4, "words": sorted(B.words(r.get("name")) & want),
                     "record": None, "source": "the brand's Drive shelves",
                     "why": "%s (%s) — on the brand's own shelf"
                            % (r.get("name"), r.get("kind"))})
    # `pick()` returns a line per asset it chose; those assets are already in
    # `rows` with their own reason, so only its FAILURES are carried up — a
    # note repeating a candidate is noise a reader has to scan past.
    why += [w for w in shelf_why if "could not be read" in w]

    rows.sort(key=lambda r: (-r["points"], str(r["clip"])))
    rows = rows[:limit]
    if not rows:
        why.append("nothing in the owned footage or the brand's shelves matches "
                   "%s — a baseline is a real frame, so this is where the chain "
                   "stops and a person picks one" % sorted(want))
    return rows, why


def choose(brand, like, given=None, collection=None, reader=None, start=None):
    """Step 3 — the one frame this build would use, and WHY that one.

    A baseline the caller named wins outright: picking the frame the way a
    person would (the right register, the right room, a clear look at the
    archetype) is a person's job, and this only ranks the candidates.
    """
    from pathlib import Path
    rows, why = baselines(brand, like, collection, reader=reader, start=start)
    if given:
        p = Path(given).expanduser()
        return {"baseline": str(p), "on_this_machine": p.is_file(),
                "why": "named by the caller — a person picked the frame",
                "candidates": rows, "notes": why}
    top = rows[0] if rows else None
    return {"baseline": top["baseline"] if top else None,
            "on_this_machine": bool(top and Path(top["baseline"]).is_file()),
            "why": top["why"] if top else "no candidate frame was found",
            "candidates": rows, "notes": why}
