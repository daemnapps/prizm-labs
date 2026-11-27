"""The brand's own mix (2026-11-04): a promo email carries the products the bank's storefront-order note mixes,
for every audience; the price check takes each member's own prices, and never a line the bank keeps off email.
No model, no network, no key."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brief  # noqa: E402
import offers  # noqa: E402
import simple_email as S  # noqa: E402

BANK = """# Bank

## the-set — The Set
_lane: b_  ·  _hero: paid_
- Price: **$129.99**, was $179.99

## device — The Device
_lane: a_  ·  _hero: paid_
- Price: **$69.99**, was $99.99
- Funnel offer: **DEVICE starting at $46**. **Funnel only**: never in an email, an SMS or on the storefront.
"""
SLOT = {"id": "nov-01", "offer": "the-set", "offer_mix": ["the-set", "device"], "source": "s.md",
        "date":"2026-11-20", "hour":13, "local":True,
        "segment": "Core | Lead", "type": "sale-window", "product": "the-set"}


class Mix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = self.ws = Path(self.tmp.name)
        (ws / "brands" / "zz" / "products").mkdir(parents=True)
        (ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(BANK)
        self.p = [mock.patch.object(m, "WORKSPACE", ws) for m in (offers, S, brief)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_the_lane_rule_yields_to_the_brands_mix(self):
        self.assertEqual(brief.offer_for(SLOT, "zz", "a"), "the-set")             # the set's lane is b
        self.assertEqual(brief.offer_for(dict(SLOT, offer_mix=None), "zz", "a"), "none")

    def test_the_writer_is_handed_the_rest_of_the_mix(self):
        argv = brief.chain_argv(SLOT, "zz", avatar="a")
        self.assertEqual(argv[argv.index("--offer") + 1], "the-set")
        self.assertEqual(argv[argv.index("--offer-also") + 1], "device")
        self.assertNotIn("--offer-also", brief.chain_argv(dict(SLOT, offer_mix=None), "zz", avatar="b"))

    def test_a_mix_of_one_is_still_the_brands_mix_in_the_chain(self):
        # December 2026: a slot whose mix is just its own offer reached the chain with no --offer-also, and the chain
        # applied the lane rule that brief.offer_for had already yielded: three sends refused before any writing
        one = dict(SLOT, offer_mix=["the-set"])
        argv = brief.chain_argv(one, "zz", avatar="a")
        self.assertEqual(argv[argv.index("--offer") + 1], "the-set")
        self.assertIn("--offer-mix", argv)
        self.assertNotIn("--offer-also", argv)
        self.assertNotIn("--offer-mix", brief.chain_argv(dict(SLOT, offer_mix=None), "zz", avatar="b"))
        self.assertIsNone(offers.refuse("zz", "the-set", None, "2026-12-01"))   # what the chain asks under --offer-mix
        self.assertTrue(offers.refuse("zz", "the-set", "a", "2026-12-01"))      # and what it asked before

    def _price(self, words):
        run = self.ws / "run"
        run.mkdir(exist_ok=True)
        (run / "run.json").write_text(json.dumps({"assignment": {"offer": "the-set", "offer_also": ["device"]}}))
        with mock.patch.object(S, "finished_text", return_value=words):
            return S.price_check({}, "zz", run)

    def test_every_price_of_the_mix_passes_and_the_funnel_line_never(self):
        self.assertEqual(self._price("The Set $129.99, or the Device at $69.99."), [])
        self.assertTrue(self._price("The Device starting at $46."))


class OneSendOfMany(unittest.TestCase):
    def test_an_email_finds_its_own_send_among_same_angle_sends_on_its_day(self):
        import reviewed_plan as RP
        ang = "the same standing angle"
        mk = lambda i, ch="email": {"id": f"nov-{i:02d}", "date": "2026-11-30", "channel": ch, "segment": "S",
                                    "variants": [{"avatar": "a", "angle": ang}]}
        slots = [mk(42), mk(43), mk(44), mk(50, "sms")]
        with mock.patch.object(RP, "reviewed", side_effect=lambda d, sl: sl):
            got = S._send_by_angle(Path("/x/runs/marketing-calendar/zz-brand/2026-11"), slots,
                                   {"date": "2026-11-30", "angle": ang}, "zz-brand-nov-43--a", RP)
        self.assertEqual(got["id"], "nov-43")


if __name__ == "__main__":
    unittest.main(verbosity=2)
