import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import script_check as C


def run(tmp, head="star crunch neck ass", hold=1.6, words="bruh your razor bumps on that neck"):
    p = Path(tmp)
    (p / "lines.json").write_text(json.dumps({"a": words, "b": "nah"}))
    (p / "plan.json").write_text(json.dumps({"scenes": [{"id": "a", "speaker": "x"}, {"id": "b", "speaker": "y"}]}))
    (p / "ad.json").write_text(json.dumps({"headline": head, "small_print": [], "timeline": [{"id": "o", "hold": hold}, {"id": "a"}, {"id": "b"}], "beats": [{"id": "o", "scene": "bath"}, {"id": "a", "scene": "porch"}]}))
    return p


class Check(unittest.TestCase):
    def test_clean_script_passes(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(C.faults(run(t), "razor bump", "neck"), [])

    def test_ad_style_top_text_fails(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(C.faults(run(t, head="WHEN YOUR BUMPS WON'T QUIT"), "razor bump", "neck"))

    def test_short_opening_fails(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(C.faults(run(t, hold=1.0), "razor bump", "neck"))

    def test_problem_must_be_named(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(C.faults(run(t, words="bruh you good"), "razor bump", "neck"))


if __name__ == "__main__":
    unittest.main()
