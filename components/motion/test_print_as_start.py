"""motion_chain._print_as_start: a filed print that matches the rehearsal is the start picture as printed; one that
does not match is never used. python3 -m unittest test_print_as_start.py"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion_chain as MC  # noqa: E402


class PrintAsStart(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "motion").mkdir()
        self.print = self.d / "print.png"
        self.print.write_bytes(b"PRINT")
        (self.d / "take.json").write_text(json.dumps({"set_print": str(self.print)}))
        self.real = MC.start_check

    def tearDown(self):
        MC.start_check = self.real

    def test_a_matching_print_is_used_as_printed(self):
        MC.start_check = lambda sd, p=None: {"failed": 0}
        pic = self.d / "motion" / "first-frame.png"
        self.assertTrue(MC._print_as_start(self.d, pic))
        self.assertEqual(pic.read_bytes(), b"PRINT")

    def test_a_print_off_the_rehearsal_is_not_used(self):
        MC.start_check = lambda sd, p=None: {"failed": 3}
        pic = self.d / "motion" / "first-frame.png"
        self.assertFalse(MC._print_as_start(self.d, pic))
        self.assertFalse(pic.exists())

    def test_camera_only_uses_the_print_without_a_rehearsal(self):
        (self.d / "motion" / "motion.json").write_text(json.dumps({"camera_only": True}))
        def no_rehearsal(sd, p=None):
            raise SystemExit("needs the scene's rehearsal")
        MC.start_check = no_rehearsal
        pic = self.d / "motion" / "first-frame.png"
        self.assertTrue(MC._print_as_start(self.d, pic))
        self.assertEqual(pic.read_bytes(), b"PRINT")
        rec = json.loads((self.d / "motion" / "match-start-picture.json").read_text())
        self.assertEqual((rec["failed"], rec["camera_only"]), (0, True))

    def test_no_print_named(self):
        (self.d / "take.json").write_text("{}")
        self.assertFalse(MC._print_as_start(self.d, self.d / "motion" / "first-frame.png"))


if __name__ == "__main__":
    unittest.main()


class PrintWords(unittest.TestCase):
    def test_people_numbered_in_lineup_order_with_their_looks(self):
        d = Path(tempfile.mkdtemp())
        (d / "take.json").write_text(json.dumps({"lineup": ["A", "B"], "look": "a candlelit hall; sound: none",
                                                 "cast": {"A": {"look": "man in a mask"}, "B": {"look": "man in a hat"},
                                                          "W": {"look": "woman with a loupe"}}}))
        real = MC.frame_words
        MC.frame_words = lambda sd, frame=0: "A: head left. B: head centre. W: head right."
        try:
            w = MC.print_words(d)
        finally:
            MC.frame_words = real
        self.assertIn("person 1 (A): head left", w)
        self.assertIn("person 3 (W): head right", w)
        self.assertIn("Person 2 (B): man in a hat.", w)
        self.assertIn("a candlelit hall", w)
        self.assertNotIn("sound", w)
