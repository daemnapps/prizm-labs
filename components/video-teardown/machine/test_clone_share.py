#!/usr/bin/env python3
"""A swipe's shared read reaches each run as its own files, without a second copy of the frames (2026-10-23).

    python3 test_clone_share.py
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("vt_run_clone", HERE / "run.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


class CloneShare(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())

    def test_a_folder_arrives_whole(self):
        (self.t / "a" / "frames" / "K01").mkdir(parents=True)
        (self.t / "a" / "frames" / "K01" / "K01-0-0.0.jpg").write_bytes(b"frame" * 1000)
        R._clone(self.t / "a", self.t / "b")
        self.assertEqual((self.t / "b" / "frames" / "K01" / "K01-0-0.0.jpg").read_bytes(), b"frame" * 1000)

    def test_a_write_to_one_run_never_reaches_the_other(self):
        (self.t / "src.json").write_text(json.dumps({"v": 1}))
        R._clone(self.t / "src.json", self.t / "run" / "src.json")
        (self.t / "run" / "src.json").write_text(json.dumps({"v": 2}))
        self.assertEqual(json.loads((self.t / "src.json").read_text()), {"v": 1})

    def test_into_a_folder_that_already_has_files(self):
        (self.t / "a").mkdir()
        (self.t / "a" / "new.txt").write_text("new")
        (self.t / "b").mkdir()
        (self.t / "b" / "old.txt").write_text("old")
        R._clone(self.t / "a", self.t / "b")
        self.assertEqual(sorted(p.name for p in (self.t / "b").iterdir()), ["new.txt", "old.txt"])


if __name__ == "__main__":
    unittest.main()
