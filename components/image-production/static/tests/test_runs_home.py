#!/usr/bin/env python3
"""The batch road's home. stdlib only, no key, no network, no PIL.

    /usr/bin/python3 static/tests/test_runs_home.py

  a  a batch lives at the record home, runs/image-production/; RUNS (the
     swipe road's) is unchanged
  b  the documented `runs/<brand>/<batch>` form, and its two siblings,
     resolve to that home; an absolute path comes back as given
  c  a batch folder inside the tool's own runs/ is refused, exit 2, naming
     the new home — unless asked non-strictly
  d  a batch whose folder IS its record folder files without copying a file
     onto itself, and run.json is written
  e  the new home is named once, in paths.py

SI-49 (static runs home), image-production#12. Before it, `shutil.copy` raised
SameFileError the first time a batch's working folder was its record folder.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))
import paths as P   # noqa: E402
import gates as G   # noqa: E402


class TestRunsHome(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def test_batches_live_at_the_record_home(self):
        self.assertEqual(P.BATCHES, P.REPO / "runs" / "image-production")
        self.assertEqual(P.BATCHES, P.RECORDS)
        self.assertEqual(P.RUNS, P.PROD / "runs")

    def test_documented_form_resolves_home(self):
        home = (P.BATCHES / "zz-brand" / "b1").resolve()
        was = os.getcwd()
        os.chdir(self.tmp)
        try:
            self.assertEqual(P.run_dir("runs/zz-brand/b1"), home)
            self.assertEqual(P.run_dir("zz-brand/b1"), home)
            self.assertEqual(P.run_dir("runs/image-production/zz-brand/b1"), home)
            given = self.tmp / "elsewhere" / "b1"
            self.assertEqual(P.run_dir(str(given)), given.resolve())
        finally:
            os.chdir(was)

    def test_a_batch_beside_the_code_is_refused(self):
        legacy = self.tmp / "legacy"
        batch = legacy / "zz-brand" / "b1"
        batch.mkdir(parents=True)
        with mock.patch.object(P, "RUNS", legacy):
            err = io.StringIO()
            with redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    P.run_dir(str(batch))
            self.assertEqual(cm.exception.code, 2)
            said = err.getvalue()
            self.assertTrue(said.startswith("refused:"), said)
            self.assertIn("runs/image-production/<brand>/<batch>/", said)
            self.assertEqual(P.run_dir(str(batch), strict=False), batch.resolve())

    def test_record_files_into_its_own_folder(self):
        records = self.tmp / "runs" / "image-production"
        (self.tmp / "brands" / "zz-brand").mkdir(parents=True)
        run = records / "zz-brand" / "b1"
        run.mkdir(parents=True)
        spec = json.dumps({"brand": "zz-brand", "batch": "b1", "ads": []})
        (run / "batch.json").write_text(spec)
        (run / "report.md").write_text("# report\n")
        before = (run / "batch.json").read_bytes()
        with mock.patch.object(P, "REPO", self.tmp), \
                mock.patch.object(P, "RECORDS", records), \
                mock.patch.object(P, "BRANDS", self.tmp / "brands"):
            dst = G.file_record(run)
        self.assertEqual(dst, run.resolve())
        rec = json.loads((run / "run.json").read_text())
        self.assertEqual(rec["machine"], "image-production")
        self.assertEqual(rec["label"], "b1")
        self.assertIn("batch.json", rec["files"])
        self.assertEqual((run / "batch.json").read_bytes(), before)

    def test_the_new_home_is_named_once(self):
        src = (TOOLS / "paths.py").read_text()
        self.assertIn("BATCHES = RECORDS", src)
        self.assertIn("def run_dir(", src)


if __name__ == "__main__":
    unittest.main()
