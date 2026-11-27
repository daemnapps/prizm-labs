#!/usr/bin/env python3
"""review.py mark (L60 (slot review), 2026-11-06): one verdict from the emails page lands in the month's review.json in
the board's own shape, stamped with the send it is for, and only that file is committed. No network; git is a seam.

    python3 components/marketing-calendar/machine/test_review_mark.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review  # noqa: E402


class R:
    def __init__(self, code=0):
        self.returncode, self.stdout, self.stderr = code, "", "boom" if code else ""


class Mark(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.month = self.root / "runs/marketing-calendar/brand-a/2030-12"
        self.month.mkdir(parents=True)
        (self.month / "slots.json").write_text(json.dumps([
            {"id": "dec-01", "date": "2030-12-01", "segment": "Core | Lead", "type": "moment", "occasion": "x"}]))
        self.calls = []

    def tearDown(self):
        self.t.cleanup()

    def run_git(self, argv, **kw):
        self.calls.append(argv)
        return R()

    def test_mark_lands_in_the_boards_shape_and_commits_that_file_only(self):
        said = review.mark("brand-a", "2030-12", "dec-01", "needs-work", "owner", note=" Softer opener ",
                           root=self.root, run=self.run_git)
        self.assertIn("committed", said)
        e = json.loads((self.month / "review.json").read_text())["slots"]["dec-01"]
        self.assertEqual((e["status"], e["note"], e["by"]), ("needs-work", "Softer opener", "owner"))
        self.assertEqual(e["identity"], {"date": "2030-12-01", "segment": "Core | Lead", "type": "moment", "occasion": "x"})
        self.assertEqual(self.calls[0], ["git", "add", "--", "runs/marketing-calendar/brand-a/2030-12/review.json"])
        self.assertEqual(self.calls[1][-2:], ["--", "runs/marketing-calendar/brand-a/2030-12/review.json"])

    def test_no_note_keeps_the_old_one(self):
        review.mark("brand-a", "2030-12", "dec-01", "needs-work", "owner", note="Keep me", root=self.root, commit=False)
        review.mark("brand-a", "2030-12", "dec-01", "approved", "email_lead", root=self.root, commit=False)
        e = json.loads((self.month / "review.json").read_text())["slots"]["dec-01"]
        self.assertEqual((e["status"], e["note"], e["by"]), ("approved", "Keep me", "email_lead"))

    def test_refused_writes_nothing(self):
        for args in (("brand-a", "2030-12", "dec-99", "approved"), ("brand-a", "2030-12", "dec-01", "wipe"),
                     ("brand-a", "2030-11", "dec-01", "approved"), ("../x", "2030-12", "dec-01", "approved")):
            with self.assertRaises(ValueError):
                review.mark(*args, by="owner", root=self.root, commit=False)
        self.assertFalse((self.month / "review.json").exists())

    def test_edit_rewrites_one_field_and_empty_clears_it(self):
        review.edit("brand-a", "2030-12", "dec-01", "offer", " black-friday ", "owner", root=self.root, commit=False)
        e = json.loads((self.month / "review.json").read_text())["slots"]["dec-01"]
        self.assertEqual((e["edits"], e["by"], e["status"]), ({"offer": "black-friday"}, "owner", "pending"))
        review.edit("brand-a", "2030-12", "dec-01", "offer", "", "owner", root=self.root, commit=False)
        self.assertEqual(json.loads((self.month / "review.json").read_text())["slots"]["dec-01"]["edits"], {})
        with self.assertRaises(ValueError):
            review.edit("brand-a", "2030-12", "dec-01", "why", "x", "owner", root=self.root, commit=False)

    def test_a_failed_commit_keeps_the_mark(self):
        with self.assertRaises(RuntimeError):
            review.mark("brand-a", "2030-12", "dec-01", "cut", "owner", root=self.root, run=lambda a, **k: R(1))
        self.assertEqual(json.loads((self.month / "review.json").read_text())["slots"]["dec-01"]["status"], "cut")


if __name__ == "__main__":
    unittest.main()
