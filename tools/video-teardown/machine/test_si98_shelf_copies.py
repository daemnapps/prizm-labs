#!/usr/bin/env python3
"""SI-98 (shelf and index homes): the teardown shelf carries run.json only.
The brief is read from the writing shelf; a brief.md already on the teardown
shelf is frozen history, read last.

    /usr/bin/python3 tools/video-teardown/machine/test_si98_shelf_copies.py

Every tree is a temp folder; nothing under the real runs/ is touched. Stdlib only.
"""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import records                                               # noqa: E402


class ShelfCopies(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.t = Path(td.name)
        work = self.t / "work" / "r1"
        (work / "stages").mkdir(parents=True)
        (work / "run.json").write_text(json.dumps({"brand": "zz-brand"}))
        (work / "brief-final.md").write_text("# final\n")
        (work / "stages" / "7b-page.md").write_text("page\n")
        for p in (mock.patch.object(records.C, "runs_root", lambda: self.t / "work"),
                  mock.patch.object(records, "RUNS_HOME", self.t / "runs" / "video-teardown")):
            p.start()
            self.addCleanup(p.stop)
        self.home = self.t / "runs" / "video-teardown" / "zz-brand" / "r1"

    def test_runs_copies_run_json_only(self):
        got = records.runs()
        self.assertEqual([slug for slug, _ in got], ["r1"])
        self.assertTrue((self.home / "run.json").is_file())
        for name in ("brief.md", "brief-final.md", "page.md"):
            self.assertFalse((self.home / name).exists(), name)
        self.assertEqual(records.SHELF_COPIES, ("run.json",))

    def test_brief_file_reads_the_writing_shelf_then_frozen_history(self):
        self.home.mkdir(parents=True)
        self.assertIsNone(records.brief_file(self.home))
        (self.home / "brief.md").write_text("# frozen\n")
        self.assertEqual(records.brief_file(self.home), self.home / "brief.md")
        out = self.t / "runs" / "video-writing" / "zz-brand" / "r1" / "deliverable"
        out.mkdir(parents=True)
        (out / "7-final-brief.md").write_text("# final\n")
        self.assertEqual(records.brief_file(self.home), out / "7-final-brief.md")

    def test_source_reads_through_brief_file(self):
        src = (HERE / "records.py").read_text()
        self.assertIn("brief_file(home)", src)
        self.assertNotIn("7b-page.md", src)


if __name__ == "__main__":
    unittest.main(verbosity=1)
