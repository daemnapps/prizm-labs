#!/usr/bin/env python3
"""The handoff — one brief, packaged for the role that makes the rest of it by hand. One front door, every lane.

    python3 tools/image-edit/handoff.py <brief ID | picture run | video production run> [--brand <brand>] [--no-drive]
    python3 tools/image-edit/handoff.py <brief key> --role graphic-designer      a test hand-off from any written brief

Every hand-off folder is SELF-CONTAINED (2026-10-28: someone in Higgsfield Supercomputer with Google Drive and
GitHub opens one folder and makes the brief with nothing from this Mac): beside the lane's own package it carries
BRIEF.md, the run sheet (RUN.md + run.json, components/briefs/runsheet.py) and refs/ with every reference file the run
sheet names, and the whole folder is mirrored to the Drive at the same path. `--role` names the lane outright: the
lane's full package when the brief is ready for it, else (no approved picture yet, no production run yet, or another
role) the run-sheet hand-off alone, with the reason printed.

The brief register decides the lane by the brief's type, and a lane is named by its role, never by who fills it (the owner,
2026-10-27: "we need to do that hand off and deliveries situation ... on the video side, everything needs to run through
the same process"; "make this name agnostic. and the name of the folders need to be the same for both repo and drive";
"standardization is the default"):
- a picture brief -> graphic-designer (image_edit/handoff.py)
- a video brief   -> video-editor (tools/video-edit/handoff.py, its own builder, called through its command)
Each lands at runs/handoffs/<role>/<brand>/<brief key>/ and on the Drive at Shared Assets/runs/handoffs/<role>/<brand>/
<brief key>/, the same words; the finished work comes back into that folder's `returned/`, named with the brief key. Only a
brief that came out of its chain's final stage is taken; anything else is refused by name. Spends nothing. Prints the
drive link last. Every hand-off rebuilds the front door, runs/handoffs/INDEX.md (handoff_index.py), here and on the Drive.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from image_edit import handoff as H  # noqa: E402
from image_edit.engine import BadRequest  # noqa: E402

VIDEO = HERE.parent / "video-edit" / "handoff.py"


def video(run, no_drive):
    """The video-editor lane, through video-edit's own command (its public door): its output passes through as it is."""
    if not VIDEO.is_file():
        raise SystemExit("REFUSED: the video editor's package (tools/video-edit/handoff.py) is not on this machine yet")
    r = subprocess.run([sys.executable, str(VIDEO), run] + (["--no-drive"] if no_drive else []), capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", help="a brief ID (brief-0325 or its register key), a picture teardown run, or a video production run")
    ap.add_argument("--brand", help="narrows a brief number two brands share; names the brand of a run not yet numbered")
    ap.add_argument("--picture", help="graphic-designer lane: the approved picture; default the run's newest Looks good")
    ap.add_argument("--out")
    ap.add_argument("--no-drive", action="store_true", help="write the folder here only")
    ap.add_argument("--role", choices=sorted(set(H.LANES.values())),
                    help="the lane, named outright; falls back to the run-sheet hand-off when the full package cannot be made")
    a = ap.parse_args()
    try:
        it = H.resolve(a.what, a.brand)
    except BadRequest as e:
        if not a.role:
            raise SystemExit(f"REFUSED: {e}")
        return sheet_only(a, str(e))
    if a.role and a.role != it["lane"]:
        return sheet_only(a, f"the brief's own lane is {it['lane']}")
    if it.get("sequence"):                    # a carousel's slides are in its brief, so its hand-off IS the run sheet
        why = H.final_stage(it["run"], it["brand"], sequence=True)
        if why and not a.role:
            raise SystemExit(f"REFUSED: {why}")
        a.role = it["lane"]
        return sheet_only(a, "a carousel: every slide's step is in the run sheet")
    if it["lane"] == "video-editor":
        print(f"lane: video-editor · {it['brief'] or 'no brief number yet'} · {it['brand']}")
        try:
            video(it["run"], a.no_drive)
        except SystemExit:
            if not a.role:
                raise
            return sheet_only(a, "the video editor's package was refused (above)")
        return index(a.no_drive)
    try:
        rec = H.build(it["run"], it["brand"], out=a.out, picture=a.picture, runsheet=True if a.out else "auto")
    except BadRequest as e:
        if not a.role:
            raise SystemExit(f"REFUSED: {e}")
        return sheet_only(a, str(e))
    said = rec.get("runsheet") or {}
    print(f"run sheet: " + (f"BRIEF.md, RUN.md, run.json + {said['refs']} reference files in refs/" if said.get("files")
                            else f"NOT packed ({said.get('error') or 'not asked'})"))
    for m in said.get("missing") or []:
        print(f"  missing  {m}")
    n = sum(1 for v in rec["variations"] if v["makes_picture"])
    print(f"lane: {H.ROLE} · {rec['brief']} · {it['brand']}")
    print(f"handoff {rec['brief']}: {len(rec['variations'])} variations ({n} new pictures, "
          f"{len(rec['variations']) - n} words only) · {rec['folder']}")
    print(f"finished pictures go to: {H.RETURNED}/ in that folder")
    if a.no_drive:
        return
    d = H.to_drive(rec)
    print(f"drive: {d['label']} ({len(d['files'])} files)")
    print(f"link: {d['link']}")
    index(a.no_drive)


def sheet_only(a, why):
    """The run-sheet hand-off alone (BRIEF.md, RUN.md, run.json, refs/) for any written brief, in
    runs/handoffs/<role>/<brand>/<brief key>/ and the same path on the Drive; the lane's full package waits."""
    RS = H._runsheet_module()
    try:
        sheet = RS.build(a.what, brand=a.brand, repo=H.P.repo())
    except SystemExit as e:
        raise SystemExit(f"REFUSED: {e}")
    try:
        got = RS.pack(sheet, folder=a.out, role=a.role, repo=H.P.repo())
    except ValueError as e:
        raise SystemExit(f"REFUSED: {e}")
    print(f"lane: {a.role} · {sheet['brief']} · {sheet['brand']} · run-sheet hand-off only ({why})")
    print(f"handoff {sheet['brief_key']}: {len(sheet['steps'])} steps · BRIEF.md, RUN.md, run.json + {len(got['refs'])} "
          f"reference files in refs/ · {got['folder']}")
    for m in got["missing"]:
        print(f"  missing  {m}")
    print(f"finished files go to: {got['drive']}/{H.RETURNED}/")
    if a.no_drive or a.out:
        return
    d = H.mirror_folder(H.P.repo() / got["folder"])
    print(f"drive: {d['label']} ({len(d['files'])} files)")
    print(f"link: {d['link']}")
    index(a.no_drive)


def index(no_drive):
    """The front door, runs/handoffs/INDEX.md + START-HERE.md, rebuilt and copied to the Drive (2026-10-28)."""
    import handoff_index as HI
    s = HI.quiet_refresh(drive=not no_drive)
    if s.get("error"):
        print(f"index: not rebuilt ({s['error']})")
    else:
        print(f"index: {s['rows']} hand-offs, {s['waiting']} waiting · {s['index']}")


if __name__ == "__main__":
    main()
