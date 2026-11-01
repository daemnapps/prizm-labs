#!/usr/bin/env python3
"""The writing station's command: steps 3 to 6 on a teardown run.

    python3 tools/image-writing/run.py <teardown run | label>[,more] [3,4,5,6 | all] --brand <b> --product <p>
                                            [--avatar <a>] [--sub <s>] [--ask <ask.json>] [--controls <preset>]
                                            [--gates hold|warn] [--dry-run]

`all` (the default) is 3 to 6. The run is a folder under runs/image-teardown/<brand>/ (its one home since 2026-10-28),
opened and torn down by the image teardown (steps 1, 2, 2b); the writing goes into that same run's out/ and the
teardown files the record beside it. `--dry-run` resolves every prompt, file and variable and calls nothing.

The teardown hands off here on its own: `tools/image-teardown/chain.py start ...` and `tools/run.py <run> all`
run steps 3 to 6 through this station. This command is for running the writing alone (a new prompt, a re-write).
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WRITING = ("3", "4", "5", "6")


def teardown_run():
    for r in HERE.parents:
        f = r / "tools" / "image-teardown" / "tools" / "run.py"
        if f.is_file():
            return f
    sys.exit("no tools/image-teardown/tools/run.py above this folder: the writing station runs on the teardown's engine")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) >= 2 else 2
    run, rest = argv[1], list(argv[2:])
    stages = "all"
    if rest and not rest[0].startswith("-"):
        stages = rest.pop(0)
    if stages == "all":
        stages = ",".join(WRITING)
    bad = [s for s in (x.strip() for x in stages.split(",")) if s and s not in WRITING]
    if bad:
        sys.exit(f"step {', '.join(bad)} is not a writing step: the writing station runs {', '.join(WRITING)} "
                 "(steps 1, 2 and 2b are the image teardown's)")
    # This folder holds a run.py of its own; it must never shadow the teardown's `run` for the modules that import it.
    sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
    f = teardown_run()
    spec = importlib.util.spec_from_file_location("image_teardown_run", str(f))
    engine = importlib.util.module_from_spec(spec)
    sys.modules["image_teardown_run"] = engine
    spec.loader.exec_module(engine)
    sys.argv = [str(f), run, stages] + rest
    return engine.main()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
