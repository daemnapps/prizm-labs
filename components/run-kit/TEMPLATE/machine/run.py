#!/usr/bin/env python3
"""<tool-name> — see ../CLAUDE.md. Built on components/run-kit."""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(REPO / "components" / "run-kit"))
sys.path.insert(0, str(REPO / "components" / "quality-checks"))
from run_kit import filing, paths          # noqa: E402
from run_kit.stage import Chain            # noqa: E402
import marketing_chain_checks as Q          # noqa: E402  (folder: quality-checks)

TOOL = "<tool-name>"
STEPS = [
    {"key": "stage1", "name": "Read", "tier": "reads", "label": "record"},
    {"key": "stage2", "name": "Write", "tier": "designs", "label": "draft", "depends": ["stage1"]},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rerun-from")
    a = ap.parse_args()
    label = a.label or Path(a.source).stem
    out = filing.run_dir(TOOL, a.brand, label)
    chain = Chain(TOOL, a.brand, label, out, HERE.parent / "prompts", STEPS,
                  assignment={"source": a.source}, dry=a.dry_run, rerun_from=a.rerun_from)
    record = chain.run("stage1", source=Path(a.source).read_text())
    draft = chain.run("stage2", record=record)
    if not a.dry_run:
        Q.hold("copy", Q.unfilled_check(draft), out)
    print(f"done -> {out}  ({chain.calls} model call(s))")


if __name__ == "__main__":
    main()
