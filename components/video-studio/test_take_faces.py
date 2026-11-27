"""take_faces: the start picture and every beat of a take hold their people to the sheets."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import take_faces as TF  # noqa: E402


class Gate:
    def __init__(self, bad=()):
        self.bad, self.calls = set(bad), []

    def require(self, pic, masters):
        self.calls.append(("require", pic, list(masters)))
        if any(Path(m).stem in self.bad for m in masters):
            raise SystemExit("refused")
        return {"pass": True}

    def stamp(self, pic, masters):
        self.calls.append(("stamp", pic, list(masters)))
        people = [{"master": m, "verdict": "DIFFERENT" if Path(m).stem in self.bad else "SAME"} for m in masters]
        return {"pass": all(p["verdict"] == "SAME" for p in people), "people": people}


class TakeFaces(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for n in ("judge", "first", "second"):
            (self.d / ("%s.jpg" % n)).write_bytes(b"x")
        self.take = {"picture": str(self.d / "start.png"),
                     "cast": {"JUDGE": {"sheet": str(self.d / "judge.jpg")}, "FIRST": {"sheet": str(self.d / "first.jpg")},
                              "SECOND": {"sheet": str(self.d / "second.jpg")}},
                     "in_picture": ["JUDGE", "FIRST"],
                     "script": [{"do": "a", "faces": {"JUDGE": "deadpan"}, "moves": {"FIRST": "stands"}},
                                {"do": "b", "faces": {"JUDGE": "deadpan"}},
                                {"do": "c", "moves": {"SECOND": "waits"}}]}

    def test_the_picture_is_checked_against_the_people_in_it_only(self):
        g = Gate()
        TF.gate_picture(self.take, gate=g)
        self.assertEqual([Path(m).stem for m in g.calls[0][2]], ["judge", "first"])
        with self.assertRaises(SystemExit):
            TF.gate_picture(self.take, gate=Gate(bad={"judge"}))

    def test_a_drifted_take_is_set_aside_and_stops(self):
        clip = self.d / "take.mp4"
        clip.write_bytes(b"v")
        kw = dict(frame=lambda c, t, o: o, seconds=lambda c: 9.0)
        res = TF.hold_drift(self.take, clip, gate=Gate(), **kw)
        self.assertTrue(res["pass"])
        self.assertEqual([b["at"] for b in res["beats"]], [1.5, 4.5, 7.5])
        with self.assertRaises(SystemExit) as e:
            TF.hold_drift(self.take, clip, gate=Gate(bad={"second"}), **kw)
        self.assertIn("beat 3", str(e.exception))
        self.assertFalse(clip.exists())
        self.assertTrue((self.d / "take.drift.mp4").exists())

    def test_the_switch(self):
        os.environ["TAKE_FACES_OFF"] = "picture"
        try:
            self.assertIsNone(TF.gate_picture(self.take, gate=Gate(bad={"judge"})))
        finally:
            os.environ.pop("TAKE_FACES_OFF")


if __name__ == "__main__":
    unittest.main()
