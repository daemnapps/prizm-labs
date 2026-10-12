#!/usr/bin/env python3
"""SI-114 (chain-checks seams): the calendar reaches the shared checks by
importing them, not by testing the package's folder layout.

    python3 machine/test_quality_import.py

    1  with the package importable, `_quality()` returns the module
    2  with a temp WORKSPACE that lacks it (and nothing cached), it returns None

No network, no model, no brand.
"""
import calendar as _stdlib_calendar      # noqa: F401 — cached BEFORE machine/ joins the path,
import os                                # because this folder has a calendar.py of its own
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
CHECKOUT = next((d for d in MACHINE.parents if (d / ".git").exists()), None)
if CHECKOUT and not os.environ.get("AI_WORKSPACE"):
    os.environ["AI_WORKSPACE"] = str(CHECKOUT)     # a worktree must read ITSELF
sys.path.insert(0, str(MACHINE))

import gates as G                        # noqa: E402
import paths as P                        # noqa: E402

PKG = "marketing_chain_checks"


class QualityImport(unittest.TestCase):

    def test_the_package_importable_returns_the_module(self):
        Q = G._quality()
        self.assertIsNotNone(Q)
        self.assertEqual(Q.__name__, PKG)
        self.assertTrue(hasattr(Q, "hold"))
        self.assertTrue(hasattr(Q, "Held"))

    def test_a_workspace_without_it_returns_none(self):
        real = str(P.WORKSPACE / "components" / "quality-checks")
        with tempfile.TemporaryDirectory() as d:
            path = [p for p in sys.path if Path(p).name != "quality-checks" and p != real]
            mods = {k: v for k, v in sys.modules.items()
                    if k != PKG and not k.startswith(PKG + ".")}
            with unittest.mock.patch.object(P, "WORKSPACE", Path(d)), \
                    unittest.mock.patch.object(sys, "path", path), \
                    unittest.mock.patch.dict(sys.modules, mods, clear=True):
                self.assertIsNone(G._quality())
                self.assertEqual(sys.path[-1],                  # appended, never ahead
                                 str(Path(d) / "components" / "quality-checks"))


if __name__ == "__main__":
    unittest.main()
