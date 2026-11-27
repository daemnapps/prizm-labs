#!/usr/bin/env python3
"""PF-18m (open issues only): the Issue queue draws only open items, a card closed with no build leaves the board, the
DQ (Dev-queue) family and its display alias, and the assigner rule.

    python3 components/page-features/test_pf18m_open_issues.py

    (a) the page: a fixture with one issue in each state (Raised, Discussing, Carded, Fixed, Closed, Won't do) and one
        open and one done follow-up → the Issue queue draws exactly the Raised and Discussing issues (narrowed by
        DQ-5 (human acts): follow-ups are acts in Up next), no closed group, and its sub-label drops "Won't do"; the data's issue list keeps every item with its state
    (b) a card headed "CLOSED — NO BUILD" is absent from every column and stat, present in `closed_no_build`, and
        `mark` and `assign` refuse it with nothing written
    (c) a PF-18x card's family is DQ (its id unchanged, its marks on RQ-dev-queue-<real id>), a PF-19 card's stays PF,
        a DQ-1 fixture card shows; the page's Family filter offers DQ
    (d) the assigner rule: a card built by email_lead, assigned by developer → reviewers ["designer"]; assigned by designer →
        ["developer"]; a self-assignment changes nothing; Understood by the sole reviewer → Reviewed; developer's "Your review"
        omits it
    (e) at this tree: PF-22 (spend route guard) and DQ-1 (closed issues link) are off the board, in closed_no_build;
        every PF-18* card is DQ; DQ-2 (file handle closed) and DQ-3 (note mark) show

Fixtures are test_pf18_dev_queue.py's repo and test_pf18b_review_marks.py's workspace (test files), with the extra deck
lines kept here; no .md fixtures under components/. Stdlib only, Python 3.9. Writes only in temp folders; no network:
the review key is removed from every environment here.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dev_queue  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo and the page harness
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture workspace with the real commands

REAL = pf18b.REAL
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
ENV = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)
DECK_MORE = (
    "### PF-18x — fixture: a dev-queue follow-up (carded 2026-10-28; APPROVED)\n"
    "### PF-19 — fixture: not a dev-queue card (carded 2026-10-28; APPROVED)\n"
    "### PF-40 — fixture: closed (carded 2026-10-28; CLOSED — NO BUILD: developer typed to the lead: \"yes, close it\")\n")
DECK_DQ = ("# dev-queue cards (fixture)\n\n"
           "### DQ-1 — fixture: the first dev-queue card (carded 2026-10-30; APPROVED)\n")


def at(n):
    return "2026-10-29T03:00:%02dZ" % n


def issue(iid, kind, state, title, n, **kw):
    """One entry of the data's `issues`, in fold_dev's shape."""
    e = {"id": iid, "alias": None, "kind": kind, "status": "proposed", "state": state, "title": title, "detail": "",
         "quote": "q " + iid, "said_by": "developer", "session": "s1", "by": "developer",
         "created": "2026-10-29T01:00:%02dZ" % n, "assignees": [], "parent": None, "on_card": None,
         "carded_as": None, "reason": None, "fixed_at": None, "fixes": [], "context": [], "notes": [], "history": [],
         "follow_ups": []}
    e.update(kw)
    return e


ISSUES = [issue("I-raised", "issue", "raised", "a raised issue", 1),
          issue("I-discussing", "issue", "discussing", "a discussing issue", 2, assignees=["email_lead"]),
          issue("I-carded", "issue", "carded", "a carded issue", 3, carded_as="PF-5", on_card="PF-5"),
          issue("I-fixed", "issue", "fixed", "a fixed issue", 4, fixed_at={"sha": "abcdef1234", "subject": "x"}),
          issue("I-closed", "issue", "closed", "a closed issue", 5),
          issue("I-wont", "issue", "wont-do", "a won't do issue", 6, reason="leave it"),
          issue("F-open", "follow-up", "raised", "an open follow-up", 7, assignees=["designer"]),
          issue("F-done", "follow-up", "done", "a done follow-up", 8, assignees=["developer"])]

# The page harness's DOM, then: each column's tiles, the Issue queue's tiles, groups, sub-label and DETAILS; the
# shipped column's tiles by group (the h4 above each list, "rest" for the fold); the Family filter's options
PAGE_RUN = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const words = e => e.textContent.replace(/\s+/g, " ").trim(), col = g("col-issue-queue");
  const out = {errors: errors, columns: {}};
  ["issue-queue", "up-next", "in-progress", "shipped", "flagged", "reviewed"].forEach(c => { out.columns[c] = tiles(c); });
  out.issue_tiles = find(col, e => e.getAttribute("data-issue")).map(e => e.getAttribute("data-issue"));
  out.groups = find(col, e => e.classList.contains("queue-group")).map(words);
  out.sub = words(find(col, e => e.classList.contains("column-sub"))[0]);
  out.details = find(col, e => e.tagName === "DETAILS").length;
  out.count = words(find(col, e => e.classList.contains("column-count"))[0]);
  out.summary = words(g("summary"));
  out.card_count = g("card-count").textContent;
  out.all_words = words(top);
  out.shipped = {};
  find(g("col-shipped"), e => e.tagName === "UL").forEach(ul => {
    let grp = "";
    if (ul.parentNode && ul.parentNode.tagName === "DETAILS") grp = "rest";
    else { const sib = ul.parentNode.children; for (let i = sib.indexOf(ul) - 1; i >= 0; i--) {
      if (sib[i].tagName === "H4") { grp = words(sib[i]).split(" · ")[0]; break; } } }
    out.shipped[grp] = (out.shipped[grp] || []).concat(find(ul, e => e.getAttribute("data-tile")).map(e => e.getAttribute("data-tile")));
  });
  out.families = find(g("family-options"), e => e.tagName === "INPUT").map(e => e.getAttribute("value"));
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


def draw(test, root, doc):
    """The template's own script on `doc` in node; skips where there is no node."""
    node = shutil.which("node")
    if not node:
        test.skipTest("no node on this machine")
    pf18.write(root, "pf18m-data.json", json.dumps(doc))
    pf18.write(root, "pf18m-harness.js", pf18.PAGE_HARNESS.split("(async () => {")[0] + PAGE_RUN)
    p = subprocess.run([node, os.path.join(root, "pf18m-harness.js"), PAGE, os.path.join(root, "pf18m-data.json")],
                       capture_output=True, text=True, timeout=60)
    test.assertEqual(p.returncode, 0, p.stderr)
    got = json.loads(p.stdout.strip().splitlines()[-1])
    test.assertEqual(got["errors"], [])
    return got


