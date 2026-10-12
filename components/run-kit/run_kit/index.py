"""One index over every run, built by reading `runs/` — nothing declares itself.

the owner, 2026-09-23, after the Clipper Kit turned out to read its briefs straight
out of a cloned lane's own `runs/` folder, which was then deleted: *"the
clipping teardown should've been a teardown, then the runs to create the briefs
should've been placed like we have creator briefs. We need to seriously ensure
the organization of our teardowns, records, and briefs."*

The filing standard already says where a run goes (`runs/README.md`):

    runs/<machine>/<brand>/<label>/        the working record
    runs/<machine>/<brand>/<label>/deliverable/   the thing a person traffics

What was missing is a way to ASK. With no index, a consumer that wants "every
brief for this brand" has to know each machine's private layout — which is how
one tool ended up hard-coding a path into another tool's runs folder, and how
deleting that tool silently took six briefs with it.

So: this reads the standard shape and answers the question. It declares
nothing, registers nothing, and is never the source of truth — `runs/` is. A
machine that files correctly appears here by doing nothing at all.
A brand slot named in WORKING is a machine's gitignored working folder, never a run, and is skipped.
"""
import json
import time
from pathlib import Path

from . import paths as P

# What a deliverable is CALLED varies by machine and that is fine — the index
# reads the file names rather than demanding one. A brief is whatever a
# teardown hands the next pair of hands.
BRIEF_NAMES = ("brief", "06-brief", "brief-final", "work-order", "shot-list",
               "creator-brief", "concept-brief")
READABLE = (".md", ".html", ".json", ".txt", ".pdf", ".docx")
# A machine's working folder sits in the brand slot under this name
# (runs/video-teardown/_work/, SI-56). It holds live runs, not filed ones.
WORKING = ("_work",)


def _is_brief(name):
    stem = Path(name).stem.lower()
    return any(k in stem for k in BRIEF_NAMES)


def runs_root(start=None):
    return P.repo(start) / "runs"


def scan(root=None):
    """Every run under `runs/`, as plain rows. No machine is named here.

    `root` lets a test point at its own tree; paths are then reported relative
    to that tree's parent rather than the workspace, so nothing here depends on
    where it is being run from."""
    root = Path(root or runs_root())
    base = root.parent
    rows = []
    if not root.is_dir():
        return rows
    for machine in sorted(p for p in root.iterdir() if p.is_dir()):
        for brand in sorted(p for p in machine.iterdir()
                            if p.is_dir() and p.name not in WORKING):
            for run in sorted(p for p in brand.iterdir() if p.is_dir()):
                deliv = run / "deliverable"
                files = sorted(f for f in deliv.iterdir()
                               if f.is_file() and f.suffix.lower() in READABLE) if deliv.is_dir() else []
                briefs = [f for f in files if _is_brief(f.name)]
                # A machine that has not moved to deliverable/ yet still has a
                # brief SOMEWHERE in its run. Finding it is the point of an
                # index: report it, and say plainly that it is not filed right.
                stray = []
                if not briefs:
                    stray = [f for f in run.rglob("*")
                             if f.is_file() and f.suffix.lower() in READABLE
                             and _is_brief(f.name) and "deliverable" not in f.parts
                             # `prompts/` holds the prompt AS SENT, named after
                             # its stage — `5-brief.md` is the instruction, not
                             # the brief. Counting it would report every run as
                             # having a brief it does not have.
                             and "prompts" not in f.parts][:4]
                rec = run / "run.json"
                state = None
                if rec.is_file():
                    try:
                        state = json.loads(rec.read_text()).get("state")
                    except ValueError:
                        state = "unreadable run.json"
                rows.append({
                    "machine": machine.name,
                    "brand": brand.name,
                    "label": run.name,
                    "path": str(run.relative_to(base)),
                    "state": state,
                    "has_record": rec.is_file(),
                    "deliverable": [str(f.relative_to(run)) for f in files],
                    "briefs": [str(f.relative_to(run)) for f in briefs],
                    "briefs_misfiled": [str(f.relative_to(run)) for f in stray],
                    "changed": time.strftime("%Y-%m-%d", time.gmtime(run.stat().st_mtime)),
                })
    return rows


def briefs(brand=None, machine=None, root=None):
    """Every brief, optionally for one brand or one machine. This is the call a
    consumer makes instead of reaching into another tool's folders."""
    out = []
    for r in scan(root):
        if brand and r["brand"] != brand:
            continue
        if machine and r["machine"] != machine:
            continue
        for b in r["briefs"]:
            out.append({**{k: r[k] for k in ("machine", "brand", "label", "path", "changed")},
                        "brief": f"{r['path']}/{b}", "filed": True})
        for b in r["briefs_misfiled"]:
            out.append({**{k: r[k] for k in ("machine", "brand", "label", "path", "changed")},
                        "brief": f"{r['path']}/{b}", "filed": False})
    return out


def health(root=None):
    """What is NOT filed to the standard, counted per machine. The number to
    drive to zero, not a scold: a run with a brief outside `deliverable/` is a
    brief nobody else can find without reading that machine's code."""
    rows = scan(root)
    per = {}
    for r in rows:
        m = per.setdefault(r["machine"], {"runs": 0, "with_brief": 0, "misfiled": 0, "no_record": 0})
        m["runs"] += 1
        m["with_brief"] += bool(r["briefs"])
        m["misfiled"] += bool(r["briefs_misfiled"])
        m["no_record"] += (not r["has_record"])
    return per
