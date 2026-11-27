#!/usr/bin/env python3
"""Tests for the copier: strips names and home paths, refuses leaks, copies only saved files, stamps what it copied."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mirror  # noqa: E402

HOME = "/" + "Users/"  # spelled in two parts so the public-repo check does not flag a sample path


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class StripTest(unittest.TestCase):
    def test_names_and_paths(self):
        out = mirror.strip("Ask Zorbo at " + HOME + "zorbo/x and zorbo's file", {"zorbo": "the owner"})
        self.assertEqual(out, "Ask the owner at ~/x and the owner's file")

    def test_file_tags_renamed_before_names(self):
        out = mirror.strip("load stage1-v3-zorbo.md", {"zorbo": "the owner"}, {"-zorbo": "-owner"})
        self.assertEqual(out, "load stage1-v3-owner.md")

    def test_code_gets_one_word(self):
        out = mirror.strip("zorbo_rule = zorbo_says()", {"zorbo": "the owner"}, code=True)
        self.assertEqual(out, "owner_rule = owner_says()")
        compile(out, "x", "exec")

    def test_drop_lines(self):
        out = mirror.strip("a\nHow to use it -> https://dash.inside/x\nb\n", {}, {}, [r"dash\.inside"])
        self.assertEqual(out, "a\nb\n")

    def test_whole_words_only(self):
        self.assertEqual(mirror.strip("zorbonia", {"zorbo": "X"}), "zorbonia")

    def test_leaks_find_keys_and_paths(self):
        kinds = {k for k, _ in mirror.leaks("key sk-" + "a" * 30 + " at " + HOME + "someone/")}
        self.assertEqual(kinds, {"key-like text", "home path"})


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        src = Path(self.tmp.name) / "src"
        (src / "a").mkdir(parents=True)
        (src / "a" / "one.md").write_text("made by Zorbo\n")
        (src / "a" / "archive").mkdir()
        (src / "a" / "archive" / "old.md").write_text("old\n")
        (src / "a" / "p-v2-zorbo.md").write_text("see p-v2-zorbo.md\n")
        (src / "a" / "p-v1-zorbo.md").write_text("older\n")
        (src / "a" / "q-v1.md").write_text("older but loaded\n")
        (src / "a" / "q-v2.md").write_text("newer\n")
        (src / "a" / "load.py").write_text("PROMPT = 'q-v1.md'\n")
        sh(src, "git", "init", "-q")
        sh(src, "git", "-c", "user.email=t@example.com", "-c", "user.name=t", "add", ".")
        sh(src, "git", "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "x")
        (src / "a" / "draft.md").write_text("not saved\n")
        self.src = str(src)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self._old = (mirror.REPO, mirror.STAMPS)
        mirror.REPO, mirror.STAMPS = self.repo, self.repo / "stamps.json"

    def tearDown(self):
        mirror.REPO, mirror.STAMPS = self._old
        self.tmp.cleanup()

    def test_copies_saved_only_and_stamps(self):
        cfg = {"source": self.src, "ref": "HEAD", "names": {"zorbo": "the owner"}, "suffixes": {"-zorbo": "-owner"}}
        groups = {"g": [{"from": "a", "to": "b"}]}
        self.assertEqual(mirror.run(cfg, groups, "g", dry=False), 0)
        self.assertEqual((self.repo / "b" / "one.md").read_text(), "made by the owner\n")
        self.assertFalse((self.repo / "b" / "draft.md").exists())
        self.assertFalse((self.repo / "b" / "archive").exists())
        self.assertFalse((self.repo / "b" / "p-v1-owner.md").exists())
        self.assertTrue((self.repo / "b" / "q-v1.md").exists())
        self.assertEqual((self.repo / "b" / "p-v2-owner.md").read_text(), "see p-v2-owner.md\n")
        self.assertIn("b/one.md", json.loads(mirror.STAMPS.read_text()))
        self.assertEqual(mirror.unsaved(groups["g"][0], self.src, "HEAD"), ["a/draft.md"])


if __name__ == "__main__":
    unittest.main()
