import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import bank  # noqa: E402
import creators  # noqa: E402
import feed  # noqa: E402
import winners  # noqa: E402
from test_bank import audit, row, w  # noqa: E402


def results(root, rows, since="2026-08-17", until="2026-11-14"):
    p = Path(root) / "runs/winners/acme/creators" / until / "trybe.json"
    w(p.parent, p.name, {"brand": "acme", "made": until + "T07:00:00", "from": since, "to": until, "rows": rows})
    return p


def vid(tid, creator, spend, buys, value, ad_ids=None, names=None):
    meta = None if spend is None else {"spend": spend, "meta_purchases": buys, "meta_purchase_value": value,
                                       "impressions": 1000, "ad_ids": ad_ids or [], "ad_names": names or []}
    return {"trybe_id": tid, "creator": creator, "status": "approved", "meta": meta}


def check(root, tid, fmt, angle, hook, label="2026-11-14", state="checked"):
    w(Path(root) / "runs/creator-machine/acme" / label / "checks", tid + ".json",
      {"trybe_id": tid, "state": state, "format": fmt, "angle": angle, "hook_line": hook, "worked": "it stops the thumb"})


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.a1 = audit(self.root, "2025", "2025-01-01", "2026-11-02",
                        [row(1, "Script 30", ["111"], 1000, 50, 1500), row(2, "Dud", ["221"], 900, 5, 300)])
        bank.main(["--brand", "acme", "--root", str(self.root), "--audit", str(self.a1)])
        check(self.root, "aaaa1111", "story b-roll", "razor bumps", "Bumps again?")
        check(self.root, "bbbb2222", "talking head", "razor bumps", "I tried everything")
        check(self.root, "cccc3333", "talking head", "the sale", "On sale today")
        self.res = results(self.root, [
            vid("aaaa1111", "Ann", 120.0, 4, 260.0, ["901"], ["UGC_x_aaaa1111"]),
            vid("bbbb2222", "Bo", 80.0, 1, 60.0, ["902"], ["UGC_y_bbbb2222"]),
            vid("cccc3333", "Cy", 70.0, 0, 0.0, ["903"], ["UGC_z_cccc3333"]),
            vid("dddd4444", "Di", None, 0, 0)])

    def tearDown(self):
        self._t.cleanup()

    def bank(self):
        return json.loads((self.root / "runs/winners/acme/bank.json").read_text())

    def run_creators(self):
        return creators.main(["--brand", "acme", "--root", str(self.root), "--results", str(self.res)])

    def test_creator_videos_land_in_the_bank_with_tags(self):
        self.assertEqual(self.run_creators(), 0)
        rows = {r.get("trybe_id"): r for r in self.bank()["rows"] if r.get("trybe_id")}
        self.assertEqual(set(rows), {"aaaa1111", "bbbb2222", "cccc3333"})   # no spend, no row
        a = rows["aaaa1111"]
        self.assertEqual(a["id"], "acme-901")
        self.assertEqual(a["tags"]["format"], "story b-roll")
        self.assertEqual(a["tags"]["angle"], "razor bumps")
        self.assertEqual(a["words"]["hook"], "Bumps again?")
        self.assertEqual(a["snapshots"][-1]["kind"], "creator")
        self.assertEqual(a["snapshots"][-1]["roas"], 2.17)
        self.assertEqual(a["state"], "candidate")   # bar open
        self.assertEqual(len(self.bank()["rows"]), 5)

    def test_rerun_same_window_changes_nothing_and_ids_stay(self):
        self.run_creators()
        before = self.bank()
        self.run_creators()
        self.assertEqual(self.bank(), before)

    def test_an_audit_row_ending_in_the_trybe_id_is_the_same_row(self):
        b = self.bank()
        b["rows"][1]["ad_names"].append("Creator ad_aaaa1111")
        (self.root / "runs/winners/acme/bank.json").write_text(json.dumps(b))
        res = results(self.root, [vid("aaaa1111", "Ann", 120.0, 4, 260.0)], until="2026-11-13")
        creators.main(["--brand", "acme", "--root", str(self.root), "--results", str(res)])
        r = [x for x in self.bank()["rows"] if x.get("trybe_id") == "aaaa1111"]
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["id"], "acme-221")
        self.assertEqual(r[0]["name"], "Dud")   # the audit's name stays

    def test_open_bar_brief_next_is_candidates_with_a_purchase(self):
        self.run_creators()
        d = json.loads((self.root / "runs/winners/acme/brief-next.json").read_text())
        self.assertTrue(d["bar_open"])
        self.assertEqual(d["basis"], "candidates")
        self.assertEqual([e["format"] for e in d["formats"]], ["story b-roll", "talking head"])
        self.assertEqual(d["formats"][1]["videos"], 1)   # the zero-purchase video is not a candidate
        self.assertEqual(d["angles"][0]["angle"], "razor bumps")
        self.assertEqual(d["angles"][0]["purchases"], 5)
        self.assertEqual(d["avoid"], [])
        self.assertEqual(sum(e["videos"] for e in d["tried"]["formats"]), 3)
        self.assertEqual(d["status"], "draft")
        self.assertIn("## Formats to brief more of", (self.root / "runs/winners/acme/brief-next.md").read_text())
        self.assertEqual(creators.winner_ids(self.root, "acme"), set())

    def test_the_one_bar_decides_winners_feed_and_avoid(self):
        self.run_creators()
        self.assertEqual(winners.main(["bar", "--brand", "acme", "--root", str(self.root),
                                       "--min-spend", "50", "--min-roas", "1.0"]), 0)
        rows = {r.get("trybe_id"): r for r in self.bank()["rows"] if r.get("trybe_id")}
        self.assertEqual(rows["aaaa1111"]["state"], "winner")
        self.assertEqual(rows["bbbb2222"]["state"], "candidate")   # ROAS 0.75
        self.assertEqual(creators.winner_ids(self.root, "acme"), {"aaaa1111"})
        d = json.loads((self.root / "runs/winners/acme/brief-next.json").read_text())
        self.assertEqual(d["basis"], "winners")
        self.assertEqual([e["format"] for e in d["formats"]], ["story b-roll"])
        self.assertEqual([a["format"] for a in d["avoid"]], ["talking head"])
        md = (self.root / "runs/winners/acme/feed.md").read_text()
        self.assertIn("## Creator videos", md)
        self.assertIn("trybe aaaa1111", md)
        self.assertNotIn("trybe bbbb2222", md)
        self.assertIn("Format: story b-roll · Angle: razor bumps", md)

    def test_creator_bar_judges_creator_videos_and_leaves_paid_rows_alone(self):
        winners.main(["creators", "--brand", "acme", "--root", str(self.root), "--results", str(self.res)])
        paid_before = [r for r in self.bank()["rows"] if not r.get("trybe_id")]
        feed_before = (self.root / "runs/winners/acme/feed.md").read_text().split("## Creator videos")[0]
        self.assertEqual(winners.main(["bar", "--brand", "acme", "--root", str(self.root), "--creators",
                                       "--min-spend", "50", "--min-purchases", "1", "--min-roas", "1.0"]), 0)
        b = self.bank()
        self.assertEqual(b["bar"], {"min_spend": None, "max_cpa": None, "min_roas": None})
        self.assertEqual(b["creator_bar"], {"min_spend": 50.0, "max_cpa": None, "min_roas": 1.0, "min_purchases": 1.0})
        self.assertEqual([r for r in b["rows"] if not r.get("trybe_id")], paid_before)   # Script 30 would clear it
        self.assertEqual((self.root / "runs/winners/acme/feed.md").read_text().split("## Creator videos")[0], feed_before)
        self.assertEqual({r["trybe_id"]: r["state"] for r in b["rows"] if r.get("trybe_id")},
                         {"aaaa1111": "winner", "bbbb2222": "candidate", "cccc3333": "candidate"})
        self.assertEqual(creators.winner_ids(self.root, "acme"), {"aaaa1111"})
        d = json.loads((self.root / "runs/winners/acme/brief-next.json").read_text())
        self.assertEqual((d["basis"], d["bar_open"]), ("winners", False))
        self.assertEqual([a["format"] for a in d["avoid"]], ["talking head"])
        self.assertEqual(winners.main(["bar", "--brand", "acme", "--root", str(self.root), "--min-purchases", "1"]), 2)

    def test_feed_without_creator_rows_is_unchanged(self):
        feed.write(self.root, "acme")
        self.assertNotIn("Creator videos", (self.root / "runs/winners/acme/feed.md").read_text())

    def test_unread_video_says_so(self):
        res = results(self.root, [vid("eeee5555", "Ed", 60.0, 2, 150.0, ["905"])], until="2026-11-12")
        creators.main(["--brand", "acme", "--root", str(self.root), "--results", str(res)])
        d = json.loads((self.root / "runs/winners/acme/brief-next.json").read_text())
        self.assertNotIn(creators.NOT_READ, [e["format"] for e in d["formats"]])   # swipe pick matches on format words
        self.assertIn(creators.NOT_READ, [e["format"] for e in d["tried"]["formats"]])

    def test_catch_all_tags_stay_out_of_what_to_brief(self):
        check(self.root, "ffff6666", "other", "none shown; it sells the sale", "Big sale today")
        res = results(self.root, [vid("aaaa1111", "Ann", 120.0, 4, 260.0, ["901"]),
                                  vid("ffff6666", "Fe", 40.0, 9, 400.0, ["906"])], until="2026-11-11")
        creators.main(["--brand", "acme", "--root", str(self.root), "--results", str(res)])
        d = json.loads((self.root / "runs/winners/acme/brief-next.json").read_text())
        self.assertEqual([e["format"] for e in d["formats"]], ["story b-roll"])
        self.assertEqual([e["angle"] for e in d["angles"]], ["razor bumps"])
        self.assertIn("other", [e["format"] for e in d["tried"]["formats"]])
        h = [x for x in d["hooks"] if x["trybe_id"] == "ffff6666"][0]   # the hook line is kept, its catch-alls are not
        self.assertEqual((h["format"], h["angle"]), (None, None))
        for t in ("Other", "none shown; it sells", "N/A", "unclear", "", None):
            self.assertTrue(creators.vague(t), t)
        for t in ("story b-roll", "talking head", "razor bumps", "nonetheless"):
            self.assertFalse(creators.vague(t), t)

    def test_verb_reads_a_given_results_file(self):
        self.assertEqual(winners.main(["creators", "--brand", "acme", "--root", str(self.root),
                                       "--results", str(self.res)]), 0)
        self.assertTrue((self.root / "runs/winners/acme/brief-next.md").is_file())


if __name__ == "__main__":
    unittest.main()
