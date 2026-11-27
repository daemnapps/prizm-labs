"""LD-104 (no invented facts), 2026-11-04: the writer may not put in a number, timeframe, guarantee term or named
quote that is not in the brand's files. Real case from the Nov 3-4 run: a send said "464 of our 625 men bought
again" where the measured repeat rate is 14.3%; 10 of 13 emails were held or fixed for invented specifics
(runs/email-production/notes/2026-11-04-november-email-audit.md, fact 3).

The rule rides in `offers.writer_rules`, which every writing step receives inside {offer_rule}. These tests prove
it is there on every kind of send, says what it must, names no brand, and reaches every writing step's prompt.
No model, no key, no brand file read."""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import email_line  # noqa: E402
import offers  # noqa: E402

BANK = """# Bank

## sale — The sale
- Price: **$57**

## Guarantees

### guarantee — exact wording
> 60 days. If it does not work, every penny back.
"""

# Every stage that writes words the reader sees. Stage 6 (expansion) writes the body for organic-lane sends.
WRITING_STAGES = ("stage3", "stage4", "stage5", "stage6", "stage7", "stage8")


class TheRuleIsAlwaysHanded(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        for b in ("zz", "yy"):
            (self.ws / "brands" / b / "products").mkdir(parents=True)
        (self.ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(BANK)   # yy has no bank at all
        self.p = mock.patch.object(offers, "WORKSPACE", self.ws)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def rule(self, r):
        """The no-invention paragraph out of everything the writer is handed."""
        m = re.search(r"\*\*Nothing is invented\.\*\*.*?(?=\n\n\*\*|\Z)", r, re.S)
        self.assertIsNotNone(m, "the no-invention rule is missing from writer_rules:\n" + r)
        return m.group(0)

    def test_every_kind_of_send_carries_it(self):
        self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))   # an offer send
        self.rule(offers.writer_rules("zz", "none", (), "routine"))                     # a send with no offer
        self.rule(offers.writer_rules("yy", None))                                      # a brand with no bank

    def test_it_names_the_four_things_that_were_invented(self):
        r = self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))
        for what in ("number", "timeframe", "guarantee term", "named quote", "not in the brand's files"):
            self.assertIn(what, r)

    def test_a_number_written_out_in_words_is_still_a_number(self):
        # "three pumps", "the twelve hours after the shave": both were invented in words, not digits
        r = self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))
        self.assertIn("written in words", r)

    def test_a_count_is_never_rounded_or_made_from_a_rate(self):
        # "1,350 five-star reviews" where the file says 1,132; "464 of 625" from a 14.3% rate
        r = self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))
        self.assertIn("exactly as the file states it", r)
        self.assertIn("never rounded up", r)
        self.assertIn("never worked out from a rate", r)

    def test_a_quote_carries_only_the_credit_its_file_gives(self):
        r = self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))
        self.assertIn("word for word", r)
        self.assertIn("credited as that file credits it", r)

    def test_it_says_what_to_do_instead(self):
        r = self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))
        self.assertIn("write the sentence without it", r)
        self.assertIn("[UNFILLED:", r)

    def test_it_names_no_brand(self):
        # the same words for every brand: brand context enters only from the brand's own files (repo rule 7)
        self.assertEqual(self.rule(offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30")),
                         self.rule(offers.writer_rules("yy", None)))

    def test_the_other_rules_still_ride_beside_it(self):
        r = offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30")
        self.assertIn("The guarantee, if it appears, is one of these lines, word for word", r)
        self.assertIn("The only deadline this send may state is 2026-11-30", r)


class EveryWritingStepReceivesIt(unittest.TestCase):
    """writer_rules reaches a stage only if the stage's prompt has an {offer_rule} slot and the line fills it."""
    src = (HERE / "email_line.py").read_text()

    def test_writer_rules_is_added_to_the_offer_rule(self):
        self.assertRegex(self.src, r"offer_rule \+= .*OFFERS\.writer_rules\(")

    def test_every_writing_prompt_has_the_slot(self):
        for stage in WRITING_STAGES:
            with self.subTest(stage=stage):
                self.assertIn("{offer_rule}", email_line.latest_prompt(stage).read_text())

    def test_every_writing_stage_is_handed_it(self):
        for stage in WRITING_STAGES:
            with self.subTest(stage=stage):
                call = re.search(r'run_stage\("%s",(.*?)\); save\(\)' % stage, self.src, re.S)
                self.assertIsNotNone(call, f"no run_stage call for {stage}")
                self.assertIn("offer_rule=offer_rule", call.group(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
