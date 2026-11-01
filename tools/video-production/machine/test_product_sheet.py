import json
import unittest
from pathlib import Path

import product_sheet as ps


class Layout(unittest.TestCase):
    def test_a_bottle_keeps_the_three_row_sheet(self):
        self.assertEqual(ps.layout(1), (3, 1856))

    def test_six_use_pictures_take_two_rows(self):
        self.assertEqual(ps.layout(6), (4, 2430))

    def test_a_case_says_its_length_as_tall(self):
        self.assertIn("12.8 cm tall × 9.4 cm wide", ps.title("CASE", {"length": 12.8, "width": 9.4}))

    def test_no_size_is_said_plainly(self):
        self.assertIn("size not measured", ps.title("POUCH", {"height": None}))

    def test_every_product_names_all_six_views_and_a_use(self):
        doc = json.loads(ps.STANDARD.read_text())
        views = {v for v, _ in doc["views"]}
        for key, spec in doc["products"].items():
            self.assertEqual(set(spec["tiles"]), views, key)
            self.assertTrue(spec["use"], key)


if __name__ == "__main__":
    unittest.main()
