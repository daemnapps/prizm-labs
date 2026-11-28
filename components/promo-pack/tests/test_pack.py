"""promo-pack: build a pack from a made-up brand, check the gate, hand off. No network, no spend.

    python3 -m unittest discover -s components/promo-pack/tests
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import pack as P  # noqa: E402

BANK = """# Offer bank — brand-a

| Offer | Price |
|---|---|
| Glow Set | $50.00 |

## glow-set — Glow Set
_lane: core_  ·  _hero: paid_

- Price: **$50.00**
- Holiday offer: **Glow Set + free Travel Case**.
- Lines the store, emails and texts may use, word for word:
  - "Glow Set + Free Travel Case"
  - "Free Travel Pouch" (through Nov 30)
  - "Order by Dec 12 for the holidays" (December sends)
  - "Order by Nov 20 for Thanksgiving"
- Link: https://example.com/glow

## serum — Serum
_lane: core_  ·  _hero: paid_

- Price: **$20.00**
- Funnel offer (example.com/funnel): **Serum starting at $15**. Funnel only.

## travel-case — Travel Case
_lane: [RULE THIS]_

- Price: **$10.00**

---

# Ruled by a human — carried forward, not generated

### popup — Standing sign-up pop-up offer

| | |
|---|---|
| Lines the pop-up may use, word for word | "FREE Travel Case with Serum" |

## promo-calendar — Promo calendar

