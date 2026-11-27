"""The design check and the delivery gate agree on a price (2026-11-11): a figure the send's own offer-bank entry sells
(WAR's "3 for $39.98") or a bank guarantee quoted whole ("$100 STORE CREDIT") is not "not in the brand's price list"
just because the look file's short list lacks it. Reads the real offer bank; no network.

    /usr/bin/python3 design/test_send_price_block.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build as B  # noqa: E402

LOOK = {"check": {"prices": {"$19.99": "WAR one bottle"}}}
GUAR = "Run the routine for 90 days, send your before & after, and we put $100 STORE CREDIT back in your account."


def spec_for(offer, d):
    (Path(d) / "run.json").write_text(json.dumps({"assignment": {"offer": offer}}))
    return {"brand": "brand_a", "_run": d, "sections": []}


class SendPriceBlock(unittest.TestCase):
    def test_the_sends_own_bank_price_passes(self):
        with tempfile.TemporaryDirectory() as d:
            rows = B.product_check(spec_for("war", d), LOOK, "WAR is buy 2, get 1 free: three bottles, $39.98.")
        self.assertIn({"result": "ok", "detail": "price $39.98 · war · the send's offer, offer bank"}, rows)

    def test_a_guarantee_quoted_whole_keeps_its_figure(self):
        with tempfile.TemporaryDirectory() as d:
            rows = B.product_check(spec_for("the-king-skin-set", d), LOOK, GUAR)
        self.assertFalse([r for r in rows if r["result"] == "PROBLEM" and "$100" in r["detail"]])

    def test_a_figure_nobody_sells_still_holds(self):
        with tempfile.TemporaryDirectory() as d:
            rows = B.product_check(spec_for("war", d), LOOK, "Three bottles for $41.00.")
        self.assertTrue([r for r in rows if r["result"] == "PROBLEM" and "$41.00" in r["detail"]])


if __name__ == "__main__":
    unittest.main()
