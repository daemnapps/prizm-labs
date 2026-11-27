#!/usr/bin/env python3
"""A saving the bank conditions is refused without its condition (2026-11-04): in a text, in an email's words and in
its subject lines. Where the bank marks no condition, nothing changes. No model, no network, no key."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import offers  # noqa: E402
import sms  # noqa: E402
import simple_email as S  # noqa: E402   (takes this folder off the path: imported last)

SET = """## the-set — The Set
_lane: b_  ·  _hero: paid_

- Price: **$129.99**, was $139.95
- Subscribed: **$109.99** first order, then **$39.99** every 45 days
- Saving: **$29.96 with the subscription** ($139.95 to $109.99); $9.96 one-time. Copy stating the saving says it's with the subscription.
"""
DEVICE = """## device — The Device
_lane: a_  ·  _hero: paid_

- Price: **$69.99**, was $99.99
"""
BANK = "# Bank\n\n" + SET + "\n" + DEVICE
CAD = {"length": {"max_chars": 160, "link_chars": 25, "opt_out": "Reply STOP to opt out"}}


class Refused(unittest.TestCase):
    def bad(self, text, alone=True):
        return offers.saving_problems(text, SET, alone)

    def test_a_saving_without_the_condition_is_refused(self):
        for line in ("Save $29.96 on The Set.", "You save $9.96.", "Savings on The Set this week.", "$29.96 less today."):
            self.assertTrue(self.bad(line), line)

    def test_the_subscribed_price_needs_it_too(self):
        self.assertTrue(self.bad("The Set is $109.99."))
        self.assertFalse(self.bad("The Set is $109.99 with the subscription."))

    def test_a_saving_with_the_condition_stands(self):
        self.assertFalse(self.bad("Save $29.96 on The Set with the subscription."))
        self.assertFalse(self.bad("Subscribe and save $29.96."))

    def test_the_store_price_and_was_price_need_no_condition(self):
        self.assertFalse(self.bad("The Set is $129.99, was $139.95."))

    def test_the_condition_sits_in_the_same_sentence(self):
        self.assertTrue(self.bad("Save $29.96. The subscription ships every 45 days."))

    def test_an_offer_with_no_marked_condition_is_untouched(self):
        self.assertIsNone(offers.saving_condition(DEVICE))
        self.assertEqual(offers.saving_problems("Save $30 today.", DEVICE), [])

    def test_in_a_mix_another_products_saving_is_not_this_ones(self):
        self.assertFalse(self.bad("Save $30 on The Device.", alone=False))
        self.assertTrue(self.bad("Save $29.96 on The Set.", alone=False))

    def test_a_text_is_refused_and_kept_held(self):
        got = sms.check("Save $29.96 on The Set. {link} Reply STOP to opt out", SET, CAD)
        self.assertTrue([p for p in got if "with the subscription" in p])
        self.assertEqual(sms.check("The Set is $129.99, was $139.95. {link} Reply STOP to opt out", SET, CAD), [])


class Email(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = self.ws = Path(self.tmp.name)
        (ws / "brands" / "zz" / "products").mkdir(parents=True)
        (ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(BANK)
        (ws / "run").mkdir()
        (ws / "run" / "run.json").write_text(json.dumps({"assignment": {"offer": "the-set", "offer_also": ["device"]}}))
        self.p = [mock.patch.object(m, "WORKSPACE", ws) for m in (offers, S)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_the_words_and_the_subject_lines_are_both_read(self):
        clean = {"headline": "H", "body": ["The Set, $129.99, was $139.95."], "offer": {"line": "The Device, $69.99."}}
        self.assertEqual(S.saving_check(clean, "zz", self.ws / "run"), [])
        self.assertTrue(S.saving_check(dict(clean, body=["Save $29.96 on The Set."]), "zz", self.ws / "run"))
        self.assertTrue(S.saving_check(dict(clean, subjects=[{"subject": "S", "preview": "$29.96 off The Set"}]),
                                       "zz", self.ws / "run"))

    def test_the_writer_is_told_before_it_writes(self):
        r = offers.writer_rules("zz", "the-set", ("device",), "sale-window", "2026-11-30")
        self.assertIn("a saving is stated only with its condition", r)
        self.assertIn("says it's with the subscription", r)
        self.assertIn("Prices and was-prices come only from the offer above", r)
        self.assertNotIn("a saving is stated", offers.writer_rules("zz", "device", (), "sale-window", "2026-11-30"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
