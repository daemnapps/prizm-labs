#!/usr/bin/env python3
"""picture_chain.products_in(): a layout names a product by its short look key ("body-scrub"); that key is the kit
whose folder name ends on it ("brilliance-body-scrub"), when exactly one does. brand-b nov-05, 2026-10-30: every
product picture was held "no product casting sheet for body-scrub" though the kit and its sheet exist.

    /usr/bin/python3 tools/email-production/design/test_picture_chain_short_name.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # design/ FIRST (email.py beside it shadows the stdlib's)
import picture_chain as C  # noqa: E402

KITS = {"zz-body-scrub": ["zz-body-scrub"], "zz-face-scrub": ["zz-face-scrub"], "glow-body-cream": ["glow-body-cream"]}


class TestShortName(unittest.TestCase):
    def setUp(self):
        self.orig = C.kits
        C.kits = lambda brand: KITS

    def tearDown(self):
        C.kits = self.orig

    def test_a_short_look_key_is_its_one_kit(self):
        self.assertEqual(C.products_in("zz", {"product": "body-scrub"}, "a tube on the sink"), ["zz-body-scrub"])
        self.assertEqual(C.products_in("zz", {"product": "body-cream"}, ""), ["glow-body-cream"])

    def test_a_key_two_kits_end_on_names_neither(self):
        self.assertEqual(C.products_in("zz", {"product": "scrub"}, ""), [])

    def test_the_full_slug_still_works(self):
        self.assertEqual(C.products_in("zz", {"product": "zz-face-scrub"}, ""), ["zz-face-scrub"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