| Dates | Promo | Code | Approved |
|---|---|---|---|
| Nov 20 – Nov 30, 2026 | Glow Set + free Travel Case. | none | the owner, 2026-11-01 |
| Dec 1 – Dec 24, 2026 | The same offer, dressed for the holidays. | none | the owner, 2026-11-01 |
"""


def slot(i, d, channel="email", offer="glow-set", occasion="holidays"):
    return {"id": "dec-%02d" % i, "date": d, "hour": 9, "local": True, "segments": ["Everyone"], "channel": channel,
            "offer": offer, "product": offer, "type": "sale-window", "occasion": occasion, "order_by": "2026-12-12",
            "variants": [{"avatar": "core-buyer", "angle": "x"}]}


SLOTS = [slot(1, "2026-12-01"), slot(2, "2026-12-05", offer="none"), slot(3, "2026-12-07", offer="mystery"),
         slot(4, "2026-12-02", channel="sms"), slot(5, "2026-12-28")]

BANK_ROWS = {"rows": [
    {"id": "a-1", "name": "Video winner one", "format": "Video", "state": "winner", "ad_ids": ["111"],
     "snapshots": [{"kind": "audit", "spend": 900, "purchases": 9, "cpa": 100, "last": "2026-10"}]},
    {"id": "a-2", "name": "Video winner two", "format": "Video", "state": "candidate", "ad_ids": ["222"],
     "snapshots": [{"kind": "audit", "spend": 1200, "purchases": 20, "cpa": 60, "last": "2026-11"}]},
    {"id": "a-3", "name": "Image winner", "format": "Image", "state": "candidate", "ad_ids": ["333"],
     "snapshots": [{"kind": "audit", "spend": 300, "purchases": 5, "cpa": 60, "last": "2026-11"}]}]}

STOCK = [
    {"sku": "case", "name": "Travel Case", "available": 40, "backup": 0, "per_day": 5, "runs_out": "2026-12-09",
     "reorder_by": "2026-10-15", "status": "LATE"},
    {"sku": "glow", "name": "Glow Set 1 x Glow Set", "available": 4000, "backup": 0, "per_day": 10,
     "runs_out": "2028-01-01", "reorder_by": "2027-11-01", "status": "ok"},
    {"sku": "other", "name": "Something else", "available": 1, "per_day": 1, "runs_out": "2026-12-02", "status": "LATE"}]


class PackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = Path(self.tmp.name)
        (b / "brands/brand-a/products").mkdir(parents=True)
        (b / "brands/brand-a/products/offer-bank.md").write_text(BANK)
        (b / "runs/marketing-calendar/brand-a/2026-12").mkdir(parents=True)
        (b / "runs/marketing-calendar/brand-a/2026-12/slots.json").write_text(json.dumps(SLOTS))
        (b / "runs/winners/brand-a").mkdir(parents=True)
        (b / "runs/winners/brand-a/bank.json").write_text(json.dumps(BANK_ROWS))
        w = b / "runs/email-production/brand-a/brand-a-dec-01--core-buyer/deliverable"
        w.mkdir(parents=True)
        (w / "email.json").write_text(json.dumps({"body": ["Glow Set. Serum starting at $15 today."]}))
        (b / "stock.json").write_text(json.dumps(STOCK))
        self.base = b
        self.pack, self.out = P.build("brand-a", "2026-12", stock=str(b / "stock.json"), base=b,
                                      today=date(2026, 11, 28))

    def tearDown(self):
        self.tmp.cleanup()

    def h(self, i):
        return next(x for x in self.pack["handoffs"] if x["id"] == i)

    def test_window_and_moment_come_from_the_bank_and_the_calendar(self):
        self.assertEqual(self.pack["window"], {"start": "2026-12-01", "end": "2026-12-24"})
        self.assertEqual(self.pack["moment"], "holidays")
        self.assertEqual(self.out, self.base / "runs/promo-pack/brand-a/holidays")
        self.assertTrue((self.out / "pack.json").is_file() and (self.out / "PACK.md").is_file())

    def test_only_the_words_the_window_allows(self):
        lines = [w["line"] for w in self.pack["offer"]["words"]]
        self.assertEqual(self.pack["offer"]["lead_line"], "Glow Set + Free Travel Case")
        self.assertIn("Order by Dec 12 for the holidays", lines)
        self.assertIn("Serum starting at $15", lines)
        dropped = {d["line"]: d["why"] for d in self.pack["offer"]["dropped"]}
        self.assertTrue(dropped["Free Travel Pouch"].startswith("retired"))
        self.assertIn("outside the window", dropped["Order by Nov 20 for Thanksgiving"])
        self.assertIn("pop-up", dropped["FREE Travel Case with Serum"])
        funnel = next(w for w in self.pack["offer"]["words"] if w["line"] == "Serum starting at $15")
        self.assertEqual(funnel["surfaces"], ["funnel", "ads"])

    def test_every_workflow_gets_a_handoff_and_doorless_ones_are_gaps(self):
        ids = [h["id"] for h in self.pack["handoffs"]]
        self.assertEqual(ids, ["video", "static", "email", "sms", "store", "funnel"])
        gaps = {g["handoff"] for g in self.pack["gaps"]}
        self.assertTrue({"store", "funnel", "stock"} <= gaps)
        self.assertIsNone(self.h("store")["door"])
        self.assertEqual(self.h("funnel")["words"], ["Serum starting at $15"])

    def test_email_and_sms_dates_come_from_the_calendar(self):
        e, s = self.h("email"), self.h("sms")
        self.assertEqual([r["id"] for r in e["sends"]], ["dec-01", "dec-02", "dec-03"])
        self.assertEqual(e["not_in_bank"], ["mystery"])
        self.assertEqual(e["after_window"], ["dec-05"])
        self.assertEqual(s["briefs"], 1)
        self.assertEqual(e["sends"][0]["ready_by"], "2026-11-30")
        self.assertEqual(e["args"]["slots"], "dec-01,dec-02,dec-03")

    def test_a_funnel_line_in_a_written_email_is_flagged(self):
        first = self.h("email")["sends"][0]["written"]
        self.assertEqual(first["state"], "written")
        self.assertEqual(first["flags"], ["funnel line in a email: Serum starting at $15"])
        self.assertEqual(self.h("email")["sends"][1]["written"]["state"], "not written")

    def test_winners_ranked_by_spend(self):
        self.assertEqual([w["id"] for w in self.h("video")["winners"]], ["a-2", "a-1"])
        self.assertEqual(self.h("video")["ending"], ["Glow Set + Free Travel Case", "Order by Dec 12 for the holidays"])
        self.assertEqual(self.h("static")["args"]["product"], "glow-set")
        self.assertEqual(self.h("static")["args"]["avatar"], "core-buyer")

    def test_stock_blocks_only_offer_items(self):
        st = self.pack["stock"]
        self.assertEqual([r["sku"] for r in st["rows"]], ["case", "glow"])
        self.assertEqual([b["sku"] for b in st["blockers"]], ["case"])
        self.assertIn("LATE", st["blockers"][0]["why"])

    def test_without_a_stock_read_the_pack_says_so(self):
        pack, _ = P.build("brand-a", "2026-12", base=self.base, today=date(2026, 11, 28))
        self.assertFalse(pack["stock"]["read"])

    def test_no_promo_row_no_pack(self):
        with self.assertRaises(SystemExit):
            P.build("brand-a", "2027-02", base=self.base)

    def test_hand_off_is_held_until_the_owner_approves_the_words(self):
        with self.assertRaises(SystemExit) as e:
            P.hand("brand-a", "holidays", base=self.base, runner=lambda a: None)
        self.assertIn("held", str(e.exception))
        self.assertFalse((self.out / "handoffs").exists())

    def test_changed_words_make_an_approval_stale(self):
        P.approve("brand-a", "holidays", "the owner", "yes", base=self.base)
        (self.base / "brands/brand-a/products/offer-bank.md").write_text(BANK.replace("Free Travel Case\"", "Free Case\""))
        pack, out = P.build("brand-a", "2026-12", base=self.base)
        self.assertEqual(pack["approval"]["state"], "stale")
        with self.assertRaises(SystemExit):
            P.hand("brand-a", "holidays", base=self.base, runner=lambda a: None)

    def test_after_approval_free_doors_run_and_spending_doors_are_written(self):
        P.approve("brand-a", "holidays", "the owner", "yes", base=self.base)
        ran = []

        class R:
            returncode, stdout, stderr = 0, "ok", ""

        def runner(argv):
            ran.append(argv)
            if "natural_statics.py" in argv[1]:       # what the real door writes
                d = self.base / "runs/ad-variations/brand-a" / argv[argv.index("--label") + 1]
                d.mkdir(parents=True)
                (d / "sprint.json").write_text(json.dumps({"offer": "", "moment": "", "until": "", "never": []}))
            return R()

        done = {r["id"]: r for r in P.hand("brand-a", "holidays", base=self.base, runner=runner)}
        self.assertEqual(done["email"]["state"].split(":")[0], "written")
        self.assertEqual(done["store"]["state"], "gap")
        self.assertEqual(done["static"]["state"], "handed")
        self.assertEqual(done["video"]["state"], "handed")
        self.assertEqual(len([a for a in ran if "run.py" in a[1]]), 2)                  # one plan per winner
        self.assertTrue(any("sms.py" in a[1] and "--dry-run" in a for a in ran))
        self.assertFalse(any("run_month.py" in a[1] for a in ran))                     # spends: never run here
        sp = json.loads((self.base / "runs/ad-variations/brand-a/holidays-2026-promo-pack/sprint.json").read_text())
        self.assertEqual(sp["offer"], "Glow Set + Free Travel Case")
        self.assertEqual(sp["until"], "2026-12-24")
        self.assertEqual(sp["never"], ["Free Travel Pouch"])
        plan = (self.base / "runs/promo-pack/brand-a/holidays/handoffs/video/campaign-plan.md").read_text()
        self.assertIn("Glow Set + Free Travel Case", plan)
        self.assertTrue((self.out / "handoffs/video/handoff.json").is_file())


if __name__ == "__main__":
    unittest.main()
