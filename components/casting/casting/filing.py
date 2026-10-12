"""Where a run and a built character go.

Three places, and none of them is a commit of pixels:

    runs/casting/<brand>/<label>/           the RUN — prompts as sent, the
                                            judge's verdicts, check.json,
                                            run.json, the proposed row
    brands/<brand>/ai-cast/<id>/            the CHARACTER's pictures, exactly
                                            where `the team notes/avatar-builder/
                                            build.py` already files them
    Team Drive/brands/<brand>/ai-cast/<id>/   the Drive mirror, step 9

The run path is `runs/<tool>/<brand>/<label>/` (ruled 2026-09-17). The
character path is the brand's and is UNCHANGED: `.gitignore`
already catches `brands/**/*.png`, so the words are versioned and the pixels
are not (workspace rule 3).

**NOTHING IS EVER DELETED ON THE DRIVE MOUNT.** A rebuild gets a new id and
every link already handed out dies; supersede into `_superseded-<date>/`
instead. A file is copied in, or replaced in place — never removed, never
moved.

**Filing never stops a delivery.** A mirror that cannot be written prints SKIP
and the reason; the pictures are already on this machine.
"""
import json
import shutil
import sys
import time
from pathlib import Path

from . import paths as P


def label_for(req):
    """The run label — the caller's, else the date."""
    return str(req.get("label") or time.strftime("%Y-%m-%d", time.gmtime()))


def plan_run_dir(brand, label, start=None):
    """Where the run WOULD be filed. Creates nothing — the dry run uses it."""
    return P.repo(start) / "runs" / P.TOOL / brand / label


def run_dir(brand, label, start=None):
    d = plan_run_dir(brand, label, start)
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir(req, start=None):
    """The caller's folder when it named one, else this run's own."""
    if req.get("out"):
        d = Path(req["out"]).expanduser()
    else:
        d = plan_run_dir(req["brand"], label_for(req), start)
    d.mkdir(parents=True, exist_ok=True)
    return d


def cast_dir(brand, cid, start=None):
    c = P.character(brand, cid, start)
    c["boards"].mkdir(parents=True, exist_ok=True)
    return c


def drive_plan(brand, cid):
    """Where the mirror WOULD go. Never touches the mount beyond asking
    whether it is there."""
    try:
        return str(P.drive_character(brand, cid)), None
    except P.MountError as e:
        return None, str(e)


def file_character(brand, cid, made, start=None):
    """The delivered sheets, into the brand's cast folder. `made` is
    `{step: path}`; a held sheet is never in it.

    Returns `{step: filed_path}`. The layout is build.py's, unchanged:
    `master-sheet.png` at the root, boards under `boards/`."""
    c = cast_dir(brand, cid, start)
    where = {"master": c["master"], "anchor": c["anchor"]}
    filed = {}
    for step, src in (made or {}).items():
        if not src or not Path(src).is_file():
            continue
        dest = where.get(step) or (c["boards"] / ("%s.png" % step))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        filed[step] = str(dest)
    return filed


def mirror(brand, cid, filed, small=True):
    """Copy the filed sheets to Drive. Returns `(copied, note)`.

    A file already there is REPLACED IN PLACE (`shutil.copy2` over the same
    name), which keeps the Drive id and so keeps every link already given."""
    try:
        dest = P.drive_character(brand, cid)
    except P.MountError as e:
        return [], "SKIP the Drive mirror — %s" % e
    copied = []
    try:
        (dest / "boards").mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return [], "SKIP the Drive mirror — %s: %s" % (type(e).__name__, e)
    root = P.character(brand, cid)["root"]
    for _step, src in (filed or {}).items():
        p = Path(src)
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = Path(p.name)
        try:
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest / rel)
            copied.append(str(dest / rel))
        except OSError as e:
            return copied, "SKIP the rest of the Drive mirror — %s: %s" % (type(e).__name__, e)
    note = None
    master = filed.get("master")
    if small and master and Path(master).is_file():
        import subprocess
        try:
            subprocess.run(["sips", "-Z", "900", "-s", "format", "jpeg",
                            "-s", "formatOptions", "75", str(master),
                            "--out", str(dest / "master-sheet-sm.jpg")],
                           capture_output=True, timeout=120)
            if (dest / "master-sheet-sm.jpg").is_file():
                copied.append(str(dest / "master-sheet-sm.jpg"))
        except (OSError, Exception) as e:        # noqa: BLE001 — a thumbnail never stops a mirror
            note = "the small copy was not made: %s" % e
    return copied, note


def record(out, req, answer, steps, prompts, sheets, filed, drive, register,
           held, start=None):
    """`run.json` — what was asked for, what each step did, where it went, and
    the state. Text only; a record never carries a picture, and never carries
    a key."""
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    state = {
        "machine": P.TOOL,
        "brand": req.get("brand"),
        "label": label_for(req),
        "role": req.get("role"),
        "id": req.get("id"),
        "kind": req.get("kind"),
        "request": dict((k, v) for k, v in req.items() if not k.startswith("_")),
        "bank": (answer or {}).get("bank"),
        "covered_before": bool((answer or {}).get("covered")),
        "baseline": (req.get("_baseline") or {}),
        "elements": (req.get("_elements") or {}).get("picked"),
        "steps": steps,
        "prompts": prompts,
        "sheets": sheets,
        "filed": filed,
        "drive": drive,
        "register": register,
        "held": held,
        "state": "held" if held else "filed",
        "filed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (d / "run.json").write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    return d / "run.json"
