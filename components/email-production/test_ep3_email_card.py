#!/usr/bin/env python3
"""EP-3 (email approval card), proven against a fake Klaviyo — no network,
no key, no Keychain.

    python3 test_ep3_email_card.py

A made-up brand, hand-off and run in a temp folder; Klaviyo is
fake_klaviyo.FakeKlaviyo; the off-switch and approver list are temp files;
the machine-run guard reads env={} and a temp home; the clock is passed in.
Every refusal asserts no campaign-send-jobs call and an unchanged card state.

  1  the upload writes the card: fields, fingerprint parts, checks, link, send
  2  Approve schedules: state scheduled, approval by the owner, two log lines,
     the campaign "Scheduled", never sent
  3  a changed subject is refused naming subject; changed HTML naming html
  4  a first send less than 30 minutes away is refused
  5  the mini, a lab-run job and a worker job are refused
  6  the off-switch off, or its file missing, is refused
  7  a failing check (links.json no longer names the URL) is refused
  8  someone not on approvers.json is refused
  9  a send strategy that is not a fixed time is refused
  10 send back needs reasons and a note; then the card is sent-back, logged,
     and a later approve is refused
  11 --card on an existing draft writes a waiting card (and refuses over a
     scheduled one)
  12 the page: /api/waiting lists the card; text/plain POST 415; a bad Host
     403; Approve 200 scheduled; stdlib `email` is not this folder's email.py
  13 a Klaviyo error on the schedule leaves the card approved; retry schedules
"""
import datetime
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ep3-email-card-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import klaviyo_upload as K                        # noqa: E402  (takes this folder off sys.path)
import http.client                                # noqa: E402  (after K: stdlib email, not ./email.py)


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

BRAND, LABEL, BRIEF = "testbrand", "sep-01", "brief-0999"
URL = "https://example.test/p"
EMAIL = {
    "headline": "A headline", "hero": {"prompt": "a picture", "alt": "a picture"},
    "body": ["First paragraph.", "Second."], "offer": None,
    "button": {"label": "Get it", "link": URL},
    "subjects": [{"subject": "A subject", "preview": "A preview line"},
                 {"subject": "Another", "preview": ""}],
}
UTC = datetime.timezone.utc
EARLIEST = datetime.datetime(2098, 12, 31, 23, 0, tzinfo=UTC)    # 2099-01-01 13:00 local, at UTC+14
AT = datetime.datetime(2098, 12, 31, 12, 0, tzinfo=UTC)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1))


# copied from test_klaviyo_upload.py (no import of the other test)
def make_brand(day):
    b = WS / "brands" / BRAND / "email-sms"
    write(b / "simple.json", {
        "logo": {"url": "https://example.test/logo.png", "alt": "T", "width": 100,
                 "link": "https://example.test"},
        "from": {"email": "hi@example.test", "label": "Test"},
        "send_time": {"local": "13:00", "recipient_time_zone": True},
        "klaviyo_key": "KLAVIYO_TESTBRAND_KEY",
        "fonts": {"headline": "serif", "body": "sans-serif"},
        "colors": {"page": "#fff", "card": "#fff", "text": "#000", "muted": "#777",
                   "button": "#000", "button_text": "#fff"}})
    write(b / "audience-matrix.json", {"segments": [{"name": "Core | Churned", "id": "SEG1"}]})
    cal = WS / "runs/marketing-calendar" / BRAND / "2099-01"
    write(cal / "run.json", {"brand": BRAND})
    write(cal / "slots.json", [{"id": LABEL, "date": day, "segment": "Core | Churned",
                                "segments": ["Core | Churned"], "type": "what-went-wrong"}])


def make_handoff(links=None):
    root = TMP / "staging/klaviyo-uploader" / BRAND / f"klaviyo-uploader-handoff_{BRAND}_2099-01-01"
    shutil.rmtree(root, ignore_errors=True)
    write(root / "manifest.json", {"schema": "handoff/1", "name": root.name, "role": "klaviyo-uploader",
                                   "brand": BRAND, "briefs": [{"id": BRIEF}], "ids": {},
                                   "drive": {}, "returned": {"expected": [], "received": []}})
    write(root / "assets/index.json", {"email_run": {"source": f"runs/email-production/{BRAND}/{LABEL}",
                                                     "here": "assets/email/"}})
    write(root / "assets/email/deliverable/email.json", EMAIL)
    write(root / "assets/email/deliverable/check.json", {"delivery": {"result": "pass", "problems": []}})
    write(root / "assets/email/media/hero.png", "png")
    write(root / "references/links.json", links if links is not None else
          {"link_test_p": {"id": "link_test_p", "url": URL}})
    write(root / "returned/README.md", "returned\n")
    return root


