#!/usr/bin/env python3
"""Tests for SI-119 (path-insert honesty): casting and image-edit APPEND to
sys.path and never jump ahead of it, and casting's filing keeps no `kit()`
that nothing calls.

    /usr/bin/python3 components/casting/tests/test_path_append.py

Stdlib `unittest`, 3.9-safe, offline. Reads source text; imports only
casting's own modules.
"""
import ast
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASTING = HERE.parent
COMPONENTS = CASTING.parent
SCANNED = (CASTING, COMPONENTS / "image-edit")

# Built from parts so this file does not match its own search.
INSERT_AT_0 = re.compile(r"sys\.path\.insert" + r"\(\s*0\s*,")


class NoInsertAtZero(unittest.TestCase):
    def test_no_module_inserts_at_0(self):
        hits = []
        for root in SCANNED:
            for py in sorted(root.rglob("*.py")):
                for n, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                    if INSERT_AT_0.search(line):
                        hits.append("%s:%d" % (py.relative_to(COMPONENTS), n))
        self.assertEqual(hits, [], "insert at 0 — append instead (rule 6)")


class KitIsUsedOrGone(unittest.TestCase):
    def test_filing_kit_absent_or_called_by_plan_run_dir(self):
        tree = ast.parse((CASTING / "casting" / "filing.py").read_text(encoding="utf-8"))
        defs = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
        self.assertIn("plan_run_dir", defs)
        if "kit" not in defs:
            return
        called = {c.func.id for c in ast.walk(defs["plan_run_dir"])
                  if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        self.assertIn("kit", called, "filing.kit() is defined but plan_run_dir never calls it")


class CastingStillImports(unittest.TestCase):
    """The kill condition: a changed module that no longer imports."""

    def test_changed_modules_import(self):
        if str(CASTING) not in sys.path:
            sys.path.append(str(CASTING))
        from casting import dryrun, filing, generate   # noqa: F401
        self.assertTrue(callable(filing.plan_run_dir))
        self.assertTrue(callable(generate.engine))


if __name__ == "__main__":
    unittest.main(verbosity=2)
