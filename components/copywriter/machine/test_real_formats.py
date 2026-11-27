#!/usr/bin/env python3
"""Tests for the formats from our own winning ads and the words filled into them. No model, no network: the strip
and the fill are answered by stubs, and every file is written under a temp workspace."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import real_formats as RF  # noqa: E402

PULL = {"rule": "top 25 by spend + top 25 by lowest CPA", "window": {}, "copy": [
    {"slot": "primary", "text": "You've already blown $150+ on face washes that didn't clear your acne. There's a reason why.",
     "spend": 15837, "purchases": 198, "value": 1, "why": ["spend"], "ads": [{"ad_id": "1", "ad_name": "Blown"}]},
    {"slot": "primary", "text": "HOLIDAY SALE! Get it for $39 today.", "spend": 9000, "purchases": 200, "value": 1,
     "why": ["cpa"], "ads": [{"ad_id": "2", "ad_name": "Holiday"}]},
    {"slot": "headlines", "text": "Women are OBSESSED with this hack", "spend": 5000, "purchases": 80, "value": 1,
     "why": ["spend"], "ads": [{"ad_id": "3", "ad_name": "Obsessed"}]},
    {"slot": "descriptions", "text": "No subscription. No catch.", "spend": 4000, "purchases": 60, "value": 1,
     "why": ["spend"], "ads": [{"ad_id": "4", "ad_name": "No catch"}]}]}

STRIPPED = {
    "primary": [
        {"format": "You've already blown [MONEY SPENT] on [WHAT THEY TRIED] that didn't [FIX IT]. There's a reason why.",
         "awareness": "problem-aware", "offer": "no", "season": "", "structure": "money wasted, hidden reason"},
        {"format": "HOLIDAY SALE! Get it for [PRICE] today.", "awareness": "most-aware", "offer": "yes",
         "season": "holiday", "structure": "sale"}],
    "headlines": [{"format": "[WHO] are OBSESSED with this [PROBLEM] hack", "awareness": "solution-aware", "offer": "no"}],
    "descriptions": [{"format": "No subscription. No catch.", "awareness": "most-aware", "offer": "no"}]}


class Bank(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "components").mkdir()
        (self.ws / "brands").mkdir()
        p = self.ws / "runs/copywriter/testbrand/meta-copy/2026-10-02-db"
        p.mkdir(parents=True)
        (p / "copy.json").write_text(json.dumps(PULL))

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def build(self, stripped=STRIPPED):
        def ask(text):
            slot = "primary" if "(primary text)" in text else "headlines" if "(headlines)" in text else "descriptions"
            return "```json\n" + json.dumps(stripped[slot]) + "\n```"
        return RF.build("testbrand", ask=ask, ws=self.ws, say=lambda *_: None)

    def test_every_real_ad_becomes_a_format_with_its_numbers(self):
        b = self.build()
        self.assertEqual(len(b["formats"]), 4)
        e = b["formats"][0]
        self.assertEqual(e["id"], "copyformat_testbrand_primary_01")
        self.assertEqual(e["name"], "Blown")
        self.assertEqual(e["numbers"]["cpa"], round(15837 / 198, 2))
        self.assertEqual(e["status"], "draft")
        self.assertTrue((self.ws / "runs/copywriter/testbrand/copy-formats/formats.md").is_file())

    def test_a_format_that_paraphrases_the_ad_is_broken(self):
        bad = json.loads(json.dumps(STRIPPED))
        bad["primary"][0]["format"] = "You spent [MONEY] on [STUFF]. Here is why."
        b = self.build(bad)
        self.assertEqual(b["formats"][0]["state"], "broken")
        self.assertEqual(RF.usable("testbrand", "primary", ws=self.ws)[0]["name"], "Holiday")

    def test_pick_keeps_offers_and_seasons_off_a_non_promotion(self):
        self.build()
        levels = {"most-aware": 1, "product-aware": 2, "solution-aware": 3, "problem-aware": 4, "unaware": 5}
        got = RF.pick("testbrand", "primary", awareness="problem-aware", promo=False, ws=self.ws, levels=levels)
        self.assertEqual([e["name"] for e in got], ["Blown"])

    def test_fits_is_the_fixed_words_in_order(self):
        f = "You've already blown [MONEY SPENT] on [WHAT THEY TRIED] that didn't [FIX IT]. There's a reason why."
        self.assertTrue(RF.fits(f, "You've already blown $200 on concealers that didn't hide a thing. There's a reason why."))
        self.assertFalse(RF.fits(f, "You've spent $200 on concealers that never worked. Here's why."))


class Keeps(unittest.TestCase):
    def test_changing_an_element_keeps_the_format(self):
        f = "That's not just [PROBLEM], you have parasites in your face. They're called Demodex mites.\n\nYour cleanser doesn't reach them."
        self.assertTrue(RF.keeps(f, "That's not just razor bumps, you have parasites in your neck. They're called Demodex mites.\n\nYour cleanser doesn't reach them."))

    def test_a_rewrite_or_a_dropped_paragraph_does_not(self):
        f = "That's not just [PROBLEM], you have parasites in your face. They're called Demodex mites.\n\nYour cleanser doesn't reach them."
        self.assertFalse(RF.keeps(f, "Razor bumps are not your fault. A brush fixes it in a week, guaranteed for life."))
        self.assertFalse(RF.keeps(f, "That's not just bumps, you have parasites in your face. They're called Demodex mites."))


class FillCheck(unittest.TestCase):
    def test_a_line_off_its_format_or_with_a_blank_left_is_named(self):
        import format_copy as FC
        lists = {"primary": [{"id": "p1", "format": "You've already blown [MONEY] on [WHAT]. There's a reason why."}],
                 "headlines": [{"id": "h1", "format": "[WHO] are OBSESSED with this [PROBLEM] hack"}],
                 "descriptions": []}
        got = {"primary": [{"format": "p1", "text": "You've already blown years on [WHAT]. There's a reason why."},
                           {"format": "p9", "text": "Something else."}],
               "headlines": [{"format": "h1", "text": "Women are OBSESSED with this dark spot hack"}]}
        import copy_set as CS
        old = CS.offer_text
        CS.offer_text = lambda b, p: ("", "")
        try:
            c = FC.check(got, lists, promo=False, awareness=None, brand="b", product="p", cited={})
        finally:
            CS.offer_text = old
        self.assertIn("a [BLANK] was left unfilled", c["primary"][0][1])
        self.assertIn("format 'p9' is not one it was handed", c["primary"][1][1])
        self.assertTrue(any("characters" in p for p in c["headlines"][0][1]))    # 43 > 40


class StoryCheck(unittest.TestCase):
    def test_a_line_telling_another_ads_story_is_named(self):
        import format_copy as FC
        checked = {"primary": [({"format": "p1", "text": "My grandmother pulled turmeric in Thailand."}, []),
                               ({"format": "p2", "text": "Women who tanned in the 80s are OBSESSED."}, [])],
                   "headlines": [], "descriptions": []}
        ask = lambda q: '[{"n": 1, "fits": false, "why": "a Thai grandmother, not the 80s woman"}, {"n": 2, "fits": true}]'
        out = FC.story_check(checked, {"who": "a woman who tanned in the 80s"}, ask)
        self.assertIn("not this ad's story", out["primary"][0][1][0])
        self.assertEqual(out["primary"][1][1], [])

    def test_a_check_that_cannot_run_never_passes_a_line(self):
        import format_copy as FC
        checked = {"primary": [({"format": "p1", "text": "x"}, [])], "headlines": [], "descriptions": []}
        out = FC.story_check(checked, {"who": "her"}, lambda q: "no json here")
        self.assertTrue(out["primary"][0][1])


if __name__ == "__main__":
    unittest.main()
