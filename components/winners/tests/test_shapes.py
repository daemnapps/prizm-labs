import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shapes as SH

CONTROLS = {"arcs": [{"id": "rise", "name": "Rise", "what": "Up.", "beats": [{"beat": "low"}, {"beat": "high"}]},
                     {"id": "fall", "name": "Fall", "what": "Down.", "beats": [{"beat": "high"}, {"beat": "low"}]}],
            "story_devices": [{"id": "twist"}, {"id": "the-receipt"}]}
NAMES = {k: {"names": [{"id": v}]} for k, v in (("production_format", "single-presenter"), ("script_format", "demonstration"), ("hook_format", "split-screen"))}
PRESETS = {"presets": [{"id": "card-a", "arc": "rise", "devices": ["twist"], "format": {}}, {"id": "card-b", "arc": "fall", "devices": ["the-receipt", "twist"], "format": {}}]}


def row(run, n, cpa, spend=None, call="keep", copy_of=None):
    return {"run": run, "label": "W " + run, "copy_of": copy_of, "retire": {"call": call, "why": "x"}, "traits": {"runtime": 30},
            "proof": {"purchases": n, "cpa": cpa, "spend": spend, "roas": 1.2}}


def call(run, arc="rise", fit="clear", devices=("twist",)):
    return {"run": run, "arc": arc, "fit": fit, "why": "w", "devices": list(devices), "production_format": "single-presenter",
            "script_format": "demonstration", "hook_format": None, "teller": "creator", "flag": None, "proof_lines": ["T1: a line"]}


class T(unittest.TestCase):
    def setUp(self):
        self.r = Path(tempfile.mkdtemp())
        cc = self.r / SH.CC
        (cc / "research").mkdir(parents=True)
        (cc / "controls.json").write_text(json.dumps(CONTROLS))
        (cc / "story_presets.json").write_text(json.dumps(PRESETS))
        f = self.r / "components/video-production/formats"
        f.mkdir(parents=True)
        (f / "names.json").write_text(json.dumps(NAMES))
        self.w = self.r / "runs/winners/acme"
        (self.w / "shapes").mkdir(parents=True)

    def put(self, rows, calls):
        (self.w / "winner-index.json").write_text(json.dumps({"winners": rows, "snapshot": "2026-01-01"}))
        (self.w / "shapes/calls.json").write_text(json.dumps({"calls": calls}))

    def test_an_uncalled_winner_fails_the_check_and_shows_in_todo(self):
        self.put([row("a", 5, 10, 50), row("b", 3, 10, 30)], [call("a")])
        self.assertEqual(SH.problems(self.r, "acme"), ["W b: no shape call"])
        self.assertEqual([x["run"] for x in SH.todo(self.r, "acme")], ["b"])

    def test_ids_must_come_from_the_lists(self):
        self.put([row("a", 5, 10, 50)], [call("a", arc="coined", devices=("made-up",))])
        bad = " ".join(SH.problems(self.r, "acme"))
        self.assertIn("arc 'coined'", bad)
        self.assertIn("device 'made-up'", bad)

    def test_no_arc_needs_fit_none(self):
        self.put([row("a", 5, 10, 50)], [call("a", arc=None, fit="loose")])
        self.assertIn("fit must be", SH.problems(self.r, "acme")[0])

    def test_folds_and_retires_are_not_ranked_and_money_rolls_up_with_derived_spend(self):
        self.put([row("a", 10, 20, 200), row("a-copy", 10, 20, 200, call="fold", copy_of="a"), row("b", 5, 40),
                  row("c", 0, None, call="retire")], [call("a"), call("b")])
        d = SH.build_data(self.r, "acme")
        r = d["rollup"][0]
        self.assertEqual((r["arc"], r["count"], r["sales"]), ("rise", 2, 15))
        self.assertEqual((r["spend_recorded"], r["spend_derived"], r["cost_per_sale"]), (200, 200, 26.67))
        self.assertEqual(d["winners"][0]["folded_copies"], ["a-copy"])
        self.assertEqual([n["run"] for n in d["not_ranked"]], ["c"])
        self.assertEqual([p["preset"] for p in r["presets_same_arc"]], ["card-a"])
        self.assertEqual([p["preset"] for p in r["presets_sharing_most_devices"]], ["card-b"])

    def test_build_writes_the_three_files_with_no_brand_in_the_code(self):
        self.put([row("a", 10, 20, 200)], [call("a")])
        h = SH.build(self.r, "acme")
        for f in ("shapes.json", "shapes.md", "page.html"):
            self.assertTrue((h / f).is_file())
        self.assertIn("ACME Winner Shapes", (h / "page.html").read_text())


if __name__ == "__main__":
    unittest.main()
