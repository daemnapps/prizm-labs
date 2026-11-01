#!/usr/bin/env python3
"""ad-handoff — every verdict leaves a record the runs filer can see (SI-103).

    python3 components/ad-handoff/tests/test_verdict_record.py

Offline: no network, no Drive, no model. A REFUSED and a READY hand-off each
write runs/ad-handoff/<brand>/<drop>/{run.json, check.json} under a temp
runs root, and the runs filer's own `held()` reads them the right way round.
"""
import importlib.util, io, json, sys, tempfile, unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import handoff as H
from test_ad_handoff import build

FILER = H.WS / "platform/workers/mini-worker/runs_filer.py"
_spec = importlib.util.spec_from_file_location("runs_filer_under_test", FILER)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)


def run_main(drop_dir, runs):
    """main() on --dir <drop> --check --offline; (exit code, stdout)."""
    argv = ["handoff.py", "--dir", str(drop_dir), "--check", "--offline"]
    out, code = io.StringIO(), 0
    with mock.patch.object(H, "RUNS", Path(runs)), mock.patch.object(sys, "argv", argv), \
            redirect_stdout(out):
        try:
            H.main()
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


class TestVerdictRecord(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        t = Path(self._t.name)
        self.drop = t / "acme" / "260101a" / "deliverable"
        self.runs = t / "runs" / "ad-handoff"
        self.rec = self.runs / "acme" / "260101a"

    def tearDown(self):
        self._t.cleanup()

    def read(self, name):
        return json.loads((self.rec / name).read_text())

    def test_a_refused_handoff_is_recorded_held(self):
        build(self.drop, copy=False)
        code, out = run_main(self.drop, self.runs)
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        run, check = self.read("run.json"), self.read("check.json")
        self.assertEqual(run["tool"], "ad-handoff")
        self.assertEqual((run["brand"], run["drop"]), ("acme", "260101a"))
        self.assertEqual(run["state"], "refused")
        self.assertIs(run["check_only"], True)
        self.assertIsNone(run["link"])
        self.assertTrue(run["at"].endswith("Z"))
        self.assertIs(check["held"], True)
        self.assertTrue(any("no copy.csv" in p for p in check["problems"]), check)
        self.assertTrue(F.held(self.rec))

    def test_a_clean_offline_handoff_is_recorded_partial_not_held(self):
        """Narrowed by SI-149: --offline skips checks, so a clean drop is PARTIAL
        (exit 2, state partial), never READY — and still not held."""
        build(self.drop)
        code, out = run_main(self.drop, self.runs)
        self.assertEqual(code, 2)
        self.assertIn("PARTIAL", out)
        self.assertNotIn("READY", out)
        run, check = self.read("run.json"), self.read("check.json")
        self.assertEqual(run["state"], "partial")
        self.assertIsNone(run["link"])            # offline: no Drive folder, no link
        self.assertEqual(check, {"held": False, "problems": []})
        self.assertFalse(F.held(self.rec))

    def test_a_record_that_cannot_be_written_changes_nothing_else(self):
        build(self.drop, copy=False)
        self.runs.parent.mkdir(parents=True)
        self.runs.write_text("a file where the runs folder should be")
        err = io.StringIO()
        with redirect_stderr(err):
            code, out = run_main(self.drop, self.runs)
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1, err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
