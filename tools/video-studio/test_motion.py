"""motion.py and take.py's motion input: python3 -m unittest test_motion (no MediaPipe or Blender needed)."""
import json
import tempfile
import unittest
from pathlib import Path

import motion as MO
import take as T


class Camera(unittest.TestCase):
    def test_push_pan_and_cut(self):
        steps = [[0, 0, 1, 0, 0]] + [[0.01, 0, 1.01, 0, 80]] * 15 + [[0, 0, 1, 0, -1]] + [[-0.02, 0, 1, 0, 80]] * 5
        cam = MO.camera_path(steps, 16)
        self.assertEqual(cam["cuts"], [1.0])
        self.assertIn("1 cut", cam["summary"])
        self.assertIn("pans left", cam["summary"])                 # since the cut the picture moves the other way
        self.assertAlmostEqual(cam["frames"][15]["zoom"], 1.01 ** 15, places=3)

    def test_still(self):
        self.assertIn("none (locked off)", MO.camera_path([[0, 0, 1, 0, 50]] * 20, 16)["summary"])


class People(unittest.TestCase):
    def test_same_person_keeps_number(self):
        tracks = {}
        a = MO._people_ids(tracks, [(0.2, 0.3), (0.7, 0.3)], 0)
        b = MO._people_ids(tracks, [(0.72, 0.31), (0.21, 0.3)], 1)
        self.assertEqual(a, [0, 1])
        self.assertEqual(b, [1, 0])
        c = MO._people_ids(tracks, [(0.45, 0.8)], 2)              # someone new walks in
        self.assertEqual(c, [2])


class Approval(unittest.TestCase):
    def test_take_waits_for_approval(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "motion").mkdir()
            rec = {"status": "tracked", "take_motion": {"source": "act.mov", "from": 0, "to": 4, "approved": False}}
            (Path(d) / "motion" / "motion.json").write_text(json.dumps(rec))
            take = {"motion": {"scene": d, "blur": []}}
            with self.assertRaises(SystemExit):
                T.motion_in(take)
            self.assertEqual(T.motion_in(take, dry_run=True)["motion"]["source"], "act.mov")
            MO.approve(d, "test")
            got = T.motion_in(take)["motion"]
            self.assertTrue(got["approved"])
            self.assertEqual((got["source"], got["to"]), ("act.mov", 4))

    def test_plain_motion_unchanged(self):
        take = {"motion": {"source": "swipe.mp4", "from": 0, "to": 10}}
        self.assertEqual(T.motion_in(take), take)


class Programmed(unittest.TestCase):
    def test_timeline_follows_the_lines(self):
        import motion_program as MP
        rows, total = MP.timeline({"script": [{"speaker": "A", "say": "one two three four five six"},
                                              {"speaker": "B", "say": "seven"}]})
        self.assertEqual([r["line"] for r in rows], [1, 2])
        self.assertGreater(rows[1]["from"], rows[0]["to"])
        self.assertGreater(total, rows[1]["to"])

    def test_clean_keeps_only_what_the_figures_can_do(self):
        import motion_program as MP
        spec = {"people": [{"name": "A", "at": [0, 0]}, {"name": "B", "at": [1, 0]}],
                "beats": [{"from": 1, "to": 2, "who": "A", "reach": "B.cheeks", "hands": "both"},
                          {"from": 2, "to": 3, "who": "C", "walk": [0, 1]},              # nobody called C
                          {"from": 3, "to": 4, "who": "B", "dance": True},               # no such action
                          {"from": 9, "to": 12, "who": "B", "nod": 2}],                  # runs past the end
                "camera": {"follow": [{"from": 0, "who": "A"}, {"from": 1, "who": "Z"}]}}
        got = MP.clean(spec, 10.0)
        self.assertEqual(len(got["beats"]), 2)
        self.assertEqual(len(got["dropped"]), 2)
        self.assertEqual(got["beats"][1]["to"], 10.0)
        self.assertEqual([f["who"] for f in got["camera"]["follow"]], ["A"])


if __name__ == "__main__":
    unittest.main()
