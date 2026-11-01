#!/usr/bin/env python3
"""K2 (brands write wall): the guard every email-production writer passes its
write path through refuses the workspace's brands/ — and only that.

    python3 test_k2_brand_guard.py

No network, no model. The workspace is a temp folder (AI_WORKSPACE, set
before paths.py is imported). SI-21 (email facts proposals), 2026-10-07.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(tempfile.mkdtemp(prefix="email-production-k2-guard-")) / "ws"
(WS / "brands" / "x" / "email-sms").mkdir(parents=True)
(WS / "runs").mkdir()
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

sys.path.insert(0, str(HERE))
from paths import refuse_brand_write  # noqa: E402


class Refused(unittest.TestCase):
    def assertRefused(self, path, root=None):
        with self.assertRaises(SystemExit) as cm:
            refuse_brand_write(path, root)
        self.assertIn("REFUSED (K2 brands write wall)", str(cm.exception))
        self.assertIn("write a proposal under runs/ instead", str(cm.exception))

    def test_a_brand_file(self):
        self.assertRefused(WS / "brands" / "x" / "email-sms" / "ledger.json")

    def test_brands_itself(self):
        self.assertRefused(WS / "brands")

    def test_dot_dot_cannot_walk_around_it(self):
        self.assertRefused(str(WS) + "/runs/../brands/x/a")

    def test_a_symlink_into_brands(self):
        link = WS / "runs" / "into-brands"
        if not link.exists():
            link.symlink_to(WS / "brands", target_is_directory=True)
        self.assertRefused(link / "x" / "a")

    def test_an_explicit_root(self):
        other = Path(tempfile.mkdtemp(prefix="email-production-k2-root-"))
        self.assertRefused(other / "brands" / "y" / "a.md", root=other)


class Allowed(unittest.TestCase):
    def test_a_proposal_run(self):
        p = WS / "runs" / "email-production" / "x" / "facts-2026-10-07" / "email-sms" / "ledger.json"
        self.assertEqual(refuse_brand_write(p), p.resolve())

    def test_a_folder_merely_named_brands(self):
        # pull/derive.py writes its derived notes inside the component
        p = HERE / "pull" / "brands" / "x-derived.md"
        self.assertEqual(refuse_brand_write(p), p.resolve())
        q = WS / "runs" / "email-production" / "brands" / "a.md"
        self.assertEqual(refuse_brand_write(q), q.resolve())

    def test_no_side_effects(self):
        p = WS / "runs" / "email-production" / "x" / "never-made" / "a.md"
        refuse_brand_write(p)
        self.assertFalse(p.parent.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
