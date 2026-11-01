"""An approval on the brief's checklist is KEPT for that brief (2026-10-19).

Found on the mini check: 5 of 7 v2 briefs on disk were refused by production with
"MANIFEST: MISSING — E…" although writing had passed them. Approvals lived only in one process's
environment, so production's own re-check read MISSING again. No network: the judge's answer is
already on file for the brief, so it is never asked.

    /usr/bin/python3 -m unittest discover -s tools/video-writing/tests
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parent.parent / "machine"
sys.path.insert(0, str(MACHINE))
import manifest as M        # noqa: E402
import swipe_match as SM    # noqa: E402

BRAND = next(p.name for p in sorted((MACHINE.parents[2] / "brands").iterdir())
             if p.is_dir() and not p.name.startswith("_") and (p / "products").is_dir())


class ApprovalsAreKept(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = Path(self.tmp.name)
        (d / "stages").mkdir()
        (d / "run.json").write_text(json.dumps({"brand": BRAND}))
        (d / "stages" / "2-spec.md").write_text("spec")
        body = "# Brief\n\nA scene with nothing priced.\n"
        stamped = "<!-- swipe-match: PASSED · %s -->\n%s" % (SM.brief_hash(M.strip(body)), body)
        (d / "stages" / "5-brief.md").write_text(stamped)
        self.h = SM.brief_hash(M.strip(stamped))
        self.write_rec({})

    def write_rec(self, extra):
        rec = {"brief_hash": self.h,
               "judge": {"elements": [{"id": "E1", "carried": False, "element": "the core beat"}], "load_bearing": []}}
        rec.update(extra)
        (self.d / "manifest.json").write_text(json.dumps(rec))

    def tearDown(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        if self.prev is not None:
            os.environ["DAEMN_STRUCTURE_APPROVALS"] = self.prev
        self.tmp.cleanup()

    def last_line(self):
        return [l for l in (self.d / "stages" / "5-brief.md").read_text().splitlines() if l.startswith("MANIFEST:")][-1]

    def test_missing_without_an_approval(self):
        self.assertEqual(M.check(self.d, BRAND), (False, ["E1"]))
        self.assertTrue(self.last_line().startswith("MANIFEST: MISSING"))

    def test_an_approval_survives_the_next_check(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "E1"
        self.assertEqual(M.check(self.d, BRAND), (True, []))
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS")
        self.assertEqual(M.check(self.d, BRAND), (True, []))            # production's re-check
        self.assertTrue(self.last_line().startswith("MANIFEST: COMPLETE"))
        self.assertEqual(M.status_of((self.d / "stages" / "5-brief.md").read_text()), "COMPLETE")

    def test_all_with_v_approves_everything(self):
        """"all,V" (Outlier's "Looks good", the batch script approval) is all, not the codes {all, V}."""
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "all,V"
        self.assertEqual(M.check(self.d, BRAND), (True, []))

    def test_an_approval_for_another_brief_does_not_count(self):
        self.write_rec({"approved": {"brief_hash": "0" * 16, "all": False, "ids": ["E1"]}})
        self.assertEqual(M.check(self.d, BRAND), (False, ["E1"]))


if __name__ == "__main__":
    unittest.main()
