#!/usr/bin/env python3
"""An AI-lane production never searches our footage and never waits on clip picks: the shots stage records every
shot as made with AI, and next_due moves past "shots" (owner, 20 Nov 2026).

    python3 components/video-studio/test_ai_lane_shots.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import video_studio as VS  # noqa: E402


class AnAiLaneProduction(unittest.TestCase):
    def setUp(self):
        self.briefs = Path(tempfile.mkdtemp(prefix="studio_ai_lane_")).resolve()
        p = mock.patch.object(VS, "BRIEFS", str(self.briefs))
        p.start()
        self.addCleanup(p.stop)
        self.B = self.briefs / "p1"
        (self.B / "scenes" / "S1").mkdir(parents=True)
        (self.B / "brief.json").write_text(json.dumps({
            "order": ["S1"], "picks": {"S1": "take-1"}, "lane": "ai", "lane_why": "test", "lane_by": "test",
            "shot_fill": {"brand": "acme"}}))
        (self.B / "scenes" / "S1" / "take-1.json").write_text(json.dumps({"steps": []}))
        self.rows = [{"id": "S1.1", "scene": "S1"}, {"id": "S1.2", "scene": "S1"}]

    def run_shots(self):
        calls = []

        def fake_tool(job, sid, args, timeout=3600):
            calls.append(args[0])
            if args[0] == "swipe_shots.py":
                (self.B / "shot-list.json").write_text(json.dumps({"shots": self.rows}))
            return True, ""
        job = {"id": "j", "n": "p1", "stage": "shots", "name": VS.NEXT_STAGES["shots"][0],
               "steps": [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in VS.NEXT_STAGES["shots"][1]]}
        with mock.patch.object(VS, "_tool", fake_tool), mock.patch.object(VS, "song_due", lambda n: None):
            VS._run_next(job)
            due = VS.next_due("p1")
        return calls, job, due

    def test_the_shot_list_is_made_and_no_library_search_runs(self):
        calls, job, due = self.run_shots()
        self.assertEqual(calls, ["swipe_shots.py"])          # no shot_fill.py, no said_shots.py
        self.assertFalse((self.B / "picks.json").exists())    # nothing placed from the library
        fill = json.loads((self.B / "shot-fill.json").read_text())
        self.assertEqual({r["status"] for r in fill["shots"]}, {"AI"})
        self.assertTrue(all(st["state"] == "done" for st in job["steps"]))

    def test_next_due_moves_past_shots_with_no_picks(self):
        _, _, due = self.run_shots()
        self.assertNotEqual(due, "shots")
        self.assertEqual(due, "cut")

    def test_the_label_says_the_ai_shots_are_planned(self):
        with mock.patch.object(VS, "song_due", lambda n: None):
            self.assertEqual(VS.next_due("p1"), "shots")
            self.assertEqual(VS.next_state("p1")["label"], "Plan the AI shots")


if __name__ == "__main__":
    unittest.main()
