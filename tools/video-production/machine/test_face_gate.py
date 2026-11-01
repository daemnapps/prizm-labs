"""The face gate (2026-10-23): no clip from a picture whose people are not their banked masters. No network — the
face question is a stub."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"t_fg_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


FG = _load("face_gate")


def stub(verdict):
    def check(picture, masters):
        return [{"master": m, "verdict": verdict, "votes": [verdict] * 3, "why": "stub"} for m in masters]
    return check


class FaceGate(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.pic = self.d / "F.png"
        self.pic.write_bytes(b"picture")
        self.master = self.d / "casting" / "marcus" / "full" / "master.png"
        self.master.parent.mkdir(parents=True)
        self.master.write_bytes(b"master")

    def test_same_face_passes_and_is_remembered(self):
        rec = FG.require(self.pic, [self.master], check=stub("SAME"))
        self.assertTrue(rec["pass"])
        self.assertTrue(FG.sidecar(self.pic).is_file())
        # the record is read back without asking again
        self.assertTrue(FG.require(self.pic, check=stub("DIFFERENT"))["pass"])

    def test_different_face_is_refused_by_name(self):
        with self.assertRaises(SystemExit) as e:
            FG.require(self.pic, [self.master], check=stub("DIFFERENT"))
        self.assertIn("marcus = DIFFERENT", str(e.exception))
        # and stays refused for the same bytes
        with self.assertRaises(SystemExit):
            FG.require(self.pic, check=stub("SAME"))

    def test_a_crowd_passes_as_a_group(self):
        # a congregation's master is one face from the crowd; the judge answers GROUP and the clip may be made
        self.assertTrue(FG.require(self.pic, [self.master], check=stub("GROUP"))["pass"])

    def test_absent_is_still_refused(self):
        with self.assertRaises(SystemExit):
            FG.require(self.pic, [self.master], check=stub("ABSENT"))

    def test_unanswered_face_is_refused(self):
        with self.assertRaises(SystemExit):
            FG.require(self.pic, [self.master], check=stub("UNCHECKED"))

    def test_a_remade_picture_is_checked_again(self):
        with self.assertRaises(SystemExit):
            FG.require(self.pic, [self.master], check=stub("DIFFERENT"))
        self.pic.write_bytes(b"picture remade")
        self.assertTrue(FG.require(self.pic, [self.master], check=stub("SAME"))["pass"])

    def test_a_picture_nobody_vouched_for_is_refused(self):
        with self.assertRaises(SystemExit) as e:
            FG.require(self.pic)
        self.assertIn("say who is in it", str(e.exception))

    def test_nobody_of_ours_passes_when_said(self):
        self.assertTrue(FG.require(self.pic, no_people=True)["pass"])
        self.assertTrue(json.loads(FG.sidecar(self.pic).read_text())["no_people"])

    def test_clip_door_refuses_before_any_call(self):
        O = _load("seedance")
        FG.stamp(self.pic, [self.master], check=stub("DIFFERENT"))

        class Door:                                     # a door that must never be reached
            calls = []

            def upload(self, *a):
                self.calls.append(a)
                return "u"

        voice = self.d / "line.mp3"
        voice.write_bytes(b"v")
        with self.assertRaises(SystemExit):
            O.motion("x", self.pic, self.d / "out.mp4", hf=Door())
        with self.assertRaises(SystemExit):
            O.talk("a line", self.pic, voice, self.d / "out.mp4", hf=Door())
        self.assertEqual(Door.calls, [])


if __name__ == "__main__":
    unittest.main()
