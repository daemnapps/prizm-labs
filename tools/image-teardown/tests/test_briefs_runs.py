"""5.4: a brief's run is looked for under runs/image-teardown/<brand>/<run>.

    python3 tools/image-teardown/tests/test_briefs_runs.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE / "tools"))
import briefs as B  # noqa: E402


class RunsRoot(unittest.TestCase):
    def test_runs_root_is_the_repo_runs_folder(self):
        self.assertEqual(B.RUNS, B.REPO / "runs" / "image-teardown")

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
        if not found:
            self.skipTest("no brief run on disk yet — the public kit starts empty")
        for r in found:
            self.assertTrue(B.run_dir(r).is_relative_to(B.RUNS) or B.run_dir(r).is_relative_to(B.OLD_RUNS))


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main(verbosity=1)
