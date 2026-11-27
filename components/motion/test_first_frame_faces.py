"""motion_program.faces_in_picture: a start picture's people against their sheets, only the people in the frame."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion_program as MP  # noqa: E402


class Gate:
    def __init__(self, bad=()):
        self.bad, self.masters = set(bad), None

    def stamp(self, pic, masters):
        self.masters = [Path(m).stem for m in masters]
        people = [{"master": m, "verdict": "DIFFERENT" if Path(m).stem in self.bad else "SAME"} for m in masters]
        return {"pass": all(p["verdict"] == "SAME" for p in people), "people": people}


class Faces(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        for n in ("judge", "first", "back"):
            (d / ("%s.jpg" % n)).write_bytes(b"x")
        self.take = {"cast": {n.upper(): {"sheet": str(d / ("%s.jpg" % n))} for n in ("judge", "first", "back")},
                     "in_picture": ["JUDGE", "FIRST"]}

    def test_only_the_people_in_the_frame_and_a_miss_fails(self):
        g = Gate()
        ok, _ = MP.faces_in_picture(self.take, "p.png", gate=g)
        self.assertTrue(ok)
        self.assertEqual(g.masters, ["judge", "first"])
        ok, _ = MP.faces_in_picture(self.take, "p.png", gate=Gate(bad={"judge"}))
        self.assertFalse(ok)

    def test_no_sheets_passes(self):
        self.assertEqual(MP.faces_in_picture({"cast": {}}, "p.png"), (True, None))


if __name__ == "__main__":
    unittest.main()


class SetPrintLeads(unittest.TestCase):
    def test_the_set_print_leads_the_references(self):
        d = Path(tempfile.mkdtemp())
        (d / "print.png").write_bytes(b"x")
        refs, from_print = MP.photoreal_refs({"set_print": str(d / "print.png")}, d / "frame-1.png")
        self.assertTrue(from_print)
        self.assertEqual([r.name for r in refs], ["print.png", "frame-1.png"])

    def test_without_one_the_stand_in_frame_leads(self):
        refs, from_print = MP.photoreal_refs({}, Path("/x/frame-1.png"))
        self.assertFalse(from_print)
        self.assertEqual(refs[0].name, "frame-1.png")
