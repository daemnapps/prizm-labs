#!/usr/bin/env python3
"""SI-98 (shelf and index homes): a video-teardown brief is read from the
writing shelf, runs/video-writing/<brand>/<run>/deliverable/; the teardown
shelf's brief.md is frozen history, and _work/ is never a filed run.

    /usr/bin/python3 tools/image-teardown/tests/test_si98_video_brief.py

No network, no model. The register, the alias file and both shelves are temp.
"""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE / "tools"))
import briefs as B  # noqa: E402


class VideoBrief(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = Path(td.name)
        self.shelf = self.td / "runs" / "video-teardown"
        self.writing = self.td / "runs" / "video-writing"
        for name, brief in (("w-1", "7-final-brief.md"), ("w-2", "5-brief.md"), ("w-3", None)):
            d = self.shelf / "brand-b" / name
            d.mkdir(parents=True)
            (d / "run.json").write_text(json.dumps({"brand": "brand-b", "product": "the-scrub"}))
            if brief:
                out = self.writing / "brand-b" / name / "deliverable"
                out.mkdir(parents=True)
                (out / brief).write_text(f"# Title of {name}\n\nbody\n")
        work = self.shelf / "_work" / "w-1"
        work.mkdir(parents=True)
        (work / "brief.md").write_text("# WRONG\n")
        (self.td / "briefs.json").write_text(json.dumps(
            {"briefs": {"p140": {"brand": "brand-b", "run": None, "opened": "x"}},
             "blocks": {"brand-a": 1, "brand-b": 140}}))
        (self.td / "aliases.json").write_text(json.dumps({"aliases": {}, "never_used": []}))
        for attr, val in (("REGISTER", self.td / "briefs.json"), ("VIDEO_RUNS", self.shelf),
                          ("VIDEO_WRITING", self.writing), ("ALIASES", self.td / "aliases.json")):
            p = mock.patch.object(B, attr, val)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(lambda: setattr(B.N, "_ALIASES", None))

    def test_a_run_filed_the_new_way_opens_from_the_writing_shelf(self):
        bid, rec = B.open_brief("w-1", "brand-b", kind="video-creator")
        self.assertEqual(rec["title"], "Title of w-1")
        self.assertEqual(rec["run"], "w-1")

    def test_work_is_never_the_run(self):
        run = B.video_run("w-1", None)
        self.assertNotIn("_work", run.parts)
        self.assertEqual(run, self.shelf / "brand-b" / "w-1")

    def test_final_brief_then_brief(self):
        self.assertTrue(B.video_brief(self.shelf / "brand-b" / "w-1").as_posix()
                        .endswith("deliverable/7-final-brief.md"))
        self.assertEqual(B.video_brief(self.shelf / "brand-b" / "w-2"),
                         self.writing / "brand-b" / "w-2" / "deliverable" / "5-brief.md")

    def test_no_brief_anywhere_is_refused(self):
        self.assertIsNone(B.video_brief(self.shelf / "brand-b" / "w-3"))
        with self.assertRaises(SystemExit):
            B.open_brief("w-3", "brand-b", kind="video-creator")
        self.assertEqual(list(B.load()["briefs"]), ["p140"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
