"""A pull ends by saying which shared-page changes a person's own page still lacks (email_lead, 2026-11-12: editor pulled
through her Done and the changes never reached her page, because only "start my email session" brought them in).
Real git, in a temporary repo; no network."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import page_sync as P


def git(root, *a):
    subprocess.run(["git"] + list(a), cwd=str(root), check=True, capture_output=True, text=True)


def commit(root, files, msg):
    for f, text in files.items():
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg)
    return subprocess.run(["git", "log", "-1", "--format=%h"], cwd=str(root), capture_output=True,
                          text=True).stdout.strip()


class AfterPull(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        self.old = P.REPO
        P.REPO = self.root
        shared, mine = P.SHARED[0], P.own("editor")[0]
        base = commit(self.root, {shared: "a", mine: "a", P.VIEWERS + "/editor/emails.sync.json": "{}"}, "base")
        (self.root / P.VIEWERS / "editor/emails.sync.json").write_text(json.dumps({"shared_brought_in": base}))
        commit(self.root, {P.VIEWERS + "/editor/emails.sync.json": json.dumps({"shared_brought_in": base})}, "record")
        self.only_shared = commit(self.root, {shared: "b"}, "shared only")
        self.both = commit(self.root, {shared: "c", mine: "c"}, "shared and hers in one act")

    def tearDown(self):
        P.REPO = self.old
        self.tmp.cleanup()

    def test_lists_only_what_her_page_lacks(self):
        note = P.after_pull_note("editor")
        self.assertIn("1 change(s)", note)
        self.assertIn(self.only_shared, note)
        self.assertNotIn(self.both, note)

    def test_silent_when_nothing_to_bring_or_no_own_page(self):
        self.assertEqual(P.after_pull_note("nobody"), "")
        self.assertEqual(P.after_pull_note(None), "")
        rec = self.root / P.VIEWERS / "editor/emails.sync.json"
        rec.write_text(json.dumps({"shared_brought_in": self.both}))
        self.assertEqual(P.after_pull_note("editor"), "")


if __name__ == "__main__":
    unittest.main()
