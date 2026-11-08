#!/usr/bin/env python3
"""The model judge can be switched off (models.json judge.on: false, 2026-11-08): no model call is made, the free
measured checks still run, and the picture is not marked below criteria for want of a judge.

    python3 tools/image-production/tests/test_judge_off.py

Stdlib `unittest`, Python 3.9. No network, no model, no key.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
from image_production import judge as J            # noqa: E402

REQ = {"_aspect": "9:16", "_gen_aspect": "9:16"}


class JudgeOff(unittest.TestCase):
    def test_off_makes_no_model_call_and_passes(self):
        called = []
        with mock.patch.object(J, "measured", return_value=[]), \
             mock.patch.object(J, "tests_for", return_value=["a test"]), \
             mock.patch.object(J, "seen", side_effect=lambda *a, **k: called.append(1) or (["x"], "")):
            v = J.verdict("pic.png", REQ, {}, entry={"on": False, "vendor_model": "stub"})
        self.assertEqual(called, [])
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(v["judge_model"], "off")

    def test_off_still_fails_a_wrong_frame(self):
        with mock.patch.object(J, "measured", return_value=["wrong frame"]), \
             mock.patch.object(J, "tests_for", return_value=[]):
            v = J.verdict("pic.png", REQ, {}, entry={"on": False})
        self.assertEqual(v["verdict"], "reject")

    def test_on_by_default_calls_the_model(self):
        called = []
        with mock.patch.object(J, "measured", return_value=[]), \
             mock.patch.object(J, "tests_for", return_value=["a test"]), \
             mock.patch.object(J, "seen", side_effect=lambda *a, **k: called.append(1) or ([], "")):
            J.verdict("pic.png", REQ, {}, entry={"vendor_model": "stub"})
        self.assertEqual(called, [1])


if __name__ == "__main__":
    unittest.main()
