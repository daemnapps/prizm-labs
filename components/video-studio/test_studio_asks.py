"""Studio asks (studio_asks.py) and the live-ads, creators and knowledge routes the Studio reads. Fixture files only;
no Claude run, no network: the ask runner is faked."""
import json
import tempfile
import unittest
from pathlib import Path

import studio_asks as SA
import workflow_desk as WD


def put(root, ref, data):
    p = Path(root) / ref
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data))
    return p


class Asks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "brands/acme").mkdir(parents=True)
        put(self.root, "brands/acme/variables/copy.md", "old voice")
        self.old = (SA.WS, WD.WS, SA.start_worker)
        SA.WS = WD.WS = self.root
        SA.start_worker = lambda: None

    def tearDown(self):
        SA.WS, WD.WS, SA.start_worker = self.old
        self.tmp.cleanup()

    def test_create_checks_the_ask(self):
        with self.assertRaises(ValueError):
            SA.create("nope", "acme", "x")
        with self.assertRaises(ValueError):
            SA.create("deeper", "ghost", "x")
        with self.assertRaises(ValueError):
            SA.create("tune", "acme", "music")
        with self.assertRaises(ValueError):
            SA.create("swipe", "acme", "not a link")
        with self.assertRaises(ValueError):
            SA.create("connect", "", "no-slash")
        r = SA.create("deeper", "acme", "dry skin in winter")
        self.assertEqual(r["state"], "queued")
        self.assertEqual(SA.listing("acme")[0]["id"], r["id"])

    def test_prompt_carries_the_rules(self):
        r = SA.create("tune", "acme", "copy")
        p = SA.prompt_for(r)
        self.assertIn("brands/acme/variables/copy.draft.md", p)
        self.assertIn("Never go live", p)
        self.assertIn(r["dir"] + "/result.md", p)

    def test_run_writes_result_and_done(self):
        r = SA.create("deeper", "acme", "dry skin")
        def fake(cmd, d):
            (Path(d) / "result.md").write_text("Found it.\n")
            return 0, "ok"
        out = SA.run_one(r, runner=fake)
        self.assertEqual(out["state"], "done")
        self.assertEqual(SA.one("acme", r["id"])["result"], "Found it.\n")

    def test_usage_is_metered_per_brand_kind_and_brief(self):
        r = SA.create("variations", "acme", "brief 0042 · acme_ad")
        def fake(cmd, d):
            (Path(d) / "result.md").write_text("Planned.\n")
            (Path(d) / "run.log").write_text("")
            return 0, json.dumps({"type": "result", "total_cost_usd": 0.5, "duration_ms": 120000,
                                  "usage": {"input_tokens": 10, "output_tokens": 5}, "modelUsage": {"m": {}}})
        SA.run_one(r, runner=fake)
        u = SA.usage("acme")
        self.assertEqual((u["total"], u["jobs"]), (0.5, 1))
        self.assertEqual(u["by_brief"][0]["key"], "0042")
        self.assertEqual(u["by_kind"][0]["key"], "variations")

    def test_failed_run_says_why(self):
        r = SA.create("deeper", "acme", "dry skin")
        out = SA.run_one(r, runner=lambda cmd, d: (1, "boom"))
        self.assertEqual(out["state"], "failed")
        self.assertIn("boom", out["why"])

    def test_taste_draft_needs_the_owners_use(self):
        r = SA.create("tune", "acme", "copy")
        put(self.root, "brands/acme/variables/copy.draft.md", "sharper voice")
        one = SA.one("acme", r["id"])
        self.assertEqual((one["live"], one["draft"]), ("old voice", "sharper voice"))
        SA.use_taste("acme", "copy", True)
        v = self.root / "brands/acme/variables"
        self.assertEqual((v / "copy.md").read_text(), "sharper voice")
        self.assertEqual(len(list(v.glob("copy.before-*.md"))), 1)
        with self.assertRaises(ValueError):
            SA.use_taste("acme", "copy", True)

    def test_discard_keeps_the_live_file(self):
        put(self.root, "brands/acme/variables/copy.draft.md", "draft")
        SA.use_taste("acme", "copy", False)
        self.assertEqual((self.root / "brands/acme/variables/copy.md").read_text(), "old voice")
        self.assertFalse((self.root / "brands/acme/variables/copy.draft.md").exists())

    def test_live_ads_join_the_desk_calls_and_briefs(self):
        put(self.root, "runs/funnel-tracking/acme/2026-11-27/warehouse.json", {
            "spend_through": "2026-11-26", "spend": {"7": 100.0, "30": 400.0},
            "orders": {"7": {"blended": {"orders": 5, "revenue": 300.0}}, "30": {"blended": {"orders": 20, "revenue": 1200.0}}},
            "ads": [{"ad_id": "1", "ad_name": "acme_x_brief-0042_batch-a_icon", "spend7": "80", "buys7": "2",
                     "spend30": "300", "buys30": "6", "value30": "500"},
                    {"ad_id": "2", "ad_name": "untagged", "spend7": "20", "buys7": "0", "spend30": "100", "buys30": "0"}]})
        put(self.root, "runs/media-buying/acme/2026-11-26/report.json", {"asof": "2026-11-26", "rule": {"_what": "one line"},
            "flags": [{"id": "1", "action": "off", "why": "over in every window", "break_even": 30}]})
        d = WD.live_ads("acme")
        a = {x["id"]: x for x in d["ads"]}
        self.assertEqual((a["1"]["brief"], a["1"]["call"], a["1"]["cpa7"]), ("0042", "off", 40.0))
        self.assertIsNone(a["2"]["brief"])
        self.assertEqual(d["money"]["revenue"], {"7": 300.0, "30": 1200.0})

    def test_creators_and_knowledge(self):
        put(self.root, "runs/winners/acme/creators/2026-11-23/trybe.json", {"creators": 2, "submissions": 1,
            "people": [{"creator": "A", "spend": 10, "ads": 1}], "rows": [{"creator": "A", "status": "pending"}]})
        put(self.root, "brands/acme/content-creators/ann/profile.md", "# ann — creator profile\n")
        c = WD.creators("acme")
        self.assertEqual(c["read"]["creators"], 2)
        self.assertEqual(c["profiles"][0]["handle"], "ann")
        put(self.root, "docs/knowledge/knowledge.json", {"items": [
            {"kind": "Rule", "title": "Hooks stop the scroll", "text": "x"}, {"kind": "Lesson", "title": "Offers", "text": "y"}]})
        WD._KN.update(m=None, items=[])
        k = WD.knowledge("hooks")
        self.assertEqual((k["total"], [i["title"] for i in k["items"]]), (2, ["Hooks stop the scroll"]))


if __name__ == "__main__":
    unittest.main()
