#!/usr/bin/env python3
"""The video editor's handoff — one video brief, packaged for the video editor (a person or an agent) to make the
finished ad from it.

    python3 tools/video-edit/handoff.py <video-production run folder> [--out DIR] [--no-drive]

Takes a production run made from the writing chain's final stage (a test run is refused by name), or a RE-EDIT run
(its deliverable/EDITOR-BRIEF.md is the whole brief; nothing is generated: machine/reedit_handoff.py). Writes
runs/handoffs/video-editor/<brand>/<brief key>/ in the Hand-off Standard's shape (handoff.md, manifest.json, briefs/,
assets/, references/, returned/), every file named with the brief key, then copies it to the same path below
Shared Assets/ on the drive. Spends nothing. Prints the drive link last. The finished videos come back into returned/,
where the delivery check reads them by the brief key in their names.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "machine"))
import editor_handoff as H  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out")
    ap.add_argument("--no-drive", action="store_true", help="write the folder here only")
    a = ap.parse_args()
    import reedit_handoff as RE                       # a brief that generates nothing: a re-edit (2026-10-28)
    if RE.is_reedit(Path(a.run)):
        rec = RE.build(Path(a.run), no_drive=a.no_drive)
        print(f"re-edit handoff {rec['brief']}: {len(rec['shots'])} shots, {len(rec['refs'])} files copied, "
              f"{len(rec['on_drive'])} pointed at on the Drive · {rec['folder']}")
        print(f"finished cuts go to: returned/ in that folder ({', '.join(rec['deliver'])})")
        if rec.get("drive"):
            H.refresh_index(drive=True)
            print(f"link: {rec['drive']}")
        return
    try:
        rec = H.build(a.run, out=a.out, runsheet=True if a.out else "auto")
    except H.Refused as e:
        raise SystemExit(f"REFUSED: {e}")
    ok = sum(1 for s in rec["scenes"] if s["approved"])
    print(f"handoff {rec['brief']} ({rec['title']}): {len(rec['scenes'])} scenes ({ok} passed, "
          f"{len(rec['scenes']) - ok} to look at), {len(rec['returned'])} videos to make, {len(rec['files'])} files · {rec['folder']}")
    for m in rec["missing"]:
        print(f"  missing  {m}")
    print(f"higgsfield: {len(rec.get('higgsfield') or [])} clips ready to remake in Supercomputer")
    print(f"finished videos go to: {rec['returned_to']}/")
    if a.no_drive:
        return
    d = H.to_drive(rec)
    print(f"drive: {d['label']} ({len(d['files'])} files)")
    print(f"link: {d['link']}")
    s = H.refresh_index(drive=True)   # the front door, runs/handoffs/INDEX.md, on the Drive too (2026-10-28)
    print(f"index: {s.get('rows', '?')} hand-offs · {s.get('index') or s.get('error')}")


if __name__ == "__main__":
    main()
