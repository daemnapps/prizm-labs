#!/usr/bin/env python3
"""The AI lane's clip sections (2026-11-21, brief-0380): a section whose clips were made from pictures since changed is
sent again, and the lane goes on through every section while each one's own clips are made. Temp folders; nothing
is called.

    python3 components/video-production/machine/test_lane_sections.py
"""
import importlib.util as u
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sp = u.spec_from_file_location("vm_test_ai_lane", HERE / "ai_lane.py")
AL = u.module_from_spec(sp)
sp.loader.exec_module(AL)


class Sections(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        (self.run / "clips").mkdir()
        (self.run / "clips" / "G01-C1.mp4").write_bytes(b"old")
        self.calls = [{"id": "G01-C1"}]

    def test_a_made_section_is_skipped_unless_a_clip_is_stale(self):
        self.assertFalse(AL.section_due(self.run, self.calls))
        self.assertTrue(AL.section_due(self.run, self.calls, stale={"G01-C1"}))
        self.assertTrue(AL.section_due(self.run, [{"id": "G05-C1"}]))

    def test_the_lane_goes_on_by_the_sections_own_clips(self):
        (self.run / "clips" / "ledger.json").write_text(json.dumps({"G01-C1": {"status": "done"}}))
        self.assertTrue(AL.section_made(self.run, self.calls))            # whatever the whole ad's count says
        (self.run / "clips" / "ledger.json").write_text(json.dumps({"G01-C1": {"status": "failed"}}))
        self.assertFalse(AL.section_made(self.run, self.calls))
        self.assertFalse(AL.section_made(self.run, [{"id": "G05-C1"}]))


    def test_a_clip_the_model_refused_is_a_gap_and_the_lane_goes_on(self):
        (self.run / "clips" / "ledger.json").write_text(json.dumps({
            "G01-C1": {"status": "done"}, "G01-C1-B": {"status": "failed", "error": "x.mp4: Seedance ended 'nsfw'"}}))
        calls = self.calls + [{"id": "G01-C1-B", "scenes": ["S5"], "section_id": "G01"}]
        self.assertTrue(AL.section_made(self.run, calls))
        gaps = json.loads((self.run / "clips" / "gaps.json").read_text())
        self.assertEqual(gaps["G01-C1-B"]["scenes"], ["S5"])

    def test_a_door_fault_still_stops(self):
        (self.run / "clips" / "ledger.json").write_text(json.dumps({
            "G01-C1": {"status": "done"}, "G01-C1-B": {"status": "failed", "error": "HTTP 520 upload error"}}))
        self.assertFalse(AL.section_made(self.run, self.calls + [{"id": "G01-C1-B"}]))


if __name__ == "__main__":
    unittest.main()
