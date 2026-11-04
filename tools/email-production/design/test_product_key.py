"""The picture step hands the image engine a product the brand declares, not its Drive folder name (the team, 2026-10-22).

BRAND-A's look names product pictures by Drive folder (nova-face-brush) while products/images.json declares them as
flex, war, crush; the engine refused every one. Reads the real brand file; no network.

    /usr/bin/python3 test_product_key.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line  # noqa: E402


class ProductKey(unittest.TestCase):
    def test_drive_folder_becomes_the_declared_product(self):
        self.assertEqual(line.product_key("brand-a", "nova-face-brush"), "nova")
        self.assertEqual(line.product_key("brand-a", "war-face-wash"), "war")
        self.assertEqual(line.product_key("brand-a", "crush-bump-eliminator"), "crush")

    def test_a_folder_no_product_claims_is_left_as_it_is(self):
        self.assertEqual(line.product_key("brand-a", "no-such-folder"), "no-such-folder")


if __name__ == "__main__":
    unittest.main()
