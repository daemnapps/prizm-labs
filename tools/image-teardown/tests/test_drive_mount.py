#!/usr/bin/env python3
"""image-teardown finds Team Drive through the shared mount helper —
SI-39 (teardown mount helper).

    python3 tests/test_drive_mount.py

No key, no network, no model. Never reads the real mount: every read goes
through a patched P.DRIVE_MOUNTED / DI.mount / swipe_home.MOUNT and a temp
folder. Stills are read from the swipe home (SI-93 (stills swipe home)), never
the old lab folders.
"""
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))
sys.path.insert(0, str(LANE))

import paths as P                     # noqa: E402
import gpt_drafts as G                # noqa: E402
import swipe_intake as SI             # noqa: E402
import chain as C                     # noqa: E402
for _r in LANE.parents:               # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home                     # noqa: E402


class DriveMount(unittest.TestCase):

    def test_shared_assets_from_the_shared_helper(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with mock.patch.object(P.DI, "mount", return_value=tmp):
                self.assertEqual(P._shared_assets(), tmp)
        with mock.patch.object(P.DI, "mount", return_value=None):
            self.assertEqual(P._shared_assets(), P.NO_MOUNT)
        with mock.patch.object(P.DI, "mount",
                               side_effect=OSError(11, "Resource deadlock avoided")):
            self.assertEqual(P._shared_assets(), P.NO_MOUNT)
        self.assertFalse(P.NO_MOUNT.exists())

    def test_every_drive_path_hangs_off_one_root(self):
        self.assertEqual(P.DRIVE, P.SHARED_ASSETS.joinpath(*P.DRIVE_SUBDIR))
        self.assertEqual(SI.DRIVE, swipe_home.root("paid"))
        self.assertEqual(G.ELEMENTS, P.SHARED_ASSETS / "brands")
        self.assertEqual(P.DRIVE_MOUNTED, P.SHARED_ASSETS != P.NO_MOUNT)

    def _stills(self, tmp, rel, names):
        photos = tmp / rel
        photos.mkdir(parents=True)
        for n in names:
            (photos / n).write_bytes(b"")
        with mock.patch.object(swipe_home, "MOUNT", return_value=tmp), \
                mock.patch.object(P, "DRIVE_MOUNTED", True):
            return C.all_stills({"file": "01_x.md"}, "zz-swipe")

    def test_stills_off_a_mount(self):
        with tempfile.TemporaryDirectory() as t:
            got = self._stills(Path(t), "swipe/paid/zz-swipe/blocks/01_x/photos",
                               ("b.jpg", "a.png", "c.txt"))
            self.assertEqual([p.name for p in got], ["a.png", "b.jpg"])

    def test_organic_post_stills_found(self):
        with tempfile.TemporaryDirectory() as t:
            got = self._stills(Path(t), "swipe/organic/zz-swipe/posts/01_x/photos",
                               ("a.jpg",))
            self.assertEqual([p.name for p in got], ["a.jpg"])

    def test_old_lab_home_never_read(self):
        with tempfile.TemporaryDirectory() as t:
            got = self._stills(Path(t), "the team notes/swipe-paid/zz-swipe/blocks/01_x/photos",
                               ("a.png", "b.jpg"))
            self.assertEqual(got, [])

    def test_no_mount_is_said_once(self):
        err = io.StringIO()
        with mock.patch.object(P, "DRIVE_MOUNTED", False), \
                mock.patch.object(C, "_SAID", set()), \
                contextlib.redirect_stderr(err):
            first = C.all_stills({"file": "01_x.md"}, "zz-swipe")
            second = C.all_stills({"file": "02_y.md"}, "zz-swipe")
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(err.getvalue().count(P.NO_MOUNT_NOTE), 1)

    def test_no_account_typed(self):
        account = "GoogleDrive-" + "damon@"          # split, so this file is not a hit
        typed = {str(f.relative_to(LANE)) for f in LANE.rglob("*.py")
                 if account in f.read_text(errors="replace")}
        # tools/variations.py is SI-34 (no Drive delete)'s; green either way.
        self.assertLessEqual(typed, {"tools/variations.py"})
        for rel in ("tools/paths.py", "tools/swipe_intake.py",
                    "tools/gpt_drafts.py", "chain.py"):
            text = (LANE / rel).read_text()
            self.assertNotIn("GoogleDrive-", text, rel)
            self.assertNotIn("CloudStorage/GoogleDrive", text, rel)


if __name__ == "__main__":
    unittest.main()
