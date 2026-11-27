#!/usr/bin/env python3
"""A Drive read that fails is named, never a traceback — LD-3 (preflight
names read errors).

    python3 tests/test_preflight_read_errors.py

The mini's preflight died on EDEADLK off a Drive placeholder: Python 3.9's
is_dir() lets every OSError but "not there" through, up into main(), and
`chain.py start` printed only 'preflight failed'. These tests make that read
fail on purpose and check what a person sees.

No key, no network, no Drive. The mount is a temp folder through a patched
swipe_home.MOUNT, and Path.is_dir / Path.exists raise only for paths under it.
"""
import argparse
import contextlib
import errno
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))
sys.path.insert(0, str(LANE))

import paths as P                     # noqa: E402
import preflight as PF                # noqa: E402
import chain as C                     # noqa: E402
import swipe_home                     # noqa: E402  (put on the path by preflight)

DEADLOCK = (errno.EDEADLK, "Resource deadlock avoided")
_REAL_IS_DIR = Path.is_dir
_REAL_EXISTS = Path.exists
NOBRAND = "zz-nobrand"                # a brand that does not exist, on purpose
SWIPE = "zz-swipe"


def _refuse_under(root, real):
    """A Path method that raises EDEADLK for anything under root."""
    def method(self, *args, **kwargs):
        if str(self).startswith(str(root)):
            raise OSError(*DEADLOCK)
        return real(self, *args, **kwargs)
    return method


@contextlib.contextmanager
def drive_refuses(root):
    """The mount is root, and every is_dir() under it fails the way the mini's did."""
    with mock.patch.object(swipe_home, "MOUNT", return_value=root), \
            mock.patch.object(Path, "is_dir", _refuse_under(root, _REAL_IS_DIR)):
        yield


def _row(rows, label):
    hit = [r for r in rows if r[0] == label]
    assert len(hit) == 1, (label, rows)
    return hit[0]


