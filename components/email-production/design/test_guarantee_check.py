"""The product check accepts any guarantee wording the brand signed, word for word, and names it (the team, 2026-10-22).
Reads the real brand files; no network.

    /usr/bin/python3 test_guarantee_check.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

LOOK = "If your skin doesn't transform, full refund. You keep the NOVA™."
FORMULAS = "Run it daily for 90 days. If you can't see the difference between day 1 and day 90, we refund you in full."


class GuaranteeCheck(unittest.TestCase):
    def found(self, words):
        return [w for w in (v for _, v in build.guarantees("brand-a", LOOK)) if w in words]

    def test_the_formulations_wording_counts(self):
        self.assertTrue(self.found("Be skeptical. " + FORMULAS))

    def test_the_look_wording_still_counts(self):
        self.assertTrue(self.found("Try it. " + LOOK))

    def test_a_paraphrase_does_not(self):
        self.assertFalse(self.found("Use it for 90 days or we refund you."))
        self.assertIsNone(build.guarantee_hit("brand-a", LOOK, "Use it for 90 days or we refund you.")[0])

    def test_the_first_letter_may_follow_the_sentence(self):
        """brand-b-nov-08 runs its heading into the guarantee: "In place of a date sixty days to ask…"."""
        hit = build.guarantee_hit("brand-b", "", "In place of a date sixty days to ask for your money back, whenever you're ready.")
        self.assertEqual(hit, ("sixty-day-email", "word for word"))



TERMS = {"all_of": [["60", "sixty"], ["money back", "refund", "every penny"]],
         "none_of": ["send it back", "return it", "twice a week", "if the spots", "consistently"]}


class GuaranteeByItsTerms(unittest.TestCase):
    """Brand-B's email guarantee may be paraphrased if it keeps its terms; BRAND-A's stay word for word (the team, 2026-10-27)."""
    def setUp(self):
        self.real = build._guarantee_rows
        rows = {"sixty-day-email": {"verbatim": "Sixty days to ask for your money back, whenever you're ready.", "terms": TERMS}}
        build._guarantee_rows = lambda brand: rows if brand == "brand-b" else self.real(brand)

    def tearDown(self):
        build._guarantee_rows = self.real

    def hit(self, line):
        return build.guarantee_hit("brand-b", "", line, line)

    def test_a_paraphrase_that_keeps_the_terms_passes(self):
        for line in ("You have sixty days to get your money back, no questions.", "60 days. If you're not happy, we refund you."):
            self.assertEqual(self.hit(line), ("sixty-day-email", "by its terms"), line)

    def test_a_paraphrase_that_breaks_a_term_is_held_and_says_which(self):
        name, why = self.hit("Love it or send it back within 60 days.")
        self.assertIsNone(name)
        self.assertIn('says "send it back"', why)
        self.assertIn("does not say", why)          # no money back either
        name, why = self.hit("Use it twice a week for 60 days or get your money back.")
        self.assertIsNone(name)
        self.assertIn('says "twice a week"', why)

    def test_the_terms_are_read_in_the_guarantee_section_only(self):
        """nov-01 says "Twice a week is the scrub" elsewhere; only the guarantee's own words are judged."""
        words = "Twice a week is the scrub. 60 days. If you're not happy, we refund you."
        self.assertEqual(build.guarantee_hit("brand-b", "", words, "60 days. If you're not happy, we refund you."),
                         ("sixty-day-email", "by its terms"))

    def test_brand_a_has_no_terms_so_a_paraphrase_is_held(self):
        self.assertIsNone(build.guarantee_hit("brand-a", LOOK, "90 days or a full refund.", "90 days or a full refund.")[0])


if __name__ == "__main__":
    unittest.main()
