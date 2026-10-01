#!/usr/bin/env python3
"""Name a finished video piece so its spend joins back to the creative.

    deliver.py <run>                    deliver <run>/deliverable (or finals/)
    deliver.py <run> --dry-run

<run> is a path to the run folder, the same way `machine/chain.py <run>`
takes one — since 2026-09-17 every machine's runs live at
`runs/<machine>/<brand>/<label>/` (see `runs/README.md`), so a run is no
longer something this script can find by name under its own folder.

Same standard as the statics — `components/naming/CONVENTION.md`. One ad unit
per piece, one asset per cut inside it. The only difference is `media=video`
and that `talent` is usually a person: the creator who shot it, or the
trained identity that appears in it.

problem, angle and concept come from the run's own brief, never from flags
typed at upload. An angle typed at upload is a guess by whoever is uploading;
an angle in the brief is the one the script was written to.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]                        # machine -> ai-video-production -> damon -> lab -> root
sys.path.insert(0, str(WS / "components" / "naming"))
import deliver as D
import names as N


def read_brief(run):
    """The three creative fields, plus anything the brief states about who is
    in the piece. A creator-shot video's talent is the creator; a generated
    one's is the trained identity; a product-only cut has none."""
    out = {}
    for cand in ("intake.json", "brief.json"):
        f = run / cand
        if f.is_file():
            try:
                d = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            for k in ("brand", "product", "problem", "angle", "concept",
                      "avatar", "format", "talent", "source", "brief",
                      "ratio"):
                if d.get(k):
                    out[k] = d[k]
    # Same search order as machine/chain.py's own brief gate, so a fully
    # brief-driven run and a legacy one are both found the same way.
    for cand in ("assets/brief-final.md", "assets/brief.md",
                 "brief-final.md", "brief.md"):
        b = run / cand
        if b.is_file():
            out.update(D.from_brief(b))
            break
    return out


def main():
    a = argparse.ArgumentParser()
    a.add_argument("run", help="path to the run folder, e.g. "
                               "runs/video-machine/<brand>/<label>")
    for f in N.AD_FIELDS:
        if f != "batch":
            a.add_argument(f"--{f}")
    a.add_argument("--batch")
    a.add_argument("--dry-run", action="store_true")
    o = a.parse_args()

    run = Path(o.run).expanduser().resolve()
    folder = run / "deliverable"
    if not folder.is_dir() and (run / "finals").is_dir():
        folder = run / "finals"             # the pre-2026-09-17 shape
    if not folder.is_dir():
        raise SystemExit(
            f"{folder} does not exist — this run has not produced finished "
            f"cuts yet. Naming is the delivery step; there is nothing to "
            f"deliver until the edit lands.")

    fields = dict(media="video", source="ugc", talent="none", ratio="9x16",
                  brief="none")
    fields.update(read_brief(run))
    fields.update({f: getattr(o, f) for f in N.AD_FIELDS
                   if f != "batch" and getattr(o, f)})

    missing = [f for f in N.AD_FIELDS if f != "batch" and not fields.get(f)]
    if missing:
        raise SystemExit(
            "the brief does not state " + ", ".join(missing) +
            " — state them in the brief, or pass them as flags. A field "
            "guessed at delivery is a field the report cannot be trusted on.")

    D.deliver(folder, fields, batch=o.batch, dry=o.dry_run)


if __name__ == "__main__":
    main()
