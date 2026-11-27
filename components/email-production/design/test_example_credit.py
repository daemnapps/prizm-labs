"""A quote section says "verified buyer" only for a buyer (brand_a dec-19, 2026-11-17: an Instagram ad comment from a
lead was shown as a verified buyer). No network, no key.

    python3 components/email-production/design/test_example_credit.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as EN  # noqa: E402


class Credit(unittest.TestCase):
    def test_a_customer_keeps_the_badge(self):
        out = EN.s_example({}, {"quote": "Works.", "who": "Marcus"}, {})
        self.assertIn("verified buyer", out)

    def test_a_public_comment_has_no_badge(self):
        out = EN.s_example({}, {"quote": "I need this.", "who": "An Instagram comment"}, {})
        self.assertNotIn("verified buyer", out)
        self.assertIn("An Instagram comment", out)

    def test_a_survey_has_no_badge(self):
        self.assertNotIn("verified buyer", EN.s_example({}, {"quote": "x", "who": "From our follower survey"}, {}))

    def test_verified_false_has_no_badge(self):
        self.assertNotIn("verified buyer", EN.s_example({}, {"quote": "x", "who": "Marcus", "verified": False}, {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
