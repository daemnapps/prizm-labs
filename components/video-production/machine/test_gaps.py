#!/usr/bin/env python3
"""A clip filed as a gap for the edit (clips/gaps.json: the model refused it) never holds the rest of the ad: the gate
leaves it out, coverage counts it as a gap, the lane never sends it again (2026-11-21, brief-0380). Nothing is called.

    python3 components/video-production/machine/test_gaps.py
"""
import importlib.util as u
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clip_gate as G  # noqa: E402

sp = u.spec_from_file_location("vm_test_ai_lane_gaps", HERE / "ai_lane.py")
AL = u.module_from_spec(sp)
sp.loader.exec_module(AL)


class Gaps(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        (self.run / "clips").mkdir()
        (self.run / "clips" / "plan.json").write_text(json.dumps({"calls": [{"id": "A"}, {"id": "B"}]}))
        (self.run / "clips" / "A.mp4").write_bytes(b"a")
        (self.run / "clips" / "gaps.json").write_text(json.dumps({"B": {"why": "Seedance ended 'nsfw'"}}))

    def test_a_gap_is_not_missing_from_coverage(self):
        res = G.coverage(self.run)
        self.assertTrue(res["complete"], res)
        self.assertEqual(res["gaps"], ["B"])

    def test_the_gate_never_asks_for_a_gap(self):
        (self.run / "clips" / "gate.json").write_text(json.dumps({"calls": [{"id": "A", "red": []}]}))
        self.assertNotIn("B: not checked by the gate", G.ready(self.run, [{"id": "A"}, {"id": "B"}]))

    def test_the_lane_never_sends_a_gap_again(self):
        self.assertFalse(AL.section_due(self.run, [{"id": "A"}, {"id": "B"}]))


if __name__ == "__main__":
    unittest.main()
