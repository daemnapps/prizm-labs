"""A gift named with its own value is that item's bank price, not a price the offer sells (2026-11-10: owner's Black
Friday wording 'Free $19 travel pouch' held two Glow Duo emails at the delivery gate).

    /usr/bin/python3 test_free_item_price.py
"""
import unittest

import simple_email as S

BANK = ("## glow-duo-bundle — Glow Duo Bundle\n\n- Price: **$58.00**\n\n"
        "## brand_b-travel-pouch — brand_b Travel Pouch\n\n- Price: **$19.00**\n\n"
        "## brilliance-face-scrub — Brilliance Face Scrub\n\n- Price: **$49.00**\n")


class FreeItemPrice(unittest.TestCase):
    def test_the_gift_at_its_own_price_is_allowed(self):
        self.assertIn("$19", S.free_item_prices("Glow Duo Bundle, $58. Free $19 travel pouch with every order.", BANK))

    def test_a_wrong_value_or_another_item_is_not(self):
        self.assertEqual(S.free_item_prices("a free $25 travel pouch", BANK), "")
        self.assertEqual(S.free_item_prices("a free $19 face scrub", BANK), "")
        self.assertEqual(S.free_item_prices("$19 travel pouch", BANK), "")


GBANK = ("### new-man-store-credit — every product\n"
         "> Run the routine for 90 days, send your before & after, and we put $100 STORE CREDIT back in your account.\n")


class GuaranteeAmount(unittest.TestCase):
    def test_the_guarantee_word_for_word_keeps_its_figure(self):
        t = "So the risk is ours. Run the routine for 90 days, send your before & after, and we put $100 STORE CREDIT back in your account."
        self.assertIn("$100", S.guarantee_amounts(t, GBANK))

    def test_the_figure_alone_or_reworded_is_not_allowed(self):
        self.assertEqual(S.guarantee_amounts("Get $100 off today.", GBANK), "")
        self.assertEqual(S.guarantee_amounts("Run it 90 days and we put $100 back in your account.", GBANK), "")


if __name__ == "__main__":
    unittest.main()
