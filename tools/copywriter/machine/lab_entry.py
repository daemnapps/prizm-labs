#!/usr/bin/python3
"""The mini's door into copy.py — a lab-run turns a request into this call.

    lab-run → lab_entry.py --source S --product P [--avatar A] [--write_as F] [--dry_run yes]

Why it exists (ready.md §L3, 2026-09-22): lab-run passes only `--name value`
pairs, but copy.py wants a positional source and a bare --dry-run (G2); copy.py
writes its run folder inside the throwaway worktree, which dies after the run,
so the folder is copied into $OUT here (G3); and the shebang above is
absolute, so the mini runs 3.9.6, not whichever python3 is first on PATH (G4).

$BRAND and $OUT come from lab-run. The label is $OUT's last segment, so the run
folder and the lab-run folder carry the same name. Brand context is read from
this checkout, not a clone elsewhere on the machine.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                   # tools/copywriter/machine → repo root
sys.path.insert(0, str(HERE))
import paths as P                        # noqa: E402  where copy.py files a run
YES = {"yes", "true", "1"}


def copy_argv(args, brand, label):
    argv = [str(HERE / "copy.py"), args.source, "--brand", brand,
            "--product", args.product, "--label", label, "--brand-root", str(REPO)]
    if args.avatar:                      # left out, triage picks — as in copy.py
        argv += ["--avatar", args.avatar]
    if args.write_as:
        argv += ["--write-as", args.write_as]
    if str(args.dry_run).strip().lower() in YES:
        argv.append("--dry-run")
    return argv


def main(argv=None, env=None, run=subprocess.call):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--product", required=True)
    ap.add_argument("--avatar", default="")
    ap.add_argument("--write_as", default="")
    ap.add_argument("--dry_run", default="no")
    args = ap.parse_args(argv)
    brand, out = env.get("BRAND"), env.get("OUT")
    if not brand or not out:
        sys.exit("lab_entry: $BRAND and $OUT are set by lab-run; run copy.py directly by hand")
    out = Path(out)
    rc = run([sys.executable] + copy_argv(args, brand, out.name))
    made = P.run_dir(brand, out.name)
    if made.is_dir():                    # a dry run writes nothing; a failed run keeps what it made
        shutil.copytree(str(made), str(out), dirs_exist_ok=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
