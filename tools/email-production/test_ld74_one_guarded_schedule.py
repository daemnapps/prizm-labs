#!/usr/bin/env python3
"""LD-74 (one guarded schedule): the Klaviyo approval page's Schedule
(approve_klaviyo.py, :8798) refuses on the same list as
klaviyo_upload.schedule_card — EP-3 (email approval card). No network, no key.

    python3 test_ld74_one_guarded_schedule.py

A made-up brand and card in a temp workspace; Klaviyo is
fake_klaviyo.FakeKlaviyo; the off-switch and approver list are temp files;
the machine-run guard reads env={} and a temp home; the clock is passed in.
Every refusal asserts no campaign-send-jobs call and an unchanged card status.

  1  the off-switch "off" is refused, naming send-switch.json
  2  the off-switch file missing is refused
  3  someone not on approvers.json is refused; a blank name too (two approvers)
  4  the team with everything right schedules: one send job, scheduled by the team
  5  a lab-run job and the mini are refused
  6  a send strategy that is not a fixed time is refused
  7  a fixed send 10 minutes away is refused, naming 30 minutes
  8  a subject changed in Klaviyo since the fingerprint is refused, naming subject
  9  a card with no fingerprint: the first press records it and refuses; the
     second press schedules
  10 approve() stores the draft's fingerprint read back from Klaviyo
  11 trial mode: the switch on and the owner → ok, trial, no Klaviyo call at all
"""
import datetime
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ld74-one-guarded-schedule-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import approve_klaviyo as A                       # noqa: E402  (imports klaviyo_upload first, then the folder is off sys.path)

K, S = A.K, A.S