def make_run():
    rd = WS / "runs/email-production" / BRAND / LABEL
    shutil.rmtree(rd, ignore_errors=True)
    write(rd / "run.json", {"brand": BRAND})
    write(rd / "deliverable/email.json", EMAIL)
    write(rd / "deliverable/check.json", {"delivery": {"result": "pass", "problems": []}})
    write(rd / "media/hero.png", "png")
    return rd


class Card(unittest.TestCase):
    def setUp(self):
        make_brand("2099-01-01")
        self.root = make_handoff()
        self.fake = FK.FakeKlaviyo()
        self.home = TMP / "home"
        shutil.rmtree(self.home, ignore_errors=True)
        self.home.mkdir(parents=True)
        self.switch = TMP / "send-switch.json"
        write(self.switch, {"email_schedule": "on"})
        self.approvers = TMP / "approvers.json"
        write(self.approvers, {"approvers": ["the owner"]})
        self.p = [mock.patch.object(K.S, "kl", self.fake.kl),
                  mock.patch.object(K.S, "kl_key", lambda lk: "test-key"),
                  mock.patch.object(K.S, "upload", lambda key, p, name: f"https://cdn.test/{name}"),
                  mock.patch.object(K.S, "web_copy", lambda p: p),
                  mock.patch.object(K, "answers", lambda url: "200"),
                  mock.patch.object(K, "SWITCH_F", self.switch),
                  mock.patch.object(K, "APPROVERS_F", self.approvers)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    # ------------------------------------------------------------ helpers
    def upload(self):
        self.assertEqual(K.main(["--handoff", str(self.root)]), 0)
        self.job = K.from_handoff(self.root)
        self.cid = self.card()["campaign_id"]
        return self.card()

    def card(self):
        return json.loads((self.root / K.CARD).read_text())

    def sends(self):
        return [c for c in self.fake.calls if c[1] == "campaign-send-jobs"]

    def schedule(self, by="the owner", env=None, at=AT):
        return K.schedule_card(self.job, by, env={} if env is None else env, home=self.home, at=at)

    def refused(self, words, **kw):
        before = self.card()["state"]
        with self.assertRaises(K.Held) as h:
            self.schedule(**kw)
        said = "; ".join(h.exception.args[0])
        self.assertIn(words, said)
        self.assertEqual(self.sends(), [])
        self.assertEqual(self.card()["state"], before)
        return said

    # -------------------------------------------------------------- cases
    def test_01_upload_writes_the_card(self):
        c = self.upload()
        self.assertEqual((c["schema"], c["state"], c["brand"], c["email"], c["from"], c["pick"]),
                         ("ep3-email-card/1", "waiting", BRAND, LABEL, "handoff", 0))
        self.assertEqual((c["subject"], c["preview"]), ("A subject", "A preview line"))
        self.assertEqual(c["audience"], [{"segment": "Core | Churned", "id": "SEG1"}])
        self.assertEqual(c["klaviyo_link"], K.KLAVIYO_LINK.format(id=self.cid))
        self.assertEqual(c["send"]["strategy"]["method"], "static")
        self.assertEqual(c["send"]["earliest_utc"], EARLIEST.isoformat())
        self.assertEqual(set(c["fingerprint"]["parts"]), {"subject", "preview", "html", "audience", "send_time"})
        self.assertEqual(c["fingerprint"]["sha256"],
                         K._sha(json.dumps(c["fingerprint"]["parts"], sort_keys=True)))
        html = (self.root / K.CARD_HTML).read_text()
        self.assertEqual(html, self.fake.campaigns[self.cid]["html"])
        self.assertEqual(c["fingerprint"]["parts"]["html"], K._sha(html))
        checks = {r["check"]: r["result"] for r in c["checks"]}
        self.assertEqual(checks["delivery gate"], "ok")
        self.assertIn("Klaviyo's HTML: link allowed", checks)
        self.assertFalse(any(r["result"] == "PROBLEM" for r in c["checks"]))
        self.assertEqual((c["approval"], c["scheduled"], c["schedule_error"]), (None, None, None))
        self.assertEqual(self.sends(), [])

    def test_02_approve_schedules(self):
        self.upload()
        cid, c = self.schedule(by="")              # one approver: a blank name is that approver
        self.assertEqual(cid, self.cid)
        self.assertEqual(c["state"], "scheduled")
        self.assertEqual(self.card()["state"], "scheduled")
        self.assertEqual((c["approval"]["by"], c["approval"]["decision"]), ("the owner", "approve"))
        self.assertEqual(c["approval"]["fingerprint"], c["fingerprint"]["sha256"])
        self.assertEqual(c["scheduled"]["klaviyo_status"], "Scheduled")
        self.assertEqual(self.sends(), [("POST", "campaign-send-jobs")])
        self.assertEqual(self.fake.campaigns[self.cid]["status"], "Scheduled")
        log = [json.loads(l) for l in (self.root / K.LOG).read_text().splitlines()]
        self.assertEqual([l["decision"] for l in log], ["approve", "scheduled"])
        self.assertTrue(all(l["by"] == "the owner" and l["campaign_id"] == self.cid for l in log))
        st = json.loads((self.root / K.STATUS).read_text())
        self.assertEqual(st["state"], "SCHEDULED IN KLAVIYO")
        self.assertIn("approved by the owner on the email approval page", st["send_go"])
        with self.assertRaises(K.Held):            # once scheduled, never again
            self.schedule()
        self.assertEqual(len(self.sends()), 1)

    def test_03_changed_since_checks(self):
        self.upload()
        self.fake.campaigns[self.cid]["subject"] = "A changed subject"
        self.assertIn("subject", self.refused("the email changed since its checks passed"))
        self.fake.campaigns[self.cid]["subject"] = "A subject"
        self.fake.campaigns[self.cid]["html"] += "<p>one more line</p>"
        said = self.refused("the email changed since its checks passed")
        self.assertIn("html", said)
        self.assertNotIn("subject", said)

    def test_04_under_thirty_minutes(self):
        self.upload()
        self.refused("less than 30 minutes", at=EARLIEST - datetime.timedelta(minutes=10))

    def test_05_never_on_a_machine(self):
        self.upload()
        write(self.home / ".workflow-worker.env", "")
        self.refused("this is the mini")
        (self.home / ".workflow-worker.env").unlink()
        self.refused("lab-run job", env={"BRAND": BRAND, "OUT": "/tmp/x"})
        self.refused("worker job", env={"WORKER_WS": "/tmp/ws"})

    def test_06_off_switch(self):
        self.upload()
        write(self.switch, {"email_schedule": "off"})
        self.refused("the email off-switch is off")
        with mock.patch.object(K, "SWITCH_F", TMP / "no-such-switch.json"):
            self.refused("the email off-switch is off")

    def test_07_failing_check(self):
        self.upload()
        write(self.root / "references/links.json",
              {"link_other": {"id": "link_other", "url": "https://example.test/other"}})
        self.job = K.from_handoff(self.root)           # as the page does, per request
        self.refused("link allowed")

    def test_08_not_an_approver(self):
        self.upload()
        self.refused("not on the approver list", by="Someone")

    def test_09_send_strategy_not_fixed(self):
        self.upload()
        self.fake.campaigns[self.cid]["strategy"] = {"method": "immediate"}
        self.refused("send strategy is immediate")

    def test_10_send_back(self):
        self.upload()
        with self.assertRaises(K.Held):
            K.send_back(self.job, "the owner", [], "a note")
        with self.assertRaises(K.Held):
            K.send_back(self.job, "the owner", ["words"], "  ")
        with self.assertRaises(K.Held):
            K.send_back(self.job, "the owner", ["no-such-reason"], "a note")
        self.assertEqual(self.card()["state"], "waiting")
        n = len(self.fake.calls)
        c = K.send_back(self.job, "the owner", ["words", "subject"], "the second line is wrong")
        self.assertEqual(len(self.fake.calls), n)      # no Klaviyo call; the draft stays
        self.assertEqual(c["state"], "sent-back")
        self.assertEqual(c["approval"]["decision"], "send-back")
        self.assertEqual([r["id"] for r in c["approval"]["reasons"]], ["words", "subject"])
        log = [json.loads(l) for l in (self.root / K.LOG).read_text().splitlines()]
        self.assertEqual([l["decision"] for l in log], ["send-back"])
        self.refused("this card is sent-back")

    def test_11_card_for_an_existing_draft(self):
        self.upload()
        (self.root / K.CARD).unlink()                 # a draft with no card yet (the owner's own, or --push)
        (self.root / K.CARD_HTML).unlink()
        self.assertEqual(K.main(["--handoff", str(self.root), "--card"]), 0)
        c = self.card()
        self.assertEqual((c["state"], c["campaign_id"]), ("waiting", self.cid))
        c["state"] = "scheduled"
        write(self.root / K.CARD, c)
        self.assertEqual(K.main(["--handoff", str(self.root), "--card"]), 1)
        self.assertEqual(self.card()["state"], "scheduled")
        self.assertEqual(self.sends(), [])

    def test_12_the_page(self):
        rd = make_run()
        self.assertEqual(K.main(["--run", str(rd)]), 0)
        self.assertEqual(json.loads((rd / "deliverable" / K.CARD).read_text())["state"], "waiting")
        EA = load("email_approve")
        EA.ENV, EA.HOME = {}, self.home
        srv = EA.server(["--port", "0", "--root", str(WS / "runs/email-production"),
                         "--fake-klaviyo", "--switch", str(self.switch)])
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        def call(method, path, body=None, headers=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
            conn.request(method, path, body=json.dumps(body) if body is not None else None,
                         headers=headers or {})
            r = conn.getresponse()
            out = (r.status, json.loads(r.read() or b"{}"))
            conn.close()
            return out

        try:
            code, got = call("GET", "/api/waiting")
            self.assertEqual(code, 200)
            self.assertEqual([w["id"] for w in got["waiting"]], [f"{BRAND}/{LABEL}"])
            self.assertTrue(got["fake"])
            self.assertEqual(got["switch"], "on")
            self.assertTrue(got["waiting"][0]["checks_ok"])
            body = {"id": f"{BRAND}/{LABEL}", "by": "the owner"}
            self.assertEqual(call("POST", "/api/approve", body, {"Content-Type": "text/plain"})[0], 415)
            self.assertEqual(call("GET", "/api/waiting", headers={"Host": f"evil.test:{port}"})[0], 403)
            self.assertEqual(call("POST", "/api/approve", body,
                                  {"Content-Type": "application/json", "Host": f"evil.test:{port}"})[0], 403)
            self.assertEqual(call("POST", "/api/approve", {"id": "nobody/none", "by": "the owner"},
                                  {"Content-Type": "application/json"})[0], 404)
            self.assertEqual(json.loads((rd / "deliverable" / K.CARD).read_text())["state"], "waiting")
            code, got = call("POST", "/api/approve", body, {"Content-Type": "application/json"})
            self.assertEqual(code, 200, got)
            self.assertEqual((got["ok"], got["state"], got["id"]), (True, "scheduled", f"{BRAND}/{LABEL}"))
            self.assertEqual(json.loads((rd / "deliverable" / K.CARD).read_text())["state"], "scheduled")
            self.assertEqual([c for c in EA.FAKE.calls if c[1] == "campaign-send-jobs"],
                             [("POST", "campaign-send-jobs")])
            self.assertEqual(call("GET", "/api/waiting")[1]["waiting"], [])
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertIn("email", sys.modules)
        here = str(K.HERE.resolve())
        self.assertFalse(str(Path(sys.modules["email"].__file__).resolve()).startswith(here + os.sep))

    def test_13_klaviyo_error_then_retry(self):
        self.upload()
        self.fake.fail.add("campaign-send-jobs")
        with self.assertRaises(K.Held) as h:
            self.schedule()
        self.assertIn("Klaviyo refused the schedule", "; ".join(h.exception.args[0]))
        c = self.card()
        self.assertEqual(c["state"], "approved")
        self.assertTrue(c["schedule_error"]["error"])
        self.fake.fail.clear()
        cid, c = self.schedule()
        self.assertEqual((c["state"], c["schedule_error"]), ("scheduled", None))
        log = [json.loads(l)["decision"] for l in (self.root / K.LOG).read_text().splitlines()]
        self.assertEqual(log, ["approve", "error", "approve", "scheduled"])


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
