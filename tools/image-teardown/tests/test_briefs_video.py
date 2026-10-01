#!/usr/bin/env python3
"""briefs.py open --type video-creator: a video-teardown creator brief gets
its number from the same bank (2026-09-29).

    python3 tools/image-teardown/tests/test_briefs_video.py

No network, no model. The register, the alias file and the runs folder are
all temp copies.
"""
import json, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE / "tools"))
import briefs as B  # noqa: E402


class VideoOpen(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        runs = self.td / "runs"
        for name, brand, creator in (("jen-01-x", "brand-b", "jen"), ("gen-y", "brand-b", None),
                                     ("other-z", "brand-a", "someone")):
            d = runs / name
            d.mkdir(parents=True)
            (d / "brief.md").write_text(f"# Title of {name}\n\nbody\n")
            (d / "run.json").write_text(json.dumps({
                "brand": brand, "creator": creator, "product": "the-scrub",
                "opened": "2026-08-27T10:00:00Z", "gdoc_url": "https://docs.google.com/document/d/abc/edit",
                "audience": {"_avatar": "<avatar>"}}))
        (runs / "unfinished").mkdir()
        (self.td / "briefs.json").write_text(json.dumps(
            {"briefs": {"p140": {"brand": "brand-b", "run": None, "opened": "x"}},
             "blocks": {"brand-a": 1, "brand-b": 140}}))
        (self.td / "aliases.json").write_text(json.dumps({"aliases": {}, "never_used": []}))
        for attr, val in (("REGISTER", self.td / "briefs.json"), ("VIDEO_RUNS", runs),
                          ("ALIASES", self.td / "aliases.json")):
            p = mock.patch.object(B, attr, val)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(lambda: setattr(B.N, "_ALIASES", None))

    def test_a_creator_run_gets_the_next_number_and_its_record(self):
        bid, rec = B.open_brief("jen-01-x", "brand-b", kind="video-creator")
        self.assertEqual((bid, rec["brief"], rec["type"]), ("p141", "brief-0141", "video-creator"))
        self.assertEqual(rec["title"], "Title of jen-01-x")
        self.assertEqual((rec["creator"], rec["product"], rec["avatar"]), ("jen", "the-scrub", "<avatar>"))
        self.assertEqual(rec["run_opened"], "2026-08-27T10:00:00Z")
        self.assertTrue(rec["gdoc_url"].startswith("https://docs.google.com/"))
        self.assertIn("p141", B.load()["briefs"])
        self.assertEqual(json.loads(B.ALIASES.read_text())["aliases"]["p141"], "brief-0141")

    def test_one_id_per_run_for_ever(self):
        first = B.open_brief("jen-01-x", "brand-b", kind="video-creator")[0]
        again = B.open_brief("jen-01-x", "brand-b", kind="video-creator")[0]
        self.assertEqual(first, again)
        self.assertEqual(B.open_brief("gen-y", "brand-b", kind="video-creator")[0], "p142")

    def test_a_general_brief_has_no_creator(self):
        self.assertIsNone(B.open_brief("gen-y", "brand-b", kind="video-creator")[1]["creator"])

    def test_no_brief_md_or_wrong_brand_is_refused(self):
        with self.assertRaises(SystemExit):
            B.open_brief("unfinished", "brand-b", kind="video-creator")
        with self.assertRaises(SystemExit):
            B.open_brief("other-z", "brand-b", kind="video-creator")
        self.assertEqual(list(B.load()["briefs"]), ["p140"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
