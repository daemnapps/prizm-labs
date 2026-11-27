#!/usr/bin/env python3
"""PF-18h (hidden cards): a card can be taken off the Dev-queue board by one setting, HIDDEN_CARDS, starting with
DB-7 (arm tools off).

    python3 components/page-features/test_pf18h_hidden_cards.py

    (a) a fixture with DB-7 (arm tools off) and DB-8 (other card) shipped after the cutoff: DB-7 is absent from `cards`
        and so from every column, DB-8 stays in Shipped, `hidden_cards` is 1 (a count, never the list)
    (b) the decisions naming DB-7 (arm tools off) are still listed, the same list as with HIDDEN_CARDS = (); Shipped
        without a card is the same list too, and a commit naming DB-7 still counts as carded
    (c) `mark DB-7 understood` is refused ("not on the board") and writes nothing, in Python and on the command line;
        DB-8 still takes a mark
    (k) the card's kill: HIDDEN_CARDS holds at most 5 ids (past that, a family rule asked of developer)
    (p) the page in node: no DB-7 tile in any column, the About line says "1 card hidden by setting" and names no id,
        the decision naming DB-7 is drawn in the stream

The fixture lives in this file (no .md fixtures under components/); the repo helpers are test_pf18_dev_queue's and
the review-module copy list test_pf18b_review_marks's. Stdlib only, Python 3.9. Writes only in temp folders; no
network: the review key is removed from the environment, so the module's git door is the one used.
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
import test_pf18_dev_queue as pf18  # noqa: E402  Repo, write, request, the page harness
import test_pf18b_review_marks as pf18b  # noqa: E402  what a workspace needs to run the review module

REAL = pf18.REAL
TPL = pf18.TPL
NOW = "2026-10-29T12:00:00Z"
COLUMNS = ("up-next", "in-progress", "shipped", "flagged", "reviewed")

DECK = """# page-features cards (fixture)

### PF-40 — page card: shipped this week (carded 2026-10-28 by the lead; owner email_lead (page-features))
"""
DECK_DB = """# dashboard cards (fixture)

### DB-7 — arm tools off: the hidden card (carded 2026-10-28 by the lead; owner developer)
### DB-8 — other card: same family, not hidden (carded 2026-10-28 by the lead; owner developer)
"""
DECISIONS = """# The org — decision log

- 2026-10-29 — ARM TOOLS OFF: DB-7 (arm tools off) merged. developer, typed to the lead: "merge it".
  KILL: a tool needs arming → revisit.

- 2026-10-25 — EARLIER WORD ON DB-7 (arm tools off), BEFORE THE CUTOFF. developer, typed to the lead.
  KILL: none.
