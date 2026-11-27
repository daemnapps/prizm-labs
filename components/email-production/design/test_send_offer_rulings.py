"""The design steps read the send's own offer, never the funnel's (2026-11-08). No model, no network."""
import json
import tempfile
import unittest
from pathlib import Path

import promises as P


class TheSendsOwnOfferWins(unittest.TestCase):
    def test_send_offers_come_from_the_copy_argv(self):
        d = Path(tempfile.mkdtemp())
        (d / "copy-argv.json").write_text(json.dumps(["x", "--offer", "a-b", "--offer-also", "c,none"]))
        self.assertEqual(P.send_offers(d), ["a-b", "c"])
        self.assertEqual(P.send_offers(Path(tempfile.mkdtemp())), [])

    def test_a_block_the_bank_keeps_for_the_funnel_is_never_an_emails(self):
        self.assertTrue(P.funnel_only("black-friday — The offer\n\nFunnels and their ads (owner). Emails lead with x."))
        self.assertFalse(P.funnel_only("the-king-skin-set — The King Set\n\n- Price: $129.99"))

    def test_funnel_lines_inside_a_product_block_are_taken_out(self):
        block = "body-scrub — Scrub\n- Price: $29\n- Sold in the CPK funnel at: $57 (3 Tubes, Buy 2 Get 1 Free)\n- Funnel offer (x): starting at $49\n- Link: y"
        got = P.email_lines(block)
        self.assertIn("$29", got)
        self.assertNotIn("$57", got)
        self.assertNotIn("$49", got)
        self.assertIn("Link: y", got)


if __name__ == "__main__":
    unittest.main()
