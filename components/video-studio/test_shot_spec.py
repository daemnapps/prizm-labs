"""shot_spec: the owner's direction sets a shot's action ahead of the swipe's, behind a per-brand switch."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import shot_spec as SP

ROW = {"id": "S2.1", "seconds": 1.3, "swipe_camera": "close-up, eye level", "swipe_does": "she sniffs his neck"}


class Direction(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        root = Path(self.d.name)
        (root / "briefs" / "idea-x").mkdir(parents=True)
        (root / "briefs" / "idea-x" / "directions.json").write_text(json.dumps({"shots": {
            "S2.1": {"does": "two women hug him from both sides", "produce": True, "said": "get the girls hugging him"},
            "S3.1": {"does": "  "}}}))
        self.sw = root / "shot_spec.json"
        self.sw.write_text(json.dumps({"direction_first": {"on": True, "lanes": {}}}))
        self.p = [mock.patch.object(SP.ST, "BRIEFS", root / "briefs"), mock.patch.object(SP, "SWITCH", self.sw),
                  mock.patch.dict(os.environ, {"SHOT_DIRECTION_OFF": ""})]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.d.cleanup()

    def test_direction_is_used(self):
        d = SP.direction_of("idea-x", "S2.1", "brand-a")
        u = SP.use_from_direction(d, ROW)
        self.assertEqual(u["our_does"], "two women hug him from both sides")
        self.assertEqual(u["from"], "direction")
        self.assertFalse(u["product_in_shot"])
        self.assertEqual(u["problems"], [])

    def test_direction_words_carry_no_swipe_lines(self):
        w = SP.direction_words({"does": "two women hug him.", "camera": "Handheld, eye level."})
        self.assertEqual(w, "two women hug him. Handheld, eye level.")
        self.assertEqual(SP.direction_words({"does": "she hugs him"}), "she hugs him.")

    def test_no_or_blank_direction_keeps_swipe_first(self):
        self.assertIsNone(SP.direction_of("idea-x", "S9.9", "brand-a"))
        self.assertIsNone(SP.direction_of("idea-x", "S3.1", "brand-a"))

    def test_switch_master_and_lane(self):
        self.sw.write_text(json.dumps({"direction_first": {"on": False}}))
        self.assertIsNone(SP.direction_of("idea-x", "S2.1", "brand-a"))
        self.sw.write_text(json.dumps({"direction_first": {"on": True, "lanes": {"brand-a": False}}}))
        self.assertIsNone(SP.direction_of("idea-x", "S2.1", "brand-a"))
        self.assertIsNotNone(SP.direction_of("idea-x", "S2.1", "brand-b"))

    def test_machine_override(self):
        with mock.patch.dict(os.environ, {"SHOT_DIRECTION_OFF": "brand-a"}):
            self.assertIsNone(SP.direction_of("idea-x", "S2.1", "brand-a"))
            self.assertIsNotNone(SP.direction_of("idea-x", "S2.1", "brand-b"))
        with mock.patch.dict(os.environ, {"SHOT_DIRECTION_OFF": "all"}):
            self.assertIsNone(SP.direction_of("idea-x", "S2.1", "brand-b"))


if __name__ == "__main__":
    unittest.main()
