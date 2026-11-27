#!/usr/bin/env python3
"""A zone the brand step marks "unchanged" keeps the swipe's own words on a word-free picture (2026-11-10: a 3D print
lost the swipe's 1-4 panel numbers). Stdlib unittest, Python 3.9, nothing spent."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("mi_preview_copy", Path(__file__).resolve().parent / "preview.py")
PV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PV)

TABLE = """| Zone | Position | Source copy | Our copy |
|---|---|---|---|
| Zone A — header banner | 0-10% top | PICK YOUR BALD ERA | PICK YOUR BUMP ERA |
| Zone B — panel 1 | 10-49.5% top | 1 | unchanged |
| Zone C — badge | 50% top | — | unchanged (red circle) |
"""


class UnchangedKeepsTheSwipesWords(unittest.TestCase):
    def test_unchanged_takes_the_source_copy(self):
        got = dict(PV._our_copy(TABLE))
        self.assertEqual(got["Zone A — header banner"], "PICK YOUR BUMP ERA")
        self.assertEqual(got["Zone B — panel 1"], "1")
        self.assertNotIn("Zone C — badge", got)      # no words in the swipe there: nothing to set


if __name__ == "__main__":
    unittest.main(verbosity=1)