def load(name):
    """A module of this folder, by path — the folder is off sys.path now."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, K.HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


FK = load("fake_klaviyo")

BRAND, LABEL, CID = "testbrand", "oct-01", "CAMP-LD74"
UTC = datetime.timezone.utc
AT = datetime.datetime(2099, 1, 1, 12, 0, tzinfo=UTC)
LATER = {"method": "static", "datetime": "2099-01-02T13:00:00+00:00", "options": {"is_local": False}}
RUNS = WS / "runs" / "email-production"
SEND_JOB = ("POST", "campaign-send-jobs")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1))


class Base(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(RUNS, ignore_errors=True)
        self.dir = RUNS / BRAND / LABEL / "klaviyo"
        self.fake = FK.FakeKlaviyo()
        self.home = TMP / "home"
        shutil.rmtree(self.home, ignore_errors=True)
        self.home.mkdir(parents=True)
        self.switch = TMP / "send-switch.json"
        write(self.switch, {"email_schedule": "on"})
        self.approvers = TMP / "approvers.json"
        write(self.approvers, {"approvers": ["the owner", "the team"]})
        self.p = [mock.patch.object(A, "RUNS", RUNS),
                  mock.patch.object(A, "FAKE", False),
                  mock.patch.object(S, "kl", self.fake.kl),
                  mock.patch.object(S, "kl_key", lambda lk: "test-key"),
                  mock.patch.object(S, "look", lambda brand: {"klaviyo_key": "KLAVIYO_TESTBRAND_KEY"}),
                  mock.patch.object(K, "SWITCH_F", self.switch),
                  mock.patch.object(K, "APPROVERS_F", self.approvers)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def campaign(self, strategy=None, subject="A subject"):
        self.fake.campaigns[CID] = {
            "name": "Test", "status": "Draft", "subject": subject, "preview": "A preview",
            "audience_ids": ["SEG1"], "strategy": strategy or dict(LATER), "message_id": "MSG-LD74",
            "template_id": "TPL-LD74", "html": "<html><body>hi</body></html>"}

    def make_card(self, strategy=None, fingerprint=True):
        """An approved card for a draft in the fake Klaviyo; its fingerprint read from that draft."""
        self.campaign(strategy)
        k = {"campaign_id": CID, "template_id": "TPL-LD74", "status": "DRAFT", "hosted": {}}
        if fingerprint:
            dr = K.klaviyo_draft("test-key", CID)
            k["fingerprint"] = K.fingerprint(dr["subject"], dr["preview"], dr["html"], dr["audience_ids"], dr["strategy"])
        write(self.dir / "card.json", {
            "brand": BRAND, "label": LABEL, "date": "01 Jan", "year": 2099, "segments": ["Core"],
            "subjects": [{"subject": "A subject", "preview": "A preview"}],
            "final_check": [{"result": "ok", "detail": "all good"}],
            "klaviyo": k, "approval": {"by": "the owner", "at": "2099-01-01T10:00:00"}, "status": "approved"})
        self.fake.calls.clear()

    def card(self):
        return json.loads((self.dir / "card.json").read_text())

    def sends(self):
        return [c for c in self.fake.calls if c == SEND_JOB]

    def schedule(self, who="the owner", env=None, home=None, at=AT):
        return A.schedule(BRAND, LABEL, who, env={} if env is None else env,
                          home=self.home if home is None else home, at=at)

    def refused(self, words, **kw):
        before = self.card()["status"]
        r = self.schedule(**kw)
        self.assertFalse(r["ok"], r)
        self.assertIn(words, r["error"])
        self.assertEqual(self.sends(), [])
        self.assertEqual(self.card()["status"], before)
        self.assertNotIn("scheduled", self.card())
        return r["error"]


class Schedule(Base):
    def test_01_switch_off(self):
        self.make_card()
        write(self.switch, {"email_schedule": "off"})
        self.refused("send-switch.json")
        self.assertEqual(self.fake.calls, [])

    def test_02_switch_missing(self):
        self.make_card()
        self.switch.unlink()
        self.refused("off-switch is off")
        self.assertEqual(self.fake.calls, [])

    def test_03_not_an_approver(self):
        self.make_card()
        self.refused("the team is not on the approver list", who="the team")
        self.refused("nobody is not on the approver list", who="")
        self.refused("nobody is not on the approver list", who=None)
        self.assertEqual(self.fake.calls, [])

    def test_04_pm_schedules(self):
        self.make_card()
        r = self.schedule(who="the team")
        self.assertEqual(r, {"ok": True, "scheduled": True})
        self.assertEqual(self.sends(), [SEND_JOB])
        c = self.card()
        self.assertEqual(c["scheduled"]["by"], "the team")
        self.assertEqual(c["scheduled"]["job"], CID)
        self.assertEqual(c["status"], "scheduled")
        self.assertEqual(self.fake.campaigns[CID]["status"], "Scheduled")
        # a second press is refused as already scheduled, with no second send job
        r = self.schedule(who="the team")
        self.assertFalse(r["ok"])
        self.assertIn("already scheduled by the team", r["error"])
        self.assertEqual(self.sends(), [SEND_JOB])

    def test_05_machine_runs(self):
        self.make_card()
        self.refused("lab-run job", env={"BRAND": "x", "OUT": "y"})
        mini = TMP / "mini-home"
        shutil.rmtree(mini, ignore_errors=True)
        write(mini / ".workflow-worker.env", "")
        self.refused("this is the mini", home=mini)
        self.refused("worker job", env={"WORKER_WS": "/w"})
        self.assertEqual(self.fake.calls, [])

    def test_06_not_a_fixed_time(self):
        self.make_card(strategy={"method": "immediate"})
        self.refused("could send now")

    def test_07_under_thirty_minutes(self):
        soon = (AT + datetime.timedelta(minutes=10)).isoformat()
        self.make_card(strategy={"method": "static", "datetime": soon, "options": {"is_local": False}})
        self.refused("less than 30 minutes")

    def test_08_subject_changed(self):
        self.make_card()
        self.fake.campaigns[CID]["subject"] = "A different subject"
        said = self.refused("changed since")
        self.assertIn("subject", said)
        self.assertNotIn("html", said)

    def test_09_no_fingerprint_recorded_once(self):
        self.make_card(fingerprint=False)
        self.refused("fingerprint recorded from Klaviyo's draft now")
        self.assertTrue(self.card()["klaviyo"]["fingerprint"]["sha256"])
        r = self.schedule()
        self.assertEqual(r, {"ok": True, "scheduled": True})
        self.assertEqual(self.sends(), [SEND_JOB])
        self.assertEqual(self.card()["scheduled"]["by"], "the owner")

    def test_11_trial_mode(self):
        self.make_card(fingerprint=False)
        with mock.patch.object(A, "FAKE", True):
            r = self.schedule(who="the owner")
        self.assertEqual(r, {"ok": True, "scheduled": True, "trial": True})
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.card()["scheduled"]["job"], "FAKE-" + CID)

    def test_11b_trial_mode_still_guarded(self):
        self.make_card()
        write(self.switch, {"email_schedule": "off"})
        with mock.patch.object(A, "FAKE", True):
            self.refused("send-switch.json")
        self.assertEqual(self.fake.calls, [])


class Approve(Base):
    def test_10_approve_stores_fingerprint(self):
        self.campaign()
        self.fake.calls.clear()
        write(self.dir / "card.json", {
            "brand": BRAND, "label": LABEL, "date": "01 Jan", "year": 2099, "send_local": "13:00",
            "segments": ["Core"], "links": ["https://example.test/p"],
            "subjects": [{"subject": "A subject", "preview": "A preview"}],
            "final_check": [{"result": "ok", "detail": "all good"}], "status": "draft"})
        write(self.dir / "email.html", "<html><body>hi</body></html>")
        made = []

        def create_draft(*a):
            made.append(a)
            return {"campaign_id": CID, "template_id": "T", "status": "DRAFT"}

        with mock.patch.object(S, "create_draft", create_draft), \
                mock.patch.object(S, "upload", lambda key, p, name: "https://cdn.test/" + name), \
                mock.patch.object(S, "send_strategy", lambda lk, slot: dict(LATER)), \
                mock.patch.object(S, "audience", lambda brand, slot: (["Core"], ["SEG1"], [])), \
                mock.patch.object(A, "link_status", lambda url: "200"):
            r = A.approve(BRAND, LABEL, "the owner")
        self.assertEqual(r, {"ok": True, "campaign_id": CID})
        self.assertEqual(len(made), 1)
        c = self.card()
        self.assertEqual(c["status"], "approved")
        dr = K.klaviyo_draft("test-key", CID)
        want = K.fingerprint(dr["subject"], dr["preview"], dr["html"], dr["audience_ids"], dr["strategy"])
        self.assertEqual(c["klaviyo"]["fingerprint"]["sha256"], want["sha256"])
        # and the stored fingerprint is the one Schedule compares: it schedules on the next press
        self.fake.calls.clear()
        self.assertEqual(self.schedule(), {"ok": True, "scheduled": True})
        self.assertEqual(self.sends(), [SEND_JOB])

    def test_10b_failed_read_back_keeps_the_approve(self):
        write(self.dir / "card.json", {
            "brand": BRAND, "label": LABEL, "date": "01 Jan", "year": 2099, "send_local": "13:00",
            "segments": ["Core"], "links": [],
            "subjects": [{"subject": "A subject", "preview": "A preview"}],
            "final_check": [{"result": "ok", "detail": "all good"}], "status": "draft"})
        write(self.dir / "email.html", "<html><body>hi</body></html>")
        with mock.patch.object(S, "create_draft", lambda *a: {"campaign_id": "NOT-IN-FAKE", "template_id": "T",
                                                               "status": "DRAFT"}), \
                mock.patch.object(S, "send_strategy", lambda lk, slot: dict(LATER)), \
                mock.patch.object(S, "audience", lambda brand, slot: (["Core"], ["SEG1"], [])):
            r = A.approve(BRAND, LABEL, "the owner")
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["fingerprint"].startswith("not read: "), r)
        c = self.card()
        self.assertEqual(c["status"], "approved")
        self.assertNotIn("fingerprint", c["klaviyo"])


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
