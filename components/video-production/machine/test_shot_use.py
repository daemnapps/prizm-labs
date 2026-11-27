"""shot_use: the swipe's product use becomes ours, and the code catches an action on the wrong body part."""
import json
import tempfile
import unittest
from pathlib import Path

import shot_use as U

KIT = {"what": "the round face brush", "behaviour": {"held": "held in a closed palm, bristle face outward",
                                                      "in_use": "foams where the bristles meet the face", "never_show": ["held as a handle"]}}
SWIPE = {"does": "rubs cream into his left forearm", "camera": "medium", "text": "no greasy residue"}
LINE = "Your face feels clean and smooth after"


class ShotUse(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        Path(self.d.name, "kit.json").write_text(json.dumps(KIT))

    def tearDown(self):
        self.d.cleanup()

    def test_copied_body_part_is_a_problem(self):
        out = U.translate(SWIPE, LINE, self.d.name, ask=lambda p: {
            "our_does": "He rubs the face brush up and down his forearm", "product_in_shot": True})
        self.assertEqual(len(out["problems"]), 2, out["problems"])   # the product's own name does not count as "face"

    def test_translated_action_passes(self):
        out = U.translate(SWIPE, LINE, self.d.name, ask=lambda p: {
            "our_does": "He slides his fingertips along his smooth cheek", "product_in_shot": False})
        self.assertEqual(out["problems"], [])

    def test_prompt_carries_the_kit_and_our_words(self):
        seen = {}
        U.translate(SWIPE, LINE, self.d.name, ask=lambda p: seen.setdefault("p", p) and {"our_does": "x on his face"})
        self.assertIn("foams where the bristles meet the face", seen["p"])
        self.assertIn(LINE, seen["p"])


if __name__ == "__main__":
    unittest.main()
