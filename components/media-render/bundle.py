#!/usr/bin/env python3
"""Emit the one <script> block a viewer template inlines. Card RV-5.

A viewer template cannot fetch a sibling asset — the viewer route serves
exactly one html file per request, the constraint that already forced
`_session-bootstrap.js`, `_report.js` and `_fb-panel.js` to travel inlined. So
a page that renders media inlines the ENGINE followed by the SHIM, in that
order, and this script is the one command that produces the pair:

    python3 components/media-render/bundle.py            # to stdout
    python3 components/media-render/bundle.py --out X.js # to a file

WHY THERE IS NO STORED COPY OF THE ENGINE ANYWHERE. The obvious alternative —
paste the engine into `_media.js` and prove the copy byte-identical in a test
— is the `_report.js` pattern, and it is right when the copy lands in a
GENERATED file. Here both files are SOURCE, and a second source copy of 260
lines is exactly the defect this card was carded to end: it goes stale the
first time someone edits the wrong one, and the test that catches it can only
say so after the fact. Concatenating at inline time cannot go stale at all.

Stdlib only. Reads two files, writes at most one, emits no record.
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "components/media-render/media-render.js"
SHIM = REPO / "platform/views/viewers/_templates/_media.js"

HEADER = (
    "/* media-render — inlined by components/media-render/bundle.py.\n"
    " * The engine is components/media-render/media-render.js; the page-side\n"
    " * shim is platform/views/viewers/_templates/_media.js. Neither is edited\n"
    " * here — regenerate this block instead. */\n"
)


def bundle():
    """The engine, then the shim. The order is load-bearing: the shim reads
    `globalThis.MediaRender`, which the engine installs."""
    return HEADER + ENGINE.read_text(encoding="utf-8") + "\n" + SHIM.read_text(encoding="utf-8")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="write the block here instead of stdout")
    args = ap.parse_args(argv)
    for f in (ENGINE, SHIM):
        if not f.exists():
            print(f"FATAL: {f.relative_to(REPO)} is missing", file=sys.stderr)
            return 2
    text = bundle()
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {len(text)} chars to {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
