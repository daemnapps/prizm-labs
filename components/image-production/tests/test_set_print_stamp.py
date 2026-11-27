"""A kept 3D set print, and what the tool lays on it, carry the tool's record (GATE-5 x GATE-4, 2026-11-24)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))

from PIL import Image  # noqa: E402

from image_production import provenance as PV  # noqa: E402
from image_production import split_slide as SS, story_caption as SC  # noqa: E402


class SetPrintStamp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = os.environ.get("IMAGE_MADE_LEDGER")
        os.environ["IMAGE_MADE_LEDGER"] = str(self.tmp / "made.jsonl")
        self.print_ = self.tmp / "print-v1.png"
        Image.new("RGB", (540, 960), (40, 60, 80)).save(self.print_)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("IMAGE_MADE_LEDGER", None)
        else:
            os.environ["IMAGE_MADE_LEDGER"] = self.old

    def test_kept_print_is_on_record(self):
        self.assertFalse(PV.known(self.print_))
        PV.set_print(self.print_, brand="b", set_name="s")
        self.assertTrue(PV.known(self.print_))

    def test_words_on_a_kept_print_are_on_record(self):
        PV.set_print(self.print_, brand="b", set_name="s")
        out = self.tmp / "ad.png"
        SC.render(self.print_, out, {"handle": "@x", "emoji": "", "bubbles": [["hi"]]})
        self.assertTrue(PV.known(out))

    def test_words_on_a_stranger_picture_are_not(self):
        out = self.tmp / "ad.png"
        SC.render(self.print_, out, {"handle": "@x", "emoji": "", "bubbles": [["hi"]]})
        self.assertFalse(PV.known(out))

    def test_a_layout_needs_every_photo_on_record(self):
        other = self.tmp / "other.png"
        Image.new("RGB", (540, 540), (90, 90, 90)).save(other)
        PV.set_print(self.print_, brand="b", set_name="s")
        words = {"title": "T", "label_l": "A", "label_r": "B", "cap_l": "( a )", "cap_r": "( b )"}
        out = self.tmp / "slide.png"
        SS.render(out, {"tl": self.print_, "tr": self.print_, "bl": self.print_, "br": other}, words)
        self.assertFalse(PV.known(out))
        PV.set_print(other, brand="b", set_name="s2")
        SS.render(out, {"tl": self.print_, "tr": self.print_, "bl": self.print_, "br": other}, words)
        self.assertTrue(PV.known(out))


if __name__ == "__main__":
    unittest.main()
