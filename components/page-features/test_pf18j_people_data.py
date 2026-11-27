#!/usr/bin/env python3
"""PF-18j (people data): an assignee per card, each card's two reviewers from its developer, and a Question or Issue on
any Up next or In progress card.

    python3 components/page-features/test_pf18j_people_data.py

    (a) `dev_queue.py assign <card> <person>|none --by <person>` writes ONE review record on RQ-dev-queue-<card>
        through the review module's writer, in the frozen grammar (a `seen` with reason "assign": the manifest has
        no assignment and no comment event, and a `seen` never enters the fold's verdicts or close); the newest wins
    (b) reviewers are the other two of developer, email_lead and designer; a email_lead-built card's are developer and designer; a
        developer outside the three, or none, keeps today's pair; the assignee outranks built_by
    (c) a card email_lead marked Understood counts for her while designer has not; fully reviewed = both of the card's
        own reviewers Understood (the developer's own Understood counts for nothing)
    (d) an unassigned Up next card with a Question sits in Flagged · before-build and returns on Resolve; an In
        progress card with an Issue sits in Flagged · while-building; a shipped one after-ship; nothing waits on a
        mark (state, chip and dispatch untouched)
    (e) Understood on an Up next or In progress card is refused and nothing is written
    (f) /data/dev-queue carries `viewer` when served: the kit's Act's person, else kit_person of the root (the page
        server's way), or None; another source is served as its command printed it

The fixture repo is test_pf18_dev_queue.py's, with test_pf18b_review_marks.py's copies of the real data command and
review module (both test files). Stdlib only, Python 3.9. Writes only in temp folders; no network: the review key is
removed from every environment here, so the module's git door is the one used.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import serve  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo, kept in its test file
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture workspace with the real commands

REAL = pf18b.REAL
ENV = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)


def at(n):
    return "2026-10-29T02:00:%02dZ" % n


class People(unittest.TestCase):
    """(a)-(e) in one fixture workspace per test."""

    def setUp(self):
        self.root = pf18b.workspace()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.rv = dev_queue.review_module()

    def records(self):
        return self.rv.read_records(root=self.root)

    def board(self):
        return pf18.by_id(dev_queue.build(self.root, now=pf18.NOW))

    def assign(self, card, person, n, by="developer"):
        return dev_queue.assign(self.root, card, person, by, env=ENV, commit=False, now=at(n))

    def mark(self, card, word, by, n, **kw):
        return dev_queue.mark(self.root, card, word, by, env=ENV, commit=False, now=at(n), **kw)

    def test_a_assign_writes_one_record_and_newest_wins(self):
        c = self.board()["PF-5"]
        self.assertEqual((c["assignee"], c["developer"], c["reviewers"]), (None, None, ["email_lead", "designer"]))
        out = self.assign("PF-5", "email_lead", 1)
        self.assertEqual(len(self.records()), 1, "one assign, one record")
        rec = out["record"]
        self.assertEqual((rec["item"], rec["reviewer"], rec["kind"]), ("RQ-dev-queue-PF-5", "developer", "review"))
        self.assertEqual(rec["verdict"], {"event": "seen", "reasons": ["assign"], "note": "email_lead"})
        self.rv.validate(rec["verdict"])                   # the frozen grammar's own door
        self.assertEqual(self.rv.fold([rec])["verdicts"], {}, "an assignment is never a verdict")
        self.assertIsNone(self.rv.fold([rec])["close"], "nor a close")
        c = self.board()["PF-5"]
        # narrowed by PF-18m (open issues only), the assigner rule: developer assigned it, so developer does not review it
        self.assertEqual((c["assignee"], c["developer"], c["reviewers"]), ("email_lead", "email_lead", ["designer"]))
        self.assertIsNone(c["marks"], "an assignment is not a mark")
        self.assertEqual(c["column"], "up-next")

        self.assign("PF-5", "designer", 2)
        self.assertEqual(len(self.records()), 2)
        c = self.board()["PF-5"]
        self.assertEqual((c["assignee"], c["reviewers"]), ("designer", ["email_lead"]), "the newest wins")   # PF-18m
        self.assign("PF-5", "none", 3)
        c = self.board()["PF-5"]
        self.assertEqual((c["assignee"], c["developer"], c["reviewers"]), (None, None, ["email_lead", "designer"]))

        n = len(self.records())
        for card, person in (("PF-5", "editor"), ("PF-5", ""), ("LD-1", "email_lead"), ("DB-7", "email_lead"), ("pf-5", "email_lead")):
            with self.assertRaises(self.rv.Refused, msg=(card, person)):
                self.assign(card, person, 4)
        self.assertEqual(len(self.records()), n, "every refusal before the write")

    def test_a_the_command_commits_one_record(self):
        p = subprocess.run([sys.executable, os.path.join(self.root, "components/page-features/dev_queue.py"),
                            "assign", "PF-11", "email_lead", "--by", "developer"], cwd=self.root, capture_output=True,
                           text=True, env=pf18b.env_for(self.root), timeout=120, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("PF-11 assigned to email_lead by developer", p.stdout)
        recs = self.records()
        self.assertEqual(len(recs), 1)
        log = subprocess.run(["git", "log", "-1", "--format=%s", "--name-only"], cwd=self.root, capture_output=True,
                             text=True, env=pf18b.env_for(self.root)).stdout.split("\n")
        self.assertTrue(log[0].startswith("review: seen RQ-dev-queue-PF-11"), log)
        self.assertEqual([x for x in log[1:] if x.strip()], [pf18b.RECORDS + "/" + self.rv.filename(recs[0])])
        c = self.board()["PF-11"]
        self.assertEqual((c["built_by"], c["assignee"], c["developer"], c["reviewers"]),
                         ("developer", "email_lead", "email_lead", ["designer"]),
                         "the assignee outranks built_by; its assigner, developer, is no reviewer (PF-18m (open issues only))")
        self.assertEqual((c["column"], c["progress"]["chip"]), ("in-progress", "Building"))
        p = subprocess.run([sys.executable, os.path.join(self.root, "components/page-features/dev_queue.py"),
                            "assign", "PF-11", "editor", "--by", "developer"], cwd=self.root, capture_output=True,
                           text=True, env=pf18b.env_for(self.root), timeout=120, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 2)
        self.assertIn("REFUSED", p.stderr)
        self.assertEqual(len(self.records()), 1)

    def test_b_reviewers_are_the_other_two(self):
        self.assertEqual(dev_queue.reviewers_of("developer"), ["email_lead", "designer"])
        self.assertEqual(dev_queue.reviewers_of("email_lead"), ["developer", "designer"])
        self.assertEqual(dev_queue.reviewers_of("designer"), ["developer", "email_lead"])
        for outside in ("editor", None):
            self.assertEqual(dev_queue.reviewers_of(outside), list(dev_queue.REVIEWERS), "today's pair")
        c = self.board()
        for cid in c:
            card = c[cid]
            self.assertEqual(len(card["reviewers"]), 2, cid)
            self.assertNotIn(card["developer"], card["reviewers"], cid)
            self.assertEqual(card["developer"], card["assignee"] or card["built_by"], cid)
        self.assertEqual((c["PF-4b"]["developer"], c["PF-4b"]["reviewers"]), ("developer", ["email_lead", "designer"]))
        self.assertEqual((c["LD-2"]["developer"], c["LD-2"]["reviewers"]), ("designer", ["developer", "email_lead"]))

    def test_b_a_email_lead_built_card_is_reviewed_by_developer_and_designer(self):
        c = self.board()["PF-3"]
        self.assertEqual((c["built_by"], c["assignee"], c["reviewers"]), ("email_lead", None, ["developer", "designer"]))
        self.assertEqual(c["review"], [{"person": "developer", "understood": None}, {"person": "designer", "understood": None}])
        self.mark("PF-3", "understood", "email_lead", 1)
        c = self.board()["PF-3"]
        self.assertEqual(c["column"], "shipped", "the developer's own Understood counts for nothing")
        self.assertNotIn("email_lead", [r["person"] for r in c["review"]])
        self.mark("PF-3", "understood", "designer", 2)
        self.assertEqual(self.board()["PF-3"]["column"], "shipped", "one of its two reviewers")
        self.mark("PF-3", "understood", "developer", 3)
        c = self.board()["PF-3"]
        self.assertEqual(c["column"], "reviewed", "both of the card's own reviewers Understood")
        self.assertEqual([(r["person"], r["understood"]) for r in c["review"]], [("developer", True), ("designer", True)])

    def test_c_stephs_understood_counts_for_her_while_designer_has_not(self):
        self.mark("PF-15", "understood", "email_lead", 1)
        c = self.board()["PF-15"]
        self.assertEqual(c["reviewers"], ["email_lead", "designer"])
        self.assertEqual([(r["person"], r["understood"]) for r in c["review"]], [("email_lead", True), ("designer", None)])
        self.assertEqual(c["column"], "shipped", "not fully reviewed: designer has not")
        mine = [m for m in c["marks"] if m["person"] == "email_lead"]
        self.assertEqual([m["mark"] for m in mine], ["understood"], "her own mark, for her view")
        # assigned to email_lead, her Understood stops counting (she is the developer); narrowed by PF-18m (open issues
        # only): developer assigned it, so designer alone reviews it
        self.assign("PF-15", "email_lead", 2)
        c = self.board()["PF-15"]
        self.assertEqual([(r["person"], r["understood"]) for r in c["review"]], [("designer", None)])

    def test_d_an_up_next_question_flags_before_build_and_returns_on_resolve(self):
        before = self.board()["PF-5"]
        self.assertEqual((before["assignee"], before["column"], before["pending"]), (None, "up-next", "approved"))
        self.assertNotIn("flag_stage", before, "only when Flagged")
        self.mark("PF-5", "question", "designer", 1, note="which mock?")
        c = self.board()["PF-5"]
        self.assertEqual((c["column"], c["flag_stage"]), ("flagged", "before-build"))
        self.assertEqual((c["state"], c["pending"], c["review"]), ("up-next", "approved", None),
                         "nothing waits on a mark: its state and chip stay")
        self.assertEqual([(m["person"], m["mark"], m["open"]) for m in c["marks"]], [("designer", "question", True)])
        self.assertIn("marked question", [h["what"] for h in c["history"]])
        self.mark("PF-5", "resolve", "designer", 2)
        c = self.board()["PF-5"]
        self.assertEqual(c["column"], "up-next", "Resolve returns it to its column")
        self.assertNotIn("flag_stage", c)

        self.mark("PF-11", "issue", "email_lead", 3, note="wrong file")
        self.mark("PF-16", "question", "developer", 4)
        c = self.board()
        self.assertEqual((c["PF-11"]["column"], c["PF-11"]["flag_stage"], c["PF-11"]["progress"]["chip"]),
                         ("flagged", "while-building", "Building"))
        self.assertEqual((c["PF-16"]["column"], c["PF-16"]["flag_stage"]), ("flagged", "after-ship"))
        self.mark("PF-11", "resolve", "developer", 5)
        self.assertEqual(self.board()["PF-11"]["column"], "in-progress")

    def test_e_understood_on_an_up_next_card_is_refused(self):
        for card in ("PF-5", "PF-11"):
            with self.assertRaises(self.rv.Refused) as cm:
                self.mark(card, "understood", "email_lead", 1)
            self.assertIn("Understood is for shipped cards on the board", str(cm.exception))
        self.assertEqual(self.records(), [], "nothing written")
        self.assertEqual(self.board()["PF-5"]["column"], "up-next")


class Viewer(unittest.TestCase):
    """(f) through the kit's real handler and a real socket; the source's command is a stand-in runner."""

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="pf18j-viewer-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        pf18.write(self.root, "components/page-features/dev_queue.py", "# stand-in\n")
        pf18.write(self.root, "team/people/email_lead/identity.json", json.dumps(
            {"person": "email_lead", "emails": [{"address": "email_lead@example.com"}]}))
        self.decl = {"dev-queue": {"argv": ["components/page-features/dev_queue.py"], "cache_s": 60},
                     "other": {"argv": ["components/page-features/dev_queue.py", "x"], "cache_s": 60}}

    def get(self, act, route):
        src = serve.Sources(self.decl, root=self.root, runner=lambda argv: '{"kind": "dev-queue", "cards": []}\n')
        h = type("H", (serve.KitHandler,), {"root": self.root, "status": None, "src": src, "act": act,
                                             "page_rel": "_templates/dev-queue.html"})
        srv = ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (srv.server_address[1], route), timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_f_viewer_present_when_served(self):
        code, doc = self.get(serve.Act("dev-queue", self.root, "email_lead", None), "/data/dev-queue")
        self.assertEqual(code, 200)
        self.assertEqual(doc, {"kind": "dev-queue", "cards": [], "viewer": "email_lead"})
        code, doc = self.get(serve.Act("dev-queue", self.root, None, "no person for this clone"), "/data/dev-queue")
        self.assertEqual((code, doc["viewer"]), (200, None), "or none")
        code, doc = self.get(serve.Act("dev-queue", self.root, "email_lead", None), "/data/other")
        self.assertNotIn("viewer", doc, "only /data/dev-queue")

    def test_f_the_page_servers_way_kit_person(self):
        # server.py's handler carries no Act: the viewer is kit_person of its own root, as its buttons' person is
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "email_lead@example.com"], cwd=self.root, check=True)
        serve._VIEWERS.pop(self.root, None)
        code, doc = self.get(None, "/data/dev-queue")
        self.assertEqual((code, doc["viewer"]), (200, "email_lead"))
        self.assertEqual(serve.kit_person(self.root), ("email_lead", None))


if __name__ == "__main__":
    unittest.main()
