#!/usr/bin/env python3
"""python3 test_he1b_true_once.py — HE-1b (true-once per email): a `true-once`
ruling belongs to its email, never replacing another email's `true-once` or a
brand-wide ruling. Stdlib unittest; no network, no model, no git. Reuses
HE-1 (fact rulings)'s helpers, which set a temp AI_WORKSPACE before importing
marketing_chain_checks."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_he1_fact_rulings as H              # noqa: E402  (sets AI_WORKSPACE first)
from marketing_chain_checks import rulings as R         # noqa: E402

PID = H.ITEMS[1]["id"]                          # a fact item: every ruling may clear it


class TrueOncePerEmail(unittest.TestCase):
    def setUp(self):
        self.root = H.fresh_root()

    def cleared(self, email):
        kept, rows = R.split(H.ITEMS, H.BRAND, email, self.root)
        self.assertEqual(len(kept) + len(rows), len(H.ITEMS))
        return {r["id"]: r["ruling"] for r in rows}

    def test_a_two_emails_each_true_once_both_pass(self):
        H.plant(self.root, PID, "true-once", email="e1")
        H.plant(self.root, PID, "true-once", email="e2")
        self.assertEqual(self.cleared("e1"), {PID: "true-once"})
        self.assertEqual(self.cleared("e2"), {PID: "true-once"})

    def test_b_true_once_never_displaces_a_brand_true(self):
        H.plant(self.root, PID, "true", email="e1", fact="it washes")
        H.plant(self.root, PID, "true-once", email="e2")
        self.assertEqual(self.cleared("e1"), {PID: "true"})
        self.assertEqual(self.cleared("e2"), {PID: "true-once"})
        self.assertEqual([f["id"] for f in R.verified_facts(self.root, H.BRAND)], [PID])

    def test_c_a_later_brand_wrong_holds_both(self):
        H.plant(self.root, PID, "true-once", email="e1")
        H.plant(self.root, PID, "true-once", email="e2")
        H.plant(self.root, PID, "wrong", email="e3")
        self.assertEqual(self.cleared("e1"), {})
        self.assertEqual(self.cleared("e2"), {})

    def test_d_a_later_true_once_clears_its_email_over_a_wrong(self):
        H.plant(self.root, PID, "wrong", email="e1")
        H.plant(self.root, PID, "true-once", email="e1")
        self.assertEqual(self.cleared("e1"), {PID: "true-once"})
        self.assertEqual(self.cleared("e2"), {})

    def test_e_a_true_once_never_clears_another_email(self):
        H.plant(self.root, PID, "true-once", email="e1")
        self.assertEqual(self.cleared("e2"), {})
        self.assertNotIn(PID, [k for k, _ in R.standing(self.root, H.BRAND).items()])
        self.assertEqual(list(R.once(self.root, H.BRAND)), [(PID, "e1")])


if __name__ == "__main__":
    unittest.main()
