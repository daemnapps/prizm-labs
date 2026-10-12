#!/usr/bin/env python3
"""SI-48 (teardown drops home): a variation drop files at
runs/image-teardown/<brand>/<drop>/ as an image-teardown run, and a drop filed
before 2026-10-07 at the legacy runs/image-edit/ home is refused, never continued.

    python3 tests/test_drop_home.py

No key, no network, no PIL. Every path is a temp folder: nothing is written
under the real runs/, brands/ or the Drive.
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))
sys.path.insert(0, str(LANE))

import variations as V                # noqa: E402


class Constants(unittest.TestCase):
    def test_home_constants(self):
        self.assertEqual(V.DROPS, V.WS / "runs" / "image-teardown")
        self.assertEqual(V.LEGACY_DROPS, V.WS / "runs" / "image-edit")


class DropHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.new = self.root / "runs" / "image-teardown"
        self.old = self.root / "runs" / "image-edit"
        for name, value in (("DROPS", self.new), ("LEGACY_DROPS", self.old)):
            p = mock.patch.object(V, name, value)
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_drop_goes_home(self):
        self.assertEqual(V.drop_home("zz-brand", "d1"), self.new / "zz-brand" / "d1")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_legacy_drop_is_refused(self):
        legacy = self.old / "zz-brand" / "d1"
        legacy.mkdir(parents=True)
        (legacy / "drop.json").write_text("{}\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                V.drop_home("zz-brand", "d1")
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("is frozen there", err.getvalue())

        (self.new / "zz-brand" / "d1").mkdir(parents=True)
        self.assertEqual(V.drop_home("zz-brand", "d1"), self.new / "zz-brand" / "d1")

    def test_no_image_edit_run_path_is_written(self):
        src = (LANE / "tools" / "variations.py").read_text()
        self.assertNotIn('"machine": "image-edit"', src)
        self.assertNotIn('WS / "runs/image-edit"', src)
        self.assertIn('"machine": P.TOOL', src)
        lines = [ln for ln in src.splitlines() if "runs/image-edit" in ln]
        self.assertTrue(lines)
        for ln in lines:
            self.assertTrue(ln.startswith("LEGACY_DROPS") or "is filed at runs/image-edit/" in ln, ln)

    def test_gemini_text_requires_out(self):
        prompt = self.root / "prompt.md"
        prompt.write_text("say nothing\n")
        r = subprocess.run([sys.executable, str(LANE / "tools/gemini_text.py"),
                            "--prompt-file", str(prompt)],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--out", r.stderr)


if __name__ == "__main__":
    unittest.main()
