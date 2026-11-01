#!/usr/bin/env python3
"""LD-32 (teardown drive switch)'s declared test — chain.py's own Drive lookup
honours LD-26 (mount switch).

    cd tools/video-teardown/machine && python3 test_ld32_drive_switch.py

Offline: no network, no real Drive mount, nothing written outside a temp
directory. Path.home() is pointed at a fake home holding a fake mount.

    (a) DRIVE_MOUNT=off: drive_mounts() is [] and drive_root() raises
        MountError, with every stat, listing and glob failing loudly — so
        nothing under the home is touched, even with a mount sitting there
    (b) unset (a person's session): the fake mount is found as today
    (c) only the exact value "off" switches
"""

import contextlib, os, pathlib, sys, tempfile, unittest
from unittest import mock

MACHINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MACHINE))

import chain as C          # noqa: E402


class DriveSwitch(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name) / "home"
        self.acct = self.home / "Library" / "CloudStorage" / "GoogleDrive-a@company.com"
        self.sa = self.acct / "Shared drives" / "Shared Assets"
        self.sa.mkdir(parents=True)
        p = mock.patch.object(pathlib.Path, "home", return_value=self.home)
        p.start()
        self.addCleanup(p.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("DRIVE_MOUNT", None)

    def no_touch(self):
        """Every stat, listing and glob fails loudly while open."""
        def boom(name):
            def f(*a, **k):
                raise AssertionError("LD-32 (teardown drive switch): %s touched the filesystem %r"
                                     % (name, a[:1]))
            return f

        stack = contextlib.ExitStack()
        for n in ("stat", "lstat", "is_dir", "is_file", "exists", "glob", "iterdir"):
            stack.enter_context(mock.patch.object(pathlib.Path, n, boom("Path." + n)))
        for n in ("stat", "lstat", "scandir", "listdir"):
            stack.enter_context(mock.patch.object(os, n, boom("os." + n)))
        return stack

    def test_guard_fires_without_the_switch_and_releases(self):
        with self.no_touch():
            with self.assertRaises(AssertionError):
                C.drive_mounts()
        self.assertEqual(C.drive_mounts(), [self.acct])

    def test_off_mounts_empty_nothing_touched(self):
        os.environ["DRIVE_MOUNT"] = "off"
        with self.no_touch():
            self.assertEqual(C.drive_mounts(), [])
        self.assertTrue(self.sa.is_dir())

    def test_off_drive_root_raises_mount_error_nothing_touched(self):
        os.environ["DRIVE_MOUNT"] = "off"
        with self.no_touch():
            with self.assertRaises(C.MountError) as cm:
                C.drive_root()
            with self.assertRaises(C.MountError):
                C.runs_mirror()
        self.assertIn("no Google Drive mount", str(cm.exception))

    def test_unset_is_todays_behaviour(self):
        self.assertEqual(C.drive_mounts(), [self.acct])
        self.assertEqual(C.drive_root(), self.sa)
        self.assertEqual(C.runs_mirror(), self.sa.joinpath(*C.RUNS_SUBPATH))

    def test_only_exact_off_switches(self):
        for v in ("", "0", "no", "OFF", "Off", " off", "off "):
            os.environ["DRIVE_MOUNT"] = v
            self.assertEqual(C.drive_mounts(), [self.acct], repr(v))
            self.assertEqual(C.drive_root(), self.sa, repr(v))


if __name__ == "__main__":
    unittest.main()
