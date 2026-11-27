"""route_facts applies SHOT-ROUTES.md to a plan and makes the route act: SWAP scenes are not generated."""
import json
import tempfile
import unittest
from pathlib import Path

import route_facts as RF


def framemap(d: Path):
    (d / "framemap").mkdir()
    (d / "framemap" / "framemap.json").write_text(json.dumps({"shots": [
        {"id": "K01", "start": 0.0, "end": 6.0, "seconds": 6.0, "clip": "K01.mp4",
         "map": {"camera": {"move": "none"}, "moments": [{"does": "jumps off the stage"}, {"does": "flips and lands"}]}},
        {"id": "K02", "start": 6.0, "end": 9.0, "seconds": 3.0, "clip": "K02.mp4",
         "map": {"camera": {"move": "none"}, "moments": [{"does": "stands still"}]}},
    ]}))
    return d / "framemap"


class RouteFacts(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.fm = framemap(self.d)

    def plan(self):
        return {"scenes": [
            {"id": "S1", "kind": "motion", "source": "K01 0:00-0:05: he jumps off and flips", "happens": "jumps and flips"},
            {"id": "S2", "kind": "talking", "to_camera": True, "voice": "a line of ours", "source": "K02 0:06-0:09: talks"},
            {"id": "S3", "kind": "motion", "source": "K01 0:04-0:08: he lands and walks", "happens": "lands and walks"},
            {"id": "S4", "kind": "motion", "source_plan": "cut", "owned_file": "x.mp4", "source": "archive"},
            {"id": "S5", "kind": "card", "source": "none"},
        ]}

    def test_routes(self):
        p = self.plan()
        res = RF.route_plan(self.d, p, str(self.fm))
        got = {r["id"]: r["route"] for r in res["rows"]}
        self.assertEqual(got["S1"], "SWAP")            # moves, clean single shot
        self.assertEqual(got["S2"], "AI")              # talks to camera
        self.assertEqual(got["S3"], "AI")              # crosses the cut at 6 s
        self.assertEqual(got["S4"], "REAL")            # footage we own
        self.assertEqual(got["S5"], "AI")              # a card is a plate

    def test_swap_scene_is_not_generated_and_has_an_order(self):
        p = self.plan()
        res = RF.route_plan(self.d, p, str(self.fm))
        s1 = next(s for s in p["scenes"] if s["id"] == "S1")
        self.assertEqual(s1["source_plan"], "swap")
        self.assertEqual(len(res["swap_orders"]), 1)
        self.assertTrue(res["swap_orders"][0]["clip"].endswith("K01.mp4"))

    def test_no_framemap_means_no_swap(self):
        p = self.plan()
        res = RF.route_plan(self.d / "nowhere", p, None)
        self.assertNotIn("SWAP", {r["route"] for r in res["rows"]})


if __name__ == "__main__":
    unittest.main()
