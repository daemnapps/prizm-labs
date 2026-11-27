#!/usr/bin/python3
"""mini-compare: what a mini run of a component would get, against what is on
this machine. Read-only; prints a report; writes nothing; never reaches the mini.

    python3 .claude/skills/mini-compare/compare.py [component ...] [--all] [--full]

The logic lives in components/run-kit/mini_compare.py since LD-41 (mini-compare
false REDs), so makers can build on it; this file only hands over to it.
Python 3.9-safe on purpose: it runs under /usr/bin/python3 like the mini.
"""

import subprocess
import sys
from pathlib import Path

root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True).stdout.strip()
if not root:
    sys.exit("mini-compare: not inside the ai-workspace checkout")
sys.path.insert(0, str(Path(root) / "components" / "run-kit"))

import mini_compare  # noqa: E402

sys.exit(mini_compare.main(sys.argv[1:]))
