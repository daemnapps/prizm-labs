#!/usr/bin/env python3
"""SI-155 (paid pool remainder): a returning ad stays live, and a fresh clone logs its paid call.

    /usr/bin/python3 components/swipe-paid/test_swp1_refresh_schema.py

Stdlib only, offline: no AdPlexity call, no key. Every write lands in a
tempfile folder — never a brand folder here or the real capture/market.db.
"""
import json, os, sqlite3, sys, tempfile, unittest
from datetime import date, timedelta
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "capture"))
import refresh as R           # noqa: E402
import adplexity_client as A  # noqa: E402

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


class Refresh(unittest.TestCase):
    def test_returning_ad_is_live_now(self):
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, "zz-brand"))
        doc = {"swept": YESTERDAY, "blocks": [{
            "nn": "01", "slug": "01_h", "headline": "H", "primary_text": "b",
            "count": 1, "video_count": 0, "image_count": 1, "rep_ad_id": 1,
            "ad_ids": [1], "variants": 1, "max_variants": 1,
            "landing_page": None, "first_swept": YESTERDAY,
            "media": {"1": {"video": "", "image": "u", "variants": 1,
                            "swept": YESTERDAY}}}]}
        with open(os.path.join(tmp, "zz-brand", "blocks.json"), "w") as f:
            json.dump(doc, f)
        sweep = os.path.join(tmp, "sweep-ALL.json")
        with open(sweep, "w") as f:
            json.dump({"items": [{"id": 1, "title": "H", "description": "b",
                                  "image_url": "u"}]}, f)
        with mock.patch.object(R, "HERE", tmp):
            R.main("zz-brand", sweep, TODAY, False)
        with open(os.path.join(tmp, "zz-brand", "blocks.json")) as f:
            b = json.load(f)["blocks"][0]
        self.assertEqual(b["media"]["1"]["swept"], TODAY)
        self.assertEqual(b["live_now"], 1)
        self.assertEqual(b["first_swept"], YESTERDAY)
        self.assertEqual(b["count"], 1)
        self.assertEqual(b["ad_ids"], [1])


class FreshClone(unittest.TestCase):
    def test_log_run_on_a_missing_db(self):
        db = os.path.join(tempfile.mkdtemp(), "market.db")
        self.assertFalse(os.path.exists(db))
        with mock.patch.object(A, "DB", db):
            con = A.log_run("adplexity watch /search/ads",
                            {"brand": "zz-brand", "domain": "zz.example"}, 3,
                            "daily delta; credits=3", "competitor")
            con.execute("UPDATE scan_runs SET cost_usd=? WHERE run_id=last_insert_rowid()",
                        (3 * 99.0 / 5000,))
            con.commit()
            con.close()
        con = sqlite3.connect(db)
        rows = con.execute("SELECT source, items_returned, purpose, cost_usd"
                           " FROM scan_runs").fetchall()
        con.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:3], ("adplexity watch /search/ads", 3, "competitor"))
        self.assertAlmostEqual(rows[0][3], 3 * 99.0 / 5000)


if __name__ == "__main__":
    unittest.main()
