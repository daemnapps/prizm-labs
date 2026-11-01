#!/usr/bin/env python3
"""SI-48 (teardown drops home): the hand-off finds a drop at its new home,
runs/image-teardown/<brand>/<drop>/deliverable/, first and at the legacy
runs/image-edit/ home second. No key, no network; temp folders only."""
import sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import handoff as H


class DropDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        p = mock.patch.object(H, "WS", self.root)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_home_first(self):
        old = self.root / "runs/image-edit/zz-brand/d1/deliverable"
        old.mkdir(parents=True)
        self.assertEqual(H.drop_dir("zz-brand", "d1"), old)
        new = self.root / "runs/image-teardown/zz-brand/d1/deliverable"
        new.mkdir(parents=True)
        self.assertEqual(H.drop_dir("zz-brand", "d1"), new)

    def test_neither_means_the_new_home(self):
        self.assertEqual(H.drop_dir("zz-brand", "d2"),
                         self.root / "runs/image-teardown/zz-brand/d2/deliverable")

    def test_no_reader_line_names_the_old_slot(self):
        src = (HERE.parent / "handoff.py").read_text()
        self.assertNotIn('WS / "runs/image-edit"', src)
        self.assertNotIn('["runs", "image-edit"', src)


if __name__ == "__main__":
    unittest.main()
