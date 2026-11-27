import datetime as dt, json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import audit as A  # noqa: E402
import winner_views as W  # noqa: E402
from test_bank import audit, row, w  # noqa: E402
from test_winners import run  # noqa: E402


def cell(name, month, spend, purchases, value):
    return {"name": name, "month": month, "spend": spend, "purchases": purchases, "value": value, "ids": ["1"]}


def day(spend, buys, funnel, store, renewal):
    return {"spend": spend, "pixel_buys": buys, "funnel": {"orders": 1, "revenue": funnel}, "store": {"orders": 2, "revenue": store},
            "renewal": {"orders": 3, "revenue": renewal}}


class Views(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.addCleanup(setattr, A, "REPO", A.REPO)
        a = audit(self.root, "2025-01-01_2026-11-02", "2025-01-01", "2026-11-02", [row(1, "Founder Ad", ["1"], 1, 1, 1)])
        w(a, "cells.json", [
            cell("Founder Ad", "2025-09", 100, 10, 200), cell("Founder Ad Copy", "2025-10", 100, 10, 100),
            cell("Script Task 7", "2025-08", 50, 5, 50), cell("Blank", "2025-08", 10, 0, 0),
            cell("Founder Ad", "2026-10", 60, 2, 30), cell("Pic", "2026-08", 40, 4, 80),
            cell("Founder Ad", "2025-07", 999, 99, 999), cell("Founder Ad", "2026-11", 999, 99, 999)])
        w(a, "merges.json", {"Founder Ad Copy": "Founder Ad"})
        w(self.root / "runs/winners/acme", "tags.json", {
            "Founder Ad": {"on_screen": "Founder to camera", "message": "The story", "format": "Video"},
            "Scrub Task 7": {"on_screen": "Actor skit", "message": "Wrong key"},
            "Pic": {"on_screen": "Sale graphic", "message": "Sale", "format": "Image"}})

    def tearDown(self):
        self._t.cleanup()

    def test_default_months_are_the_last_three_full_ones(self):
        self.assertEqual(W.default_months("2026-11-02"), (8, 10))
        self.assertEqual(W.default_months("2026-10-31"), (8, 10))
        self.assertEqual(W.default_months("2026-02-10"), (11, 1))

    def test_a_run_across_new_year(self):
        self.assertEqual(W.periods("2026-02-10", 11, 1), [("2024-25", ["2024-11", "2024-12", "2025-01"]),
                                                          ("2025-26", ["2025-11", "2025-12", "2026-01"])])

    def test_yoy(self):
        code, out, _ = run(self.root, "yoy", "--brand", "acme")
        self.assertEqual(code, 0)
        self.assertIn("Aug to Oct, 2025 vs 2026", out)
        doc = json.loads((self.root / "runs/winners/acme/views/yoy-08-10.json").read_text())
        self.assertEqual(doc["years"]["2025"], {"ads": 3, "purchases": 25, "spend": 260, "cpa": 10.4, "roas": 1.35})
        group = {r["value"]: r for r in doc["by_group"]}
        self.assertEqual(group["Founder"]["2025"]["ads"], 1)      # the copy merged in
        self.assertEqual(group["Founder"]["2025"]["purchases"], 20)
        self.assertEqual(group["Founder"]["2025"]["share"], 0.8)
        self.assertEqual(group["Statics"]["2026"]["purchases"], 4)
        self.assertEqual(group["Not tagged yet"]["2025"]["ads"], 2)
        self.assertEqual({r["value"] for r in doc["by_message"]}, {"The story", "Sale", "Not tagged yet"})
        self.assertEqual([r["month"] for r in doc["by_month"]], ["Aug", "Sep", "Oct"])
        self.assertEqual(doc["by_month"][0]["2026"]["spend"], 40)
        md = (self.root / "runs/winners/acme/views/yoy-08-10.md").read_text()
        for head in ("## By group", "## By what's on screen", "## By message", "## Month by month"):
            self.assertIn(head, md)

    def test_yoy_months_and_bad_use(self):
        self.assertEqual(run(self.root, "yoy", "--brand", "acme", "--from-month", "09", "--to-month", "09")[0], 0)
        doc = json.loads((self.root / "runs/winners/acme/views/yoy-09-09.json").read_text())
        self.assertEqual(doc["years"]["2025"]["spend"], 100)
        for args in (["--from-month", "09"], ["--from-month", "13", "--to-month", "1"], ["--window", "nope"]):
            code, _, err = run(self.root, "yoy", "--brand", "acme", *args)
            self.assertEqual(code, 2, args)
            self.assertEqual(len(err.strip().splitlines()), 1)

    def test_yoy_uses_the_widest_window_unless_told(self):
        a = audit(self.root, "2026-10-04_2026-11-03", "2026-10-04", "2026-11-03", [row(1, "X", ["1"], 1, 1, 1)])
        w(a, "cells.json", [cell("X", "2026-10", 1, 1, 1)])
        self.assertEqual(W.widest_label(self.root, "acme"), "2025-01-01_2026-11-02")
        self.assertEqual(W.yoy(self.root, "acme", "2026-10-04_2026-11-03")[2]["window"], "2026-10-04_2026-11-03")

    def test_store(self):
        asked = {}

        def pull(brand, days, today):
            asked.update(brand=brand, days=days)
            # Monday 2026-10-26 to Tuesday 2026-11-03
            return {(dt.date(2026, 10, 26) + dt.timedelta(days=i)).isoformat(): day(10, 1, 20, 10, 10) for i in range(days)}

        _, _, doc = W.store(self.root, "acme", weeks=2, today=dt.date(2026, 11, 4), pull=pull)
        self.assertEqual(asked, {"brand": "acme", "days": 9})
        self.assertEqual([r["week"] for r in doc["weeks"]], ["2026-10-26", "2026-11-02"])
        self.assertEqual(doc["weeks"][1]["days"], 2)
        wk = doc["weeks"][0]
        self.assertEqual((wk["orders"], wk["funnel_revenue"], wk["store_revenue"], wk["renewal_revenue"], wk["revenue"]),
                         (42, 140, 70, 70, 280))
        self.assertEqual((wk["spend"], wk["spend_share"], wk["ad_purchases"]), (70, 0.25, 7))
        self.assertEqual(doc["total"]["revenue"], 360)
        md = (self.root / "runs/winners/acme/views/store-2026-11-04.md").read_text()
        self.assertIn("| 2026-10-26 | 7 | 42 | $140 | $70 | $70 | $280 | $70 | 25.0% | 7 |", md)

    def test_store_weeks_has_to_be_positive(self):
        self.assertEqual(run(self.root, "store", "--brand", "acme", "--weeks", "0")[0], 2)


if __name__ == "__main__":
    unittest.main()
