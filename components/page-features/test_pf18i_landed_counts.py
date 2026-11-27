#!/usr/bin/env python3
"""PF-18i (landed counts): a card whose heading says LANDED, MERGED or CLOSED with a commit on HEAD counts as Shipped
on the Dev-queue board.

    python3 components/page-features/test_pf18i_landed_counts.py

    (a) "LANDED <sha>" of a commit whose subject is "emails page: PF-X (tag) — …" → Shipped at its committer time,
        `via` "heading", the sha kept, built_by its author (PF-18g (built by)'s "commit" rule)
    (b) "CLOSED at <sha> — absorbed by …" → Shipped
    (c) a heading sha not in the repo → stays Up next, one warning in `sources.warnings`; a sha of a commit that is in
        the repo but not reachable from HEAD → the same
    (d) a merge commit wins over a LANDED heading, and a direct commit wins over one too
    (e) a lead subject "lead: PF-Y (tag) carded" → not shipped (DIRECT_RE is not widened)
    plus: a request newer than the heading's commit keeps the card In progress (the direct commit's rule); a sha after
    the next ";" is not the ship word's; every heading sha is resolved by ONE git log and one rev-list of HEAD

The fixture lives in this file (no .md fixtures under components/); the repo helpers are test_pf18_dev_queue's.
Stdlib only, Python 3.9. Writes only in temp folders; no network.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  Repo, write, request

NOW = "2026-10-30T05:00:00Z"
MISSING = "0123abcd99"

DECK = """# page-features cards (fixture)

