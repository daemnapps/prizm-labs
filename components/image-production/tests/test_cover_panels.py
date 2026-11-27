"""covers.panels: a cover that holds a strip or grid of other frames is not fit to file (2026-11-21, brief-0380: the
backup picture model laid three small video frames along a cover's bottom). Pictures made here; nothing is called."""
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import covers as C  # noqa: E402


def picture(strip):
    from PIL import Image
    rnd = random.Random(7)
    im = Image.new("L", (540, 960))
    px = im.load()
    for y in range(960):
        for x in range(540):
            px[x, y] = rnd.randint(30, 220)                 # a textured photograph
    if strip:
        for x in range(540):
            for y in range(790, 796):
                px[x, y] = 235                               # the full-width divider
        for gap in (178, 358):
            for y in range(796, 960):
                for x in range(gap, gap + 6):
                    px[x, y] = 235                           # the gaps between the small frames
    else:
        for y in range(600, 960):
            for x in range(540):
                px[x, y] = 12                                # a flat dark shirt is no divider
    f = Path(tempfile.mkdtemp()) / "p.png"
    im.save(f)
    return f


class Panels(unittest.TestCase):
    def test_a_strip_of_frames_is_found_and_stops_the_cover(self):
        why = C.panels(picture(True))
        self.assertIn("strip of other frames", why)
        self.assertTrue(any("one single photograph" in p for p in C.problems({"panels": why})))

    def test_one_photograph_with_a_flat_dark_area_is_not_a_strip(self):
        self.assertIsNone(C.panels(picture(False)))


class DrawnWords(unittest.TestCase):
    """brief-0380 H6: the picture model painted the headline, then the tool set it again; it showed twice."""
    def test_headline_sized_or_headline_words_in_the_plate_stop_the_cover(self):
        from unittest import mock
        from image_production import text_read as TR
        with mock.patch.object(TR, "lines", lambda p: [(0.058, "YOUR SKIN FEELS"), (0.01, "brand_b")]):
            got = C.plate_words("p.png", "Your skin feels like sand paper")
        self.assertEqual(got, ["YOUR SKIN FEELS"])                     # a small label is not drawn words
        self.assertTrue(any("words drawn in the picture" in p for p in C.problems({"plate_words": got})))
        with mock.patch.object(TR, "lines", lambda p: None):
            self.assertIsNone(C.plate_words("p.png", "x"))

    def test_a_failed_picture_judge_stops_the_cover(self):
        self.assertTrue(any("picture judge failed" in p for p in
                            C.problems({"below_criteria": True, "judge_fails": ["a doubled copy of the hand"]})))


class FitsTheDoor(unittest.TestCase):
    """brief-0380 covers: 32,000 characters, mostly past-review lessons, so Seedream refused the cover."""
    def test_the_lessons_go_first_and_the_pictures_own_words_stay(self):
        from image_production import engine as E
        own, after = "The cover: one moment. " * 50, "THE FRAME: 9:16, safe zone. " * 40
        text = own + "\n\nFrom every past review (a NEVER never happens again, a DO always does):\n" + \
            "\n".join("- DO: lesson %d " % n + "x" * 400 for n in range(80)) + "\n\n" + after
        got = E.fit_prompt(text)
        self.assertLessEqual(len(got), E.PROMPT_CAP)
        self.assertIn(own, got)
        self.assertIn(after.strip(), got)
        self.assertIn("- DO: lesson 0 ", got)            # the earliest lessons stay while they fit
        self.assertEqual(E.fit_prompt("short"), "short")


if __name__ == "__main__":
    unittest.main()
