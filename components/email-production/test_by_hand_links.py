#!/usr/bin/env python3
"""A link the store keeps the check out of (429) is a "by-hand" row on the final check: it holds nothing on the
team's page, and the approval page (approve_klaviyo.py, :8798) waits for an approver to open it and confirm
before Approve or Schedule (the team, 2026-10-27). No network, no key.

    python3 test_by_hand_links.py

  1  an unconfirmed by-hand page holds Approve, naming the page; its live 429 is not a second problem
  2  someone not on approvers.json cannot confirm; nothing is written
  3  the team confirms: the card records who, when and which pages, and Approve stops waiting
  4  a real PROBLEM row still holds after the confirm
  5  Schedule refuses while a by-hand page waits
  6  the page shows the row as BY HAND with the confirm button, and the button goes once confirmed
  7  the team's page and the queue do not count a by-hand row as held
  8  the page's live check asks each page once, whatever its tracking tags
  9  Approve refuses, and reaches nothing, when the team's Drive copy of the pictures can't be read
 10  a pull puts the Drive's pictures over this Mac's and names the ones the Drive does not have
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="by-hand-links-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import approve_klaviyo as A                       # noqa: E402  (imports klaviyo_upload first, then the folder is off sys.path)

K = A.K
HERE = Path(__file__).resolve().parent
BRAND, LABEL = "testbrand", "nov-01"
RUNS = WS / "runs" / "email-production"
PAGE = "https://example.com/products/brush"
HAND = {"result": "by-hand", "detail": PAGE + " → 429: the store would not let the check in; open it and confirm"}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


class Base(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(RUNS, ignore_errors=True)
        self.dir = RUNS / BRAND / LABEL / "klaviyo"
        (self.dir / "email.html").parent.mkdir(parents=True, exist_ok=True)
        (self.dir / "email.html").write_text("<html></html>")
        self.switch = TMP / "send-switch.json"
        write(self.switch, {"email_schedule": "on"})
        self.approvers = TMP / "approvers.json"
        write(self.approvers, {"approvers": ["the owner", "the team"]})
        self.p = [mock.patch.object(A, "RUNS", RUNS),
                  mock.patch.object(A, "FAKE", False),
                  mock.patch.object(A, "audience", lambda c: ([("Core", "SEG1")], [])),
                  mock.patch.object(A, "link_status", lambda u: "429" if "/products/" in u else "200"),
                  mock.patch.object(A, "klaviyo_status", lambda b: {"ok": True, "account": "test", "error": None, "segments": {}}),
                  mock.patch.object(K, "SWITCH_F", self.switch),
                  mock.patch.object(K, "APPROVERS_F", self.approvers)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def make_card(self, rows=None, klaviyo=None):
        c = {"brand": BRAND, "label": LABEL, "date": "02 Nov", "segments": ["Core"],
             "subjects": [{"subject": "A subject", "preview": "A preview"}],
             "links": [PAGE + "?utm_source=klaviyo&utm_content=a", PAGE + "?utm_source=klaviyo&utm_content=b", "https://example.com/"],
             "final_check": rows if rows is not None else [{"result": "ok", "detail": "subject: A subject"}, HAND]}
        if klaviyo:
            c.update(klaviyo={"campaign_id": "CAMP-1", "status": "DRAFT", "hosted": {}}, status="approved")
        write(self.dir / "card.json", c)

    def card(self):
        return json.loads((self.dir / "card.json").read_text())

    def problems(self):
        c = self.card()
        c["_dir"] = str(self.dir)
        return A.check(c)


class ByHand(Base):
    def test_01_waits_and_names_the_page(self):
        self.make_card()
        probs = self.problems()
        self.assertEqual(probs, ["open and confirm by hand first: " + PAGE])

    def test_02_not_an_approver(self):
        self.make_card()
        r = A.confirm_links(BRAND, LABEL, "Someone")
        self.assertFalse(r["ok"])
        self.assertIn("approver", r["error"])
        self.assertNotIn("links_confirmed", self.card())

    def test_03_pm_confirms(self):
        self.make_card()
        r = A.confirm_links(BRAND, LABEL, "the team")
        self.assertTrue(r["ok"], r)
        lc = self.card()["links_confirmed"]
        self.assertEqual((lc["by"], lc["pages"]), ("the team", [PAGE]))
        self.assertTrue(lc["at"])
        self.assertEqual(self.problems(), [])

    def test_04_a_real_problem_still_holds(self):
        self.make_card([HAND, {"result": "PROBLEM", "detail": "https://example.com/gone → 404"}])
        A.confirm_links(BRAND, LABEL, "the team")
        self.assertEqual(self.problems(), ["final check: https://example.com/gone → 404"])

    def test_05_schedule_waits(self):
        self.make_card(klaviyo=True)
        r = A.schedule(BRAND, LABEL, "the team", env={}, home=TMP)
        self.assertFalse(r["ok"])
        self.assertIn("confirm by hand", r["error"])
        self.assertNotIn("scheduled", self.card())

    def test_06_the_page(self):
        self.make_card()
        with mock.patch.object(A, "cards", lambda: [dict(self.card(), _dir=str(self.dir))]):
            html = A.page()
            self.assertIn("BY HAND", html)
            self.assertIn('data-a="confirm"', html)
            self.assertIn("Open 1 link first", html)
            A.confirm_links(BRAND, LABEL, "the team")
            html = A.page()
        self.assertNotIn('data-a="confirm"', html)
        self.assertIn("confirmed by the team", html)
        self.assertIn("Ready for Klaviyo", html)

    def test_07_team_page_and_queue_do_not_hold(self):
        sys.path.insert(0, str(HERE / "adapter"))
        import adapter as AD
        self.assertEqual(AD._held({"final_check": [HAND, {"result": "ok", "detail": "x"}]}), [])
        self.assertEqual(AD._held({"final_check": [HAND, {"result": "PROBLEM", "detail": "y"}]}), ["y"])
        # the emails page (sync.py) splits holds by who fixes them (the team, 2026-10-28): by-hand and notes hold no one,
        # a picture problem holds the team, the words and the product hold only the team
        sys.path.insert(0, str(HERE / "design"))
        import check as CK
        card = {"product_check": [{"result": "PROBLEM", "detail": "price $9", }],
                "final_check": [HAND, {"result": "note", "detail": "shared"},
                                {"result": "PROBLEM", "detail": "the poster picture shows the case", "about": "picture"}]}
        self.assertEqual(CK.holds(card), (["the poster picture shows the case"], ["price $9"]))


class PicturesFromTheDrive(Base):
    """Approve uploads the team's pictures from the Drive, never this Mac's older copies (the team, 2026-10-27)."""
    def test_09_approve_refuses_when_the_drive_cannot_be_read(self):
        self.make_card([{"result": "ok", "detail": "subject: A subject"}])
        (self.dir / "email.html").write_text('<img src="assets/s01.jpg">')
        lf = mock.Mock(pull_build=lambda brand, run: {"got": [], "missing": [], "error": "NoDrive: no route"})
        with mock.patch.object(A, "_layout_file", lambda: lf), mock.patch.object(A, "link_status", lambda u: "200"), \
                mock.patch.object(A.S, "look", lambda b: {}), mock.patch.object(A.S, "kl_key", lambda lk: self.fail("reached Klaviyo")):
            r = A.approve(BRAND, LABEL, "the team")
        self.assertFalse(r["ok"])
        self.assertIn("team's Drive", r["error"])
        self.assertNotIn("klaviyo", self.card())

    def test_10_pull_puts_the_drive_copy_over_the_local_one(self):
        sys.path.append(str(HERE / "design"))
        import layout_file as LF
        run = RUNS / BRAND / LABEL
        (self.dir / "assets").mkdir(exist_ok=True)
        (self.dir / "assets" / "s01.jpg").write_bytes(b"old")
        (self.dir / "email.html").write_text('<img src="assets/s01.jpg"><img src="assets/s02.jpg">')
        asked = []
        class Reach:
            def get(self, parts, name, dest):
                asked.append((parts[-1], name))
                if name == "s02.jpg":
                    return None
                f = Path(dest) / name
                f.write_bytes(b"new from drive")
                return str(f)
        r = LF.pull_build(BRAND, run, reach=Reach())
        self.assertEqual((r["got"], r["missing"], r["error"]), (["s01.jpg"], ["s02.jpg"], None))
        self.assertEqual((self.dir / "assets" / "s01.jpg").read_bytes(), b"new from drive")
        self.assertIn(("assets", "s01.jpg"), asked)


class OneAskPerPage(unittest.TestCase):
    def test_tagged_links_to_one_page_are_asked_once(self):
        asked = []
        class R:
            stdout = "200"
        def run(argv, **kw):
            asked.append(argv[-1])
            return R
        A._ASKED.clear()
        with mock.patch.object(A.subprocess, "run", run):
            codes = [A.link_status(PAGE + "?utm_content=%d" % n) for n in range(6)] + [A.link_status("https://example.com/")]
        self.assertEqual(codes, ["200"] * 7)
        self.assertEqual(asked, [PAGE, "https://example.com/"])


if __name__ == "__main__":
    unittest.main()
