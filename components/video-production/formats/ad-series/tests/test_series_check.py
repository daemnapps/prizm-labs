"""series_check.py: the ledger checks L1 to L8 (FORMAT.md, "The ledger") and the format home's own shape."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location("series_check", HERE / "series_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GOOD = {
    "series": "brand_a-flex-test", "brand": "brand_a", "product": "flex",
    "contract": "the after side wins", "curve": "descending",
    "arc": [
        {"ad": 1, "task": "the loss and the stance", "brief": "a", "ask": "Get it below."},
        {"ad": 2, "task": "the evidence, replayed", "brief": "b", "ask": "Get it below."},
        {"ad": 3, "task": "the stakes go public", "brief": "c", "ask": "Get it below."},
    ],
    "carried": [{"id": "C1", "item": "the card", "source": "brands/x/card.md", "state": "clean", "ads": [1, 2, 3]}],
    "cast": [
        {"id": "P1", "who": "the stranger", "source": "owned", "state": "in", "ads": [1, 3]},
        {"id": "P2", "who": "creator", "source": "owned", "state": "out", "out_after": 2, "ads": [2]},
    ],
    "setups": [
        {"id": "F1", "setup": "the doubt", "planted": 2, "due": 3, "status": "paid", "paid": 3},
        {"id": "F2", "setup": "the brush", "planted": 1, "due": 2, "status": "paid", "paid": 2},
    ],
    "rules": [{"id": "R1", "rule": "up to 12,000 RPM, ten settings", "source": "brands/x/flex.md", "ads": [2]}],
    "proof": [
        {"ad": 1, "type": "verdict", "item": "her pick"},
        {"ad": 2, "type": "demonstration", "item": "the brush"},
        {"ad": 3, "type": "before-after", "item": "the card"},
    ],
}


class SeriesCheck(unittest.TestCase):
    def setUp(self):
        self.m = _mod()

    def codes(self, ledger):
        return [c for c, _m in self.m.check(ledger)]

    def test_good_ledger_passes(self):
        self.assertEqual(self.m.check(GOOD), [])

    def test_missing_kind(self):
        bad = copy.deepcopy(GOOD)
        del bad["rules"]
        self.assertEqual(self.codes(bad), ["L0"])

    def test_overdue_setup(self):
        bad = copy.deepcopy(GOOD)
        bad["setups"][1].update(status="planted", paid=None)
        self.assertIn("L1", self.codes(bad))

    def test_setup_due_on_last_ad_is_not_overdue_yet(self):
        ok = copy.deepcopy(GOOD)
        ok["setups"][0].update(status="planted", paid=None)
        self.assertNotIn("L1", self.codes(ok))

    def test_planned_ads_are_not_due_yet(self):
        ok = copy.deepcopy(GOOD)
        ok["current"] = 1
        ok["setups"][1].update(status="planted", paid=None)
        self.assertNotIn("L1", self.codes(ok))
        ok["current"] = 3
        self.assertIn("L1", self.codes(ok))

    def test_paid_setup_names_its_ad(self):
        bad = copy.deepcopy(GOOD)
        bad["setups"][0]["paid"] = None
        self.assertIn("L1", self.codes(bad))

    def test_out_cast_returns(self):
        bad = copy.deepcopy(GOOD)
        bad["cast"][1]["ads"] = [2, 3]
        self.assertIn("L2", self.codes(bad))

    def test_source_required(self):
        bad = copy.deepcopy(GOOD)
        bad["carried"][0]["source"] = ""
        self.assertIn("L3", self.codes(bad))

    def test_adjacent_proof_type(self):
        bad = copy.deepcopy(GOOD)
        bad["proof"][2]["type"] = "demonstration"
        self.assertIn("L4", self.codes(bad))

    def test_arc_needs_three_tasks(self):
        bad = copy.deepcopy(GOOD)
        bad["arc"] = bad["arc"][:2]
        self.assertIn("L5", self.codes(bad))

    def test_every_ad_asks(self):
        bad = copy.deepcopy(GOOD)
        bad["arc"][1]["ask"] = ""
        self.assertIn("L6", self.codes(bad))

    def test_creator_brief_ask_must_match_the_ledger(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            head = "# Creator brief: X\n\n**DRAFT. Not sent.**\n**Format:** problem_solution · **Length:** 30 s · **Ask:** %s\n"
            Path(d, "ok.md").write_text(head % "Get it below.")
            Path(d, "off.md").write_text(head % "Get it below and see for yourself.")
            ok = copy.deepcopy(GOOD)
            ok["arc"][0]["creator_brief"] = "ok.md"
            self.assertEqual(self.m.check(ok, d), [])
            bad = copy.deepcopy(GOOD)
            bad["arc"][0]["creator_brief"] = "off.md"
            self.assertEqual(self.codes_at(bad, d), ["L7"])
            gone = copy.deepcopy(GOOD)
            gone["arc"][1]["creator_brief"] = "nowhere.md"
            self.assertEqual(self.codes_at(gone, d), ["L7"])

    def test_a_setup_the_filed_brief_already_says_is_planted_no_later_than_that_ad(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "brief1.md").write_text('| S8 | "Does it actually work, though?" |')
            led = copy.deepcopy(GOOD)
            led["arc"][0]["brief_file"] = "brief1.md"
            led["setups"].append({"id": "F9", "setup": "Does it actually work though? (the doubt)", "planted": 2,
                                  "due": 3, "status": "planted", "paid": None})
            self.assertEqual(self.codes_at(led, d), ["L8"])
            led["setups"][-1].update({"planted": 1, "due": 1, "status": "paid", "paid": 1})
            self.assertEqual(self.codes_at(led, d), [])
            led["arc"][0]["brief_file"] = "nowhere.md"
            self.assertEqual(self.codes_at(led, d), ["L8"])

    def codes_at(self, ledger, base):
        return [c for c, _m in self.m.check(ledger, base)]

    def test_hot_rows_before_ad_3(self):
        h = self.m.hot(GOOD, 3)
        self.assertEqual([p["ad"] for p in h["proof"]], [1, 2])
        self.assertEqual([p["id"] for p in h["cast"]], ["P1"])


class Home(unittest.TestCase):
    def test_home_files(self):
        for name in ("FORMAT.md", "LEARNINGS.md", "format.json"):
            self.assertTrue((HERE / name).is_file(), name)

    def test_registered_once(self):
        # registered 2026-11-07: formats/sync.py writes its row from format.json; the draft name is gone
        self.assertFalse((HERE / "format.draft.json").is_file())
        self.assertIn('"home": "components/video-production/formats/%s/format.json"' % HERE.name,
                      (HERE.parent / "bank.json").read_text())

    def test_workflow_validates(self):
        import sys
        sys.path.insert(0, str(HERE.parents[1] / "machine"))
        import workflow_catalog as catalog
        doc = json.loads((HERE / "format.json").read_text())
        self.assertEqual(doc["id"], HERE.name)
        self.assertIn(doc["status"], ("draft", "approved", "deprecated"))
        self.assertEqual(catalog.validate(doc["playbook"]["workflow"]), [])


if __name__ == "__main__":
    unittest.main()
