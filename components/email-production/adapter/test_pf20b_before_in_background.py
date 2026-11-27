"""PF-20b (before in background): the emails list never waits for a "before" picture (the team, 2026-10-29: her page
server's copy sat on "Loading your emails…" for minutes while every received-<rev>.jpg was re-made).

A missing picture is `pending` on the row and made by ONE background maker; a failure is named on the row. The
render, the git lookups and the process start are faked: no Chrome, no git, no network.

    /usr/bin/python3 test_pf20b_before_in_background.py
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "design"))
import received as R  # noqa: E402
import sync as S  # noqa: E402

SPEC = {"sections": [{"s": "letter", "text": "hello"}]}
FOUND = {"rev": "abc1234567", "by": "the team", "at": "2026-10-29T10:00:00-03:00", "waiting": True}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.tmp))
        self.run_dir = self.tmp / "fx" / "fx-nov-01"
        (self.run_dir / "design").mkdir(parents=True)
        state = self.tmp / "state"
        state.mkdir()
        for name, value in (("found", lambda run: dict(FOUND)), ("spec_at", lambda run, rev: SPEC),
                            ("_state_dir", lambda: state)):
            p = mock.patch.object(R, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.pic = self.run_dir / "design" / "received-abc1234567.jpg"


class TheList(Base):
    def test_a_missing_picture_is_pending_and_never_rendered_in_the_list(self):
        missing = []
        with mock.patch.object(R, "picture", side_effect=AssertionError("the list must not render")):
            row = S._before(self.run_dir, SPEC, missing)
        self.assertTrue(row["before"]["pending"])
        self.assertTrue(row["before"]["waiting"])
        self.assertEqual(row["_before_pending"], str(self.pic))
        self.assertNotIn("_before", row)
        self.assertEqual(missing, [self.run_dir])

    def test_a_picture_on_disk_is_served_as_before(self):
        self.pic.write_bytes(b"jpg")
        missing = []
        row = S._before(self.run_dir, SPEC, missing)
        self.assertEqual(row["_before"], str(self.pic))
        self.assertNotIn("pending", row["before"])
        self.assertEqual(missing, [])

    def test_a_failed_picture_is_named_on_the_row_and_not_retried(self):
        R._error_file(self.run_dir, FOUND).write_text("RuntimeError: headless Chrome made no picture")
        missing = []
        row = S._before(self.run_dir, SPEC, missing)
        self.assertEqual(row["before"]["error"], "RuntimeError: headless Chrome made no picture")
        self.assertNotIn("pending", row["before"])
        self.assertEqual(missing, [])


class TheMaker(Base):
    def test_only_one_maker_runs_at_a_time(self):
        started = []

        class P:
            pid = 4242

        def popen(argv, **kw):
            started.append(argv)
            return P()
        with mock.patch.object(R, "_alive", return_value=True):
            self.assertTrue(R.start_maker([self.run_dir], popen=popen))      # no lock yet: starts
            self.assertFalse(R.start_maker([self.run_dir], popen=popen))     # pid 4242 alive: does not
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0][1:3], [str(Path(R.__file__).resolve()), "--make"])
        with mock.patch.object(R, "_alive", return_value=False):
            self.assertTrue(R.start_maker([self.run_dir], popen=popen))      # the old one is gone: starts again

    def test_nothing_missing_starts_nothing(self):
        self.assertFalse(R.start_maker([], popen=lambda *a, **k: self.fail("started")))

    def test_the_maker_makes_what_is_missing_and_skips_what_exists(self):
        other = self.tmp / "fx" / "fx-nov-02"
        (other / "design").mkdir(parents=True)
        (other / "design" / "received-abc1234567.jpg").write_bytes(b"jpg")
        made = []

        def make(run, f):
            made.append(Path(run))
            R.picture_path(run, f).write_bytes(b"jpg")
        done, bad = R.make_missing([self.run_dir, other], make=make)
        self.assertEqual(made, [self.run_dir])
        self.assertEqual((len(done), bad), (1, []))
        self.assertTrue(self.pic.is_file())

    def test_a_failure_is_written_down_and_the_next_one_goes_on(self):
        other = self.tmp / "fx" / "fx-nov-02"
        (other / "design").mkdir(parents=True)

        def make(run, f):
            if Path(run) == self.run_dir:
                raise RuntimeError("no Chrome")
            R.picture_path(run, f).write_bytes(b"jpg")
        done, bad = R.make_missing([self.run_dir, other], make=make)
        self.assertEqual((done, bad), ([str(other)], [str(self.run_dir)]))
        self.assertEqual(R.error(self.run_dir, FOUND), "RuntimeError: no Chrome")
        self.assertIsNone(R.error(other, FOUND))


if __name__ == "__main__":
    unittest.main()
