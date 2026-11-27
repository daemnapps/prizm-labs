"""The approval page and the finished-ads index keep briefs that share a number apart (2026-11-11). A brief is
brand + product + number; cases: components/naming/fixtures/brief-ids-0324.json (the three real 0324s)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
FX = json.loads((HERE.parent.parent / "naming" / "fixtures" / "brief-ids-0324.json").read_text())
A, B, C = FX["briefs"]          # A and B: one brand, two products; C: another brand


def brand(b):
    return b["key"].split("_")[0]


class AdsIndexBriefIds(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("BRIEF_IDS_OFF", None)

    def build(self):
        import ads_index as AI
        with tempfile.TemporaryDirectory() as r, tempfile.TemporaryDirectory() as out:
            for b, state in ((A, "2-approved"), (B, "3-live")):
                d = Path(r) / brand(b) / state / "video" / b["ad_name"]
                d.mkdir(parents=True)
                (d / "card.json").write_text(json.dumps({"ad_name": b["ad_name"]}))
            os.environ["META_CARDS_ROOT"] = r
            try:
                AI.build(brand(A), out=out, log=lambda *_: None)
                rows = json.loads((Path(out) / brand(A) / AI.INDEX).read_text())["briefs"]
                return rows, AI.find_ad(brand(A), "0324", out=out), AI.find_ad(brand(A), A["key"], out=out)
            finally:
                os.environ.pop("META_CARDS_ROOT", None)

    def test_two_products_two_rows(self):
        rows, by_number, by_key = self.build()
        got = {r["names"][0]: r["state"] for r in rows if r.get("number") == "0324"}
        self.assertEqual(got, {A["key"]: "2-approved", B["key"]: "3-live"})
        self.assertIsNone(by_number)                       # a number two products share answers nothing
        self.assertEqual(by_key["state"], "2-approved")

    def test_switch_off_merges_as_before(self):
        os.environ["BRIEF_IDS_OFF"] = "1"
        rows, _, _ = self.build()
        self.assertEqual(len([r for r in rows if r.get("number") == "0324"]), 1)


class ApprovePageBriefIds(unittest.TestCase):
    def test_cards_carry_the_key_and_the_readable_id(self):
        import approve as AP
        for b in FX["briefs"]:
            self.assertEqual(AP.brief_ids(b["ad_name"]), {"brief_key": b["key"], "brief_label": b["label"]})
        self.assertEqual(AP.brief_ids(None), {"brief_key": "", "brief_label": ""})


if __name__ == "__main__":
    unittest.main()
