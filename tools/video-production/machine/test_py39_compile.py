#!/usr/bin/env python3
"""python3 machine/test_py39_compile.py — from any cwd. Stdlib unittest only.

Every .py under tools/video-production compiles under whichever
interpreter runs this file — the mini's /usr/bin/python3 is 3.9.6, where a
backslash inside an f-string expression is a SyntaxError (SI-104 (run.py 3.9
compile), video-production#30)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
COMPONENT = MACHINE.parent


def _sources():
    for root, dirs, files in os.walk(COMPONENT):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git"))
        for name in sorted(files):
            if name.endswith(".py"):
                yield Path(root) / name


class CompilesUnderThisInterpreter(unittest.TestCase):
    def test_every_py_compiles(self):
        failed = []
        count = 0
        for path in _sources():
            count += 1
            try:
                compile(path.read_bytes(), str(path), "exec")
            except SyntaxError as e:
                failed.append(f"{path.relative_to(COMPONENT)}:{e.lineno}: {e.msg}")
        self.assertGreater(count, 0, f"no .py found under {COMPONENT}")
        self.assertEqual(failed, [], f"does not compile under Python {sys.version.split()[0]}:\n" + "\n".join(failed))

    def test_run_py_keeps_the_placeholder_check(self):
        src = (MACHINE / "run.py").read_text(encoding="utf-8")
        self.assertIn("(SLOT|UNFILLED)", src)


if __name__ == "__main__":
    unittest.main()
