"""Every change to an ad's words on the approval page is logged, digested for the copywriter, and offered back
in the copy library for the next batch."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


class CopyLog(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.tmp)})
        self.env.start()
        import copy_library
        self.CL = copy_library
        self.CL.L.SD.save = lambda p: None
        self.card = {"brand": "acme", "lane": "video", "ad_name": "acme_widget_brief-0001_batch-2026-11-08-a",
                     "brief_id": "brief-0001", "product": "widget"}

    def tearDown(self):
        self.env.stop()

    def test_a_change_is_logged_digested_and_offered_back(self):
        before = {"primary": ["Old body"], "headlines": ["Old head"], "descriptions": []}
        after = {"primary": ["New body that worked better"], "headlines": ["Old head"], "descriptions": ["Short line"]}
        row = self.CL.log_edit(self.card, before, after, picked=["headlines:Old head"], by="owner")
        self.assertEqual(row["after"]["primary"], ["New body that worked better"])
        lines = (self.tmp / "copy-edits.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 1)
        dig = (self.tmp / "learnings" / self.CL.L.step_dir(4) / "acme-copy-edits.md").read_text()
        self.assertIn('Primary text now: "New body that worked better"', dig)
        self.assertIn('Primary text removed: "Old body"', dig)
        lib = self.CL.library("acme")
        self.assertIn("New body that worked better", [o["text"] for o in lib["primary"]])
        self.assertEqual(next(o for o in lib["descriptions"] if o["text"] == "Short line")["from"], "edit")

    def test_no_change_writes_nothing(self):
        w = {"primary": ["Same"], "headlines": ["Same"], "descriptions": []}
        self.assertIsNone(self.CL.log_edit(self.card, w, w))
        self.assertFalse((self.tmp / "copy-edits.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
