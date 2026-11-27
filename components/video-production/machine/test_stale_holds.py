#!/usr/bin/env python3
"""A review hold counts only for the picture it reviewed (2026-11-21, brief-0380: a review of generated stills, since set
aside for the kept 3D prints, took back the gate's approval of the prints). Temp folders only; nothing is called.

    python3 components/video-production/machine/test_stale_holds.py
"""
import importlib.util as u
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class StaleHolds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sp = u.spec_from_file_location("vm_test_run_v2_stale", HERE / "run_v2.py")
        cls.V2 = u.module_from_spec(sp)
        sp.loader.exec_module(cls.V2)

    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        (self.run / "clips").mkdir(); (self.run / "media" / "versions").mkdir(parents=True)
        (self.run / "media" / "versions" / "S1-F1-v2-v1.png").write_bytes(b"generated")
        (self.run / "clips" / "gate-approved.json").write_text(json.dumps({"S1-F1": {"by": "the system"}}))
        self.row = {"id": "S1-F1", "verdict": "FLAGGED",
                    "rounds": [{"check": 1, "file": str(self.run / "media" / "versions" / "S1-F1-v2-v1.png")}]}

    def test_a_review_of_a_picture_since_replaced_holds_nothing(self):
        (self.run / "media" / "S1-F1.png").write_bytes(b"the-kept-print")
        self.assertEqual(self.V2._hold_flagged(self.run, [self.row]), [])
        self.assertIn("S1-F1", json.loads((self.run / "clips" / "gate-approved.json").read_text()))

    def test_a_review_of_the_picture_as_it_is_still_holds_it(self):
        (self.run / "media" / "S1-F1.png").write_bytes(b"generated")
        self.assertEqual(self.V2._hold_flagged(self.run, [self.row]), ["S1-F1"])


if __name__ == "__main__":
    unittest.main()
