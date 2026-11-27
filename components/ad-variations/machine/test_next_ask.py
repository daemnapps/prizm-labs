"""next_ask.py: a variation plan becomes the next ask. Offline, a scratch workspace, nothing generated.
Run: /usr/bin/python3 components/ad-variations/machine/test_next_ask.py"""
import importlib.util, json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import next_ask as NA  # noqa: E402


def variation(vid, title, blocked=None, ruling=None):
    return {"id": vid, "title": title, "changes": [{"variable": "V-hook.03", "from": "a", "to": "b"}],
            "locked": ["product_reveal"], "hypothesis": "h", "confirms_if": "c", "kills_if": "k",
            "recipe": {"blocked_by": blocked}, "needs_ruling": ruling, "cost": {"usd_own": 1.0, "hours": 1.0},
            "gates": []}


PLAN = {"schema": "ad-variations/1", "brand": "acme",
        "source": {"teardown_run": "runs/video-teardown/acme/proven-one", "metrics": {}, "video": "Shared Assets/x.mp4"},
        "variations": [variation("V00", "Control", blocked="a claim on the before and after needs a call"),
                       variation("V01", "Hook line", ruling="a real person's likeness"),
                       variation("V02", "Hook picture", blocked="None"),
                       variation("V03", "Captions")]}


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.repo = Path(self._t.name)
        self.folder = self.repo / "runs" / "ad-variations" / "acme" / "proven-one-matrix"
        self.folder.mkdir(parents=True)
        (self.folder / "variation-plan.json").write_text(json.dumps(PLAN))
        run = self.repo / "runs" / "video-teardown" / "acme" / "proven-one"
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "acme", "product": "widget", "brief": "brief-0007",
                                                  "brief_key": "acme_widget_brief-0007",
                                                  "audience": {"_avatar": "core-a", "_funnel": "prospect",
                                                               "_sub_avatar": "sub-b"}}))
        bank = self.repo / "brands" / "acme" / "products"
        bank.mkdir(parents=True)
        (bank / "offer-bank.md").write_text("# offers\n")

    def tearDown(self):
        self._t.cleanup()

    def go(self, **kw):
        return NA.run(self.folder, self.repo, "2026-11-18", **kw)


class NextAsk(Base):
    def test_files_the_first_variation_the_plan_does_not_hold(self):
        doc = self.go()
        self.assertEqual(doc["next"]["id"], "V02")                     # V00 is blocked, V01 needs a ruling
        ask = json.loads((self.repo / doc["next"]["ask"]).read_text())
        self.assertEqual((ask["brand"], ask["product"], ask["avatar"], ask["sub_avatar"], ask["asked"]),
                         ("acme", "widget", "core-a", "sub-b", "2026-11-18"))
        self.assertEqual(ask["ask"], "proven-one-matrix-v02")
        self.assertEqual(ask["offer"], {"bank": "brands/acme/products/offer-bank.md#widget", "lines": [], "never": []})
        self.assertEqual(ask["variation"]["id"], "V02")
        self.assertEqual(ask["variation"]["locked"], ["product_reveal"])
        self.assertEqual(ask["variation"]["source"]["brief"], "brief-0007")
        self.assertEqual(ask["variation"]["plan"], "runs/ad-variations/acme/proven-one-matrix/variation-plan.json")
        self.assertIn("variation planner's reader", ask["said"])       # never passed off as a person's words
        self.assertEqual(doc["next"]["missing"], [])

    def test_the_ask_reads_as_an_ask_to_the_strategists_own_check(self):
        doc = self.go()
        f = HERE.parents[1] / "creative-strategist" / "machine" / "ask.py"
        spec = importlib.util.spec_from_file_location("strategist_ask", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.check(json.loads((self.repo / doc["next"]["ask"]).read_text())), [])

    def test_held_variations_are_listed_with_the_plans_own_reason_never_skipped_silently(self):
        doc = self.go()
        self.assertEqual([h["id"] for h in doc["held"]], ["V00", "V01"])
        self.assertTrue(doc["held"][0]["why"].startswith("blocked: a claim"))
        self.assertTrue(doc["held"][1]["why"].startswith("needs a ruling: a real person"))
        self.assertEqual(json.loads((self.folder / "next-ask.json").read_text())["held"], doc["held"])

    def test_each_run_files_the_next_one_and_then_there_is_nothing_left(self):
        self.assertEqual(self.go()["next"]["id"], "V02")
        second = self.go()
        self.assertEqual(second["next"]["id"], "V03")
        self.assertEqual(second["asked"], ["V02", "V03"])
        third = self.go()
        self.assertIsNone(third["next"])
        self.assertEqual((third["left"], third["total"]), ([], 4))

    def test_the_winner_it_is_for_is_kept(self):
        self.assertEqual(NA.run(self.folder, self.repo, "2026-11-18", winner="acme-111")["winner"], "acme-111")
        self.assertEqual(self.go()["winner"], "acme-111")             # kept on the next run

    def test_a_dry_run_writes_nothing(self):
        doc = self.go(dry_run=True)
        self.assertEqual(doc["next"]["id"], "V02")
        self.assertFalse((self.folder / "asks").exists())
        self.assertFalse((self.folder / "next-ask.json").exists())

    def test_what_cannot_be_found_is_left_empty_and_named(self):
        (self.repo / "runs/video-teardown/acme/proven-one/run.json").write_text(json.dumps({"brand": "acme"}))
        (self.repo / "brands/acme/products/offer-bank.md").unlink()
        doc = self.go()
        self.assertEqual(doc["next"]["missing"], ["product", "avatar", "funnel", "offer bank"])
        ask = json.loads((self.repo / doc["next"]["ask"]).read_text())
        self.assertIsNone(ask["product"])
        self.assertIsNone(ask["offer"]["bank"])

    def test_a_file_that_is_not_a_plan_is_refused_by_name(self):
        (self.folder / "variation-plan.json").write_text(json.dumps({"schema": "other"}))
        self.assertEqual(NA.main([str(self.folder), "--repo", str(self.repo)]), 2)


if __name__ == "__main__":
    unittest.main()
