"""5.4: a brief's run is looked for under runs/image-teardown/<brand>/<run>.

    python3 tools/image-teardown/tests/test_briefs_runs.py
"""
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE / "tools"))
import briefs as B  # noqa: E402


class KeepsItsNumber(unittest.TestCase):
    """A filed run that already carries its number keeps it when its register row is opened again."""

    def opened(self, reg, record):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run = d / "brand-x" / "r1"
            (run / "out").mkdir(parents=True)
            (run / "out" / "06-brief.md").write_text("# brief")
            (run / "run.json").write_text(json.dumps(record))
            with unittest.mock.patch.object(B, "RUNS", d), unittest.mock.patch.object(B, "save"), \
                 unittest.mock.patch.object(B, "add_alias"), unittest.mock.patch.object(B, "next_id", return_value="brief-0009"), \
                 unittest.mock.patch.object(B, "run_dir", return_value=run):
                return B._open_brief("r1", "brand-x", reg, product="thing", kind="image-ai")

    def test_the_filed_number_is_kept_and_nothing_is_minted(self):
        reg = {"briefs": {}}
        bid, rec = self.opened(reg, {"brief": "brief-0297"})
        self.assertEqual(rec["brief"], "brief-0297")
        self.assertEqual(bid, B.new_key("brand-x", "thing", "brief-0297"))

    def test_a_run_with_no_number_gets_the_next_one(self):
        _, rec = self.opened({"briefs": {}}, {})
        self.assertEqual(rec["brief"], "brief-0009")

    def test_a_number_another_run_holds_is_refused(self):
        key = B.new_key("brand-x", "thing", "brief-0297")
        with self.assertRaises(SystemExit):
            self.opened({"briefs": {key: {"run": "other"}}}, {"brief": "brief-0297"})


class RunsRoot(unittest.TestCase):
    def test_runs_root_is_the_repo_runs_folder(self):
        self.assertEqual(B.RUNS, B.REPO / "runs" / "image-teardown")
        self.assertTrue(B.RUNS.is_dir())

    def test_brand_folder_first_then_unbranded_then_old_home(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "new" / "brand-x" / "r1").mkdir(parents=True)
            (d / "old" / "r2").mkdir(parents=True)
            with unittest.mock.patch.object(B, "RUNS", d / "new"), \
                 unittest.mock.patch.object(B, "OLD_RUNS", d / "old"):
                self.assertEqual(B.run_dir({"run": "r1", "brand": "brand-x"}), d / "new" / "brand-x" / "r1")
                self.assertEqual(B.run_dir("r1"), d / "new" / "brand-x" / "r1")      # found by glob, brand unknown
                self.assertEqual(B.run_dir("r2"), d / "old" / "r2")                  # pre-move home still answers
                self.assertEqual(B.run_dir({"run": "r3", "brand": "brand-x"}), d / "new" / "brand-x" / "r3")  # the new home when absent

    def test_registered_runs_resolve_under_the_real_root(self):
        reg = json.loads(B.REGISTER.read_text())
        recs = reg.get("briefs", reg) if isinstance(reg, dict) else reg
        recs = list(recs.values()) if isinstance(recs, dict) else recs
        found = [r for r in recs if isinstance(r, dict) and r.get("run") and B.run_dir(r).is_dir()]
        self.assertTrue(found, "no registered brief has a run folder on disk")
        for r in found:
            self.assertTrue(B.run_dir(r).is_relative_to(B.RUNS) or B.run_dir(r).is_relative_to(B.OLD_RUNS))


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main(verbosity=1)
