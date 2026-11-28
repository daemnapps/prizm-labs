"""Spend per Facebook Page: read from the upload record, an older name's Page tag, else the brand's own Page."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import page_index as PI  # noqa: E402

PAGES = [{"id": "111", "name": "Brand Page", "tag": "brand", "default": True},
         {"id": "222", "name": "Second Page", "tag": "sp", "default": False}]
ADS = [{"ad_id": "1", "ad_name": "b_w_brief-0001_batch-2026-11-20-a_f", "spend30": "10", "buys30": "1"},
       {"ad_id": "2", "ad_name": "b_w_brief-0002_batch-2026-11-20-a_f", "spend30": "20", "buys30": "2"},
       {"ad_id": "3", "ad_name": "b_w_brief-0003_batch-2026-11-20-a_f_p-sp", "spend30": "5", "buys30": "0"},
       {"ad_id": "4", "ad_name": "b_w_brief-0002_batch-2026-11-20-a_f", "spend30": "1", "buys30": "0"}]


class PageIndex(unittest.TestCase):
    def run_it(self):
        with tempfile.TemporaryDirectory() as d:
            live = Path(d) / "live.jsonl"
            live.write_text("\n".join(json.dumps(x) for x in [
                {"brand": "b", "ad_id": "2", "fb_page": "222", "fb_page_name": "Second Page"},
                {"brand": "b", "ad_id": "4", "copied_from": "2"}]) + "\n")
            with mock.patch.object(PI, "pages", return_value=PAGES):
                return PI.index("b", ADS, live), PI.spend("b", ADS, live)

    def test_each_ad_has_its_page_and_how_it_was_known(self):
        ix, _ = self.run_it()
        self.assertEqual((ix["1"]["fb_page_name"], ix["1"]["by"]), ("Brand Page", "default"))
        self.assertEqual((ix["2"]["fb_page_name"], ix["2"]["by"]), ("Second Page", "record"))
        self.assertEqual((ix["3"]["fb_page_name"], ix["3"]["by"]), ("Second Page", "name"))
        self.assertEqual(ix["4"]["fb_page_name"], "Second Page")          # a copy runs from its source's Page

    def test_spend_per_page(self):
        _, sp = self.run_it()
        by = {g["fb_page_name"]: g for g in sp}
        self.assertEqual((by["Second Page"]["spend30"], by["Second Page"]["ads"]), (26.0, 3))
        self.assertEqual(by["Brand Page"]["spend30"], 10.0)


if __name__ == "__main__":
    unittest.main()
