#!/usr/bin/env python3
"""PF-18f (earlier PF review): the earlier PF cards go to Shipped for review like any other; the board says nothing
about the cutoff date.

    python3 components/page-features/test_pf18f_earlier_pf.py

    (a) a fixture with a PF card shipped before the cutoff, one shipped after, and another family's card shipped
        before it (with a request record after it, so only this card's rule keeps it off): both PF cards in Shipped
        with an unmarked review line, the other card absent
    (b) Reviewed counts 0 until both reviewers mark Understood on the early PF card, then 1; `mark` on the early PF
        card writes a record, on the other family's early card it refuses and writes nothing
    (c) the kill is one setting: EARLY_REVIEW_FAMILIES = () takes the early PF card off the board again
    (p) the page in node: the early PF card's tile is in Shipped, Reviewed holds and counts only the card both
        reviewers understood, and the visible text of the columns, tiles, panel and stats has no "before" and no
        cutoff date; the template no longer carries the fold, its panel label or the "shipped before" stat

The fixture lives in this file (no .md fixtures under components/); the repo helpers are test_pf18_dev_queue's and
the review-module copy list test_pf18b_review_marks's. Stdlib only, Python 3.9. Writes only in temp folders; no
network: the review key is removed from the environment, so the module's git door is the one used.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  Repo, write, request, the page harness
import test_pf18b_review_marks as pf18b  # noqa: E402  what a workspace needs to run the review module

REAL = pf18.REAL
TPL = pf18.TPL
NOW = "2026-10-29T05:00:00Z"
CUTOFF_DAY = "27 Oct"                                  # dev_queue.CUTOFF as the page would print it

DECK = """# page-features cards (fixture)

### PF-30 — early card: shipped in the first PF week (carded 2026-10-20 by the lead; owner email_lead (page-features))
### PF-31 — late card: shipped this week (carded 2026-10-28 by the lead; owner email_lead (page-features))
"""
DECK_QX = """# another family (fixture)

