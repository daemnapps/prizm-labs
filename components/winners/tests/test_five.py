import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import five as FV  # noqa: E402
import winners  # noqa: E402
from test_bank import w  # noqa: E402

AUD = {"kind": "audit", "since": "2025-01-01", "until": "2026-11-02", "pulled_at": "x", "audit": "audit/2025-01-01_2026-11-02"}


def row(i, name, purchases, spend, roas, **more):
    sn = dict(AUD, purchases=purchases, spend=spend, roas=roas, cpa=round(spend / purchases, 2) if purchases else None,
              first="2025-01", last="2026-06")
    r = {"id": "acme-%d" % i, "state": "candidate", "name": name, "ad_ids": [str(i)], "ad_names": [name],
         "words": {"hook": "hook %d" % i}, "source": {}, "snapshots": [sn]}
    r.update(more)
    return r


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.home = "runs/winners/acme/"
        tags = {"A": {"on_screen": "Founder to camera", "message": "Acne"},
                "B": {"on_screen": "Founder to camera", "message": "Acne"},          # same pair as A
                "C": {"on_screen": "Founder to camera", "message": "Aging"},         # same format, new angle: in
                "D": {"on_screen": "Unclear", "message": "Acne"},                     # catch-all: held
                "E": {"on_screen": "Product shot", "message": "Acne"},
                "F": {"on_screen": "Skin close-up", "message": "Acne"}}
        self.rows = [row(1, "A", 900, 50000, 1.4), row(2, "B", 800, 40000, 1.3), row(3, "C", 700, 40000, 1.2),
                     row(4, "D", 650, 30000, 1.5), row(5, "E", 600, 30000, 0.8),        # ROAS under the floor
                     row(6, "F", 100, 5000, 1.1),
                     row(7, "vid", 5, 105, 2.2, trybe_id="t7", creator="Bo",
                         tags={"format": "Creator talking to camera", "angle": "Sale", "hook_line": "grab it"})]
        self.rows[6]["snapshots"][0]["kind"] = "creator"
        w(self.root, self.home + "tags.json", tags)
        w(self.root, self.home + "audit/2025-01-01_2026-11-02/ranked.json",
          {"rows": [{"name": "A", "ids": ["1"], "link": "https://example.com/a"}]})
        (self.root / "runs/video-teardown/acme/a-run").mkdir(parents=True)
        w(self.root, "team/reg.json", {"rows": [{"id": "r1", "run": "runs/video-teardown/acme/a-run/"}]})
        self.rows[0]["source"] = {"registry": "team/reg.json#r1"}
        self.bank({"min_spend": None, "max_cpa": None, "min_roas": None},
                  {"min_spend": 50.0, "min_roas": 1.0, "min_purchases": 1.0})

    def bank(self, bar, cbar):
        w(self.root, self.home + "bank.json", {"brand": "acme", "bar": bar, "creator_bar": cbar, "sources": [],
                                                "rows": self.rows})

    def tearDown(self):
        self._t.cleanup()

    def test_ranked_on_numbers_distinct_pairs_and_nothing_padded(self):
        _, d = FV.write(self.root, "acme", "2026-11-15")
        self.assertEqual([e["name"] for e in d["five"]], ["A", "C", "F", "vid"])
        self.assertEqual(d["proven"], 6)                     # A B C D F vid; E fails ROAS 1.0 on the one set bar
        self.assertEqual(d["same_pair_skipped"], 1)          # B repeats A's pair
        self.assertIn("only 4 proven", d["short"])
        self.assertEqual([e["name"] for e in d["held"]], ["D"])
        a = d["five"][0]
        self.assertEqual((a["rank"], a["link"], a["numbers"]["purchases"]), (1, "https://example.com/a", 900))
        self.assertEqual(a["teardown"], [{"kind": "teardown run", "path": "runs/video-teardown/acme/a-run"}])
        v = d["five"][3]
        self.assertEqual((v["kind"], v["trybe_id"], v["format"], v["hook_line"]),
                         ("creator", "t7", "Creator talking to camera", "grab it"))
        self.assertIn("Only 4 proven", (self.root / self.home / "brief-five.md").read_text())

    def test_a_set_paid_bar_decides_paid_rows(self):
        self.bank({"min_spend": None, "max_cpa": 60.0, "min_roas": None}, {"min_spend": 50.0, "min_roas": 1.0})
        _, d = FV.write(self.root, "acme", "2026-11-15")
        self.assertEqual([e["name"] for e in d["five"]], ["A", "C", "E", "F", "vid"])   # E clears CPA 60 at ROAS 0.8

    def test_the_verb(self):
        self.assertEqual(winners.main(["--root", str(self.root), "five", "--brand", "acme"]), 0)
        self.assertTrue((self.root / self.home / "brief-five.json").is_file())


if __name__ == "__main__":
    unittest.main()
