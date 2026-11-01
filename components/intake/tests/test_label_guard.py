#!/usr/bin/env python3
"""intake's label guard (SI-51, intake#1) — stdlib unittest, no network, no model.

    python3 components/intake/tests/test_label_guard.py

A --label or --brand that is not one plain folder name, or that resolves
outside runs/intake/<brand>/, is refused before anything is read or written.
Runs against a TINY FAKE WORKSPACE in a temp folder reached through
`AI_WORKSPACE`; the real `runs/` and `brands/` are never touched.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.append(str(TOOLS))                             # appended, never inserted at 0

import paths as P                                           # noqa: E402
import run as R                                             # noqa: E402


class LabelGuard(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name) / "ws"
        (self.ws / "brands/alpha").mkdir(parents=True)      # alpha is a made-up brand
        (self.ws / "components").mkdir(parents=True)
        self._old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.ws)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._old
        self._tmp.cleanup()

    def test_escaping_label_is_refused(self):
        with self.assertRaises(ValueError) as cm:
            P.run_dir("alpha", "../../../brands/alpha/x", make=False)
        self.assertTrue(str(cm.exception).startswith("refused: label"), str(cm.exception))
        self.assertIn("runs/intake/", str(cm.exception))

    def test_unplain_names_are_refused(self):
        for label in ("", ".", "..", "a/b", "/abs/x", "a\\b"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                P.run_dir("alpha", label, make=False)
        for brand in ("../alpha", ""):
            with self.subTest(brand=brand), self.assertRaises(ValueError) as cm:
                P.run_dir(brand, "2026-10-07", make=False)
            self.assertTrue(str(cm.exception).startswith("refused: brand"), str(cm.exception))

    def test_plain_label_files_home(self):
        d = P.run_dir("alpha", "2026-10-07", make=True)
        self.assertEqual(d, self.ws / "runs/intake/alpha/2026-10-07")
        self.assertTrue(d.is_dir())

    def test_symlink_cannot_escape(self):
        home = self.ws / "runs/intake/alpha"
        home.mkdir(parents=True)
        os.symlink(self.ws / "brands/alpha", home / "sneak")
        with self.assertRaises(ValueError) as cm:
            P.run_dir("alpha", "sneak", make=False)
        self.assertIn("resolves outside", str(cm.exception))

    def test_run_exits_2_and_writes_nothing(self):
        before = sorted(p.relative_to(self.ws) for p in (self.ws / "brands/alpha").rglob("*"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = R.main(["--brand", "alpha", "--label", "../../../brands/alpha/x"])
        self.assertEqual(code, 2)
        self.assertIn("refused:", err.getvalue())
        self.assertFalse((self.ws / "brands/alpha/x").exists())
        after = sorted(p.relative_to(self.ws) for p in (self.ws / "brands/alpha").rglob("*"))
        self.assertEqual(after, before)
        self.assertEqual(before, [])                        # the fixture put nothing inside alpha


if __name__ == "__main__":
    unittest.main()
