"""sent_back.py: the approval page's send-backs, counted per brand for the results feed. Counts and labels only,
never a typed note. Every test writes into its own scratch folders.

    /usr/bin/python3 components/meta-upload/tests/test_sent_back.py
"""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import sent_back as SB  # noqa: E402

STEPS = {"2": "Teardown", "4": "Brief", "7": "Make"}


def rec(at, unit, reasons, brand="acme", note="typed words that must stay on the Drive"):
    return {"at": at, "by": "someone", "brand": brand, "lane": "video", "unit": unit, "note": note,
            "reasons": [{"id": i, "label": l, "step": s, "tool": t} for i, l, s, t in reasons]}


HOOK = [("hook", "Hook weak", 2, "video-teardown"), ("hook", "Hook weak", 4, "copywriter")]
EDIT = [("edit", "Cut, pacing, captions or sound", 7, "video-edit")]
RECS = [rec("2026-11-01T10:00:00", "ad-a", HOOK), rec("2026-11-03T10:00:00", "ad-b", HOOK + EDIT),
        rec("2026-11-02T10:00:00", "ad-c", EDIT), rec("2026-11-04T10:00:00", "ad-z", EDIT, brand="other")]


class Build(unittest.TestCase):
    def test_counts_each_send_back_once_per_reason_and_names_every_step_it_points_at(self):
        d = SB.build("acme", RECS, STEPS)
        self.assertEqual((d["total"], d["since"], d["until"]), (3, "2026-11-01", "2026-11-03"))
        by = {r["id"]: r for r in d["reasons"]}
        self.assertEqual(by["hook"]["count"], 2)                 # two send-backs named it, each pointing at two steps
        self.assertEqual(by["hook"]["steps"], [{"step": 2, "name": "Teardown", "tool": "video-teardown"},
                                               {"step": 4, "name": "Brief", "tool": "copywriter"}])
        self.assertEqual((by["edit"]["count"], by["edit"]["last"], by["edit"]["units"]), (2, "2026-11-03", ["ad-b", "ad-c"]))
        self.assertEqual(d["steps"], [{"step": 2, "name": "Teardown", "count": 2}, {"step": 4, "name": "Brief", "count": 2},
                                      {"step": 7, "name": "Make", "count": 2}])

    def test_no_typed_note_is_ever_copied(self):
        self.assertNotIn("typed words", json.dumps(SB.build("acme", RECS, STEPS)))

    def test_a_brand_with_none_is_an_empty_summary(self):
        d = SB.build("nobody", RECS, STEPS)
        self.assertEqual((d["total"], d["reasons"], d["steps"], d["since"]), (0, [], [], None))


class Write(unittest.TestCase):
    def test_writes_under_runs_and_only_when_the_counts_change(self):
        with tempfile.TemporaryDirectory() as t:
            out, changed = SB.write("acme", t, RECS)
            self.assertTrue(changed)
            self.assertEqual(out, Path(t) / "runs" / "meta-upload" / "acme" / "SENT-BACK.json")
            self.assertEqual(json.loads(out.read_text())["total"], 3)
            self.assertFalse(SB.write("acme", t, RECS)[1])
            self.assertTrue(SB.write("acme", t, RECS[:1])[1])

    def test_reads_the_send_back_log_through_the_learnings_reader(self):
        with tempfile.TemporaryDirectory() as t:
            cards = Path(t) / "meta"
            cards.mkdir()
            (cards / "learnings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in RECS))
            with mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(cards)}):
                self.assertEqual(SB.main(["--repo", t]), 0)
            self.assertEqual(json.loads((Path(t) / "runs/meta-upload/acme" / SB.NAME).read_text())["total"], 3)
            self.assertEqual(json.loads((Path(t) / "runs/meta-upload/other" / SB.NAME).read_text())["total"], 1)

    def test_a_failure_is_said_and_never_raised(self):
        with mock.patch.object(SB, "write", side_effect=RuntimeError("boom")):
            self.assertIsNone(SB.rebuild_quietly("acme"))


if __name__ == "__main__":
    unittest.main()
