"""vary_recipe on a run with a kept 3D set: a picture change is a set change, a words-only row stays a plain edit, and a
run with no kept set goes as it did. Spends nothing: the builder, the judge and the words are stubbed."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_edit import engine as E  # noqa: E402

RUN = "brand-batch-1"
ONE = "a 12 cm brass tray under the product, on the slab"


class Builder:
    """The parts of model-inputs' preview.py vary_recipe calls. make_picture must never run on a set row."""
    FILLED = "filled"

    def __init__(self):
        self.made = []

    def variation_brief(self, brief, change, approved=None):
        return dict(brief)

    def preview(self, job, recipe, quote=False):
        return {"prompt": "the flat prompt", "inputs": [], "send": {"type_layer": {"x": 1}, "bars": [0, 0]}, "findings": []}

    def needs_picture(self, change):
        return bool(change.get("picture") or change.get("swap") or change.get("people") or change.get("stays_drop"))

    def make_picture(self, recipe, by, out_dir=None):
        self.made.append(recipe)
        return {"file": str(self.flat), "plate": str(self.flat), "model": "m", "rung": "r"}


class VarySets(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vary-sets-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.sets = E._picture_sets()
        for p in (mock.patch.object(self.sets, "home", lambda brand, name: self.tmp / "sets" / name),
                  mock.patch.object(self.sets.P, "rel", lambda p, *a: Path(p).name),
                  mock.patch.object(E, "_words_on", self.words),
                  mock.patch.object(E.CMP, "compare", self.compare)):
            p.start()
            self.addCleanup(p.stop)
        self.base = self.tmp / "approved.png"
        self.base.write_bytes(b"a")
        (self.tmp / "generated").mkdir()
        (self.tmp / "generated" / "approved.plate.png").write_bytes(b"p")
        self.base.with_suffix(".recipe.json").write_text(json.dumps({"brief": {"run": RUN}, "sheet": {}}))
        self.pv = Builder()
        self.pv.flat = self.tmp / "flat.png"
        self.pv.flat.write_bytes(b"f")
        self.verdict = ("pass", [], ["t"], "")
        self.compared = []

    def words(self, picture, out, name, pv, PV):
        self.worded = Path(picture)
        (out / name).write_bytes(b"done")
        return {"plate": str(picture)}

    def compare(self, plate, got, change, keeps, caller=None):
        self.compared.append((got, change))
        return self.verdict

    def kept_set(self):
        d = self.sets.home("b", "hero")
        d.mkdir(parents=True)
        (d / "print-v1.png").write_bytes(b"x")
        (d / "set.json").write_text(json.dumps({"runs": [RUN], "project": {"id": "p1"}, "camera": "85 mm", "light": "one key",
                                                "prints": [{"file": "print-v1.png", "note": "kept: first"}]}))

    def vary(self, rows, **kw):
        return E.vary_recipe({"brand": "b", "baseline": str(self.base), "variations": rows, "out": str(self.tmp / "out"), **kw},
                             builder=self.pv, sets=self.sets)

    def record(self, vid):
        return json.loads((self.tmp / "out" / vid / "edit.json").read_text())

    def file_print(self, vid="v1", note="kept: tray in"):
        q = json.loads((self.tmp / "out" / vid / "set-request.json").read_text())
        src = self.tmp / "made.png"
        src.write_bytes(b"y")
        self.sets.put_change(q, printed=src, note=note)

    def test_a_dry_run_writes_the_request_and_spends_nothing(self):
        self.kept_set()
        s = self.vary([{"id": "v1", "words": ["NEW"], "picture": ONE}], dry_run=True)
        r = self.record("v1")
        self.assertEqual((r["state"], r["route"]), ("dry", "set"))
        self.assertTrue((self.tmp / "out" / "v1" / "set-request.json").is_file())
        self.assertIn(ONE, r["set_request"]["print_words"])
        self.assertEqual(s["print_credits"], self.sets.PRINT_CREDITS)
        self.assertEqual(self.pv.made, [])

    def test_a_real_run_waits_for_the_print_and_never_goes_flat(self):
        self.kept_set()
        with mock.patch.object(E, "_copy_not_approved", return_value=[]):
            s = self.vary([{"id": "v1", "words": ["NEW"], "picture": ONE}])
        self.assertEqual(self.record("v1")["state"], "waiting-for-set")
        self.assertEqual((s["waiting_for_set"], s["delivered"]), (1, 0))
        self.assertEqual(self.pv.made, [])

    def test_a_filed_print_is_the_picture_judged_against_the_approved_one(self):
        self.kept_set()
        rows = [{"id": "v1", "words": ["NEW"], "picture": ONE}]
        self.vary(rows, dry_run=True)
        self.file_print()
        with mock.patch.object(E, "_copy_not_approved", return_value=[]):
            s = self.vary(rows)
        r = self.record("v1")
        self.assertEqual(r["state"], "filed")
        self.assertEqual(self.worded.parent.name, "hero--v1")
        self.assertEqual(self.compared[0][1], ONE)
        self.assertEqual((s["delivered"], s["print_credits"]), (1, 0))
        self.assertEqual(self.pv.made, [])

    def test_a_print_the_judge_fails_is_delivered_marked_below_criteria(self):
        self.kept_set()
        rows = [{"id": "v1", "picture": ONE}]
        self.vary(rows, dry_run=True)
        self.file_print()
        self.verdict = ("fail", ["the slab moved"], ["t"], "")
        with mock.patch.object(E, "_copy_not_approved", return_value=[]):
            self.vary(rows)
        self.assertEqual(self.record("v1")["below_criteria"], ["the slab moved"])

    def test_the_copy_gate_still_stands_in_front_of_a_set_row(self):
        self.kept_set()
        with mock.patch.object(E, "_copy_not_approved", return_value=["NEW"]):
            self.vary([{"id": "v1", "words": ["NEW"], "picture": ONE}])
        self.assertEqual(self.record("v1")["state"], "refused")

    def test_a_words_only_row_stays_a_plain_edit_on_a_run_with_a_set(self):
        self.kept_set()
        with mock.patch.object(E, "_copy_not_approved", return_value=[]):
            s = self.vary([{"id": "v1", "words": ["NEW"]}])
        r = self.record("v1")
        self.assertEqual((r["route"], r["state"]), ("words", "filed"))
        self.assertNotIn("set_request", r)
        self.assertEqual(self.worded.name, "approved.plate.png")
        self.assertEqual(s["print_credits"], 0)

    def test_a_run_with_no_kept_set_goes_the_old_way(self):
        with mock.patch.object(E, "_copy_not_approved", return_value=[]):
            self.vary([{"id": "v1", "picture": ONE}])
        r = self.record("v1")
        self.assertEqual((r["route"], r["state"]), ("edit", "filed"))
        self.assertEqual(len(self.pv.made), 1)


if __name__ == "__main__":
    unittest.main()
