#!/usr/bin/env python3
"""The pronoun gate: no generic gendered pronoun in anything we write.

    python3 components/marketing-doctrine/lint_prompts.py <file> [<file> ...]

A generic person in a prompt, a slice or a doctrine page is "the viewer", "the
avatar", "the speaker", "they". A gendered pronoun narrows an agnostic system
to one reader for no reason, so it is a defect, not a style note.

Two exemptions, both deliberate:
  * a fenced code block (``` or ~~~) — a quoted example is evidence, not our voice
  * anything inside double quotes on a line — real speech, quoted verbatim

Exit 0 = clean. Exit 1 = findings, one `file:line:col: word` per finding.
Exit 2 = nothing to check / a file could not be read.

Stdlib only, no dependency, runs from any machine's test suite.
"""

import argparse
import re
import sys
from pathlib import Path

PRONOUN = re.compile(r"\b(she|her|hers|herself|he|him|his|himself)\b", re.IGNORECASE)
FENCE = re.compile(r"^\s*(```|~~~)")
QUOTED = re.compile(r'"[^"\n]*"')


def findings_in_text(text):
    """-> [(lineno, col, word)] for one file's text."""
    out = []
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # blank out quoted speech, keeping columns honest
        masked = QUOTED.sub(lambda m: " " * len(m.group(0)), line)
        for m in PRONOUN.finditer(masked):
            out.append((n, m.start() + 1, m.group(0)))
    return out


def check(paths):
    """-> (findings_count, unreadable_count), printing every finding."""
    found = 0
    unreadable = 0
    for p in paths:
        path = Path(p)
        try:
            text = path.read_text(errors="replace")
        except (OSError, IsADirectoryError):
            print("%s: cannot read" % path, file=sys.stderr)
            unreadable += 1
            continue
        for lineno, col, word in findings_in_text(text):
            print("%s:%d:%d: gendered pronoun %r" % (path, lineno, col, word))
            found += 1
    return found, unreadable


def main(argv=None):
    ap = argparse.ArgumentParser(description="fail on generic gendered pronouns")
    ap.add_argument("files", nargs="*", help="files to check")
    args = ap.parse_args(argv)
    if not args.files:
        ap.print_usage(sys.stderr)
        return 2
    found, unreadable = check(args.files)
    if unreadable:
        return 2
    if found:
        print("%d finding(s)" % found, file=sys.stderr)
        return 1
    print("clean: %d file(s)" % len(args.files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
