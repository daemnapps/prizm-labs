#!/usr/bin/env python3
"""SI-121 (teardown stops reaching), part 1: the brief register asks naming
to write a brief alias through naming's public `add_alias` — it does not
write brief-aliases.json itself or touch naming's private `_ALIASES` cache.

    python3 tests/test_no_reach.py

Reads source text only. No key, no network, nothing written.
"""
import ast
import re
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parent.parent
BRIEFS = LANE / "tools" / "briefs.py"


class BriefsDoesNotReachIntoNaming(unittest.TestCase):
    def setUp(self):
        self.src = BRIEFS.read_text()
        self.tree = ast.parse(self.src)

    def test_no_private_alias_cache(self):
        self.assertNotIn("_ALIASES", self.src)

    def test_no_path_to_the_alias_file(self):
        # the file may be NAMED in prose; it is never built as a path here
        self.assertIsNone(re.search(r'/\s*["\']brief-aliases\.json["\']', self.src))
        self.assertIsNone(re.search(r'["\']components/naming/brief-aliases\.json["\']', self.src))

    def test_no_write_to_the_alias_file(self):
        self.assertIsNone(re.search(r'ALIASES\s*\.\s*(write_text|write_bytes|open)\b', self.src))
        for line in self.src.splitlines():
            if "brief-aliases" in line:
                self.assertIsNone(re.search(r'write_text|write_bytes|open\(|json\.dump\(', line), line)

    def test_add_alias_goes_through_naming(self):
        fn = next((n for n in ast.walk(self.tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "add_alias"), None)
        self.assertIsNotNone(fn, "briefs.py has no add_alias")
        calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call)]
        self.assertTrue(any(isinstance(c.func, ast.Attribute) and c.func.attr == "add_alias"
                            and isinstance(c.func.value, ast.Name) and c.func.value.id == "N"
                            for c in calls), "add_alias does not call names.add_alias")
        writes = [c for c in calls if isinstance(c.func, ast.Attribute)
                  and c.func.attr in ("write_text", "write_bytes", "open", "dump")]
        self.assertEqual(writes, [], "add_alias writes a file itself")


if __name__ == "__main__":
    unittest.main()
