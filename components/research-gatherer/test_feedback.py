#!/usr/bin/env python3
"""Tests for the `feedback` mode (research_gatherer/feedback.py) — the brand's
own feedback-form answers (Klaviyo "Submitted Feedback" events) into the bank.
No network, no model, no Keychain, temp folders only: the Klaviyo read is a
stand-in, the intake read a stand-in script, the labeller a stand-in module."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from research_gatherer import feedback as F, voicepull as V   # noqa: E402
import daily as D   # noqa: E402
from test_voicepull import LAB, ws_with_bank, entries   # noqa: E402

STAGES = {"stages": [
    {"stage": "new-customer", "label": "First order", "lane": "customer", "relationship": "ordered", "force_lane": None, "known": {"orders": 1}},
    {"stage": "abandoned-checkout", "label": "Checkout, no order", "lane": "lead", "relationship": "checkout-started", "force_lane": "lead"},
    {"stage": "churned-refund", "label": "Refunded", "lane": "churned", "relationship": "ordered", "force_lane": "churned"},
    {"stage": "churned-cancelled", "label": "Cancelled", "lane": "churned", "relationship": "ordered", "force_lane": "churned-subscriber"},
]}
QUESTIONS = {"stages": {
    "new-customer": {"questions": [
        {"id": "recommend", "n": 1, "type": "scale", "text": "How likely?", "areas": ["marketing"], "yields": ["rating"]},
        {"id": "first-saw", "n": 2, "type": "choice", "text": "Where did you first see us?", "options": ["TikTok"], "other": True,
         "areas": ["marketing"], "yields": ["channel"]},
        {"id": "why-us", "n": 3, "type": "text", "text": "Why did you buy from us?", "areas": ["marketing"], "yields": ["why-bought"]},
        {"id": "change", "n": 4, "type": "text", "text": "One thing to change?", "areas": ["operations", "website"], "yields": ["friction"]}]},
    "abandoned-checkout": {"questions": [
        {"id": "stop", "n": 1, "type": "choice", "text": "What stopped you?", "options": ["Price"], "areas": ["website"], "yields": ["objection"]},
        {"id": "help", "n": 2, "type": "text", "text": "What would help?", "areas": ["marketing", "website"], "yields": ["buy-trigger"]}]},
    "churned-refund": {"questions": [
        {"id": "what-happened", "n": 2, "type": "text", "text": "What happened?", "areas": ["operations"], "yields": ["refund-reason"]}]},
    "churned-cancelled": {"questions": [
        {"id": "tell-more", "n": 2, "type": "text", "text": "Tell me more?", "areas": ["operations"], "yields": ["cancel-reason"]}]},
}}


def ev(eid, when, stage, answers, **extra):
    return {"id": eid, "attributes": {"datetime": when, "event_properties": dict(
        {"brand": "b", "stage": stage, "form_version": "v1", "answers": answers, "email": "never@x.com"}, **extra)}}


EVENTS = [
    ev("E1", "2026-09-29T10:00:00+00:00", "new-customer", [
        {"id": "recommend", "type": "scale", "answer": 9},
        {"id": "first-saw", "type": "choice", "answer": "Other", "other": "My barber put me on"},
        {"id": "why-us", "type": "text", "answer": "Nothing else touched my razor bumps"},
        {"id": "change", "type": "text", "answer": "no"}]),
    ev("E2", "2026-09-29T11:00:00+00:00", "abandoned-checkout", [
        {"id": "stop", "type": "choice", "answer": "Price"},
        {"id": "help", "type": "text", "answer": "A smaller starter size so I can try it first"}]),
    ev("E3", "2026-09-29T12:00:00+00:00", "churned-refund", [{"id": "what-happened", "type": "text", "answer": "It took three weeks to arrive"}]),
    ev("E4", "2026-09-29T13:00:00+00:00", "churned-cancelled", [{"id": "tell-more", "type": "text", "answer": "Too many bottles piling up in my cabinet"}]),
    ev("E5", "2026-09-29T14:00:00+00:00", "new-customer", [{"id": "why-us", "type": "text", "answer": "TEST answer from the proof"}], test=True),
    ev("E6", "2026-09-29T15:00:00+00:00", "no-such-stage", [{"id": "x", "type": "text", "answer": "Lost answer here"}]),
    ev("E7", "2026-09-29T16:00:00+00:00", "new-customer", [{"id": "why-us", "type": "text", "answer": "Other brand's form"}], brand="other"),
]


def with_forms(tmp, enabled=True):
    ldir, fake = ws_with_bank(tmp, pulls={"feedback": {"enabled": enabled, "key": "K", "metric": "Submitted Feedback",
                                                       "since": "2026-09-01", "why": "waits on its key"}})
    ops = tmp / "brands" / "b" / "operations"
    (ops / "feedback-stages.json").write_text(json.dumps(STAGES))
    (ops / "feedback-questions.json").write_text(json.dumps(QUESTIONS))
    return ldir, fake


class Rows(unittest.TestCase):
    def test_open_text_only_with_stage_lane_areas_and_taps(self):
        rows, newest, skipped = F.rows_from_events(EVENTS, "b", {s["stage"]: s for s in STAGES["stages"]},
                                                   QUESTIONS["stages"], "2026-09-29")
        self.assertEqual([r["text"] for r in rows], ["My barber put me on", "Nothing else touched my razor bumps",
                                                     "A smaller starter size so I can try it first",
                                                     "It took three weeks to arrive", "Too many bottles piling up in my cabinet"])
        self.assertEqual(skipped, {"test": 1, "other brand": 1, "unknown stage": 1})
        self.assertEqual(newest, "2026-09-29T16:00:00+00:00")
        r = rows[1]
        self.assertEqual((r["source_id"], r["question"], r["item"], r["relationship"], r["force_lane"], r["rating"]),
                         ("survey_b_feedback-new-customer", "q-03_why-did-you-buy-from-us", "E1", "ordered", None, 9))
        self.assertEqual(r["feedback"]["areas"], ["marketing"])
        self.assertEqual(r["feedback"]["taps"], {"recommend": 9, "first-saw": "Other: My barber put me on"})
        self.assertEqual((rows[2]["relationship"], rows[2]["force_lane"]), ("checkout-started", "lead"))
        self.assertEqual(rows[3]["force_lane"], "churned")
        self.assertEqual(rows[4]["force_lane"], "churned-subscriber")
        self.assertNotIn("never@x.com", json.dumps(rows))   # the email is never read into a row

    def test_tests_kept_only_when_asked(self):
        rows, _, skipped = F.rows_from_events(EVENTS[4:5], "b", {s["stage"]: s for s in STAGES["stages"]},
                                              QUESTIONS["stages"], "t", include_tests=True)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["feedback"]["test"])
        self.assertEqual(skipped["test"], 0)


class Run(unittest.TestCase):
    def test_files_into_the_stage_lanes_then_nothing_twice(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = with_forms(tmp)
        calls = []
        fetch = lambda key, metric, since: calls.append((key, metric, since)) or (EVENTS, None)
        self.assertEqual(F.main(["--brand", "b", "--dry-run"], fetch=fetch, labeller=LAB, claude=fake), 0)
        self.assertEqual(entries(ldir), [])
        self.assertEqual(calls[0], ("K", "Submitted Feedback", "2026-09-01"))
        F.main(["--brand", "b"], fetch=fetch, labeller=LAB, claude=fake)
        got = {e["text"]: e for e in entries(ldir)}
        self.assertEqual(len(got), 5)
        self.assertEqual(got["Nothing else touched my razor bumps"]["_f"], "customers/unsegmented.json")
        lead = got["A smaller starter size so I can try it first"]
        self.assertEqual((lead["_f"], lead["lane_by"], lead["funnel"]), ("leads.json", "relationship", "lead"))
        self.assertNotIn("attribution", lead)
        self.assertEqual(got["It took three weeks to arrive"]["_f"], "churned/non-subscriber.json")
        self.assertEqual(got["Too many bottles piling up in my cabinet"]["_f"], "churned/subscriber.json")
        c = got["Nothing else touched my razor bumps"]
        self.assertEqual(c["feedback"]["stage"], "new-customer")
        self.assertEqual(c["signal"]["rating"], 9)
        self.assertEqual((c["source"]["id"], c["source"]["item"], c["origin"]), ("survey_b_feedback-new-customer", "E1", "internal"))
        st = json.loads((tmp / "runs/research/b/feedback-state.json").read_text())
        self.assertEqual(st["last_event"], "2026-09-29T16:00:00+00:00")
        F.main(["--brand", "b"], fetch=lambda k, m, s: (EVENTS, None), labeller=LAB, claude=fake)
        self.assertEqual(len(entries(ldir)), 5)
        self.assertTrue(list((tmp / "runs/research/b").glob("feedback-*/page.html")))

    def test_switched_off_brand_says_why(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = with_forms(tmp, enabled=False)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            F.main(["--brand", "b"], fetch=lambda *a: self.fail("must not read Klaviyo"), labeller=LAB, claude=fake)
        self.assertIn("MISSING — waits on its key", buf.getvalue())

    def test_unreadable_klaviyo_is_named(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = with_forms(tmp)
        F.main(["--brand", "b"], fetch=lambda *a: (None, "no key"), labeller=LAB, claude=fake)
        self.assertEqual(entries(ldir), [])
        self.assertFalse((tmp / "runs/research/b/feedback-state.json").exists())

    def test_daily_runs_it(self):
        self.assertIn("feedback", D.MODES)

    def test_lay_extras_force_lead_keeps_feedback(self):
        lane, e = V.lay_extras("customer", {"source": {}, "funnel": "customer", "speaker": "customer", "attribution": "assumed"},
                               {"force_lane": "lead", "feedback": {"stage": "s", "areas": ["website"]}})
        self.assertEqual((lane, e["funnel"], e["lane_by"], e["feedback"]["areas"]), ("lead", "lead", "relationship", ["website"]))
        self.assertNotIn("attribution", e)


if __name__ == "__main__":
    unittest.main()
