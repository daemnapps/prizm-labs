"""Every brand's desk calls its offers by offer bank key, and a desk on a Shopify-style store reads that
store's own P&L table (no warehouse: the reads are replaced)."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import analyze as A  # noqa: E402

DESKS = sorted((ROOT / "runs" / "media-buying").glob("*/desk.json"))


def bank_keys(brand):
    md = (ROOT / "brands" / brand / "products" / "offer-bank.md").read_text()
    return set(re.findall(r"^#{1,6}\s+([a-z0-9-]+)\s+[—–-]\s", md, re.M))


class Desks(unittest.TestCase):
    def test_desks_exist(self):
        self.assertGreaterEqual(len(DESKS), 2)

    def test_every_funnel_names_an_offer_bank_key_or_says_why_not(self):
        for f in DESKS:
            d = json.loads(f.read_text())
            keys = bank_keys(d["brand"])
            for fn in d["funnels"]:
                if fn.get("offer_key") is None:
                    self.assertTrue(fn.get("offer_key_gap"), "%s %s has no key and no reason" % (d["brand"], fn["match"]))
                else:
                    self.assertIn(fn["offer_key"], keys, "%s %s" % (d["brand"], fn["match"]))
                self.assertGreater(fn["fallback_break_even"], 0)

    def test_every_desk_has_the_lines_the_engine_reads(self):
        for f in DESKS:
            d = json.loads(f.read_text())
            for k in ("too_early_below", "kill_no_sale_at", "decision_at", "cut_cpa_over", "keep_cpa_up_to",
                      "double_down_cpa_up_to", "double_down_min_purchases", "budget_up_cpa_up_to", "budget_down_cpa_over",
                      "budget_step_pct"):
                self.assertIn(k, d["lines"], d["brand"])
            for k in ("share_of_spend_pct", "checkouts", "link_click_rate_pct"):
                self.assertIn(k, d["signs_of_life"], d["brand"])


class ShopifyStore(unittest.TestCase):
    DESK = {"store_source": "shopify_pnl", "store_table": "some_store_orders", "min_store_orders": 15, "store_window_days": 30,
            "funnels": [{"match": "/x", "store_funnel": None, "fallback_break_even": 50.0}]}

    def setUp(self):
        self.seen = []
        self.orig = A.W.rows
        A.W.rows = lambda sql, **k: (self.seen.append(sql) or
                                     [{"orders": "10", "revenue": "500", "contribution": "300", "last_order": "2026-11-02", "spend": "100"}])

    def tearDown(self):
        A.W.rows = self.orig

    def test_no_funnel_rows_and_no_query(self):
        self.assertEqual(A.store_funnels(30, "2026-11-02", self.DESK), {})
        self.assertEqual(self.seen, [])

    def test_break_even_falls_back_to_the_funnel_line(self):
        f = A.funnel_of(self.DESK, "https://h.example/x/page")
        self.assertEqual(A.break_even(self.DESK, f, {})[0], 50.0)

    def test_blend_reads_the_desks_own_table(self):
        b = A.store_blend("acct", "2026-11-02", desk=self.DESK)
        self.assertIn("from some_store_orders p", self.seen[0])
        self.assertNotIn("pnl_orders", self.seen[0])
        self.assertEqual(b["store_contribution"], 300.0)

    def test_a_table_name_that_is_not_plain_is_refused(self):
        bad = dict(self.DESK, store_table="x; drop table y")
        with self.assertRaises(SystemExit):
            A.store_blend("acct", "2026-11-02", desk=bad)

    def test_a_desk_without_store_source_still_reads_the_default_tables(self):
        A.store_blend("acct", "2026-11-02", desk={"funnels": []})
        self.assertIn("from pnl_orders p", self.seen[0])


if __name__ == "__main__":
    unittest.main()
