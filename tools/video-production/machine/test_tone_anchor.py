"""P69 (2026-10-21): every start picture of a run graded to ONE anchor — the frame closest to the cast master —
by the person's skin, the grade only. Fakes for the face finder; real small pictures."""
import json
import tempfile
import unittest
from pathlib import Path

import tone_anchor as TA


def picture(path, skin, shirt, room=(200, 200, 200)):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (100, 160), room)
    d = ImageDraw.Draw(im)
    d.rectangle([30, 20, 70, 60], fill=skin)            # the face
    d.rectangle([20, 70, 80, 140], fill=shirt)          # the shirt
    im.save(path)


FACE = lambda folder: [{"file": "x.png", "x": 0.3, "y": 20 / 160, "w": 0.4, "h": 40 / 160, "open": 0}]


class OneTone(unittest.TestCase):
    def test_the_frame_nearest_the_master_anchors_and_a_yellow_frame_is_pulled_back(self):
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            (run / "media").mkdir()
            picture(run / "media" / "S1-F1.png", (190, 140, 115), (40, 55, 95))      # like the master
            picture(run / "media" / "S2-F1.png", (200, 150, 70), (55, 60, 60))       # yellow skin, grey shirt
            picture(run / "master.png", (192, 140, 112), (40, 56, 93))
            rec = TA.run(run, run / "master.png", faces=FACE)
            self.assertEqual(rec["anchor"], "S1-F1")
            from PIL import Image
            with Image.open(run / "media" / "S2-F1.png") as im:
                r, g, b = im.getpixel((50, 40))
            self.assertGreater(b, 70 + 10, "the yellow cast is pulled back toward the anchor (blue up)")
            self.assertTrue((run / "media" / "versions" / "S2-F1-before-tone.png").is_file(), "the ungraded picture is kept")
            # a second pass grades the kept original again — never twice on top of itself
            once = (run / "media" / "S2-F1.png").read_bytes()
            TA.run(run, run / "master.png", faces=FACE)
            self.assertEqual((run / "media" / "S2-F1.png").read_bytes(), once)

    def test_a_face_with_no_body_is_never_the_anchor_nor_graded(self):
        people = {"S1-F1": {"skin": [(190, 1), (140, 1), (110, 1)]},
                  "S2-F1": {"skin": [(180, 1), (130, 1), (100, 1)], "shirt": [(40, 1), (50, 1), (90, 1)]}}
        self.assertEqual(TA.choose_anchor(people, {"skin": [(190, 1), (140, 1), (110, 1)]}), "S2-F1")

    def test_the_grade_is_held_to_a_grade(self):
        g = TA.gains({"skin": [(100, 1), (100, 1), (100, 1)]}, {"skin": [(200, 1), (50, 1), (100, 1)]})
        self.assertEqual([x for x, _ in g], [1.25, 0.8, 1.0])


if __name__ == "__main__":
    unittest.main()
