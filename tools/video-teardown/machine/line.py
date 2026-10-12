#!/usr/bin/env python3
"""
line.py — the two production lines, and the one thing they share.

    python3 machine/line.py teardown <video> --brand brand-b
    python3 machine/line.py creator  --label <run> --brand brand-b --creator <handle>
    python3 machine/line.py ai       --label <run> --brand brand-b --product widget

**Reading a swiped video is one job. What you do with it is two.**

Tearing a source down — what is on screen, who it is for, and the reusable
machine underneath — does not care who performs the result. Everything after
that does, and the two jobs have almost nothing in common: one ends with a
person holding a phone in their own bathroom, the other with nobody on set at
all.

Ruled by the owner 2026-09-11, after a run where "the same workflows are
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
import workdir  # noqa: E402  — the working folder (SI-56)

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
            # The run names its own copy (run.py open_run stores `source`,
            # e.g. source.mov); only an older run without it is guessed at,
            # in the order run.py would have written it (SI-161 (teardown
            # runs honest)) — it used to look for source.mp4 alone.
            import json
            rd = workdir.run_dir(label)
            named = None
            try:
                named = json.loads((rd / "run.json").read_text()).get("source")
            except Exception:
                named = None
            cands = ([rd / Path(str(named)).name] if named else []) + [
                rd / n for n in ("source.mp4", "source.mov", "source.m4v")]
            src = next((c for c in cands if c.is_file()), None)
            if src is not None:
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
            run_dir = workdir.run_dir(label)
            # Found, not assumed. This was Path(os.environ.get("AI_WORKSPACE") or ".").resolve()
            # pointing at the team notes/video-production — a home that only exists on
            # one Mac, naming a folder renamed to ai-video-production on
            # 2026-08-31, which then left lab entirely for
            # tools/video-production on 2026-09-22. Both old homes are gone,
            # so the search found nothing and the next-steps list silently
            # stopped printing. The new home is searched for first, the old one
            # kept behind it for a checkout that has not landed the move yet.
            vp = next((d / rel for d in Path(__file__).resolve().parents
                       for rel in (Path("components") / "video-production" / "machine",
                                   Path("lab") / "damon" / "ai-video-production" / "machine")
                       if (d / rel).is_dir()), None)
            if vp is None:
                print("\n▸ the AI video machine is not in this checkout — "
                      "skipping the next-steps list.\n")
                return code
            print("\n▸ next, in this order — the order is the point:\n")
            print(f"  1. ASK THE LIBRARY FIRST. Nothing is generated until this has run.\n"
                  f"       python3 {vp/'footage.py'} {run_dir}\n")
            print(f"  2. Generate only what it could not cover.\n")
            print(f"  3. Judge every plate before anyone sees it "
                  f"({vp.parent / 'PLATE-CHECK.md'}).\n")
            print(f"  4. The board:\n"
                  f"       python3 {vp/'storyboard.py'} {run_dir}\n")
            print(f"  5. Assemble:\n"
                  f"       python3 {vp/'assemble.py'} {run_dir}\n")
    sys.exit(code)


if __name__ == "__main__":
    main()
