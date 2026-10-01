#!/usr/bin/env python3
"""
line.py — the two production lines, and the one thing they share.

    python3 machine/line.py teardown <video> --brand <brand>
    python3 machine/line.py creator  --label <run> --brand <brand> --creator <handle>
    python3 machine/line.py ai       --label <run> --brand <brand> --product flex

**Reading a swiped video is one job. What you do with it is two.**

Tearing a source down — what is on screen, who it is for, and the reusable
machine underneath — does not care who performs the result. Everything after
that does, and the two jobs have almost nothing in common: one ends with a
person holding a phone in their own bathroom, the other with nobody on set at
all.

Ruled by Damon 2026-09-11, after a run where "the same workflows are
activating for both". Until then it was one chain with a `--route` flag, and
the flag was a noun the stages repeated back rather than a fork they obeyed.
A brief written for a generator went out reading "film this"; a stage that
writes the page a creator reads ran on a route with no creator.

```
                    ┌─ TEARDOWN ─┐   swipe in, spec out. Route-free.
                    │  0 1 1b 2  │   Shared, because it is the same work.
                    └─────┬──────┘
              ┌───────────┴───────────┐
      ┌───────▼────────┐     ┌────────▼────────┐
      │ CREATOR        │     │ AI              │
      │ inject → loop  │     │ inject → loop   │
      │ → brief        │     │ → scenes        │
      │ → frames       │     │ → storyboard    │
      │ → one-sheet    │     │ → generate      │
      │ → Google Doc   │     │ → Premiere      │
      └────────────────┘     └─────────────────┘
         a person films          nobody is on set
```

The front half stays shared on purpose. Two teardowns of the same source would
drift, and then two lines would be arguing about what the video actually was.

This is a door, not a new machine: each line calls the same stages with the
right range and route, so nothing another brand's runs depend on moves.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LINES = {
    # name: (stage range, route, what it ends with)
    "teardown": (("0", "2"), None,
                 "a teardown record and a reusable spec — no brand in it yet"),
    "creator": (("3", None), "creator",
                "a one-sheet a creator can film from, and the Doc it lives in"),
    "ai": (("3", None), "ai",
           "a scene list, a storyboard, and clips — nobody on set"),
}


def run(args: list[str]) -> int:
    return subprocess.call([sys.executable, str(HERE / "run.py")] + args)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("lines:")
        for name, (rng, route, ends) in LINES.items():
            print(f"  {name:9} stages {rng[0]}{'→' + rng[1] if rng[1] else '→end'}"
                  f"{'  route ' + route if route else '':16}  ends with {ends}")
        sys.exit(0)

    line = sys.argv[1]
    if line not in LINES:
        sys.exit(f"no line called '{line}'. Have: {', '.join(LINES)}")
    (start, stop), route, ends = LINES[line]

    rest = sys.argv[2:]
    passthru = list(rest)
    if "--from" not in rest:
        passthru += ["--from", start]
    if stop and "--to" not in rest:
        passthru += ["--to", stop]
    if route and "--route" not in rest:
        passthru += ["--route", route]

    # A line that starts mid-chain needs the run it is continuing. run.py wants
    # a video path even then, so resolve it from the label rather than making
    # the caller type a path into a folder they did not create.
    if line != "teardown" and not any(
            a.endswith((".mp4", ".mov", ".m4v")) for a in passthru):
        label = None
        for i, a in enumerate(passthru):
            if a == "--label" and i + 1 < len(passthru):
                label = passthru[i + 1]
        if label:
            src = HERE / "runs" / label / "source.mp4"
            if src.exists():
                passthru.insert(0, str(src))
            else:
                sys.exit(f"no run called '{label}' — tear one down first:\n"
                         f"    python3 machine/line.py teardown <video> --brand <brand>")

    print(f"▸ {line} line — ends with {ends}\n")
    code = run(passthru)

    if code == 0 and line == "ai":
        label = next((passthru[i + 1] for i, a in enumerate(passthru)
                      if a == "--label"), None)
        if label:
            run_dir = HERE / "runs" / label
            vp = Path.home() / "Projects/ai-workspace/video-production/machine"
            print("\n▸ next, in this order — the order is the point:\n")
            print(f"  1. ASK THE LIBRARY FIRST. Nothing is generated until this has run.\n"
                  f"       python3 {vp/'footage.py'} {run_dir}\n")
            print(f"  2. Generate only what it could not cover.\n")
            print(f"  3. Judge every plate before anyone sees it "
                  f"(video-production/PLATE-CHECK.md).\n")
            print(f"  4. The board:\n"
                  f"       python3 {vp/'storyboard.py'} {run_dir}\n")
            print(f"  5. Assemble:\n"
                  f"       python3 {vp/'assemble.py'} {run_dir}\n")
    sys.exit(code)


if __name__ == "__main__":
    main()
