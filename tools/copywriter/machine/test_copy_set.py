#!/usr/bin/env python3
"""copy_set — checks and filling. No model, no network."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import copy_set as CS  # noqa: E402

BODY = " ".join(["word"] * 30)
GOOD = {
    "brand": "brand-a", "product": "crush", "angle": "razor-not-problem",
    "primary": [{"format": "short", "text": f"{BODY}\n\n{{offer}}\n\n{{click}}"},
                {"format": "standard", "text": " ".join(["word"] * 90) + "\n\n{offer}\n\n{click}"},
                {"format": "proof", "text": ""}],
    "headlines": ["Your razor isn't the problem"], "descriptions": ["$19.99 · 3 for $49.99"],
    "offer_line": "CRUSH™ Bump Eliminator is $19.99, or $49.99 for 3.",
    "click": {"quiz": "Tap Learn More to take the quiz.", "product": "Tap Shop Now to get CRUSH™."},
    "rows_used": [], "rows": {},
    "promo": True,      # a promotion: its description may carry the price (the owner, 2026-10-12)
}


class Checks(unittest.TestCase):
    def test_a_sound_set_passes(self):
        self.assertEqual(CS.check(GOOD), [])

    def test_what_fails(self):
        bad = dict(GOOD, headlines=["x" * 41], offer_line="CRUSH is $14.99.",
                   click={"quiz": "Link in bio", "product": "Tap Shop Now"},
                   primary=[{"format": "short", "text": BODY}, GOOD["primary"][1],
                            {"format": "proof", "text": "\"I made this quote up myself today\"\n\n{offer}\n\n{click}"}])
        got = " | ".join(CS.check(bad))
        for want in ("headline over 40", "organic ask", "short: no {offer}", "short: the last line is not {click}",
                     "proof quote not found", "14.99"):
            self.assertIn(want, got)


class TheTwoRules(unittest.TestCase):
    """the owner, 2026-10-12: no price in headlines or descriptions unless a promotion; words at the ad's level."""

    def test_a_price_in_a_description_holds_a_set_that_is_not_a_promotion(self):
        got = " | ".join(CS.check(dict(GOOD, promo=False)))
        self.assertIn("description carries a price or offer", got)
        got = " | ".join(CS.check(dict(GOOD, promo=False, headlines=["Buy 2, get 1 free"],
                                       descriptions=["Money back guarantee"])))
        self.assertIn("headline carries a price or offer", got)
        self.assertIn("description carries a price or offer", got)

    def test_unaware_bars_the_offer_in_the_bodies_and_needs_no_offer_line(self):
        plain = [{"format": "short", "text": f"{BODY}\n\n{{click}}"},
                 {"format": "standard", "text": " ".join(["word"] * 90) + "\n\n{click}"},
                 {"format": "proof", "text": ""}]
        ok = dict(GOOD, promo=False, awareness="unaware", primary=plain, offer_line="",
                  headlines=["It was never the razor"], descriptions=["A sonic brush for the neck"])
        self.assertEqual(CS.check(ok), [])
        got = " | ".join(CS.check(dict(ok, primary=GOOD["primary"])))
        self.assertIn("carries {offer} at awareness `unaware`", got)
        got = " | ".join(CS.check(dict(ok, primary=[{"format": "short", "text": f"{BODY} Only $19.99.\n\n{{click}}"}]
                                       + plain[1:])))
        self.assertIn("doctrine entry bars price", got)

    def test_the_level_is_read_from_the_doctrine(self):
        self.assertTrue(CS.bars_price("unaware"))
        self.assertFalse(CS.bars_price("most-aware"))
        self.assertFalse(CS.bars_price(None))
        with self.assertRaises(ValueError):
            CS.awareness_entry("tip-of-funnel")

    def test_promo_comes_from_the_flag_or_the_angle_row_never_the_copy(self):
        import json, tempfile
        ws = Path(tempfile.mkdtemp())
        (ws / "brands/b/strategy").mkdir(parents=True)
        (ws / "brands/b/strategy/angles.json").write_text(json.dumps({"angles": [
            {"id": "stock-up-value", "name": "Stock-up value"}, {"id": "a-story", "name": "A story"},
            {"id": "flagged", "name": "Plain", "promo": True}]}))
        self.assertTrue(CS.is_promo("b", "stock-up-value", ws=ws))
        self.assertFalse(CS.is_promo("b", "a-story", ws=ws))
        self.assertTrue(CS.is_promo("b", "flagged", ws=ws))
        self.assertFalse(CS.is_promo("b", "stock-up-value", flag=False, ws=ws))
        self.assertFalse(CS.is_promo("b", "not-there", ws=ws))

    def test_a_run_s_recorded_awareness_is_found(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "brief.md").write_text('```json\n{"piece": {"awareness": "unaware"}}\n```')
        self.assertEqual(CS.awareness_from_run(d), "unaware")
        self.assertIsNone(CS.awareness_from_run(None))


class Fill(unittest.TestCase):
    def test_tokens_follow_the_page(self):
        q = CS.fill(GOOD, page_type="quiz")
        self.assertTrue(q["primary"][0].endswith("Tap Learn More to take the quiz."))
        self.assertIn("$19.99", q["primary"][0])
        self.assertEqual(len(q["primary"]), 2)          # the empty proof body is dropped
        self.assertTrue(CS.fill(GOOD, link_id="link_b_cpk_bump-check-portal")["primary"][0]
                        .endswith("Tap Learn More to take the quiz."))      # a portal is quiz-shaped
        p = CS.fill(GOOD, link_id="link_brand_a_store_crush")
        self.assertTrue(p["primary"][1].endswith("Tap Shop Now to get CRUSH™."))

    def test_only_an_approved_set_is_used(self):
        orig = CS.load
        try:
            CS.load = lambda *a, **k: dict(GOOD, status="draft")
            self.assertIsNone(CS.approved("brand-a", "crush", "razor-not-problem"))
            CS.load = lambda *a, **k: dict(GOOD, status="approved")
            self.assertIsNotNone(CS.approved("brand-a", "crush", "razor-not-problem"))
        finally:
            CS.load = orig


if __name__ == "__main__":
    unittest.main()
