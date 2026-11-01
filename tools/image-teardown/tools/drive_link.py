#!/usr/bin/env python3
"""The Drive link for anything the lane made. Mirrors first, then links.

    drive_link.py <run>          the run's finished pictures
    drive_link.py --all          every run

Pictures live on Drive, never in git — so the only way to see a finished ad is
a Drive link, and a link nobody was handed is a picture nobody saw. This
mirrors each run's finals/ through gdrive-creator and prints the folder link
the API returned, so showing the work is one command rather than a thing to
remember.

Through the API, never the mount, and never through a lab script (workspace
rule 9; SI-36 (teardown lab mirror), 2026-10-07). Only the finished pictures
go: the rest of a run's media (drafts, worksheets, reference) is not this
tool's to carry. No key on this machine is a loud SKIP; a key with a broken
install is a failure, named.
"""
import os, shutil, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import deliver as DV

PICTURES = (".png", ".jpg", ".jpeg", ".webp")


def finished(run):
    """The finished pictures directly in the run's finals/ — never the page
    cache (finals/.web) or the composer's scratch (finals/.compose-tmp)."""
    finals = P.run_dir(run) / "finals"
    if not finals.is_dir():
        return []
    return sorted(p for p in finals.iterdir()
                  if p.is_file() and p.suffix.lower() in PICTURES
                  and not p.name.startswith("."))


def _service():
    """(engine, svc, None), or (None, None, note) when this machine holds no
    key. A key that is set but cannot be used is not a skip — it raises."""
    try:
        engine, svc = DV.service()
    except SystemExit as e:
        if os.environ.get("GDRIVE_SA_KEY"):
            raise
        return (None, None,
                "SKIP the Drive mirror — no GDRIVE_SA_KEY on this machine ("
                + str(e) + "). The pictures are on disk; nothing on Drive was touched.")
    return engine, svc, None


BRANDS = ("brand-a", "brand-b", "company")


def brand_of(run):
    """The brand a run belongs to, from its name (runs are named
    <brand>-... or <date>-<brand>-...). No brand in the name is refused —
    a run with no brand has no home on Drive."""
    for part in run.split("-"):
        if part in BRANDS:
            return part
    sys.exit(f"{run}: no brand in the run's name — cannot place it on Drive")


def mirror(run, engine, svc):
    """The run's finished pictures into the same Drive folder the lab script
    feeds — Shared Assets/runs/image-teardown/<brand>/<run>/finals/ — updated
    in place, never deleted. The brand is read from the run's name. Returns (folder id, {name: file id}); (None, {})
    when there is nothing finished to send."""
    files = finished(run)
    if not files:
        return None, {}
    root = DV.drive_root(engine, svc)
    dest = engine.folder("finals",
                         engine.folder(run, engine.folder(brand_of(run), root, svc), svc),
                         svc)
    # A staging copy holding only the pictures: finals/ also keeps .web and
    # .compose-tmp, and mirror_tree carries a whole folder.
    with tempfile.TemporaryDirectory(prefix="drive-link-") as tmp:
        for f in files:
            shutil.copy2(str(f), str(Path(tmp) / f.name))
        ids = engine.mirror_tree(tmp, dest, svc)
    return dest, ids


def main():
    args = sys.argv[1:]
    if not P.all_runs():
        sys.exit(f"no runs under {P.RUNS} — nothing to mirror")
    names = [Path(a).name for a in args if not a.startswith("--")]
    if "--all" in args or not names:
        names = [d.name for d in P.all_runs()]

    engine, svc, note = _service()
    if note:
        print(note)

    for run in names:
        files = finished(run)
        if not files:
            continue
        print(f"\n{run} — {len(files)} finished")
        for f in files:
            print(f"   {f.name}")
        if svc is not None:
            fid, _ = mirror(run, engine, svc)
            print(f"   https://drive.google.com/drive/folders/{fid}")
        else:
            print(f"   (not on Drive — {note})")


if __name__ == "__main__":
    main()
