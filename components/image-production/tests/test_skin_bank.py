"""The skin bank and its place in the print (owner, 2026-11-26: real skin on every picture that shows skin)."""
import sys, unittest
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import skin_bank as K
import picture_sets as S

ROWS = [{"file": "a", "kind": "customer", "condition": "acne", "tone": "deep-brown", "marks": ["acne"]},
        {"file": "b", "kind": "customer", "condition": "razor bumps", "tone": "fair", "marks": ["razor bumps"]},
        {"file": "c", "kind": "macro", "condition": "clear", "tone": "fair"},
        {"file": "d", "kind": "macro", "condition": "clear", "tone": "dark-brown"}]


class Bank(unittest.TestCase):
    def test_customer_and_macro_together_tone_matched(self):
        got = K.pick("acne", rows=ROWS)
        self.assertEqual([r["file"] for r in got], ["a", "d"])

    def test_gap_named(self):
        self.assertTrue(K.gaps([ROWS[0]]))

    def test_print_words_carry_skin(self):
        w = S.print_prompt({"shot": "a cheek", "light": "dim", "skin": True})
        self.assertIn("'skin'", w)

    def test_filing_skin_without_bank_refused(self):
        self.assertTrue(S.shows_skin([], [{"to": "acne on his cheek"}]))
        self.assertFalse(S.shows_skin([], [{"to": "the black face brush on a shelf"}]))

    def test_pick_reads_condition_and_tone_from_the_scene(self):
        got = S.skin_pick("a deep brown Black man's neck covered in razor bumps after a cut, acne once")
        self.assertTrue(got and "razor" in got[0]["condition"])


if __name__ == "__main__":
    unittest.main()