### QX-1 — other early card: shipped in the first week too (carded 2026-10-20; owner developer)
"""


def workspace():
    root = os.path.realpath(tempfile.mkdtemp(prefix="pf18f-"))
    os.makedirs(os.path.join(root, "brands"))
    for pid, email in pf18.EMAILS.items():
        pf18.write(root, "team/people/%s/identity.json" % pid,
                   json.dumps({"person": pid, "emails": [{"address": email}]}))
    pf18.write(root, "team/id-tags.json", json.dumps({"_readme": "fixture"}))
    pf18.write(root, "new-workflow-design/builds/page-features/task-cards.md", DECK)
    pf18.write(root, "new-workflow-design/builds/other/task-cards.md", DECK_QX)
    pf18.request(root, "2026-10-28T06:00:00Z", "developer", "impl-qx1-again", {"action": "implement", "cards": ["QX-1"]})
    git = pf18.Repo(root)
    git.commit("lead: card the decks", "2026-10-20T00:00:00Z")
    git.merge("merge PF-30 (early card) — developer typed to the lead: \"merge it\"", "2026-10-21T09:00:00Z")
    git.merge("merge QX-1 (other early card) — developer typed to the lead: \"merge it\"", "2026-10-22T09:00:00Z")
    git.merge("merge PF-31 (late card) — developer typed to the lead: \"merge it\"", "2026-10-28T09:00:00Z")
    for rel in pf18b.COPY:
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copy(os.path.join(REAL, rel), os.path.join(root, rel))
    shutil.copytree(os.path.join(REAL, "components/run-kit/run_kit"), os.path.join(root, "components/run-kit/run_kit"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    return root


def env():
    return dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)


def reviewed(doc):
    return [c["id"] for c in doc["cards"] if c["column"] == "reviewed"]


class Board(unittest.TestCase):
    """(a) (b) (c)"""

    def setUp(self):
        self.root = workspace()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.rv = dev_queue.review_module()

    def board(self):
        return dev_queue.build(self.root, now=NOW)

    def test_a_early_pf_cards_ship_for_review_and_other_families_stay_off(self):
        doc = self.board()
        c = pf18.by_id(doc)
        self.assertEqual(doc["cutoff"], "2026-10-27T00:00:00Z")
        self.assertLess(c["PF-30"]["merged"]["at"], doc["cutoff"])
        self.assertGreater(c["PF-31"]["merged"]["at"], doc["cutoff"])
        for cid in ("PF-30", "PF-31"):
            self.assertEqual(c[cid]["column"], "shipped", cid)
            self.assertEqual(c[cid]["review"], [{"person": "email_lead", "understood": None},
                                                {"person": "designer", "understood": None}], cid)
            self.assertEqual(c[cid]["marks"], [], "%s takes marks" % cid)
        self.assertNotIn("QX-1", c, "another family's card shipped before the cutoff is left off the board, even with "
                                    "a request record after it")
        self.assertEqual(doc["early_review_families"], ["PF", "DQ"])   # DQ (Dev-queue) added by PF-18m (open issues only)

    def test_b_reviewed_counts_only_both_understood_and_mark_scope(self):
        e = env()
        self.assertEqual(reviewed(self.board()), [], "Reviewed counts 0 with no marks")
        out = dev_queue.mark(self.root, "PF-30", "understood", "email_lead", env=e, commit=False, now="2026-10-29T01:00:00Z")
        self.assertEqual((out["record"]["item"], out["record"]["reviewer"]), ("RQ-dev-queue-PF-30", "email_lead"))
        self.assertEqual(len(self.rv.read_records(root=self.root)), 1, "the early PF card's mark is one record")
        doc = self.board()
        self.assertEqual(reviewed(doc), [], "one reviewer's Understood is not Reviewed")
        self.assertEqual(pf18.by_id(doc)["PF-30"]["column"], "shipped")
        dev_queue.mark(self.root, "PF-30", "understood", "designer", env=e, commit=False, now="2026-10-29T01:00:01Z")
        doc = self.board()
        self.assertEqual(reviewed(doc), ["PF-30"], "both reviewers Understood: Reviewed counts 1")
        self.assertEqual(pf18.by_id(doc)["PF-31"]["column"], "shipped")
        n = len(self.rv.read_records(root=self.root))
        with self.assertRaises(self.rv.Refused) as cm:
            dev_queue.mark(self.root, "QX-1", "understood", "email_lead", env=e, commit=False, now="2026-10-29T01:00:02Z")
        self.assertIn("QX-1 is not a card shipped since 2026-10-27T00:00:00Z", str(cm.exception))
        self.assertEqual(len(self.rv.read_records(root=self.root)), n, "the refusal writes nothing")

    def test_b_mark_through_the_command_line(self):
        def run(card):
            return subprocess.run([sys.executable, os.path.join(self.root, "components/page-features/dev_queue.py"),
                                   "mark", card, "question", "--by", "email_lead", "--root", self.root, "--no-commit"],
                                  capture_output=True, text=True, env=env(), timeout=120)
        p = run("PF-30")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("PF-30 marked question by email_lead", p.stdout)
        p = run("QX-1")
        self.assertEqual(p.returncode, 2)
        self.assertIn("REFUSED: QX-1 is not a card shipped since", p.stderr)
        self.assertEqual([r["item"] for r in self.rv.read_records(root=self.root)], ["RQ-dev-queue-PF-30"])
        self.assertEqual(pf18.by_id(self.board())["PF-30"]["column"], "flagged", "an open Question flags it")

    def test_c_the_kill_is_one_setting(self):
        saved = dev_queue.EARLY_REVIEW_FAMILIES
        dev_queue.EARLY_REVIEW_FAMILIES = ()
        try:
            c = pf18.by_id(self.board())
        finally:
            dev_queue.EARLY_REVIEW_FAMILIES = saved
        self.assertNotIn("PF-30", c, "the early PF card leaves Shipped again")
        self.assertEqual(c["PF-31"]["column"], "shipped", "current work stays")


PAGE_TAIL = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const words = e => e.textContent.replace(/\s+/g, " ").trim();
  const out = {asked: asked, errors: errors, columns: {}, words: {}, counts: {}};
  ["up-next", "in-progress", "shipped", "flagged", "reviewed"].forEach(c => {
    out.columns[c] = tiles(c);
    out.words[c] = words(g("col-" + c));
    out.counts[c] = words(find(g("col-" + c), e => e.classList.contains("column-count"))[0]);
  });
  out.summary = words(g("summary"));
  const buttons = every().filter(e => e.tagName === "BUTTON");
  buttons.find(b => b.className === "tile-open" && b.getAttribute("aria-label").indexOf("Open PF-30 (") === 0).fire("click");
  out.panel = words(g("panel-content"));
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


class Page(unittest.TestCase):
    """(p) the template's own script on the fixture's data, in node (skipped where there is no node)."""

    def draw(self, root, node):
        pf18.write(root, "data.json", json.dumps(dev_queue.build(root, now=NOW)))
        pf18.write(root, "harness.js", pf18.PAGE_HARNESS[:pf18.PAGE_HARNESS.index("(async () => {")] + PAGE_TAIL)
        p = subprocess.run([node, os.path.join(root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        return got

    def visible(self, got):
        return " ".join([got["summary"], got["panel"]] + list(got["words"].values()))

    def test_p_the_page_says_nothing_about_the_cutoff(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        root = workspace()
        self.addCleanup(shutil.rmtree, root, True)
        got = self.draw(root, node)
        self.assertEqual(got["asked"], [["/data/dev-queue", "GET"], ["/stamp/dev-queue", "GET"]])
        # narrowed by DQ-6 (built by label)'s order rule: Shipped is a queue, oldest merge first
        self.assertEqual(got["columns"]["shipped"], ["PF-30", "PF-31"], "both PF cards, oldest first")
        self.assertEqual((got["columns"]["reviewed"], got["counts"]["reviewed"]), ([], "0"))
        self.assertIn("2 shipped", got["summary"])
        self.assertNotIn("QX-1", self.visible(got))
        text = self.visible(got)
        self.assertNotRegex(text, r"(?i)\bbefore\b", "no column, tile, panel or stat says 'before'")
        self.assertNotIn(CUTOFF_DAY, text, "no column, tile, panel or stat names the cutoff date")
        self.assertNotIn("since", got["summary"])
        self.assertIn("PF-30 (early card)", got["panel"])
        self.assertIn("Shipped", got["panel"])

        e = env()
        dev_queue.mark(root, "PF-30", "understood", "email_lead", env=e, commit=False, now="2026-10-29T01:00:00Z")
        dev_queue.mark(root, "PF-30", "understood", "designer", env=e, commit=False, now="2026-10-29T01:00:01Z")
        got = self.draw(root, node)
        self.assertEqual((got["columns"]["reviewed"], got["counts"]["reviewed"]), (["PF-30"], "1"))
        self.assertEqual(got["columns"]["shipped"], ["PF-31"])
        self.assertIn("Reviewed", got["panel"])
        text = self.visible(got)
        self.assertNotRegex(text, r"(?i)\bbefore\b")
        self.assertNotIn(CUTOFF_DAY, text)

    def test_p_the_template_has_no_fold(self):
        text = pf18.read(os.path.join(REAL, TPL, "dev-queue.html"))
        code = re.search(r'<script id="dev-queue-page">([\s\S]*?)</script>', text).group(1)
        for gone in ('" shipped before " + day(D.cutoff)', '"Shipped before " + day(D.cutoff)', '"shipped before"]',
                     '"shipped since " + day(', 'id: "older"'):
            self.assertNotIn(gone, code, gone)
        self.assertIn('[shipped, "shipped"]', code, "the stat reads \"shipped\"")


if __name__ == "__main__":
    unittest.main()
