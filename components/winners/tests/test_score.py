import json, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.insert(0, str(COMPONENT))
sys.path.append(str(COMPONENT.parent / "run-kit"))
from run_kit import paths  # noqa: E402
import score  # noqa: E402

REPO = paths.repo(__file__)


def w(root, rel, obj):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def stage(name, v=2):
    return {"prompt_name": name, "version": v, "status": "done"}


def ad(i, name, spend, purch, roas):
    return {"ad_id": str(i), "ad_name": name, "spend": spend, "purchases": purch,
            "cpa": spend / purch if purch else None, "roas": roas}


def fixture(root):
    # real naming module is needed; link it in by symlink so the fixture root stays read-only to the repo
    (Path(root) / "components").mkdir(parents=True)
    (Path(root) / "components" / "naming").symlink_to(REPO / "components" / "naming")
    (Path(root) / "components" / "run-kit").symlink_to(REPO / "components" / "run-kit")
    (Path(root) / "components" / "brandpath").symlink_to(REPO / "components" / "brandpath")
    w(root, "runs/media-buying/brand_a/filter/2026-10-20/verdicts.json", {"data_through": "2026-10-19", "ads": [
        ad(1, "brand_a_flex_brief-0019_batch-2026-10-09-b_cpk-a", 100, 4, 2.0),
        ad(2, "brand_a_flex_brief-0020_batch-2026-10-09-b_cpk-a", 50, 1, 1.0),
        ad(3, "brand_a_flex_brief-0021_batch-2026-10-09-b_cpk-a", 10, 0, 0.0),
        ad(4, "brand_a_flex_brief-0099_batch-2026-10-09-b_cpk-a", 5, 0, 0.0),
        ad(5, "garbage name", 1, 0, 0.0)]})
    w(root, "components/image-teardown/briefs.json", {"briefs": {
        "brand_a_flex-face-brush_brief-0019": {"run": "runs/video-writing/brand_a/r19"},
        "brand_a_flex-face-brush_brief-0020": {"run": "runs/video-production/brand_a/elsewhere"},
        "brand_a_flex-face-brush_brief-0021": {"run": "runs/video-writing/brand_a/r21"}}})
    w(root, "runs/video-writing/brand_a/r19/run.json", {"brief_key": "brand_a_flex-face-brush_brief-0019", "stages": {
        "stage4b": stage("stage4v2a-readhooks-v8-owner.md"), "stage5": stage("stage5-ai-brief-v6-owner.md")}})
    w(root, "runs/video-writing/brand_a/r20/run.json", {"brief": "brief-0020", "product": "flex", "stages": {
        "stage4b": stage("stage4b-hook-v21-owner.md", 21), "stage5": stage("stage5-ai-brief-v25-owner.md", 25)}})
    w(root, "runs/video-writing/brand_a/r21/run.json", {"brief_key": "brand_a_flex-face-brush_brief-0021", "stages": {
        "stage0": stage("triage-v3.md", 3)}})


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        fixture(self.root)

    def tearDown(self):
        self._t.cleanup()

    def test_join(self):
        o = score.build(self.root, "brand_a")
        self.assertEqual(o["asof"], "2026-10-20")
        self.assertEqual(o["counts"]["matched"], 2)
        self.assertEqual(o["counts"]["unmatched"], 3)
        m = {r["ad_id"]: r for r in o["matched"]}
        self.assertEqual(m["1"]["hook_prompt"]["version"], 8)       # from name, not version=2
        self.assertEqual(m["1"]["joined_by"], "register run path")
        self.assertEqual(m["2"]["joined_by"], "run.json brief match")  # register path points at production
        self.assertEqual(m["2"]["brief_prompt"]["label"], "stage5-ai-brief v25")
        reasons = {r["ad_id"]: r["reason"] for r in o["unmatched"]}
        self.assertIn("no hook or brief", reasons["3"])
        self.assertIn("not in register", reasons["4"])
        self.assertIn("does not parse", reasons["5"])

    def test_rollup(self):
        o = score.build(self.root, "brand_a")
        r = {x["version"]: x for x in o["by_hook_prompt"]}["stage4v2a-readhooks v8"]
        self.assertEqual((r["ads"], r["spend"], r["purchases"], r["cpa"], r["roas"]), (1, 100, 4, 25.0, 2.0))

    def test_cli_writes_and_bad_input(self):
        cmd = [sys.executable, str(COMPONENT / "score.py"), "--root", str(self.root)]
        self.assertEqual(subprocess.run(cmd + ["--brand", "brand_a"], capture_output=True).returncode, 0)
        d = self.root / "runs/winners/brand_a/score/2026-10-20"
        self.assertTrue((d / "score.json").is_file() and (d / "score.md").is_file())
        self.assertIn("asof: 2026-10-20", (d / "score.md").read_text())
        self.assertIn("Results from: the media-buying file dated 2026-10-20", (d / "score.md").read_text())
        p = subprocess.run(cmd + ["--brand", "nobrand"], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        (self.root / "components/image-teardown/briefs.json").write_text("{not json")
        self.assertNotEqual(subprocess.run(cmd + ["--brand", "brand_a"], capture_output=True).returncode, 0)


class Upgrades(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        fixture(self.root)

    def tearDown(self):
        self._t.cleanup()

    def test_register_entries_by_own_key_and_bare_label(self):
        # an entry under a p-number answers to its `key`; its `run` is a bare label, not a path
        w(self.root, "components/image-teardown/briefs.json", {"briefs": {
            "p099": {"key": "brand_a_flex-face-brush_brief-0099", "run": "r99"}}})
        w(self.root, "runs/video-teardown/brand_a/r99/run.json", {"stages": {"stage4b": stage("stage4b-hook-v21-owner.md", 21)}})
        o = score.build(self.root, "brand_a")
        m = {r["ad_id"]: r for r in o["matched"]}
        self.assertEqual(m["4"]["joined_by"], "register run label")
        self.assertEqual(m["4"]["run"], "runs/video-teardown/brand_a/r99")
        self.assertEqual(o["counts"]["brief_keys_in_register"], 1)

    def test_rollup_by_borrowed_from_lists_every_id_and_none(self):
        (self.root / "runs/video-writing/brand_a/r19/stages").mkdir(parents=True)
        (self.root / "runs/video-writing/brand_a/r19/stages/4b-hooks.md").write_text(
            "BORROWED_FROM V1: brand_a-111 · the question\nBORROWED_FROM V2: none\nBORROWED_FROM V3: `brand_a-222`\n"
            "BORROWED_FROM V4: brand_a-111\n")
        o = score.build(self.root, "brand_a")
        m = {r["ad_id"]: r for r in o["matched"]}
        self.assertEqual(m["1"]["borrowed_from"], ["brand_a-111", "brand_a-222"])
        self.assertEqual(m["2"]["borrowed_from"], ["none"])
        r = {x["version"]: x for x in o["by_borrowed_from"]}
        self.assertEqual((r["brand_a-111"]["ads"], r["brand_a-111"]["spend"]), (1, 100))
        self.assertEqual((r["none"]["ads"], r["none"]["spend"]), (1, 50))
        self.assertIn("## By winner borrowed from", score.render_md(o))

    def test_results_fall_back_to_the_file_and_say_so(self):
        import audit as A
        real = A.warehouse_ads

        def down(*a, **k):
            raise RuntimeError("warehouse: no route")
        A.warehouse_ads = down
        self.addCleanup(setattr, A, "warehouse_ads", real)
        res = score.results(self.root, "brand_a", 90)
        self.assertEqual(res["asof"], "2026-10-20")
        self.assertIn("warehouse could not be used", res["used"])
        self.assertIn("warehouse could not be used", score.build(self.root, "brand_a", res=res)["results_from"])

    def test_results_from_the_warehouse(self):
        import datetime as dt
        import audit as A
        real = A.warehouse_ads
        A.warehouse_ads = lambda b, s, u, monthly=False: [
            dict(ad_id="1", ad_name="brand_a_flex_brief-0019_batch-2026-10-09-b_cpk-a", spend=100.0, purchases=4.0, value=200.0, last="2026-11-02"),
            dict(ad_id="9", ad_name="zero spend", spend=0.0, purchases=0.0, value=0.0, last="2026-11-03")]
        self.addCleanup(setattr, A, "warehouse_ads", real)
        res = score.results(self.root, "brand_a", 90, today=dt.date(2026, 11, 4))
        self.assertEqual((res["asof"], res["since"], res["data_through"]), ("2026-11-04", "2026-08-06", "2026-11-02"))
        self.assertEqual(len(res["ads"]), 1)
        o = score.build(self.root, "brand_a", res=res)
        self.assertEqual(o["matched"][0]["value"], 200.0)
        self.assertEqual(o["matched"][0]["roas"], 2.0)
        self.assertIn("trailing 90 days", score.render_md(o))


if __name__ == "__main__":
    unittest.main()
