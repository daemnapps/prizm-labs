#!/usr/bin/env python3
"""The copy sign-off: no picture is made from words a person has not approved.

the owner, 2026-10-27: "before images are generated in general, the actual copy needs to be reviewed so [we] can actually
put some sauce on it for a while until we're ready for full auto, because awareness levels and verbatims and spice are
the foundation of what we're doing here."

    copy_ok.py show <run>                      the words waiting for a yes: the approved picture's and the five rows'
    copy_ok.py approve <run> --by <name>       record the yes for exactly those words
    copy_ok.py check <run>                     exit 0 when every word on file is approved, 1 with what is not

The record is `out/copy-approved.json` in the run: who said yes, when, and the exact words. Words changed after the yes
are not approved: the check compares word for word. Readers: tools/image-edit `vary_recipe` (no variation picture
without it) and the teardown's `tools/pictures.py` (no first picture without it).
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

FILE = "copy-approved.json"


def _run(run):
    p = Path(run)
    if p.is_dir():
        return p
    # the run's one home since 2026-10-28: runs/image-teardown/<brand>/<run>/ (the old lane folder read for one release)
    return _teardown_paths().run_dir(str(run))


def _teardown_paths():
    """image-teardown's tools/paths.py (the writing seam), loaded under its own name so a caller's own `paths`
    module (image-edit has one) is never shadowed."""
    import importlib.util
    m = sys.modules.get("image_teardown_paths")
    if m is None:
        f = Path(__file__).resolve().parents[2] / "image-teardown" / "tools" / "paths.py"
        spec = importlib.util.spec_from_file_location("image_teardown_paths", f)
        m = importlib.util.module_from_spec(spec)
        sys.modules["image_teardown_paths"] = m
        spec.loader.exec_module(m)
    return m


def words_on_file(run):
    """Every line of copy a picture of this run would carry: the approved picture's words (out/approved-words.md, else
    the brand step's 'Our copy'), then each variation row's words."""
    o = _run(run) / "out"
    lines = []
    aw = o / "approved-words.md"
    if aw.is_file():
        lines += [l.split("`")[1] for l in aw.read_text().splitlines() if l.count("`") >= 2]
    vf = o / "variations.json"
    if vf.is_file():
        for v in json.loads(vf.read_text()).get("variations") or []:
            lines += [w for w in v.get("words") or [] if w not in lines]
    return lines


def approved(run, words=None):
    """[] when every word given (default: every word on file) is in the yes on record; else the lines that are not."""
    f = _run(run) / "out" / FILE
    yes = set(json.loads(f.read_text()).get("words") or []) if f.is_file() else set()
    want = words if words is not None else words_on_file(run)
    return [w for w in want if w not in yes]


def approve(run, by, words=None):
    o = _run(run) / "out"
    words = words if words is not None else words_on_file(run)
    if not words:
        raise SystemExit("no words on file for this run yet")
    rec = {"by": by, "at": datetime.now().isoformat(timespec="seconds"), "words": words}
    (o / FILE).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("show", "approve", "check"))
    ap.add_argument("run")
    ap.add_argument("--by")
    a = ap.parse_args()
    if a.cmd == "show":
        vf = _run(a.run) / "out" / "variations.json"
        for b in (json.loads(vf.read_text()).get("format_breaks") or []) if vf.is_file() else []:
            print("  !!  " + b)
        for w in words_on_file(a.run):
            print(("  ok  " if not approved(a.run, [w]) else "  --  ") + w)
    elif a.cmd == "approve":
        if not a.by:
            sys.exit("--by <name>: the person saying yes")
        rec = approve(a.run, a.by)
        print(f"approved by {rec['by']} at {rec['at']}: {len(rec['words'])} line(s)")
    else:
        missing = approved(a.run)
        if missing:
            print("not approved yet:\n  " + "\n  ".join(missing))
            sys.exit(1)
        print("every word on file is approved")


if __name__ == "__main__":
    main()
