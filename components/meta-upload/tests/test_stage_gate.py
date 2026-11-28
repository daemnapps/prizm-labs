"""The stage-check gate: a piece whose stage-check failed, never ran or ran before the card was filed is refused at
upload, and the refusal names the check."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import stage_gate as SG  # noqa: E402

NAME = "brand-a_widget_brief-0042_batch-2026-11-20-a_page-one"
KEY = "brand-a_widget_brief-0042"


def steps(**fail):
    names = ["swipe", "teardown", "format", "brief", "pictures", "card", "queue"]
    return [{"step": s, "name": f"the {s}", "ok": s not in fail} for s in names]


class Gate(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        os.environ["STAGE_CHECK_ROOT"] = self.d.name
        self.card = {"brand": "brand-a", "ad_name": NAME, "made_at": "2026-11-20T10:00:00"}

    def tearDown(self):
        os.environ.pop("STAGE_CHECK_ROOT", None)
        self.d.cleanup()

    def record(self, at="2026-11-21T09:00:00", **fail):
        f = Path(self.d.name) / "brand-a" / KEY / "latest.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"piece": KEY, "brief": KEY, "brand": "brand-a", "at": at, "steps": steps(**fail)}))

    def test_never_ran_is_refused(self):
        g = SG.check(self.card)
        self.assertFalse(g["ok"])
        self.assertIn("never run on " + KEY, g["why"])

    def test_failed_step_is_refused_by_name(self):
        self.record(pictures=True)
        g = SG.check(self.card)
        self.assertFalse(g["ok"])
        self.assertIn("failed on " + KEY, g["why"])
        self.assertIn("the pictures", g["why"])

    def test_stale_run_is_refused(self):
        self.record(at="2026-10-30T09:00:00")
        g = SG.check(self.card)
        self.assertFalse(g["ok"])
        self.assertIn("before this card was filed", g["why"])

    def test_card_step_format_and_after_are_not_asked(self):
        self.record(card=True, queue=True, format=True)
        self.assertTrue(SG.check(self.card)["ok"])

    def test_no_brief_in_the_name(self):
        self.assertFalse(SG.check(dict(self.card, ad_name="Story Images - LP - Copy"))["ok"])


class Upload(unittest.TestCase):
    """upload_card is the last step before Meta: a failing piece never reaches it."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        os.environ["STAGE_CHECK_ROOT"] = str(Path(self.d.name) / "sc")
        try:
            import upload as U
        except Exception as e:  # noqa: BLE001
            self.skipTest(f"the uploader does not load here: {e}")
        self.U = U
        self.folder = Path(self.d.name) / "meta" / "brand-a" / "2-approved" / "image" / NAME
        self.folder.mkdir(parents=True)
        (self.folder / "card.json").write_text(json.dumps({
            "brand": "brand-a", "ad_name": NAME, "made_at": "2026-11-20T10:00:00",
            "approval": {"decision": "approve", "by": "tester", "start": "PAUSED"}}))

    def tearDown(self):
        os.environ.pop("STAGE_CHECK_ROOT", None)
        self.d.cleanup()

    def test_failing_piece_is_refused_at_upload(self):
        f = Path(os.environ["STAGE_CHECK_ROOT"]) / "brand-a" / KEY / "latest.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"brief": KEY, "at": "2026-11-21T09:00:00", "steps": steps(brief=True)}))
        with mock.patch.object(self.U, "approvers", return_value=["tester"]), \
                mock.patch.object(self.U, "card_plan", side_effect=AssertionError("got past the gate")):
            with self.assertRaises(SystemExit) as e:
                self.U.upload_card(self.folder, log=lambda *_: None)
        self.assertIn("REFUSED: stage-check failed on " + KEY, str(e.exception))
        self.assertIn("the brief", str(e.exception))

    def test_piece_never_checked_is_refused_at_upload(self):
        with mock.patch.object(self.U, "approvers", return_value=["tester"]), \
                mock.patch.object(self.U, "card_plan", side_effect=AssertionError("got past the gate")):
            with self.assertRaises(SystemExit) as e:
                self.U.upload_card(self.folder, log=lambda *_: None)
        self.assertIn("never run on " + KEY, str(e.exception))

    def test_passing_piece_goes_on(self):
        f = Path(os.environ["STAGE_CHECK_ROOT"]) / "brand-a" / KEY / "latest.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"brief": KEY, "at": "2026-11-21T09:00:00", "steps": steps(card=True)}))
        with mock.patch.object(self.U, "approvers", return_value=["tester"]), \
                mock.patch.object(self.U, "card_plan", side_effect=AssertionError("got past the gate")):
            with self.assertRaises(AssertionError):
                self.U.upload_card(self.folder, log=lambda *_: None)


if __name__ == "__main__":
    unittest.main()
