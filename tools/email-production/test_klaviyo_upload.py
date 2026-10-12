#!/usr/bin/env python3
"""The Klaviyo uploader's promises, proven without Klaviyo.

    python3 test_klaviyo_upload.py

A made-up brand and hand-off in a temp folder; every Klaviyo call, link
fetch and Keychain read is replaced by a recorder.

  1  --dry-run talks to nothing and writes nothing
  2  a link the hand-off does not name holds the email — no Klaviyo call
  3  the default makes a DRAFT only, writes live-ids.json, and take-back
     puts live_klaviyo_<id> in the ledger
  4  a second run will not make a second draft
  5  --send refuses without the owner's go, refuses a go for another campaign
     or by someone else, and only then creates a send job
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="klaviyo-upload-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import klaviyo_upload as K                        # noqa: E402

BRAND, LABEL, BRIEF = "testbrand", "sep-01", "brief-0999"
URL = "https://example.test/p"
EMAIL = {
    "headline": "A headline", "hero": {"prompt": "a picture", "alt": "a picture"},
    "body": ["First paragraph.", "Second."], "offer": None,
    "button": {"label": "Get it", "link": URL},
    "subjects": [{"subject": "A subject", "preview": "A preview line"},
                 {"subject": "Another", "preview": ""}],
}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1))


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
    cal = WS / "runs/marketing-calendar" / BRAND / "2099-01"     # one month, rewritten per test
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


def files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


class Recorder:
    def __init__(self):
        self.calls = []

    def kl(self, method, path, key, payload=None, form=None):
        self.calls.append((method, path))
        if path == "templates":
            return {"data": {"id": "TPL1"}}
        if path == "campaigns":
            return {"data": {"id": "CAMP1", "relationships": {
                "campaign-messages": {"data": [{"id": "MSG1"}]}}}}
        return {"data": {}}


def patched(rec):
    return [mock.patch.object(K.S, "kl", rec.kl),
            mock.patch.object(K.S, "kl_key", lambda lk: "test-key"),
            mock.patch.object(K.S, "upload", lambda key, p, name: f"https://cdn.test/{name}"),
            mock.patch.object(K.S, "web_copy", lambda p: p),
            mock.patch.object(K, "answers", lambda url: "200")]


class Uploader(unittest.TestCase):
    def setUp(self):
        make_brand("2099-01-01")
        self.root = make_handoff()
        self.rec = Recorder()
        self.p = patched(self.rec)
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_1_dry_run_talks_to_nothing(self):
        before = files(self.root)
        boom = mock.Mock(side_effect=AssertionError("network/Keychain touched in a dry run"))
        with mock.patch.object(K.S, "kl", boom), mock.patch.object(K.S, "kl_key", boom), \
                mock.patch.object(K, "answers", boom), mock.patch.object(K.S, "upload", boom):
            self.assertEqual(K.main(["--handoff", str(self.root), "--dry-run"]), 0)
        self.assertEqual(files(self.root), before)

    def test_2_unnamed_link_holds(self):
        root = make_handoff(links={"link_other": {"id": "link_other", "url": "https://example.test/other"}})
        self.assertEqual(K.main(["--handoff", str(root)]), 1)
        self.assertEqual(self.rec.calls, [])
        st = json.loads((root / K.STATUS).read_text())
        self.assertEqual(st["state"], "HELD")
        self.assertTrue(any(URL in p for p in st["problems"]))

    def test_3_draft_only_and_take_back(self):
        self.assertEqual(K.main(["--handoff", str(self.root)]), 0)
        paths = [c[1] for c in self.rec.calls]
        self.assertEqual(paths, ["templates", "campaigns", "campaign-message-assign-template"])
        self.assertNotIn("campaign-send-jobs", paths)
        live = json.loads((self.root / "returned/live-ids.json").read_text())
        self.assertEqual(live[0]["platform_id"], "CAMP1")
        self.assertEqual(live[0]["channel"], "klaviyo")
        self.assertEqual(live[0]["status"], "DRAFT")
        ledger = (TMP / "staging/ledger.jsonl").read_text().splitlines()
        self.assertIn("live_klaviyo_CAMP1", json.loads(ledger[-1])["live_ids"])
        st = json.loads((self.root / K.STATUS).read_text())
        self.assertEqual((st["state"], st["campaign_id"]), ("DRAFT IN KLAVIYO", "CAMP1"))

    def test_4_no_second_draft(self):
        self.assertEqual(K.main(["--handoff", str(self.root)]), 0)
        n = len(self.rec.calls)
        self.assertEqual(K.main(["--handoff", str(self.root)]), 1)
        self.assertEqual(len(self.rec.calls), n)

    def test_5_send_needs_damons_go(self):
        self.assertEqual(K.main(["--handoff", str(self.root)]), 0)
        self.assertEqual(K.main(["--handoff", str(self.root), "--send"]), 1)        # no file
        write(self.root / K.APPROVALS, [{"campaign_id": "OTHER", "go_by": "the owner"}])
        self.assertEqual(K.main(["--handoff", str(self.root), "--send"]), 1)        # wrong campaign
        write(self.root / K.APPROVALS, [{"campaign_id": "CAMP1", "go_by": "Someone"}])
        self.assertEqual(K.main(["--handoff", str(self.root), "--send"]), 1)        # not the owner
        self.assertNotIn("campaign-send-jobs", [c[1] for c in self.rec.calls])
        write(self.root / K.APPROVALS, [{"campaign_id": "CAMP1", "go_by": "the owner"}])
        self.assertEqual(K.main(["--handoff", str(self.root), "--send"]), 0)
        self.assertEqual(self.rec.calls[-1], ("POST", "campaign-send-jobs"))

    def test_6_past_day_draft_has_no_send_time_and_send_needs_a_time(self):
        make_brand("2000-01-01")
        self.assertEqual(K.main(["--handoff", str(self.root)]), 0)
        write(self.root / K.APPROVALS, [{"campaign_id": "CAMP1", "go_by": "the owner"}])
        self.assertEqual(K.main(["--handoff", str(self.root), "--send"]), 1)
        self.assertNotIn("campaign-send-jobs", [c[1] for c in self.rec.calls])


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
