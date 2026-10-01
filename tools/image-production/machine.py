#!/usr/bin/env python3
"""The image machine — every swipe through the whole chain, all at once.

    machine.py                 every swipe that has a teardown
    machine.py <competitor>-09...   just these
    machine.py --from 4        start at a later stage
    machine.py --lanes 3       how many swipes at a time (default 4)

    machine.py --dry-run runs/<brand>/<batch>         a batch, resolved
    machine.py --dry-run <swipe> --brand <brand> ...  a swipe, resolved

**The dry run spends nothing.** For every batch folder or swipe named it
resolves each input — the batch.json, the template, the style pack, the
picture format, the prompt as it would be sent, the packshot, the logo, the
palette, the fonts, the offer bank — says OK or MISSING per concept, and says
what the elements and copy gates would decide. No model, no generator, no
judge; nothing written to the run, to `runs/` or to Drive. Exit 1 if anything
required is missing. A batch folder carries its own brand, so `--brand`,
`--avatar` and `--product` are only needed for swipes.

Each swipe walks its own stages 2 → 6 and then builds its ads. Swipes run
beside each other; the stages inside one swipe stay strictly in order,
because they feed each other.

**One job per swipe, never two.** Two jobs on the same swipe overwrite each
other's outputs and the brief comes back half-written — that happened on
2026-08-31 and cost an afternoon. The lock below is what stops it.

Watch it on the board: http://localhost:8779/image-lane/image-board.html
"""
import argparse, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))
import paths as P                       # every path is found by walking up

LAB = P.LAB
TD = P.TEARDOWN
LOGS = P.PROD / "logs"


def log(run, msg):
    LOGS.mkdir(exist_ok=True)
    line = f"{datetime.now():%H:%M:%S}  {msg}\n"
    (LOGS / f"{run}.log").open("a").write(line)
    print(f"  {run:<28} {msg}", flush=True)


def locked(run):
    """One job per swipe. A stale lock from a killed job is not a lock."""
    f = LOGS / f".{run}.lock"
    if f.exists():
        try:
            pid = int(f.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    LOGS.mkdir(exist_ok=True)
    f.write_text(str(os.getpid()))
    return False


def unlock(run):
    (LOGS / f".{run}.lock").unlink(missing_ok=True)


def one(run, first, last, build, brandargs, brand=None, product=None):
    if locked(run):
        print(f"  {run:<28} already running — skipped")
        return run, "skipped"
    try:
        for s in range(first, last + 1):
            t0 = time.time()
            r = subprocess.run(
                [sys.executable, str(TD / "tools/run.py"), run, str(s)]
                + brandargs,
                capture_output=True, text=True, cwd=str(TD))
            if r.returncode:
                log(run, f"stage {s} FAILED — {r.stderr.strip()[-160:]}")
                return run, f"failed at stage {s}"
            log(run, f"stage {s} done in {round(time.time()-t0)}s")
        if build:
            t0 = time.time()
            r = subprocess.run(
                [sys.executable, str(P.TOOLS / "run_production.py"), run]
                + (["--brand", brand] if brand else [])
                + (["--product", product] if product else []),
                capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if line.strip():
                    log(run, line.strip()[:150])
            log(run, f"build done in {round(time.time()-t0)}s")
        return run, "done"
    finally:
        unlock(run)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("runs", nargs="*")
    a.add_argument("--from", dest="first", type=int, default=2)
    a.add_argument("--to", dest="last", type=int, default=6)
    a.add_argument("--lanes", type=int, default=4)
    a.add_argument("--no-build", action="store_true")
    a.add_argument("--brand")
    a.add_argument("--avatar")
    a.add_argument("--product")
    a.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true",
                   help="resolve every input and say OK or MISSING per concept — "
                        "no model, no generator, no judge, nothing written")
    o = a.parse_args()

    def is_batch(t):
        return any((c / "batch.json").is_file() for c in (Path(t), P.PROD / t, P.RUNS / t))

    # A batch folder names its own brand. A swipe does not, and no brand is
    # ever the default — so for swipes all three are required, as before.
    swipes_named = [t for t in o.runs if not is_batch(t)]
    if (swipes_named or not o.runs) and not (o.brand and o.avatar and o.product):
        a.error("the following arguments are required for a swipe: --brand, --avatar, --product")

    if o.dry_run:
        import dryrun
        targets = o.runs or sorted(
            d.name for d in (TD / "runs").iterdir()
            if d.is_dir() and (d / "out/01-teardown.md").is_file())
        sys.exit(dryrun.main(
            targets, o.brand, o.product, o.first, o.last, not o.no_build,
            ["--brand", o.brand or "", "--avatar", o.avatar or "", "--product", o.product or ""]))
    if len(swipes_named) != len(o.runs):
        a.error("a batch folder is run with run.py <batch-folder>; machine.py "
                "runs swipes (and dry-runs either)")
    # No brand is the default. Defaulting to one meant every other brand's
    # run silently used the wrong avatar and product.
    brandargs = ["--brand", o.brand, "--avatar", o.avatar,
                 "--product", o.product]

    runs = o.runs or sorted(
        d.name for d in (TD / "runs").iterdir()
        if d.is_dir() and (d / "out/01-teardown.md").is_file())
    if not runs:
        sys.exit("no swipes with a teardown to run")

    print(f"{len(runs)} swipe(s), {o.lanes} at a time, "
          f"stages {o.first}-{o.last}{'' if o.no_build else ' + build'}")
    print("watch: http://localhost:8779/image-lane/image-board.html\n")
    with ThreadPoolExecutor(max_workers=o.lanes) as pool:
        for run, how in pool.map(
                lambda r: one(r, o.first, o.last, not o.no_build, brandargs,
                              o.brand, o.product),
                runs):
            print(f"{run:<30} {how}")


if __name__ == "__main__":
    main()
