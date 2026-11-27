#!/usr/bin/env python3
"""PF-18l (fixed move): an issue fixed by a commit on main with no card leaves the Issue queue through `fixed`.

    python3 components/page-features/test_pf18l_fixed_move.py

    (a) `fixed <issue> <sha>` with a sha on HEAD writes two records (a comment "Fixed at commit <full sha>", then
        status done with the note "fixed at <short sha>: <subject>"; the tasks kind allows no commit link type) and
        the issue folds to `fixed` with fixed_at {sha, subject, at} from git
    (b) a sha not in the repo refuses, and so does a commit that is not on HEAD; nothing written
    (c) a follow-up refuses (`done` is its move); nothing written
    (d) the page data: the template's queue lists neither a fixed nor a closed issue (node; skipped without it), and
        the fold keeps `closed` for an issue done with no card and no fix

Fixtures are built in temp folders from test_pf18_dev_queue's fixture repo; no .md fixtures under components/.
Stdlib only, Python 3.9. No network; no real task record is written.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dev_issues  # noqa: E402
import dev_queue  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the PF-18 fixture repo and page harness, reused

REAL = os.path.dirname(os.path.dirname(HERE))
TASKS = "platform/data/records/tasks/"
TPL = "platform/views/viewers/_templates/dev-queue.html"
SUBJECT = "skills: /page-draft and /page-change hand people the page URL"
FIX_AT = "2026-10-29T06:00:00Z"
ITEMS = [{"kind": "issue", "ref": "1", "title": "The draft skills hand people the FILE path", "quote": "file path",
          "session": "811f93"},
         {"kind": "issue", "ref": "2", "title": "An issue someone ticked done by hand", "quote": "done?",
          "session": "811f93"},
         {"kind": "issue", "ref": "3", "title": "An issue still raised", "quote": "still open", "session": "811f93"},
         {"kind": "follow-up", "ref": "4", "title": "Tell email_lead the skill changed", "quote": "tell her",
          "session": "811f93", "person": "email_lead"}]


def run(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = dev_issues.main(list(argv) + ["--root", root], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def listing(root):
    d = os.path.join(root, TASKS)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def shown(root):
    items, _n = dev_queue.dev_items(root)
    return dict((e["title"], e) for e in items)


class Fixed(unittest.TestCase):

    def setUp(self):
        self.root = pf18.fixture()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.repo = pf18.Repo(self.root)
        self.sha = self.repo.commit(SUBJECT, FIX_AT, "developer", {"skills/page-draft.txt": "the URL"})
        pf18.write(self.root, "items.json", json.dumps(ITEMS))
        code, out, err = run(self.root, "file", os.path.join(self.root, "items.json"), "--by", "developer", "--now",
                             "2026-10-29T07:00:00Z")
        self.assertEqual(code, 0, err)
        e = shown(self.root)
        self.issue = e["The draft skills hand people the FILE path"]["id"]
        self.follow = e["Tell email_lead the skill changed"]["id"]

    def test_a_a_sha_on_head_writes_two_records_and_folds_to_fixed(self):
        before = listing(self.root)
        code, out, err = run(self.root, "fixed", self.issue, self.sha[:10], "--by", "developer", "--now",
                             "2026-10-29T08:00:00Z")
        self.assertEqual(code, 0, err)
        new = sorted(set(listing(self.root)) - set(before))
        self.assertEqual(len(new), 2, "two records")
        recs = [json.loads(pf18.read(os.path.join(self.root, TASKS, f))) for f in new]
        recs.sort(key=lambda r: r["created"])
        self.assertEqual([r["verdict"]["event"] for r in recs], ["comment", "status"])
        self.assertEqual(recs[0]["verdict"]["text"], "Fixed at commit " + self.sha, "the full sha is kept")
        self.assertEqual(recs[1]["verdict"]["to"], "done")
        self.assertEqual(recs[1]["verdict"]["note"], "fixed at %s: %s" % (self.sha[:10], SUBJECT))
        for r in recs:
            self.assertEqual((r["kind"], r["item"], r["reviewer"]), ("tasks", self.issue, "developer"))
        e = shown(self.root)["The draft skills hand people the FILE path"]
        self.assertEqual(e["state"], "fixed")
        self.assertEqual(e["fixed_at"], {"sha": self.sha, "subject": SUBJECT, "at": FIX_AT})
        self.assertEqual(e["notes"], [], "the fix's comment is not a loose note")
        self.assertIn("Fixed at %s · %s" % (self.sha[:10], SUBJECT), out)

    def test_a_a_note_is_kept_after_the_subject(self):
        code, out, err = run(self.root, "fixed", self.issue, self.sha, "--by", "developer", "--note", "first use",
                             "--now", "2026-10-29T08:00:00Z")
        self.assertEqual(code, 0, err)
        e = shown(self.root)["The draft skills hand people the FILE path"]
        self.assertEqual((e["state"], e["fixed_at"]["subject"]), ("fixed", SUBJECT), "the subject comes from git")
        self.assertTrue(e["history"][-1]["note"].endswith(" — first use"))

    def test_b_a_sha_not_in_the_repo_refuses(self):
        before = listing(self.root)
        for sha, words in (("deadbeef00", "is no commit"), ("not-a-sha", "is not a commit sha")):
            code, out, err = run(self.root, "fixed", self.issue, sha, "--by", "developer", "--now", "2026-10-29T08:00:00Z")
            self.assertEqual(code, 2, out)
            self.assertIn(words, err)
            self.assertEqual(listing(self.root), before, "nothing written")
        self.assertEqual(shown(self.root)["The draft skills hand people the FILE path"]["state"], "raised")

    def test_b_a_commit_not_on_head_refuses(self):
        tree = self.repo.git("rev-parse", "HEAD^{tree}")
        side = self.repo.git("commit-tree", tree, "-p", self.sha, "-m", "a branch commit, never merged")
        before = listing(self.root)
        code, out, err = run(self.root, "fixed", self.issue, side, "--by", "developer", "--now", "2026-10-29T08:00:00Z")
        self.assertEqual(code, 2, out)
        self.assertIn("is not on HEAD", err)
        self.assertEqual(listing(self.root), before, "nothing written")

    def test_c_a_follow_up_refuses(self):
        before = listing(self.root)
        code, out, err = run(self.root, "fixed", self.follow, self.sha, "--by", "developer", "--now", "2026-10-29T08:00:00Z")
        self.assertEqual(code, 2, out)
        self.assertIn("`done` is its move", err)
        self.assertEqual(listing(self.root), before, "nothing written")

    def test_c_it_takes_two_arguments(self):
        code, out, err = run(self.root, "fixed", self.issue, "--by", "developer")
        self.assertEqual(code, 2)
        self.assertIn("takes 2 arguments, got 1", err)

    def test_d_the_queue_lists_neither_fixed_nor_closed(self):
        code, out, err = run(self.root, "fixed", self.issue, self.sha, "--by", "developer", "--now", "2026-10-29T08:00:00Z")
        self.assertEqual(code, 0, err)
        e = shown(self.root)
        hand = e["An issue someone ticked done by hand"]["id"]
        pf18.write(self.root, TASKS + "20261029T080500Z--developer--%s--status.json" % hand, json.dumps(
            {"schema": 1, "kind": "tasks", "reviewer": "developer", "item": hand, "notes": "", "via": "test",
             "verdict": {"event": "status", "to": "done", "note": "ticked done"}, "created": "2026-10-29T08:05:00Z"}))
        doc = dev_queue.build(self.root, now="2026-10-29T09:00:00Z")
        states = dict((x["title"], x["state"]) for x in doc["issues"])
        self.assertEqual(states["An issue someone ticked done by hand"], "closed", "closed stays for anything else")
        self.assertEqual(states["The draft skills hand people the FILE path"], "fixed")
        raised = e["An issue still raised"]["id"]
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        harness = pf18.PAGE_HARNESS.split("(async () => {")[0] + PAGE_RUN
        pf18.write(self.root, "data.json", json.dumps(doc))
        pf18.write(self.root, "harness.js", harness)
        p = subprocess.run([node, os.path.join(self.root, "harness.js"), os.path.join(REAL, TPL),
                            os.path.join(self.root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        self.assertIn(raised, got["tiles"])
        self.assertNotIn(self.issue, got["tiles"], "a fixed issue leaves the queue")
        self.assertNotIn(hand, got["tiles"], "a closed issue leaves the queue")
        self.assertNotIn("Closed", got["words"])


PAGE_RUN = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const col = g("col-issue-queue"), words = e => e.textContent.replace(/\s+/g, " ").trim();
  console.log(JSON.stringify({errors: errors, words: words(col),
    tiles: find(col, e => e.getAttribute("data-issue")).map(e => e.getAttribute("data-issue"))}));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


if __name__ == "__main__":
    unittest.main()
