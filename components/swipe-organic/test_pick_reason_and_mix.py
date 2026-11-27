"""The pick's reason travels, and the pick mix is a rule on the picker role (logic layer W1, 2026-11-18).

  - a hand pick keeps one line built from the card's own read (format, why it holds attention, what it is, the
    level its lane enters at) instead of a stock string, and nothing is asked of the person clicking;
  - every door that starts a teardown from a pick hands the run the pick's reason (--picked-why / --picked-by);
  - the split between the market's own feeds and adjacent markets and competitors is data on the picker role,
    counted on the week's queue, printed with every pick run and written on each pick; it changes which picks
    are taken only when the rule says it applies.

Runs in a temp workspace; never touches the live queue and never downloads.
    /usr/bin/python3 -m unittest test_pick_reason_and_mix"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import desklib as D
import briefs as B
import creator_picks as CP
import test_creator_picks as T


class AHandPickKeepsItsReason(unittest.TestCase):
    def test_the_line_is_built_from_what_the_sift_already_read_off_the_post(self):
        line = D.hand_pick_why({"format": "street interview", "why": "the answer flips the question",
                                "what": "a man asks strangers one thing", "lane": "entertainment"})
        self.assertTrue(line.startswith(D.HAND_PICK + " — "))
        self.assertIn("format: street interview", line)
        self.assertIn("why the feed kept it: the answer flips the question", line)
        self.assertIn("what it is: a man asks strangers one thing", line)
        self.assertIn("enters at unaware (entertainment lane)", line)

    def test_the_sifts_unread_is_never_printed_as_a_format(self):
        self.assertNotIn("format", D.hand_pick_why({"format": "unread", "kind": "?", "why": "x"}))
        self.assertIn("format: skit", D.hand_pick_why({"format": "unread", "kind": "skit"}))

    def test_the_sifts_kind_stands_in_when_it_named_no_format(self):
        self.assertIn("format: skit", D.hand_pick_why({"kind": "skit", "format": None}))

    def test_a_card_the_sift_has_not_read_says_only_that_it_was_picked_by_hand(self):
        self.assertEqual(D.hand_pick_why({}), D.HAND_PICK)
        self.assertEqual(D.hand_pick_why(None), D.HAND_PICK)
        self.assertEqual(D.hand_pick_why({"lane": "something-else"}), D.HAND_PICK)

    def test_one_awareness_map_for_the_feed_line_and_the_hand_pick(self):
        self.assertIs(B.LANE_AWARENESS, D.LANE_AWARENESS)


class ThePickReasonGoesIntoTheRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.calls = []

        def fake_run(cmd, *a, **k):
            self.calls.append(list(cmd))
            if cmd and cmd[0] == "yt-dlp":
                out = next(c for c in cmd if "video.%(ext)s" in str(c))
                Path(str(out).replace("%(ext)s", "mp4")).write_bytes(b"x")
            return subprocess.CompletedProcess(cmd, 1, "", "")
        for obj, name, val in ((B, "QUEUE", t / "queue"), (B, "MEDIA", t / "media"), (B, "ROUTE", None),
                               (B, "product_for", lambda brand, core: None), (B, "sub_stem", lambda feed: None),
                               (B.subprocess, "run", fake_run)):
            p = mock.patch.object(obj, name, val)
            p.start()
            self.addCleanup(p.stop)
        (t / "queue").mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.feed = {"id": "tb--core-a", "brand": "tb", "core": "core-a", "sub": None, "title": "A"}
        self.card = {"key": "tiktok:1", "url": "https://example.test/v/1", "author": "x", "caption": "c", "cover": None,
                     "views": 900_000, "sent": 41, "lane": "entertainment", "format": "street interview",
                     "why": "the answer flips the question", "what": "a man asks strangers one thing"}

    def machine_call(self):
        return next(c for c in self.calls if any(str(x).endswith("run.py") for x in c))

    def test_the_rules_own_reason_is_handed_to_the_teardown(self):
        why = "top untouched entertainment post in this feed — sent 41 times per 1K views"
        B.tear((self.feed, self.card, why))
        cmd = self.machine_call()
        self.assertEqual(cmd[cmd.index("--picked-why") + 1], why)
        self.assertEqual(cmd[cmd.index("--picked-by") + 1], "the feed's pick rule")
        rec = json.loads(next((Path(self.tmp.name) / "queue").glob("*.json")).read_text())
        self.assertEqual(rec["picked_why"], why)                      # the queue card keeps it as before

    def test_a_product_the_feeds_map_chose_says_so(self):
        with mock.patch.object(B, "product_for", lambda brand, core: "the-thing"):
            B.tear((self.feed, self.card, "top untouched entertainment post in this feed — 900,000 views"))
        cmd = self.machine_call()
        self.assertEqual(cmd[cmd.index("--product") + 1], "the-thing")
        self.assertIn("product map", cmd[cmd.index("--product-why") + 1])

    def test_a_hand_pick_hands_over_the_cards_own_read_and_says_a_person_picked_it(self):
        B.tear((self.feed, self.card, D.hand_pick_why(self.card)))
        cmd = self.machine_call()
        self.assertIn("why the feed kept it: the answer flips the question", cmd[cmd.index("--picked-why") + 1])
        self.assertEqual(cmd[cmd.index("--picked-by") + 1], "a person on the feed page")


class ThePickMix(unittest.TestCase):
    setUp, tearDown = T.Door.setUp, T.Door.tearDown
    run_, queue, items_ = T.Door.run_, T.Door.queue, T.Door.items_

    def role(self, **mix):
        rf = self.ws / "strategist.json"
        d = {"filled_by": "default", "command": None, "owner_yes": True}
        if mix:
            d["mix"] = mix
        rf.write_text(json.dumps(d))
        return mock.patch.object(CP, "ROLE_FILE", rf)

    def test_the_committed_rule_is_the_default_offered_and_is_not_switched_on(self):
        rule = CP.mix_rule(json.loads((Path(CP.__file__).resolve().parent / "strategist.json").read_text()))
        self.assertEqual(rule, (4, 1, False))

    def test_a_role_with_no_rule_or_a_broken_one_has_no_mix(self):
        self.assertIsNone(CP.mix_rule({}))
        self.assertIsNone(CP.mix_rule({"mix": {"market_now": "four", "adjacent": 1}}))
        self.assertIsNone(CP.mix_rule({"mix": {"market_now": 0, "adjacent": 0}}))
        self.assertEqual(CP.mix_rule({"mix": {"market_now": 4, "adjacent": 1, "applies": "yes"}}), (4, 1, False))

    def test_not_switched_on_it_is_printed_and_written_and_changes_no_pick(self):
        with self.role():
            self.run_("pick", "--brand", "tb")
        plain = self.items_()
        T.Door.tearDown(self); T.Door.setUp(self)
        with self.role(market_now=4, adjacent=1, applies=False):
            out = self.run_("pick", "--brand", "tb")
        self.assertEqual(self.items_(), plain)                         # the same picks, in the same order
        self.assertIn("pick mix 4 in 5 from the market's own feeds, 1 in 5 from adjacent markets and competitors", out)
        self.assertIn("printed only", out)
        self.assertTrue(all(r["mix"] == {"side": "adjacent", "rule": "4:1", "applies": False} for r in self.queue()))

    def test_switched_on_this_picker_takes_only_the_adjacent_sides_share(self):
        with self.role(market_now=4, adjacent=1, applies=True):
            out = self.run_("pick", "--brand", "tb")
            self.assertEqual(len(self.queue()), 1)                     # a week may start on either side: one, no more
            self.assertIn("applies", out)
            again = self.run_("pick", "--brand", "tb")
            self.assertEqual(len(self.queue()), 1)
            self.assertIn("the adjacent side of the mix is full for this week", again)

    def test_a_card_added_by_hand_keeps_the_cards_own_read_not_a_stock_line(self):
        cards = {"tb--core-a": [T.card("tiktok:1", 9_000_000, kind="street interview", what="a man asks strangers one thing")]}
        with mock.patch.object(CP.D, "cards", lambda f: cards.get(f, [])):
            self.run_("add", "--brand", "tb", "--feed", "tb--core-a", "--item", "tiktok:1")
        why = self.queue()[0]["why"]
        self.assertTrue(why.startswith(D.HAND_PICK))
        self.assertIn("format: street interview", why)
        self.assertIn("what it is: a man asks strangers one thing", why)

    def test_a_reason_given_with_the_add_is_kept_as_given(self):
        self.run_("add", "--brand", "tb", "--feed", "tb--core-a", "--item", "tiktok:1", "--why", "the owner's own reason")
        self.assertEqual(self.queue()[0]["why"], "the owner's own reason")

    def test_the_weeks_count_reads_each_picks_own_source(self):
        week = CP.week_of()
        rows = [{"swipe_id": f"s{i}", "week": week, "state": "picked", "pick_source": src}
                for i, src in enumerate(["my-feeds"] * 8 + ["trendtrack", "hand"])] \
            + [{"swipe_id": "old", "week": "1999-W01", "state": "picked", "pick_source": "trendtrack"},
               {"swipe_id": "gone", "week": week, "state": "dropped", "pick_source": "tiktok-shop"}]
        with mock.patch.object(CP, "items", lambda brand: rows):
            got = CP.mix_read("tb", week, {"mix": {"market_now": 4, "adjacent": 1, "applies": True}})
        self.assertEqual((got["market_now"], got["adjacent"], got["room"]), (8, 1, 1))   # 8 feed picks allow 2 adjacent


if __name__ == "__main__":
    unittest.main()
