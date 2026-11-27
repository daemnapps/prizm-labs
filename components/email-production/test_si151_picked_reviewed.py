#!/usr/bin/env python3
"""SI-151 (picked subject gated), the card's tests: the delivery gate checks
the subject pair that will be sent, and the push reads the send the reviewer
approved, failing closed on an unreadable review (email-production#11).

    /usr/bin/python3 tools/email-production/test_si151_picked_reviewed.py

Offline. A made-up brand `zz-brand` in a temp workspace; the brand's
catalogue, the price check, the look and the Keychain are stubs.

  1  delivery_items gates subjects[pick]; a pick outside the set is an item
  2  push(pick=-1) stops before the Keychain or any upload
  3  klaviyo_upload.check(job, 1) reruns the gate on pair 1 — and the
     check.json fallback refuses a pick other than 0
  4  the_slot returns the reviewer's segment and date, and None for a cut send
  5  a review.json holding `{` raises, and run_month's review step exits non-zero
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="si151-picked-reviewed-")).resolve()
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import run_month as RM                            # noqa: E402  (first: simple_email takes this folder off the path)
import klaviyo_upload as K                        # noqa: E402
import simple_email as S                          # noqa: E402  (puts machine/ on the path)
import brand_facts as BF                          # noqa: E402
import reviewed_plan as RP                        # noqa: E402

BRAND, SID = "zz-brand", "oct-01"
LABEL = f"{BRAND}-{SID}"
URL = "https://example.test/p"
EMAIL = {
    "headline": "A headline", "body": ["First paragraph.", "Second."], "offer": None,
    "button": {"label": "Get it", "link": URL},
    "subjects": [{"subject": "A clean subject", "preview": "A clean preview"},
                 {"subject": "ubject lost its first letter", "preview": "A preview"}],
}
LOOK = {
    "logo": {"url": "https://example.test/logo.png", "alt": "Z", "width": 100,
             "link": "https://example.test"},
    "from": {"email": "hi@example.test", "label": "Zz"},
    "send_time": {"local": "13:00", "recipient_time_zone": True},
    "klaviyo_key": "KLAVIYO_ZZ_KEY",
    "fonts": {"headline": "serif", "body": "sans-serif"},
    "colors": {"page": "#fff", "card": "#fff", "text": "#000", "muted": "#777",
               "button": "#000", "button_text": "#fff"}}
SLOT = {"id": SID, "date": "2099-10-01", "segment": "Core | A", "segments": ["Core | A"],
        "type": "what-went-wrong", "occasion": None}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1))


def email_run():
    """runs/email-production/zz-brand/<label>/ with a passing step 8c."""
    rd = WS / "runs/email-production" / BRAND / LABEL
    write(rd / "run.json", {"brand": BRAND, "assignment": {}})
    write(rd / "stage8c--check.md", "```CHECK\n{}\n```\n")
    write(rd / "deliverable/email.json", EMAIL)
    return rd


def month():
    """runs/marketing-calendar/zz-brand/2026-10/, as the planner wrote it."""
    cal = WS / "runs/marketing-calendar" / BRAND / "2026-10"
    write(cal / "run.json", {"brand": BRAND, "month": "2026-10"})
    write(cal / "slots.json", [SLOT])
    return cal


def stubs():
    return [mock.patch.object(BF, "catalogue", lambda brand, ws=None: {"sellable": [{"url": URL}],
                                                                       "never": []}),
            mock.patch.object(S, "price_check", lambda email, brand, run_dir: []),
            mock.patch.object(S, "look", lambda brand: LOOK),
            mock.patch.object(S, "kl_key", mock.Mock(side_effect=AssertionError("Keychain read")))]


class Base(unittest.TestCase):
    def setUp(self):
        self.p = stubs()
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        shutil.rmtree(str(WS), ignore_errors=True)


class T1PickedSubjectGated(Base):
    def subject_items(self, pick):
        return [i for i in S.delivery_items(EMAIL, BRAND, email_run(), pick=pick)
                if i["kind"] == "subject"]

    def test_pair_1_mid_word_is_held(self):
        got = self.subject_items(1)
        self.assertTrue(got, "pair 1 starts mid-word and was not gated")
        self.assertTrue(all(i["text"].startswith("subject pair 1: ") for i in got), got)
        self.assertTrue(any("mid-word" in i["text"] for i in got), got)

    def test_clean_pair_0_gives_none(self):
        self.assertEqual(self.subject_items(0), [])

    def test_negative_pick_is_out_of_range(self):
        got = self.subject_items(-1)
        self.assertEqual([i["text"] for i in got], ["pick -1 is not in the subject set (0..1)"])

    def test_pick_passes_through_split_and_problems(self):
        rd = email_run()
        self.assertTrue(any(i["kind"] == "subject" for i in S.delivery_split(EMAIL, BRAND, rd, 1)[0]))
        self.assertTrue(any(p.startswith("subject pair 1: ") for p in S.delivery_problems(EMAIL, BRAND, rd, 1)))
        self.assertFalse(any("subject" in p for p in S.delivery_problems(EMAIL, BRAND, rd)))


class T2PushGuardFirst(Base):
    def test_negative_pick_stops_before_key_and_upload(self):
        month()
        out = TMP / "push-out"
        out.mkdir(exist_ok=True)
        key, up = mock.Mock(return_value="k"), mock.Mock(return_value="https://cdn.test/x")
        with mock.patch.object(S, "kl_key", key), mock.patch.object(S, "upload", up):
            for pick in (-1, 2):
                with self.assertRaises(SystemExit):
                    S.push(EMAIL, LOOK, BRAND, LABEL, {"hero": out / "hero.png"}, pick, out)
        key.assert_not_called()
        up.assert_not_called()
        self.assertFalse((out / "hosted.json").exists())


class T3UploaderGatesThePick(Base):
    def job(self, rd, run_dir):
        return {"mode": "run", "root": rd, "brand": BRAND, "label": LABEL, "brief_ids": [],
                "deliverable": rd / "deliverable", "media": [], "run_dir": run_dir,
                "links": None, "out": rd / "deliverable"}

    def gate(self, rows):
        return next(r for r in rows if r["check"] == "delivery gate")

    def test_rerun_gates_pair_1(self):
        rd = email_run()
        rows, problems, _ = K.check(self.job(rd, rd), 1, online=False)
        self.assertEqual(self.gate(rows)["result"], "PROBLEM", rows)
        self.assertTrue(any(p.startswith("delivery gate:") and "subject pair 1" in p for p in problems),
                        problems)
        rows, _, _ = K.check(self.job(rd, rd), 0, online=False)
        self.assertEqual(self.gate(rows)["result"], "ok", self.gate(rows))

    def test_check_json_fallback_vouches_for_pair_0_only(self):
        rd = email_run()
        write(rd / "deliverable/check.json", {"delivery": {"result": "pass", "problems": []}})
        rows, _, _ = K.check(self.job(rd, None), 0, online=False)
        self.assertEqual(self.gate(rows)["result"], "ok")
        rows, _, _ = K.check(self.job(rd, None), 1, online=False)
        self.assertEqual(self.gate(rows)["result"], "PROBLEM")
        self.assertIn("rerun the gate with --pick 1", self.gate(rows)["detail"])


class T4TheSlotAsReviewed(Base):
    def test_no_review_is_the_plan(self):
        month()
        got = S.the_slot(BRAND, LABEL)
        self.assertEqual((got["date"], got["segment"]), (SLOT["date"], SLOT["segment"]))

    def test_reviewer_edits_reach_the_draft(self):
        cal = month()
        write(cal / "review.json", {"slots": {SID: {"status": "approved", "note": "",
                                                    "edits": {"date": "2099-10-03",
                                                              "segment": "Core | B"}}},
                                    "copy": {}})
        got = S.the_slot(BRAND, LABEL)
        self.assertEqual((got["date"], got["segment"]), ("2099-10-03", "Core | B"))
        write(WS / "brands" / BRAND / "email-sms/audience-matrix.json",      # the temp tree's, not the repo's
              {"segments": [{"name": "Core | A", "id": "SEGA"}, {"name": "Core | B", "id": "SEGB"}]})
        self.assertEqual(S.audience(BRAND, got), (["Core | B"], ["SEGB"], []))

    def test_a_cut_send_is_none(self):
        cal = month()
        RP._review().set_status(cal, SID, "cut", who="tester")     # the board's own writer
        self.assertIsNone(S.the_slot(BRAND, LABEL))

    def test_an_unreadable_review_is_none(self):
        cal = month()
        write(cal / "review.json", "{")
        self.assertIsNone(S.the_slot(BRAND, LABEL))


class T5UnreadableReviewFailsClosed(Base):
    def test_reviewed_raises(self):
        cal = month()
        write(cal / "review.json", "{")
        with self.assertRaises(RP.ReviewUnreadable):
            RP.reviewed(cal, [SLOT])

    def run_month(self, cal):
        produce = mock.Mock(return_value=0)
        with mock.patch.object(sys, "argv", ["run_month.py", str(cal)]), \
                mock.patch.object(RM, "produce", produce), \
                self.assertRaises(SystemExit) as e:
            RM.main()
        produce.assert_not_called()
        return e.exception.code

    def test_run_month_exits_non_zero(self):
        cal = month()
        write(cal / "review.json", "{")
        code = self.run_month(cal)
        self.assertNotIn(code, (0, None))
        self.assertIn("review layer unreadable", str(code))

    def test_run_month_exits_non_zero_when_the_review_module_is_missing(self):
        cal = month()
        with mock.patch.object(RP, "_review", mock.Mock(side_effect=ImportError("gone"))):
            code = self.run_month(cal)
        self.assertNotIn(code, (0, None))


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(str(TMP), ignore_errors=True)
