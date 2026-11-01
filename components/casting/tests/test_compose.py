#!/usr/bin/env python3
"""Tests for casting.compose: picks become one prompt plus references.

    /usr/bin/python3 components/casting/tests/test_compose.py

Stdlib unittest, 3.9-safe, offline, temp dirs only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from casting import compose  # noqa: E402

EL = {"identity": "A woman of about 76.",
      "slots": {"outfit": {"robe": {"words": "a turquoise robe", "references": ["sheets/look-4.jpg"]}},
                "eyewear": {"round": {"words": "round tortoiseshell sunglasses"}}}}


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        Path(self.d.name, "elements.json").write_text(json.dumps(EL))

    def tearDown(self):
        self.d.cleanup()

    def test_picked_skin_adds_its_reference_and_drops_the_stock_age_spots(self):
        el = json.loads(json.dumps(EL))
        el["slots"]["skin"] = {"clear": {"words": "clear skin"},
                               "marks": {"words": "dark marks", "references": ["../../skin/marks/reference.jpg"]}}
        Path(self.d.name, "elements.json").write_text(json.dumps(el))
        r = compose.compose(self.d.name, {"skin": "marks"})
        self.assertIn("../../skin/marks/reference.jpg", r["references"])
        self.assertNotIn("age spots", r["prompt"])
        self.assertIn("age spots", compose.compose(self.d.name, {"eyewear": "round"})["prompt"])

    def test_headshot_first_and_picks_in_prompt(self):
        r = compose.compose(self.d.name, {"outfit": "robe", "eyewear": "round"}, scene="by the pool")
        self.assertEqual(r["references"][0], compose.HEADSHOT)
        self.assertIn("sheets/look-4.jpg", r["references"])
        self.assertIn("a turquoise robe", r["prompt"])
        self.assertIn("by the pool", r["prompt"])

    def test_baseline_is_layered_and_never_the_master(self):
        Path(self.d.name, "sheets").mkdir()
        for f in ("details.jpg", "angles-expressions.jpg", "look-4.jpg", "master.jpg"):
            (Path(self.d.name, "sheets") / f).write_bytes(b"x")
        r = compose.compose(self.d.name, {"outfit": "robe"})
        names = [n for n, _ in r["layers"]]
        self.assertEqual(names[:4], ["headshot", "look", "details", "expression"])
        self.assertNotIn("master.jpg", " ".join(r["references"]))

    def test_unpicked_slot_not_invented(self):
        r = compose.compose(self.d.name, {"outfit": "robe"})
        self.assertNotIn("sunglasses", r["prompt"])

    def test_unknown_slot_and_option_refused_by_name(self):
        with self.assertRaises(compose.PickError):
            compose.compose(self.d.name, {"hat": "x"})
        with self.assertRaises(compose.PickError):
            compose.compose(self.d.name, {"outfit": "nope"})

    def test_choices_lists_options(self):
        self.assertEqual(compose.choices(self.d.name)["outfit"], ["robe"])


if __name__ == "__main__":
    unittest.main()
