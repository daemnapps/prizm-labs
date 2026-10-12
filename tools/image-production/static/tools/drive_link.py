#!/usr/bin/env python3
"""The Drive link for anything the lane made. Mirrors first, then links.

    drive_link.py <run>                  the run's finished ads
    drive_link.py --all                  every run
    drive_link.py <run> --brand <brand>  when the run records no brand

Pictures live on Drive, never in git — so the only way to see a finished ad is
a Drive link, and a link nobody was handed is a picture nobody saw. This
mirrors each run's finished ads to `Team Drive/runs/image-production/
<brand>/<run>/` through gdrive-creator and prints that folder's link, so
showing the work is one command rather than a thing to remember.

The link is the folder id the API returned — nothing is read off the Drive
mount. With no GDRIVE_SA_KEY in the environment it says SKIP, out loud, and
exits 0: the ads are on disk. A gdrive-creator failure (a missing package, an
unreadable key) is NOT a skip — it exits non-zero and names itself (SI-35
(static mirror live): step [10] used to run a mirror script that was not there,
drop its output, and mirror nothing without a word).
"""
import os, shutil, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

NO_KEY = ("SKIP the Drive mirror — no GDRIVE_SA_KEY in the environment "
          "(components rule 8). The ads are on disk; nothing on Drive was touched.")


def finished(run):
    """The run's finished ads: `finals/ad-*.png|jpg`, directly in finals/."""
    finals = P.RUNS / run / "finals"
    if not finals.is_dir():
        return []
    return sorted(p for p in finals.iterdir()
                  if p.suffix.lower() in (".png", ".jpg") and p.name.startswith("ad-"))


def _service():
    """(engine, svc, None), or (None, None, why) when there is no key. The key
    comes from the environment only, as finish.py's delivery reads it."""
    if not os.environ.get("GDRIVE_SA_KEY"):
        return None, None, NO_KEY
    sys.path.insert(0, str(P.GDRIVE))
    from gdrive_creator import engine
    return engine, engine.service(), None


def _drive_folder(engine, svc, parts):
    """The folder id of `Team Drive/<parts…>`, found by name, made if not there."""
    d = svc.drives().list(fields="drives(id,name)", pageSize=100).execute().get("drives") or []
    shared = next((x for x in d if x["name"] == "Team Drive"), None)
    if not shared:
        raise SystemExit("no 'Team Drive' shared drive reachable by this account")
    node = shared["id"]
    for p in parts:
        node = engine.folder(p, node, svc=svc)
    return node


def mirror(run, brand, engine, svc):
    """The run's finished ads to `Team Drive/runs/<tool>/<brand>/<run>/`.
    Returns (folder id, {name: file id}); (None, {}) when nothing is finished.

    Same name = the same file, updated in place, so a link already handed out
    keeps working; nothing on Drive is ever deleted. The ads go up from a
    staging copy, not from finals/ itself, because compose leaves its
    `.compose-tmp-*` folders inside finals/ and those are not deliverables."""
    files = finished(run)
    if not files:
        return None, {}
    dest = _drive_folder(engine, svc, ["runs", P.TOOL, brand, run])
    with tempfile.TemporaryDirectory(prefix="drive-link-") as tmp:
        for f in files:
            shutil.copy2(str(f), str(Path(tmp) / f.name))
        ids = engine.mirror_tree(tmp, dest, svc)
    return dest, ids


def main():
    argv = list(sys.argv[1:])
    brand_flag = None
    if "--brand" in argv:
        i = argv.index("--brand")
        if i + 1 >= len(argv):
            sys.exit("--brand needs a value: a folder under brands/")
        brand_flag = argv[i + 1]
        del argv[i:i + 2]
    names = [a for a in argv if not a.startswith("--")]
    if not P.RUNS.is_dir():
        sys.exit(f"no runs at {P.RUNS} — nothing to mirror")
    if "--all" in argv or not names:
        runs = [d.name for d in sorted(P.RUNS.iterdir()) if d.is_dir()]
    else:
        runs = [Path(a).name for a in names]

    engine, svc, note = _service()
    if note:
        print(note)

    for run in runs:
        files = finished(run)
        if not files:
            continue
        print(f"\n{run} — {len(files)} finished")
        for f in files:
            print(f"   {f.name}")
        if not svc:
            print(f"   (not on Drive — {note})")
            continue
        try:
            brand = P.brand_of_run(run, brand_flag)
        except P.BrandRequired as e:
            print(f"   SKIP {run} — {e}")
            continue
        fid, ids = mirror(run, brand, engine, svc)
        print(f"   https://drive.google.com/drive/folders/{fid}")


if __name__ == "__main__":
    main()
