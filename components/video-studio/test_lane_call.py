#!/usr/bin/env python3
"""How an ad is made is the chain's call; the Studio shows it and never assumes a lane of its own (2026-11-18).
Until then Produce and the production seed assumed "ai" while the next-step tools assumed "real" for the same
production with no lane on it.

    python3 components/video-studio/test_lane_call.py
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import video_studio as V  # noqa: E402
import seed_from_brief as S  # noqa: E402


class TheStudioAsksTheChain(unittest.TestCase):
    def test_every_reader_of_a_production_gets_one_answer(self):
        self.assertEqual(V.lane_of({})["lane"], "real")
        self.assertEqual(V.lane_of({"lane": None})["lane"], "real")
        self.assertEqual(V.lane_of({"lane": "ai"})["lane"], "ai")
        self.assertEqual(V.lane_of({"lane": "mix", "lane_why": "x", "lane_by": "y"}), {"lane": "mix", "why": "x", "by": "y"})

    def test_no_lane_is_assumed_anywhere_in_the_studio(self):
        """The two spellings of the old disagreement are gone from the Studio's code and its page."""
        for name in ("video_studio.py", "seed_from_brief.py", "studio.html"):
            text = (HERE / name).read_text()
            self.assertIsNone(re.search(r"""\.get\(["']lane["']\)\s*or\s*["'](?:ai|real|mix)["']""", text), name)
            self.assertIsNone(re.search(r"""lane\s*\|\|\s*['"]ai['"]""", text), name)
        self.assertIn('def handoff_start(idea, lane=None)', (HERE / "video_studio.py").read_text())
        self.assertIn("def main(idea, picked=None, lane=None", (HERE / "seed_from_brief.py").read_text())

    def test_the_rule_is_the_chains_own_file(self):
        self.assertEqual(Path(V._lane().__file__).name, "lane.py")
        self.assertEqual(Path(V._lane().__file__).parent.parent.name, "video-production")

    def test_the_picked_lanes_the_studio_accepts_are_the_chains_lanes(self):
        self.assertEqual(set(V._lane().lanes()), {"ai", "mix", "real", "creator"})


class TheSeedRecordsTheCall(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="studio_lane_")).resolve()
        self.work = self.tmp / "ws" / "runs" / "video-teardown" / "_work"
        (self.work / "run-1" / "stages").mkdir(parents=True)
        p = mock.patch.object(S, "WORK", self.work)
        p.start()
        self.addCleanup(p.stop)

    def writing(self, route="ai", footage=None, style=None):
        (self.work / "run-1" / "run.json").write_text(json.dumps({"production_route": route, "format_id": "narrator-montage",
                                                                   "style_id": style}))
        if footage is not None:
            (self.work / "run-1" / "stages" / "storyboard-footage.json").write_text(
                json.dumps({"scenes": {k: {"plan": v} for k, v in footage.items()}}))

    def test_nobody_picked_so_the_chain_decides_with_its_reason(self):
        self.writing(footage={"S1": "cut", "S2": "generate"})
        got = S.lane_call("run-1")
        self.assertEqual(got["lane"], "mix")
        self.assertIn("passed 1 of 2", got["why"])
        self.assertTrue(got["by"].startswith("the chain"))

    def test_a_persons_pick_is_recorded_as_theirs(self):
        self.writing(footage={"S1": "generate"})
        got = S.lane_call("run-1", "real")
        self.assertEqual((got["lane"], got["by"]), ("real", "a person at Produce"))

    def test_a_call_the_studio_already_asked_for_is_kept_word_for_word(self):
        self.writing()
        got = S.lane_call("run-1", "mix", "the footage decision passed 3 of 9 shot(s)", "the chain: format, route and the footage decision")
        self.assertEqual(got, {"lane": "mix", "why": "the footage decision passed 3 of 9 shot(s)",
                               "by": "the chain: format, route and the footage decision"})

    def test_the_first_trail_row_is_the_production_decision(self):
        rows = S.trail_rows("how the ad is made", "mix", "the footage decision passed 1 of 2 shot(s)", "the chain")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["stage"], rows[0]["decision"], rows[0]["choice"]), ("production", "how the ad is made", "mix"))
        self.assertEqual(rows[0]["by"], "the chain")


if __name__ == "__main__":
    unittest.main()