class InputsNameTheReadError(unittest.TestCase):

    def test_is_dir_refused_is_a_failing_swipe_on_drive_row(self):
        with tempfile.TemporaryDirectory() as t, drive_refuses(Path(t)):
            rows = PF.inputs(NOBRAND, None, None, SWIPE)
        label, path, ok, kind, why = _row(rows, "swipe on Drive")
        self.assertFalse(ok)
        self.assertEqual(kind, "fail")
        self.assertEqual(Path(path), Path(t) / "swipe/paid" / SWIPE / "blocks")
        self.assertEqual(why, "unreadable: EDEADLK (Resource deadlock avoided)")
        # every other row read normally: a missing brand is missing, not unreadable
        self.assertTrue(all(r[4] is None for r in rows if r[0] != "swipe on Drive"))

    def test_mount_read_refused_names_the_drive_label(self):
        with mock.patch.object(swipe_home, "path", side_effect=OSError(*DEADLOCK)):
            label, path, ok, kind, why = _row(PF.inputs(NOBRAND, None, None, SWIPE),
                                              "swipe on Drive")
        self.assertFalse(ok)
        self.assertEqual(path, f"Shared Assets/swipe/paid/{SWIPE}/blocks")
        self.assertIn("EDEADLK", why)

    def test_exists_refused_is_a_failing_row(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "blocks"
            with mock.patch.object(PF, "drive_swipe", return_value=d), \
                    mock.patch.object(Path, "exists", _refuse_under(Path(t), _REAL_EXISTS)):
                label, path, ok, kind, why = _row(PF.inputs(NOBRAND, None, None, SWIPE),
                                                  "swipe on Drive")
        self.assertEqual(path, d)
        self.assertFalse(ok)
        self.assertEqual(why, "unreadable: EDEADLK (Resource deadlock avoided)")


class MainEndsInThingsToFix(unittest.TestCase):

    def _main(self, *patches):
        out, err = io.StringIO(), io.StringIO()
        argv = ["preflight.py", "--brand", NOBRAND, "--swipe", SWIPE]
        with contextlib.ExitStack() as st:
            for p in (mock.patch.object(sys, "argv", argv),
                      mock.patch.object(PF, "audit", return_value=[]),
                      mock.patch.object(PF, "placeholders", return_value=[]),
                      mock.patch.object(PF, "briefs_have_drafts", return_value=[]),
                      *patches):
                st.enter_context(p)
            st.enter_context(contextlib.redirect_stdout(out))
            st.enter_context(contextlib.redirect_stderr(err))
            with self.assertRaises(SystemExit) as cm:
                PF.main()
        return cm.exception.code, out.getvalue(), err.getvalue()

    def test_an_unreadable_drive_exits_1_with_a_fail_line_and_no_traceback(self):
        with tempfile.TemporaryDirectory() as t:
            with drive_refuses(Path(t)):
                code, out, err = self._main()
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", out + err)
        self.assertRegex(out, r"(?m)^  FAIL  swipe on Drive +\S+/swipe/paid/zz-swipe/blocks"
                              r"  unreadable: EDEADLK \(Resource deadlock avoided\)$")
        self.assertRegex(out.strip().splitlines()[-1], r"^\d+ things? to fix$")
        # the stills count is not tried against a Drive that just refused a read
        self.assertNotIn("runnable blocks", out)

    def test_a_coverage_read_error_is_a_fail_line_too(self):
        with tempfile.TemporaryDirectory() as t:
            refused = PF.Unreadable(f"{t}/swipe/paid/{SWIPE}/blocks", OSError(*DEADLOCK))
            code, out, err = self._main(
                mock.patch.object(PF, "drive_swipe", return_value=Path(t)),
                mock.patch.object(PF, "swipe_coverage", return_value=refused))
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", out + err)
        self.assertIn(f"  FAIL  swipe on Drive    {t}/swipe/paid/{SWIPE}/blocks"
                      f"  unreadable: EDEADLK (Resource deadlock avoided)", out)
        self.assertRegex(out.strip().splitlines()[-1], r"^\d+ things? to fix$")


class CoverageNeverRaises(unittest.TestCase):

    def test_pick_still_oserror_comes_back_unreadable(self):
        with mock.patch.object(C, "blocks", return_value=[{"file": "01_x.md"}]), \
                mock.patch.object(C, "pick_still", side_effect=OSError(*DEADLOCK)):
            got = PF.swipe_coverage(SWIPE)
        self.assertIsInstance(got, PF.Unreadable)
        self.assertEqual(got.path, f"Shared Assets/swipe/paid/{SWIPE}/blocks")
        self.assertEqual(PF.unreadable(got.err),
                         "unreadable: EDEADLK (Resource deadlock avoided)")

    def test_refused_stills_count_as_none(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as t, drive_refuses(Path(t)), \
                mock.patch.object(P, "DRIVE_MOUNTED", True), \
                mock.patch.object(C, "blocks", return_value=[{"file": "01_x.md"}]), \
                contextlib.redirect_stderr(err):
            got = PF.swipe_coverage(SWIPE)
        self.assertEqual(got, (0, 1))
        self.assertIn("EDEADLK", err.getvalue())


class AllStillsReadsRefusalAsNoStills(unittest.TestCase):

    def test_refused_everywhere_is_empty_and_one_stderr_line(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as t, drive_refuses(Path(t)), \
                mock.patch.object(P, "DRIVE_MOUNTED", True), \
                contextlib.redirect_stderr(err):
            got = C.all_stills({"file": "01_x.md"}, SWIPE)
        self.assertEqual(got, [])
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(f"Shared Assets/swipe/paid/{SWIPE}/blocks/01_x/photos", lines[0])
        self.assertIn("EDEADLK (Resource deadlock avoided)", lines[0])

    def test_one_refused_folder_does_not_hide_another_with_stills(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            photos = tmp / "swipe/organic" / SWIPE / "posts/01_x/photos"
            photos.mkdir(parents=True)
            (photos / "a.jpg").write_bytes(b"")
            bad = tmp / "swipe/paid"
            with mock.patch.object(swipe_home, "MOUNT", return_value=tmp), \
                    mock.patch.object(Path, "is_dir", _refuse_under(bad, _REAL_IS_DIR)), \
                    mock.patch.object(P, "DRIVE_MOUNTED", True), \
                    contextlib.redirect_stderr(err):
                got = C.all_stills({"file": "01_x.md"}, SWIPE)
        self.assertEqual([p.name for p in got], ["a.jpg"])
        self.assertEqual(len(err.getvalue().splitlines()), 1)


class StartShowsTheChildsStderr(unittest.TestCase):

    def test_failure_prints_stdout_then_stderr(self):
        child = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="INPUTS — zz\n  FAIL  brand folder  /x\n\n1 thing to fix\n",
            stderr="Traceback (most recent call last):\n"
                   "OSError: [Errno 11] Resource deadlock avoided\n")
        a = argparse.Namespace(brand=NOBRAND, product="p", avatar="a", swipe=SWIPE)
        out = io.StringIO()
        with mock.patch.object(C.subprocess, "run", return_value=child) as run, \
                contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                C.start(a)
        self.assertEqual(run.call_args[0][0][0], sys.executable)
        text = out.getvalue()
        self.assertIn("1 thing to fix", text)
        self.assertIn("OSError: [Errno 11] Resource deadlock avoided", text)
        self.assertLess(text.index("1 thing to fix"), text.index("Traceback"))
        self.assertIn("preflight failed", str(cm.exception.code))


if __name__ == "__main__":
    unittest.main()
