#!/usr/bin/env python3
"""The run log lives on the runs plane, not inside the component (SI-26).

    python3 components/local-studio/test_run_log.py

No network. Only test_the_log_moved_whole reads the real log; nothing here writes it.
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_spec = importlib.util.spec_from_file_location("local_studio_local", Path(__file__).resolve().parent / "local.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


class RunLogTest(unittest.TestCase):
    def setUp(self):
        self._runs = m.RUNS
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        m.RUNS = self._runs
        self._tmp.cleanup()

    def _probe_run(self, log):
        m.RUNS = log
        with redirect_stdout(io.StringIO()):
            return m.run(["/usr/bin/true"], "probe", {"tool": "t"})

    def test_runs_lives_on_the_runs_plane(self):
        self.assertEqual(m.RUNS, m.REPO / "runs" / "local-studio" / "_system" / "runs.jsonl")
        self.assertNotIn("components", m.RUNS.relative_to(m.REPO).parts)

    def test_run_makes_parents_and_appends_one_line(self):
        log = self.tmp / "a" / "b" / "runs.jsonl"
        self.assertFalse(log.parent.exists())
        rec = self._probe_run(log)
        self.assertTrue(log.exists())
        lines = log.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        row = json.loads(lines[0])
        self.assertEqual(row["job"], "probe")
        self.assertIsInstance(row["seconds"], (int, float))
        self.assertEqual(row["tool"], "t")
        self.assertEqual(rec, row)

    def test_runs_prints_rows_and_says_when_empty(self):
        self._probe_run(self.tmp / "x" / "runs.jsonl")
        out = io.StringIO()
        with redirect_stdout(out):
            m.job_runs(None)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("probe", lines[0])

        m.RUNS = self.tmp / "missing" / "runs.jsonl"
        out = io.StringIO()
        with redirect_stdout(out):
            m.job_runs(None)
        self.assertEqual(out.getvalue().strip(), "no runs yet")

    @unittest.skipUnless(m.RUNS.exists(), "the run log is run output and does not ship in the public copy")
    def test_the_log_moved_whole(self):
        self.assertTrue(m.RUNS.exists())
        lines = m.RUNS.read_text().splitlines()
        self.assertGreaterEqual(len(lines), 26)
        for line in lines:
            row = json.loads(line)
            self.assertIsInstance(row, dict)
            for key in ("job", "when", "seconds"):
                self.assertIn(key, row)
        first = json.loads(lines[0])
        self.assertEqual(first["job"], "upscale")
        self.assertEqual(first["when"], "2026-09-27 15:37:50")
        self.assertFalse((Path(m.ROOT) / "bench" / "runs.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