class Board(unittest.TestCase):
    """(a)(b)(c) on one fixture workspace with the extra deck lines."""

    @classmethod
    def setUpClass(cls):
        cls.root = pf18b.workspace()
        deck = os.path.join(cls.root, "new-workflow-design/builds/page-features/task-cards.md")
        with open(deck, "a", encoding="utf-8") as fh:
            fh.write(DECK_MORE)
        pf18.write(cls.root, "new-workflow-design/builds/dev-queue/task-cards.md", DECK_DQ)
        pf18.Repo(cls.root).commit("lead: card PF-18x, PF-19, PF-40 and DQ-1 (fixture cards)", "2026-10-28T16:30:00Z")
        cls.doc = dev_queue.build(cls.root, now=pf18.NOW)
        cls.cards = pf18.by_id(cls.doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_a_the_queue_draws_only_open_items(self):
        doc = dict(self.doc, issues=ISSUES)
        got = draw(self, self.root, doc)
        # narrowed by DQ-5 (human acts): the queue holds issues only; an open follow-up is an act in Up next
        self.assertEqual(sorted(got["issue_tiles"]), ["I-discussing", "I-raised"],
                         "exactly the Raised and Discussing issues")
        self.assertEqual(got["groups"], ["Discussing · 1", "Raised · 1"])
        self.assertEqual(got["details"], 0, "no collapsed closed group")
        self.assertEqual(got["count"], "2")
        self.assertEqual(got["sub"], "Raised · Discussing", "the sub-label drops Won't do")
        self.assertTrue(got["summary"].startswith("2 open in the issue queue"), got["summary"])
        self.assertEqual([(e["id"], e["state"]) for e in doc["issues"]],
                         [(e["id"], e["state"]) for e in ISSUES], "the records are untouched")

    def test_b_a_closed_no_build_card_is_off_the_board(self):
        self.assertNotIn("PF-40", self.cards)
        self.assertEqual(self.doc["closed_no_build"], ["PF-40"])
        self.assertEqual(self.doc["hidden_cards"], 0, "not counted as hidden")
        got = draw(self, self.root, self.doc)
        for col, ids in got["columns"].items():
            self.assertNotIn("PF-40", ids, col)
        self.assertNotIn("PF-40", got["all_words"], "no tile, no stat, no word")
        self.assertTrue(got["card_count"].endswith(" of %d cards" % len(self.doc["cards"])), got["card_count"])
        rv = dev_queue.review_module()
        before = len(rv.read_records(root=self.root))
        with self.assertRaises(rv.Refused) as cm:
            dev_queue.mark(self.root, "PF-40", "question", "email_lead", env=ENV, commit=False, now=at(1))
        self.assertIn("closed with no build", str(cm.exception))
        with self.assertRaises(rv.Refused):
            dev_queue.assign(self.root, "PF-40", "email_lead", "developer", env=ENV, commit=False, now=at(2))
        self.assertEqual(len(rv.read_records(root=self.root)), before, "nothing written")
        self.assertTrue(dev_queue.parse_heading("### PF-41 — t (carded 2026-10-28; CLOSED — NO BUILD)", {}, {})
                        ["closed_no_build"])
        for near in ("closed — no build", "CLOSED - NO BUILD", "CLOSED at abc1234"):
            self.assertFalse(dev_queue.parse_heading("### PF-41 — t (carded 2026-10-28; %s)" % near, {}, {})
                             ["closed_no_build"], "exact words only: %s" % near)

    def test_c_the_dq_family_and_alias(self):
        c = self.cards
        self.assertEqual((c["PF-18x"]["id"], c["PF-18x"]["family"]), ("PF-18x", "DQ"))
        self.assertEqual(c["PF-19"]["family"], "PF")
        self.assertIn("DQ-1", c, "a DQ-1 card shows")
        self.assertEqual(c["DQ-1"]["family"], "DQ")
        self.assertEqual((dev_queue.shown_family("PF-18"), dev_queue.shown_family("PF-180"),
                          dev_queue.shown_family("PF-1")), ("DQ", "PF", "PF"))
        self.assertEqual(self.doc["baseline_families"], ["PF", "DQ"])
        self.assertEqual(self.doc["early_review_families"], ["PF", "DQ"])
        got = draw(self, self.root, self.doc)
        self.assertIn("DQ", got["families"], "the Family filter offers DQ")
        self.assertIn("PF-18x", got["columns"]["up-next"])

    def test_c_marks_read_the_real_id(self):
        root = pf18b.workspace()
        self.addCleanup(shutil.rmtree, root, True)
        with open(os.path.join(root, "new-workflow-design/builds/page-features/task-cards.md"), "a",
                  encoding="utf-8") as fh:
            fh.write(DECK_MORE)
        out = dev_queue.mark(root, "PF-18x", "question", "email_lead", env=ENV, commit=False, now=at(3))
        self.assertEqual(out["record"]["item"], "RQ-dev-queue-PF-18x")
        c = pf18.by_id(dev_queue.build(root, now=pf18.NOW))["PF-18x"]
        self.assertEqual((c["column"], c["family"]), ("flagged", "DQ"))


class Assigner(unittest.TestCase):
    """(d) PF-3 is built by email_lead and shipped in the fixture."""

    def setUp(self):
        self.root = pf18b.workspace()
        self.addCleanup(shutil.rmtree, self.root, True)

    def board(self):
        return dev_queue.build(self.root, now=pf18.NOW)

    def assign(self, card, person, by, n):
        dev_queue.assign(self.root, card, person, by, env=ENV, commit=False, now=at(n))

    def test_d_the_assigner_is_no_reviewer(self):
        self.assertEqual(dev_queue.reviewers_of("email_lead", "developer"), ["designer"])
        self.assertEqual(dev_queue.reviewers_of("email_lead", "email_lead"), ["developer", "designer"], "self-assignment")
        self.assertEqual(dev_queue.reviewers_of(None, "developer"), list(dev_queue.REVIEWERS))
        c = pf18.by_id(self.board())["PF-3"]
        self.assertEqual((c["built_by"], c["assignee"], c["reviewers"]), ("email_lead", None, ["developer", "designer"]),
                         "unassigned: PF-18j (people data)'s rule")
        self.assign("PF-3", "email_lead", "developer", 1)
        c = pf18.by_id(self.board())["PF-3"]
        self.assertEqual(c["reviewers"], ["designer"], "built by email_lead, assigned by developer")
        self.assertEqual(c["review"], [{"person": "designer", "understood": None}])
        self.assign("PF-3", "email_lead", "designer", 2)
        self.assertEqual(pf18.by_id(self.board())["PF-3"]["reviewers"], ["developer"], "assigned by designer")
        self.assign("PF-3", "email_lead", "email_lead", 3)
        self.assertEqual(pf18.by_id(self.board())["PF-3"]["reviewers"], ["developer", "designer"],
                         "a self-assignment changes nothing")
        self.assign("PF-3", "none", "developer", 4)
        self.assertEqual(pf18.by_id(self.board())["PF-3"]["reviewers"], ["developer", "designer"], "unassigned again")

    def test_d_the_sole_reviewer_reviews_and_dayus_view_omits_it(self):
        got = draw(self, self.root, dict(self.board(), viewer="developer"))
        self.assertIn("PF-3", got["shipped"].get("Your review", []), "the control: unassigned, it waits on developer")
        self.assign("PF-3", "email_lead", "developer", 1)
        doc = self.board()
        self.assertEqual(pf18.by_id(doc)["PF-3"]["column"], "shipped")
        got = draw(self, self.root, dict(doc, viewer="developer"))
        self.assertNotIn("PF-3", got["shipped"].get("Your review", []), "developer assigned it: not his to review")
        self.assertIn("PF-3", got["columns"]["shipped"])
        dev_queue.mark(self.root, "PF-3", "understood", "designer", env=ENV, commit=False, now=at(2))
        c = pf18.by_id(self.board())["PF-3"]
        self.assertEqual(c["column"], "reviewed", "Understood by the sole reviewer")
        self.assertEqual([(r["person"], r["understood"]) for r in c["review"]], [("designer", True)])


class AtThisTree(unittest.TestCase):
    """(e) this repo, read-only."""

    def test_e_real_cases(self):
        doc = dev_queue.build(REAL)
        c = pf18.by_id(doc)
        for cid in ("PF-22", "DQ-1"):
            self.assertNotIn(cid, c, cid)
            self.assertIn(cid, doc["closed_no_build"], cid)
        for cid in ("DQ-2", "DQ-3"):
            self.assertIn(cid, c, cid)
            self.assertEqual(c[cid]["family"], "DQ")
        pf18s = [k for k in c if dev_queue.FAMILY_ALIASES[0][0].match(k)]
        self.assertIn("PF-18", pf18s)
        self.assertEqual(set(c[k]["family"] for k in pf18s), {"DQ"})


if __name__ == "__main__":
    unittest.main()