### PF-50 — session build: built in a person's own session (carded 2026-10-28 by the lead; owner developer (assumption); LANDED {landed})
### PF-51 — absorbed card: another card did it (carded 2026-10-28 by the lead; owner developer (assumption); CLOSED at {closed} — absorbed by LD-77 (one person resolver))
### PF-52 — wrong sha: the heading names no commit here (carded 2026-10-28 by the lead; APPROVED; LANDED %s)
### PF-53 — merged card: a merge commit and a heading (carded 2026-10-28 by the lead; LANDED {landed})
### PF-54 — go button: only carded so far (carded 2026-10-28 by the lead; APPROVED)
### PF-55 — side branch: the sha is not on HEAD (carded 2026-10-28 by the lead; MERGED {side})
### PF-56 — direct card: a direct commit and a heading (carded 2026-10-28 by the lead; LANDED {closed})
### PF-57 — rebuilt card: a request after its landing (carded 2026-10-28 by the lead; LANDED {landed})
### PF-58 — far sha: the sha sits after the next semicolon (carded 2026-10-28 by the lead; CLOSED as not needed; see {landed})
""" % MISSING


def fixture():
    root = os.path.realpath(tempfile.mkdtemp(prefix="pf18i-"))
    os.makedirs(os.path.join(root, "brands"))
    for pid, email in pf18.EMAILS.items():
        pf18.write(root, "team/people/%s/identity.json" % pid,
                   json.dumps({"person": pid, "emails": [{"address": email}]}))
    pf18.write(root, "team/id-tags.json", json.dumps({"_readme": "fixture"}))
    pf18.request(root, "2026-10-29T09:00:00Z", "designer", "impl-pf57-again",
                 {"action": "implement", "cards": ["PF-57"]})
    pf18.request(root, "2026-10-29T09:05:00Z", "mini-worker", "impl-pf57-again", {"status": "running", "detail": "go"})
    git = pf18.Repo(root)
    git.commit("lead: card the deck", "2026-10-28T00:00:00Z")
    shas = {"landed": git.commit("emails page: PF-50 (session build) — the page does the thing (email_lead, 2026-10-29)",
                                 "2026-10-29T03:00:00Z", "email_lead"),
            "closed": git.commit("impl(system-path): LD-77 — the one person resolver", "2026-10-29T04:00:00Z")}
    git.commit("lead: PF-54 (go button) carded", "2026-10-29T04:30:00Z")
    git.merge("merge PF-53 (merged card) — record done", "2026-10-29T05:00:00Z")
    git.commit("PF-56 (direct card), built on main", "2026-10-29T06:00:00Z", "designer")
    tree = git.git("rev-parse", "HEAD^{tree}")
    shas["side"] = git.git("commit-tree", tree, "-p", git.git("rev-parse", "HEAD"), "-m", "PF-55 side work, never merged")
    deck = DECK.format(**dict((k, v[:10]) for k, v in shas.items()))
    pf18.write(root, "new-workflow-design/builds/page-features/task-cards.md", deck)
    return root, shas


class LandedCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root, cls.shas = fixture()
        cls.started = []
        real = subprocess.run

        def spy(argv, *a, **k):
            cls.started.append(list(argv))
            return real(argv, *a, **k)
        dev_queue.subprocess.run = spy
        try:
            cls.doc = dev_queue.build(cls.root, now=NOW)
        finally:
            dev_queue.subprocess.run = real
        cls.cards = pf18.by_id(cls.doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_a_landed_heading_ships_at_its_commit(self):
        c = self.cards["PF-50"]
        self.assertEqual((c["state"], c["column"]), ("shipped", "shipped"))
        self.assertEqual(c["merged"]["via"], "heading")
        self.assertEqual(c["merged"]["sha"], self.shas["landed"][:10])
        self.assertEqual(c["merged"]["at"], "2026-10-29T03:00:00Z", "the commit's committer time")
        self.assertTrue(c["merged"]["subject"].startswith("emails page: PF-50 (session build)"))
        self.assertEqual((c["built_by"], c["built_by_from"]), ("email_lead", "commit"), "the commit's author")
        self.assertEqual(c["owner"], "developer", "the build owner stays the heading's")
        self.assertIsNone(c["pending"])
        self.assertIn({"at": "2026-10-29T03:00:00Z", "what": "committed on main", "by": None,
                       "sha": self.shas["landed"][:10]}, c["history"])
        self.assertNotIn("landed", c, "the heading's sha list is internal")

    def test_b_closed_at_ships(self):
        c = self.cards["PF-51"]
        self.assertEqual(c["column"], "shipped")
        self.assertEqual((c["merged"]["via"], c["merged"]["sha"]), ("heading", self.shas["closed"][:10]))
        self.assertEqual(c["merged"]["at"], "2026-10-29T04:00:00Z")
        self.assertEqual((c["built_by"], c["built_by_from"]), ("developer", "commit"))

    def test_c_a_sha_not_on_head_is_ignored_and_warned_once(self):
        for cid, short in (("PF-52", MISSING), ("PF-55", self.shas["side"][:10])):
            c = self.cards[cid]
            self.assertEqual((c["state"], c["column"], c["merged"]), ("up-next", "up-next", None), cid)
            lines = [w for w in self.doc["sources"]["warnings"] if short in w]
            self.assertEqual(len(lines), 1, (cid, self.doc["sources"]["warnings"]))
            self.assertIn(cid, lines[0])
        self.assertEqual(self.cards["PF-52"]["pending"], "approved", "the card stays where it was, chip and all")
        self.assertEqual(len(self.doc["sources"]["warnings"]), 2, self.doc["sources"]["warnings"])

    def test_d_a_merge_wins_then_a_direct_commit(self):
        m = self.cards["PF-53"]
        self.assertEqual((m["column"], m["merged"]["via"], m["merged"]["at"]),
                         ("shipped", "merge commit", "2026-10-29T05:00:00Z"))
        d = self.cards["PF-56"]
        self.assertEqual((d["column"], d["merged"]["via"], d["merged"]["at"]),
                         ("shipped", "direct commit", "2026-10-29T06:00:00Z"))
        self.assertEqual((d["built_by"], d["built_by_from"]), ("designer", "commit"))

    def test_e_a_lead_subject_is_not_a_ship(self):
        c = self.cards["PF-54"]
        self.assertEqual((c["state"], c["merged"]), ("up-next", None))
        self.assertIsNone(dev_queue.DIRECT_RE.match("lead: PF-54 (go button) carded"))
        self.assertIsNone(dev_queue.DIRECT_RE.match("emails page: PF-50 (session build) — x"))

    def test_a_newer_request_keeps_it_in_progress(self):
        c = self.cards["PF-57"]
        self.assertEqual((c["state"], c["progress"]["chip"]), ("in-progress", "Building"))
        self.assertEqual((c["built_by"], c["built_by_from"]), ("designer", "request"))

    def test_the_sha_belongs_to_its_own_segment(self):
        self.assertEqual(self.cards["PF-58"]["column"], "up-next")
        self.assertEqual(dev_queue.landed_of("x; LANDED 83080b3f11; MERGED at abcdef1 2026-10-07 [7f1d527e]"),
                         ["83080b3f11", "abcdef1"])
        self.assertEqual(dev_queue.landed_of("CLOSED 2026-09-11 AS DONE; landed 83080b3f11"), [])
        self.assertEqual(dev_queue.landed_of("LANDED 20261030T034957Z; MERGED 83080B3F11"), [])

    def test_one_git_log_for_every_heading_sha(self):
        logs = [a for a in self.started if a[1:3] == ["log", "--no-walk"]]
        self.assertEqual(len(logs), 1, logs)
        for short in (self.shas["landed"][:10], self.shas["closed"][:10], self.shas["side"][:10], MISSING):
            self.assertIn(short, logs[0])
        self.assertEqual(len([a for a in self.started if a[1:3] == ["rev-list", "HEAD"]]), 1)
        self.assertEqual(sorted(set(a[0] for a in self.started)), ["git"])

    def test_no_heading_sha_no_git_call(self):
        ships, warnings = dev_queue.heading_ships(self.root, {"PF-1": {"landed": []}})
        self.assertEqual((ships, warnings), ({}, []))


if __name__ == "__main__":
    unittest.main()
