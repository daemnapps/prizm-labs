#!/usr/bin/env python3
"""A micro-drama series, planned ahead: each part runs the micro-drama workflow; part N is written from what part N-1
shows on screen and keeps its creative matrix row.

    drama_series.py check   <series.json>                          before writing; writes series-check.json on a pass
    drama_series.py written <series.json> --writing-run <folder>   after writing; writes continuity.json on a pass

series.json (recipe formats/recipes/drama-series-v1.md):
    part 1  {"series": "<slug>", "part": 1}
    part N  {"series", "part", "previous": {"workflow": "<repo path>", "cut": {"path", "sha256"} | {"drive_id", "label"}},
             "on_screen": "<repo path>", "story": "<repo path>", "pin": {"batch", "row"}}

`check` holds part N when the on-screen read, the cut or the story is missing, the story does not name the on-screen
read as its source, or the pin is not part N-1's own row. `written` holds a writing run whose creative matrix row is not
the pin (part N) or whose locked story is not this part's story, and records the run's row for the next part.
Every reason is printed; exit 1 on a hold. No model, no network. Brand-agnostic; Python 3.9.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "run-kit"))
from run_kit.paths import repo  # noqa: E402

WS = repo(HERE)


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _file(ref):
    return (WS / str(ref)) if ref else None


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _cell(writing_run):
    c = _read(Path(writing_run) / "matrix-cell.json") or {}
    return {"batch": c.get("batch"), "row": c.get("row")} if c.get("row") else None


def check(series_path):
    s = _read(series_path)
    if not isinstance(s, dict):
        return ["series.json is missing or not JSON"]
    bad = []
    if not s.get("series"):
        bad.append("series.json names no series")
    part = s.get("part")
    if not isinstance(part, int) or part < 1:
        return bad + ["part must be a whole number from 1"]
    if part == 1:
        return bad
    prev = s.get("previous") or {}
    pw = _file(prev.get("workflow"))
    cont = _read(pw / "continuity.json") if pw else None
    if not isinstance(cont, dict):
        bad.append("part %d: part %d's continuity.json is not found in %s" % (part, part - 1, prev.get("workflow")))
    elif cont.get("part") != part - 1:
        bad.append("part %d follows part %s, not part %d" % (part, cont.get("part"), part - 1))
    cut = prev.get("cut") or {}
    if cut.get("path"):
        f = _file(cut["path"])
        if not f.is_file():
            bad.append("the previous part's cut is not on this machine: %s" % cut["path"])
        elif cut.get("sha256") != _sha(f):
            bad.append("the previous part's cut has changed since it was named (sha256)")
    elif not (cut.get("drive_id") and cut.get("label")):
        bad.append("name the previous part's accepted cut: a repo path with sha256, or a drive_id and label")
    read = _file(s.get("on_screen"))
    if not (read and read.is_file()):
        bad.append("no on-screen read of the previous part (previous-part-on-screen.md)")
    else:
        text = read.read_text()
        if "product" not in text.lower():
            bad.append("the on-screen read says nothing about the product: where it is on screen, or that it never appears")
    story = _file(s.get("story"))
    if not (story and story.is_file()):
        bad.append("no story.md for this part")
    elif read and s.get("on_screen") not in (story.read_text().splitlines() or [""])[0]:
        bad.append("story.md's first line is not 'Built from: %s'" % s.get("on_screen"))
    pin = s.get("pin") or {}
    if not (pin.get("batch") and pin.get("row")):
        bad.append("no pinned creative matrix row (pin: batch and row)")
    elif isinstance(cont, dict):
        had = cont.get("matrix_cell") or {}
        if (had.get("batch"), had.get("row")) != (pin.get("batch"), pin.get("row")):
            bad.append("the pin %s/%s is not part %d's row %s/%s" % (pin.get("batch"), pin.get("row"), part - 1,
                                                                    had.get("batch"), had.get("row")))
    return bad


def written(series_path, writing_run):
    bad = check(series_path)
    s = _read(series_path) or {}
    run = Path(writing_run)
    if not run.is_absolute():
        run = WS / run
    st = _read(run / "run.json")
    if not isinstance(st, dict):
        return bad + ["no writing run at %s" % writing_run], None
    cell = _cell(run)
    if not cell:
        bad.append("the writing run has no creative matrix row (matrix-cell.json)")
    if (s.get("part") or 1) > 1:
        pin = s.get("pin") or {}
        if cell and (cell["batch"], cell["row"]) != (pin.get("batch"), pin.get("row")):
            bad.append("the writing ran on row %s/%s, not the pinned %s/%s: pin it before writing (creative_matrix.py cell)"
                       % (cell["batch"], cell["row"], pin.get("batch"), pin.get("row")))
        story = _file(s.get("story"))
        want = hashlib.sha256(story.read_bytes()).hexdigest()[:16] if story and story.is_file() else None
        if (st.get("story") or {}).get("sha") != want:
            bad.append("the writing run's locked story is not this part's story.md (run.py <label> --story <story.md>)")
    rec = {"series": s.get("series"), "part": s.get("part"), "writing_run": str(run.relative_to(WS)) if str(run).startswith(str(WS)) else str(writing_run),
           "matrix_cell": cell, "story_sha": (st.get("story") or {}).get("sha"),
           "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return bad, rec


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "written"):
        print(__doc__)
        return 2
    series = Path(argv[1])
    if not series.is_absolute():
        series = WS / series
    if argv[0] == "check":
        bad = check(series)
        if not bad:
            (series.parent / "series-check.json").write_text(json.dumps(
                {"result": "PASS", "series_sha256": _sha(series), "part": (_read(series) or {}).get("part")}, indent=1) + "\n")
    else:
        if "--writing-run" not in argv:
            print("written needs --writing-run <folder>")
            return 2
        bad, rec = written(series, argv[argv.index("--writing-run") + 1])
        if not bad:
            (series.parent / "continuity.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print("PASS" if not bad else "\n".join("HOLD " + b for b in bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
