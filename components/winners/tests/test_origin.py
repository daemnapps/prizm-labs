import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import score  # noqa: E402
import winners  # noqa: E402
from test_score import ad, fixture, stage, w  # noqa: E402
from test_winners import run  # noqa: E402


OLD = "acme-widget-static-ai-omar-king-acne-fix-void-twopanel-p005-9x16-260907a-a01"


class Origin(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        fixture(self.root)
        w(self.root, "components/image-teardown/briefs.json", {"briefs": {
            "acme_widget_brief-0001": {"brand": "acme", "title": "Chain title", "run": "runs/video-writing/acme/r1"},
            "acme_widget_brief-0002": {"brand": "acme", "title": "Song ad", "lane": "video-production", "type": "video-ai",
                                       "run": "runs/video-production/acme/song"},
            "acme_widget_brief-0003": {"brand": "acme", "type": "image-ai", "run": "pic-run"},
            "p005": {"brand": "acme", "brief": "brief-0005", "key": "acme_none_brief-0005", "run": None},
            "p006": {"brand": "other", "brief": "brief-0006", "key": "other_none_brief-0006", "run": None},
            "p007": {"brand": "acme", "brief": "brief-0007", "key": "acme_none_brief-0007", "title": "Old title", "run": None}}})
        w(self.root, "runs/video-writing/acme/r1/run.json", {"brief_key": "acme_widget_brief-0001", "stages": {
            "stage4b": stage("stage4b-hook-v21-owner.md", 21), "stage5": stage("stage5-ai-brief-v25-owner.md", 25)}})
        w(self.root, "runs/video-writing/acme/w2/run.json", {"stages": {"stage0": stage("triage-v2-owner.md", 2)}})
        w(self.root, "runs/video-production/acme/song/run.json", {"brief_from": "runs/video-writing/acme/w2/deliverable/5-brief.md"})
        pic = self.root / "runs/image-teardown/acme/pic-run"
        pic.mkdir(parents=True)
        (pic / "01-teardown.md").write_text("<!-- images: a.jpg | prompt: stage1-image-teardown-v6-owner.md | model: m -->\nbody\n")
        (pic / "03-injection.md").write_text("<!-- prompt: _prompt-3-learned.md | model: m -->\nbody\n")
        w(self.root, "runs/winners/acme/bank.json", {"brand": "acme", "bar": {}, "sources": [], "rows": [
            {"id": "acme-900", "name": "Script 30", "ad_ids": ["900"], "ad_names": ["Scrub Task 30 (Hook 2)"],
             "snapshots": [{"kind": "audit", "audit": "audit/w"}]},
            {"id": "acme-910", "name": "Proven Video", "ad_ids": ["910"], "ad_names": ["Proven Video"],
             "snapshots": [{"kind": "audit", "audit": "audit/w"}]}]})
        w(self.root, "runs/winners/acme/audit/w/merges.json", {"Same Footage": "Proven Video"})
        w(self.root, "runs/media-buying/acme/filter/2026-11-01/verdicts.json", {"data_through": "2026-10-31", "ads": [
            ad(1, "acme_widget_brief-0001_batch-2026-10-09-b_cpk-a", 100, 4, 2.0),       # chain
            ad(900, "Whatever it was called - Icon LP", 200, 10, 2.0),                   # banked by id
            ad(21, "Scrub Task 30 (Hook 9) - Copy", 300, 10, 1.0),                       # banked by script
            ad(22, "Same Footage - Actually Works LP", 50, 1, 1.0),                      # banked through merges.json
            ad(910, "acme_widget_brief-0002_batch-2026-10-09-b_cpk-a", 25, 1, 1.0),      # banked beats the brief
            ad(3, "acme_widget_brief-0002_batch-2026-10-09-c_cpk-a", 40, 1, 1.0),        # brief, song lane, linked prompts
            ad(4, "acme_widget_brief-0003_batch-2026-10-09-b_cpk-a", 30, 0, 0.0),        # brief, image run's headers
            ad(5, "acme_widget_brief-0099_batch-2026-10-09-b_cpk-a", 20, 0, 0.0),        # brief, not in the register
            ad(6, OLD, 10, 0, 0.0),                                                      # old form, p005
            ad(7, "ai_bs_p007_v1 - Copy", 15, 1, 1.0),                                   # bare p-number, register title
            ad(8, "ai_bs_p006_v1", 12, 0, 0.0),                                          # p-number another brand holds
            ad(9, "Old Founder Story - 311385264607819 - Copy", 600, 12, 1.5),           # pre-system, over the line
            ad(10, "Small old one", 5, 0, 0.0)]})
        self.o = score.build(self.root, "acme")
        self.ads = {r["ad_id"]: r for r in self.o["matched"] + self.o["unmatched"]}

    def tearDown(self):
        self._t.cleanup()

    def origin(self, i):
        return self.ads[str(i)]["origin"]

    def test_each_origin_in_order(self):
        self.assertEqual(self.origin(1), "chain")
        self.assertEqual(self.ads["1"]["family"], "Chain title")
        for i, row in ((900, "acme-900"), (21, "acme-900"), (22, "acme-910"), (910, "acme-910")):
            self.assertEqual(self.origin(i), "banked", i)
            self.assertEqual(self.ads[str(i)]["bank_row"], row)
        self.assertEqual(self.ads["21"]["family"], "Script 30")
        for i in (3, 4, 5, 6, 7):
            self.assertEqual(self.origin(i), "brief, made outside writing", i)
        for i in (8, 9, 10):
            self.assertEqual(self.origin(i), "pre-system", i)
        self.assertEqual(self.ads["9"]["family"], "Old Founder Story")

    def test_brief_rows_say_where_they_were_made(self):
        self.assertEqual(self.ads["3"]["family"], "Song ad")
        self.assertEqual(self.ads["3"]["made_in"], "video-production / video-ai")
        self.assertEqual([p["label"] for p in self.ads["3"]["prompt_other"]], ["triage v2"])
        self.assertEqual(self.ads["4"]["made_in"], "image-ai")
        self.assertEqual(self.ads["4"]["family"], "pic-run")
        self.assertEqual([p["label"] for p in self.ads["4"]["prompt_other"]], ["stage1-image-teardown v6"])
        self.assertEqual(self.ads["5"]["made_in"], "unknown")
        self.assertNotIn("prompt_other", self.ads["5"])
        self.assertEqual(self.ads["7"]["family"], "Old title")
        self.assertEqual({r["version"] for r in self.o["by_other_prompt"]}, {"triage v2", "stage1-image-teardown v6"})

    def test_old_names_read_their_brief(self):
        self.assertEqual(self.ads["6"]["brief_as_named"], "p005")
        self.assertEqual(self.ads["7"]["brief_as_named"], "p007")
        self.assertEqual(self.ads["7"]["brief_key"], "acme_none_brief-0007")
        self.assertEqual(self.o["counts"]["old_name_briefs"], 2)

    def test_every_dollar_is_accounted_for(self):
        rows = self.o["by_origin"]
        self.assertEqual(sum(r["ads"] for r in rows), self.o["counts"]["ads"])
        self.assertAlmostEqual(sum(r["spend"] for r in rows), sum(r["spend"] for r in self.ads.values()), 2)
        self.assertAlmostEqual(sum(r["share"] for r in rows), 1, 3)
        self.assertEqual([r["origin"] for r in rows], list(score.ORIGINS))
        self.assertEqual(self.o["counts"]["matched"], 1)      # readers of matched still get chain ads only
        self.assertEqual(self.o["counts"]["unmatched"], 12)

    def test_page(self):
        md = score.render_md(self.o)
        self.assertLess(md.index("## Every dollar by origin"), md.index("## By hook prompt version"))
        self.assertNotIn("not joined:", md)
        self.assertIn("| Total | 13 | $1,407.00 | 100.0% |", md)
        self.assertIn("## Other prompts", md)
        self.assertIn("## Top families by spend", md)
        cant = md[md.index("## Can't trace"):md.index("## Joined ads")]
        self.assertIn("Old Founder Story", cant)
        self.assertNotIn("Small old one", cant)

    def test_status_line(self):
        self.assertEqual(score.origin_line({}), None)
        line = score.origin_line(self.o)
        self.assertIn("$100 traced to a chain prompt", line)
        self.assertIn("$575 banked winners", line)
        self.assertIn("$115 brief outside writing", line)
        self.assertIn("$617 pre-system", line)
        score.write(self.root, self.o)
        code, out, _ = run(self.root, "status", "--brand", "acme")
        self.assertEqual(code, 0)
        self.assertIn(line, out)


if __name__ == "__main__":
    unittest.main()
