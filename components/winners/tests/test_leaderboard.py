import json, sys, tempfile, unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import leaderboard as LB  # noqa: E402
from test_bank import w  # noqa: E402

TODAY = date(2026, 11, 15)


def clip(handle, views, spend_cents, submitted="2026-11-01", platform="tiktok"):
    acc = {"handle": handle, "platform": platform, "key": "k"} if handle else None
    return {"postingAccount": acc, "views": views, "spend": spend_cents, "submittedAt": submitted + " 10:00:00",
            "campaignName": "Camp", "status": "approved"}


def acct(handle, cents, kind="account"):
    return {"handle": handle, "kind": kind, "spendCents": str(cents), "platform": "tiktok"}


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        w(self.root, "runs/winners/acme/campaigns.json", {"campaigns": [{"pool": "live", "link": "x", "state": "live"},
                                                                         {"pool": "old", "link": "y", "state": "filled"}],
                                                           "aliases": {"Bo Brown": ["bo_clips"]}})
        w(self.root, "runs/content-rewards/acme/live/2026-11-15/clips.json", json.dumps({
            "pulled": "2026-11-15T09:00:00",
            "clips": [clip("ann", 1000, 500), clip("ann", 500, 100, "2026-11-12"), clip("bo_clips", 300, 50, "2026-11-13"),
                      clip(None, 40, 10)],
            "accounts": {"accounts": [acct("ann", 600), acct("bo_clips", 50), acct(None, 25, "campaign-payments")]}}))
        w(self.root, "runs/content-rewards/acme/old/2026-11-15/clips.json", json.dumps({
            "clips": [clip("Ann", 2000, 1000, "2026-06-01")], "accounts": {"accounts": [acct("Ann", 1000)]}}))
        rows = [{"trybe_id": "t1", "creator": "Bo Brown", "created": "2026-11-13", "meta": {"impressions": 400}},
                {"trybe_id": "t2", "creator": "Cy Doe", "created": "2026-10-01", "meta": {"impressions": 0}}]
        ppl = [{"creator": "Bo Brown", "earnings": 5.0, "trybe_gmv": 100.0, "purchases": 3, "purchase_value": 90.0},
               {"creator": "Cy Doe", "earnings": 0, "trybe_gmv": 0, "purchases": 0, "purchase_value": 0},
               {"creator": "Never Did", "earnings": 0, "trybe_gmv": 0, "purchases": 0, "purchase_value": 0}]
        w(self.root, "runs/winners/acme/creators/2026-11-15/trybe.json", {"rows": rows, "people": ppl})
        w(self.root, "runs/winners/acme/creators/2026-11-15/week/trybe.json", {"rows": rows, "people": ppl[:1]})
        w(self.root, "runs/winners/acme/bank.json", {"brand": "acme", "bar": {}, "creator_bar": {"min_spend": 50},
                                                     "sources": [], "rows": [{"id": "acme-1", "trybe_id": "t1", "state": "winner"}]})

    def tearDown(self):
        self._t.cleanup()

    def test_one_row_per_person_across_campaigns_and_platforms(self):
        _, d = LB.write(self.root, "acme", TODAY)
        by = {p["key"]: p for p in d["people"]}
        self.assertEqual(set(by), {"ann", "boclips", "cydoe"})   # "Never Did" did nothing; the loose clip is no person
        self.assertEqual(by["ann"]["all_time"]["views"], 3500)   # @ann and @Ann, two campaigns
        self.assertEqual(by["ann"]["all_time"]["paid"], 16.0)
        self.assertEqual(sorted(by["ann"]["campaigns"]), ["live", "old"])
        bo = by["boclips"]                                        # the alias joins the Trybe creator to the clipper
        self.assertEqual(sorted(bo["platforms"]), ["trybe", "whop"])
        self.assertEqual(bo["all_time"]["views"], 700)
        self.assertEqual(bo["all_time"]["paid"], 5.5)
        self.assertEqual(bo["all_time"]["trybe_gmv"], 100.0)
        self.assertEqual(bo["tier"], "top earner")
        self.assertEqual(by["cydoe"]["name"], "Cy D.")
        self.assertEqual(by["cydoe"]["tier"], "rising")
        self.assertEqual([p["key"] for p in d["people"]], ["ann", "boclips", "cydoe"])
        self.assertEqual([p["rank"] for p in d["people"]], [1, 2, 3])
        self.assertIsNone(d["people"][0]["move"])

    def test_totals_match_the_reports(self):
        _, d = LB.write(self.root, "acme", TODAY)
        t = d["totals"]["all_time"]
        self.assertEqual(t["views"], 1000 + 500 + 300 + 40 + 2000 + 400)
        self.assertEqual(t["paid"], 6.0 + 0.5 + 0.25 + 10.0 + 5.0)
        self.assertEqual(d["unattributed"]["all_time"]["paid"], 0.25)
        self.assertEqual(d["sources"]["campaigns"][0]["paid"], 6.75)
        self.assertEqual(t["ad_purchases"], 3)
        self.assertEqual(t["trybe_gmv"], 100.0)
        w_ = d["totals"]["week"]
        self.assertEqual(w_["views"], 500 + 300 + 400)           # clips posted this week + Trybe's week
        self.assertEqual(w_["clips"], 3)

    def test_a_snapshot_counts_in_all_time_with_its_read_date(self):
        w(self.root, "runs/winners/acme/sources/affiliates-2026-11-10.json",
          {"source": "affiliates", "kind": "snapshot", "read": "2026-11-10",
           "totals": {"sales": 1000.0, "orders": 10, "paid": 200.0, "ready_unpaid": 5.0},
           "top": [{"name": "Dee Evans", "orders": 6, "sales": 700.0}]})
        _, d = LB.write(self.root, "acme", TODAY)
        t, wk = d["totals"]["all_time"], d["totals"]["week"]
        self.assertEqual(t["paid"], 21.75 + 200.0)
        self.assertEqual(t["sales_driven"], 100.0 + 1000.0)      # Trybe GMV + affiliate sales, both store-credited
        self.assertEqual(t["ad_purchase_value"], 90.0)            # the platform's count stays apart
        self.assertEqual(t["orders"], 10)
        self.assertEqual((wk["paid"], wk["sales_driven"]), (1.0 + 0.5 + 5.0, 100.0))   # a snapshot is never in the week
        dee = [p for p in d["people"] if p["key"] == "deeevans"][0]
        self.assertEqual((dee["name"], dee["snapshot_read"], dee["platforms"]), ("Dee E.", "2026-11-10", ["affiliates"]))
        self.assertEqual(dee["sales_rank"], 1)
        self.assertEqual(dee["tier"], "top earner")
        self.assertEqual(d["sources"]["snapshots"][0]["read"], "2026-11-10")
        self.assertEqual(d["unattributed"]["all_time"]["sales_driven"], 300.0)
        self.assertIn("snapshot read 2026-11-10, not live", (self.root / "runs/winners/acme/leaderboard.md").read_text())
        flat = {c["handle"]: c for c in d["creators"]}
        self.assertEqual(flat["Dee E."]["move"], "new")
        self.assertEqual(d["totals"]["paid"], t["paid"])

    def test_programs_file_is_read_first_and_no_link_is_written(self):
        w(self.root, "runs/creator-machine/acme/hub/programs.json",
          {"programs": [{"id": "trybe", "platform": "trybe"},
                        {"id": "whop-live", "via": "content-rewards", "pool": "live", "state": "live", "report": "SECRET-LINK"}]})
        camps, _ = LB.campaigns(self.root, "acme")
        self.assertEqual([c["pool"] for c in camps], ["live"])
        LB.write(self.root, "acme", TODAY)
        self.assertNotIn("SECRET-LINK", (self.root / "runs/winners/acme/leaderboard.json").read_text())

    def test_a_week_later_counts_the_change_and_the_move(self):
        LB.write(self.root, "acme", TODAY)
        f = self.root / "runs/content-rewards/acme/live/2026-11-22/clips.json"
        w(f.parent, f.name, json.dumps({"clips": [clip("bo_clips", 9000, 2000, "2026-11-20")],
                                        "accounts": {"accounts": [acct("bo_clips", 2000)]}}))
        _, d = LB.write(self.root, "acme", date(2026, 11, 22))
        by = {p["key"]: p for p in d["people"]}
        self.assertEqual(by["boclips"]["rank"], 1)
        self.assertEqual(by["boclips"]["move"], 1)
        self.assertEqual(by["boclips"]["week"]["views"], 9400 - 700)
        self.assertIn("change since the leaderboard of 2026-11-15", d["week"]["basis"])
        self.assertTrue((self.root / "runs/winners/acme/leaderboard/2026-11-22.json").is_file())


if __name__ == "__main__":
    unittest.main()
