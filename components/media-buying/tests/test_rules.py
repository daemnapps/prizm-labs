"""The desk's lines, on made-up ads: bleeding goes off, a live one is pulled up, a cheap seller is doubled down."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import analyze as A  # noqa: E402

L = {"too_early_below": 1.0, "kill_no_sale_at": 2.0, "decision_at": 3.0, "cut_cpa_over": 1.5, "keep_cpa_up_to": 1.2,
     "double_down_cpa_up_to": 0.8, "double_down_min_purchases": 3, "budget_up_cpa_up_to": 1.0, "budget_down_cpa_over": 1.3,
     "budget_step_pct": 20}
LIFE = {"share_of_spend_pct": 15, "checkouts": 5, "link_click_rate_pct": 4.4}


def ad(**k):
    a = {"life_spend": 0, "life_buys": 0, "spend7": 0, "buys7": 0, "share": 0, "checkouts": 0, "link_rate": 1}
    a.update(k)
    return a


class Ads(unittest.TestCase):
    def test_too_early(self):
        self.assertEqual(A.judge_ad(ad(life_spend=20), 40, L, LIFE)[0], "too_early")

    def test_no_sale_past_two_break_evens_goes_off(self):
        self.assertEqual(A.judge_ad(ad(life_spend=90, spend7=30), 40, L, LIFE)[0], "off")

    def test_kill_line_with_signs_of_life_is_his_call(self):
        self.assertEqual(A.judge_ad(ad(life_spend=90, spend7=30, checkouts=6), 40, L, LIFE)[0], "pull_up")

    def test_expensive_after_decision_goes_off(self):
        self.assertEqual(A.judge_ad(ad(life_spend=130, life_buys=2, spend7=20), 40, L, LIFE)[0], "off")

    def test_cheap_seller_doubles_down(self):
        self.assertEqual(A.judge_ad(ad(life_spend=90, life_buys=4, spend7=30), 40, L, LIFE)[0], "double_down")

    def test_old_ad_judged_on_its_week(self):
        # great lifetime, bad week -> not kept on the lifetime average
        self.assertEqual(A.judge_ad(ad(life_spend=50000, life_buys=1500, spend7=600, buys7=6), 40, L, LIFE)[0], "watch")


class Campaigns(unittest.TestCase):
    up = {"after_ads": 100}
    down = {"after_ads": -100}

    def test_budget_up_needs_the_store_up_too(self):
        c = {"spend3": 100, "buys3": 3, "spend7": 300, "buys7": 9}
        self.assertEqual(A.judge_campaign(c, 40, L, self.up)[0], "budget_up")
        self.assertEqual(A.judge_campaign(c, 40, L, self.down)[0], "budget_hold")

    def test_budget_down_over_the_line_both_windows(self):
        c = {"spend3": 300, "buys3": 3, "spend7": 700, "buys7": 7}
        self.assertEqual(A.judge_campaign(c, 40, L, self.up)[0], "budget_down")


R = {"type": "meta_cpa_windows", "cpa": 50, "judge_at_14d_spend": 200, "no_sale_off_at_14d_spend": 100,
     "prospecting": {"cpa14_up_to": 65, "daily_frequency7_up_to": 1.2, "share7_from_pct": 10}}


def win(s3=0, b3=0, s7=0, b7=0, s14=0, b14=0, freq7=1.5, share7=5):
    return {"spend3": s3, "buys3": b3, "spend7": s7, "buys7": b7, "spend14": s14, "buys14": b14, "freq7": freq7, "share7": share7}


class Windows(unittest.TestCase):
    def call(self, **k):
        return A.judge_windows(win(**k), R)[0]

    def test_under_the_line_in_one_window_keeps(self):
        self.assertEqual(self.call(s3=100, b3=2, s7=300, b7=4, s14=600, b14=8), "keep")     # 50 / 75 / 75

    def test_exactly_on_the_line_is_under(self):
        self.assertEqual(self.call(s3=200, b3=2, s7=300, b7=4, s14=500, b14=10), "keep")

    def test_over_in_every_window_goes_off(self):
        self.assertEqual(self.call(s3=120, b3=2, s7=300, b7=5, s14=600, b14=10), "off")     # 60 / 60 / 60, not prospecting

    def test_prospecting_keeps_on_share_frequency_and_a_near_cpa(self):
        k = dict(s3=120, b3=2, s7=300, b7=5, s14=600, b14=10)
        self.assertEqual(self.call(freq7=1.2, share7=10, **k), "prospect")
        self.assertEqual(self.call(freq7=1.21, share7=30, **k), "off")
        self.assertEqual(self.call(freq7=1.1, share7=9.9, **k), "off")
        self.assertEqual(self.call(freq7=None, share7=30, **k), "off")
        self.assertEqual(self.call(freq7=1.1, share7=30, s3=140, b3=2, s7=350, b7=5, s14=660, b14=10), "off")   # 14 days over its own cap

    def test_no_sale_by_the_mark_goes_off_before_it_is_judged(self):
        self.assertEqual(self.call(s7=60, s14=100), "off")
        self.assertEqual(self.call(s7=60, s14=99), "too_early")

    def test_under_the_judging_spend_is_not_judged(self):
        self.assertEqual(self.call(s3=50, b3=0, s7=150, b7=1, s14=199, b14=1), "too_early")

    def test_a_window_with_no_spend_is_left_out(self):
        self.assertEqual(self.call(s7=0, s14=600, b14=10), "off")

    def test_an_unknown_rule_is_refused(self):
        self.assertIsNone(A.rule_of({}))
        with self.assertRaises(SystemExit):
            A.rule_of({"rule": {"type": "x"}})


if __name__ == "__main__":
    unittest.main()
