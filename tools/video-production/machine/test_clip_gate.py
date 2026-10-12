"""The clip gate — each check is a fault from the Grandma TV-shopping clips (2026-10-09). No network,
no model: the text reader is faked, runs live in a temp folder."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import clip_gate as g
import omni_clips as oc

SPOTS = ("64-year-old woman, silver bob, blue-grey eyes; flat brown age spots on her FACE: a cluster across "
         "both temples (the right side of the picture when she faces the lens); freckling on her arms")


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "run"
        (self.run / "media").mkdir(parents=True)
        (self.run / "clips").mkdir()
        td = Path(self.tmp.name) / "teardown"
        (td / "framemap" / "shots").mkdir(parents=True)
        (td / "framemap" / "shots" / "K05.mp4").write_bytes(b"x")
        (td / "framemap" / "framemap.json").write_text(json.dumps({"shots": [{"map": "screen reads LIVE MASCARA DEMO"}]}))
        (self.run / "storyboard.json").write_text(json.dumps({"teardown": str(td)}))
        for s in ("S2", "S8"):
            Image.new("RGB", (8, 12), "white").save(self.run / "media" / f"{s}-F1.png")
        (self.run / "plan.json").write_text(json.dumps({"scenes": [
            {"id": "S2", "who": "NOVA", "say": "look at that scrub, live demo",
             "frames": [{"subject": "NOVA scrubs her cheek, the dark spots visible"}]},
            {"id": "S8", "who": "NOVA", "say": "look at her now",
             "frames": [{"subject": "NOVA, weeks into the routine", "refs": ["the face even where the dark spots were (no dark spots)"]}]},
        ]}))
        self.calls = [
            {"id": "G02-C1", "section_id": "G02", "start_frame": "S2-F1", "people": ["NOVA"],
             "refs": [{"clip": "K05.mp4"}], "prompt": f"keep. NOVA: {SPOTS}.", "params": {"prompt": f"keep. NOVA: {SPOTS}."}},
            {"id": "G08-C1", "section_id": "G08", "start_frame": "S8-F1", "people": ["NOVA"],
             "prompt": "keep. NOVA: even.", "params": {"prompt": "keep. NOVA: even."}},
        ]
        self.write_plan()
        self.clean = lambda p: ["LIVE DEMO"]

    def tearDown(self):
        self.tmp.cleanup()

    def write_plan(self):
        (self.run / "clips" / "plan.json").write_text(json.dumps({"route": "omni", "calls": self.calls}))

    def reds(self, cid, read=None):
        res = g.check(self.run, read_text=read or self.clean)
        return next(r for r in res["calls"] if r["id"] == cid)["red"]

    def approve(self):
        g.approve(self.run, "test")

    def test_unapproved_then_green(self):
        self.assertTrue(any(x.startswith("APPROVED") for x in self.reds("G08-C1")))
        self.approve()
        self.assertEqual(self.reds("G08-C1"), [])

    def test_a_changed_picture_needs_a_new_look(self):
        self.approve()
        Image.new("RGB", (8, 12), "black").save(self.run / "media" / "S8-F1.png")
        r = self.reds("G08-C1")
        self.assertTrue(any("changed after" in x for x in r))
        self.assertTrue(any(x.startswith("FACES") for x in r), "the person's lineup re-opens too")

    def test_shown_is_sent(self):
        self.approve()
        self.calls[1]["prompt"] = "keep. a fix written into the shown copy only"
        self.write_plan()
        self.assertTrue(any(x.startswith("SENT") for x in self.reds("G08-C1")))

    def test_a_moved_swipe_folder_is_held(self):
        self.approve()
        (self.run / "storyboard.json").write_text(json.dumps({"teardown": "/nowhere/old-teardown"}))
        self.assertTrue(any(x.startswith("PATHS") for x in self.reds("G02-C1")))

    def test_swipe_words_on_our_picture(self):
        self.approve()
        r = self.reds("G02-C1", read=lambda p: ["LIVE MASCARA DEMO"])
        self.assertTrue(any(x.startswith("SWIPE WORDS") and "mascara" in x for x in r))
        self.assertFalse(any(x.startswith("SWIPE WORDS") for x in self.reds("G02-C1")), "our own words pass")

    def test_after_scene_never_describes_spots(self):
        self.approve()
        self.calls[1]["prompt"] = self.calls[1]["params"]["prompt"] = f"keep. NOVA: {SPOTS}."
        self.write_plan()
        self.assertTrue(any(x.startswith("SKIN") for x in self.reds("G08-C1")))
        self.assertFalse(any(x.startswith("SKIN") for x in self.reds("G02-C1")), "a before scene keeps its spots")

    def test_planner_drops_spots_in_an_after_scene(self):
        scenes = json.loads((self.run / "plan.json").read_text())["scenes"]
        self.assertTrue(oc.scene_even(scenes[1]))
        self.assertFalse(oc.scene_even(scenes[0]))
        said = oc.identity_for(SPOTS, True, {"identity_even": "{poss} face is even now, no dark spots."}, "her")
        self.assertNotIn("age spots", said)
        self.assertIn("her face is even now", said)
        self.assertEqual(oc.identity_for(SPOTS, False, {}), SPOTS)

    def test_a_refused_request_is_not_sent_again_unchanged(self):
        self.approve()
        g.coverage(self.run, {"G08-C1": "refused by the model: Could not generate a video"})
        self.assertTrue(any(x.startswith("REFUSED") for x in self.reds("G08-C1")))
        self.calls[1]["prompt"] = self.calls[1]["params"]["prompt"] = "keep. NOVA: even, said another way."
        self.write_plan()
        self.assertFalse(any(x.startswith("REFUSED") for x in self.reds("G08-C1")))

    def test_ready_holds_until_green_and_current(self):
        self.assertTrue(g.ready(self.run, self.calls), "no gate run yet")
        self.approve()
        g.check(self.run, read_text=self.clean)
        self.assertEqual(g.ready(self.run, self.calls), [])
        self.calls[1]["params"]["prompt"] = self.calls[1]["prompt"] = "keep. changed after the gate"
        self.write_plan()
        self.assertTrue(g.ready(self.run, self.calls))

    def test_missing_clip_is_incomplete_and_remake_really_remakes(self):
        (self.run / "clips" / "G02-C1.mp4").write_bytes(b"old")
        (self.run / "clips" / "omni-ledger.json").write_text(json.dumps({"G02-C1": {"status": "done"}}))
        cov = g.coverage(self.run)
        self.assertFalse(cov["complete"])
        self.assertEqual([m["id"] for m in cov["missing"]], ["G08-C1"])
        moved = g.remake(self.run, ["G02-C1"])
        self.assertEqual(moved, ["clips/G02-C1.mp4"])
        self.assertFalse((self.run / "clips" / "G02-C1.mp4").exists())
        self.assertTrue(list((self.run / "clips" / "versions").rglob("G02-C1.mp4")), "moved aside, never deleted")
        self.assertEqual(json.loads((self.run / "clips" / "omni-ledger.json").read_text())["G02-C1"]["status"], "remake")


if __name__ == "__main__":
    unittest.main()
