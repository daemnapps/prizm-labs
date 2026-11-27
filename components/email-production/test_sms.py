"""SMS words (2026-11-03): the prompt is filled from the slot and the offer's own section, and every text is
checked in code before a person sees it. No model is called; no SMS platform is touched."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sms  # noqa: E402

BANK = """# Offer bank

## tube — The Tube
- Price: **$29.00**

---

# Ruled by a human

### holiday-sale — The holiday offer
| The 3-pack | **$57** — starting at $19 a tube |
No code necessary.

### rules — Standing rules
- Never invent an offer.
"""
CAD = {"length": {"max_chars": 160, "link_chars": 25, "opt_out": "Reply STOP to opt out"},
       "beat_meaning": {"open": "the sale opens"}, "audience": "SMS-consented members only"}
SLOT = {"id": "nov-21", "date": "2026-11-20", "channel": "sms", "sms_beat": "open", "offer": "holiday-sale",
        "occasion": "holiday", "segments": ["Core | Lead"], "why": "the open"}


class Sms(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "brands" / "zz" / "products").mkdir(parents=True)
        (self.ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(BANK)
        self.p = mock.patch.object(sms, "WORKSPACE", self.ws)
        self.p.start()
        self.sec = sms.offer_section("zz", "holiday-sale")

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_the_offer_section_is_read_as_written(self):
        self.assertIn("starting at $19 a tube", self.sec)
        self.assertNotIn("Standing rules", self.sec)
        self.assertIn("$29.00", sms.offer_section("zz", "tube"))

    def test_a_good_text_passes(self):
        msg = "The sale is on: 3 for the price of 2, starting at $19 a tube. No code necessary. {link} Reply STOP to opt out"
        self.assertEqual(sms.check(msg, self.sec, CAD), [])

    def test_every_rule_holds_a_bad_text(self):
        msg = "SALE! Use code SAVE10 for $15 off at https://example.test today only " + "x" * 120
        got = " | ".join(sms.check(msg, self.sec, CAD))
        for want in ("the limit is 160", "the link must appear once", "a real URL", "no opt-out line",
                     "prices the offer section does not state: $15", "mentions a code"):
            self.assertIn(want, got)

    def test_the_prompt_carries_the_slot_and_the_offer_section(self):
        text, sec = sms.fill(sms.latest_prompt().read_text(), SLOT, "zz", CAD)
        self.assertEqual(sec, self.sec)
        for want in ("`holiday-sale`", "starting at $19 a tube", "2026-11-20", "Core | Lead",
                     "SMS-consented members only", "`{link}`", "Reply STOP to opt out", "160 characters"):
            self.assertIn(want, text)
        self.assertNotIn("{offer_section}", text)

    def test_a_text_is_written_beside_its_prompt_and_never_sent(self):
        msg = "The sale is on: starting at $19 a tube. {link} Reply STOP to opt out"   # SLOT is the open beat
        label, rec, problems = sms.write_one(SLOT, "zz", CAD, sms.latest_prompt(), call=lambda p: msg)
        d = self.ws / "runs" / "email-production" / "zz" / label
        self.assertEqual(problems, [])
        self.assertEqual(json.loads((d / "sms.json").read_text())["state"], "ready for review")
        self.assertFalse(rec["sent"])
        self.assertTrue((d / "prompt-sent.md").is_file())


class Beats(unittest.TestCase):
    def test_a_text_says_its_own_beat_only(self):
        cad = {"length": {"max_chars": 160, "link_chars": 25, "opt_out": "Reply STOP to opt out"}}
        sec = "starting at $19 a tube"
        msg = "Early access is open: starting at $19 a tube. {link} Reply STOP to opt out"
        self.assertEqual(sms.check(msg, sec, cad, {"sms_beat": "early-access"}), [])
        self.assertTrue(any("early access" in p for p in sms.check(msg, sec, cad, {"sms_beat": "open"})))
        last = "Today only: starting at $19 a tube. {link} Reply STOP to opt out"
        self.assertTrue(any("last day" in p for p in sms.check(last, sec, cad, {"sms_beat": "peak"})))
        self.assertEqual(sms.check(last, sec, cad, {"sms_beat": "last-chance"}), [])
        held = "Black Friday is here and your discount is waiting: starting at $19 a tube. {link} Reply STOP to opt out"
        self.assertTrue(any("held for the reader" in p for p in sms.check(held, sec + " No code necessary.", cad, {"sms_beat": "peak"})))
        ask = "The sale is on: starting at $19 a tube. Reply YES for yours. {link} Reply STOP to opt out"
        self.assertTrue(any("reply" in p for p in sms.check(ask, sec, cad, {"sms_beat": "open", "sms_job": "engagement"})))
        self.assertEqual(sms.check(ask, sec, cad, {"sms_beat": "open", "sms_job": "reply", "reply_keyword": "YES"}), [])


class FunnelLineStaysOnTheFunnel(unittest.TestCase):
    def test_a_funnel_only_price_never_passes_on_another_offer(self):
        # a bank where one product's funnel line ("starting at $46") is funnel-only and the sale's offer is a set
        bank = ("# Bank\n\n## device — The Device\n- Price: **$69.99**\n- Funnel offer: **DEVICE starting at $46**. "
                "**Funnel only**: never in an email, an SMS or on the storefront.\n\n"
                "## the-set — The Set\n- Price: **$129.99**, was $179.99\n")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "brands" / "zz" / "products").mkdir(parents=True)
            (ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(bank)
            with mock.patch.object(sms, "WORKSPACE", ws):
                sec = sms.offer_section("zz", "the-set")
        cad = {"length": {"max_chars": 160, "link_chars": 25, "opt_out": "Reply STOP to opt out"}}
        bad = "Black Friday is on: DEVICE starting at $46. {link} Reply STOP to opt out"
        good = "Black Friday is on: The Set is $129.99, was $179.99. {link} Reply STOP to opt out"
        self.assertTrue(any("$46" in p for p in sms.check(bad, sec, cad, {"sms_beat": "open"})))
        self.assertEqual(sms.check(good, sec, cad, {"sms_beat": "open"}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
