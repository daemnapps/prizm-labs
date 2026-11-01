#!/usr/bin/env python3
"""python3 test_drive_runs_helper.py — SI-42 (run-kit mount helper): filing.drive_runs()
finds Shared Assets through components/brandpath/drive_index.py mount(), not its
own glob (O9 (Drive by fileId)). Stdlib unittest, fake HOME, no key, no network."""
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_kit import filing   # noqa: E402

sys.path.insert(0, str(HERE.parent / "brandpath"))
import drive_index   # noqa: E402

FILING = HERE / "run_kit" / "filing.py"


class DriveRunsHelper(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        for p in (mock.patch.object(pathlib.Path, "home", return_value=self.home),
                  mock.patch.dict(os.environ)):
            p.start()
            self.addCleanup(p.stop)
        # LD-26 (mount switch): a worker-spawned run of this suite inherits
        # DRIVE_MOUNT=off; these tests are a person's session, so drop it.
        os.environ.pop("DRIVE_MOUNT", None)

    def fake_mount(self):
        s = (self.home / "Library" / "CloudStorage" / "GoogleDrive-tester@company.com"
             / "Shared drives" / "Shared Assets")
        s.mkdir(parents=True)
        return s

    def test_drive_runs_is_the_helpers_mount_plus_runs(self):
        shared = self.fake_mount()
        self.assertEqual(filing.drive_runs(), shared / "runs")
        self.assertEqual(filing.drive_runs(), drive_index.mount() / "runs")

    def test_no_mount_is_a_loud_mount_error(self):
        with self.assertRaises(filing.MountError) as cm:
            filing.drive_runs()
        self.assertIn("Shared Assets", str(cm.exception))

    def test_media_dir_lands_under_the_mount(self):
        shared = self.fake_mount()
        d = filing.media_dir("zz-tool", "zz-test-brand", "zz-label")
        want = shared / "runs" / "zz-tool" / "zz-test-brand" / "zz-label"
        self.assertEqual(d, want)
        self.assertTrue(want.is_dir())

    def test_no_own_glob_left(self):
        text = FILING.read_text()
        self.assertNotIn("CloudStorage", text)
        self.assertNotIn("GoogleDrive-", text)


if __name__ == "__main__":
    unittest.main()
