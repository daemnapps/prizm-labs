#!/usr/bin/env python3
"""engine.s_example(): a customer's words with no picture of that customer draw as words only (the team, 2026-10-30,
brand-a nov-06 glow-up: "replace the $24.99 receipt and the WAR bottle in the two customer slots with that customer's
own picture from the archive, or words only"). With a picture, it draws as before.

    /usr/bin/python3 tools/email-production/design/test_example_words_only.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # design/ FIRST (email.py beside it shadows the stdlib's)
import engine as EN  # noqa: E402
import look as L  # noqa: E402


class TestWordsOnly(unittest.TestCase):
    def test_no_picture_is_words_only(self):
        lk = L.Look("zz", {}, None)
        for style in ({}, {"quote_card": True}):
            h = EN.s_example(lk, {"s": "example", "quote": "a brush for my pores", "who": "A ZZ customer",
                                  "ask": "That is the step.", "style": style}, None)
            self.assertIn("a brush for my pores", h)
            self.assertIn("That is the step.", h)
            self.assertNotIn("<img", h)
            self.assertNotIn("<figure", h)


if __name__ == "__main__":
    unittest.main(verbosity=2)
