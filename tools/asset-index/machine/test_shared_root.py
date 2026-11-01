#!/usr/bin/env python3
"""Tests for where shared_paths.py finds the Shared Assets root (SI-45 (footage
mount helper)): SHARED_ASSETS_ROOT wins, else the one shared mount helper
(components/brandpath/drive_index.py mount()), else None and the walk refuses
loudly. No network, no drive: every HOME and mount is made in a temp folder.

    /usr/bin/python3 tools/asset-index/machine/test_shared_root.py
"""
from __future__ import annotations

import contextlib
import importlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "brandpath"))
import drive_index  # noqa: E402
sys.path.insert(0, str(HERE))
import shared_paths  # noqa: E402

BRAND = "zz-test-brand"


class SharedRoot(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="asset-index-root-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()

    def tearDown(self):
        importlib.reload(shared_paths)

    def fake_mount(self) -> pathlib.Path:
        m = (self.home / "Library" / "CloudStorage" / "GoogleDrive-tester@company.com"
             / "Shared drives" / "Shared Assets")
        m.mkdir(parents=True)
        return m

    def env_without_root(self) -> dict:
        # LD-26 (mount switch): a worker-spawned run of this suite inherits
        # DRIVE_MOUNT=off; these tests are a person's session, so drop it.
        return {k: v for k, v in os.environ.items()
                if k not in ("SHARED_ASSETS_ROOT", "DRIVE_MOUNT")}

    def test_env_wins(self):
        self.fake_mount()
        env_root = self.tmp / "elsewhere"
        env_root.mkdir()
        with mock.patch.object(pathlib.Path, "home", return_value=self.home), \
                mock.patch.dict(os.environ, {"SHARED_ASSETS_ROOT": str(env_root)}):
            importlib.reload(shared_paths)
            self.assertEqual(shared_paths.SHARED_ROOT, env_root)

    def test_mount_is_the_default(self):
        m = self.fake_mount()
        with mock.patch.object(pathlib.Path, "home", return_value=self.home), \
                mock.patch.dict(os.environ, self.env_without_root(), clear=True):
            importlib.reload(shared_paths)
            self.assertEqual(drive_index.mount(), m)
            self.assertEqual(shared_paths.SHARED_ROOT, drive_index.mount())
            self.assertEqual(shared_paths.brand_root(BRAND),
                             shared_paths.SHARED_ROOT / "brands" / BRAND)

    def test_no_mount_no_env_is_loud(self):
        with mock.patch.object(pathlib.Path, "home", return_value=self.home), \
                mock.patch.dict(os.environ, self.env_without_root(), clear=True):
            importlib.reload(shared_paths)
            self.assertIsNone(shared_paths.SHARED_ROOT)
            with self.assertRaises(SystemExit) as cm:
                shared_paths.brand_root(BRAND)
            self.assertIn("SHARED_ASSETS_ROOT", str(cm.exception))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertFalse(shared_paths.on_shared(str(self.tmp / "x.mp4")))
            self.assertIn("SHARED_ASSETS_ROOT", err.getvalue())

    def test_no_personal_path_left(self):
        text = pathlib.Path(shared_paths.__file__).read_text()
        self.assertNotIn("CloudStorage", text)
        self.assertNotIn("GoogleDrive-", text)


if __name__ == "__main__":
    unittest.main()
