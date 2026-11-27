"""The video line's work queue reads a run's Drive card by brand + product + number (2026-11-11: a number is one
brief per brand AND product). Cases: components/naming/fixtures/brief-ids-0324.json."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import work_queue as W  # noqa: E402

FX = json.loads((HERE.parents[1] / "naming" / "fixtures" / "brief-ids-0324.json").read_text())
A, B, C = FX["briefs"]


def brand(b):
    return b["key"].split("_")[0]


class WorkQueueBriefIds(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("BRIEF_IDS_OFF", None)

    def test_live_card_of_another_product_is_not_this_runs_card(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as drive:
            for b in (B, C):                       # the other two 0324s are live
                (Path(drive) / "meta" / brand(b) / "3-live" / "video" / b["ad_name"]).mkdir(parents=True)
            run = Path(repo) / "runs" / "video-production" / brand(A) / A["key"]
            run.mkdir(parents=True)
            (run / "run.json").write_text(json.dumps({"brief": "brief-0324"}))
            ads = W.scan(repo, drive)
            mine = [a for a in ads.values() if a.get("label") == A["key"]]
            self.assertEqual(len(mine), 1)
            self.assertIsNone(mine[0]["card"])
            self.assertNotEqual(mine[0]["stage"], "done")


if __name__ == "__main__":
    unittest.main()
