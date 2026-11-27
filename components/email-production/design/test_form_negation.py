#!/usr/bin/env python3
"""form_problems(): a word naming a product in a form it never takes (a 'jar' for a tube) holds the layout, but the
same word inside a "never …" / "no …" / "not …" clause is the product truth repeated, not a wrong form (brand-b
nov-04, 2026-10-30: "Never a jar, pot, bottle or tub" held its own layout three times).

    /usr/bin/python3 tools/email-production/design/test_form_negation.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # design/ FIRST (email.py beside it shadows the stdlib's)
import line as LN  # noqa: E402

BANNED = {"zz-scrub": ["jar", "pot", "bottle", "tub"]}


class TestNegation(unittest.TestCase):
    def test_a_wrong_form_holds(self):
        self.assertEqual(LN.form_problems("the scrub in a glass jar on the sink", BANNED),
                         ["calls the product a jar: the product file says it never is one"])
        self.assertEqual(len(LN.form_problems("two jars and a bottle", BANNED)), 2)

    def test_the_truth_repeated_in_a_never_clause_does_not(self):
        for ok in ("a brown squeeze tube, never a jar, pot, bottle or tub (product truth)",
                   "Never a jar, pot, bottle or tub; no sibling tubes in frame",
                   "the tube standing on the sink. Not a bottle.",
                   '{"todo": "the tube, no jar or tub", "alt": "x"}'):
            self.assertEqual(LN.form_problems(ok, BANNED), [], ok)

    def test_a_wrong_form_after_the_clause_still_holds(self):
        self.assertEqual(LN.form_problems("never a tub. She holds the jar.", BANNED),
                         ["calls the product a jar: the product file says it never is one"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
