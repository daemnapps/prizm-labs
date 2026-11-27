"""An SMS from its text to a person's go (2026-11-04). The card needs the email it follows; Approve runs the
email gate's refusals; Klaviyo gets its two calls through the stand-in; Postscript gets a hand-off and no call.
No network, no key, no platform."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sms  # noqa: E402  first, while this folder is on the path
import importlib.util  # noqa: E402
import klaviyo_upload as K  # noqa: E402
_spec = importlib.util.spec_from_file_location("sms_launch", HERE / "sms_launch.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

BANK = "# Bank\n\n## tube — The Tube\n- Price: **$29.00**\n\n# Ruled by a human\n\n### sale — The sale\n| Pack | starting at $19 a tube |\nNo code necessary.\n"
TEXT = "Last day: starting at $19 a tube. {link} Reply STOP to opt out"


class Launch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = self.ws = Path(self.tmp.name)
        b = ws / "brands" / "zz"
        (b / "products").mkdir(parents=True)
        (b / "products" / "offer-bank.md").write_text(BANK)
        (b / "operations").mkdir()
        self.platform("postscript")
        (b / "email-sms").mkdir()
        (b / "email-sms" / "audience-matrix.json").write_text(json.dumps({"segments": [{"name": "Core | Lead", "id": "SEG1"}]}))
        m = ws / "runs" / "marketing-calendar" / "zz" / "2099-11"
        m.mkdir(parents=True)
        (m / "slots.json").write_text(json.dumps([
            {"id": "nov-01", "date": "2099-11-30", "channel": "email", "segments": ["Core | Lead"]},
            {"id": "nov-02", "date": "2099-11-30", "channel": "sms", "follows": "nov-01", "hour": 12,
             "segments": ["Core | Lead"], "sms_job": "reminder", "sms_beat": "last-chance", "audience_rule": "SMS-consented members only"}]))
        e = ws / "runs" / "email-production" / "zz" / "zz-nov-01" / "deliverable"
        e.mkdir(parents=True)
        (e / "email.json").write_text(json.dumps({"subjects": [{"subject": "Last day"}],
                                                  "button": {"label": "SHOP", "link": "https://shop.test/sale"}}))
        self.email_card = e / K.CARD
        self.email_card.write_text(json.dumps({"state": "scheduled"}))
        self.run = ws / "runs" / "email-production" / "zz" / "zz-nov-02-sms"
        self.run.mkdir(parents=True)
        (self.run / "sms.json").write_text(json.dumps({"brand": "zz", "slot": "nov-02", "date": "2099-11-30",
                                                       "offer": "sale", "job": "reminder", "text": TEXT,
                                                       "state": "ready for review"}))
        self.patches = [mock.patch.object(mod, "WORKSPACE", ws) for mod in (L, sms, K.S)]
        self.patches += [mock.patch.object(K, "switch_state", return_value="on"),
                         mock.patch.object(K, "approvers", return_value=["owner"]),
                         mock.patch.object(sms, "cadence", return_value={"length": {"max_chars": 160, "link_chars": 25,
                                                                                      "opt_out": "Reply STOP to opt out"}})]
        for p in self.patches:
            p.start()
        self.home = ws / "home"
        self.home.mkdir()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def platform(self, name):
        (self.ws / "brands" / "zz" / "operations" / "brand.json").write_text(json.dumps({"sms_platform": name}))

    def approve(self, **kw):
        return L.approve(self.run, "owner", env={}, home=self.home,
                         at=datetime(2099, 11, 1, tzinfo=timezone.utc), **kw)

    def test_the_card_carries_the_link_of_the_email_it_follows(self):
        card, probs = L.make_card(self.run)
        self.assertEqual(probs, [])
        self.assertEqual(card["sent_text"], TEXT.replace("{link}", "https://shop.test/sale"))
        self.assertEqual((card["follows"], card["platform"], card["send_at"]), ("nov-01", "postscript", "2099-11-30T12:00:00"))
        self.assertTrue((self.run / L.CARD).is_file())

    def test_the_designed_emails_link_wins_over_the_copys(self):
        """brand_a-nov-10 glow-up (2026-11-06): the button was moved to the quiz in the design before the Go; the text
        follows the email as it goes out, not the copy's first link."""
        d = self.ws / "runs" / "email-production" / "zz" / "zz-nov-01" / "design"
        d.mkdir(parents=True, exist_ok=True)
        (d / "email.json").write_text(json.dumps({"link": "https://shop.test/quiz"}))
        card, probs = L.make_card(self.run)
        self.assertEqual(probs, [])
        self.assertEqual(card["link"], "https://shop.test/quiz")

    def test_an_email_scheduled_through_its_design_card_lets_the_text_go(self):
        """brand_b-nov-08a (2026-11-06): the designed email was scheduled (klaviyo/card.json) while the copy-line card
        still said waiting; the text follows the email that was actually scheduled."""
        self.email_card.write_text(json.dumps({"state": "waiting"}))
        k = self.email_card.parent.parent / "klaviyo"
        k.mkdir(parents=True, exist_ok=True)
        (k / "card.json").write_text(json.dumps({"status": "scheduled"}))
        self.assertEqual(L.email_state(self.email_card.parent.parent), "scheduled")
        (k / "card.json").write_text(json.dumps({"status": "draft"}))
        self.assertEqual(L.email_state(self.email_card.parent.parent), "waiting")

    def test_no_card_without_its_email(self):
        import shutil
        shutil.rmtree(self.ws / "runs" / "email-production" / "zz" / "zz-nov-01")
        card, probs = L.make_card(self.run)
        self.assertTrue(any("companion" in p for p in probs))
        self.assertFalse((self.run / L.CARD).is_file())

    def test_postscript_is_a_handoff_and_no_call(self):
        L.make_card(self.run)
        calls = []
        card = self.approve(client=lambda *a: calls.append(a))
        self.assertEqual(card["state"], "approved — place in Postscript")
        self.assertEqual(calls, [])
        self.assertIn("https://shop.test/sale", (self.run / L.HANDOFF).read_text())

    def test_klaviyo_is_created_and_scheduled_never_sent_now(self):
        self.platform("klaviyo")
        L.make_card(self.run)
        calls = []

        def client(method, path, body):
            calls.append((method, path, body))
            return {"data": {"id": "CAMP1"}}
        card = self.approve(client=client)
        self.assertEqual([c[:2] for c in calls], [("POST", "campaigns"), ("POST", "campaign-send-jobs")])
        a = calls[0][2]["data"]["attributes"]
        self.assertEqual(a["audiences"]["included"], ["SEG1"])
        self.assertEqual(a["send_strategy"]["method"], "static")
        self.assertEqual(a["campaign-messages"]["data"][0]["attributes"]["definition"]["channel"], "sms")
        self.assertEqual(card["state"], "scheduled")

    def test_the_gate_refuses(self):
        L.make_card(self.run)
        with mock.patch.object(K, "switch_state", return_value="off"):
            with self.assertRaises(K.Held):
                self.approve()
        with self.assertRaises(K.Held):
            L.approve(self.run, "Somebody", env={}, home=self.home, at=datetime(2099, 11, 1, tzinfo=timezone.utc))
        with self.assertRaises(K.Held):                  # the mini never schedules
            L.approve(self.run, "owner", env={"BRAND": "zz", "OUT": "x"}, home=self.home,
                      at=datetime(2099, 11, 1, tzinfo=timezone.utc))
        with self.assertRaises(K.Held):                  # under 30 minutes away
            L.approve(self.run, "owner", env={}, home=self.home, at=datetime(2099, 11, 29, 22, 0, tzinfo=timezone.utc))
        rec = json.loads((self.run / "sms.json").read_text())
        rec["text"] = rec["text"].replace("Last day", "Final day")
        (self.run / "sms.json").write_text(json.dumps(rec))
        with self.assertRaises(K.Held):                  # changed since the card
            self.approve()
        self.assertEqual(json.loads((self.run / L.CARD).read_text())["state"], "waiting")

    def test_no_sms_goes_before_its_email_is_approved(self):
        L.make_card(self.run)
        self.email_card.write_text(json.dumps({"state": "waiting"}))
        with self.assertRaises(K.Held) as h:
            self.approve(client=lambda *a: None)
        self.assertIn("approve the email first", str(h.exception))

    def test_klaviyo_gets_no_second_brand_prefix(self):
        (self.ws / "brands" / "zz" / "operations" / "brand.json").write_text(json.dumps({"sms_platform": "klaviyo", "label": "Zz"}))
        card = {"brand": "zz", "sent_text": "Zz: last day. https://shop.test Reply STOP to opt out"}
        self.assertEqual(L.without_brand_prefix(card), "last day. https://shop.test Reply STOP to opt out")

    def test_every_version_of_its_email_is_approved_first(self):
        L.make_card(self.run)
        v = self.ws / "runs" / "email-production" / "zz" / "zz-nov-01--second" / "deliverable"
        v.mkdir(parents=True)
        (v / "email.json").write_text(json.dumps({"button": {"link": "https://shop.test/sale"}}))
        (v / K.CARD).write_text(json.dumps({"state": "waiting"}))
        with self.assertRaises(K.Held) as h:
            self.approve(client=lambda *a: None)
        self.assertIn("zz-nov-01--second", str(h.exception))

    def test_the_link_comes_from_the_version_carrying_the_texts_offer(self):
        home = self.ws / "runs" / "email-production" / "zz"
        for name, offer, link in (("zz-nov-01--first", "none", "https://shop.test/other"),
                                  ("zz-nov-01--second", "sale", "https://shop.test/the-set")):
            (home / name / "deliverable").mkdir(parents=True)
            (home / name / "deliverable" / "email.json").write_text(json.dumps({"button": {"link": link}}))
            (home / name / "run.json").write_text(json.dumps({"assignment": {"offer": offer}}))
        import shutil
        shutil.rmtree(home / "zz-nov-01")
        card, probs = L.make_card(self.run)
        self.assertEqual(card["link"], "https://shop.test/the-set")

    def test_an_email_for_a_hidden_page_waits_at_approve(self):
        bank = self.ws / "brands" / "zz" / "products" / "offer-bank.md"
        bank.write_text(bank.read_text().replace("## tube — The Tube", "## sale — The sale\n- Store: **hidden until the owner's go**\n\n## tube — The Tube"))
        root = self.ws / "runs" / "email-production" / "zz" / "zz-nov-01"
        (root / "run.json").write_text(json.dumps({"assignment": {"offer": "sale"}}))
        job = {"root": root, "brand": "zz", "label": root.name, "out": root / "deliverable"}
        with mock.patch.object(K, "read_card", return_value={"state": "waiting"}), \
                mock.patch.object(K, "checks_now", side_effect=AssertionError("the gate comes first")):
            with self.assertRaises(K.Held) as h:
                K.schedule_card(job, "owner", env={}, home=self.home)
        self.assertIn("its store page is not open yet", str(h.exception))

    def test_a_text_for_a_hidden_page_waits_at_approve(self):
        L.make_card(self.run)
        bank = self.ws / "brands" / "zz" / "products" / "offer-bank.md"
        bank.write_text(bank.read_text().replace("## tube — The Tube", "## sale — The sale\n- Store: **hidden until the owner's go**\n\n## tube — The Tube"))
        with self.assertRaises(K.Held) as h:
            self.approve(client=lambda *a: None)
        self.assertIn("its store page is not open yet", str(h.exception))
        self.assertEqual(json.loads((self.run / L.CARD).read_text())["state"], "waiting")

    def test_dry_run_names_its_calls_and_makes_none(self):
        self.platform("klaviyo")
        out = L.dry(self.run)
        self.assertEqual(out["would_call"], [("POST", "campaigns"), ("POST", "campaign-send-jobs")])
        self.assertFalse((self.run / L.CARD).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
