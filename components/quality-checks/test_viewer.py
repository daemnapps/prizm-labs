"""The viewer check's scoring and routing — no network (python3 test_viewer.py)."""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from marketing_chain_checks import viewer as V



def p(n, stop="no", left="1", ad="no", tap="no", felt="", friend=""):
    return {"n": n, "stop": stop, "left_at": left, "ad_at": ad, "tap": tap, "felt": felt, "text_friend": friend}


class Viewer(unittest.TestCase):
    def test_clocked_together_then_left_goes_back_to_the_giveaway(self):
        # the shape of the first real trial: all stop, all clock it as an ad at 0:08,
        # two of three leave at 0:12, before the offer at 0:21
        a = [[p(1), p(2, "yes", "end", "8", "yes"), p(3)], [p(1), p(2, "yes", "12", "8", "yes"), p(3)],
             [p(1), p(2, "yes", "12", "8", "yes"), p(3)]]
        at = [2, 2, 2]
        sc = V.score(a, at, 25, 21)
        self.assertFalse(sc["passed"])
        self.assertFalse(sc["checks"]["stays_to_offer"]["passed"])
        self.assertEqual(V.route(sc, 25), {"fix_at": "giveaway", "at": "0:08"})

    def test_no_stop_goes_to_openings(self):
        a = [[p(1), p(2, stop="yes", left="5")] for _ in range(3)]
        sc = V.score(a, [1, 1, 1], 20, 15)
        self.assertEqual(V.route(sc, 20)["fix_at"], "openings")

    def test_must_beat_the_real_posts(self):
        a = [[p(1, "yes", "end", tap="yes"), p(2, "yes", "end")] for _ in range(3)]
        sc = V.score(a, [1, 1, 1], 20, 15)
        self.assertFalse(sc["checks"]["beats_feed"]["passed"])     # 100% vs 100%

    def test_a_pass(self):
        a = [[p(1, "yes", "end", "18", "yes"), p(2)] for _ in range(3)]
        sc = V.score(a, [1, 1, 1], 20, 15)
        self.assertTrue(sc["passed"])
        self.assertEqual(V.route(sc, 20)["fix_at"], None)

    def test_stayed_but_no_tap_goes_to_close(self):
        a = [[p(1, "yes", "end"), p(2)] for _ in range(3)]
        self.assertEqual(V.route(V.score(a, [1, 1, 1], 20, 15), 20)["fix_at"], "close")

    def test_not_for_me_goes_to_audience(self):
        a = [[p(1, "yes", "3", felt="not for me, I'm not a dad"), p(2)] for _ in range(3)]
        self.assertEqual(V.route(V.score(a, [1, 1, 1], 20, 15), 20)["fix_at"], "audience")

    def test_a_still_is_not_scored_on_watch_time(self):
        a = [[p(1, "yes", "2", tap="yes"), p(2)] for _ in range(3)]
        sc = V.score(a, [1, 1, 1], 0, None)
        self.assertTrue(sc["checks"]["stays_to_offer"]["passed"])
        self.assertTrue(sc["passed"])

    def test_the_viewer_prompt_never_names_a_score(self):
        t = V.newest("viewer-check").read_text().lower()
        for w in ("score", "pass", "fail", "rate this"):
            self.assertNotIn(w, t)

    def test_predicted_numbers_from_the_viewers_seconds(self):
        a = [[p(1, "yes", "end", tap="yes"), p(2)], [p(1, "yes", "10"), p(2)], [p(1, "no", "1"), p(2)]]
        pr = V.score(a, [1, 1, 1], 20, 15)["predicted"]
        self.assertEqual(pr["hook_rate"], 0.67)
        self.assertEqual(pr["avg_watch_s"], round((20 + 10 + 1) / 3, 1))
        self.assertEqual(pr["reach_offer"], 0.33)
        self.assertEqual(pr["retention"][0], 1.0)
        self.assertEqual(pr["retention"][20], 0.33)

    def test_the_stamp_follows_the_brief_not_its_stamp_lines(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        brief = 'Brief\n```json\n{"scenes": [1]}\n```\n'
        (d / "viewer-check").mkdir()
        (d / "viewer-check" / "STAMP.json").write_text(json.dumps({"brief": V.brief_key(brief), "passed": True}))
        self.assertTrue(V.stamp_of(d, brief + "DAMON READ: APPROVED\n"))          # a stamp line changes nothing
        self.assertIsNone(V.stamp_of(d, brief.replace("[1]", "[2]")))              # the words changed: check again

    def test_damons_v_passes_it(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        V.approve(d, "some brief")
        ok, why, _ = V.worth_making(d, "b", "a", "some brief")
        self.assertTrue(ok)

    def test_v2_belief_and_pitch(self):
        def q(n, believe="yes", pitch="no", fake="no", got="yes", do="save"):
            d = p(n, "yes", "end", tap="yes"); d.update(believe=believe, pitch=pitch, fake=fake, got_it=got, do=do, for_me="yes"); return d
        a = [[q(1, believe="not sure", pitch="yes"), p(2)] for _ in range(5)]
        sc = V.score(a, [1] * 5, 20, 15, muted=[1, 3])
        self.assertFalse(sc["checks"]["believe"]["passed"])
        self.assertFalse(sc["checks"]["not_a_pitch"]["passed"])
        self.assertTrue(sc["checks"]["works_muted"]["passed"])
        self.assertEqual(V.route(sc, 20)["fix_at"], "words")
        self.assertEqual(sc["predicted"]["save_rate"], 1.0)
        b = [[q(1, believe="no"), p(2)] for _ in range(5)]
        self.assertEqual(V.route(V.score(b, [1] * 5, 20, 15), 20)["fix_at"], "proof")

    def test_the_offer_is_allowed_to_sell(self):
        cut = {"offer_at": 21, "lines": ["0:00–0:02  a woman at a mirror", "0:18–0:21  text: nothing else ever cleared it", "0:21–0:25  Text: THE PRODUCT — $49.99 / 90 days. If your skin doesn't transform, full refund."]}
        ow = V.offer_words(cut)
        self.assertTrue(V.is_offer("If your skin doesn't transform, full refund.", ow))
        self.assertFalse(V.is_offer("nothing else ever cleared it for me", ow))
        def q(n, line):
            d = p(n, "yes", "end", tap="yes"); d.update(believe="yes", pitch="yes", pitch_line=line, fake="no", got_it="yes", do="save", for_me="yes"); return d
        a = [[q(1, "90 days. If your skin doesn't transform, full refund."), p(2)] for _ in range(5)]
        self.assertTrue(V.score(a, [1] * 5, 25, 21, offer_set=ow)["checks"]["not_a_pitch"]["passed"])
        b = [[q(1, "nothing else ever cleared it for me"), p(2)] for _ in range(5)]
        self.assertFalse(V.score(b, [1] * 5, 25, 21, offer_set=ow)["checks"]["not_a_pitch"]["passed"])

    def test_the_rewrite_keeps_offer_lines_word_for_word(self):
        brief = 'Frame 10\nOn screen: "PRODUCT™ — $49.99 / 90 days. full refund."\nFrame 9 text: old line\n'
        good = ('=== BRIEF ===\nFrame 10\nOn screen: "PRODUCT™ — $49.99 / 90 days. full refund."\nFrame 9 text: new line\n=== END BRIEF ===\n'
                '=== CHANGES ===\n{"changes":[{"where":"Frame 9","was":"old line","now":"new line"}],"open":[]}\n=== END CHANGES ===')
        t, ch = V.fix(brief, {"fix_at": "proof", "notes": "n"}, "b", "a", caller=lambda *x: good)
        self.assertIn("new line", t)
        self.assertEqual(ch["changes"][0]["now"], "new line")
        with self.assertRaises(ValueError):
            V.fix(brief, {"fix_at": "proof", "notes": "n"}, "b", "a", caller=lambda *x: good.replace("PRODUCT™ — $49.99", "PRODUCT — $49.99"))

    def test_the_rewrite_quotes_only_real_data(self):
        brief = 'Frame 9 text: "old line here and more"\nOn screen: "PRODUCT™ — $49.99 / 90 days."\n'
        def out(q):
            return (f'=== BRIEF ===\nFrame 9 text: "{q}"\nOn screen: "PRODUCT™ — $49.99 / 90 days."\n=== END BRIEF ===\n'
                    f'=== CHANGES ===\n{{"changes":[{{"where":"Frame 9","was":"old","now":"\\"{q}\\""}}]}}\n=== END CHANGES ===')
        V._real_text = lambda b, a: "very bad acne as a teen right now."
        for invented in ("it looks simple, $50 is a lot", "worth the investment because they see real differences"):
            with self.assertRaises(ValueError):
                V.fix(brief, {"fix_at": "proof", "notes": "n"}, "b", "a", caller=lambda *x, q=invented: out(q))
        V.fix(brief, {"fix_at": "proof", "notes": "n"}, "b", "a", caller=lambda *x: out("Very bad acne as a teen right now."))

    def test_belief_is_what_real_buyers_said(self):
        import json as J, tempfile
        d = Path(tempfile.mkdtemp())
        ex = [{"quote": "a line", "id": "r1"}]
        (d / "a-brand.json").write_text(J.dumps({"total": 100, "themes": [
            {"theme": "Saw real results (before/after, other people's)", "count": 40, "share": 0.4, "examples": ex},
            {"theme": "Reviews and testimonials", "count": 30, "share": 0.3, "examples": ex},
            {"theme": "Made for people like me", "count": 20, "share": 0.2, "examples": ex}]}))
        V.BELIEF = d
        out = '{"drivers":[{"reason":"Saw real results (before/after, other people\'s)","in_ad":"no"},{"reason":"Reviews and testimonials","in_ad":"yes","where":"0:18"},{"reason":"Made for people like me","in_ad":"yes","where":"0:00"}]}'
        bd = V.belief_drivers({"lines": ["0:00 a woman at a mirror"]}, "a-brand", caller=lambda *x: J.loads(out))
        self.assertTrue(bd["passed"])
        self.assertEqual(bd["given"], 2)
        self.assertIn("Saw real results (before/after, other people's)", bd["missing"])


if __name__ == "__main__":
    unittest.main()
