"""Pace and caption look resolved by format, with the reason (the logic layer, 2026-11-18): the per-format lists
were empty or two rows long, and pace() read its three rungs in the wrong order."""
import json
import sys
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parents[1] / "machine"
TOOL = MACHINE.parent
sys.path.insert(0, str(MACHINE))
import looks as LK  # noqa: E402
import run as R  # noqa: E402

DEFAULTS = json.loads((MACHINE / "defaults.json").read_text())
BANK = json.loads((TOOL / "looks" / "bank.json").read_text())


def controls(**pace):
    return {"pace": {**DEFAULTS["pace"], **pace}}


class PaceOrder(unittest.TestCase):
    """A value SET wins for every take; else the format's own; else the default. That is what the dial always said."""

    def test_a_set_value_wins_over_the_format_and_the_default(self):
        got = LK.pace("remedy", controls(value="tight"))
        self.assertEqual((got["name"], got["by"]), ("tight", "the run"))
        self.assertEqual(got["max_pause"], 0.25)

    def test_the_format_wins_over_the_default(self):
        got = LK.pace("remedy")
        self.assertEqual((got["name"], got["by"]), ("whole-breathing", "the format"))

    def test_a_format_with_no_row_takes_the_default(self):
        got = LK.pace("single-presenter")
        self.assertEqual((got["name"], got["by"]), ("whole", "the default"))
        self.assertEqual(LK.pace(None)["name"], "whole")

    def test_the_old_order_would_have_ignored_a_set_value(self):
        p = controls(value="tight")["pace"]
        old = (p.get("by_format") or {}).get("song-ad") or p.get("default") or p.get("value")
        self.assertEqual(old, "whole", "format, default, value: the set value was never reached")
        self.assertEqual(LK.pace("song-ad", controls(value="tight"))["name"], "tight")


class PaceByFormat(unittest.TestCase):
    def rows(self):
        return {k: v for k, v in DEFAULTS["pace"]["by_format"].items() if not k.startswith("_")}

    def test_the_list_is_filled_and_every_row_names_an_option_a_reason_and_its_source(self):
        rows = self.rows()
        self.assertGreaterEqual(len(rows), 4)
        for fmt, row in rows.items():
            self.assertIn(row["use"], DEFAULTS["pace"]["options"], fmt)
            self.assertTrue(row["why"].strip() and row["from"].strip(), fmt)
            self.assertEqual(row["status"], "draft")

    def test_no_format_ever_cuts_inside_a_take(self):
        """V15 holds for every format: a per-format pace changes the breath between lines, never a take's inside."""
        for fmt in self.rows():
            self.assertIsNone(LK.pace(fmt)["max_pause"], fmt)

    def test_each_format_breathes_as_its_source_says(self):
        self.assertLess(LK.pace("testimonial-montage")["breath_s"], LK.pace(None)["breath_s"])    # voices butt together
        self.assertGreater(LK.pace("remedy")["breath_s"], LK.pace(None)["breath_s"])              # breathing, step by step
        self.assertGreater(LK.pace("comedy-skit")["breath_s"], LK.pace(None)["breath_s"])         # let the joke land

    def test_the_call_carries_the_reason_and_the_doctrines_cutting_words(self):
        got = LK.pace_call("testimonial-montage")
        self.assertEqual(got["by"], "the format")
        self.assertIn("butt together", got["why"])
        doc = json.loads((TOOL.parent / "video-doctrine" / "frameworks.json").read_text())
        row = next(r for r in doc["shapes"]["rows"] if r["format"] == "testimonial-montage")
        self.assertEqual(got["cutting"], row["cutting"], "read from the doctrine, never restated")
        self.assertNotIn("cutting", LK.pace_call("a-format-the-doctrine-does-not-know"))

    def test_the_auto_cut_takes_the_formats_pace_unless_the_run_sets_one(self):
        c = R.controls_for(None)
        self.assertIsNone(c["pace"]["value"])
        self.assertIsNone(LK.pace("remedy", c)["max_pause"])


class CaptionLookByFormat(unittest.TestCase):
    def test_the_format_banks_own_id_finds_the_remedy_look(self):
        self.assertEqual(LK.pick_caption("remedy", "tiktok"), "edits-glow")
        self.assertEqual(LK.pick_caption("remedy-reel", "tiktok"), "edits-glow")

    def test_a_format_with_no_look_of_its_own_stays_native_to_its_app(self):
        """Not pinned by format: a piece made to look native to an app keeps that app's own look (V13)."""
        for fmt in ("single-presenter", "expert-consult", "micro-drama", "narrator-montage"):
            self.assertEqual(LK.pick_caption(fmt, "tiktok"), "tiktok-native", fmt)
            self.assertEqual(LK.pick_caption(fmt, "instagram-reels"), "tiktok-native", fmt)  # owner 2026-11-21

    def test_every_pick_is_a_look_in_the_bank(self):
        ids = {l["id"] for l in BANK["looks"]}
        for fmt, look in BANK["pick"]["by_format"].items():
            self.assertIn(look if isinstance(look, str) else look["look"], ids, fmt)

    def test_the_call_says_which_rung_answered_and_why(self):
        self.assertEqual(LK.caption_call("remedy", "tiktok")["by"], "the format")
        got = LK.caption_call("micro-drama", "tiktok")
        self.assertEqual((got["look"], got["by"]), ("tiktok-native", "the app"))
        got = LK.caption_call(None, None)
        self.assertEqual((got["look"], got["by"]), ("tiktok-native", "the default"))
        for fmt, app in (("remedy", None), ("x", "tiktok"), (None, None), ("song-ad", "instagram")):
            call = LK.caption_call(fmt, app)
            self.assertTrue(call["why"].strip())
            self.assertEqual(call["look"], LK.pick_caption(fmt, app), "the call is the pick, with its reason beside it")

    def test_a_look_the_brief_asks_for_in_words_rides_as_a_note(self):
        got = LK.caption_call("micro-drama", "tiktok", "big white capitals")
        self.assertEqual(got["look"], "tiktok-native")
        self.assertEqual(got["asked"], "big white capitals")


if __name__ == "__main__":
    unittest.main()
