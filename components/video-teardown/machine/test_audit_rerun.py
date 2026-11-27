#!/usr/bin/env python3
"""The audit's RE-RUN on writing v1 (creator, founder): its fixes go back into the passes it names.

    /usr/bin/python3 components/video-teardown/machine/test_audit_rerun.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("vt_run_audit", HERE / "run.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

ORDER = ["stage0", "stage1", "stage2", "stage3", "stage4r", "stage4b", "stage4a", "stage4c",
         "stage4d", "stage4e", "stage4g", "stage5", "stage7", "stage7b"]

RERUN = """THE VIBE: straight.

## VERDICT — RE-RUN (pass 1 of 2)

| Re-run | The one thing that must change |
|---|---|
| **4d** | **B7.** Keep the track stopped over the reveal. |
| **4c** | **B1.** Put the swipe's severity back: "severe acne and dark marks". |
| **4e** | **B10.** Hold the cards long enough to read. |

---

## CHECK TABLE

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Spine survived | **PASS** | ok |
"""

SHIP = "## VERDICT — SHIP\n\nAll good.\n\n## CHECK TABLE\n\n| 1 | Spine | **PASS** | ok |\n"


def st_for(**kw):
    st = {"slug": "t", "brand": "b", "production_route": "creator", "_order": list(ORDER),
          "stages": {"stage4e": {"status": "done", "out": "stages/4f-audit.md"}}}
    st.update(kw)
    return st


class TestAuditRerunPlan(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)

    def tearDown(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        if self.old is not None:
            os.environ["DAEMN_STRUCTURE_APPROVALS"] = self.old

    def test_plan_starts_at_the_earliest_named_pass(self):
        p = R.audit_redo_plan(st_for(), RERUN)
        self.assertEqual(p["stage"], "stage4a")                 # board 4c = placement
        self.assertEqual(p["stages"], ["stage4a", "stage4c", "stage4d", "stage4e"])
        self.assertTrue(p["pending"])
        self.assertEqual(p["round"], 1)
        for words in ("**4d**", "**4c**", "**4e**", "severe acne and dark marks", "THE AUDIT SENT THIS SCRIPT BACK"):
            self.assertIn(words, p["notes"])

    def test_no_plan_when_it_ships_on_v2_or_rounds_spent(self):
        self.assertIsNone(R.audit_redo_plan(st_for(), SHIP))
        self.assertIsNone(R.audit_redo_plan(st_for(writing="v2"), RERUN))
        self.assertIsNone(R.audit_redo_plan(st_for(audit_rounds=R.AUDIT_ROUNDS), RERUN))

    def _gate(self, st, body):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "stages").mkdir()
            (d / "stages" / "4f-audit.md").write_text(body)
            (d / "run.json").write_text(json.dumps(st))
            try:
                R.structure_gate(d, st, "stage4e", body)
                held = False
            except RuntimeError:
                held = True
            return held, json.loads((d / "run.json").read_text())

    def test_gate_holds_and_queues_one_round(self):
        held, saved = self._gate(st_for(), RERUN)
        self.assertTrue(held)
        self.assertEqual(saved["stages"]["stage4e"]["status"], "held")
        self.assertTrue(saved["audit_redo"]["pending"])
        self.assertEqual(saved["audit_rounds"], 1)

    def test_second_hold_waits_for_the_owner(self):
        held, saved = self._gate(st_for(audit_rounds=R.AUDIT_ROUNDS, audit_redo={"pending": False, "stages": []}), RERUN)
        self.assertTrue(held)
        self.assertFalse(saved["audit_redo"].get("pending"))

    def test_a_ship_clears_the_notes(self):
        held, saved = self._gate(st_for(audit_redo={"pending": False, "stages": ["stage4a"], "notes": "x"}), SHIP)
        self.assertFalse(held)
        self.assertNotIn("audit_redo", saved)
        self.assertEqual(saved["stages"]["stage4e"]["status"], "done")

    def test_passed_by_number_does_not_redo(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "A"
        held, saved = self._gate(st_for(), RERUN)
        self.assertFalse(held)
        self.assertNotIn("audit_redo", saved)


if __name__ == "__main__":
    unittest.main()
