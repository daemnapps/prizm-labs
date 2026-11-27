import contextlib, io, json, sys, tempfile, types, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import who_view as WV  # noqa: E402
import winners  # noqa: E402

AIMS = {"acme_flex_brief-0001": {"avatar": "man", "sub": "night", "demographic": "none", "desire": "clear skin", "awareness": "unaware", "doubt": "for-me"},
        "acme_flex_brief-0002": {"avatar": "man", "sub": None, "demographic": None, "desire": None, "awareness": "unaware", "doubt": None},
        "p138": {"avatar": "woman", "sub": "old"}}


class FakeAims:
    brand = "acme"
    N = types.SimpleNamespace(full_brief_key=lambda n: "acme_flex_brief-0002" if "brief-0002" in n else None)

    def of(self, key):
        return AIMS.get(key) or {}


def w(root, rel, obj):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def ad(i, name, spend, buys, **k):
    return {"ad_id": str(i), "ad_name": name, "spend": spend, "purchases": buys, **k}


class Who(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        (self.root / "brands" / "acme").mkdir(parents=True)
        w(self.root, "runs/winners/acme/score/2026-10-20/score.json", {"since": "2026-10-13", "data_through": "2026-10-19", "matched": [],
                                                                       "unmatched": [ad(1, "a", 5, 1, brief_key="acme_flex_brief-0001")]})
        w(self.root, "runs/winners/acme/score/2026-11-04/score.json", {"since": "2026-08-06", "data_through": "2026-11-03",
          "matched": [ad(1, "a", 100, 12, brief_key="acme_flex_brief-0001")],
          "unmatched": [ad(2, "acme_flex_brief-0002_x_old", 50, 1), ad(3, "old p138", 20, 1, brief_key="acme_none_brief-0138", brief_as_named="p138"),
                        ad(4, "no number", 400, 20), ad(5, "carded", 30, 0), ad(6, "in an ad set", 10, 0)]})
        w(self.root, "runs/meta-upload/acme/ADS-INDEX.json", {"briefs": [
            {"brief": "acme_flex_brief-0002", "number": "0002", "avatar": "man", "sub_avatar": "carded-sub", "meta_ad_ids": ["5"], "cards": []},
            {"brief": "acme_none", "meta_ad_ids": ["6"], "cards": [{"meta_ads": [{"ad_id": "6", "ad_set": "adset_acme_woman_its-claim"}]}]}]})

    def tearDown(self):
        self._t.cleanup()

    def build(self, **k):
        return WV.build(self.root, "acme", aims=FakeAims(), **k)

    def test_every_ad_is_in_every_dimension_once(self):
        o = self.build()
        for k, _ in WV.DIMS:
            d = o["by"][k]
            rows = d["rows"] + [d["unknown"]]
            self.assertEqual((sum(x["ads"] for x in rows), sum(x["spend"] for x in rows), sum(x["purchases"] for x in rows)), (6, 610, 34))

    def test_join_and_numbers(self):
        o = self.build()
        a = {r["ad_id"]: r for r in o["ads"]}
        self.assertEqual([a[i]["brief"] for i in "123456"], ["acme_flex_brief-0001", "acme_flex_brief-0002", "p138", None, "acme_flex_brief-0002", None])
        self.assertEqual((a["5"]["joined_by"], a["5"]["sub"]), ("its approval card", "carded-sub"))
        self.assertEqual((a["6"]["avatar"], a["6"]["avatar_from"], a["6"]["sub"]), ("woman", "its ad set", None))
        aw = {x["value"]: x for x in o["by"]["awareness"]["rows"]}["unaware"]
        self.assertEqual((aw["ads"], aw["spend"], aw["purchases"], aw["cpa"], aw["few"]), (3, 180, 13, 13.85, False))
        u = o["by"]["awareness"]["unknown"]
        self.assertEqual((u["ads"], u["no_brief"]["ads"], u["brief_does_not_say"]["ads"]), (3, 2, 1))
        self.assertEqual(o["by"]["doubt"]["coverage"], {"ads": 16.7, "spend": 16.4, "purchases": 35.3})
        self.assertIn("man / night", [x["value"] for x in o["by"]["sub"]["rows"]])

    def test_page_marks_few_sales_and_always_shows_unknown(self):
        md = WV.render(self.build())
        self.assertEqual(md.count("| unknown |"), len(WV.DIMS))
        self.assertIn("| woman | 2 | $30.00 | 1 | $30.00 | few sales |", md)
        self.assertIn("| man / night | 1 | $100.00 | 12 | $8.33 |  |", md)
        self.assertIn("none (no face on screen)", md)

    def test_days_takes_the_nearest_window_and_says_so(self):
        self.assertIsNone(self.build(days=90)["note"])
        o = self.build(days=14)
        self.assertEqual((o["days"], o["total"]["ads"]), (7, 1))
        self.assertIn("nearest score on disk covers 7", o["note"])

    def test_desk_source_reads_live_ads_only_and_refuses_a_window_it_lacks(self):
        w(self.root, "runs/media-buying/acme/2026-11-23/report.json", {"asof": "2026-11-23", "flags": [
            {"kind": "campaign", "id": "9", "name": "c", "spend": 999}, {"kind": "ad", "id": "1", "name": "a", "spend": 40, "purchases": 2, "windows": {"7": {"spend": 9, "sales": 1}}}]})
        real, WV.S.build = WV.S.build, lambda root, brand, res=None: {"matched": [], "unmatched": res["ads"]}
        try:
            self.assertEqual(self.build(source="desk")["total"]["spend"], 40)
            o = self.build(source="desk", days=7)
            self.assertEqual((o["total"]["spend"], o["total"]["purchases"]), (9, 1))
            self.assertIn("switched off", o["note"])
            with self.assertRaises(WV.BadInput):
                self.build(source="desk", days=30)
        finally:
            WV.S.build = real

    def test_command_writes_the_markdown_copy_and_nothing_else(self):
        real, WV.load_aims = WV.load_aims, lambda root, brand: FakeAims()
        before = {p for p in self.root.rglob("*") if p.is_file()}
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                self.assertEqual(winners.main(["--root", str(self.root), "who", "--brand", "acme"]), 0)
        finally:
            WV.load_aims = real
        new = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file() and p not in before)
        self.assertEqual([x.split("/")[-1] for x in new], ["who.json", "who.md"])
        self.assertTrue(new[0].startswith("runs/winners/acme/who-"))

    def test_no_score_is_one_sentence(self):
        (self.root / "brands" / "bare").mkdir()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(winners.main(["--root", str(self.root), "who", "--brand", "bare"]), 2)
        self.assertIn("no score on disk", err.getvalue())


if __name__ == "__main__":
    unittest.main()
