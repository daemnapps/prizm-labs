#!/usr/bin/env python3
"""A final check speaks only for the build it checked (email_lead, 2026-11-16).

brand_b-nov-23: a picture placed after the last check rebuilt the email, the card kept the older build's finding
(says "—"), and the Go held for nothing. check.py now records which email.html it checked (`final_check_of`), and the
Go re-runs the check when the card's is about another build. No network.

    python3 design/test_final_check_fresh.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check as FC  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="final-check-fresh-"))
os.environ["AI_WORKSPACE"] = str(TMP / "ws")
sys.path.insert(0, str(HERE.parent))
import approve_klaviyo as A  # noqa: E402


class Fresh(unittest.TestCase):
    def setUp(self):
        self.k = TMP / "run" / "klaviyo"
        self.k.mkdir(parents=True, exist_ok=True)
        (self.k / "email.html").write_text("<html>build two</html>")

    def card(self, **kw):
        c = dict({"label": "brand_b-nov-23", "final_check": [{"result": "ok", "detail": "x"}]}, **kw)
        (self.k / "card.json").write_text(json.dumps(c))
        return c

    def test_same_build_is_fresh(self):
        c = self.card(final_check_of=FC.html_sha(self.k / "email.html"))
        self.assertTrue(FC.is_fresh(c, self.k / "email.html"))

    def test_another_build_is_not(self):
        c = self.card(final_check_of=FC.html_sha(self.k / "card.json"))
        self.assertFalse(FC.is_fresh(c, self.k / "email.html"))

    def test_a_card_that_never_recorded_its_build_is_not(self):
        self.assertFalse(FC.is_fresh(self.card(), self.k / "email.html"))

    def test_the_go_reruns_a_stale_check(self):
        self.card(final_check=[{"result": "PROBLEM", "detail": 'says "—" (the brand\'s never list)'}])
        with mock.patch.object(A.subprocess, "run") as run:
            self.assertFalse(A._fresh_final_check(self.k))
        self.assertIn("check.py", " ".join(run.call_args[0][0]))

    def test_the_go_leaves_a_fresh_check_alone(self):
        self.card(final_check_of=FC.html_sha(self.k / "email.html"))
        with mock.patch.object(A.subprocess, "run") as run:
            self.assertTrue(A._fresh_final_check(self.k))
        run.assert_not_called()


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
