#!/usr/bin/python3
"""The mini's door into the edit — a lab-run turns a request into one call on the ONE edit path.

    lab-run → lab_entry.py --kit <repo-relative kit folder> --label <label> [--dry_run yes]
            → the kit names its production run (edit-kit.json `from_run`): line.py <run> --out $OUT/.runs-*/$BRAND/<label>
              (a dry run says that call and runs nothing — line.py has no dry run)
            → a kit with no production run (a creator's clips): run.py start <kit> --brand $BRAND --label <label>
              --runs-root $OUT/.runs-* --cut auto [--dry-run]
    lab-run → lab_entry.py --route handoff --folder <repo-relative hand-off folder> --label <label> [--dry_run yes]
            → run.py handoff <folder> --runs-root $OUT/.runs-* --cut auto [--dry-run]

ONE EDIT PATH (C13; verify 2026-10-21 row 16): this door used to run `run.py start` on its `--cut model` default — the
retired 2026-09-20 pause-cutter prompt (prompts/stage-2-cut/stage2-cut-v2-owner.md: "cut at every pause"). A kit from
a production run now goes through line.py, the road the runners use; any other kit takes run.py's own take-whole cut
(`--cut auto`, a take laid whole, V15).

Why it exists (VE-1 (video-edit mini door), from the 2026-10-16 ready run's L3
gap 2): lab-run passes only sorted `--name value` pairs, but `run.py start`
takes the kit as a POSITIONAL path; and the lab-run worktree dies after the
run, so the run folder must end up in $OUT. The shebang above is absolute, so
the mini runs 3.9.6, not whichever python3 is first on PATH.

Two routes, exactly (LD-2 (portable video kits)): `kit`, the default, and
`handoff`, a video-editor hand-off folder in the checkout. No `pack`, and no
`--approve`, `--note`, `--controls` or `--versions` — the stops are a person's
word, not a lab-run's. Reads no vendor key — a dry
run needs none — and passes the environment through untouched apart from
AI_WORKSPACE, which names this checkout. With its own --runs-root, the
hand-off route mirrors nothing to the Drive and files no card (handoff_run.py).

Where the run lands: run.py is handed a fresh runs root under $OUT
(`$OUT/.runs-*`), so it writes `<root>/<brand>/<label>/` and nothing goes into
this checkout's runs/ (the hand-off route names its own brand and label from
the hand-off's manifest; the one folder it makes is the run). That run folder
is then MOVED (not copied — one copy, same disk) to `$OUT/<label>/`, and the
scaffold left behind is removed only if empty (rmdir, never a tree delete).
Media stays where run.py put it; this script adds none.

$BRAND and $OUT come from lab-run. Refuses (exit 2, named): a missing $BRAND
or $OUT, a kit or hand-off folder outside this checkout or not a folder, an
existing `$OUT/<label>/`, a route's folder flag on the other route, and any
argument it does not know.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                   # tools/video-edit/machine → repo root
YES = {"yes", "true", "1"}


def kit_path(repo, kit, flag="--kit"):
    """The kit (or hand-off) folder, resolved inside `repo`. A `..` part, a path that
    resolves outside the checkout, or a non-folder is a ValueError (main returns 2)."""
    raw = Path(kit)
    if ".." in raw.parts:
        raise ValueError(f"{flag} {kit} has a '..' part; name the folder from the repo root")
    repo = Path(repo).resolve()
    p = (raw if raw.is_absolute() else repo / raw).resolve()
    if p != repo and repo not in p.parents:
        raise ValueError(f"{flag} {kit} is outside this checkout ({repo})")
    if not p.is_dir():
        raise ValueError(f"{flag} {kit} is not a folder ({p})")
    return p


def start_argv(kit, brand, label, runs_root, dry):
    return ([str(HERE / "run.py"), "start", str(kit), "--brand", brand, "--label", label,
             "--runs-root", str(runs_root), "--cut", "auto"]
            + (["--dry-run"] if dry else []))


def from_run(kit):
    """The production run a kit was joined from (edit-kit.json `from_run`), when it is a folder here; else None."""
    import json
    try:
        fr = (json.loads((Path(kit) / "edit-kit.json").read_text()) or {}).get("from_run")
    except (OSError, ValueError):
        return None
    p = Path(str(fr)) if fr else None
    if p is not None and not p.is_absolute():
        p = REPO / p
    return p if p is not None and (p / "run.json").is_file() else None


def line_argv(run, brand, label, runs_root):
    return [str(HERE / "line.py"), str(run), "--out", str(Path(runs_root) / brand / label)]


def handoff_argv(folder, runs_root, dry):
    return ([str(HERE / "run.py"), "handoff", str(folder), "--runs-root", str(runs_root), "--cut", "auto"]
            + (["--dry-run"] if dry else []))


def child_env(env, repo):
    env = dict(env)
    env["AI_WORKSPACE"] = str(repo)      # runs resolve against this checkout, not ~/Projects/workspace
    return env


def main(argv=None, env=None, run=subprocess.call):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", choices=["kit", "handoff"], default="kit")
    ap.add_argument("--kit")
    ap.add_argument("--folder")
    ap.add_argument("--label", required=True)
    ap.add_argument("--dry_run", default="no")
    args = ap.parse_args(argv)
    flag, other = ("--kit", "--folder") if args.route == "kit" else ("--folder", "--kit")
    if not getattr(args, flag[2:]):
        ap.error(f"the {args.route} route needs {flag}")
    if getattr(args, other[2:]):
        ap.error(f"{other} is not the {args.route} route's — it takes {flag}")
    missing = [n for n in ("BRAND", "OUT") if not env.get(n)]
    if missing:
        print(f"lab_entry: ${' and $'.join(missing)} not set — lab-run sets them; run run.py directly by hand")
        return 2
    brand, out = env["BRAND"], Path(env["OUT"])
    try:
        folder = kit_path(REPO, getattr(args, flag[2:]), flag)
    except ValueError as e:
        print(f"lab_entry: {e}")
        return 2
    dest = out / args.label
    if dest.exists():
        print(f"lab_entry: {dest} already exists — refusing to overwrite it")
        return 2
    dry = str(args.dry_run).strip().lower() in YES
    out.mkdir(parents=True, exist_ok=True)
    runs_root = Path(tempfile.mkdtemp(prefix=".runs-", dir=str(out)))
    prod = from_run(folder) if args.route == "kit" else None
    if prod is not None:
        argv_ = line_argv(prod, brand, args.label, runs_root)
    else:
        argv_ = start_argv(folder, brand, args.label, runs_root, dry) if args.route == "kit" else handoff_argv(folder, runs_root, dry)
    cmd = [sys.executable] + argv_
    if prod is not None and dry:                         # line.py has no dry run: say the call, run nothing
        print("dry run — would run: " + " ".join(cmd))
        try:
            runs_root.rmdir()
        except OSError:
            pass
        return 0
    print(("dry run — " if dry else "") + "running: " + " ".join(cmd))
    rc = run(cmd, env=child_env(env, REPO))
    if args.route == "kit":
        made = [runs_root / brand / args.label]
    else:  # the hand-off names its own brand and label from its manifest: the one folder it made
        made = sorted(p for p in runs_root.glob("*/*") if p.is_dir())
    made = [p for p in made if p.is_dir()]
    if len(made) == 1:
        shutil.move(str(made[0]), str(dest))
        print(f"lab_entry: run folder → {dest}")
    elif made:
        print(f"lab_entry: run.py made {len(made)} run folders, not one — left under {runs_root}")
    else:
        print(f"lab_entry: run.py made no run folder (exit {rc})")
    for d in [*(p for p in runs_root.glob("*") if p.is_dir()), runs_root]:    # the scaffold, only if empty
        try:
            d.rmdir()
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
