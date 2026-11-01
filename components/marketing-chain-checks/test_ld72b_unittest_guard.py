#!/usr/bin/env python3
"""LD-72b (unittest guard): the viewer check skips Claude only when a TEST is the
program running, not whenever some library has loaded unittest (production on the
mini: vp-grandma-dbmik-dry-4 logged "not tried under unittest").

    /usr/bin/python3 components/marketing-chain-checks/test_ld72b_unittest_guard.py
No network, no real claude: shutil.which is faked to find nothing."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from marketing_chain_checks import viewer as V  # noqa: E402


class Guard(unittest.TestCase):
    def setUp(self):
        V._CLAUDE_OK[0] = None
        V.CLAUDE_WHY = ""

    def test_under_a_test_program_claude_is_not_tried(self):
        with mock.patch.object(sys, "argv", ["test_something.py"]):
            self.assertTrue(V._under_test())
            self.assertIsNone(V._claude_cli("hi", False))
        self.assertIn("unittest", V.claude_why())

    def test_production_program_with_unittest_loaded_still_tries_claude(self):
        # unittest IS in sys.modules here (this file imports it), as in the mini run
        with mock.patch.object(sys, "argv", ["run_v2.py"]), \
             mock.patch.dict(os.environ, {"QC_VIEWER_CLAUDE": "1"}), \
             mock.patch("shutil.which", return_value=None):
            self.assertFalse(V._under_test())
            self.assertIsNone(V._claude_cli("hi", False))
        self.assertNotIn("unittest", V.claude_why())

    def test_python_m_unittest_counts_as_a_test(self):
        with mock.patch.object(sys, "argv", ["/usr/lib/python3.9/unittest/__main__.py"]):
            self.assertTrue(V._under_test())

    def test_explicit_off_switch_still_wins(self):
        with mock.patch.object(sys, "argv", ["run_v2.py"]), \
             mock.patch.dict(os.environ, {"QC_VIEWER_CLAUDE": "0"}):
            self.assertIsNone(V._claude_cli("hi", False))
        self.assertIn("QC_VIEWER_CLAUDE=0", V.claude_why())


if __name__ == "__main__":
    unittest.main()
