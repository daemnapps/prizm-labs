#!/usr/bin/env python3
"""drive_hand: a finished file under runs/ goes to the Drive's same path, a pointer stays behind,
tracked files and machines without a mount are left alone. No real Drive: a temp folder stands in
for the mount and the follower is never started."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from run_kit import drive_hand as D
from run_kit import filing


def _git(*args):
    """git in the test's own workspace only: no GIT_* setting from the caller (an index or a work tree)
    may point it at a real checkout."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", *args], check=True, env=env, capture_output=True)


class DriveHandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.ws = t / "ws"
        for d in ("components", "brands", "runs/video-edit/b/l"):
            (self.ws / d).mkdir(parents=True)
        _git("init", "-q", str(self.ws))
        self.mount = t / "Shared Assets"
        (self.mount / "runs").mkdir(parents=True)
        self._drive_runs = filing.drive_runs
        filing.drive_runs = lambda: self.mount / "runs"
        self._cache = D.CACHE
        D.CACHE = t / "cache"
        self._homes = D.HOMES_FILE
        D.HOMES_FILE = t / "drive-homes.json"
        self.other = t / "Other Drive"
        (self.other / "runs").mkdir(parents=True)
        os.environ.pop("RUNS_TO_DRIVE", None)

    def tearDown(self):
        filing.drive_runs = self._drive_runs
        D.CACHE = self._cache
        D.HOMES_FILE = self._homes
        os.environ.pop("RUNS_TO_DRIVE", None)
        self.tmp.cleanup()

    def _file(self, rel, data=b"video-bytes"):
        p = self.ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def test_moves_to_same_path_and_leaves_pointer(self):
        p = self._file("runs/video-edit/b/l/work/final.mp4")
        dst, note = D.hand(p, follow_up=False)
        want = self.mount / "runs/video-edit/b/l/work/final.mp4"
        self.assertEqual(Path(dst), want, note)
        self.assertEqual(want.read_bytes(), b"video-bytes")
        self.assertTrue(p.is_symlink())
        self.assertEqual(p.read_bytes(), b"video-bytes")          # readers still find it
        self.assertIn(str(want), (D.CACHE / "pending.json").read_text())

    def test_overwrites_drive_copy_in_place(self):
        want = self.mount / "runs/video-edit/b/l/final.mp4"
        want.parent.mkdir(parents=True)
        want.write_bytes(b"old")
        ino = os.stat(want).st_ino
        p = self._file("runs/video-edit/b/l/final.mp4", b"new")
        D.hand(p, follow_up=False)
        self.assertEqual(want.read_bytes(), b"new")
        self.assertEqual(os.stat(want).st_ino, ino)               # same file, so the same Drive id

    def test_second_hand_is_a_no_op_that_requeues(self):
        p = self._file("runs/video-edit/b/l/final.mp4")
        D.hand(p, follow_up=False)
        dst, note = D.hand(p, follow_up=False)
        self.assertEqual(note, "on the upright Drive")
        self.assertTrue(p.is_symlink())

    def _two_homes(self, routes=None):
        D.HOMES_FILE.write_text(json.dumps({"homes": {"second": str(self.other)}, "routes": routes or {}}))

    def test_named_home_by_call(self):
        self._two_homes()
        p = self._file("runs/video-edit/b/l/final.mp4")
        dst, note = D.hand(p, follow_up=False, to="second")
        self.assertEqual(Path(dst), self.other / "runs/video-edit/b/l/final.mp4", note)
        self.assertFalse((self.mount / "runs/video-edit/b/l/final.mp4").exists())

    def test_route_picks_home_longest_wins(self):
        self._two_homes({"runs/video-edit/b": "upright", "runs/video-edit/b/l": "second"})
        p = self._file("runs/video-edit/b/l/final.mp4")
        q = self._file("runs/video-edit/b/m/final.mp4")
        self.assertTrue(str(D.hand(p, follow_up=False)[0]).startswith(str(self.other)))
        self.assertTrue(str(D.hand(q, follow_up=False)[0]).startswith(str(self.mount)))

    def test_env_names_home(self):
        self._two_homes()
        os.environ["RUNS_TO_DRIVE"] = "second"
        p = self._file("runs/video-edit/b/l/final.mp4")
        self.assertTrue(str(D.hand(p, follow_up=False)[0]).startswith(str(self.other)))

    def test_move_between_homes_keeps_first_copy(self):
        self._two_homes()
        p = self._file("runs/video-edit/b/l/final.mp4")
        D.hand(p, follow_up=False)
        dst, note = D.hand(p, follow_up=False, to="second")
        self.assertEqual(Path(dst), self.other / "runs/video-edit/b/l/final.mp4", note)
        self.assertEqual(Path(os.path.realpath(p)), Path(os.path.realpath(dst)))
        self.assertTrue((self.mount / "runs/video-edit/b/l/final.mp4").exists())   # never removed

    def test_unknown_home_keeps_file(self):
        p = self._file("runs/video-edit/b/l/final.mp4")
        dst, note = D.hand(p, follow_up=False, to="nowhere")
        self.assertIsNone(dst)
        self.assertFalse(p.is_symlink())

    def test_route_writer(self):
        D.route("runs/video-edit/b/l", "second")
        self.assertEqual(json.loads(D.HOMES_FILE.read_text())["routes"], {"runs/video-edit/b/l": "second"})
        D.route("runs/video-edit/b/l", None)
        self.assertEqual(json.loads(D.HOMES_FILE.read_text())["routes"], {})

    def test_readable_follows_pointer_into_drive_only(self):
        p = self._file("runs/video-edit/b/l/final.mp4")
        D.hand(p, follow_up=False)
        self.assertEqual(D.readable(p, self.ws), Path(os.path.realpath(self.mount / "runs/video-edit/b/l/final.mp4")))
        self.assertIsNone(D.readable(self.ws / "runs/../../etc/passwd", self.ws))
        out = self.ws / "runs/video-edit/b/l/elsewhere.mp4"
        os.symlink("/etc/hosts", out)
        self.assertIsNone(D.readable(out, self.ws))

    def test_tracked_file_left_alone(self):
        p = self._file("runs/video-edit/b/l/record.png")
        _git("-C", str(self.ws), "add", "-f", "runs/video-edit/b/l/record.png")
        dst, note = D.hand(p, follow_up=False)
        self.assertIsNone(dst)
        self.assertIn("tracked", note)
        self.assertFalse(p.is_symlink())
        self.assertFalse((self.mount / "runs/video-edit/b/l/record.png").exists())

    def test_outside_runs_left_alone(self):
        p = self._file("components/x.mp4")
        dst, note = D.hand(p, follow_up=False)
        self.assertIsNone(dst)
        self.assertFalse(p.is_symlink())

    def test_no_mount_is_a_no_op(self):
        def none():
            raise filing.MountError("none")
        filing.drive_runs = none
        p = self._file("runs/video-edit/b/l/final.mp4")
        dst, note = D.hand(p, follow_up=False)
        self.assertIsNone(dst)
        self.assertFalse(p.is_symlink())

    def test_switch_off(self):
        os.environ["RUNS_TO_DRIVE"] = "off"
        try:
            p = self._file("runs/video-edit/b/l/final.mp4")
            self.assertIsNone(D.hand(p, follow_up=False)[0])
            self.assertFalse(p.is_symlink())
        finally:
            os.environ.pop("RUNS_TO_DRIVE")

    def test_never_raises(self):
        dst, note = D.hand(self.ws / "runs/video-edit/b/l/missing.mp4", follow_up=False)
        self.assertIsNone(dst)


if __name__ == "__main__":
    unittest.main()
