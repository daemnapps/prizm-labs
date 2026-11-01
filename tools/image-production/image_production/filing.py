"""Where the pictures go.

Media is not git (workspace rule 3), so a picture lands in two places and
neither of them is a commit:

    <out>                                          the caller names it
    Shared Assets/runs/<tool>/<brand>/<label>/      the Drive mirror

The mirror path is exactly the one `components/run-kit/run_kit/filing.py`
builds, so a picture made here sits beside the run record of whatever chain
asked for it.

The mirror reaches the Drive through the mount when this run has no
GDRIVE_SA_KEY, else through gdrive-creator by id (`drive_reach.route()`), and
says so out loud when there is neither.

**NOTHING IS EVER DELETED ON THE DRIVE, MOUNT OR API.** `rm -rf` on a Drive
folder trashes it and the rebuild gets a new id, killing every link already
handed out. A file is copied in, or replaced in place — never removed, never
moved.

**Filing never stops a delivery.** A mirror that cannot be written prints
SKIP and the reason; the pictures are already in `out` and the caller has
them (`gates.py file_quietly`, same rule).
"""
import json
import time
from pathlib import Path

from . import drive_reach as DR
from . import paths as P


def out_dir(req):
    d = Path(req["out"]).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def label_for(req):
    """The run label — the caller's, else the date. It is the folder name on
    Drive, so it is a label a person can read."""
    return str(req.get("label") or time.strftime("%Y-%m-%d", time.gmtime()))


def drive_plan(brand, label, tool=None):
    """Where the mirror WOULD go, for the dry run. Never calls the API and
    never touches the mount beyond asking whether it is there."""
    t = tool or P.TOOL
    try:
        how = DR.route()
    except DR.NoDrive as e:
        return None, str(e)
    if how == "mount":
        return str(DR.mount() / "runs" / t / brand / label), None
    return f"Shared Assets/runs/{t}/{brand}/{label}/ (through the Drive API, by id)", None


def mirror(files, brand, label, tool=None):
    """Copy the delivered pictures to Drive. Returns (copied, note).

    A file already there is REPLACED IN PLACE (same name, on the mount or
    through the API), which keeps the Drive id and so keeps every link
    already given. `copied` holds mount paths, or `Shared Assets/...` paths
    for an API mirror."""
    copied, note, _ = mirror_record(files, brand, label, tool)
    return copied, note


def mirror_record(files, brand, label, tool=None):
    """mirror(), plus the drive.json record of what it wrote
    (LD-64 (records Drive ids)). Returns (copied, note, record): copied and note exactly as
    mirror gives them; record the Drive folder, its id and each picture's id
    (null ids on the mount route; route "none" and no files with no Drive)."""
    t = tool or P.TOOL
    parts = ["runs", t, brand, label]
    try:
        r = DR.put_ids(files, parts)
    except DR.NoDrive as e:
        return [], f"SKIP the Drive mirror — {e}", DR.drive_json(parts, None, "none", [])
    how, placed, note = r["how"], r["placed"], r["note"]
    if how == "api" and note is None:
        note = (f"mirrored through the Drive API (no mount here): {len(placed)} "
                f"file(s) to Shared Assets/runs/{t}/{brand}/{label}/")
    record = DR.drive_json(parts, r["folder_id"], how, [
        {"path": row["name"], "id": row["id"], "kind": row["kind"]} for row in r["files"]])
    return placed, note, record


def write_drive_json(out, record):
    """<out>/drive.json holding the record, or None (nothing written) when
    record is None (LD-64 (records Drive ids))."""
    if record is None:
        return None
    p = Path(out) / "drive.json"
    p.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def record(out, req, ctx, model, prompt_path, pictures, held, drive, tool=None):
    """`run.json` — what was asked for, what wrote it, where it went, and the
    state. Text only; a record never carries a picture."""
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    state = {
        "machine": tool or P.TOOL,
        "brand": ctx["brand"],
        "label": label_for(req),
        "purpose": ctx["purpose"]["id"],
        "request": {k: v for k, v in req.items() if not k.startswith("_")},
        "context": {
            "product": {k: v for k, v in ctx["product"].items() if k != "judge_tests"},
            "palette": ctx["palette"],
            "palette_from": ctx["palette_from"],
            "logo": ctx["logo"],
            "fonts": ctx["fonts"],
            "elements": ctx["elements"]["picked"],
            "references": ctx["references"],
            "missing": ctx["missing"],
        },
        "model": model,
        "prompt": {"skeleton": P.rel(prompt_path), "as_sent": "prompt-as-sent.txt"},
        "pictures": pictures,
        "held": held,
        "drive": drive,
        "state": "held" if held else "filed",
        "filed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (d / "run.json").write_text(P.portable(json.dumps(state, indent=1, ensure_ascii=False)) + "\n")   # rule 4
    return d / "run.json"