"""


def workspace():
    root = os.path.realpath(tempfile.mkdtemp(prefix="pf18h-"))
    os.makedirs(os.path.join(root, "brands"))
    for pid, email in pf18.EMAILS.items():
        pf18.write(root, "team/people/%s/identity.json" % pid,
                   json.dumps({"person": pid, "emails": [{"address": email}]}))
    pf18.write(root, "team/id-tags.json", json.dumps({"_readme": "fixture", "DB-7": "arm tools off"}))
    pf18.write(root, "new-workflow-design/builds/page-features/task-cards.md", DECK)
    pf18.write(root, "new-workflow-design/builds/dashboard/task-cards.md", DECK_DB)
    pf18.write(root, "the-org/decision-log.md", DECISIONS)
    git = pf18.Repo(root)
    git.commit("lead: card the decks", "2026-10-28T00:00:00Z")
    git.merge("merge PF-40 (page card) — developer typed to the lead: \"merge it\"", "2026-10-28T09:00:00Z")
    git.merge("merge DB-7 (arm tools off) — developer typed to the lead: \"merge it\"", "2026-10-29T02:00:00Z")
    git.merge("merge DB-8 (other card) — developer typed to the lead: \"merge it\"", "2026-10-29T03:00:00Z")
    git.commit("a note on DB-7 after the merge", "2026-10-29T04:00:00Z", "designer")
    git.commit("gdrive-creator: retry once more", "2026-10-29T05:00:00Z", "developer",
               {"components/gdrive-creator/a.txt": "1"})
    for rel in pf18b.COPY:
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copy(os.path.join(REAL, rel), os.path.join(root, rel))
    shutil.copytree(os.path.join(REAL, "components/run-kit/run_kit"), os.path.join(root, "components/run-kit/run_kit"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    return root


def env():
    return dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)


def unhidden(root):
    saved = dev_queue.HIDDEN_CARDS
    dev_queue.HIDDEN_CARDS = ()
    try:
        return dev_queue.build(root, now=NOW)
    finally:
        dev_queue.HIDDEN_CARDS = saved


class Board(unittest.TestCase):
    """(a) (b) (c) (k)"""

    def setUp(self):
        self.root = workspace()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.rv = dev_queue.review_module()

    def board(self):
        return dev_queue.build(self.root, now=NOW)

    def test_a_the_hidden_card_is_off_the_board(self):
        self.assertEqual(dev_queue.HIDDEN_CARDS, ("DB-7",), "the setting starts with DB-7 (arm tools off)")
        doc = self.board()
        c = pf18.by_id(doc)
        self.assertNotIn("DB-7", c, "absent from `cards`")
        for col in COLUMNS:
            self.assertNotIn("DB-7", [x["id"] for x in doc["cards"] if x["column"] == col], col)
        self.assertEqual(c["DB-8"]["column"], "shipped", "the same family's other card stays")
        self.assertEqual(c["PF-40"]["column"], "shipped")
        self.assertEqual(doc["hidden_cards"], 1, "the count only")
        self.assertNotIn("DB-7", json.dumps([doc["hidden_cards"], doc["sources"]]), "never the list")
        before = pf18.by_id(unhidden(self.root))
        self.assertEqual(before["DB-7"]["column"], "shipped", "without the setting the fixture ships it")
        self.assertEqual(sorted(before), sorted(list(c) + ["DB-7"]), "the setting removes DB-7 and nothing else")

    def test_b_decisions_and_shipped_without_a_card_still_read_it(self):
        doc, plain = self.board(), unhidden(self.root)
        named = [d for d in doc["decisions"] if any(x["id"] == "DB-7" for x in d["cards"])]
        self.assertEqual([d["date"] for d in named], ["2026-10-29", "2026-10-25"], "a decision naming it still listed")
        self.assertEqual(named[0]["cards"][0]["tag"], "arm tools off")
        self.assertTrue(named[0]["in_stream"])
        self.assertEqual(doc["decisions"], plain["decisions"], "Decisions are the same as without the setting")
        self.assertEqual(doc["direct_work"], plain["direct_work"], "Shipped without a card is the same too")
        self.assertEqual([w["what"] for w in doc["direct_work"]], ["gdrive-creator: retry once more"],
                         "a commit naming DB-7 still counts as carded")

    def test_c_mark_refuses_the_hidden_card(self):
        e = env()
        with self.assertRaises(self.rv.Refused) as cm:
            dev_queue.mark(self.root, "DB-7", "understood", "email_lead", env=e, commit=False, now="2026-10-29T06:00:00Z")
        self.assertIn("not on the board", str(cm.exception))
        self.assertEqual(self.rv.read_records(root=self.root), [], "the refusal writes nothing")
        out = dev_queue.mark(self.root, "DB-8", "understood", "email_lead", env=e, commit=False, now="2026-10-29T06:00:01Z")
        self.assertEqual(out["record"]["item"], "RQ-dev-queue-DB-8")

    def test_c_mark_through_the_command_line(self):
        p = subprocess.run([sys.executable, os.path.join(self.root, "components/page-features/dev_queue.py"),
                            "mark", "DB-7", "understood", "--by", "email_lead", "--root", self.root, "--no-commit"],
                           capture_output=True, text=True, env=env(), timeout=120)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("REFUSED: DB-7 is hidden by setting", p.stderr)
        self.assertIn("not on the board", p.stderr)
        self.assertEqual(self.rv.read_records(root=self.root), [])

    def test_k_the_list_stays_short(self):
        self.assertLessEqual(len(dev_queue.HIDDEN_CARDS), 5, "the card's kill: past 5 ids, replace the list with a "
                                                             "family rule, asked of developer")


PAGE_TAIL = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const words = e => e.textContent.replace(/\s+/g, " ").trim();
  const out = {asked: asked, errors: errors, columns: {}, words: {}};
  ["issue-queue", "up-next", "in-progress", "shipped", "flagged", "reviewed"].forEach(c => {
    out.columns[c] = tiles(c);
    out.words[c] = words(g("col-" + c));
  });
  out.about = words(g("about"));
  out.decisions = find(g("decisions"), e => e.classList.contains("decision")).map(words);
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


class Page(unittest.TestCase):
    """(p) the template's own script on the fixture's data, in node (skipped where there is no node)."""

    def test_p_the_page_shows_no_hidden_tile_and_counts_it(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        root = workspace()
        self.addCleanup(shutil.rmtree, root, True)
        pf18.write(root, "data.json", json.dumps(dev_queue.build(root, now=NOW)))
        pf18.write(root, "harness.js", pf18.PAGE_HARNESS[:pf18.PAGE_HARNESS.index("(async () => {")] + PAGE_TAIL)
        p = subprocess.run([node, os.path.join(root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        for col, ids in got["columns"].items():
            self.assertNotIn("DB-7", ids, col)
            self.assertNotIn("DB-7", got["words"][col], col)
        # narrowed by DQ-6 (built by label)'s order rule: Shipped is a queue, oldest merge first
        self.assertEqual(got["columns"]["shipped"], ["PF-40", "DB-8"])
        self.assertIn("1 card hidden by setting", got["about"])
        self.assertNotIn("DB-7", got["about"], "the count only, no list")
        self.assertEqual(len(got["decisions"]), 1, "the one decision since the cutoff")
        self.assertIn("DB-7 (arm tools off)", got["decisions"][0])


if __name__ == "__main__":
    unittest.main()
