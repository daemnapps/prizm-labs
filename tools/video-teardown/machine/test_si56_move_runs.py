#!/usr/bin/env python3
"""SI-56 (teardown working home): move_runs.py carries a Mac's old working runs
into runs/video-teardown/_work/ once — never overwrites, never merges, skips a
run in flight, removes the old folder only when it is empty.

    /usr/bin/python3 tools/video-teardown/machine/test_si56_move_runs.py

Stdlib only, no key, no network. Every tree is a temp folder.
"""
import contextlib, io, os, sys, tempfile, time, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import move_runs                                            # noqa: E402

LATER = time.time() + 3600          # every entry made below is an hour old by this clock


def _run(src, name, body=b"{}"):
    d = src / name
    (d / "stages").mkdir(parents=True)
    (d / "run.json").write_bytes(body)
    (d / "stages" / "1-teardown.md").write_bytes(b"| 0:01 | v | - | A: hi |\n")
    return d


def _call(argv, src, dest, now=LATER):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = move_runs.main(argv, src=src, dest=dest, now=now)
    return code, out.getvalue()


class MoveRuns(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.t = Path(self._t.name)
        self.src, self.dest = self.t / "src", self.t / "dest"
        self.src.mkdir()
        _run(self.src, "r1")
        _run(self.src, "r2")
        (self.src / "_general-queue.txt").write_text("a\tb\tc\n")

    def tearDown(self):
        self._t.cleanup()

    def test_a_dry_run_moves_nothing(self):
        code, out = _call([], self.src, self.dest)
        self.assertEqual(code, 0)
        for name in ("_general-queue.txt", "r1", "r2"):
            self.assertEqual(out.count(f"would move {name}"), 1, out)
        self.assertEqual(sorted(p.name for p in self.src.iterdir()), ["_general-queue.txt", "r1", "r2"])
        self.assertFalse(self.dest.exists())

    def test_b_go_moves_runs_and_loose_files_and_removes_the_old_folder(self):
        code, out = _call(["--go"], self.src, self.dest)
        self.assertEqual(code, 0, out)
        self.assertFalse(self.src.exists())
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ["_general-queue.txt", "r1", "r2"])
        self.assertTrue((self.dest / "r1" / "stages" / "1-teardown.md").is_file())
        self.assertEqual((self.dest / "_general-queue.txt").read_text(), "a\tb\tc\n")
        for name in ("_general-queue.txt", "r1", "r2"):
            self.assertIn(f"moved {name}", out)

    def test_c_a_name_already_there_is_skipped_never_merged(self):
        _run(self.dest, "r1", body=b'{"theirs": 1}')
        (self.dest / "r1" / "extra.md").write_bytes(b"dest only")
        before_src = (self.src / "r1" / "run.json").read_bytes()
        code, out = _call(["--go"], self.src, self.dest)
        self.assertEqual(code, 2, out)
        self.assertIn("SKIPPED r1", out)
        self.assertIn("already in", out)
        self.assertEqual((self.src / "r1" / "run.json").read_bytes(), before_src)
        self.assertEqual((self.dest / "r1" / "run.json").read_bytes(), b'{"theirs": 1}')
        self.assertEqual((self.dest / "r1" / "extra.md").read_bytes(), b"dest only")
        self.assertFalse((self.src / "r1" / "extra.md").exists())
        self.assertTrue(self.src.is_dir())                        # kept: not empty
        self.assertEqual([p.name for p in self.src.iterdir()], ["r1"])
        self.assertTrue((self.dest / "r2").is_dir())

    def test_d_a_run_in_flight_waits_unless_forced(self):
        now = time.time()
        os.utime(self.src / "r1" / "run.json", (now - 60, now - 60))
        old = now - 7200
        for p in (self.src / "r1", self.src / "r2", self.src / "r2" / "run.json"):
            os.utime(p, (old, old))
        code, out = _call(["--go"], self.src, self.dest, now=now)
        self.assertEqual(code, 2, out)
        self.assertIn("SKIPPED r1 — in flight", out)
        self.assertTrue((self.src / "r1" / "run.json").is_file())
        self.assertTrue((self.dest / "r2").is_dir())
        code, out = _call(["--go", "--force"], self.src, self.dest, now=now)
        self.assertEqual(code, 0, out)
        self.assertIn("moved r1", out)
        self.assertTrue((self.dest / "r1" / "run.json").is_file())
        self.assertFalse(self.src.exists())

    def test_e_nothing_to_move(self):
        code, out = _call(["--go"], self.t / "absent", self.dest)
        self.assertEqual(code, 0)
        self.assertIn("nothing to move", out)
        self.assertFalse(self.dest.exists())

    def test_it_never_imports_the_chain(self):
        src = (HERE / "move_runs.py").read_text(encoding="utf-8")
        self.assertNotIn("import chain", src)
        self.assertNotIn("rmtree", src)


if __name__ == "__main__":
    unittest.main()
