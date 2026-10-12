#!/usr/bin/env python3
"""The calendar's gates hold (CAL-1 (calendar gates hold), SI-148 (calendar gates hold)).

    python3 machine/test_cal1_gates.py

    1  a replan that puts a new send at an approved id: the new send reads
       pending, and the old send's approval and offer edit are not on it
    2  the same send unchanged across a replan keeps its approval
    3  a legacy entry with no stored identity applies as before, flagged
       unverified
    4  the copy button hands off only approved ids, and names the rest

Offline: a tempdir month, the hand-off stubbed. Nothing under runs/ or brands/
is written.
"""
import calendar as _stdlib_calendar      # noqa: F401 — cached BEFORE machine/ joins the path,
import json                              # because this folder has a calendar.py of its own
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
CHECKOUT = next((d for d in MACHINE.parents if (d / ".git").exists()), None)
if CHECKOUT and not os.environ.get("AI_WORKSPACE"):
    os.environ["AI_WORKSPACE"] = str(CHECKOUT)     # a worktree must read ITSELF
sys.path.insert(0, str(MACHINE))

import review as R                       # noqa: E402
import serve                             # noqa: E402


def send(sid, date, segment="Core | Regulars", type_="promo", occasion="Autumn sale"):
    return {"id": sid, "date": date, "segment": segment, "type": type_,
            "occasion": occasion, "offer": "none"}


def plan(run_dir, slots):
    (Path(run_dir) / "slots.json").write_text(json.dumps(slots))
    return slots


def by_id(run_dir):
    return {s["id"]: s for s in R.applied(R.month_slots(run_dir), R.load(run_dir))}


class Gates(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.run = Path(self._tmp.name) / "zz-brand" / "2026-10"
        self.run.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_1_replan_does_not_carry_an_approval_to_a_new_send(self):
        plan(self.run, [send("oct-01", "2026-10-09"), send("oct-02", "2026-10-20")])
        R.set_status(self.run, "oct-01", "approved")
        R.set_edit(self.run, "oct-01", "offer", "20% off")
        self.assertEqual(by_id(self.run)["oct-01"]["_review"]["status"], "approved")

        # a new, earlier send is planned: it takes oct-01, the original moves to oct-02
        plan(self.run, [send("oct-01", "2026-10-03", type_="education", occasion=None),
                        send("oct-02", "2026-10-09"), send("oct-03", "2026-10-20")])
        new = by_id(self.run)["oct-01"]
        self.assertEqual(new["_review"]["status"], "pending")
        self.assertEqual(new["_review"]["edits"], {})
        self.assertEqual(new["offer"], "none")
        self.assertEqual(new["_review"]["identity"], "mismatch")
        self.assertIn("review was for 2026-10-09", new["_review"]["note"])
        self.assertTrue(new["_review"]["note"].endswith("; re-review"))

        # a write on the new send starts clean — the old approval is not revived
        R.set_note(self.run, "oct-01", "fine as planned")
        new = by_id(self.run)["oct-01"]
        self.assertEqual(new["_review"]["status"], "pending")
        self.assertEqual(new["_review"]["edits"], {})
        self.assertEqual(new["_review"]["identity"], "verified")
        self.assertEqual(R.load(self.run)["slots"]["oct-01"]["superseded"]["status"],
                         "approved")      # set aside, not deleted

    def test_2_unchanged_send_keeps_its_approval(self):
        plan(self.run, [send("oct-01", "2026-10-09")])
        R.set_status(self.run, "oct-01", "approved")
        R.set_edit(self.run, "oct-01", "offer", "20% off")
        plan(self.run, [send("oct-01", "2026-10-09")])
        s = by_id(self.run)["oct-01"]
        self.assertEqual(s["_review"]["status"], "approved")
        self.assertEqual(s["offer"], "20% off")
        self.assertEqual(s["_review"]["identity"], "verified")

    def test_3_legacy_entry_applies_flagged_unverified(self):
        plan(self.run, [send("oct-01", "2026-10-09")])
        R.save(self.run, {"slots": {"oct-01": {"status": "approved", "note": "",
                                               "edits": {"offer": "20% off"}}},
                          "copy": {}})
        s = by_id(self.run)["oct-01"]
        self.assertEqual(s["_review"]["status"], "approved")
        self.assertEqual(s["offer"], "20% off")
        self.assertEqual(s["_review"]["identity"], "unverified")

    def test_4_copy_button_refuses_a_send_that_is_not_approved(self):
        plan(self.run, [send("oct-01", "2026-10-09"), send("oct-02", "2026-10-20")])
        R.set_status(self.run, "oct-01", "approved")
        handed = []

        def stub(run_dir, slot_ids):
            handed.append(list(slot_ids))
            return None, "stubbed."

        real = serve.handoff_for
        serve.handoff_for = stub
        try:
            out = serve.Handler.write_copy(types.SimpleNamespace(run_dir=self.run),
                                           ["oct-01", "oct-02"])
        finally:
            serve.handoff_for = real
        self.assertEqual(handed, [["oct-01"]])
        self.assertEqual(out["refused"], ["oct-02"])
        self.assertIn("oct-02", out["message"])
        self.assertEqual(R.load(self.run)["copy"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
